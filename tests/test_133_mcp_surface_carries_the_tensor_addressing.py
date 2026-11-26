# Copyright holders : Commissariat à l’Energie Atomique et aux Energies
# Alternatives (CEA), France; and Laboratory for Engineering Design - LECAD,
# University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C
# open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted
# upon downloading the software and/or exercising any of the rights granted
# under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The tensor addressing is on both faces of the one core, not on one only.

One shared core, two faces. The in-app agent, the page and the socket all
take the addressing of a multi-axis quantity -- `along` to say which axis a
profile runs along, `indices` to pin the others at an element rank -- from
the same `TOOLS` table of `imasviz/VizAgent/tools.py`, and the core they
dispatch onto (`imasviz/VizAgent/core.py`) already answers them: the
drawing's single mode reaches `plot_one(along=, indices=, time=,
time_interp=)` and `get_signal` takes `along` / `indices`. `test_124` and
`test_132` prove that the *read* and the *draw* of a pressure profile held
by a dynamic time array address the same element -- along the clock at one
`psi`, along the clock at two `psi` on one figure, and the peaks that fall
off it.

The face that lagged was the standalone MCP server (`python -m mcp_server`,
the entry external MCP clients use). When this file was written it exposed
`plot_one` with only `along_time` / `into_figure_key` and `get_signal` with
only the legacy `as_function_of_time` / `coordinate_index` / `time_index`,
and it had no slice read at all. A client of that server could therefore
not name the axis a profile runs along, nor pin the others at an index --
the "soucis avec les traces de signaux multi-axes" the field met, on the
face that serves them.

The guard moved when the copy did. This file used to read
`mcp_server/tools.py` as text, hunting the `def plot(...)` of a
hand-written declaration; since T6 that file declares no signature of its
own -- it walks the table and assembles one per entry -- so those three
tests would have hunted a shape that is no longer there, and found
nothing. What they ask now is the table, which is the one place the
addressing is spelled once for every face. That the socket really sends
that table -- every parameter, every note, every action -- is
`test_177`, which reads `list_tools()` rather than a file.
"""

from imasviz.VizAgent.tools import TOOLS, actionsOf

SCHEMAS = {tool['function']['name']: tool['function']['parameters']
           for tool in TOOLS}


def test_the_drawing_names_the_addressing_every_face_sends():
    """`along` and `indices` in the schema the drawing is offered with: the
    axis a curve runs along and the rank of every element it does not run
    along. A surface that carries only `along_time` answers one axis and
    no element, which is the half that was missing."""
    properties = SCHEMAS['plot']['properties']
    for param in ('along', 'indices'):
        assert param in properties, \
            'the drawing offers no %s: a profile cannot be addressed by ' \
            'axis on any face' % param


def test_the_read_names_the_same_addressing_as_the_draw():
    """The word, in the read as in the draw. Two spellings of the same
    question is how the read and the draw came to address *different*
    elements of one array while both looking correct on screen."""
    properties = SCHEMAS['get_signal']['properties']
    for param in ('along', 'indices'):
        assert param in properties, \
            'get_signal offers no %s: the read and the draw would address ' \
            'different elements again' % param


def test_the_slice_read_is_one_mode_of_the_one_drawing():
    """The slice read is the one value answered through `DBEntry.get_slice`.
    It is a mode of the one `plot` entry, as it is on every face: a surface
    that kept five drawing names while the others merged them would be a
    third vocabulary, not the same one served twice.

    And the slice read's own address -- the instant, the occurrence, and
    how the instant is settled between two slices -- is declared beside
    them, because a mode the schema cannot answer is a mode that runs on a
    default nobody chose."""
    assert list(actionsOf('plot')) == ['single', 'slice', 'selection',
                                       'table', 'stacked'], \
        'the drawing no longer answers the five asks: %s' \
        % list(actionsOf('plot'))
    properties = SCHEMAS['plot']['properties']
    for param in ('time', 'occurrence', 'interpolation'):
        assert param in properties, \
            'the slice read is offered without %s' % param
    for merged in ('plot_one', 'plot_slice', 'plot_selection', 'plot_table',
                   'plot_stacked'):
        assert merged not in SCHEMAS, \
            '%s is offered under its own name again: the drawing is one ' \
            'ask with five modes, on every face' % merged
