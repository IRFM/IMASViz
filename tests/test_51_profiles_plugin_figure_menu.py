# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The Profiles plugin run end to end, and the menu its plots answer with.

No test in this suite had ever *run* a plugin. `test_43` pins the menu that
offers one and the catalog that builds it; what happens once an entry is chosen
had never been asked. It matters here because the Profiles plugin is the only
door left to the legacy figure island (T22): its own `CustomizedViewBox` calls
`AddPlot1DToFig`, `plotVsCoordinate1AtGivenTime` and
`plotVsTimeAtGivenCoordinate1`, which engine `QVizPlotWidget` and the `Figure:`
namespace. That island cannot be removed on the strength of a grep: the door has
to be walked, and what it produces measured. Two defects, both measured before
either was touched, stood in the way of walking it.

**The window never got its bottom half.** The plugin builds its tabs, then lays
out the time slider, the spin box, the time-value field and the *Plot* button.
Labelling the slider asks the case for `time_slice[0].time`, which on
IMAS-Python answers an `IDSFloat0D` -- a `numbers.Real` wrapper defining
`__float__` and no `__format__` -- so the f-string `{tmin:.2f}` answered
`TypeError: unsupported format string passed to IDSFloat0D.__format__`
(`VizProfiles.py:504`). The exception left the tabs on screen and everything
below them absent: measured, `slider_time`, `spinBox_timeIndex`,
`lineEdit_timeValue` and `plotButton` do not exist, and `addNewTabsButton` is
`None`. The manual's step 4 ("Move the time slider") was not a slow feature, it
was no feature.

**The plot menu could not open.** `CustomizedViewBox.getMenu` renamed the two
mouse-mode choices by walking `self.menu.leftMenu.actions()`. On pyqtgraph 0.13.7
that sub-menu is a *local* of `ViewBoxMenu.__init__` -- what the object keeps is
`mouseModes` -- so the right click answered `AttributeError: 'ViewBoxMenu' object
has no attribute 'leftMenu'`, and steps 5 and 6 of the manual ("right-click on a
particular plot", "select 'Plot this in a new separate figure'") were unreachable
whatever the rest of the code did.

What the run answers on the reference case (WEST 54924 run 0, data dictionary
3.35.0), in absolute numbers. The case holds occurrences **[0, 1, 2, 3]** of both
`equilibrium` and `core_profiles`, and nothing of `edge_profiles`, `core_sources`
or `core_transport` -- so on this case the plugin always has to ask which
occurrence to plot, and it asks the view that owns the menu, bounded **0..3**.
`run` returns in **4,94 s**; **6,5 s** later the window is on screen, registered
as `PlotView:1`, a top-level window and not an MDI subwindow (measured: its
parent is `None`), holding **2** tabs, **41** plots and **41** curves, every view
box a `CustomizedViewBox`. Those 41 curves are not all the same width: **37** are
drawn over the **101**-point radial coordinate and **4** over their own **72**
points -- the boundary outlines, which carry their own base of points. The slider runs
**0..48**, labelled `n_t = 49; t_min = 32.13` and `t_max = 48.55`, and the time
field starts at `32.1336784362793`.

`getMenu()` costs **0,03 s** and answers **13** actions. Its "Plot <quantity> to"
sub-menu holds **0** lines while no `Figure:` window exists: it lists the figures
this quantity could join, and there are none yet. The two new-figure entries then
build `Figure:1` (a `QVizPlotWidget` drawing **101** points along coordinate1) and
`Figure:2` (**49** points along time), each in **0,05 s**; and the sub-menu now
lists those two.

The plots are counted through `layout.ci.items`, not through `findChildren`: a
`GraphicsLayoutWidget` keeps its plots as scene items, and measured on this very
window `findChildren(PlotItem)` answers **0** while 41 are drawn. An earlier
probe read that as "the plugin builds no plot at all"; this file is what replaced
that reading, and it pins the difference.
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
from imasviz.VizUtils import FigureTypes

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip)
from support import ownership

IDS_NAME = 'equilibrium'
PLUGIN = 'VizProfiles_plugin'
WINDOW_KEY = 'PlotView:1'
ROOT_WINDOW = 'IMASViz root window'

# What the case answers, which is what makes the occurrence question below a
# question the plugin really has to ask here rather than a stub's invention.
OCCURRENCES = [0, 1, 2, 3]
TABS = 2
PLOTS = 41
# Measured, the 41 curves are not all the same width: 37 of them are drawn over
# the 101-point radial coordinate, and 4 over their own 72 points -- the four
# boundary outlines, which carry their own base of points.
WIDTHS = {101: 37, 72: 4}
SLICES = 49
MENU_ACTIONS = 13

