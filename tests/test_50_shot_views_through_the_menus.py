# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The case views in the *Windows* menu: showing, hiding, deleting a shot view.

The manual's "Hide/Show/Delete DTV" is the only way a user gets a case view back
once it is out of the way, and it is the only way out of a case they opened by
mistake. ``QVizOpenShotView.Open`` -- the start window's *Open* button -- was
driven by no test, and four test files rebuild its body by hand instead of calling
it, so the rule that decision rests on (one view per case) was pinned nowhere.
T20 found that rule the hard way: ``data_entries`` is one cache per case for the
whole process, and a second view of a case shares it.

Where those commands are found changed with T52, and the change is the point of
this file. They used to sit on the right-click pop-up of the *start panel*, built
by ``QVizMainMenuController.menusShowHideAndDelete`` -- the only place in the
application able to bring a hidden case view back, on a panel that looks like a
form and is nowhere anybody right-clicks looking for a menu. They are on the
*Windows* menu now, together with the figures, filled by ``QVizWindowMenu`` from
``Viz_API.openWindows``. So the pop-up is pinned empty of windows, and the menu is
pinned holding the case views -- and one property of the new placement gets a test
it could not have before: hiding a case view takes its menu bar off the screen
with it, so the gesture has to live somewhere the hidden view does not own.

Measured on two cases of the same pulse directory (``west`` 54924 and 55799, run
0). Opening a case the way the start window does costs **0,70 s** the first time
and **0,15 s** for a second case, and puts **1** frame, **1** view and **1** MDI
window on the screen. Opening the same case a second time costs **0,00 s** and
changes nothing: the reuse rule holds, and what ``GetDTVFor`` hands
``ShowDataTree`` is the **view**, not the frame its docstring promises.

Four measurements still stand, and are why these tests are shaped as they are.

**A sub-menu built with ``addMenu(title)`` dies before anyone can click it.** The
QMenu that call hands out belongs to the Python wrapper it comes back in: once the
builder returns, the QAction still names a menu whose C++ object is gone. Reading
one back answers ``RuntimeError: Internal C++ object (PySide6.QtWidgets.QMenu)
already deleted`` -- timing-dependent, a standalone probe kept it alive and a
pytest run did not, the same trap T7 found in ``QVizPluginMenu``. Every sub-menu
here is built with its parent at construction, and the menu is rebuilt on
``aboutToShow``.

**A hidden view does not come back by itself.** ``ShowDataTree`` shows the frame
and not the window holding it -- the T19 defect, which had not reached the shot
view -- so both stayed invisible through ``Open`` and through ``ShowDataTree``
alike.

**Deleting a view releases its window.** ``deleteLater()`` sat commented out under
a TODO claiming it "results in a bug when trying to run the delete DTV feature the
second time"; on Qt 6.6.3 it does not. What the commented release was costing:
four openings and two deletions left **8** MDI windows for **2** live views. A
released window only leaves ``QMdiArea.subWindowList()`` once the deferred deletes
are delivered (**2 -> 1** after ``sendPostedEvents``, where ``processEvents`` alone
answered **2**), so this file delivers them before counting.

**The window is asked what it is, not what it is called.** All three entries used
to branch on ``objectName() == "IMASViz root window"``. Measured on an MDI area
without that name, Show/Hide hid the **whole window** holding the area, and every
other view in it went with it. Asking what a frame's parent *is*
(``Viz_API.mdiWindowOf``, T19) answers both cases, and the second window class is
driven here on purpose.

