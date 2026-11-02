# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The Profiles plugin run end to end, on every IDS of the case.

No test in this suite had ever *run* a plugin before this file: `test_43` pins the
menu that offers one and the catalog that builds it, and what happened once an
entry was chosen had never been asked. It mattered then because the plugin was the
only door left to the legacy figure island (T22), and it matters now because the
plugin is the one entry offered for **any** IDS of the case.

The old window knew five IDSs by name and about a hundred and twenty literals of
paths and tab labels; it read its quantities through `getAll_0D_1D_Nodes`, which
keeps only a child that `isDynamicData()`, so an IDS written at
`homogeneous_time = 1` -- `magnetics`, `wall`, most of the dictionary -- had
nothing to show and the entry said so by not existing. It drew its own grid, so
nothing it produced was in `figureframes` under a key the rest of the application
knows: no *Show/Hide* line, no session, no *Configure Plot*, no error bars.

What the run answers on the reference case (WEST 54924 run 0, data dictionary
3.35.0, `Ignore_GGD = 1`, the tensor-rank preference off), in absolute numbers. The
case holds occurrences **[0, 1, 2, 3]** of `equilibrium` and `core_profiles`, **[0,
1]** of `magnetics` and **[0]** of `wall`:

    equilibrium     0,67 s   10 tabs   191 quantities   536 error fields refused
    core_profiles   0,30 s    9 tabs   220 quantities   558 error fields refused
    magnetics       0,91 s    4 tabs    21 quantities    16 error fields refused
    wall            0,20 s    4 tabs    52 quantities    96 error fields refused

The time the panel costs includes loading the occurrence it was asked for, asked
synchronously: the offer is a walk of the tree that load builds, so an
asynchronous one leaves the panel with nothing to walk. The error-field count is a
refusal the panel says out loud rather than a pile of panels -- `equilibrium`
answers 727 plottable quantities and **536** of them are `*_error_upper` and
friends, which the application draws as bars on the curve they belong to.