pytestmark = [pytest.mark.case, pytest.mark.dd, pytest.mark.ui]


class BrowserStub:
    """The database browser, reduced to what the session reads from it."""

    def getActiveUsername(self):
        return ''

    def addUserDB(self, username):
        pass


class RootWindow(QMainWindow):
    """The application's root window, named the way the application names it."""

    def __init__(self):
        super().__init__()
        self.setObjectName(ROOT_WINDOW)
        self.MDI = QMdiArea(self)
        self.IMASdbBrowserWidget = BrowserStub()

    def getMDI(self):
        return self.MDI


class StubDialog:
    """The occurrence question, recorded instead of asked.

    Measured: this question is a modal `QInputDialog` spin box, and with the four
    occurrences this case holds a probe sat inside `askForOccurrence` for 240 s
    until the watchdog killed the process. What the tests assert on is the
    question -- its parent, its bounds, its title; only its answer is supplied.
    """

    asked = []

    def __init__(self, parent=None):
        self.parent = parent

    @staticmethod
    def getInt(parent, title, label, value, minimum, maximum):
        StubDialog.asked.append((parent, title, label, value, minimum, maximum))
        return (0, True)


def plotsOf(window):
    """Every plot pyqtgraph holds, asked of the layouts that own them."""
    found = []
    for layout in window.findChildren(pyqtgraph.GraphicsLayoutWidget):
        found.extend(item for item in layout.ci.items
                     if isinstance(item, pyqtgraph.PlotItem))
    return found


def subMenuOf(box, title):
    """The "Plot <quantity> to" sub-menu this class builds, by its title.

    Asked through `box.getMenu()`, the gesture that fills it: `getMenu()` clears
    the QMenu this class keeps as `box.contextMenu` and `buildContextMenu()`
    rebuilds it from the figures that exist *now*, so reading that QMenu without
    opening the menu first answers an empty menu rather than a refusal -- measured.
    The sub-menus of the surrounding `ViewBoxMenu` are not safe to re-read, one
    of them measured dead (see the menu tests below).
    """
    box.getMenu()
    if box.contextMenu is None or box.contextMenu.title() != title:
        raise AssertionError('no %r sub-menu on this plot, got %r'
                             % (title, box.contextMenu is None
                                and 'no menu yet' or box.contextMenu.title()))
    return box.contextMenu