The database browser is out of scope: the pop-up reads a username from it and hands
one name back, so the session carries a stub that records the calls. Everything
about the case views is real.
"""

import pytest

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QMainWindow, QMenu, QMdiArea, QMdiSubWindow

from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizMainMenuController \
    import QVizMainMenuController
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizWindowMenu import \
    QVizWindowMenu
from imasviz.VizUtils.QVizGlobalValues import QVizPreferences

from conftest import (CASE_URI, RANK3_CASE_URI, case_uri_or_skip,
                      rank3_case_uri_or_skip)
from support import ownership

ROOT_WINDOW = 'IMASViz root window'
DELETE = QVizWindowMenu.DELETE
ALL = QVizWindowMenu.ALL

pytestmark = [pytest.mark.case, pytest.mark.dd, pytest.mark.ui]


class BrowserStub:
    """The database browser, reduced to the two calls the pop-up makes.

    ``updateMenu`` reads the active username from it and the two entries hand a
    name back to ``addUserDB``. The browser itself -- what it lists, where it
    reads it from -- is not what this file looks at.
    """

    def __init__(self):
        self.username = ''
        self.added = []

    def getActiveUsername(self):
        return self.username

    def addUserDB(self, username):
        self.added.append(username)


class RootWindow(QMainWindow):
    """The window the application builds, named the way the application names it.

    The name is what the api used to compare against; the session keeps it so that
    the branch the real application takes is the branch these tests drive.
    """

    def __init__(self):
        super().__init__()
        self.setObjectName(ROOT_WINDOW)
        self.MDI = QMdiArea(self)
        self.IMASdbBrowserWidget = BrowserStub()

    def getMDI(self):
        return self.MDI


class Session:
    """One application session, driven through the menu that lists its windows.

    The controller owns the ``Viz_API`` the views are registered in -- it builds
    one through ``QVizOpenShotView`` the way ``QtVIZ_GUI`` does -- so a test never
    reaches past the gesture to a registry of its own. ``windows()`` is what
    ``QVizMainWindow.addWindowMenu`` and ``QVizDataTreeView.addMenuBar`` both hang:
    one ``QVizWindowMenu`` over that same api.
    """

    def __init__(self, root, controller):
        self.root = root
        self.controller = controller
        self.api = controller.openShotView.api
        self.mdi = root.MDI

    def open(self, uri):
        """The start window's "Open" button, with the URI already typed."""
        self.controller.openShotView.Open(None, uri)

    def popUp(self):
        """The right-click pop-up of the start panel."""
        menu = QMenu(self.root)
        ownership.keep(menu)
        self.controller.updateMenu(menu, self.root)
        return menu

    def windows(self):
        """The *Windows* menu, filled as a menu bar fills it."""
        menu = QMenu(self.root)
        ownership.keep(menu)
        QVizWindowMenu(menu, self.api).show()
        return menu

    def lines(self, menu=None):
        """The window lines the run holds, walking any sub-menu they sit in.

        Since the *Windows* menu groups its cases and their figures into
        sub-menus, a window's line is no longer necessarily at the top level.
        These helpers walk in; the fixed entries (the *All* / *Delete* /
        *Disposition* families and the *Hide/Close others* top-level gestures)
        are left out so the reading is the window's, not the run's.
        """
        base = menu if menu is not None else self.windows()
        fixed = (QVizWindowMenu.NO_WINDOW, QVizWindowMenu.SHOW_ALL,
                 QVizWindowMenu.HIDE_ALL, DELETE,
                 QVizWindowMenu.NEXT, QVizWindowMenu.PREVIOUS,
                 QVizWindowMenu.HIDE_OTHERS, QVizWindowMenu.CLOSE_OTHERS,
                 QVizWindowMenu.DISPOSITION, QVizWindowMenu.ISOLATE,
                 QVizWindowMenu.CLOSE_CASE)
        # Sub-menus that hold gestures, not the state of a window -- the
        # *Delete* and *Disposition* families. A window's line lives in its
        # case's sub-menu (or at the top for a case-less one), so walk those,
        # and leave the gesture sub-menus, and their *All*, alone.
        gestureSub = (DELETE, QVizWindowMenu.DISPOSITION)
        out = []
        def walk(m):
            for action in m.actions():
                if action.isSeparator():
                    continue
                if action.menu() is not None:
                    if action.text() not in gestureSub:
                        walk(action.menu())
                elif action.text() not in fixed:
                    out.append((action.text(), action.isChecked()))
        walk(base)
        return out

    def delete(self, menu=None):
        for action in (menu if menu is not None else self.windows()).actions():
            if action.text() == DELETE and action.menu() is not None:
                return action.menu()
        raise AssertionError('no %r sub-menu' % DELETE)

    def frames(self):
        return list(self.api.GetDTVFrames())

    def subWindows(self):
        return list(self.mdi.subWindowList())

    def released(self, qapp):
        """Let Qt finish the deletions it deferred, so a window count is honest."""
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        qapp.processEvents()

    def actOn(self, qapp, label, menu=None):
        """Trigger one window's line of the *Windows* menu, as the click does.

        The line may sit inside a case's sub-menu (the menu groups its windows
        by case now), so the search walks down; a separator or a sub-menu header
        is skipped. The deferred deletions are delivered here, not left for a
        later test: a window Qt was asked to delete stays in `subWindowList()`
        until it is, so a count taken before that answers what the *previous*
        test left behind.
        """
        target = menu if menu is not None else self.windows()

        def find(m):
            for action in m.actions():
                if action.isSeparator():
                    continue
                if action.menu() is not None:
                    found = find(action.menu())
                    if found is not None:
                        return found
                elif action.text() == label:
                    return action
            return None

        action = find(target)
        if action is None:
            raise AssertionError('%r is not a line of %r'
                                 % (label, [a.text() for a in target.actions()]))
        action.trigger()
        self.released(qapp)
        return action

    def labels(self):
        return [frame.dataTreeView.dataSource.getLongLabel()
                for frame in self.frames()]


