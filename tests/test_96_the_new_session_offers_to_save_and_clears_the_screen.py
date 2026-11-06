# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The *New session* entry of the *File* menu: one question, then a clean screen.

The gesture a run that wants to start over asks. It sits on top of the
session entries because it is the same question a run ends with -- what to
keep before the screen goes -- and it answers with the two halves the
application already owns:

* the save, through the *same* name dialog and the *same* command as
  *Save session* (`askSessionName` was cut out of `saveSession` for exactly
  the two callers it now serves), so a session kept this way comes back the
  way any other saved one does;
* the clear, through `Viz_API.closeAll` -- the same shape as the *Delete*
  lines of the *Windows* menu, which is what keeps a new session from being
  a second, divergent way of closing a window.

What the two halves owe each other, and what this file pins:

* a **Yes** is a save *and* a clear, in that order: the session is written
  under a name the user gave before any window leaves the screen;
* a **No** is a clear *only*: nothing is written, and the name dialog is
  never opened, because a save the user refused is not a save a disk should
  make for them;
* a refusal of either half keeps the *whole* screen and says why in the log
  panel: a name the user does not give, a session the disk refuses -- in
  both the windows stay where they are, because what the gesture promised
  was "save, then clear", and half of that did not happen;
* a screen that holds no window answers with no question: nothing to save,
  nothing to clear, and a question over nothing is an answer the user gives
  for nothing.

Two stand-ins for the windows are plain Python, and `shiboken6.isValid`
answers **True** for them (measured on this Qt) -- the answer `openWindows`
and `releaseLeftBehind` need to see the stubs as alive -- while the close
path only asks `parent()`, `hide` and `deleteLater` of them, the surface
this file records and asserts on. The real save already runs end to end in
`test_75` on an empty api, which is why the save here is recorded rather
than run: the subject is the flow the gesture decides -- *whether* it
saves, *under which name*, and *what it clears* -- not the file the command
writes. A real widget that is never shown is a paint-queue hazard this suite
already guards against (`tests/support/ownership.py`); these frames are
never going on the screen.
"""

import logging

import pytest

from PySide6.QtWidgets import QMenuBar

from imasviz.VizGUI.QtVIZ_GUI import QVizMainWindow
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizMainMenuController \
    import QVizMainMenuController
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizUtils.QVizGlobalValues import QVizPreferences

from support import ownership

# The package re-exports the class under the module's own name, so `import ...
# as` binds the *class*; the module is where the names this test patches
# live, and it is reached by the exact device `test_75` uses.
CONTROLLER_MODULE = __import__(QVizMainMenuController.__module__,
                               fromlist=['QVizSaveSession'])

NEW_SESSION = 'New session'
SAVE = 'Save session'
URI = 'imas:hdf5?path=/afs/cluster/imasdb/users/nobody/west/shot/0'


@pytest.fixture(autouse=True)
def privateHome(tmp_path, monkeypatch):
    """The sessions and the preferences file both live under $HOME/.imasviz."""
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setattr(QVizPreferences, 'Auto_save_session', 0)
    return tmp_path


@pytest.fixture
def question(monkeypatch):
    """The one Yes/No question the gesture asks, with the answer it gets."""
    class Asked(list):
        answer = True

    asked = Asked()

    def ask(question='?', caption=''):
        asked.append(question)
        return asked.answer

    monkeypatch.setattr(QVizGlobalOperations, 'YesNo', ask)
    return asked


def patchNameDialog(monkeypatch, name, ok=True):
    """The session-name dialog, answering a fixed name and a fixed ok.

    Returns the questions it was asked, so a test can say "the dialog was
    never opened" and not only "no file was written".
    """
    asked = []

    class Named:
        @staticmethod
        def getText(parent, title, label, text=''):
            asked.append([parent, title])
            return [name, ok]

    monkeypatch.setattr(CONTROLLER_MODULE, 'QInputDialog', Named)
    return asked


def recordSaves(monkeypatch, raised=None):
    """The session command as this gesture makes it: recorded, not run.

    `raised` is what the disk may answer `execute` with, and the record
    holds the api and the name the flow decided to give it.
    """
    saved = []

    class Saved:
        def __init__(self, api, name=None, path=None):
            saved.append((api, name, path))

        def execute(self):
            if raised is not None:
                raise raised
            return True

    monkeypatch.setattr(CONTROLLER_MODULE, 'QVizSaveSession', Saved)
    return saved


# ------------------------------------------------------------------- the stand-ins

class BrowserStub:
    def getActiveUsername(self):
        return ''


class StubMainWindow:
    """What `QVizMainMenuController` asks of the window it belongs to."""

    def __init__(self):
        self.IMASdbBrowserWidget = BrowserStub()

    def getMDI(self):
        return None

    def window(self):
        return self


def aController():
    """The session's controller: its api is the bookkeeping the gesture clears."""
    return QVizMainMenuController(StubMainWindow())


