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

* before it, four plugin windows of a probe wrote a **432 byte** file holding **0**
  ``<Figure>`` in **0,013 s**, and the same warning came out four times. A session
  that named its lost windows and lost all of them;
* the Profiles entry used to ask which occurrence to plot through a modal
  ``QInputDialog``: a probe left to answer that one sat in ``askForOccurrence`` for
  **240 s** until a watchdog killed it. The answers still travel in the file and the
  restore still hands them over -- what changed is that the entry has nothing left
  to ask, so the last test of this file refuses a modal question in the source of
  the three modules of the plugin, and a ``<PluginWindow>`` naming another
  occurrence is answered by the panel sitting on that one;
* neither window is in the MDI area: measured, ``mdiWindowOf`` answers None for
  both, so the key comes from ``figureframes`` and where the window came from comes
  from the stamp the plugin leaves. The panel answers a ``figureKey`` of its own
  (``PlotView:1``) because that is the key a session names it by; the Equilibrium
  chart answers none, and its stamp is the only answer there is.

The window that comes back is the one the entry draws, not the one the user left:
its occurrence combo stands where the file put it and its abscissa at the first
choice, because keeping a combo position would be a state of a widget -- the thing
this file format refuses to record. What *does* come back now is everything that
panel drew: a page plotted by the panel is a Table Plot View of the application, so
it is a ``<Figure>`` of the file like any other window, and the last-but-one test
here puts one back.
"""

import ast
import time

import pytest
from PySide6.QtWidgets import QMainWindow, QMdiArea

import imasviz.VizPlugins.viz_Profiles.VizProfiles_plugin as profilesPlugin
from imasviz.VizDataAccess.QVizCurveAbscissa import TIME
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
from imasviz.VizPlugins.viz_Profiles.viz_profiles import QVizProfileOffer as \
    offerModule, QVizProfilePanel as panelModule
from imasviz.VizPlugins.viz_Profiles.viz_profiles.QVizProfilePanel import \
    QVizProfilePanel

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip)
from support import ownership

IDS_NAME = 'equilibrium'
PROFILES = 'VizProfiles_plugin'
CHARTS = 'equilibriumcharts'
ROOT_WINDOW = 'IMASViz root window'

# What the entry takes when nobody answers for it: the first occurrence the case
# holds. The case holds [0, 1, 2, 3], so the other test below can name one the
# entry would never have chosen and check the file's answer wins.
OCCURRENCE = 0
OTHER_OCCURRENCE = 2

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


def waitFor(qapp, what, whatFor, limit=120.):
    """Pump events until `what` answers something.

    Kept for the Equilibrium chart, whose window is a matplotlib figure built
    inside the entry. The Profiles panel is built synchronously in the entry, so
    its tabs are on screen when the entry returns -- and the panel starts no
    thread of its own, which is what a `QThread: Destroyed while thread is still
    running` core dump used to come from.
    """
    deadline = time.time() + limit
    while time.time() < deadline:
        answer = what()
        if answer is not None:
            return answer
        qapp.processEvents()
        time.sleep(0.02)
    raise AssertionError('%s never arrived within %.0f s' % (whatFor, limit))


def profilesPanel(api, key):
    """The Profiles window of that key, once its tabs are built."""

    def ask():
        window = api.figureframes.get(key)
        if window is not None and window.tabs.count():
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
    made = Run(qapp)
    try:
        made.openCase(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
        made.catalog.run(made.entry(PROFILES))
        waitFor(qapp, profilesPanel(made.api, 'PlotView:1'),
                'the Profiles panel')
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

def test_the_run_writes_both_windows_and_no_figure(run):
    """The two plugin windows are lines of their case, not `<Figure>`s.

    Neither holds a quantity this session chose, and neither stands in the MDI
    area, so what a file can say about them is the entry that drew them -- which
    is exactly what the next run needs to ask for them again.
    """
    saved = QVizSessionFile.read(
        QVizSaveSession(run.api, name='panels').execute())
    windows = saved.cases[0].pluginWindows

    assert windows == [
        QVizSessionPluginWindow('PlotView:1', PROFILES, 0, IDS_NAME,
                                OCCURRENCE),
        QVizSessionPluginWindow('EquiPlotView:1', CHARTS, 0, IDS_NAME, 0)]
    assert saved.figures == []


def test_the_plugin_entry_asks_nothing_of_its_user():
    """No modal question in the click path of any module of the plugin.

    Measured once, on this case: the occurrence question was a `QInputDialog` and
    a probe sat in it **240 s** with no way out, because nothing in an automated
    run can answer a dialog. The occurrence is now a combo the panel fills from
    the case, so the entry has nothing to ask -- and the guard is on the source,
    because a question put back a year from now is exactly what no test of a
    session restore would notice.
    """
    asked = ('getInt', 'getItem', 'getDouble', 'getText', 'getMultiLineText',
             'exec', 'exec_', 'open')
    for module in (profilesPlugin, offerModule, panelModule):
        with open(module.__file__) as handle:
            tree = ast.parse(handle.read())
        calls = {node.func.attr for node in ast.walk(tree)
                 if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute)}
        names = {node.id for node in ast.walk(tree) if isinstance(node,
                                                                  ast.Name)}
        assert not (calls & set(asked)), '%s still asks its user by hand: %r' \
                                         % (module.__name__,
                                            sorted(calls & set(asked)))
        assert 'QInputDialog' not in names and 'QMessageBox' not in names, \
            '%s still imports a dialog' % module.__name__


def test_the_window_is_stamped_with_what_nothing_else_answers(run):
    """The stamp says which plugin, entry, IDS and occurrence drew the window.

    The panel answers a `figureKey` -- it needs one to be in `figureframes`, and
    a session names it by that key -- but a key says nothing about where a window
    came from, and the chart answers no key at all. Measured: `mdiWindowOf`
    answers None for both, so neither can be found through the MDI area.
    """
    panel = run.api.figureframes['PlotView:1']
    chart = run.api.figureframes['EquiPlotView:1']

    assert panel.figureKey == 'PlotView:1'
    assert panel.pluginWindow == QVizPluginWindow(uri=CASE_URI, plugin=PROFILES,
                                                  entry=0, ids=IDS_NAME,
                                                  occurrence=OCCURRENCE)
    assert run.api.mdiWindowOf(panel) is None
    assert not hasattr(chart, 'figureKey')
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

    other = run.freshApi()
    views = QVizRestoreSession(other, path=path).execute()

    assert list(views) == [CASE_URI]
    assert sorted(other.figureframes) == ['EquiPlotView:1', 'PlotView:1']

    back = waitFor(qapp, profilesPanel(other, 'PlotView:1'),
                   'the restored Profiles panel')
    assert isinstance(back, QVizProfilePanel)
    assert back.idsName == IDS_NAME
    assert back.occurrence == OCCURRENCE
    assert back.figureKey == 'PlotView:1'
    assert back.pluginWindow == QVizPluginWindow(uri=CASE_URI, plugin=PROFILES,
                                                 entry=0, ids=IDS_NAME,
                                                 occurrence=OCCURRENCE)
    chart = other.figureframes['EquiPlotView:1']
    assert chart.uri == CASE_URI

    # What is *not* kept, and said here rather than hidden: the entry draws its
    # window, so the panel stands where the entry puts it -- the first abscissa the
    # offer answers -- and no line of the file says which tab was on screen.
    assert back.abscissa() == TIME
    assert back.tabs.currentIndex() == 0


def test_an_occurrence_the_entry_would_not_choose_is_answered_by_the_file(run,
                                                                         qapp):
    """The file's answer wins over the first occurrence the case holds.

    The entry takes occurrence **0** of this case, which holds [0, 1, 2, 3]. A
    ``<PluginWindow>`` naming occurrence 2 has to put the panel on 2, or the
    restore draws curves of another occurrence under a window saying it is the
    second one.
    """
    saved = QVizSessionFile.read(
        QVizSaveSession(run.api, name='panels').execute())
    saved.cases[0] = saved.cases[0]._replace(
        pluginWindows=[QVizSessionPluginWindow('PlotView:1', PROFILES, 0,
                                               IDS_NAME, OTHER_OCCURRENCE)])
    path = saved.write(QVizSessionFile.named('other_occurrence'))

    other = run.freshApi()
    QVizRestoreSession(other, path=path).execute()

    back = waitFor(qapp, profilesPanel(other, 'PlotView:1'),
                   'the Profiles panel of occurrence %d' % OTHER_OCCURRENCE)
    assert back.occurrence == OTHER_OCCURRENCE
    assert back.occurrenceBox.currentData() == OTHER_OCCURRENCE
    assert [back.occurrenceBox.itemData(index)
            for index in range(back.occurrenceBox.count())] == [0, 1, 2, 3]


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
    path = saved.write(QVizSessionFile.named('bad_lines'))

    other = run.freshApi()
    QVizRestoreSession(other, path=path).execute()

    assert 'NoSuchPlugin' in caplog.text
    assert 'no_such_ids' in caplog.text
    assert sorted(other.figureframes) == ['PlotView:1']
    waitFor(qapp, profilesPanel(other, 'PlotView:1'),
            'the Profiles panel of the window that was kept')


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
    path = saved.write(QVizSessionFile.named('other_occurrence_for_charts'))

    other = run.freshApi()
    QVizRestoreSession(other, path=path).execute()

    assert 'reads occurrence 0' in caplog.text
    assert 'drew nothing' in caplog.text
    assert other.figureframes == {}


# --------------------------------------------------------------------------
# What the panel drew comes back as a figure of its own
# --------------------------------------------------------------------------

def test_a_page_the_panel_drew_is_a_figure_the_session_puts_back(run, qapp):
    """The payoff of drawing through the application's commands.

    A page plotted by the panel is a Table Plot View under a `TablePlotView:` key
    in `figureframes`, so the *Windows* menu, *Configure Plot* and the session
    file reach it like any window the tree's own right click produced. Measured on
    the reference case: the smallest group of `equilibrium` occurrence 0 draws one
    panel, and the file that follows names it, its kind and its one quantity.

    Last in the file on purpose: the windows this test opens are in `figureframes`
    for the tests above, which count what the run left there.
    """
    panel = run.api.figureframes['PlotView:1']
    group = min(panel.groups(), key=lambda one: len(one.following(
        panel.abscissa())))
    frame = panel.drawQuantities(group, group.following(panel.abscissa()))
    assert frame is not None, 'no panel drawn from the smallest group'
    assert frame.figureKey.startswith('TablePlotView:')

    path = QVizSaveSession(run.api, name='with_a_page').execute()
    saved = QVizSessionFile.read(path)
    drawn = [figure for figure in saved.figures
             if figure.key == frame.figureKey]
    assert len(drawn) == 1
    assert drawn[0].kind == 'table'
    assert len(drawn[0].quantities) == len(frame.panels())

    other = run.freshApi()
    QVizRestoreSession(other, path=path).execute()
    back = other.figureframes.get(frame.figureKey)
    assert back is not None, 'the window the panel drew did not come back'
    assert back.panelCount() == frame.panelCount()
    assert back.getPlotAxis() == frame.getPlotAxis()