Drawing is the application's command, and the numbers show what that costs and
what it refuses: the `time_slice/profiles_1d` page of `equilibrium` occurrence 0
holds **50** quantities and puts **37** panels on screen in **1,05 s**. The **13**
that are missing each said why in the log of the case ("no values along the plotted
axis"), and the window they were refused from is the one the tree's own right click
would have opened: a `TablePlotView:` key in `figureframes`, embedded in the MDI
area, dressed by *Configure Plot* and put back by a session -- see `test_69` for
what a session does with it.
"""

import time

import pytest
import pyqtgraph

from PySide6.QtWidgets import QMainWindow, QMdiArea

import imasviz.VizPlugins.viz_Profiles.VizProfiles_plugin as profilesPlugin
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizMainMenuController \
    import QVizMainMenuController
from imasviz.VizPlugins.QVizPluginCatalog import QVizPluginCatalog
from imasviz.VizPlugins.VizPlugin import QVizPluginWindow
from imasviz.VizPlugins.viz_Profiles.viz_profiles.QVizProfilePanel import \
    QVizProfilePanel
from imasviz.VizUtils import FigureTypes

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip)
from support import ownership

IDS_NAME = 'equilibrium'
PLUGIN = 'VizProfiles_plugin'
WINDOW_KEY = 'PlotView:1'
ROOT_WINDOW = 'IMASViz root window'

# What the case answers for each of the four IDSs this file walks: the occurrence
# list the combo is bounded by, and the offer the tree answers for occurrence 0.
CASE_ANSWERS = {
    'equilibrium': ([0, 1, 2, 3], 10, 191, 536),
    'core_profiles': ([0, 1, 2, 3], 9, 220, 558),
    'magnetics': ([0, 1], 4, 21, 16),
    'wall': ([0], 4, 52, 96)}

# The tab bar of `equilibrium` occurrence 0: one tab per array of structures the
# tree holds, and one for the quantities outside any of them.
TABS = ['time_slice/boundary', 'time_slice/boundary_separatrix',
        'time_slice/boundary_secondary_separatrix', 'time_slice/constraints',
        'time_slice/global_quantities', 'time_slice/profiles_1d',
        'time_slice/coordinate_system', 'time_slice/convergence',
        'time_slice', 'no array of structures']

# The page this file draws: 50 quantities along the clock, 37 panels, because 13
# of those quantities hold no value along the plotted axis and each says so.
PAGE = 'time_slice/profiles_1d'
PAGE_QUANTITIES = 50
PAGE_PANELS = 37

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


class Session:
    """One application session, with one case view and one plugin entry run.

    The case view is opened the way the application opens it -- a source from the
    factory, the data dictionary the case was written with, then the api building
    the view -- because pinning the dictionary after the view exists moves the
    registry key under it, and the view can then ask the case nothing at all.
    """

    def __init__(self, qapp, root):
        self.qapp = qapp
        self.root = root
        self.api = QVizMainMenuController(root).openShotView.api
        self.view = None
        self.catalog = None
        self.panel = None
        self.windowKey = None
        self.cost = None
        self.frames = []

    def openCase(self, uri, ddVersion):
        source = QVizDataSourceFactory().create(uri)
        source.dd_version = ddVersion
        self.view = self.api.CreateDataTree(source).dataTreeView
        self.catalog = QVizPluginCatalog(self.view)
        self.view.pluginCatalog = self.catalog
        self.api.ShowDataTree(self.view)
        self.qapp.processEvents()

    def entriesOf(self, idsName):
        return [(entry.pluginName, entry.number, entry.label)
                for entry in self.catalog.entriesFor(
                    self.view.IDSRoots[idsName])]

    def profilesEntry(self, idsName=IDS_NAME):
        chosen = [entry for entry
                  in self.catalog.entriesFor(self.view.IDSRoots[idsName])
                  if entry.pluginName == PLUGIN]
        assert chosen, 'no %s entry on the %s IDS' % (PLUGIN, idsName)
        return chosen[0]

    def run(self, entry):
        """Choose the entry and keep what it put on screen."""
        before = set(self.api.figureframes)
        t0 = time.time()
        self.catalog.run(entry)
        self.cost = time.time() - t0
        self.qapp.processEvents()
        new = sorted(set(self.api.figureframes) - before)
        assert len(new) == 1, 'the entry registered %r' % (new,)
        self.windowKey, self.panel = new[0], self.api.figureframes[new[0]]
        return self.panel

    def pump(self, times=50):
        for _ in range(times):
            self.qapp.processEvents()


@pytest.fixture(scope='module')
def session(qapp):
    """One case, and the Profiles entry run on `equilibrium` -- so these tests
    read what the entry left on screen, in the order they are written.
    """
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    root = RootWindow()
    root.show()
    qapp.processEvents()
    made = Session(qapp, root)
    made.openCase(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
    made.run(made.profilesEntry())
    # The window, its api and the frames its buttons draw are what keeps every
    # pyqtgraph view here alive -- which is what the application does through
    # `figureframes`, and what the ownership guard of test_44 asks a test for.
    ownership.keep(made)
    yield made


# --------------------------------------------------------------------------
# What the menu offers, and on which IDS
# --------------------------------------------------------------------------

def test_the_entry_is_offered_on_every_ids_of_the_case(session):
    """The plugin used to know five IDS names; the tree answers the question now.

    Measured on this case: `magnetics` and `wall` carried no entry at all, because
    their IDSs are written at `homogeneous_time = 1` and the old read kept only
    what it called dynamic. Each of the four IDSs walked here earns the line, and
    the text of the line says which IDS it was offered on.
    """
    assert session.entriesOf('magnetics') == \
        [(PLUGIN, 0, 'Plot what the magnetics IDS holds...')]
    assert session.entriesOf('wall') == \
        [(PLUGIN, 0, 'Plot what the wall IDS holds...')]
    # equilibrium carries the other plugin's line too, and the two numbers are the
    # plugins' own, not their place in the menu.
    assert session.entriesOf('equilibrium') == [
        ('equilibriumcharts', 0, 'Equilibrium overview...'),
        (PLUGIN, 0, 'Plot what the equilibrium IDS holds...')]


def test_the_entry_asks_its_window_nothing_of_its_user(session):
    """No dialog stands between the click and the window.

    The occurrence question used to be a modal `QInputDialog` spin box: measured, a
    probe sat in it **240 s** on this case, because nothing in an automated run can
    answer a dialog. The occurrence is a combo on the window now, bounded by what
    the case holds, and the entry takes the first of them when nobody answered.
    """
    assert not hasattr(profilesPlugin, 'QInputDialog')
    assert session.panel.occurrences() == CASE_ANSWERS[IDS_NAME][0]
    assert session.panel.occurrence == 0


# --------------------------------------------------------------------------
# What the window holds
# --------------------------------------------------------------------------

def test_the_window_is_registered_held_and_shown(session):
    assert session.windowKey == WINDOW_KEY
    assert isinstance(session.panel, QVizProfilePanel)
    assert session.panel.isVisible()
    assert WINDOW_KEY in session.api.GetFiguresKeys(
        FigureTypes.PROFILESPLOTTYPE)
    # A plugin window is not an MDI subwindow: measured, `mdiWindowOf` answers
    # None, which is why it travels in a session as a `<PluginWindow>` and not as
    # a `<Figure>`.
    assert session.api.mdiWindowOf(session.panel) is None
    assert session.panel.pluginWindow == QVizPluginWindow(
        uri=CASE_URI, plugin=PLUGIN, entry=0, ids=IDS_NAME, occurrence=0)
    # The whole entry, load included: the offer walks the tree the load builds.
    assert session.cost < 2.0, 'the panel cost %.2f s' % session.cost


def test_the_tabs_are_the_arrays_of_the_case(session):
    """One tab per array of structures, named the way the tree names it.

    Not a list written in the plugin: the same entry on another IDS answers that
    IDS' own arrays, which the two tests below measure.
    """
    panel = session.panel
    assert [panel.tabs.tabText(index) for index in range(panel.tabs.count())] \
        == TABS
    assert panel.offer().quantityCount() == CASE_ANSWERS[IDS_NAME][2]
    assert '536 error fields are not plotted here' in panel.explains.text()


@pytest.mark.parametrize('idsName', ['core_profiles', 'magnetics', 'wall'])
def test_another_ids_answers_its_own_tabs(session, idsName):
    """The same entry, another IDS, and no list of its own anywhere.

    Measured, in seconds for the panel including its synchronous load:
    `core_profiles` 0,30 s / 9 tabs, `magnetics` 0,91 s / 4 tabs, `wall` 0,20 s /
    4 tabs. `magnetics` and `wall` are the two the old plugin refused to offer.
    """
    occurrences, tabs, quantities, errors = CASE_ANSWERS[idsName]
    panel = ownership.keep(QVizProfilePanel(session.api, session.view, idsName,
                                            0))
    session.pump()

    assert panel.occurrences() == occurrences
    assert [panel.occurrenceBox.itemData(index)
            for index in range(panel.occurrenceBox.count())] == occurrences
    assert panel.tabs.count() == tabs
    assert panel.offer().quantityCount() == quantities
    assert ('%d error fields are not plotted here' % errors) \
        in panel.explains.text()
    # The IDS' own arrays, not the equilibrium ones: `wall` is four outline
    # structures and a 2D description, `magnetics` three static arrays.
    assert all(panel.tabs.tabText(index) for index
               in range(panel.tabs.count()))


def test_the_abscissa_choice_offers_the_two_readings_the_commands_honour(session):
    """`TIME`, or the read answering per quantity -- and nothing else.

    A Table Plot View cannot be told to run every panel along one named
    coordinate: its panels are independent by design, so a third entry would
    promise what the command cannot do.
    """
    box = session.panel.abscissaBox
    assert [box.itemData(index) for index in range(box.count())] == \
        [('time',), 'own axis']
    assert session.panel.abscissa() == ('time',)


# --------------------------------------------------------------------------
# What a click draws
# --------------------------------------------------------------------------

def test_a_page_of_the_panel_is_a_table_of_the_application(session):
    """The click runs `QVizPlotAsTable`, so the window is one the api knows.

    Measured: 50 quantities on the tab, **37** panels, in about a second. The 13
    that are missing each said why in the log of the case; a panel that cannot
    read its quantity is refused by name and takes its empty panel back with it,
    which is why the count of panels is 37 and not 50.
    """
    panel = session.panel
    tab = [panel.tabs.widget(index) for index in range(panel.tabs.count())
           if panel.tabs.tabText(index) == PAGE][0]
    assert tab.quantities.count() == PAGE_QUANTITIES

    before = set(session.api.figureframes)
    t0 = time.time()
    frame = tab.drawPage()
    session.pump()
    cost = time.time() - t0

    assert frame is not None
    assert sorted(set(session.api.figureframes) - before) == [frame.figureKey]
    assert frame.figureKey == '%s1' % FigureTypes.TABLEPLOTTYPE
    assert frame.panelCount() == PAGE_PANELS
    assert frame.getPlotAxis() == 'TIME'
    assert session.api.mdiWindowOf(frame) is not None, \
        'the window the plugin drew is not in the MDI area'
    assert cost < 5.0, 'the page cost %.2f s' % cost
    # The window is the api's, so the menus that reach a figure reach it: a key
    # in the `TablePlotView:` namespace, listed by Show/Hide.
    assert session.api.GetFiguresKeys(
        figureType=FigureTypes.TABLEPLOTTYPE) == [frame.figureKey]
    session.frames.append(frame)


def test_the_panels_of_that_window_answer_their_own_right_click(session):
    """*Configure Plot* is on each panel's menu, and one panel at a time.

    Nothing of the plugin's own view box is left to dress a panel: the entry is
    spelled once in `QVizPlotStyling.ENTRY`, so the windows this plugin opens and
    the ones the tree's own right click opens cannot drift apart in wording. The
    menu belongs to the panel's own view box, so styling one panel never reaches
    its neighbour -- and the room between panels, which no panel owns, is asked of
    the window: that is what the margins section writes.

    The error-bar lines are **not** on this menu, and that is said here rather
    than left to be discovered: they belong to a figure of curves, the only frame
    owning a `QVizCurveErrors` (pinned in `test_58`). Which is why the tab offers
    *Draw the selected quantity* beside the page -- an error field is a bar on a
    curve, and the curve lives in the other kind of window.
    """
    frame = session.frames[0]
    panel, neighbour = frame.panels()[0], frame.panels()[1]
    lines = [action.text()
             for action in panel.pgPlotWidget.getViewBox().menu.actions()]

    assert 'Configure Plot' in lines
    assert not any('error bars' in line for line in lines), \
        'a table panel now claims the bars of a curve figure'
    assert panel.styleMargins() is frame.grid
    assert panel.pgPlotWidget.getViewBox() is not \
        neighbour.pgPlotWidget.getViewBox(), 'one menu for two panels'


def test_a_single_quantity_goes_through_the_tree_s_own_command(session):
    """*Draw the selected quantity* is `QVizPlotOneNode`, not a panel of its own.

    Asked for a quantity the page above already drew, so the answer is about the
    frame the gesture opens: a curve figure under a `SlicesPlot:` key, embedded
    like any other, and not a widget of the plugin's making. A quantity of two
    axes of its own answers an image window instead -- which is what the tab's
    sentence about the left-out quantities promises.
    """
    panel = session.panel
    leaf = session.frames[0].panels()[0].treeNode

    frame = panel.drawQuantity(leaf)
    session.pump()

    assert type(frame).__name__ == 'QVizCurvePlot'
    assert frame.figureKey.startswith(FigureTypes.CURVEPLOTTYPE)
    assert session.api.mdiWindowOf(frame) is not None


def test_the_panel_names_what_its_abscissa_cannot_carry(session):
    """A tab that shows fewer rows than its array holds says which and why.

    Measured on `time_slice/coordinate_system`: 3 quantities along the clock and
    **18** left out -- `volume_element`, `r`, `z`, the Jacobian and friends, each
    with two axes of its own. Counting panels without naming the difference is
    how a tab reads as a bug.
    """
    panel = session.panel
    tab = [panel.tabs.widget(index) for index in range(panel.tabs.count())
           if panel.tabs.tabText(index) == 'time_slice/coordinate_system'][0]

    assert tab.quantities.count() == 3
    assert len(tab.group.leftOut(panel.abscissa())) == 18
    assert '18 cannot be read along' in tab.summary.text()
    assert 'volume_element' in tab.summary.text()