class StubWindow:
    """A window's content as `closeWindow` knows it, with the calls recorded.

    The close path only asks this small surface of a frame -- `parent()`,
    `hide`, `deleteLater` -- and the test asserts on whether each window was
    closed **once**: that is the whole of the "a window no one closes twice"
    rule of `closeAll`.
    """

    def __init__(self):
        self._parent = None
        self.hides = 0
        self.deletes = 0

    def parent(self):
        return self._parent

    def hide(self):
        self.hides += 1

    def deleteLater(self):
        self.deletes += 1


class StubSource:
    """The reads the session paths make of a case view's data source.

    `openWindows` asks the long label and the uri; `defaultSessionName` --
    the name the dialog pre-fills -- asks the short label.
    """

    def __init__(self, uri):
        self.uri = uri
        self.forgetCases = 0

    def getLongLabel(self):
        return URI.split('path=')[-1]

    def getShortLabel(self):
        return 'shot 0'

    def forget_case(self):
        self.forgetCases += 1


class StubTree:
    def __init__(self, source):
        self.dataSource = source
        self.selectedSignalsDict = {}


class StubView(StubWindow):
    """A case view: the tree and the data source `RemoveDTVFrame` asks of it."""

    def __init__(self, source):
        super(StubView, self).__init__()
        self.dataTreeView = StubTree(source)


def aScreen(api):
    """One case view and one curve figure, both in the bookkeeping they hold.

    The two kinds of window a real run holds that are not parented anywhere:
    the case view and the figure of the MDI area.
    """
    view = StubView(StubSource(URI))
    api.DTVframeList.append(view)
    api.DTVlist.append(view.dataTreeView)
    curve = StubWindow()
    api.figureframes['Plot1'] = curve
    return view, curve


def pluginOn(api, view):
    """The third kind of window a real run holds: the one a plugin draws *inside*
    the view its entry ran on -- the one that dies with the view, and the one
    the case close is the only thing allowed to forget.
    """
    plugin = StubWindow()
    plugin._parent = view
    api.figureframes['PlotView1'] = plugin
    return plugin


class AWindow:
    """The two methods of the window the *File* menu hangs from, borrowed.

    `test_75` says why the real ones are borrowed rather than the
    application built: a test that assembles start window, MDI and
    maximized frame to reach one menu line is testing a machine that is not
    under test.
    """

    addFileMenu = QVizMainWindow.addFileMenu
    sessionMenuEntries = QVizMainWindow.sessionMenuEntries
    startMenuController = QVizMainWindow.startMenuController

    def __init__(self, controller):
        self.bar = ownership.keep(QMenuBar())
        self.startWindow = AStartWindow(controller)

    def menuBar(self):
        return self.bar


class AStartWindow:
    def __init__(self, controller):
        self.central = AFrame(controller)

    def centralWidget(self):
        return self.central


class AFrame:
    def __init__(self, controller):
        self.mainMenuController = controller


# ---------------------------------------------------------------- the menu line

@pytest.mark.ui
def test_the_new_session_sits_on_top_of_the_file_menu(qapp):
    """One gesture, on the one bar the user can see, above the entries it
    supersedes: clearing the screen is what both *Save session* and
    *Load session* keep, so it sits above them."""
    window = AWindow(aController())
    window.addFileMenu()

    labels = [action.text() for action in window.fileMenu.menu.actions()]
    assert labels[:2] == [NEW_SESSION, SAVE]
    line = [action for action in window.fileMenu.menu.actions()
            if action.text() == NEW_SESSION][0]
    assert line.isEnabled()


# ------------------------------------------------------------- the question, saved

