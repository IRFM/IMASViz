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
"""The plotting refusals the agent loop earns, and the one that ends a loop.

The field, on WEST 65782 run 0 (`equilibrium` occurrence 0), where
`profiles_1d.j_tor` holds **no value in any slice** (the `psi` coordinate
and `pressure`, `q`, `elongation` all hold 101 points): the user asked for
`j_tor` as a function of `psi` at four instants, and the loop turned the
ask into a cascade of raw Python errors and then a table it invented.

* `time` is one instant (a number). A `time=[200, 400, 600, 800]` used to
  fall through to `float(time)` and die as `TypeError: float() argument must
  be a string or a real number, not 'list'` -- a data-shaped error the model
  read as a wrong value and retried. It is a schema miss, refused by naming
  the shape that works (one per instant, into the same figure).
* `indices` is a mapping `{"axis": i}`. A `indices=44` used to fall into
  `for key in (indices or {})` and die as `TypeError: 'int' object is not
  iterable`. Same class, same fix: refuse by naming the mapping.
* a display path (`equilibrium/time_slice(0)/profiles_1d/pressure`) is the
  same leaf as the data path (`equilibrium.time_slice[0].profiles_1d.pressure`),
  and `plot_one(mode="single")` always accepted both through the alias.
  `plot_slice` re-parsed the raw string and refused the display spelling as
  "not a leaf of an IDS" -- a spelling miss mistaken for a missing leaf.
* a leaf that holds no values earns a refusal that says so and names the
  filled siblings under the same structure -- not "no values along the
  plotted axis" (a widget phrase the model reads as a wrong axis and retries,
  and then, when it stops, as a table it put together from the filled
  coordinate and invented values).

All pinned on the reference case (WEST 54924 run 0, `equilibrium`
occurrence 0), where `profiles_1d` holds both filled and empty direct
leaves -- so the empty-leaf half does not depend on a specific shot.
"""

import pytest

from mcp_server.core import McpGuiCore

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI,
                      case_uri_or_skip)

IDS_NAME = 'equilibrium'
FILLED = 'equilibrium.time_slice[0].profiles_1d.pressure'
FILLED_DISPLAY = 'equilibrium/time_slice(0)/profiles_1d/pressure'

pytestmark = [pytest.mark.case, pytest.mark.ui]


@pytest.fixture(scope='module')
def core(qapp, tmp_path_factory):
    """One self-contained session: the case open and equilibrium loaded.

    HOME is patched for the module, and every figure this file drew is closed
    before the session goes, so a shown-and-open frame does not outlive it.
    """
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    home = tmp_path_factory.mktemp('plotRefusalHome')
    patch = pytest.MonkeyPatch()
    patch.setenv('HOME', str(home))
    session = McpGuiCore()
    session.open_case(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
    session.load_ids(CASE_URI, IDS_NAME, 0)
    try:
        yield session
    finally:
        for key in list(getattr(session.api, 'figureframes', None) or {}):
            try:
                session.close_window(key)
            except Exception:
                pass
        patch.undo()


def test_time_is_one_instant_not_a_list(core):
    """A `time` that is a list is a schema miss: refused by naming the shape
    that works, not as the `float() ... not 'list'` the model read as a
    wrong value and retried into the turn budget."""
    with pytest.raises(ValueError) as exc:
        core.plot_slice(CASE_URI, FILLED, [200, 400, 600, 800])
    message = str(exc.value)
    assert 'time' in message and 'instant' in message, message
    assert 'into_figure_key' in message, \
        'the refusal must steer to the working multi-instant path: %s' \
        % message
    # And it is the named refusal, not the raw Python error it used to be
    # (the `pytest.raises(ValueError)` above already rules out the TypeError;
    # this rules out its signature).
    assert 'argument must be' not in message, \
        'a raw float() TypeError slipped through: %s' % message


def test_indices_is_a_mapping_not_a_bare_index(core):
    """A `indices` that is a bare index is a schema miss: refused by naming
    the mapping, not as `'int' object is not iterable`."""
    with pytest.raises(ValueError) as exc:
        core.plot_one(CASE_URI, FILLED, along='psi', indices=44)
    message = str(exc.value)
    assert 'indices' in message and 'mapping' in message, message
    assert '44' in message, \
        'the refusal must name the value it got: %s' % message
    assert 'iterable' not in message, \
        'a raw TypeError slipped through: %s' % message


def test_the_display_path_is_the_same_leaf(core):
    """The display spelling (slashes + parentheses) of a filled leaf must
    draw, not be refused as "not a leaf of an IDS" -- the spelling the
    search hit answers is the same leaf the data path names."""
    answer = core.plot_slice(CASE_URI, FILLED_DISPLAY, 400)
    assert answer['drawn'] > 0, \
        'the display path of a filled leaf must draw: %r' % answer
    assert answer['figure'] in core.api.figureframes


def _empty_curve_leaf_with_filled_siblings(core):
    """One empty 1D-profile leaf of `profiles_1d` that has filled siblings,
    or None when the case does not hold that shape."""
    view = core._viewForUri(CASE_URI)
    for node in view.signalsList:
        dataName = node.getDataName() or ''
        if '.profiles_1d.' not in dataName:
            continue
        if '.' in dataName.rsplit('.profiles_1d.', 1)[1]:
            continue  # a structure further down, not a direct profile
        try:
            if node.hasAvailableData():
                continue
        except Exception:
            continue
        if core._leafKind(node) != 'curve':
            continue
        if core._filledSiblings(view, node):
            return node
    return None


def test_an_empty_leaf_names_the_filled_siblings(core):
    """A leaf that holds no values earns a refusal that says so and names the
    filled siblings under the same structure -- not "no values along the
    plotted axis", the phrase that sent the model to read directly and then
    invent the table."""
    node = _empty_curve_leaf_with_filled_siblings(core)
    if node is None:
        pytest.skip('no empty profiles_1d leaf with filled siblings')
    view = core._viewForUri(CASE_URI)
    path = node.getDataName()
    filled = core._filledSiblings(view, node)

    with pytest.raises(ValueError) as exc:
        core.plot_one(CASE_URI, path)
    message = str(exc.value)
    assert 'no values' in message, message
    assert 'not a leaf' not in message, \
        'a spelling or missing-leaf refusal, not the emptiness: %s' % message
    assert any('"%s"' % name in message for name in filled), \
        'the refusal must name a filled sibling: %s' % message


def test_an_empty_read_says_empty_and_names_the_siblings(core):
    """The read twin of the same leaf must say it is empty and name the
    filled siblings too -- this is the path a "read it directly" reaches, and
    it is where the invented table was assembled from the filled coordinate."""
    node = _empty_curve_leaf_with_filled_siblings(core)
    if node is None:
        pytest.skip('no empty profiles_1d leaf with filled siblings')
    view = core._viewForUri(CASE_URI)
    filled = core._filledSiblings(view, node)
    answer = core.get_signal(CASE_URI, node.getDataName())
    assert answer.get('kind') == 'curve' and answer.get('samples') == 0, answer
    note = answer.get('note', '')
    assert 'no values' in note, 'the empty read must say it is empty: %r' % answer
    assert any('"%s"' % name in note for name in filled), \
        'the note must name a filled sibling: %r' % answer