@pytest.fixture(scope='module')
def session(qapp):
    """A root window, an MDI area, a menu controller -- and no case view yet."""
    if case_uri_or_skip() is None or rank3_case_uri_or_skip() is None:
        pytest.skip('both cases are needed: %s and %s' % (CASE_URI, RANK3_CASE_URI))
    root = RootWindow()
    ownership.keep(root)
    controller = QVizMainMenuController(root)
    ownership.keep(controller)
    root.show()
    qapp.processEvents()
    return Session(root, controller)


@pytest.fixture(autouse=True)
def closeBoxKeepsTheWindow(monkeypatch):
    """The default of the application: the box hides, it does not delete."""
    monkeypatch.setattr(QVizPreferences, 'Close_button_deletes', 0)


def titles(menu):
    return [action.text() for action in menu.actions()]


# --------------------------------------------------------------------------
# The pop-up that used to hold these commands
# --------------------------------------------------------------------------

def test_the_start_pop_up_offers_databases_and_no_windows(session, qapp):
    menu = titles(session.popUp())
    assert menu == ['Add public databases']
    # And it stays that way once cases are open: the windows of the run are not
    # the business of a pop-up on the start panel. This is where the case views
    # used to be -- the only place in the application able to bring a hidden view
    # back, on a panel nobody right-clicks looking for a menu.
    session.open(CASE_URI)
    qapp.processEvents()
    assert titles(session.popUp()) == ['Add public databases']


def test_the_user_entry_follows_the_username_the_browser_answers(session, qapp):
    # Measured: an empty username means no entry at all -- the menu does not
    # offer to add databases of nobody.
    assert 'Add databases from user' not in ' '.join(titles(session.popUp()))

    session.root.IMASdbBrowserWidget.username = 'g2lfleur'
    menu = session.popUp()
    assert titles(menu)[-1] == 'Add databases from user g2lfleur'
    # And the entry hands that name to the browser, which is all the entry does.
    [action for action in menu.actions()
     if action.text() == 'Add databases from user g2lfleur'][0].trigger()
    qapp.processEvents()
    assert session.root.IMASdbBrowserWidget.added == ['g2lfleur']


# --------------------------------------------------------------------------
# Opening a case the way the start window does
# --------------------------------------------------------------------------

def test_opening_a_case_puts_one_view_in_one_window(session, qapp):
    session.open(CASE_URI)
    qapp.processEvents()

    assert len(session.frames()) == 1
    assert len(session.api.DTVlist) == 1
    assert len(session.subWindows()) == 1
    frame = session.frames()[0]
    assert frame.isVisible()
    assert session.subWindows()[0].isVisible()
    # The window holding a frame is the subwindow it is embedded in -- and
    # `frame.window()`, which is what the code compared until T19, is the root
    # window. Two different questions; only one of them identifies a window.
    assert frame.parent() is session.subWindows()[0]
    assert isinstance(session.api.mdiWindowOf(frame), QMdiSubWindow)
    assert session.api.mdiWindowOf(frame) is session.subWindows()[0]
    assert frame.window() is session.root


