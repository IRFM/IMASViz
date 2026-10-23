# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The case views in the *Actions* menu: showing, hiding, deleting a shot view.

The manual's "Hide/Show/Delete DTV" is the only way a user gets a case view back
once it is out of the way, and it is the only way out of a case they opened by
mistake. Nothing in the suite drove it: ``QVizMainMenuController`` is named by no
test, and four test files rebuild the body of ``QVizOpenShotView.Open`` by hand
instead of calling it, so the rule that decision rests on -- **one view per case**
-- was pinned nowhere. T20 found that rule the hard way: ``data_entries`` is one
cache per case for the whole process, and a second view of a case shares it.

Measured on two cases of the same pulse directory (``west`` 54924 and 55799, run
0) before a line of this file was written. Building the menu costs **0,31 s** the
first time; with no view open it holds three entries, the two case-view ones
**disabled** and carrying **0** line each. Opening a case the way the start window
does costs **0,70 s** the first time and **0,15 s** for a second case, and puts
**1** frame, **1** view and **1** MDI window on the screen. Opening the same case
a second time costs **0,00 s** and changes nothing: the reuse rule holds, and what
``GetDTVFor`` hands ``ShowDataTree`` is the **view**, not the frame its docstring
promises.

Four measurements are why this file exists.

**The sub-menus die before anyone can click them.** ``menusShowHideAndDelete``
builds the two *Views* sub-menus with ``menu_showHide.addMenu('Views')``, and the
QMenu that call hands out belongs to the Python wrapper it comes back in: once
that method returns, the QAction still names a menu whose C++ object is gone.
Reading one back answers ``RuntimeError: Internal C++ object
(PySide6.QtWidgets.QMenu) already deleted`` -- which is timing-dependent, a
standalone probe kept the menu alive and a pytest run did not, the same trap T7
found in ``QVizPluginMenu``. Both sub-menus are now built with their parent at
construction.

**A hidden view never comes back.** Show/Hide hides the MDI window, and then
re-opening that case leaves both the frame and its window invisible -- twice
measured, through ``Open`` and through ``ShowDataTree`` directly. The view branch
of ``ShowDataTree`` shows the frame and never the window holding it, which is the
defect T19 fixed for figures and did not reach here.

**Deleting a view leaves its window in the area.** ``deleteLater()`` is commented
out with a TODO saying it "results in a bug when trying to run the delete DTV
feature the second time". Measured on Qt 6.6.3, it does not: hiding the window,
releasing it and dropping the frame costs **0,041 s**, deleting a second one and
re-opening the case afterwards answer no exception at all. What the commented
release costs is counted: four openings and two deletions leave **8** MDI windows
in the area for **2** live views. A released window only leaves
``QMdiArea.subWindowList()`` once the deferred delete events are delivered
(**2 -> 1** after ``sendPostedEvents``, where ``processEvents`` alone answered
**2**), so this file delivers them before counting.

**The window is asked what it is called.** All three entries branch on
``objectName() == "IMASViz root window"``. On the application's own window that
test is true -- measured, ``frame.window()`` there is the root window, not the
subwindow -- so the branch it skips, commented "e.g. when running examples", is
the one an MDI area without that name takes. Measured on such an area, Show/Hide
hid the **whole window** holding the area: the area itself went invisible. Asking
what a frame's window *is* (``Viz_API.mdiWindowOf``, T19) answers both cases.

