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

"""A family's member is named by its path, and `indices` is not the way to
pick one.

Measured on the shot the user reported (WEST 54924 run 0, `magnetics`
occurrence 0), the ask was: "trace boucles 2 et 10 (0-based) du signal
`flux_loop` sur la même figure". The tree holds each member as its own leaf --
`magnetics.flux_loop[2].flux.data` and `...[10]...` are two distinct nodes,
each a time curve. The element is therefore the path's identity, not an axis a
figure slides on.

The regression this file fixes: the unified `indices` schema taught the model
to pick the loop with `indices={"flux_loop": N}`. A figure for one family
member holds no slider for that family -- the member is already fixed by the
path -- so the call was refused, and the refusal said "name a different one".
That is false advice: there is no "different one" to name for a single
element; the move is to use the *other member's path*. The model followed the
false advice and retried the same refused call until it hit the turn budget,
and the user was left with a figure that was not loops 2 and 10.

What a test pins here:

    the refusal on a family axis still says why, and it names the working
    move (address the member by its path, or select the members and plot the
    selection) -- it never says "name a different one";
    the working move itself works: the two members, addressed by path, come
    out as two curves on the one figure asked for.

`test_124` is the same doctrine on the other axis shape (`equilibrium` profile
at `psi[50]`); this one is the family shape the user actually hit.
"""

import pytest

from mcp_server.core import McpGuiCore

from conftest import CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip

IDS_NAME = 'magnetics'
LOOP2 = 'magnetics.flux_loop[2].flux.data'
LOOP10 = 'magnetics.flux_loop[10].flux.data'

pytestmark = [pytest.mark.case, pytest.mark.ui]


@pytest.fixture(scope='module')
def core(qapp, tmp_path_factory):
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    home = tmp_path_factory.mktemp('fluxLoopCoreHome')
    patch = pytest.MonkeyPatch()
    patch.setenv('HOME', str(home))
    session = McpGuiCore()
    try:
        session.open_case(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
        session.load_ids(CASE_URI, IDS_NAME, 0)
        yield session, home
    finally:
        patch.undo()


def test_an_indices_pick_on_a_family_member_is_refused_and_pointed_right(core):
    """`{"flux_loop": N}` on a family member is not a slider there is to move:
    the member is already the path. The refusal keeps saying why, and it names
    the move that works -- the path / the selection -- instead of "name a
    different one", which pushed the model to retry itself.
    """
    session, _home = core
    with pytest.raises(ValueError) as exc:
        session.plot_one(CASE_URI, LOOP2, indices={'flux_loop': 2})
    message = str(exc.value)
    assert 'flux_loop' in message, message
    # The false advice is gone: there is no "different one" to name for a
    # single element of the family.
    assert 'a different one' not in message, message
    # And the refusal points the model at the working move: the member's own
    # path, or a selection of the members.
    assert 'path' in message, 'the refusal must name the path as the move'
    assert ('into_figure_key' in message
            or 'plot_selection' in message or 'select' in message), message


def test_two_members_addressed_by_path_are_two_curves_on_one_figure(core):
    """The ask itself, done the way the tree holds it: loop 2 and loop 10,
    each by its own path, on the one figure. That is what "trace boucles 2 et
    10 sur la même figure" means, and it has to come out as two curves.
    """
    session, _home = core
    first = session.plot_one(CASE_URI, LOOP2, along_time=True)
    second = session.plot_one(CASE_URI, LOOP10, along_time=True,
                              into_figure_key=first['figure'])
    assert first['figure'] == second['figure'], (first, second)
    frame = session.api.figureframes[first['figure']]
    assert frame.isDrawing(), 'the two members should draw'
    assert frame.curveCount() == 2, 'loop 2 and loop 10 are two curves'


def test_the_selection_of_two_members_draws_two_curves(core):
    """The other working move: select the two members and plot the selection.
    The selection holds exactly those members, and the figure holds two curves.
    """
    session, _home = core
    selection = session.select_signals(CASE_URI, [LOOP2, LOOP10])
    assert selection['selection_size'] == 2
    answer = session.plot_selection(CASE_URI)
    frame = session.api.figureframes[answer['figures'][0]]
    assert frame.isDrawing()
    assert frame.curveCount() == 2