def test_the_same_case_opened_twice_stays_one_view(session, qapp):
    """The rule four test files side-step by rebuilding `Open`'s body."""
    session.open(CASE_URI)
    qapp.processEvents()

    assert len(session.frames()) == 1
    assert len(session.subWindows()) == 1
    assert session.frames()[0] is not None
    # The reuse answers the view, which is what ShowDataTree then shows -- its
    # docstring promises a frame, and does not answer one.
    key = session.frames()[0].dataTreeView.dataSource.getKey()
    assert session.api.GetDTVFor(key) is session.frames()[0].dataTreeView


def test_each_open_case_is_one_line_on_the_menu(session, qapp):
    session.open(RANK3_CASE_URI)
    qapp.processEvents()

    assert len(session.frames()) == 2
    labels = session.labels()
    assert [label for label, _ in session.lines()] == labels
    # The state is the mark: both are on the screen.
    assert [checked for _, checked in session.lines()] == [True, True]
    # The case views and the figures share that list, grouped by kind -- and
    # closing a whole kind at a time is offered once per group, not once per view.
    assert titles(session.delete()) == labels + [ALL]


# --------------------------------------------------------------------------
# Show/Hide
# --------------------------------------------------------------------------

def test_showHide_hides_the_window_holding_the_view(session, qapp):
    label = session.labels()[0]
    session.actOn(qapp, label)

    frame = session.frames()[0]
    window = session.api.mdiWindowOf(frame)
    assert window.isVisible() is False
    assert frame.isVisible() is False
    # The other case is untouched: one line, one view.
    assert session.api.mdiWindowOf(session.frames()[1]).isVisible() is True

    # The line says so, because the menu is drawn again on every opening.
    assert session.lines() == [(label, False), (session.labels()[1], True)]

    session.actOn(qapp, label)
    assert window.isVisible() is True
    assert frame.isVisible() is True


def test_a_hidden_view_comes_back_when_its_case_is_opened_again(session, qapp):
    """The manual's "show" is not the only way back: opening the case is the other.

    Measured before the fix: the frame and its window stayed invisible through
    ``Open`` and through ``ShowDataTree`` alike -- the view branch shows the
    frame, and a frame is not what hides it.
    """
    frame = session.frames()[0]
    label = frame.dataTreeView.dataSource.getLongLabel()
    session.actOn(qapp, label)
    assert session.api.mdiWindowOf(frame).isVisible() is False

    session.open(CASE_URI)
    qapp.processEvents()

    assert len(session.frames()) == 2
    assert session.api.mdiWindowOf(frame).isVisible() is True
    assert frame.isVisible() is True


def test_hiding_the_last_view_does_not_take_the_gesture_with_it(session, qapp):
    """The property the old placement could not have.

    A case view owns the menu bar its *Windows* entry hangs on, so hiding that
    view takes the entry off the screen with it. The application bar is filled by
    the same object over the same api, and it is on screen whatever the user is
    looking at -- which is the argument that moved the session entries to *File*
    (T46), and it is what brings a hidden view back.
    """
    labels = session.labels()
    hidden = [session.api.mdiWindowOf(frame) for frame in session.frames()]
    for label in labels:
        session.actOn(qapp, label)
    assert all(window.isVisible() is False for window in hidden)
    assert [checked for _, checked in session.lines()] == [False] * len(labels)

    # A second menu over the same api -- the application bar's, which no hidden
    # view can hide -- still names both and puts them back.
    applicationBar = QMenu(session.root)
    ownership.keep(applicationBar)
    QVizWindowMenu(applicationBar, session.api, applicationBar=True).show()
    assert [label for label, _ in session.lines(applicationBar)] == labels
    session.actOn(qapp, labels[0], menu=applicationBar)
    assert hidden[0].isVisible() is True