@pytest.mark.ui
def test_a_yes_is_a_save_then_a_clear(qapp, question, monkeypatch):
    """The whole of the promise: the session is written under a name the user
    gave, and only then does any window leave the screen -- the case view
    first, so the plugin window parented on it is forgotten exactly once, by
    the close that took its parent, and the curve figure that stands in the
    MDI area gets its own line in the clear."""
    controller = aController()
    api = controller.openShotView.api
    view, curve = aScreen(api)
    plugin = pluginOn(api, view)
    saved = recordSaves(monkeypatch)
    asks = patchNameDialog(monkeypatch, 'monday')

    closed = controller.newSession()

    assert question == ['Save the current session before starting a new one?']
    assert saved == [(api, 'monday', None)]
    assert asks and asks[0][1] == 'Save session'
    assert closed == [view, curve]
    assert api.DTVframeList == [] and api.DTVlist == [] and \
        api.figureframes == {}
    assert view.deletes == 1 and curve.deletes == 1
    assert plugin.deletes == 0, \
        'the plugin window dies with the view it is parented on: closeAll ' \
        'forgets its key and must not close what the case close already took'
    assert view.dataTreeView.dataSource.forgetCases == 1


@pytest.mark.ui
def test_a_no_is_a_clear_without_the_save(qapp, question, monkeypatch):
    """A save the user did not answer is not a save a disk should make: the
    name dialog is never opened and the command never made, but the screen
    is still cleared -- the clear was the request, the save was the offer.
    """
    question.answer = False
    controller = aController()
    api = controller.openShotView.api
    view, curve = aScreen(api)
    plugin = pluginOn(api, view)
    saved = recordSaves(monkeypatch)
    asks = patchNameDialog(monkeypatch, 'monday')

    closed = controller.newSession()

    assert question == ['Save the current session before starting a new one?']
    assert saved == []
    assert asks == [], 'the name dialog of a save that was refused'
    assert closed == [view, curve]
    assert api.DTVframeList == [] and api.figureframes == {}
    assert view.deletes == 1 and curve.deletes == 1
    assert plugin.deletes == 0, \
        'the plugin window dies with the view it is parented on: closeAll ' \
        'forgets its key and must not close what the case close already took'


# ------------------------------------------------- the refusals keep the screen

@pytest.mark.ui
def test_a_name_refused_keeps_the_whole_screen(qapp, question, monkeypatch,
                                               caplog):
    """A name the user does not give is a save that did not happen, and a save
    that did not happen cannot be the half of a promise a screen is given up
    on: every window stays, and the refusal is where the user reads it."""
    controller = aController()
    api = controller.openShotView.api
    view, curve = aScreen(api)
    plugin = pluginOn(api, view)
    saved = recordSaves(monkeypatch)
    patchNameDialog(monkeypatch, None, ok=False)

    with caplog.at_level(logging.ERROR):
        closed = controller.newSession()

    assert saved == []
    assert closed is False
    assert api.DTVframeList == [view] and \
        api.DTVlist == [view.dataTreeView]
    assert api.figureframes == {'Plot1': curve, 'PlotView1': plugin}
    assert view.deletes == 0 and curve.deletes == 0 and plugin.deletes == 0
    assert 'no name' in caplog.text


@pytest.mark.ui
def test_a_save_the_disk_refuses_keeps_the_whole_screen(qapp, question,
                                                        monkeypatch, caplog):
    """A save the user answered and the disk refused is closer to a broken
    promise than a kept one: the screen the user gave up for that session is
    not spent on the refusal, and the reason the disk gave is the one the
    user reads."""
    controller = aController()
    api = controller.openShotView.api
    view, curve = aScreen(api)
    plugin = pluginOn(api, view)
    recordSaves(monkeypatch, raised=ValueError('The folder refuses the name.'))
    patchNameDialog(monkeypatch, 'monday')

    with caplog.at_level(logging.ERROR):
        closed = controller.newSession()

    assert closed is False
    assert api.DTVframeList == [view]
    assert api.figureframes == {'Plot1': curve, 'PlotView1': plugin}
    assert view.deletes == 0 and curve.deletes == 0 and plugin.deletes == 0
    assert 'The folder refuses the name.' in caplog.text
    assert 'was not started' in caplog.text


# ------------------------------------------------------------ the empty screen

@pytest.mark.ui
def test_an_empty_screen_is_answered_with_no_question(qapp, question, caplog):
    """Nothing on the screen is already a new session: no question is asked
    over nothing, nothing is cleared, and the answer is said out loud
    rather than spent on a click that would answer nothing."""
    controller = aController()
    api = controller.openShotView.api

    with caplog.at_level(logging.INFO):
        closed = controller.newSession()

    assert question == []
    assert closed is False
    assert api.DTVframeList == [] and api.figureframes == {}
    assert 'already a new session' in caplog.text