The database browser is out of scope: the menu reads a username from it and hands
one name back, so the session carries a stub that records the calls. Everything
about the case views is real.
"""

import pytest

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QMainWindow, QMenu, QMdiArea, QMdiSubWindow

from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizMainMenuController \
    import QVizMainMenuController

from conftest import (CASE_URI, RANK3_CASE_URI, case_uri_or_skip,
                      rank3_case_uri_or_skip)
from support import ownership

ROOT_WINDOW = 'IMASViz root window'

# The two entries the gestures address, and the submenu each one puts its case
# views in. 'All' belongs to the deletion menu alone -- measured, the Show/Hide
# submenu carries the views and nothing else.
SHOW_HIDE = 'Show/Hide shot views'
DELETE = 'Delete'
VIEWS = 'Views'

pytestmark = [pytest.mark.case, pytest.mark.dd, pytest.mark.ui]


class BrowserStub:
    """The database browser, reduced to the two calls the menu makes.

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

    The name is what ``QVizMainMenuController`` compares against today; the
    session keeps it so that the branch the real application takes is the branch
    these tests drive.
    """

    def __init__(self):
        super().__init__()
        self.setObjectName(ROOT_WINDOW)
        self.MDI = QMdiArea(self)
        self.IMASdbBrowserWidget = BrowserStub()

    def getMDI(self):
        return self.MDI


class Session:
    """One application session, driven through its *Actions* menu.

    The controller owns the ``Viz_API`` the views are registered in -- it builds
    one through ``QVizOpenShotView`` the way ``QtVIZ_GUI`` does -- so a test never
    reaches past the gesture to a registry of its own.
    """

    def __init__(self, root, controller):
        self.root = root
        self.controller = controller
        self.api = controller.openShotView.api
        self.mdi = root.MDI

    def open(self, uri):
        """The start window's "Open" button, with the URI already typed."""
        self.controller.openShotView.Open(None, uri)

    def menu(self):
        menu = QMenu(self.root)
        ownership.keep(menu)
        self.controller.updateMenu(menu, self.root)
        return menu

    def frames(self):
        return list(self.api.GetDTVFrames())

    def windows(self):
        return list(self.mdi.subWindowList())

    def released(self, qapp):
        """Let Qt finish the deletions it deferred, so a window count is honest."""
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        qapp.processEvents()

    def actOn(self, qapp, menuTitle, label):
        """Trigger one entry of the menu, as the click does.

        The deferred deletions are delivered here, not left for a later test:
        a window Qt was asked to delete stays in `subWindowList()` until it is,
        so a count taken before that answers what the *previous* test left
        behind, not what this gesture did.
        """
        entry = subNamed(self.menu(), menuTitle)
        for action in subNamed(entry, VIEWS).actions():
            if action.text() == label:
                action.trigger()
                self.released(qapp)
                return
        raise AssertionError('%r is not a %s entry of %r'
                             % (label, menuTitle, [a.text() for a in
                                                   subNamed(entry, VIEWS).actions()]))


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


def subNamed(menu, title):
    for action in menu.actions():
        if action.text() == title and action.menu() is not None:
            return action.menu()
    raise AssertionError('no %r submenu in %r'
                         % (title, [a.text() for a in menu.actions()]))


def titles(menu):
    return [action.text() for action in menu.actions()]


def viewTitles(session, menuTitle):
    """What one entry of the menu offers, as the case labels it."""
    return titles(subNamed(subNamed(session.menu(), menuTitle), VIEWS))


# --------------------------------------------------------------------------
# Nothing open yet, and what the menu says about it
# --------------------------------------------------------------------------

def test_with_no_case_view_the_two_entries_are_there_and_disabled(session):
    menu = session.menu()

    assert titles(menu) == [SHOW_HIDE, DELETE, 'Add public databases']
    # A user has to see that there is nothing to hide or delete: the entries are
    # on the menu, disabled, and carry no line.
    for title in (SHOW_HIDE, DELETE):
        assert subNamed(menu, title).isEnabled() is False
        assert titles(subNamed(menu, title)) == []
    assert session.frames() == []
    assert session.windows() == []


def test_the_user_entry_follows_the_username_the_browser_answers(session, qapp):
    # Measured: an empty username means no entry at all -- the menu does not
    # offer to add databases of nobody.
    assert 'Add databases from user' not in ' '.join(titles(session.menu()))

    session.root.IMASdbBrowserWidget.username = 'g2lfleur'
    menu = session.menu()
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
    assert len(session.windows()) == 1
    frame = session.frames()[0]
    assert frame.isVisible()
    assert session.windows()[0].isVisible()
    # The window holding a frame is the subwindow it is embedded in -- and
    # `frame.window()`, which is what the menu compares today, is the root
    # window. Two different questions; only one of them identifies a window.
    assert frame.parent() is session.windows()[0]
    assert isinstance(session.api.mdiWindowOf(frame), QMdiSubWindow)
    assert session.api.mdiWindowOf(frame) is session.windows()[0]
    assert frame.window() is session.root


def test_the_same_case_opened_twice_stays_one_view(session, qapp):
    """The rule four test files side-step by rebuilding `Open`'s body."""
    session.open(CASE_URI)
    qapp.processEvents()

    assert len(session.frames()) == 1
    assert len(session.windows()) == 1
    assert session.frames()[0] is not None
    # The reuse answers the view, which is what ShowDataTree then shows -- its
    # docstring promises a frame, and does not answer one.
    key = session.frames()[0].dataTreeView.dataSource.getKey()
    assert session.api.GetDTVFor(key) is session.frames()[0].dataTreeView


def test_each_open_case_is_one_line_in_each_entry(session, qapp):
    session.open(RANK3_CASE_URI)
    qapp.processEvents()

    assert len(session.frames()) == 2
    labels = [frame.dataTreeView.dataSource.getLongLabel()
              for frame in session.frames()]
    assert viewTitles(session, SHOW_HIDE) == labels
    # 'All' is offered for deleting every view, never for hiding them.
    assert viewTitles(session, DELETE) == labels + ['All']