def test_hiding_a_view_leaves_the_area_itself_on_screen(qapp):
    """The branch the application does not take: an MDI area without that name.

    Measured, Show/Hide then hid the window holding the area -- the area itself
    went invisible, and with it every other view in it.
    """
    class PlainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.MDI = QMdiArea(self)
            self.IMASdbBrowserWidget = BrowserStub()

        def getMDI(self):
            return self.MDI

    root = PlainWindow()
    ownership.keep(root)
    controller = QVizMainMenuController(root)
    ownership.keep(controller)
    root.show()
    qapp.processEvents()
    session = Session(root, controller)
    session.open(CASE_URI)
    qapp.processEvents()

    label = session.labels()[0]
    session.actOn(qapp, label)

    assert session.subWindows()[0].isVisible() is False
    assert root.MDI.isVisible() is True
    session.actOn(qapp, label)
    assert session.subWindows()[0].isVisible() is True


# --------------------------------------------------------------------------
# Delete
# --------------------------------------------------------------------------

def test_deleting_a_view_takes_it_out_of_both_lists(session, qapp):
    frame = session.frames()[0]
    key = frame.dataTreeView.dataSource.getKey()
    label = frame.dataTreeView.dataSource.getLongLabel()
    frames = len(session.frames())
    views = len(session.api.DTVlist)
    session.actOn(qapp, label, menu=session.delete())

    # Read the lists, not the frame: releasing the window deletes the frame and
    # everything in it, so asking a deleted object what its view was answers
    # "Internal C++ object already deleted" -- which is the behaviour, not a bug.
    assert len(session.frames()) == frames - 1
    assert len(session.api.DTVlist) == views - 1
    assert session.api.GetDTVFor(key) is None
    # The view is gone from the menu the next time it is built.
    assert label not in [text for text, _ in session.lines()]


def test_deleting_a_view_releases_the_window_it_was_in(session, qapp):
    """Measured before the fix: 2 windows for 1 view, and 8 for 2 after a cycle.

    The release is deferred by Qt, so it is delivered before the count is taken;
    ``processEvents`` alone leaves the window listed, hidden.
    """
    before = len(session.subWindows())
    label = session.labels()[0]
    session.actOn(qapp, label, menu=session.delete())
    session.released(qapp)

    assert len(session.subWindows()) == before - 1


def test_the_all_line_clears_both_lists_and_leaves_no_window(qapp):
    """One line closes every window of its kind -- the entry the old ``All`` was.

    Measured before the fix, the old entry took an ``index`` no signal ever
    passed: the QAction answers a ``checked`` flag, so it was fed ``False``,
    behaved as index 0, and emptied the lists only because the loop bound shrank
    underneath it. It also left **2** windows on screen.
    """
    root = RootWindow()
    ownership.keep(root)
    controller = QVizMainMenuController(root)
    ownership.keep(controller)
    root.show()
    qapp.processEvents()
    session = Session(root, controller)
    session.open(CASE_URI)
    session.open(RANK3_CASE_URI)
    qapp.processEvents()
    assert len(session.frames()) == 2

    alls = [action for action in session.delete().actions()
            if action.text() == ALL]
    assert len(alls) == 1
    alls[0].trigger()
    session.released(qapp)

    assert session.frames() == []
    assert session.api.DTVlist == []
    assert session.subWindows() == []
    # With nothing open the menu is there, enabled, and names itself: one
    # disabled line, not a bar entry that comes and goes under the hand.
    assert [a.text() for a in session.windows().actions()] == [
        QVizWindowMenu.NO_WINDOW]


def test_re_opening_after_deleting_everything_costs_one_window_each(session,
                                                                   qapp):
    """The leak, counted: four openings and two deletions used to leave 8 windows."""
    session.open(CASE_URI)
    session.open(RANK3_CASE_URI)
    qapp.processEvents()
    session.released(qapp)

    assert len(session.frames()) == 2
    assert len(session.subWindows()) == 2
    assert all(window.isVisible() for window in session.subWindows())


# --------------------------------------------------------------------------
# A case that cannot be opened
# --------------------------------------------------------------------------

def test_an_unreachable_case_is_refused_in_the_log_and_opens_nothing(session,
                                                                    caplog):
    frames = len(session.frames())
    windows = len(session.subWindows())

    session.open('imas:hdf5?path=/afs/eufus.eu/g2itmdev/user/g2lfleur/public/'
                 'imasdb/west/3/999999/0')

    assert len(session.frames()) == frames
    assert len(session.subWindows()) == windows
    assert 'master.h5' in caplog.text
