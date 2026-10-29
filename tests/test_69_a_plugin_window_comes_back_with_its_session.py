# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""A window a plugin drew, saved as the menu line that drew it, and put back.

``test_66`` pins what a ``<PluginWindow>`` says and what it refuses; ``test_43``
pins what a catalog will and will not answer. This file pins the promise on the
reference case (WEST 54924 run 0, pinned at data dictionary 3.35.0): the Profiles
panel and the Equilibrium chart come back in a session that never saw them, under
the keys the file names, **without asking their user anything again**.

What made this worth measuring, in absolute numbers, on the reference case:

* before it, four plugin windows of a probe wrote a **432 byte** file holding
  **0** ``<Figure>`` in **0,013 s**, and the same warning came out four times. A
  session that named its lost windows and lost all of them;
* the Profiles entry asks which occurrence to plot through a modal
  ``QInputDialog``, and a probe left to answer that one sat in
  ``askForOccurrence`` for **240 s** until a watchdog killed it. So the answers
  travel in the file and the restore hands them over; a plugin that cannot take
  them is refused by name rather than run into its own dialog;
* the cost of putting both windows back: the case view **1,55 s**, the Profiles
  entry **0,27 s** with its interface **0,31 s** later (the tabs are built on a
  thread of its own), the Equilibrium chart **2,88 s** cold and **0,34 s** once
  the IDS is in memory. A restore of the four windows of the probe took **2,23 s**
  for the file and **3,78 s** more before the Profiles interface was on screen;
* neither window answers where it came from: measured, the Profiles panel has no
  ``figureKey`` and no ``key`` attribute and the Equilibrium chart has neither,
  while ``mdiWindowOf`` answers None for both -- so the key comes from
  ``figureframes`` and the rest from the stamp the plugin leaves.

The window that comes back is the one the entry draws, not the one the user left:
its time slider stands at 0 and the tabs a user added inside the panel are not in
the file. That is said here rather than fixed, because keeping it would be a
state of a widget -- the thing this file format refuses to record.
"""

import time

import pytest
from PySide6.QtWidgets import QMainWindow, QMdiArea

import imasviz.VizPlugins.viz_Profiles.VizProfiles_plugin as profilesPlugin
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizGUI.VizConfigurations.QVizSessionFile import (
    QVizSessionFile, QVizSessionPluginWindow)
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizMainMenuController \
    import QVizMainMenuController
from imasviz.VizGUI.VizGUICommands.VizSession.QVizRestoreSession import \
    QVizRestoreSession
from imasviz.VizGUI.VizGUICommands.VizSession.QVizSaveSession import \
    QVizSaveSession
from imasviz.VizPlugins.QVizPluginCatalog import QVizPluginCatalog
from imasviz.VizPlugins.VizPlugin import QVizPluginWindow
from imasviz.VizPlugins.viz_Profiles.viz_profiles.VizProfiles import VizProfiles

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip)
from support import ownership

IDS_NAME = 'equilibrium'
PROFILES = 'VizProfiles_plugin'
CHARTS = 'equilibriumcharts'
ROOT_WINDOW = 'IMASViz root window'

# What the stub below answers. Not the first occurrence the case holds: the file
# has to carry the difference, and a restore that ignored it would draw
# occurrence 0 while the file says 2.
OCCURRENCE = 2

pytestmark = [pytest.mark.case, pytest.mark.dd, pytest.mark.ui]


class RootWindow(QMainWindow):
    """The application's root window, named the way the application names it."""

    def __init__(self):
        super().__init__()
        self.setObjectName(ROOT_WINDOW)
        self.MDI = QMdiArea(self)
        self.IMASdbBrowserWidget = None

    def getMDI(self):
        return self.MDI


class StubDialog:
    """The occurrence question, recorded rather than asked.

    The tests read this list: an empty one after a restore is the promise that no
    modal dialog was opened in the user's place.
    """

    asked = []

    def __init__(self, parent=None):
        self.parent = parent

    @staticmethod
    def getInt(parent, title, label, value, minimum, maximum):
        StubDialog.asked.append((title, label, value, minimum, maximum))
        return (OCCURRENCE, True)


def waitFor(qapp, what, whatFor, limit=120.):
    """Pump events until `what` answers something.

    Waiting is for the **interface**, not for the key: the Profiles panel
    registers itself in `figureframes` inside its constructor and builds its tabs
    on a thread of its own, so reading `spinBox_timeIndex` right after the entry
    answers `<absent>` -- and a process that dies while that thread runs dies
    with `QThread: Destroyed while thread is still running` and a core dump.
    """
    deadline = time.time() + limit
    while time.time() < deadline:
        answer = what()
        if answer is not None:
            return answer
        qapp.processEvents()
        time.sleep(0.02)
    raise AssertionError('%s never arrived within %.0f s' % (whatFor, limit))


