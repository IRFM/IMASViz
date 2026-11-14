# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The ten figure-manipulation methods, driven end to end on the reference case.

What each of the ten methods does and how it refuses, pinned off the
reference case by driving `McpGuiCore` the way the suite does everything
else: offscreen, through the application's own commands and the
application's own bookkeeping.

The figure is a `QVizCurvePlot` of WEST 54924 run 0, occurrence 0,
holding two curves:

    equilibrium.time  (x = 0..48, y = 32..48 -- all positive)
    equilibrium.time_slice[0].global_quantities.ip
                      (x = 0..48, y = -77009  -- all negative, constant)

That mix of a positive and a negative curve, and an abscissa that starts
at zero, is what makes every named refusal of the axis methods deterministic:
scale, shift, normalize -- and the log-axis refusal that names the count
of non-positive samples. The success path of `set_log_scale` is tested
after the negative curve is cleared with `shift_curve`, which the refusal
message names as the remedy.

`export_curve` writes into `~/.imasviz/exports`, the guard is the same
shape the configurations use -- a `name` that is a place (contains `/`)
is refused by name. `remove_curve` is destructive and runs last on the
curve figure.

The tests run in the order written against one module-scoped core, the
same rule `test_45` states for its journey.
"""

import os

import pytest

from mcp_server.core import McpGuiCore

from conftest import CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip

IDS_NAME = 'equilibrium'
TIME_PATH = 'equilibrium.time'
IP_PATH = 'equilibrium.time_slice[0].global_quantities.ip'

TIME_Y_MIN = 32.13   # measured on WEST 54924, DD 3.35.0, 49 samples
TIME_Y_MAX = 48.55
IP_Y = -77009.3      # constant negative value, all 49 samples

pytestmark = [pytest.mark.case, pytest.mark.ui]


# ==================================================================== fixtures


@pytest.fixture(scope='module')
def core(qapp, tmp_path_factory):
    """One McpGuiCore session with $HOME patched for the module.

    Same pattern as test_100's module-scoped core: HOME is patched so
    the exports folder is isolated and does not overwrite the real
    ``~/.imasviz``.
    """
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    home = tmp_path_factory.mktemp('manipHome')
    patch = pytest.MonkeyPatch()
    patch.setenv('HOME', str(home))
    session = McpGuiCore()
    try:
        yield (session, home)
    finally:
        patch.undo()


@pytest.fixture(scope='module')
def curve_figure(core):
    """The curve figure the module works on, set up once.

    Returns (session, home, figure_key, frame).
    """
    session, home = core
    session.open_case(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
    session.load_ids(CASE_URI, IDS_NAME, 0)
    session.select_signals(CASE_URI, [TIME_PATH, IP_PATH])
    figures = session.plot_selection(CASE_URI)['figures']
    assert figures, 'the selection of time + ip drew no figure'
    key = figures[0]
    frame = session.api.figureframes[key]
    return session, home, key, frame


def _xrange(vb):
    return [float(v) for v in vb.state['viewRange'][0]]


def _yrange(vb):
    return [float(v) for v in vb.state['viewRange'][1]]


def _logmode(vb):
    lm = vb.state.get('logMode') or [None, None]
    return [bool(v) for v in lm]


# ==================================================================== setup


def test_figure_is_a_curve_plot_with_two_curves(curve_figure):
    session, _home, key, frame = curve_figure
    from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
    assert isinstance(frame, QVizCurvePlot)
    assert frame.curveCount() == 2, 'expected 2 curves (time + ip), got %d' % frame.curveCount()
    assert key.startswith('Plot'), key


# ==================================================================== stats


def test_curve_stats_answers_both_curves(curve_figure):
    session, _h, key, frame = curve_figure
    answer = session.curve_stats(key)
    assert answer['count'] == 2
    assert len(answer['curves']) == 2
    byname = {c['name']: c for c in answer['curves']}
    assert any('time' in n for n in byname), byname
    assert any('ip' in n for n in byname), byname
    # every curve must carry the minimum set of fields
    for c in answer['curves']:
        assert c['n'] == 49, c
        assert c['min'] is not None
        assert c['max'] is not None
        assert c['mean'] is not None
        assert c['peak_value'] is not None
        assert c['peak_at'] is not None
        assert 'rank' in c


def test_curve_stats_single_curve_by_index(curve_figure):
    session, _h, key, frame = curve_figure
    answer = session.curve_stats(key, curve=0)
    assert answer['count'] == 1
    assert answer['curves'][0]['rank'] == 0
    assert 'time' in answer['curves'][0]['name'].lower()


def test_curve_stats_single_curve_by_name(curve_figure):
    session, _h, key, frame = curve_figure
    # 'ip' is a substring of the ip path
    answer = session.curve_stats(key, curve='ip')
    assert answer['count'] == 1
    assert 'ip' in answer['curves'][0]['name'].lower()


def test_curve_stats_refuses_a_bool(curve_figure):
    session, _h, key, _frame = curve_figure
    with pytest.raises(ValueError, match='true/false answer'):
        session.curve_stats(key, curve=True)


def test_curve_stats_refuses_an_out_of_range_index(curve_figure):
    session, _h, key, frame = curve_figure
    with pytest.raises(ValueError) as exc:
        session.curve_stats(key, curve=5)
    msg = str(exc.value)
    assert 'curve=5' in msg, msg
    assert 'out of range' in msg, msg
    assert '5 to 1' in msg or 'holds 2' in msg, 'must name the count: %s' % msg


def test_curve_stats_refuses_an_unknown_name(curve_figure):
    session, _h, key, _frame = curve_figure
    with pytest.raises(ValueError) as exc:
        session.curve_stats(key, curve='zzz_no_such_curv')
    msg = str(exc.value)
    assert 'No curve of' in msg or 'zzz_no_such_curv' in msg, msg
    # the refusal names the real curves
    assert 'time' in msg or 'ip' in msg, 'refusal should name the curves: %s' % msg


# ==================================================================== scale


def test_scale_curve_applies_the_factor(curve_figure):
    session, _h, key, frame = curve_figure
    # first, note the starting value
    start_answer = session.curve_stats(key, curve=0)
    start_y_max = start_answer['curves'][0]['max']

    answer = session.scale_curve(key, 2.0, curve=0)
    assert answer['factor'] == 2.0
    assert 'time' in answer['curves'][0] or 'time' in key

    # verify the curve actually doubled
    verify = session.curve_stats(key, curve=0)
    assert abs(verify['curves'][0]['max'] - start_y_max * 2.0) < 1e-6

    # restore, so the figure is clean for the tests that follow
    session.reset_curve(key, curve=0)
    restored = session.curve_stats(key, curve=0)
    assert abs(restored['curves'][0]['max'] - start_y_max) < 1e-6


def test_scale_curve_refuses_a_bool(curve_figure):
    session, _h, key, _frame = curve_figure
    with pytest.raises(ValueError, match='factor'):
        session.scale_curve(key, True)


def test_scale_curve_refuses_a_non_number(curve_figure):
    session, _h, key, _frame = curve_figure
    with pytest.raises(ValueError, match='finite number'):
        session.scale_curve(key, 'two')


def test_scale_curve_and_reset_restores_original(curve_figure):
    session, _h, key, _frame = curve_figure
    before = session.curve_stats(key, curve=0)
    before_max = before['curves'][0]['max']

    session.scale_curve(key, 10.0, curve=0)
    mid = session.curve_stats(key, curve=0)
    assert abs(mid['curves'][0]['max'] - before_max * 10.0) < 1e-6

    reset = session.reset_curve(key, curve=0)
    assert reset['restored'], 'reset_curve said nothing was restored'

    after = session.curve_stats(key, curve=0)
    assert abs(after['curves'][0]['max'] - before_max) < 1e-6, \
        'reset_curve did not restore the original value'


# ==================================================================== shift


def test_shift_curve_adds_the_offset(curve_figure):
    session, _h, key, _frame = curve_figure
    before = session.curve_stats(key, curve=1)   # the ip curve
    before_max = before['curves'][0]['max']

    answer = session.shift_curve(key, 100.0, curve=1)
    assert answer['offset'] == 100.0

    verify = session.curve_stats(key, curve=1)
    assert abs(verify['curves'][0]['max'] - (before_max + 100.0)) < 1e-6

    # restore, so the figure is clean for the tests that follow
    session.reset_curve(key, curve=1)
    restored = session.curve_stats(key, curve=1)
    assert abs(restored['curves'][0]['max'] - before_max) < 1e-6


def test_shift_curve_refuses_a_non_number(curve_figure):
    session, _h, key, _frame = curve_figure
    with pytest.raises(ValueError, match='finite number'):
        session.shift_curve(key, 'ten')


def test_shift_curve_and_reset_restores_original(curve_figure):
    session, _h, key, _frame = curve_figure
    before = session.curve_stats(key, curve=1)
    before_max = before['curves'][0]['max']

    session.shift_curve(key, 500.0, curve=1)
    session.reset_curve(key, curve=1)
    after = session.curve_stats(key, curve=1)
    assert abs(after['curves'][0]['max'] - before_max) < 1e-6, \
        'reset_curve did not restore after shift'


# ==================================================================== normalize


def test_normalize_curve_max_mode(curve_figure):
    session, _h, key, _frame = curve_figure
    before = session.curve_stats(key, curve=0)
    before_max = before['curves'][0]['max']

    answer = session.normalize_curve(key, mode='max', curve=0)
    assert answer['mode'] == 'max'
    assert abs(answer['reference'] - before_max) < 1e-9

    verify = session.curve_stats(key, curve=0)
    # after normalizing by max, the max should be 1.0
    assert abs(verify['curves'][0]['max'] - 1.0) < 1e-9

    session.reset_curve(key, curve=0)


def test_normalize_curve_first_mode(curve_figure):
    session, _h, key, _frame = curve_figure
    before = session.curve_stats(key, curve=0)
    before_min = before['curves'][0]['min']   # the first sample is the min for time

    answer = session.normalize_curve(key, mode='first', curve=0)
    assert answer['mode'] == 'first'

    verify = session.curve_stats(key, curve=0)
    # after normalizing by first, the first sample should be 1.0 (min here)
    assert abs(verify['curves'][0]['min'] - 1.0) < 1e-9

    session.reset_curve(key, curve=0)


def test_normalize_curve_mean_mode(curve_figure):
    session, _h, key, _frame = curve_figure
    before = session.curve_stats(key, curve=0)
    before_mean = before['curves'][0]['mean']

    answer = session.normalize_curve(key, mode='mean', curve=0)
    assert answer['mode'] == 'mean'
    assert abs(answer['reference'] - before_mean) < 1e-9

    verify = session.curve_stats(key, curve=0)
    assert abs(verify['curves'][0]['mean'] - 1.0) < 1e-9

    session.reset_curve(key, curve=0)


def test_normalize_curve_refuses_an_unknown_mode(curve_figure):
    session, _h, key, _frame = curve_figure
    with pytest.raises(ValueError, match='max, first, or mean'):
        session.normalize_curve(key, mode='banana')


def test_normalize_curve_refuses_a_zero_reference(curve_figure):
    session, _h, key, _frame = curve_figure
    # first zero out curve 1 (scale by 0 -- finite, allowed)
    session.scale_curve(key, 0, curve=1)
    try:
        with pytest.raises(ValueError) as exc:
            session.normalize_curve(key, mode='first', curve=1)
        msg = str(exc.value)
        assert 'zero' in msg or 'undefined' in msg, \
            'refusal should say the reference is zero: %s' % msg
    finally:
        session.reset_curve(key, curve=1)


# ==================================================================== axis range


def test_set_axis_range_pins_x(curve_figure):
    session, _h, key, frame = curve_figure
    vb = frame.pgPlotWidget.getViewBox()

    answer = session.set_axis_range(key, xmin=0, xmax=10)
    assert answer['pinned'] is True
    assert 'xRange' in answer
    # after pinning, autoRange for x should be off
    assert vb.state['autoRange'][0] == 0, 'autoRange x should be disabled'
    # the x range should contain 0..10 (pyqtgraph adds default padding around
    # the requested range)
    xr = _xrange(vb)
    assert xr[0] <= 0, 'visible x should not start after the pinned 0: %s' % xr
    assert xr[1] >= 10, 'visible x should not end before the pinned 10: %s' % xr
    # restore
    session.set_axis_range(key, auto=True)


def test_set_axis_range_pins_y(curve_figure):
    session, _h, key, frame = curve_figure
    vb = frame.pgPlotWidget.getViewBox()

    answer = session.set_axis_range(key, ymin=0, ymax=100)
    assert answer['pinned'] is True
    assert 'yRange' in answer
    assert vb.state['autoRange'][1] == 0, 'autoRange y should be disabled'
    session.set_axis_range(key, auto=True)


def test_set_axis_range_auto_restores_autorange(curve_figure):
    session, _h, key, frame = curve_figure
    vb = frame.pgPlotWidget.getViewBox()

    session.set_axis_range(key, xmin=0, xmax=1)
    session.set_axis_range(key, ymin=0, ymax=1)
    assert vb.state['autoRange'][0] == 0

    answer = session.set_axis_range(key, auto=True)
    assert answer['auto'] is True
    assert vb.state['autoRange'][0] == 1, 'autoRange x should be restored'
    assert vb.state['autoRange'][1] == 1, 'autoRange y should be restored'


def test_set_axis_range_refuses_a_half_pair(curve_figure):
    session, _h, key, _frame = curve_figure
    with pytest.raises(ValueError, match='together'):
        session.set_axis_range(key, xmin=0)


def test_set_axis_range_refuses_an_inverted_range(curve_figure):
    session, _h, key, _frame = curve_figure
    with pytest.raises(ValueError, match='inverted'):
        session.set_axis_range(key, xmin=10, xmax=0)


def test_set_axis_range_refuses_auto_and_bounds_together(curve_figure):
    session, _h, key, _frame = curve_figure
    with pytest.raises(ValueError, match='not a bound'):
        session.set_axis_range(key, auto=True, xmin=0, xmax=1)


def test_set_axis_range_refuses_no_axis(curve_figure):
    session, _h, key, _frame = curve_figure
    with pytest.raises(ValueError, match='at least one axis'):
        session.set_axis_range(key)


def test_set_axis_range_refuses_a_bool_bound(curve_figure):
    session, _h, key, _frame = curve_figure
    with pytest.raises(ValueError, match='finite number'):
        session.set_axis_range(key, xmin=True, xmax=10)


# ==================================================================== log scale


def test_set_log_scale_refuses_y_axis_when_values_are_negative(curve_figure):
    """The ip curve is fully negative -- turning the y axis to log is
    undefined over it, so the refusal names the count of non-positive
    samples and points at shift_curve as the remedy."""
    session, _h, key, _frame = curve_figure
    with pytest.raises(ValueError) as exc:
        session.set_log_scale(key, y=True)
    msg = str(exc.value)
    assert 'negative' in msg or 'zero or negative' in msg, \
        'refusal should say the axis is undefined: %s' % msg
    assert 'shift_curve' in msg, \
        'refusal should name shift_curve as the remedy: %s' % msg


def test_set_log_scale_refuses_x_axis_when_zero_is_present(curve_figure):
    """The abscissa contains zero -- a log x axis is undefined at zero."""
    session, _h, key, _frame = curve_figure
    with pytest.raises(ValueError) as exc:
        session.set_log_scale(key, x=True)
    msg = str(exc.value)
    assert 'zero or negative' in msg or 'negative' in msg, msg


def test_set_log_scale_refuses_no_axis_named(curve_figure):
    session, _h, key, _frame = curve_figure
    with pytest.raises(ValueError, match='An axis is named'):
        session.set_log_scale(key)


def test_set_log_scale_refuses_a_non_bool(curve_figure):
    session, _h, key, _frame = curve_figure
    with pytest.raises(ValueError, match='log'):
        session.set_log_scale(key, x='yes')


def test_set_log_scale_success_after_clearing_negative_values(curve_figure):
    """After shifting the fully negative curve positive, y=True should land;
    the state should reflect x=False, y=True, and then y=False restores it."""
    session, _h, key, frame = curve_figure
    vb = frame.pgPlotWidget.getViewBox()

    # Clear the negative values: shift ip (curve 1) up by 80000
    # (-77009 + 80000 = 2991, all positive), time (curve 0) was already positive
    session.shift_curve(key, 80000.0, curve=1)

    try:
        answer = session.set_log_scale(key, y=True)
        assert answer['y'] is True, 'answer should report y log is on'
        assert _logmode(vb)[1] is True, 'vb.state logMode[1] should be True'
        assert _logmode(vb)[0] is False, 'x log should stay off'

        session.set_log_scale(key, y=False)
        assert _logmode(vb)[1] is False, 'vb.state logMode[1] should be False after y=False'
    finally:
        session.reset_curve(key)  # restore the shift


# ==================================================================== invert


def test_invert_axis_toggles_x(curve_figure):
    session, _h, key, frame = curve_figure
    vb = frame.pgPlotWidget.getViewBox()

    answer = session.invert_axis(key, x=True)
    assert answer['xInverted'] is True
    assert vb.state.get('xInverted') is True

    answer = session.invert_axis(key, x=False)
    assert answer['xInverted'] is False
    assert vb.state.get('xInverted') is False


def test_invert_axis_toggles_y(curve_figure):
    session, _h, key, frame = curve_figure
    vb = frame.pgPlotWidget.getViewBox()

    answer = session.invert_axis(key, y=True)
    assert answer['yInverted'] is True
    assert vb.state.get('yInverted') is True

    answer = session.invert_axis(key, y=False)
    assert answer['yInverted'] is False
    assert vb.state.get('yInverted') is False


def test_invert_axis_refuses_no_axis_named(curve_figure):
    session, _h, key, _frame = curve_figure
    with pytest.raises(ValueError, match='An axis is named'):
        session.invert_axis(key)


def test_invert_axis_refuses_a_non_bool(curve_figure):
    session, _h, key, _frame = curve_figure
    with pytest.raises(ValueError, match='put back'):
        session.invert_axis(key, x='no')


# ==================================================================== export


def test_export_curve_csv_writes_the_file(curve_figure):
    session, home, key, _frame = curve_figure
    answer = session.export_curve(key)
    assert answer['curves'] == 2
    assert os.path.exists(answer['saved_to']), answer['saved_to']
    assert '.imasviz' in answer['saved_to'], answer['saved_to']
    assert answer['saved_to'].endswith('.csv'), answer['saved_to']
    # the file must have content
    with open(answer['saved_to']) as f:
        content = f.read()
    assert '# ' in content, 'the CSV should have a header comment line'
    assert len(content) > 50


def test_export_curve_json_writes_the_file(curve_figure):
    session, _h, key, _frame = curve_figure
    answer = session.export_curve(key, format='json', name='mcp_test_json')
    assert answer['curves'] == 2
    assert answer['saved_to'].endswith('.json'), answer['saved_to']
    assert os.path.exists(answer['saved_to'])
    import json
    with open(answer['saved_to']) as f:
        data = json.load(f)
    assert data['window'] == key
    assert len(data['curves']) == 2
    for c in data['curves']:
        assert len(c['x']) == 49
        assert len(c['y']) == 49


def test_export_curve_single_curve_by_index(curve_figure):
    session, _h, key, _frame = curve_figure
    answer = session.export_curve(key, curve=0)
    assert answer['curves'] == 1
    assert answer['saved_to'].endswith('.csv')
    # the file content should be for one curve only
    with open(answer['saved_to']) as f:
        content = f.read()
    # at least 49 data lines + 1 header line = 50
    lines = [ln for ln in content.splitlines() if not ln.startswith('#')]
    assert len(lines) == 49, 'expected 49 data lines, got %d' % len(lines)


def test_export_curve_refuses_an_unknown_format(curve_figure):
    session, _h, key, _frame = curve_figure
    with pytest.raises(ValueError, match='xml'):
        session.export_curve(key, format='xml')


def test_export_curve_refuses_a_name_that_is_a_place(curve_figure):
    session, _h, key, _frame = curve_figure
    with pytest.raises(ValueError, match='not a file name'):
        session.export_curve(key, name='../etc/passwd')
    # the path-traversal guard should also catch os.sep
    with pytest.raises(ValueError, match='not a file name'):
        session.export_curve(key, name='sub/dir')


# ==================================================================== non-curve window refusals


def test_set_axis_range_refuses_a_table_figure(curve_figure):
    """A Table Plot View draws its own panel per quantity, none of which is
    a single figure a `getViewBox()` addresses -- the refusal is the
    `_viewBoxOf` shape, naming what the window does instead."""
    session, _h, _key, _frame = curve_figure
    session.unselect_all(CASE_URI)
    session.select_signals(CASE_URI, [IP_PATH])
    table_key = session.plot_table(CASE_URI, [IP_PATH])['figure']
    assert 'TablePlotView' in table_key or table_key.startswith('Table'), \
        'expected a table figure, got %r' % table_key
    with pytest.raises(ValueError) as exc:
        session.set_axis_range(table_key, xmin=0, xmax=1)
    msg = str(exc.value)
    assert 'no single figure' in msg or 'curve figure' in msg, \
        'refusal should say the window draws no single figure: %s' % msg


def test_set_log_scale_refuses_a_table_figure(curve_figure):
    session, _h, _key, _frame = curve_figure
    session.unselect_all(CASE_URI)
    session.select_signals(CASE_URI, [IP_PATH])
    table_key = session.plot_table(CASE_URI, [IP_PATH])['figure']
    with pytest.raises(ValueError) as exc:
        session.set_log_scale(table_key, y=True)
    msg = str(exc.value)
    assert 'no single figure' in msg or 'curve figure' in msg, \
        'refusal should say the window draws no single figure: %s' % msg


def test_remove_curve_refuses_a_table_figure(curve_figure):
    """A Table Plot View does not have `removeCurve` -- the refusal is
    the `hasattr(frame, 'removeCurve')` branch, naming the window kind."""
    session, _h, _key, _frame = curve_figure
    session.unselect_all(CASE_URI)
    session.select_signals(CASE_URI, [IP_PATH])
    table_key = session.plot_table(CASE_URI, [IP_PATH])['figure']
    with pytest.raises(ValueError) as exc:
        session.remove_curve(table_key)
    msg = str(exc.value)
    assert 'not a single figure' in msg or 'TablePlotView' in msg or 'table' in msg.lower(), \
        'refusal should name the kind: %s' % msg


# ==================================================================== export refusal on empty


def test_export_curve_refuses_when_a_curve_has_no_value(curve_figure):
    """A figure that holds no curve is refused by name: the refusal that
    `curve_stats` and the scale/shift family share, the one that names the
    window rather than a curve it does not hold.

    A fresh figure is used for the same reason the remove tests use one: the
    no-MDI embed keeps only the newest window, so an earlier figure is not
    guaranteed to outlive a later plot.
    """
    session, _h, _key, _frame = curve_figure
    key, _frame2 = _fresh_curve(session)
    session.remove_curve(key)
    # now the figure holds no curve at all; any curve-family gesture refuses
    # by the same shape, naming the window it was asked of
    with pytest.raises(ValueError) as exc:
        session.export_curve(key)
    msg = str(exc.value)
    assert 'no curve' in msg.lower() or 'no value' in msg or 'empty' in msg, \
        'refusal should say the curve holds no value: %s' % msg


# ==================================================================== remove


def _fresh_curve(session):
    """A newly plotted curve figure holding exactly the two reference curves.

    `plot_selection` is destructive-free for the selection (it draws), but the
    figure it returns is a fresh one each call, and `remove_curve` is
    destructive on whatever figure it is asked of -- so each of the remove
    tests works on its own figure rather than the module's, and the module
    figure keeps its two curves for any test that reads it by reference later.
    """
    session.unselect_all(CASE_URI)
    session.select_signals(CASE_URI, [TIME_PATH, IP_PATH])
    key = session.plot_selection(CASE_URI)['figures'][0]
    frame = session.api.figureframes[key]
    assert frame.curveCount() == 2, 'fresh figure held %d curves' % frame.curveCount()
    return key, frame


def test_remove_curve_one_indexed(curve_figure):
    session, _h, _key, _frame = curve_figure
    key, frame = _fresh_curve(session)

    answer = session.remove_curve(key, curve=1)
    assert answer['curves_left'] == 1
    assert frame.curveCount() == 1

    # the time curve (index 0) should still be there
    stats = session.curve_stats(key)
    assert stats['count'] == 1
    assert 'time' in stats['curves'][0]['name'].lower()


def test_remove_curve_by_name(curve_figure):
    session, _h, _key, _frame = curve_figure
    key, frame = _fresh_curve(session)

    answer = session.remove_curve(key, curve='ip')
    assert answer['curves_left'] == 1
    assert frame.curveCount() == 1
    # remaining curve should be the time one
    stats = session.curve_stats(key)
    assert 'time' in stats['curves'][0]['name'].lower()


def test_remove_curve_refuses_an_unknown_name(curve_figure):
    session, _h, _key, _frame = curve_figure
    key, _frame2 = _fresh_curve(session)
    with pytest.raises(ValueError, match='No curve of'):
        session.remove_curve(key, curve='zzz_no_such')


def test_remove_curve_all(curve_figure):
    session, _h, _key, _frame = curve_figure
    key, frame = _fresh_curve(session)

    answer = session.remove_curve(key)
    assert answer['curves_left'] == 0, 'remove_curve(all) should leave 0 curves'
    assert frame.curveCount() == 0


def test_remove_curve_refuses_an_out_of_range_index(curve_figure):
    session, _h, _key, _frame = curve_figure
    key, _frame2 = _fresh_curve(session)
    with pytest.raises(ValueError) as exc:
        session.remove_curve(key, curve=7)
    msg = str(exc.value)
    assert 'out of range' in msg or 'not on' in msg, msg
    assert 'holds 2' in msg, 'refusal should name the count: %s' % msg
