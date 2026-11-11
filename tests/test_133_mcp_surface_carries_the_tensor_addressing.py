# Copyright holders : Commissariat à l'Energie Atomique
# et aux Energies Alternatives (CEA), France; and Laboratory for
# Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C
# open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted
# upon downloading the software and/or exercising any of the rights
# granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The standalone MCP surface carries the same tensor addressing the agent
already has.

One shared core, two surfaces. The in-app agent and the web page take the
addressing of a multi-axis quantity from the rich `TOOLS` of
`imasviz/VizAgent/tools.py` (the `along` / `indices` pair `test_125` pins),
and the core they dispatch onto (`imasviz/VizAgent/core.py`) already
answers them: `plot_one` takes `along` / `indices` / `time` / `time_interp`
and `get_signal` takes `along` / `indices`. `test_124` and `test_132` prove
that the *read* and the *draw* of a pressure profile held by a dynamic time
array address the same element -- along the clock at one `psi`, along the
clock at two `psi` on one figure, and the peaks that fall off it.

The one surface that lagged was the standalone MCP
server (`python -m mcp_server`, the entry external MCP clients use):
`mcp_server/tools.py` exposed `plot_one` with only `along_time` /
`into_figure_key` and `get_signal` with only the legacy
`as_function_of_time` / `coordinate_index` / `time_index`, and it had no
`plot_slice` at all. A client of that server could therefore not name the
axis a profile runs along, nor pin the others at an index -- the "soucis
avec les traces de signaux multi-axes" the field met, on the surface that
serves them. The core behind it already does it, so the fix is a matter of
letting that surface name and forward the same parameters.

Pinned at the source, not by import: `mcp_server/tools.py` is decorated
from the MCP SDK (`from mcp.server.fastmcp import FastMCP`), and importing
it for a text assertion would drag the SDK into the guard for no reason.
This reads the declarations the way `test_121` reads the page -- a name a
surface does not carry is one its clients cannot reach, so the two
surfaces the one core serves have to stop agreeing in one half only.
"""

import os
import re

TOOLS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'mcp_server', 'tools.py')


def _sourceOf(name):
    """The `def name( ... )` of one declared tool, and its body.

    From the `def` up to the next `@server.tool`, the section divider or a
    two-blank-line break -- the shape the file lays that tool's body out.
    A declaration that is not there is an assertion of its own, naming the
    tool, rather than an empty slice the checks pass over.
    """
    with open(TOOLS, 'r', encoding='utf-8') as f:
        text = f.read()
    found = re.search(
        r'def %s\(.*?(?=\n\s*@server\.tool|\n\s*# ----|\n\n\n|\Z)'
        % re.escape(name), text, re.S)
    assert found is not None, 'no @server.tool function def %s in mcp_server/tools.py' % name
    return found.group(0)


def _signatureHas(name, param):
    """The `def name(` carries the parameter, before its first close-paren."""
    signature = re.match(r'def %s\([^)]*\)' % re.escape(name), _sourceOf(name))
    assert signature is not None, 'no readable def signature for %s' % name
    return param in signature.group(0)


def test_plot_one_names_and_forwards_the_addressing():
    body = _sourceOf('plot_one')
    for param in ('along', 'indices'):
        assert _signatureHas('plot_one', param), \
            'plot_one does not name %s: the MCP surface cannot address a ' \
            'profile by axis' % param
    assert 'along' in body and 'indices' in body, \
        'plot_one names the addressing but does not forward it to the core'


def test_get_signal_names_and_forwards_the_addressing():
    body = _sourceOf('get_signal')
    for param in ('along', 'indices'):
        assert _signatureHas('get_signal', param), \
            'get_signal does not name %s: the read and the draw would ' \
            'address different elements again' % param
    assert 'along' in body and 'indices' in body, \
        'get_signal names the addressing but does not forward it to the core'


def test_the_mcp_surface_offers_the_slice_read():
    """`plot_slice` is the one value a slice answers through
    `DBEntry.get_slice` -- the agent surface has it, so the MCP surface
    does not leave that reading out of the two surfaces of the one core.
    """
    assert re.search(r"@server\.tool\(name='plot_slice'\)",
                     open(TOOLS, encoding='utf-8').read()), \
        'no plot_slice tool: the slice read the agent answers is missing ' \
        'from the MCP surface'