def profilesInterface(api, key):
    """The Profiles window of that key, once its interface exists."""

    def ask():
        window = api.figureframes.get(key)
        if window is not None and getattr(window, 'spinBox_timeIndex',
                                          None) is not None:
            return window
        return None

    return ask


class Run:
    """One application run: a root window, an api on its area, one case view.

    The case view is opened as the application opens it, because the plugin
    entries are a menu of that view and their catalog belongs to it -- the same
    catalog the right click installs on `view.pluginCatalog`.
    """

    def __init__(self, qapp):
        self.qapp = qapp
        self.root = RootWindow()
        self.root.show()
        qapp.processEvents()
        self.api = QVizMainMenuController(self.root).openShotView.api
        self.view = None
        self.catalog = None

    def openCase(self, uri, ddVersion):
        source = QVizDataSourceFactory().create(uri)
        source.dd_version = ddVersion
        self.view = self.api.CreateDataTree(source).dataTreeView
        self.catalog = QVizPluginCatalog(self.view)
        self.view.pluginCatalog = self.catalog
        self.api.ShowDataTree(self.view)
        self.qapp.processEvents()

    def entry(self, pluginName, number=0):
        chosen = [candidate for candidate
                  in self.catalog.entriesFor(self.view.IDSRoots[IDS_NAME])
                  if candidate.pluginName == pluginName
                  and candidate.number == number]
        assert chosen, 'no %s entry %d on this node' % (pluginName, number)
        return chosen[0]

    def freshApi(self):
        """An api that never saw those windows: the next run of the application."""
        root = RootWindow()
        root.show()
        self.qapp.processEvents()
        api = QVizMainMenuController(root).openShotView.api
        # Both are held: the root window owns the Qt side, and the api owns
        # `figureframes` -- which is what keeps every window the restore draws
        # alive, exactly as it does in the application.
        ownership.keep(root)
        ownership.keep(api)
        return api


