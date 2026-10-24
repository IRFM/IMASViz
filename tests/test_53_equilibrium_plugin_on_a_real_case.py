# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The Equilibrium plugin run end to end on the reference case.

The question this file answers: is the plugin that has been sitting registered
since the beginning really wired to the IMAS surface the application now runs on,
or does it still speak to the generated data dictionary through a side door? It
turned out to be wired to the framework -- the contract, the catalog, `getEntries`
gated on the IDS name, the label read back by number -- and to have exactly one
side door left: `ids_read_multiprocess.py`, 64 lines opening a case through
`imas.ids(shot, run)` and `idd.open_env(user, machine, '3')`, the pre-reflection
Access Layer, called by no one but imported by the plugin. That file, the
59-line `test_equilibriumcharts_plugin.py` demo that could no longer run (it
built `PlotFrame` with the argument list of an older signature and ended in
`app.exec_()`), and the plugin's own `__main__` block are gone. What this file
pins is what runs in their place.

**The window was never built, and nothing knew it had been.** Measured on the
reference case through the catalog, choosing the entry the way the menu does:
`Plugin equilibriumcharts failed: TypeError: unsupported format string passed to
IDSFloat0D.__format__`, the plugin's `frame` never assigned, and `figureframes`
**empty** -- the label of the magnetic-surfaces chart formats the vacuum field
`r0`, which on IMAS-Python is an `IDSFloat0D`: a `numbers.Real` wrapper with
`__float__` and no `__format__`. It is the same defect `test_51` pins in the
Profiles plugin, in a second place. Two consequences followed, and both are
pinned below: the window the user clicked for never appeared, and because it was
never registered either, the Show/Hide and Delete menus had no kind to list it
under -- each click built another top-level window no menu could reach. The key
is now taken from `GetNextKeyForFigure`, the window is registered once it exists
(a refused run costs no key), and `FigureTypes.MENU_ORDER` carries the kind.

**Two more places where the current libraries refuse what the code asks.** The
slider's redraw and the "Enable Grid" checkbox both raised, and Qt swallowed it:
measured, `set_xdata(scalar)` answers `RuntimeError: x must be a sequence` on
matplotlib **3.11.2** (a vertical line carries two points), and `grid(b=True,
which=...)` answers `ValueError: keyword grid_b is not recognized` as soon as
another keyword follows -- so dragging the slider left the picture showing the
previous slice, and the checkbox did nothing at all. Both are pinned below, on
the effect rather than on the exception, because the exception never reached the
caller.

**A refusal is now a sentence, not a sentinel.** `DataGen` used to answer a
`status` of -1 and let `PlotFrame` return before building anything, while
`execute` showed the empty window anyway. It now raises `ValueError` naming what
the case lacks, and the catalog logs it: measured, patching the data source so it
answers nothing costs **0,03 s**, puts no window on screen and leaves in the log
"Unable to start the Equilibrium plugin: occurrence 0 of the 'equilibrium' IDS
could not be read from ...".

