# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The *File* menu of the application window, and the preference behind the auto-save.

Two things the user asked for, and both were about reaching a feature at all.

**The session menu was on no menu.** ``Save session`` and ``Load session`` have
been built by ``QVizMainMenuController.menuSession`` since T40a, and the only
caller was ``GUIFrame.showPopUpMenu`` -- the right-click pop-up of the *start
panel*, where the entries hang under no title. The application window has no menu
bar at all (measured before this file: ``QVizMainWindow`` never calls
``menuBar()``, and the only menu bars in the package are a shot view's
``Actions``/``Node Selection Actions``/``Plot windows`` and the plugins' own),
while ``manual/other_GUI_features.rst`` sent the user to
:menuselection:`Actions --> Save session` and ``askForLastSession`` told the one
who refused to "open it from the File menu". Neither menu existed.

**The automatic session was not asked for.** Every close wrote
``last_session.vsess`` and the next start asked a question about it, whatever the
user wanted. It is a preference now (``Auto_save_session``, off), and the one
question the preference answers is asked once for both ends of it: the write at
the close and the offer at the start.

Two facts decided the shape of the code, both measured before writing it:

* ``Viz_API`` is **not** a singleton -- ``QVizOpenShotView.__init__`` makes one --
  so the menu's session entries are asked of the *start window's* controller, the
  one the *Open* gesture drives. A controller of the menu's own would hold a
  second bookkeeping holding none of the windows on screen, and *Save session*
  would write an empty file while *Load session* would open windows nothing
  displays.
* ``QMenu.clear()`` removes actions and **keeps the objects**, and a sub-menu
  built with its parent (the only shape that survives -- see T0, T7, T21) stays a
  child of the menu. Refilling on ``aboutToShow`` without deleting would pile one
  pair of lines per opening on a menu that shows two.
"""

import gc
import os
import weakref

import pytest

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QMenu, QMenuBar

from imasviz.VizGUI.QtVIZ_GUI import QVizMainWindow, autoSavesSession
from imasviz.VizGUI.VizConfigurations.QVizSessionFile import QVizSessionFile
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizFileMenu import \
    QVizFileMenu
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizMainMenuController \
    import QVizMainMenuController
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizUtils.QVizGlobalValues import QVizPreferences
from imasviz.Viz_API import Viz_API

from support import ownership

SAVE = 'Save session'
LOAD = 'Load session'
QUIT = 'Quit'
GUI = __import__(QVizMainWindow.__module__, fromlist=['autoSavesSession'])
CONTROLLER_MODULE = __import__(QVizMainMenuController.__module__,
                               fromlist=['QVizSaveSession'])


@pytest.fixture(autouse=True)
def privateHome(tmp_path, monkeypatch):
    """The sessions and the preferences file both live under $HOME/.imasviz.

    ``QVizPreferences.Auto_save_session`` is pinned back by ``monkeypatch``, so a
    test that turns it on cannot leave the next one -- or the rest of the suite --
    with an application that saves behind its user's back. The default the suite
    runs on is the default of the application: off.
    """
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setattr(QVizPreferences, 'Auto_save_session', 0)
    return tmp_path


class AWindow:
    """What the *File* menu and the window's own methods ask of the window.

    A plain Python object, not a widget: the menu asks the window for one thing
    -- to close itself -- and ``QVizMainWindow()`` would be the whole application
    (start window, MDI, maximized window), as ``test_68`` says of the same
    methods. The real methods are borrowed, so what is pinned runs on the
    production code.
    """

    addFileMenu = QVizMainWindow.addFileMenu
    sessionMenuEntries = QVizMainWindow.sessionMenuEntries
    startMenuController = QVizMainWindow.startMenuController
    sessionApi = QVizMainWindow.sessionApi

    def __init__(self, controller=None):
        self.bar = ownership.keep(QMenuBar())
        self.startWindow = AStartWindow(controller)
        self.closed = 0

    def menuBar(self):
        return self.bar

    def close(self):
        self.closed += 1
        return True


class AStartWindow:
    def __init__(self, controller):
        self.central = AFrame(controller)

    def centralWidget(self):
        return self.central


class AFrame:
    def __init__(self, controller):
        self.mainMenuController = controller


class AController:
    """A menu controller of the shape the window reaches: an api, and the entries.

    ``menuSession`` is recorded rather than run -- the real one is the subject of
    the tests below, driven through a real ``QVizMainMenuController``.
    """

    def __init__(self, api=None):
        self.api = api if api is not None else Viz_API()
        self.openShotView = AnOpenShotView(self.api)
        self.askedFor = []

    def menuSession(self, menu, listenerWidget):
        self.askedFor.append(menu)
        menu.addAction('Save session')


class AnOpenShotView:
    def __init__(self, api):
        self.api = api


class BrowserStub:
    def getActiveUsername(self):
        return ''


class StubMainWindow:
    """What ``QVizMainMenuController`` asks of the window it belongs to.

    A widget answers ``window()`` for the dialog parent, so the stand-in does: the
    controller holds the frame of the start window, and a stand-in that cannot
    spell that contract is a stub missing a call, not a production guard.
    """

    def __init__(self, mdi=None):
        self.IMASdbBrowserWidget = BrowserStub()

    def getMDI(self):
        return None

    def window(self):
        return self


class AnEvent:
    def __init__(self):
        self.accepted = False
        self.ignored = False

    def accept(self):
        self.accepted = True

    def ignore(self):
        self.ignored = True


@pytest.fixture
def question(monkeypatch):
    """The Yes/No question of the close and of the start, recorded."""
    class Asked(list):
        answer = True

    def ask(question='?', caption=''):
        asked.append(question)
        return asked.answer

    asked = Asked()
    monkeypatch.setattr(QVizGlobalOperations, 'YesNo', ask)
    return asked


def aRealController():
    """The controller of the start window, with the api of the session."""
    return QVizMainMenuController(StubMainWindow())


def aFileMenu(controller=None, window=None):
    """A *File* menu built the way the window builds it, on a bar of its own."""
    window = window or AWindow(controller)
    window.addFileMenu()
    return window, window.fileMenu


def openMenu(menu):
    """Open the menu the way Qt does, so the rebuild is the one the user gets."""
    menu.aboutToShow.emit()


def labels(menu):
    return [action.text() for action in menu.actions()]


def subMenuOf(menu, title):
    for action in menu.actions():
        submenu = action.menu()
        if submenu is not None and submenu.title() == title:
            return submenu
    return None


# ---------------------------------------------------------------------------
# The menu on the bar.

@pytest.mark.ui
def test_the_file_menu_is_on_the_window_its_menu_bar_holds(qapp):
    """The bar is the point of this: an entry the user sees without knowing a
    gesture. Before, the application window had no menu bar at all."""
    window, fileMenu = aFileMenu(aRealController())

    assert [menu.title() for menu in window.bar.findChildren(QMenu)] == \
        [QVizFileMenu.TITLE]
    assert SAVE in labels(window.bar.actions()[0].menu())
    assert QUIT in labels(window.bar.actions()[0].menu())


@pytest.mark.ui
def test_a_window_that_holds_no_session_yet_offers_no_load_menu(qapp):
    """Nothing saved: an empty list leaves no sub-menu on screen, and *Save
    session* is still there to make the first one."""
    window, fileMenu = aFileMenu(aRealController())

    assert labels(fileMenu.menu) == [SAVE, QUIT]
    assert subMenuOf(fileMenu.menu, LOAD) is None


@pytest.mark.ui
def test_the_file_menu_lists_the_sessions_the_folder_holds(qapp):
    QVizSessionFile().write(QVizSessionFile.named('weekend'))
    QVizSessionFile().write(QVizSessionFile.named('monday'))

    window, fileMenu = aFileMenu(aRealController())

    load = subMenuOf(fileMenu.menu, LOAD)
    assert load is not None
    assert [action.text() for action in load.actions()] \
        == ['monday.vsess', 'weekend.vsess']


@pytest.mark.ui
def test_the_session_saved_a_minute_ago_is_on_the_list_without_restarting(qapp):
    """The list is refilled on every opening, and not once at start-up -- which is
    the whole point of saving a session by name: coming back to it in the run that
    saved it, and in the one after."""
    window, fileMenu = aFileMenu(aRealController())
    assert subMenuOf(fileMenu.menu, LOAD) is None

    QVizSessionFile().write(QVizSessionFile.named('monday'))
    openMenu(fileMenu.menu)

    load = subMenuOf(fileMenu.menu, LOAD)
    assert load is not None
    assert [action.text() for action in load.actions()] == ['monday.vsess']


@pytest.mark.ui
def test_refilling_the_menu_leaves_no_duplicate_line_on_it(qapp):
    """``QMenu.clear()`` removes actions and keeps the objects, and a sub-menu
    parented on the menu stays its child -- so a refill that does not delete would
    show the same entries twice, then three times."""
    QVizSessionFile().write(QVizSessionFile.named('monday'))
    window, fileMenu = aFileMenu(aRealController())

    for _ in range(4):
        openMenu(fileMenu.menu)

    assert labels(fileMenu.menu) == [SAVE, LOAD, QUIT]
    assert len(subMenuOf(fileMenu.menu, LOAD).actions()) == 1


@pytest.mark.ui
def test_quitting_closes_the_application_window(qapp):
    """Not ``QApplication.quit``: closing the window is what runs its close event,
    and that is where the confirmation and the session live."""
    window, fileMenu = aFileMenu(aRealController())
    quit_line = [action for action in fileMenu.menu.actions()
                 if action.text() == QUIT][0]

    quit_line.trigger()

    assert window.closed == 1


@pytest.mark.ui
def test_quitting_answers_the_standard_shortcut(qapp):
    window, fileMenu = aFileMenu(aRealController())
    quit_line = [action for action in fileMenu.menu.actions()
                 if action.text() == QUIT][0]

    assert quit_line.shortcut() == QKeySequence.Quit


@pytest.mark.ui
def test_a_window_holding_no_controller_offers_a_menu_that_quits_only(qapp):
    """Half a start window is a normal state during the start-up sequence. A menu
    bar is not where an ``AttributeError`` should land, and *Quit* is worth
    drawing on its own."""
    window = AWindow(controller=None)

    window.addFileMenu()

    assert window.sessionMenuEntries() is None
    assert labels(window.fileMenu.menu) == [QUIT]


# ---------------------------------------------------------------------------
# Whose session the menu saves.

@pytest.mark.ui
def test_the_entries_are_asked_of_the_controller_the_open_gesture_built(qapp):
    """One api serves the session, and it lives in the start window's controller
    (`Viz_API` is not a singleton). Asking that controller is what keeps *Save
    session* and the screen talking about the same windows."""
    controller = AController()
    window = AWindow(controller)

    window.addFileMenu()

    assert window.sessionMenuEntries().__self__ is controller
    assert window.startMenuController() is controller
    assert window.sessionApi() is controller.api
    assert controller.askedFor == [window.fileMenu.menu]


@pytest.mark.ui
def test_saving_from_the_menu_writes_the_session_of_the_controller(qapp,
                                                                   monkeypatch):
    """The gesture end to end: the name asked in the slot the user clicked, the
    session written on the api that owns the windows, and the list refilled with
    what it just wrote."""
    class AskedForName(list):
        @staticmethod
        def getText(parent, title, label, text=''):
            return ['monday', True]

    saved = []
    realSave = CONTROLLER_MODULE.QVizSaveSession

    class Recorded:
        def __init__(self, api, name=None, path=None):
            saved.append((api, name, path))
            self.wrapped = realSave(api, name=name, path=path)

        def execute(self):
            return self.wrapped.execute()

    monkeypatch.setattr(CONTROLLER_MODULE, 'QInputDialog', AskedForName)
    monkeypatch.setattr(CONTROLLER_MODULE, 'QVizSaveSession', Recorded)
    controller = aRealController()
    window, fileMenu = aFileMenu(controller)
    apiOfTheSession = window.sessionApi()
    assert apiOfTheSession is controller.openShotView.api

    save_line = [action for action in fileMenu.menu.actions()
                 if action.text() == SAVE][0]
    save_line.trigger()
    openMenu(fileMenu.menu)

    assert saved == [(apiOfTheSession, 'monday', None)]
    assert os.path.exists(QVizSessionFile.named('monday')) is True
    assert [action.text() for action in subMenuOf(fileMenu.menu, LOAD).actions()] \
        == ['monday.vsess']


# ---------------------------------------------------------------------------
# What the helper holds of the window (the T25 rule).

@pytest.mark.ui
def test_the_file_menu_does_not_keep_its_window_alive():
    """The helper is kept by the window's own bookkeeping; holding the window back
    would make a cycle, and on this Qt stack a widget freed by the cyclic collector
    is freed while Qt still owes it a paint event."""
    window = AWindow(AController())
    window.addFileMenu()

    assert isinstance(window.fileMenu._window, weakref.ref)
    assert window.fileMenu._window() is window

    reference = weakref.ref(window)
    del window
    gc.collect()
    assert reference() is None


@pytest.mark.ui
def test_quitting_on_a_window_that_is_gone_answers_nothing():
    """The connection outlives nothing: asked after the window is gone, *Quit*
    says no rather than raising in a slot nobody can answer."""
    window = AWindow(AController())
    window.addFileMenu()
    fileMenu = window.fileMenu
    del window
    gc.collect()

    assert fileMenu.quit() is False


# ---------------------------------------------------------------------------
# The preference: off by default, and both ends of it at once.

@pytest.mark.ui
def test_the_session_is_not_kept_behind_the_user_s_back_by_default():
    assert QVizPreferences.Auto_save_session == 0
    assert autoSavesSession() is False


@pytest.mark.ui
def test_a_close_keeps_nothing_when_the_preference_is_off(question):
    window = AWindow(AController())
    saved = []
    window.saveLastSession = lambda: saved.append(True)
    event = AnEvent()

    QVizMainWindow.closeEvent(window, event)

    assert question == ['Exit IMAS_VIZ?']
    assert event.accepted is True and event.ignored is False
    assert saved == []
    assert QVizSessionFile.hasLastSession() is False


@pytest.mark.ui
def test_a_start_asks_nothing_when_the_preference_is_off(question, caplog):
    """Even a file left by an older run does not bring the question back: the
    preference answers both ends, and half a behaviour the user turned off is
    still the behaviour they turned off."""
    QVizSessionFile().write(QVizSessionFile.lastSession())
    window = AWindow(AController())
    restored = []
    window.restoreLastSession = lambda: restored.append(True)

    assert QVizMainWindow.askForLastSession(window) is False

    assert question == []
    assert restored == []


@pytest.mark.ui
def test_the_preference_turns_both_halves_on(question, monkeypatch):
    monkeypatch.setattr(QVizPreferences, 'Auto_save_session', 1)
    window = AWindow(AController())
    QVizSessionFile().write(QVizSessionFile.lastSession())
    saved, restored = [], []
    window.saveLastSession = lambda: saved.append(True)
    window.restoreLastSession = lambda: restored.append(True)
    event = AnEvent()

    QVizMainWindow.closeEvent(window, event)
    asked = QVizMainWindow.askForLastSession(window)

    assert saved == [True]
    assert asked is True and restored == [True]
    assert question == ['Exit IMAS_VIZ?',
                        'Restore the session IMASViz was closed with?']


@pytest.mark.ui
def test_the_preference_is_read_from_the_file_the_manual_documents(
        tmp_path, monkeypatch):
    """A line in :file:`~/.imasviz/preferences`, like the four options before it:
    uncommented and 1 turns it on, commented out leaves it off."""
    folder = tmp_path / '.imasviz'
    folder.mkdir()
    preferences = folder / 'preferences'
    monkeypatch.setattr(QVizPreferences, 'userPreferencesInitialized', False)

    preferences.write_text('#Auto_save_session=1\nIgnore_GGD=1\n')
    QVizPreferences().build()
    assert QVizPreferences.Auto_save_session == 0

    monkeypatch.setattr(QVizPreferences, 'userPreferencesInitialized', False)
    preferences.write_text('Auto_save_session=1\nIgnore_GGD=1\n')
    QVizPreferences().build()
    assert QVizPreferences.Auto_save_session == 1
    assert autoSavesSession() is True
