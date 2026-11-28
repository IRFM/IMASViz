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
"""The `slices` mode of `plot`: one ask, one window, one trace per instant.

The field, on WEST 64782, was « Trace j_tor en fonction de psi pour
t=100, t=400, t=700 sur la meme figure »: the model had to make one call
per instant, each opening a window of its own (or overdrawing the name
of the trace before), and every refusal was a separate call that burned
the turn budget. The mode this file pins is the one shape that asks for
the whole thing once:

* one call, one window of curves, one trace per instant, named for the
  slice it shows -- not N windows, not one window with N overwritten
  names;
* a leaf that holds no values answers ONE aggregate refusal, before any
  window is opened, naming the instants asked and the filled siblings
  under the same structure -- not one refusal per instant;
* the abscissa is the leaf's own coordinate (psi for a profiles_1d
  leaf), not the clock and not a normalized rho_tor.

All pinned on the reference case (WEST 54924 run 0, `equilibrium`
occurrence 0), where the filled `profiles_1d.pressure` leaf draws.
"""

import pytest

from mcp_server.core import McpGuiCore

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI,
                      case_uri_or_skip)

IDS_NAME = 'equilibrium'
FILLED = 'equilibrium.time_slice[0].profiles_1d.pressure'

pytestmark = [pytest.mark.case, pytest.mark.ui]


@pytest.fixture(scope='module')
def core(qapp, tmp_path_factory):
    """One self-contained session: the case open and equilibrium loaded.

    HOME is patched for the module, and every figure this file drew is
    closed before the session goes, so a shown-and-open frame does not
    outlive it.
    """
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    home = tmp_path_factory.mktemp('slicesHome')
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


def _filled_node(core):
    """The filled leaf's tree node, looked up by data path."""
    view = core._viewForUri(CASE_URI)
    for candidate in view.signalsList:
        if (candidate.getDataName() or '') == FILLED:
            return candidate
    return None