What the reference case answers (WEST 54924 run 0, data dictionary 3.35.0), in
absolute numbers. The case holds occurrences **[0, 1, 2, 3]** of `equilibrium`
and **[0]** of `wall`; the plugin reads occurrence 0 of each, and the plugin has
no occurrence question to ask -- unlike the Profiles plugin, it takes occurrence
0. That occurrence carries **49** time values and **49** time slices; its grid is
**7229** points and **13857** triangles, and -- measured, because the first branch
of `DataGen` looks elsewhere -- `time_slice[0].ggd[0].grid.space` holds **0**
elements while the grid lives in `grids_ggd[0].grid[0]`. The 1D profiles carry
**101** radial points, the limiter outline **164** points. The window holds **14**
axes: **6** time traces drawn over the 49 slices, **1** magnetic-surfaces chart
(1 tri-contour over the 7229-point grid, the 201-point boundary box, the magnetic
axis, the X point and the 164-point wall), and **7** radial profiles over 101
points. `catalog.run` returns in **6,73 s** cold -- it is the first reader of this
IDS in the process -- and **0,44 s** when the case has it in memory; the refused
run costs **0,03 s**. Note that these numbers do not depend on the `Ignore_GGD`
preference: that preference moves the shot view's *walk*, not `db_entry.get`, and
this plugin reads through `get`.
"""

import logging
import time

import pytest

from PySide6.QtWidgets import QMainWindow, QMdiArea, QMenu

from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizMainMenuController \
    import QVizMainMenuController
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizPlugins.QVizPluginCatalog import QVizPluginCatalog
from imasviz.VizUtils import FigureTypes, QVizPreferences

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip)
from support import ownership

IDS_NAME = 'equilibrium'
OTHER_ID_NAME = 'core_profiles'
PLUGIN = 'equilibriumcharts'
ENTRY_NUMBER = 0
ENTRY_LABEL = 'Equilibrium overview...'
KIND = FigureTypes.EQUILIBRIUMPLOTTYPE
FIRST_KEY = KIND + '1'
SECOND_KEY = KIND + '2'

# What the case answers, which is what the numbers below are read from.
OCCURRENCES = [0, 1, 2, 3]
WALL_OCCURRENCES = [0]
SLICES = 49
GRID_POINTS = 7229
TRIANGLES = 13857
RADIAL_POINTS = 101
WALL_POINTS = 164
AXES = 14
FIRST_TIME = 32.1336784362793
LAST_TIME = 48.54828643798828
MIDDLE_SLICE = 24
MIDDLE_TIME = 40.17202377319336

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
        self.setObjectName('IMASViz root window')
        self.MDI = QMdiArea(self)
        self.IMASdbBrowserWidget = BrowserStub()

    def getMDI(self):
        return self.MDI


def subMenuNamed(menu, title):
    for action in menu.actions():
        if action.menu() is not None and action.text() == title:
            return action.menu()
    return None


def actionNamed(menu, title):
    for action in menu.actions():
        if action.text() == title:
            return action
    return None


def figureMenus(view):
    """The Show/Hide and Delete menus, as the shot view builds them."""
    menu = QMenu()
    QVizSignalHandling(dataTreeView=view).menusShowHideAndDelete(menu)
    return menu


def elapsed(action, *args):
    t0 = time.time()
    result = action(*args)
    return result, time.time() - t0


class Session:
    """One application session: one case, one shot view, one plugin entry run.

    The view is opened the way the application opens it -- a source from the
    factory, the data dictionary the case was written with, then the api building
    the view -- because pinning the dictionary after the view exists moves the
    registry key under it. The catalog is the view's own, so the plugin is asked
    once, on the node the menu was built on.
    """

    def __init__(self, qapp, root):
        self.qapp = qapp
        self.root = root
        self.api = QVizMainMenuController(root).openShotView.api
        self.view = None
        self.catalog = None
        self.entry = None
        self.frame = None
        self.keys = []
        self.runCost = None

    def openCase(self, uri, ddVersion):
        source = QVizDataSourceFactory(None).create(uri)
        source.dd_version = ddVersion
        self.view = self.api.CreateDataTree(source).dataTreeView
        self.catalog = self.view.pluginCatalog or QVizPluginCatalog(self.view)
        self.view.pluginCatalog = self.catalog
        self.api.ShowDataTree(self.view)
        self.qapp.processEvents()

    def entriesOn(self, idsName):
        return self.catalog.entriesFor(self.view.IDSRoots[idsName])

    def equilibriumEntry(self):
        chosen = [entry for entry in self.entriesOn(IDS_NAME)
                  if entry.pluginName == PLUGIN]
        assert len(chosen) == 1, [entry.pluginName
                                  for entry in self.entriesOn(IDS_NAME)]
        self.entry = chosen[0]
        return self.entry

    def run(self, entry=None):
        """Choose the entry and take what it registers.

        This plugin builds its window inside `run` -- it walks the case on the GUI
        thread -- so the key is known as soon as the call returns, and no event
        pump is needed to see it.
        """
        before = set(self.api.figureframes)
        _refused, self.runCost = elapsed(self.catalog.run,
                                         entry or self.entry)
        self.qapp.processEvents()
        new = sorted(set(self.api.figureframes) - before)
        self.keys.extend(new)
        if new:
            self.frame = self.api.figureframes[new[-1]]
        return new


@pytest.fixture(scope='module')
def session(qapp):
    """One case, one entry, one run -- shared below, so these tests run in the
    order written and each reads what the one before it left on the screen.
    """
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    # Pinned, not inherited: what this preference moves is the shot view's walk,
    # and with the GGD of this IDS walked the case costs minutes (measured: 287 s
    # for the whole run, against 6,73 s here). It changes nothing the plugin
    # reads -- that goes through `db_entry.get`, which the preference does not
    # touch -- but it decides whether this file finishes inside the cap.
    QVizPreferences.Ignore_GGD = 1
    root = RootWindow()
    root.show()
    qapp.processEvents()
    made = Session(qapp, root)
    made.openCase(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
    made.run(made.equilibriumEntry())
    # The api holding `figureframes`, and the view holding that api, are what
    # keeps every matplotlib canvas in this file alive -- which is what the
    # application does, and what the ownership guard asks a test for.
    ownership.keep(made)
    yield made


# --------------------------------------------------------------------------
# What the case answers, and what the menu offers
# --------------------------------------------------------------------------

def test_the_case_holds_both_ids_the_plugin_reads(session):
    # The plugin reads occurrence 0 of `equilibrium` and of `wall`, and asks for
    # no answer from the user: these are the numbers its refusals are written
    # against.
    assert {ids: session.view.occurrences.occurrencesOf(ids)
            for ids in (IDS_NAME, 'wall')} \
        == {IDS_NAME: OCCURRENCES, 'wall': WALL_OCCURRENCES}
    equilibrium = session.view.dataSource.get(IDS_NAME, 0)
    assert len(equilibrium.time) == len(equilibrium.time_slice) == SLICES
    # Measured: the grid is not where the first branch of DataGen looks.
    assert len(equilibrium.time_slice[0].ggd[0].grid.space) == 0
    assert len(equilibrium.grids_ggd[0].grid[0].space[0]
               .objects_per_dimension[0].object) == GRID_POINTS
    outline = session.view.dataSource.get('wall', 0) \
        .description_2d[0].limiter.unit[0].outline
    assert len(outline.r) == len(outline.z) == WALL_POINTS


def test_the_entry_is_offered_on_the_equilibrium_root_only(session):
    # `getEntries` claims the node by IDS name, and the catalog reads the label
    # back by the number the entry carries.
    entry = session.entry
    assert (entry.number, entry.label) == (ENTRY_NUMBER, ENTRY_LABEL)
    assert PLUGIN not in [e.pluginName for e in session.entriesOn(OTHER_ID_NAME)]


# --------------------------------------------------------------------------
# The window the entry builds
# --------------------------------------------------------------------------

def test_the_window_is_registered_under_a_kind_the_menus_walk(session):
    assert session.keys == [FIRST_KEY]
    assert session.api.GetFiguresKeys(figureType=KIND) == [FIRST_KEY]
    assert session.api.GetFiguresCount(figureType=KIND) == 1
    # Measured before: nothing was registered at all, because the window was
    # never built. Registered, Show/Hide and Delete have a kind to list it under.
    assert KIND in [prefix for _label, _icon, prefix in FigureTypes.MENU_ORDER]
    assert type(session.frame).__name__ == 'PlotFrame'
    assert session.frame.isVisible()
    # Measured: like the Profiles window, a plugin window is not embedded in the
    # MDI area -- its parent is the shot view that opened it.
    assert session.frame.parent() is session.view
    assert session.api.mdiWindowOf(session.frame) is None


def test_the_window_is_titled_with_the_key_it_is_registered_under(session):
    # The title argument used to be accepted by this signature and used by no
    # statement: measured, the window sat on screen with an empty title bar while
    # the two menus listed it as 'EquiPlotView:1', so nothing tied a line of
    # those menus to a window -- and two of these windows look identical.
    assert session.frame.windowTitle() == 'Equilibrium charts [%s]' % FIRST_KEY


def test_the_arrays_hold_every_slice_and_point_the_case_holds(session):
    frame = session.frame
    assert frame.lenArrTimes == SLICES
    assert frame.Psi_val.shape == (SLICES, GRID_POINTS)
    assert frame.RNodes.shape == frame.ZNodes.shape == (GRID_POINTS,)
    assert frame.triKnots.shape == (TRIANGLES, 3)
    assert frame.prof_1d.shape == (SLICES, 9, RADIAL_POINTS)
    assert frame.wall.shape == (2, WALL_POINTS)
    assert len(frame.b0) == SLICES
    assert float(frame.timeEquiIDS[0]) == pytest.approx(FIRST_TIME)
    assert float(frame.timeEquiIDS[-1]) == pytest.approx(LAST_TIME)
    # The measured field: `r0` is an IDSFloat0D and `b0` an IDSNumericArray, so
    # neither can be formatted, and both are read here as numbers.
    assert float(frame.r0) == pytest.approx(2.42)
    assert float(frame.b0[0]) == pytest.approx(-3.7634230842275067)


def test_the_magnetic_surfaces_chart_is_labelled_with_the_field_it_draws(session):
    # This is the statement that used to raise, inside the constructor, and take
    # the whole window down with it -- `frame` never assigned, `figureframes`
    # empty, the log saying only "Plugin equilibriumcharts failed".
    title = session.frame.axes[6].get_title()
    assert title == 'Psi with B0=-3.763 [T] at R0=2.420 [m]'
    assert session.frame.axes[7].get_title() == 'Time = %s' % FIRST_TIME


def test_the_fourteen_axes_hold_the_curves_the_case_answers(session):
    frame = session.frame
    assert len(frame.axes) == AXES
    # The six time traces: one curve over the 49 slices, plus the vertical line
    # marking the slice the other charts are drawn for -- and on the q chart, a
    # second curve, since it draws q95 and q_axis together.
    for index in range(6):
        widths = set(len(line.get_xdata()) for line in frame.axes[index].lines)
        assert widths <= {2, SLICES}, (index, sorted(widths))
        assert SLICES in widths, index
    # The magnetic-surfaces chart: the psi contours over the 7229-point grid,
    # the boundary, the magnetic axis, the X point, the wall.
    assert len(frame.axes[6].collections) == 1
    assert type(frame.axes[6].collections[0]).__name__ == 'TriContourSet'
    assert sorted(len(line.get_xdata())
                  for line in frame.axes[6].lines) == [1, 1, 164, 201]
    assert frame.axes[6].get_title() != ''
    # The seven radial profiles, over the 101-point coordinate.
    for index in range(7, AXES):
        widths = set(len(line.get_xdata()) for line in frame.axes[index].lines)
        assert widths <= {2, RADIAL_POINTS}, (index, widths)
        assert RADIAL_POINTS in widths, index
    assert [frame.axes[7].get_ylabel(), frame.axes[13].get_ylabel()] == \
        ['q', "P'"]


def test_the_slider_moves_the_drawn_slice_and_its_labels(session):
    # The second site formatting the field, and the vertical line: measured, both
    # raised inside the slot, which Qt swallowed -- the labels changed and the
    # rest of the redraw did not, so the picture kept the previous slice.
    frame = session.frame
    _value, cost = elapsed(frame.slider_time.setValue, MIDDLE_SLICE)
    session.qapp.processEvents()
    assert frame.slider_time.minimum() == 0
    assert frame.slider_time.maximum() == SLICES - 1
    assert frame.axes[7].get_title() == 'Time = %s' % MIDDLE_TIME
    assert frame.axes[6].get_title() == 'Psi with B0=-3.763 [T] at R0=2.420 [m]'
    for line in frame.pltaxv:
        assert [float(x) for x in line.get_xdata()] == \
            pytest.approx([MIDDLE_TIME] * 2)
    assert cost < 5.0, 'redrawing one slice cost %.2f s' % cost


def test_the_grid_checkbox_lays_a_grid_and_takes_it_back_off(session):
    frame = session.frame
    frame.cb_grid.setChecked(True)
    session.qapp.processEvents()
    visible = sum(1 for line in frame.axes[6].xaxis.get_gridlines()
                  if line.get_visible())
    assert visible == 5
    frame.cb_grid.setChecked(False)
    session.qapp.processEvents()
    assert sum(1 for line in frame.axes[6].xaxis.get_gridlines()
               if line.get_visible()) == 0


def test_run_animates_the_slices_and_stop_stops_them(session):
    frame = session.frame
    frame.slider_time.setValue(MIDDLE_SLICE)
    session.qapp.processEvents()
    frame.on_draw_buttonRun()
    session.qapp.processEvents()
    assert frame.redraw_timer.isActive()
    # The tick the 400 ms timer would deliver, asked for directly rather than
    # waited for: it draws the slice the slider is on and hands the next one to
    # the following tick. This is the path the two refused calls above stand on.
    frame.on_redraw_timer()
    session.qapp.processEvents()
    assert frame.slider_time.value() == MIDDLE_SLICE
    assert frame.it_data == MIDDLE_SLICE + 1
    frame.on_draw_buttonStop()
    session.qapp.processEvents()
    assert not frame.redraw_timer.isActive()


def test_the_text_box_draws_two_times_on_the_time_traces(session):
    frame = session.frame
    frame.textbox.setText('35.0 44.0')
    frame.on_text_enter()
    session.qapp.processEvents()
    # One Ip trace, the vertical line, and one comparison curve per time asked
    # for: measured 5 lines, the axes not cleared between the two.
    assert len(frame.axes[0].lines) == 5
    frame.textbox.setText('')
    frame.on_text_enter()
    session.qapp.processEvents()
    assert len(frame.axes[0].lines) == 2


# --------------------------------------------------------------------------
# The window is a figure like the others: it is listed, hidden, deleted
# --------------------------------------------------------------------------

def test_a_second_click_gets_its_own_key(session):
    before = set(session.api.figureframes)
    new = session.run()
    assert new == [SECOND_KEY]
    assert set(session.api.figureframes) == before | {SECOND_KEY}
    # Measured: 0,44 s once the case holds the IDS, against 6,73 s for the first
    # run, which is the one reading it.
    assert session.runCost < 5.0, 'the second run cost %.2f s' % session.runCost


def test_the_two_menus_list_the_windows_and_delete_takes_one_away(session):
    menu = figureMenus(session.view)
    showHide = subMenuNamed(menu, 'Show/Hide')
    delete = subMenuNamed(menu, 'Delete')
    assert [a.text() for a in showHide.actions() if a.menu()] == ['Equilibrium']
    kindMenu = subMenuNamed(showHide, 'Equilibrium')
    assert [a.text() for a in kindMenu.actions()] == [FIRST_KEY, SECOND_KEY]
    assert [a.text() for a in subMenuNamed(delete, 'Equilibrium').actions()] \
        == [FIRST_KEY, SECOND_KEY, 'All']

    # The Show/Hide line addresses the window it names: this one is not embedded
    # in the MDI area, so the entry acts on the frame itself.
    actionNamed(kindMenu, FIRST_KEY).trigger()
    session.qapp.processEvents()
    assert not session.api.figureframes[FIRST_KEY].isVisible()
    actionNamed(kindMenu, FIRST_KEY).trigger()
    session.qapp.processEvents()
    assert session.api.figureframes[FIRST_KEY].isVisible()

    # Held before the line is triggered: Delete takes the key out of the
    # bookkeeping, so this is the only way left to ask what happened to the
    # window itself -- and asking it is the point, a key silently replaced by
    # another frame would pass the assertion above and leave a window on screen.
    frame = session.api.figureframes[FIRST_KEY]
    actionNamed(subMenuNamed(delete, 'Equilibrium'), FIRST_KEY).trigger()
    session.qapp.processEvents()
    assert session.api.GetFiguresKeys(figureType=KIND) == [SECOND_KEY]
    assert not frame.isVisible()
    assert session.api.GetFigureKeyOf(frame) is None


# --------------------------------------------------------------------------
# What a case that cannot answer costs
# --------------------------------------------------------------------------

def test_a_case_that_cannot_answer_is_refused_by_name(session, monkeypatch,
                                                       caplog):
    # `QVizIMASDataSource.get` logs the Access Layer error and answers None; a
    # plugin reading a node of that would answer AttributeError, which the
    # catalog reports as "failed" -- a broken plugin rather than an empty case.
    monkeypatch.setattr(session.view.dataSource, 'get',
                        lambda *args, **kwargs: None)
    before = set(session.api.figureframes)
    nextKeyBefore = session.api.GetNextKeyForFigure(KIND)
    with caplog.at_level(logging.ERROR, logger=session.view.uri):
        new = session.run()
    assert new == []
    assert set(session.api.figureframes) == before
    assert ("Unable to start the Equilibrium plugin: occurrence 0 of the "
            "'equilibrium' IDS could not be read from %s." % CASE_URI) \
        in caplog.text
    assert 'Plugin equilibriumcharts could not run:' in caplog.text
    # A key is taken before the window is built but the registry is only written
    # once that window exists, so a refused run hands the same number to the next
    # one -- measured, the refused call costs 0,03 s against 6,73 s for the run
    # that reads the case.
    assert session.api.GetNextKeyForFigure(KIND) == nextKeyBefore
