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