def test_one_call_one_window_one_trace_per_instant(core):
    """A list of instants is one call and one window: one trace per
    instant, each named for the slice it shows."""
    node = _filled_node(core)
    if node is None:
        pytest.skip('the filled leaf is not in the tree: %r' % FILLED)
    view = core._viewForUri(CASE_URI)
    tbase = core._timeBase(view, node)
    if tbase is None or tbase.size < 3:
        pytest.skip('no time base on the filled leaf')
    instants = [float(tbase[0]), float(tbase[tbase.size // 2]),
                float(tbase[-1])]
    answer = core.plot_slices(CASE_URI, FILLED, instants)
    assert answer['figure'] in core.api.figureframes, answer
    assert answer['kind'] == 'QVizCurvePlot', answer
    assert len(answer['traces']) == 3, answer
    requests = [entry.get('time_requested') for entry in answer['traces']]
    assert requests == instants, requests
    drawn_traces = [entry for entry in answer['traces']
                    if 'error' not in entry]
    assert len(drawn_traces) == 3, answer['traces']
    for entry in drawn_traces:
        assert entry['samples'] > 0, entry
        assert entry['time_slice_time'] is not None, entry
        assert entry['trace'].endswith('t=%g s' % entry['time_slice_time']), entry
    frame = core.api.figureframes[answer['figure']]
    items = frame.pgPlotWidget.getPlotItem().listDataItems()
    assert len(items) == 3, 'one trace per instant: %r' % items
    names = [item.name() for item in items]
    assert len(set(names)) == 3, 'traces must be named apart: %r' % names
    assert all(' t=' in name for name in names), names
    assert answer['drawn'] == sum(entry['samples'] for entry in drawn_traces)


def test_an_instant_outside_the_range_is_clamped_and_named(core):
    """An instant past the case's range is read at the case's own edge:
    the entry says the instant was clamped, and the trace still draws."""
    import numpy as np

    view = core._viewForUri(CASE_URI)
    node = None
    for candidate in view.signalsList:
        if (candidate.getDataName() or '') == FILLED:
            node = candidate
            break
    if node is None:
        pytest.skip('the filled leaf is not in the tree: %r' % FILLED)
    tbase = core._timeBase(view, node)
    if tbase is None or tbase.size == 0:
        pytest.skip('no time base on the filled leaf')
    requested = float(tbase[-1]) + 1000.0
    answer = core.plot_slices(CASE_URI, FILLED, [requested])
    entry = answer['traces'][0]
    assert entry['clamped'] is True, entry
    assert 'error' not in entry, entry
    assert entry['samples'] > 0, entry
    assert abs(entry['time_slice_time'] - float(tbase[-1])) <= 1.0, entry


def test_times_is_refused_by_naming_the_list_shape(core):
    """A `times` that is not a list is a schema miss: refused by naming the
    shape that works, not as a Python error."""
    with pytest.raises(ValueError) as exc:
        core.plot_slices(CASE_URI, FILLED, 'not a list')
    message = str(exc.value)
    assert 'times' in message and 'instants' in message, message
    with pytest.raises(ValueError) as exc:
        core.plot_slices(CASE_URI, FILLED, [])
    assert 'empty' in str(exc.value), str(exc.value)


def test_a_list_is_refused_for_the_singular_word_too(core):
    """The singular `time` (plot(mode="slice")) refuses a list by pointing
    at the slices mode -- the same steering from both sides."""
    with pytest.raises(ValueError) as exc:
        core.plot_slice(CASE_URI, FILLED, [100, 400, 700])
    message = str(exc.value)
    assert 'slices' in message and 'times' in message, message


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


def test_an_empty_leaf_earns_one_aggregate_refusal(core):
    """A leaf that holds no values answers ONE refusal, before any window
    opens, naming the instants asked and the filled siblings under the
    same structure -- not one refusal per instant, and not a raw error."""
    node = _empty_curve_leaf_with_filled_siblings(core)
    if node is None:
        pytest.skip('no empty profiles_1d leaf with filled siblings')
    view = core._viewForUri(CASE_URI)
    path = node.getDataName()
    filled = core._filledSiblings(view, node)

    with pytest.raises(ValueError) as exc:
        core.plot_slices(CASE_URI, path, [100, 400, 700])
    message = str(exc.value)
    assert 'no values' in message, message
    assert 't=100' in message and 't=400' in message and 't=700' in message, \
        'the refusal must name the instants asked: %s' % message
    assert any('"%s"' % name in message for name in filled), \
        'the refusal must name a filled sibling: %s' % message
    # One refusal: one raise, no per-instant retry -- the caller sees one
    # answer, not a cascade.
    assert message.count('plot_slices') == 1, \
        'one refusal, not a cascade: %s' % message


def _rgbOf(curve):
    """The colour a trace is drawn with, whether its pen is a QPen or a tuple."""
    pen = curve.opts['pen']
    return pen if isinstance(pen, tuple) else pen.color().getRgb()[:3]


def test_slices_traces_are_drawn_with_different_pens(core):
    """One profile at several instants draws one colour per slice, the
    same house palette the frame itself uses -- the ground is the black
    every figure paints, so a default grey trace is a trace nobody can
    tell from its neighbours."""
    node = _filled_node(core)
    if node is None:
        pytest.skip('the filled leaf is not in the tree: %r' % FILLED)
    view = core._viewForUri(CASE_URI)
    tbase = core._timeBase(view, node)
    if tbase is None or tbase.size < 3:
        pytest.skip('no time base on the filled leaf')
    instants = [float(tbase[0]), float(tbase[tbase.size // 2]),
                float(tbase[-1])]
    answer = core.plot_slices(CASE_URI, FILLED, instants)
    frame = core.api.figureframes[answer['figure']]
    items = frame.pgPlotWidget.getPlotItem().listDataItems()
    assert len(items) == 3, items
    pens = [_rgbOf(item) for item in items]
    assert len(set(pens)) == 3, \
        'one colour per slice: %r' % pens
    assert all(pen != (200, 200, 200) for pen in pens), \
        'a slice must not wear the default grey: %r' % pens


def test_a_slice_drawn_on_its_own_figure_wears_a_house_pen(core):
    """The singular mode draws one trace, and that trace wears the palette's
    first colour on a fresh figure -- not the default grey a pen-less plot
    falls back to."""
    node = _filled_node(core)
    if node is None:
        pytest.skip('the filled leaf is not in the tree: %r' % FILLED)
    view = core._viewForUri(CASE_URI)
    tbase = core._timeBase(view, node)
    if tbase is None or tbase.size == 0:
        pytest.skip('no time base on the filled leaf')
    answer = core.plot_slice(CASE_URI, FILLED, float(tbase[0]))
    frame = core.api.figureframes[answer['figure']]
    items = frame.pgPlotWidget.getPlotItem().listDataItems()
    assert len(items) == 1, items
    pen = _rgbOf(items[0])
    assert pen != (200, 200, 200), 'a slice trace wears the house palette: %r' % (pen,)