@pytest.fixture(scope='module')
def run(qapp, tmp_path_factory):
    """One run with both plugin windows open, shared in the order written."""
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    home = tmp_path_factory.mktemp('pluginHome')
    patch = pytest.MonkeyPatch()
    # The session files below are named, so they land in `$HOME/.imasviz`: the
    # suite does not isolate that folder anywhere else, and a test that lets the
    # application write there leaves a session the next run will be offered.
    patch.setenv('HOME', str(home))
    patch.setattr(profilesPlugin, 'QInputDialog', StubDialog)
    StubDialog.asked = []
    made = Run(qapp)
    try:
        made.openCase(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
        made.catalog.run(made.entry(PROFILES))
        waitFor(qapp, profilesInterface(made.api, 'PlotView:1'),
                'the Profiles interface')
        made.catalog.run(made.entry(CHARTS))
        waitFor(qapp, lambda: made.api.figureframes.get('EquiPlotView:1'),
                'the Equilibrium frame')
        ownership.keep(made)
        yield made
    finally:
        patch.undo()


# --------------------------------------------------------------------------
# What the run writes
# --------------------------------------------------------------------------

def test_the_run_asks_its_occurrence_once_and_the_file_carries_the_answer(run):
    """The question is real on this case, and it is answered in the file.

    The case holds occurrences [0, 1, 2, 3] of `equilibrium`, so the entry has to
    choose -- and what it chose is the only way a later run can skip the dialog.
    """
    assert [title for title, _, _, _, _ in StubDialog.asked] \
        == ['Which occurrence of the equilibrium IDS?']

    saved = QVizSessionFile.read(
        QVizSaveSession(run.api, name='panels').execute())
    windows = saved.cases[0].pluginWindows

    assert windows == [
        QVizSessionPluginWindow('PlotView:1', PROFILES, 0, IDS_NAME,
                                OCCURRENCE),
        QVizSessionPluginWindow('EquiPlotView:1', CHARTS, 0, IDS_NAME, 0)]
    # Not a `<Figure>`: it holds no quantity this session chose, and it stands
    # outside the MDI area.
    assert saved.figures == []


def test_the_window_is_stamped_with_what_nothing_else_answers(run):
    """Neither registered window says where it came from, so the plugin says it.

    Measured on the reference case: the Profiles panel has no `figureKey` and no
    `key` attribute, and the Equilibrium chart has neither.
    """
    panel = run.api.figureframes['PlotView:1']
    chart = run.api.figureframes['EquiPlotView:1']

    assert not hasattr(panel, 'figureKey') and not hasattr(panel, 'key')
    assert panel.pluginWindow == QVizPluginWindow(uri=CASE_URI, plugin=PROFILES,
                                                  entry=0, ids=IDS_NAME,
                                                  occurrence=OCCURRENCE)
    assert run.api.mdiWindowOf(chart) is None
    assert chart.pluginWindow == QVizPluginWindow(uri=CASE_URI, plugin=CHARTS,
                                                  entry=0, ids=IDS_NAME,
                                                  occurrence=0)


# --------------------------------------------------------------------------
# What the next run puts back
# --------------------------------------------------------------------------

def test_the_windows_come_back_under_their_own_keys_without_a_question(run,
                                                                      qapp):
    """The point of T40c: the same windows, the same keys, nobody asked again."""
    path = QVizSaveSession(run.api, name='panels').execute()
    askedBefore = len(StubDialog.asked)

    other = run.freshApi()
    views = QVizRestoreSession(other, path=path).execute()

    assert list(views) == [CASE_URI]
    assert sorted(other.figureframes) == ['EquiPlotView:1', 'PlotView:1']
    assert len(StubDialog.asked) == askedBefore, \
        'the restore asked the user something: %r' % (StubDialog.asked
                                                      [askedBefore:],)

    back = waitFor(qapp, profilesInterface(other, 'PlotView:1'),
                   'the restored Profiles interface')
    assert isinstance(back, VizProfiles)
    # The occurrence the file named, not the first the case holds.
    assert back.IDS_parameters['occurrence'] == OCCURRENCE
    assert back.ids_related == IDS_NAME
    assert back.pluginWindow == QVizPluginWindow(uri=CASE_URI, plugin=PROFILES,
                                                 entry=0, ids=IDS_NAME,
                                                 occurrence=OCCURRENCE)
    chart = other.figureframes['EquiPlotView:1']
    assert chart.uri == CASE_URI

    # What is *not* kept, and said here rather than hidden: the entry draws its
    # window, so the time index it stands at is the one the entry gives it.
    assert back.time_index == 0


def test_a_window_the_restore_cannot_ask_is_named_and_costs_the_rest_nothing(
        run, qapp, caplog):
    """A `<PluginWindow>` naming what the view does not offer is refused by name.

    Both halves of that refusal are on the log of the case: the entry the tree
    does not hold, and the window that drew nothing once it was asked. The other
    window of the same file comes back regardless -- one bad line is not a
    reason to lose a session.
    """
    saved = QVizSessionFile.read(
        QVizSaveSession(run.api, name='panels').execute())
    saved.cases[0] = saved.cases[0]._replace(
        pluginWindows=[QVizSessionPluginWindow('PlotView:9', 'NoSuchPlugin',
                                               0, IDS_NAME, OCCURRENCE),
                       QVizSessionPluginWindow('EquiPlotView:1', CHARTS, 0,
                                               'no_such_ids', 0),
                       QVizSessionPluginWindow('PlotView:1', PROFILES, 0,
                                               IDS_NAME, OCCURRENCE)])
    askedBefore = len(StubDialog.asked)
    path = saved.write(QVizSessionFile.named('bad_lines'))

    other = run.freshApi()
    QVizRestoreSession(other, path=path).execute()

    assert 'NoSuchPlugin' in caplog.text
    assert 'no_such_ids' in caplog.text
    assert sorted(other.figureframes) == ['PlotView:1']
    assert len(StubDialog.asked) == askedBefore
    # Waited for, not left behind: the entry builds its interface on a thread of
    # its own, and a process that ends while that thread runs dies with
    # `QThread: Destroyed while thread is still running` and a core dump.
    waitFor(qapp, profilesInterface(other, 'PlotView:1'),
            'the Profiles interface of the window that was kept')


def test_an_entry_that_reads_one_occurrence_refuses_another_by_name(run, qapp,
                                                                   caplog):
    """The Equilibrium chart reads occurrence 0 of `equilibrium` and of `wall`.

    A file naming another one is refused rather than answered with a window whose
    curves come from somewhere else, and the reason says which occurrence the
    plugin reads.
    """
    saved = QVizSessionFile.read(
        QVizSaveSession(run.api, name='panels').execute())
    saved.cases[0] = saved.cases[0]._replace(
        pluginWindows=[QVizSessionPluginWindow('EquiPlotView:1', CHARTS, 0,
                                               IDS_NAME, 2)])
    path = saved.write(QVizSessionFile.named('other_occurrence'))

    other = run.freshApi()
    QVizRestoreSession(other, path=path).execute()

    assert 'reads occurrence 0' in caplog.text
    assert 'drew nothing' in caplog.text
    assert other.figureframes == {}