# --------------------------------------------------------------------------
# Show/Hide
# --------------------------------------------------------------------------

def test_showHide_hides_the_window_holding_the_view(session, qapp):
    label = session.frames()[0].dataTreeView.dataSource.getLongLabel()
    session.actOn(qapp, SHOW_HIDE, label)

    frame = session.frames()[0]
    window = session.api.mdiWindowOf(frame)
    assert window.isVisible() is False
    assert frame.isVisible() is False
    # The other case is untouched: one entry, one view.
    assert session.api.mdiWindowOf(session.frames()[1]).isVisible() is True

    session.actOn(qapp, SHOW_HIDE, label)
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
    session.actOn(qapp, SHOW_HIDE, label)
    assert session.api.mdiWindowOf(frame).isVisible() is False

    session.open(CASE_URI)
    qapp.processEvents()

    assert len(session.frames()) == 2
    assert session.api.mdiWindowOf(frame).isVisible() is True
    assert frame.isVisible() is True


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

    label = session.frames()[0].dataTreeView.dataSource.getLongLabel()
    session.actOn(qapp, SHOW_HIDE, label)

    assert session.windows()[0].isVisible() is False
    assert root.MDI.isVisible() is True
    session.actOn(qapp, SHOW_HIDE, label)
    assert session.windows()[0].isVisible() is True


# --------------------------------------------------------------------------
# Delete
# --------------------------------------------------------------------------

def test_deleting_a_view_takes_it_out_of_both_lists(session, qapp):
    frame = session.frames()[0]
    key = frame.dataTreeView.dataSource.getKey()
    label = frame.dataTreeView.dataSource.getLongLabel()
    frames = len(session.frames())
    views = len(session.api.DTVlist)
    session.actOn(qapp, DELETE, label)

    # Read the lists, not the frame: releasing the window deletes the frame and
    # everything in it, so asking a deleted object what its view was answers
    # "Internal C++ object already deleted" -- which is the behaviour, not a bug.
    assert len(session.frames()) == frames - 1
    assert len(session.api.DTVlist) == views - 1
    assert session.api.GetDTVFor(key) is None
    # The view is gone from the menu the next time it is built.
    assert label not in viewTitles(session, DELETE)


def test_deleting_a_view_releases_the_window_it_was_in(session, qapp):
    """Measured before the fix: 2 windows for 1 view, and 8 for 2 after a cycle.

    The release is deferred by Qt, so it is delivered before the count is taken;
    ``processEvents`` alone leaves the window listed, hidden.
    """
    before = len(session.windows())
    frame = session.frames()[0]
    label = frame.dataTreeView.dataSource.getLongLabel()
    session.actOn(qapp, DELETE, label)
    session.released(qapp)

    assert len(session.windows()) == before - 1


def test_delete_all_clears_both_lists_and_leaves_no_window(qapp):
    """The entry the QAction drives, `checked=False` into a parameter named `index`.

    Measured, it clears both lists -- because it always takes the first frame
    while the list shrinks, which is an accident of `False` being 0. And it
    releases every window it hides: measured before the fix, **2** stayed.
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

    allAction = [action for action in subNamed(subNamed(session.menu(), DELETE),
                                               VIEWS).actions()
                 if action.text() == 'All'][0]
    allAction.trigger()
    qapp.processEvents()
    session.released(qapp)

    assert session.frames() == []
    assert session.api.DTVlist == []
    assert session.windows() == []
    menu = session.menu()
    assert subNamed(menu, SHOW_HIDE).isEnabled() is False
    assert subNamed(menu, DELETE).isEnabled() is False


def test_re_opening_after_deleting_everything_costs_one_window_each(session, qapp):
    """The leak, counted: four openings and two deletions used to leave 8 windows."""
    session.open(CASE_URI)
    session.open(RANK3_CASE_URI)
    qapp.processEvents()
    session.released(qapp)

    assert len(session.frames()) == 2
    assert len(session.windows()) == 2
    assert all(window.isVisible() for window in session.windows())


# --------------------------------------------------------------------------
# A case that cannot be opened
# --------------------------------------------------------------------------

def test_an_unreachable_case_is_refused_in_the_log_and_opens_nothing(session,
                                                                    caplog):
    frames = len(session.frames())
    windows = len(session.windows())

    session.open('imas:hdf5?path=/afs/eufus.eu/g2itmdev/user/g2lfleur/public/'
                 'imasdb/west/3/999999/0')

    assert len(session.frames()) == frames
    assert len(session.windows()) == windows
    assert 'master.h5' in caplog.text
