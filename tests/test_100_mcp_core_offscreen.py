# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""`McpGuiCore`, end to end, on the reference case, without the MCP SDK.

This file drives the layer the agent drives, the way the suite drives
everything else: offscreen, on the real case, through the application's own
commands. What it pins, in absolute numbers (WEST 54924 run 0, data
dictionary 3.35.0, the same numbers the journey in `test_45` measured):

* the case comes open with `equilibrium` holding `[0, 1, 2, 3]`, asked of
  the case and not listed from a file;
* loading occurrence 0 keeps 3368 signals for the tree, as the journey
  measured;
* the selection of `equilibrium.time` and two global quantities plots into
  a curve figure of the `SlicesPlot` namespace, and the case's log panel
  carries a line after each gesture;
* the read answers 49 samples for `equilibrium.time` along time, the number
  the coordinate tests of the suite pin for that clock;
* a refused path is refused by name, and does not touch the selection;
* the Profiles entry of `equilibrium` runs with the occurrence handed as an
  answer, and a window the plugin drew appears in the window bookkeeping;
* the session written by `save_session` comes back by `restore_session`, the
  case reported open;
* the export writes a `master.h5` the target can be opened on.

The tests run in the order written against one module-scoped core, the same
rule the journey in `test_45` states for itself.
"""

import os
import re

import pytest

from mcp_server.core import McpGuiCore

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI,
                      case_uri_or_skip)

IDS_NAME = 'equilibrium'
TIME_PATH = 'equilibrium.time'
IP_PATH = 'equilibrium.time_slice[0].global_quantities.ip'
PUI_PATH = 'equilibrium.time_slice[0].global_quantities.pui'

EQUILIBRIUM_OCCURRENCES = [0, 1, 2, 3]
EQUILIBRIUM_SIGNALS = 3368
TIME_SAMPLES = 49

PNG_MAGIC = b'\x89PNG\r\n\x1a\n'

pytestmark = [pytest.mark.case, pytest.mark.ui]


@pytest.fixture(scope='module')
def core(qapp, tmp_path_factory):
    """One session of the core, and the case it works on.

    The suite does not isolate ``$HOME``, so the session and the selection
    this file writes land in the real ``~/.imasviz`` when ``HOME`` is left
    alone; the helpers read ``HOME`` when they are called, so patching it for
    the module is enough, and it is undone when the module is done -- the
    fixture of the journey in ``test_45``, the same reason.
    """
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    home = tmp_path_factory.mktemp('mcpCoreHome')
    patch = pytest.MonkeyPatch()
    patch.setenv('HOME', str(home))
    session = McpGuiCore()
    try:
        yield session, home
    finally:
        patch.undo()


# ------------------------------------------------------------------ opening


def test_a_fresh_session_holds_no_case(core):
    session, _home = core
    assert session.list_cases() == []
    assert session.list_windows() == []


def test_opening_the_case_registers_its_idss_and_asks_the_case(core):
    session, _home = core
    answer = session.open_case(CASE_URI, CASE_DATA_DICTIONARY_VERSION)

    assert answer['uri'] == CASE_URI
    assert answer['dd_version'] == CASE_DATA_DICTIONARY_VERSION
    assert answer['already_open'] is False
    assert IDS_NAME in answer['ids']

    listed = {entry['name']: entry['occurrences']
              for entry in session.list_idss(CASE_URI)}
    assert listed[IDS_NAME] == EQUILIBRIUM_OCCURRENCES

    cases = session.list_cases()
    assert len(cases) == 1
    assert cases[0]['loaded'] == {}


def test_opening_the_same_case_again_is_the_already_answer(core):
    session, _home = core
    answer = session.open_case(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
    assert answer['already_open'] is True
    assert len(session.api.DTVlist) == 1


def test_a_case_that_is_not_open_is_refused_by_name(core):
    session, _home = core
    with pytest.raises(ValueError, match='is not open in this session'):
        session.list_idss('imas:hdf5?path=/no/such/case')


# -------------------------------------------------------------------- load


def test_loading_an_occurrence_fills_the_tree_and_lists_nothing_else(core):
    session, _home = core
    answer = session.load_ids(CASE_URI, IDS_NAME, 0)

    assert answer['already'] is False
    assert answer['signals'] == EQUILIBRIUM_SIGNALS
    assert session.list_cases()[0]['loaded'][IDS_NAME] == [0]

    # The other IDSs still hold data -- the case answers for them -- while the
    # bookkeeping of this view recorded only what this load put in it.
    listed = {entry['name']: entry['occurrences']
              for entry in session.list_idss(CASE_URI)}
    assert listed['pulse_schedule'], 'pulse_schedule holds occurrence 0'
    assert 'pulse_schedule' not in session.list_cases()[0]['loaded']


def test_loading_the_same_occurrence_is_the_already_answer(core):
    session, _home = core
    answer = session.load_ids(CASE_URI, IDS_NAME, 0)
    assert answer['already'] is True
    assert answer['signals'] == EQUILIBRIUM_SIGNALS


# -------------------------------------------------------------------- search


def test_searching_answers_the_named_leaf_and_only_leaves(core):
    """The three spellings of a node are all answers and all are matched.

    The tree carries a display path (`equilibrium/time_slice(0)/...`), a
    data name (`equilibrium.time_slice[0]....`) and a parametrized path
    (`equilibrium.time_slice[i]....`); an agent is handed whichever of the
    three it wants, and the search answers them together.
    """
    session, _home = core
    found = session.search_nodes(CASE_URI, 'global_quantities.ip')
    assert found, 'the needle names at least the ip leaf'
    # The needle is a substring: the neighbours (`ip_error_*`) may answer
    # with it, but nothing that does not spell it in one of its three forms.
    for entry in found:
        aliases = [entry['path'], entry['data_name'], entry['parametrized']]
        assert any('global_quantities.ip' in (alias or '')
                   for alias in aliases), entry
    named = next(entry for entry in found
                 if entry['data_name'] == IP_PATH)
    assert named['path'] == 'equilibrium/time_slice(0)/global_quantities/ip'
    assert named['ids'] == IDS_NAME
    assert int(named['occurrence']) == 0

    assert session.search_nodes(CASE_URI, ids_name='no_such_ids') == []


def test_selecting_records_the_paths_and_refuses_the_missing_ones(core):
    session, _home = core
    answer = session.select_signals(CASE_URI, [TIME_PATH, IP_PATH])
    assert answer['selection_size'] == 2

    # A path that is a quantity in the dictionary but not a leaf of **this**
    # case is refused by name, and the refusal costs nothing: the selection
    # is what it was.
    with pytest.raises(ValueError, match='Not found in the tree'):
        session.select_signals(CASE_URI, [PUI_PATH])
    assert len(session.api.DTVlist[0].selectedSignalsDict) == 2


def test_unselecting_empties_the_selection_and_says_how_many(core):
    session, _home = core
    assert session.unselect_all(CASE_URI) == {'dropped': 2}
    assert len(session.api.DTVlist[0].selectedSignalsDict) == 0


def test_list_selection_answers_what_the_case_holds_selected(core):
    """`select_signals` puts two leaves in, and the read answers them -- in
    order, with the ids and occurrence the record holds. Empty is the
    answer `count: 0`, not a refusal."""
    session, _home = core
    assert session.list_selection(CASE_URI) == {'count': 0,
                                                'selection': []}

    session.select_signals(CASE_URI, [TIME_PATH, IP_PATH])
    answer = session.list_selection(CASE_URI)
    assert answer['count'] == 2
    dataNames = [entry['data_name'] for entry in answer['selection']]
    assert dataNames == [TIME_PATH, IP_PATH]
    for entry in answer['selection']:
        assert entry['ids'] == IDS_NAME
        assert entry['occurrence'] == 0
        assert entry['path'], entry


def test_describe_node_is_the_documentation_of_the_tree(core):
    """The same answer the *Node Documentation* panel draws: the array leaf
    says its size and its finite numbers, the clock its number of samples,
    and a leaf the tree does not hold is refused by name, through the same
    lookup as every gesture that looks one up."""
    session, _home = core

    leaf = session.describe_node(
        CASE_URI, 'equilibrium/time_slice(0)/profiles_1d/psi')
    assert leaf['name'] == 'equilibrium.time_slice[0].profiles_1d.psi'
    assert leaf['size'] == '101'
    assert leaf['minimum'] is not None and leaf['maximum'] is not None
    assert float(leaf['minimum']) <= float(leaf['maximum'])
    assert leaf['preview']

    clock = session.describe_node(CASE_URI, TIME_PATH)
    assert clock['size'] == str(TIME_SAMPLES)

    with pytest.raises(ValueError, match='is not a leaf of the case'):
        session.describe_node(CASE_URI,
                              'equilibrium/time_slice(7)/global_quantities/ip')
    with pytest.raises(ValueError, match='is not open in this session'):
        session.describe_node('imas:hdf5?path=/no/such/case', IP_PATH)


# ------------------------------------------------------------------- plotting


def test_plotting_the_selection_builds_a_curve_figure(core):
    session, _home = core
    session.select_signals(CASE_URI, [TIME_PATH, IP_PATH])

    figures = session.plot_selection(CASE_URI)['figures']
    assert figures, 'the selection of two readable quantities drew nothing'
    head = figures[0]
    assert head.startswith('SlicesPlot'), head
    frame = session.api.figureframes[head]
    assert frame.isDrawing()

    windows = session.list_windows()
    assert head in {entry['key'] for entry in windows}
    assert any(entry['key'] is None and entry['cases'] == [CASE_URI]
               for entry in windows), 'the case view is not in the list'


def test_hiding_and_showing_a_window_keeps_its_key(core):
    session, _home = core
    head = sorted(session.api.figureframes)[0]

    assert session.hide_window(head)['visible'] is False
    assert head in session.api.figureframes
    assert session.show_window(head)['visible'] is True

    with pytest.raises(ValueError, match='No window holds the key'):
        session.hide_window('SlicesPlotDoesNotExist')


def test_get_signal_answers_the_read_along_time(core):
    session, _home = core
    payload = session.get_signal(CASE_URI, TIME_PATH,
                                 as_function_of_time=True)
    assert payload['kind'] == 'curve'
    assert len(payload['x']) == TIME_SAMPLES
    assert len(payload['y']) == TIME_SAMPLES


def test_screenshots_answer_png_and_refuse_the_absent_window(core):
    session, _home = core
    head = sorted(session.api.figureframes)[0]
    png = session.screenshot(head)
    assert isinstance(png, bytes)
    assert png[:len(PNG_MAGIC)] == PNG_MAGIC

    with pytest.raises(ValueError, match='No application window'):
        session.screenshot('app')

    # A name that is neither a figure key nor an open case is refused by name,
    # through the same case lookup as every other gesture.
    with pytest.raises(ValueError, match='is not open in this session'):
        session.screenshot('no/such/thing')


def test_the_log_panel_carries_the_gestures(core):
    session, _home = core
    logs = session.get_logs(CASE_URI, tail=50)
    assert logs['uri'] == CASE_URI
    assert logs['lines'], 'the log panel is empty after open, load, select, plot'
    # The panel is where the named refusals end up: one of the gestures is told.
    assert any('equilibrium' in line for line in logs['lines']), logs['lines']

    with pytest.raises(ValueError, match='is not open in this session'):
        session.get_logs('imas:hdf5?path=/no/such/case')


# ------------------------------------------------------------------- plugins


def test_both_registered_plugins_are_offered_for_equilibrium(core):
    """The two names of the table `RegisteredPlugins`: one claims this IDS.

    `VizProfiles_plugin` offers on any IDS root, `equilibriumcharts` only on
    the one it claims -- so the two together are the answer for this root,
    and a refusal of one must not cost the other (the catalog is where it is
    named, and this list carries the refusals with the entries).
    """
    session, _home = core
    offer = session.list_plugins(CASE_URI, IDS_NAME)
    offered = {entry['plugin'] for entry in offer['entries']}
    assert 'VizProfiles_plugin' in offered, offer
    assert 'equilibriumcharts' in offered, offer


def test_running_the_profiles_entry_answers_with_a_window(core):
    session, _home = core
    offer = session.list_plugins(CASE_URI, IDS_NAME)
    entry = next(entry for entry in offer['entries']
                 if entry['plugin'] == 'VizProfiles_plugin')

    before = len(session.api.figureframes)
    answer = session.run_plugin(CASE_URI, 'VizProfiles_plugin',
                                entry['entry'], occurrence=0,
                                ids_name=IDS_NAME)
    assert answer['ran']['occurrence'] == 0
    after = len(session.api.figureframes)
    assert after > before, 'the entry ran and added no window'


def test_an_entry_the_case_does_not_offer_is_refused_by_name(core):
    session, _home = core
    with pytest.raises(ValueError, match='does not offer entry'):
        session.run_plugin(CASE_URI, 'VizProfiles_plugin', 9999,
                           occurrence=0, ids_name=IDS_NAME)


# ------------------------------------------------------------------- session


def test_saving_writes_the_file_and_restore_puts_it_back(core):
    session, home = core
    saved = session.save_session(name='mcp_core')
    path = saved['saved_to']
    assert os.path.exists(path), path
    assert 'imasviz' in os.path.dirname(path), path

    putBack = session.restore_session(name='mcp_core')
    assert putBack['cases'] and putBack['cases'][0]['opened'] is True
    assert putBack['cases'][0]['uri'] == CASE_URI
    # The figure the session wrote is back under the key it held.
    assert session.api.figureframes, 'the restore put back no window'


# --------------------------------------------------------- configurations


def test_listings_name_the_files_the_folder_holds(core):
    """The listings read the folder the way the application's dialogs
    name it, and a kind the application does not answer is refused by
    name -- 'session' among them, by the tool that lists the sessions."""
    session, home = core
    assert 'mcp_core.vsess' in session.list_sessions()['sessions']

    both = session.list_configurations()
    assert 'plot' in both and 'selection' in both
    assert session.list_configurations(kind='plot').keys() == {'plot'}
    assert session.list_configurations(kind='selection').keys() == {'selection'}

    with pytest.raises(ValueError, match='not a configuration kind'):
        session.list_configurations(kind='banana')
    with pytest.raises(ValueError, match='list_sessions'):
        session.list_configurations(kind='session')


def test_a_selection_is_saved_applied_and_listed_again(core):
    """`save_selection` writes the .lsp the application writes,
    `select_from_configuration` applies it the way the menu does (loading
    what the case lacks first), and the listing sees the file under its
    name."""
    session, home = core
    session.select_signals(CASE_URI, [TIME_PATH, IP_PATH])
    saved = session.save_selection(CASE_URI, 'mcp_sel')
    assert saved['count'] == 2
    assert saved['saved_to'].endswith('.lsp')
    assert os.path.exists(saved['saved_to'])
    assert 'mcp_sel.lsp' in session.list_configurations('selection')['selection']

    assert session.unselect_all(CASE_URI) == {'dropped': 2}
    answer = session.select_from_configuration(CASE_URI, 'mcp_sel')
    assert answer['selected'] == 2
    assert answer['from'] == saved['saved_to']
    assert session.list_selection(CASE_URI)['count'] == 2

    # A name the folder does not hold is refused by name, and names the
    # ones the folder does hold.
    with pytest.raises(ValueError, match='No configuration \"banana\"'):
        session.select_from_configuration(CASE_URI, 'banana')


def test_saving_a_selection_with_nothing_selected_is_refused_by_name(core):
    session, _home = core
    session.unselect_all(CASE_URI)
    with pytest.raises(ValueError, match='Nothing to save'):
        session.save_selection(CASE_URI, 'nothing_selected')


def test_a_table_window_is_saved_as_a_plot_configuration(core):
    """`save_plot_configuration` writes one Table Plot View as
    `QVizSavePlotConfiguration` writes it: the .pcfg holding the panels
    and their places, in the listing of its kind -- and refused by name
    on a window that is not a Table Plot View."""
    session, home = core
    # The table window fills its panels from the case's selection, the
    # way its entry fills them: the two quantities are in the selection
    # when the window is asked for.
    session.select_signals(CASE_URI, [TIME_PATH, IP_PATH], additive=False)
    table = session.plot_table(CASE_URI, [TIME_PATH, IP_PATH])
    assert table['panels'] == 2

    saved = session.save_plot_configuration(CASE_URI, table['figure'],
                                            'mcp_table')
    assert saved['panels'] == 2
    assert saved['saved_to'].endswith('.pcfg')
    assert os.path.exists(saved['saved_to'])
    assert 'mcp_table.pcfg' in session.list_configurations('plot')['plot']

    # A window that is not a Table Plot View is refused by name: a curve
    # figure this test drew itself, so the window is alive when the
    # refusal is asked.
    curveFigure = session.plot_selection(CASE_URI)['figures'][0]
    with pytest.raises(ValueError, match='not a Table Plot View'):
        session.save_plot_configuration(CASE_URI, curveFigure,
                                        'not_a_table')


# ------------------------------------------------------------------- reports


def test_curve_stats_are_nan_aware_and_empty_answers_zero(core):
    """`curveStats` is a pure function of one `(x, y)` curve: one number
    per field, the nan and inf entries *counted* rather than folded into
    the minimum or the mean, and an empty curve the answer `n: 0` -- not
    an exception, and not a minimum of the nothing."""
    stats = McpGuiCore.curveStats(
        ([0, 1, 2, 3], [1.0, 2.0, float('nan'), 4.0]))
    assert stats['n'] == 4
    assert stats['x0'] == 0 and stats['x1'] == 3
    # The finite minimum and maximum: the nan is not one of them.
    assert stats['min'] == 1.0 and stats['max'] == 4.0
    assert stats['nan'] == 1 and stats['inf'] == 0
    assert stats['mean'] == pytest.approx((1.0 + 2.0 + 4.0) / 3)
    assert stats['std'] >= 0

    empty = McpGuiCore.curveStats(([], []))
    assert empty['n'] == 0
    assert empty['min'] is None and empty['max'] is None
    assert empty['nan'] == 0 and empty['inf'] == 0

    both = McpGuiCore.curveStats(([1.0], [float('nan'), float('inf')]))
    assert both['nan'] == 1 and both['inf'] == 1


def test_plot_report_writes_the_window_and_refuses_the_panel(core):
    """`plot_report` draws one window of curves into a self-contained
    HTML page under the session's `~/.imasviz/reports`: the window's
    image, one row per trace it drew with the statistics of each -- and
    a window that draws no curve it could stat is refused by name."""
    session, home = core
    session.select_signals(CASE_URI, [TIME_PATH, IP_PATH], additive=False)
    figure = session.plot_selection(CASE_URI)['figures'][0]
    assert figure.startswith('SlicesPlot'), figure

    answer = session.plot_report(figure, name='mcp_plot_report')
    saved = answer['saved_to']
    assert saved.endswith('mcp_plot_report.html'), saved
    assert answer['traces'] >= 2, 'the two quantities drew nothing to stat'
    assert os.path.dirname(saved) == os.path.join(str(home), '.imasviz',
                                                  'reports'), saved
    assert os.path.exists(saved), saved

    with open(saved, encoding='utf-8') as file:
        page = file.read()
    assert '<table>' in page, 'the page carries no table of curves'
    assert 'data:image/png;base64,' in page, 'the window image is not in it'
    assert 'equilibrium.time' in page, 'the clock quantity is not a row'
    assert 'global_quantities.ip' in page, 'the scalar is not a row'

    # A window that draws no curve it could stat is refused by name: the
    # Profiles panel this file's own run put on screen is exactly such a
    # window -- it holds a list, not a curve.
    panelKeys = [key for key in session.api.figureframes
                 if key.startswith('PlotView:')]
    assert panelKeys, 'the Profiles window of the entry run is not on screen'
    with pytest.raises(ValueError, match='has nothing to say about it'):
        session.plot_report(panelKeys[0], name='no_curves')


def test_case_report_stats_the_loaded_tree_and_refuses_the_absent(core):
    """`case_report` stats the whole loaded tree of the case in tree
    order, and a case that is not open in this session is refused by
    name -- the read is of the one the session holds, not a guess.

    A curve is a non-empty multi-dimensional number: the loaded
    `equilibrium` here is mostly 0-D scalars (a single point, the domain
    of `describe_node`) and empty 1-D bound arrays (no sample to stat),
    so the report carries the arrays that actually hold values -- a
    handful on this case, and among them the two named below.
    """
    session, home = core
    answer = session.case_report(CASE_URI, name='mcp_case_report')
    saved = answer['saved_to']
    assert saved.endswith('mcp_case_report.html'), saved
    # At least the clock and one profile curve hold values on this case.
    assert answer['curves'] >= 2, answer
    assert os.path.dirname(saved) == os.path.join(str(home), '.imasviz',
                                                  'reports'), saved
    assert os.path.exists(saved), saved

    with open(saved, encoding='utf-8') as file:
        page = file.read()
    assert '<table>' in page, 'the page carries no table of curves'
    assert 'equilibrium.time' in page, 'the clock curve is not a row'
    assert 'profiles_1d.psi' in page, 'a profile curve is not a row'
    # One row carries its sample count as an integer statistic cell.
    assert re.search(r'<td class="s">\d+</td>', page), \
        'no row carries a numeric statistic'

    with pytest.raises(ValueError, match='is not open in this session'):
        session.case_report('imas:hdf5?path=/no/such/case', name='nope')


# -------------------------------------------------------------------- export


def test_exporting_writes_a_case_that_can_be_opened(core):
    session, home = core
    target = 'imas:hdf5?path=' + os.path.join(
        home, 'export', 'west', '3', '54924', '0')
    answer = session.export_to_ids(CASE_URI, target)
    written = answer['written_to']
    assert written == target

    directory = os.path.join(home, 'export', 'west', '3', '54924', '0')
    assert os.path.exists(os.path.join(directory, 'master.h5')), directory


# ---------------------------------------------------------------- closing


def test_closing_the_case_closes_its_view(core):
    session, _home = core
    session.close_case(CASE_URI)
    assert session.list_cases() == []
    assert session.api.DTVlist == []