class Session:
    """One application session, with one plugin entry run on its case view.

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
        self.window = None
        self.windowKey = None
        self.runCost = None

    def openCase(self, uri, ddVersion):
        source = QVizDataSourceFactory(None).create(uri)
        source.dd_version = ddVersion
        self.view = self.api.CreateDataTree(source).dataTreeView
        # The catalog is the view's own, as QVizPluginMenu installs it: one set
        # of plugins per shot view, however many menus are built on it.
        self.catalog = self.view.pluginCatalog or QVizPluginCatalog(self.view)
        self.view.pluginCatalog = self.catalog
        self.api.ShowDataTree(self.view)
        self.qapp.processEvents()

    def profilesEntry(self):
        entries = self.catalog.entriesFor(self.view.IDSRoots[IDS_NAME])
        chosen = [e for e in entries if e.pluginName == PLUGIN]
        assert chosen, 'no %s entry among %r' % (PLUGIN, [e.pluginName
                                                          for e in entries])
        return chosen[0]

    def run(self, entry):
        """Choose the entry, then wait for what it puts on the screen.

        The plugin walks the case in a thread of its own and builds its tabs back
        on the GUI thread through a signal, so the window appears during the pump
        and not inside `run`.
        """
        before = set(self.api.figureframes)
        self.runCost = _elapsed(self.catalog.run, entry)
        deadline = time.time() + 60
        new = []
        while time.time() < deadline:
            self.qapp.processEvents()
            new = sorted(set(self.api.figureframes) - before)
            if new and plotsOf(self.api.figureframes[new[0]]):
                break
            time.sleep(0.02)
        else:
            raise AssertionError('the plugin entry built no plot within 60 s '
                                 '(new figureframes: %r)' % new)
        assert len(new) == 1, new
        self.windowKey, self.window = new[0], self.api.figureframes[new[0]]
        return self.window

    def pump(self, times=300):
        for _ in range(times):
            self.qapp.processEvents()


def _elapsed(action, *args):
    t0 = time.time()
    action(*args)
    return time.time() - t0


@pytest.fixture(scope='module')
def session(qapp):
    """One case and one plugin run, shared below -- so these tests run in the
    order written, each reading what the one before it left on the screen.
    """
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    patch = pytest.MonkeyPatch()
    patch.setattr(profilesPlugin, 'QInputDialog', StubDialog)
    StubDialog.asked = []
    root = RootWindow()
    root.show()
    qapp.processEvents()
    made = Session(qapp, root)
    try:
        made.openCase(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
        made.run(made.profilesEntry())
        # The window, its api and the frames the entries add are what keeps every
        # pyqtgraph view in this file alive -- which is what the application does
        # with `figureframes`, and what the ownership guard asks a test for.
        ownership.keep(made)
        yield made
    finally:
        patch.undo()


# --------------------------------------------------------------------------
# What the case answers, and what the plugin asks back
# --------------------------------------------------------------------------

def test_the_case_holds_occurrences_the_plugin_has_to_choose_between(session):
    # The stub above answers a question; this says the question is real here:
    # both IDSs this plugin plots on this case hold four occurrences each, and
    # the three others it claims to support hold none.
    assert {ids: session.view.occurrences.occurrencesOf(ids)
            for ids in ('equilibrium', 'core_profiles', 'edge_profiles',
                        'core_sources', 'core_transport')} \
        == {'equilibrium': OCCURRENCES, 'core_profiles': OCCURRENCES,
            'edge_profiles': [], 'core_sources': [], 'core_transport': []}


def test_the_plugin_asks_its_own_view_which_occurrence_to_plot(session):
    # Parented to the view whose node the menu was built on, and bounded by what
    # the case holds -- not by the data dictionary, and not by the spin box's
    # default ceiling of 2147483647.
    assert StubDialog.asked == [
        (session.view, 'Which occurrence of the equilibrium IDS?',
         'Occurrence:', OCCURRENCES[0], OCCURRENCES[0], OCCURRENCES[-1])]


# --------------------------------------------------------------------------
# What the entry builds
# --------------------------------------------------------------------------

def test_the_window_is_registered_held_and_shown(session):
    assert session.windowKey == WINDOW_KEY
    assert type(session.window).__name__ == 'VizProfiles'
    assert session.window.isVisible()
    assert WINDOW_KEY in session.api.GetFiguresKeys(
        FigureTypes.PROFILESPLOTTYPE)
    # Measured: a top-level window of its own. The figure frames are embedded in
    # the MDI area (T19); the plugin windows never were, and nothing hides them
    # with the shot view they were opened from.
    assert session.window.parent() is None


def test_the_window_drew_every_curve_the_case_holds(session):
    plots = plotsOf(session.window)
    assert session.window.tabWidget.count() == TABS
    assert len(plots) == PLOTS
    assert {type(p.getViewBox()).__name__ for p in plots} == \
        {'CustomizedViewBox'}
    curves = [item for p in plots for item in p.listDataItems()]
    assert len(curves) == PLOTS
    # The curves are not all one width: the boundary outlines are drawn over the
    # points of their own outline, not over the 101-point radial coordinate.
    widths = {}
    for curve in curves:
        widths[len(curve.getData()[0])] = widths.get(len(curve.getData()[0]),
                                                     0) + 1
    assert widths == WIDTHS
    titles = sorted(p.titleLabel.item.toPlainText() for p in plots)
    assert [t for t in titles if 'separatrix' in t] == \
        ['boundary_separatrix/outline/r', 'boundary_separatrix/outline/z']
    # The count above is the only way to see these plots. Asked of the window,
    # Qt answers no PlotItem at all -- an earlier probe read that as "the plugin
    # builds 0 plot", on a window that had drawn 41.
    assert session.window.findChildren(pyqtgraph.PlotItem) == []


def test_the_time_row_under_the_tabs_is_there(session):
    # Measured with the defect in place, this row did not exist at all: labelling
    # the slider formatted an IDSFloat0D with ':.2f' and took the rest of setUI
    # down with it.
    window = session.window
    assert window.slider_time.minimum() == 0
    assert window.slider_time.maximum() == SLICES - 1
    assert window.label_slider_tmin.text() == ('n<sub>t</sub> = %d; '
                                               't<sub>min</sub> = 32.13'
                                               % SLICES)
    assert window.label_slider_tmax.text() == 't<sub>max</sub> = 48.55'
    assert window.spinBox_timeIndex.maximum() == SLICES - 1
    assert window.lineEdit_timeValue.text() == '32.1336784362793'
    assert window.plotButton.text() == 'Plot'
    assert window.addNewTabsButton.text() == 'Add 1 tab of plots'


# --------------------------------------------------------------------------
# The menu a plot answers with, and what its entries build
# --------------------------------------------------------------------------

def test_right_clicking_a_plot_opens_a_menu(session):
    box = plotsOf(session.window)[0].getViewBox()
    menu = box.getMenu()
    session.pump()

    assert len(menu.actions()) == MENU_ACTIONS
    # The two choices this menu renames are asked of ViewBoxMenu.mouseModes, the
    # list pyqtgraph keeps: the "Mouse Mode" sub-menu it builds them in is a
    # local of its constructor, and measured on this window re-reading that
    # QMenu answers `RuntimeError: Internal C++ object
    # (PySide6.QtWidgets.QMenu) already deleted` -- the ownership trap T7 and
    # T21 met in our own menus, standing in a third party's constructor. The
    # actions are the objects the rename acts on, so the actions are what this
    # asserts on.
    assert [a.text() for a in box.menu.mouseModes] == ['Pan Mode',
                                                       'Area Zoom Mode']
    assert [a.text() for a in menu.actions()
            if a.text().startswith('Plot this in a new separate figure')] \
        == ['Plot this in a new separate figure']


def test_a_second_right_click_adds_nothing(session):
    # The rename and the custom entries are added once, behind `menuUpdate`; a
    # user right-clicking the same plot twice gets the same menu, not a menu
    # with its custom half repeated. Measured: 13 actions on each of three
    # calls, and the "Plot <quantity> to" sub-menu present once.
    box = plotsOf(session.window)[0].getViewBox()
    counts = []
    for _call in range(3):
        counts.append(len(box.getMenu().actions()))
        session.pump()
    assert counts == [MENU_ACTIONS] * 3
    assert [a for a in box.getMenu().actions()
            if a.menu() is box.contextMenu].__len__() == 1


def test_the_add_to_submenu_is_empty_while_there_is_nothing_to_add_to(session):
    box = plotsOf(session.window)[0].getViewBox()
    node = box.vizTreeNodesList[0]
    sub = subMenuOf(box, 'Plot %s to' % node.getName())

    # The sub-menu lists the existing figures this quantity shares coordinates
    # with. None exists yet, so the documented step 6 has exactly one way to be
    # taken: the entry that opens a new figure.
    assert list(sub.actions()) == []
    assert session.api.GetFiguresKeys(FigureTypes.FIGURETYPE) == []


def test_the_two_entries_build_the_two_figures_the_manual_promises(session):
    box = plotsOf(session.window)[0].getViewBox()
    menu = box.getMenu()
    built = []
    for label in ('Plot this in a new separate figure',
                  'Plot in a new separate figure (along time axis)'):
        action = [a for a in menu.actions() if a.text() == label]
        assert action, '%r is not in %r' % (label, [a.text()
                                                    for a in menu.actions()])
        before = set(session.api.figureframes)
        cost = _elapsed(action[0].trigger)
        session.pump()
        new = sorted(set(session.api.figureframes) - before)
        assert len(new) == 1, new
        built.append((new[0], session.api.figureframes[new[0]], cost))

    keys = [key for key, _figure, _cost in built]
    assert keys == ['Figure:1', 'Figure:2']
    assert session.api.GetFiguresKeys(FigureTypes.FIGURETYPE) == keys
    for key, figure, cost in built:
        assert type(figure).__name__ == 'QVizPlotWidget', key
        assert figure.isVisible()
        assert cost < 1.0, '%s cost %.2f s' % (key, cost)
    # One curve each: 101 points of the radial coordinate for the first, the 49
    # time slices of this occurrence for the second, starting where the slider's
    # label says the case starts.
    curves = [item.getData()
              for _key, figure, _cost in built
              for p in figure.findChildren(pyqtgraph.PlotWidget)
              for item in p.listDataItems()]
    assert [len(x) for x, _y in curves] == [max(WIDTHS), SLICES]
    assert curves[1][0][0] == pytest.approx(32.1336784362793, abs=1e-4)
    assert curves[1][0][-1] == pytest.approx(48.5483, abs=1e-3)


def test_the_add_to_submenu_then_lists_those_two_figures(session):
    box = plotsOf(session.window)[0].getViewBox()
    sub = subMenuOf(box, 'Plot %s to' % box.vizTreeNodesList[0].getName())

    assert [a.text() for a in sub.actions()] == ['Figure:1', 'Figure:2']
