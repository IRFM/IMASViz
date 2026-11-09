# Copyright holders: Commissariat à l'Energie Atomique et aux Energies
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

"""The figure `plot_one` opens answers the index the user named.

The other half of the same schema `get_signal` uses in
`test_100` (the `along` / `indices` of a quantity). Measured on the case the
user reported (WEST 54924 run 0, `equilibrium` occurrence 0) before this
commit: `get_signal` on
`equilibrium.time_slice[0].profiles_1d.j_tor` named `psi[50]` answered 49
points, one per time slice, while `plot_one` opened the same quantity with its
one slider on `psi[0]` -- one figure, two elements of the same array of
structures. Now both halves go through the shared resolver `axesAddressing`
(see `test_123`, the pure version), so the number the value names and the
element the slider sits on are the same.

This file opens its own session and case rather than joining the journey in
`test_100`: the `Plot` figure namespace keeps only the newest figure of a
kind, and the later tests of `test_100` read the earliest one, so a figure
opened here and a figure opened there cannot share one shared session.
"""

import pytest

from mcp_server.core import McpGuiCore

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI,
                      case_uri_or_skip)

IDS_NAME = 'equilibrium'
JTOR_PATH = 'equilibrium.time_slice[0].profiles_1d.j_tor'

pytestmark = [pytest.mark.case, pytest.mark.ui]


@pytest.fixture(scope='module')
def core(qapp, tmp_path_factory):
    """One session of the core on the reference case, equilibrium loaded."""
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    home = tmp_path_factory.mktemp('addressedPlotCoreHome')
    patch = pytest.MonkeyPatch()
    patch.setenv('HOME', str(home))
    session = McpGuiCore()
    try:
        session.open_case(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
        session.load_ids(CASE_URI, IDS_NAME, 0)
        yield session, home
    finally:
        patch.undo()


def _latestFigure(session):
    """The last figure the session opened: the newest in the Plot namespace."""
    key = sorted(session.api.figureframes)[-1]
    return key, session.api.figureframes[key]


def test_the_figure_opens_at_the_named_leaf_index(core):
    """Along the clock, `psi` is the one axis the figure pins; it opens at 50
    -- not the index 0 the tree happened to carry, which is the reported bug.
    """
    session, _home = core
    answer = session.plot_one(CASE_URI, JTOR_PATH, along=None,
                              indices={'psi': 50})
    key, frame = _latestFigure(session)
    assert answer['figure'] == key
    assert frame.isDrawing(), 'the figure did not draw its curve'

    # The answer says where it opened: on `psi`, at 50.
    assert answer.get('opened_at', {}).get('psi') == 50, answer
    # And the frame carries it: the one slider the figure holds sits at 50.
    controls = frame.sliceControls
    assert controls is not None, 'a profile along time holds a slider for psi'
    assert any(index == 50 for index in controls.indices().values()), \
        controls.indices()
    # ...and it is not the element the tree carried (index 0).
    assert any(index != 0 for index in controls.indices().values())


def test_a_different_named_index_opens_the_slider_there(core):
    """A different named index opens a different figure at that index: the
    comparison moves by hand without sliding back to the tree default.
    """
    session, _home = core
    answer = session.plot_one(CASE_URI, JTOR_PATH, indices={'psi': 42})
    key, frame = _latestFigure(session)
    assert answer['figure'] == key
    assert frame.isDrawing()
    assert answer.get('opened_at', {}).get('psi') == 42, answer
    controls = frame.sliceControls
    assert any(index == 42 for index in controls.indices().values()), \
        controls.indices()


def test_the_same_element_the_value_names_and_the_slider_holds(core):
    """The number and the figure answer one element, the same array, the same
    index: what `get_signal` at `psi[50]` answers is what a curve `plot_one`
    opens at `psi[50]` holds.
    """
    session, _home = core
    numbers = session.get_signal(CASE_URI, JTOR_PATH, along=None,
                                 indices={'psi': 50})
    assert numbers['kind'] == 'curve'
    assert numbers['samples'] > 0
    figure = session.plot_one(CASE_URI, JTOR_PATH, along=None,
                              indices={'psi': 50})
    key, frame = _latestFigure(session)
    assert figure['figure'] == key
    assert frame.isDrawing()
    # The figure holds the index the value was named at, so the two are about
    # the same element of the same array -- the read of psi[50].
    assert any(index == 50 for index in frame.sliceControls.indices().values())


def test_the_time_value_and_a_named_index_are_refused_named(core):
    """`time=` pins one slice; an index in `indices` runs along an axis. The
    two are opposite readings of the same array and are refused together, by
    name, not a silent default.
    """
    session, _home = core
    with pytest.raises(ValueError) as exc:
        session.plot_one(CASE_URI, JTOR_PATH, time=35.0,
                         indices={'psi': 50})
    # Names the contradiction, and both options, not a bare "bad arguments".
    message = str(exc.value)
    assert 'time' in message
    assert 'index' in message or 'along' in message
