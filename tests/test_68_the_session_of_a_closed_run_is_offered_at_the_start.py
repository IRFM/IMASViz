# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The session the close writes, and the one the start offers.

``test_66`` pins the session file, ``test_67`` puts a session back on a real
case. What is pinned here is the pair of gestures around them: a run that ends
leaves its session behind without being asked, and the next run asks **once**
whether to take it back. Both halves matter -- a session nobody writes is a file
the user has to remember to save, and a session put back without a word opens
windows on a machine where the user closed them on purpose.

The main window is not built here: ``QVizMainWindow()`` is the whole application
(a central area, a start window, a maximized window on a screen), and what these
methods ask of it is one api and one answer. So they are driven as the plain
functions they are -- called with a ``self`` that answers ``sessionApi()`` --
which is also how the application reaches them: from ``closeEvent``, and from
``main()`` once the window is on screen.

The Yes/No question is a ``QInputDialog`` of the Access Layer helpers, so it is
patched at module level and recorded: a test that let it be asked off screen would
sit there until the 180 s cap, which is what the Profiles plugin's occurrence
question does to the tests that meet it.
"""

import logging

import pytest

from imasviz.VizGUI.QtVIZ_GUI import QVizMainWindow
from imasviz.VizGUI.VizConfigurations.QVizSessionFile import (
    QVizSessionFile, QVizSessionCase)
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.Viz_API import Viz_API

from support import ownership

UNREACHABLE = 'imas:hdf5?path=/no/such/case/0'
QUESTION = 'Restore the session IMASViz was closed with?'
GUI = __import__(QVizMainWindow.__module__, fromlist=['QVizSaveSession'])


@pytest.fixture(autouse=True)
def privateHome(tmp_path, monkeypatch):
    """The last session belongs to $HOME/.imasviz: keep it inside the test.

    Those helpers read ``HOME`` when they are called, which is what makes this
    enough -- the same pattern ``test_39`` uses for the configurations.
    """
    monkeypatch.setenv('HOME', str(tmp_path))
    return tmp_path


class AWindow:
    """What the four methods ask of the main window: the api of the session.

    The two commands are borrowed from the window they belong to -- a stand-in for
    the *window* is not a stand-in for the *command*, and the question is pinned
    against what the real command does with the file it is pointed at.
    """

    saveLastSession = QVizMainWindow.saveLastSession
    restoreLastSession = QVizMainWindow.restoreLastSession

    def __init__(self, api=None):
        self.api = api

    def sessionApi(self):
        return self.api


class AWindowThatCounts(AWindow):
    """The same, with the two commands counted instead of run.

    Used by ``closeEvent`` and by the question, whose promise is *which* of the
    two paths ran and how often -- not what the command does, pinned next door.
    """

    def __init__(self, api=None):
        AWindow.__init__(self, api)
        self.saved = 0
        self.restored = 0

    def saveLastSession(self):
        self.saved += 1

    def restoreLastSession(self):
        self.restored += 1


@pytest.fixture
def question(monkeypatch):
    """The Yes/No question: recorded, and answered with ``.answer``."""
    class Asked(list):
        answer = True

    def ask(question='?', caption=''):
        asked.append(question)
        return asked.answer

    asked = Asked()
    monkeypatch.setattr(QVizGlobalOperations, 'YesNo', ask)
    return asked


def aSessionOfOneCase(uri=UNREACHABLE):
    """A session file of the name the close uses, naming one case."""
    return QVizSessionFile(
        cases=[QVizSessionCase(uri=uri, dd_version='3.35.0', label=None,
                               loads=[], expanded=[], selection=[])],
        figures=[]).write(QVizSessionFile.lastSession())


# ---------------------------------------------------------------------------
# The start, and the question it asks.

@pytest.mark.ui
def test_a_start_with_no_session_behind_it_asks_nothing(question):
    """The first run, and every run that follows one closed by hand with nothing
    open: a question answered for nothing is a dialog too many."""
    assert QVizSessionFile.hasLastSession() is False

    assert QVizMainWindow.askForLastSession(AWindow(Viz_API())) is False
    assert question == []


@pytest.mark.ui
def test_the_session_a_run_left_behind_is_asked_about_once(question):
    aSessionOfOneCase()
    window = AWindowThatCounts(Viz_API())

    assert QVizMainWindow.askForLastSession(window) is True
    assert question == [QUESTION]
    assert window.restored == 1
    assert window.saved == 0


@pytest.mark.ui
def test_a_refusal_leaves_the_session_closed(question, caplog):
    """The refusal is an answer, not a failure: nothing is opened, the file stays
    where the *Load session* menu can find it, and the user is told so."""
    caplog.set_level(logging.INFO)
    aSessionOfOneCase()
    question.answer = False

    class Refused(AWindowThatCounts):
        def restoreLastSession(self):
            raise AssertionError('a refused session was restored anyway')

    assert QVizMainWindow.askForLastSession(Refused(Viz_API())) is False
    assert 'last session was left closed' in caplog.text
    assert 'File menu' in caplog.text
    assert QVizSessionFile.hasLastSession() is True


@pytest.mark.ui
def test_taking_the_offer_runs_the_restore_on_the_api_of_the_new_run(question,
                                                                    monkeypatch):
    """The restore is driven here, on the api this run was started with, and on
    that file -- not on a copy of the session.

    The command itself is recorded rather than run: what it does with the case a
    session names, reachable or not, is pinned in ``test_67``, on a real case.
    And the Access Layer is not asked for a case this process never opened:
    measured while writing this file, that call sat inside `openCase` past the
    180 s cap of this suite, in a process that had opened no case before it.
    """
    path = aSessionOfOneCase()
    asked = []

    class Recorded:
        def __init__(self, api, path=None):
            asked.append((api, path))

        def execute(self):
            return {}

    monkeypatch.setattr(GUI, 'QVizRestoreSession', Recorded)
    api = ownership.keep(Viz_API())

    assert QVizMainWindow.askForLastSession(AWindow(api)) is True
    assert asked == [(api, path)]


@pytest.mark.ui
def test_a_last_session_that_does_not_parse_costs_the_start_nothing(caplog):
    """The file is written by one release and read by another. A session that
    does not parse is named on the log, and the window the user is opening is not
    lost to it -- nor is the question the only thing that was asked."""
    with open(QVizSessionFile.lastSession(), 'w') as handle:
        handle.write('<IMASVizSession version="2"><Case')

    QVizMainWindow.restoreLastSession(AWindow(ownership.keep(Viz_API())))

    assert 'not a session file' in caplog.text


# ---------------------------------------------------------------------------
# The close, and what it leaves behind.

class AnEvent:
    """A close event: only the answer is read here."""

    def __init__(self):
        self.accepted = False
        self.ignored = False

    def accept(self):
        self.accepted = True

    def ignore(self):
        self.ignored = True


@pytest.mark.ui
def test_the_close_keeps_the_session_before_it_accepts_its_own_end(question):
    """Written in ``closeEvent``, and not from a ``destroyed`` handler: by the
    time Qt starts taking windows away, the session has already lost the windows
    it is supposed to describe."""
    window = AWindowThatCounts()
    event = AnEvent()

    QVizMainWindow.closeEvent(window, event)

    assert question == ['Exit IMAS_VIZ?']
    assert event.accepted is True and event.ignored is False
    assert window.saved == 1


@pytest.mark.ui
def test_a_close_answered_no_keeps_nothing(question):
    question.answer = False
    window = AWindowThatCounts()
    event = AnEvent()

    QVizMainWindow.closeEvent(window, event)

    assert event.ignored is True and event.accepted is False
    assert window.saved == 0


@pytest.mark.ui
def test_a_session_that_cannot_be_written_is_said_rather_than_lost_quietly(
        monkeypatch, caplog):
    """The user is leaving: the one thing they should hear is that the next start
    will not look like this one."""
    class Refused:
        def __init__(self, api, path=None):
            pass

        def execute(self):
            raise ValueError('No file was named to save the session to.')

    monkeypatch.setattr(GUI, 'QVizSaveSession', Refused)

    QVizMainWindow.saveLastSession(AWindow(Viz_API()))

    assert 'not kept for the next start' in caplog.text


@pytest.mark.ui
def test_a_window_holding_no_api_keeps_no_session(monkeypatch):
    """Nothing was opened, so nothing is written -- and no empty file is left for
    the next start to ask a question about."""
    class Never:
        def __init__(self, *args, **kwargs):
            raise AssertionError('a session was written for a window holding no '
                                 'api')

    monkeypatch.setattr(GUI, 'QVizSaveSession', Never)

    QVizMainWindow.saveLastSession(AWindow(None))

    assert QVizSessionFile.hasLastSession() is False


@pytest.mark.ui
def test_the_session_the_close_writes_is_a_session_the_folder_lists(qapp):
    """The whole path, through the writer the application uses: what the close
    leaves behind is a session the *Load session* menu lists under that name -- a
    session that cannot be opened by hand is a file, not a feature."""
    api = ownership.keep(Viz_API())
    QVizMainWindow.saveLastSession(AWindow(api))

    assert QVizSessionFile.hasLastSession() is True
    assert QVizSessionFile.listing() == ['last_session.vsess']
    assert QVizSessionFile.read(QVizSessionFile.lastSession()).cases == []


# ---------------------------------------------------------------------------
# Where the api of the session is reached.

class AStartWindow:
    def __init__(self, controller):
        self.central = AFrame(controller)

    def centralWidget(self):
        return self.central


class AFrame:
    def __init__(self, controller):
        self.mainMenuController = controller


class AController:
    def __init__(self, api):
        self.openShotView = AnOpenShotView(api)


class AnOpenShotView:
    def __init__(self, api):
        self.api = api


@pytest.mark.ui
def test_the_api_is_reached_where_the_open_gesture_put_it():
    """One api serves the session, and it lives where *Open* built it: the shot
    view the start window's menu holds. Reaching it rather than copying it is
    what keeps one bookkeeping of the windows, and one list of shot views."""
    window = AWindow()
    api = object()
    window.startWindow = AStartWindow(AController(api))

    assert QVizMainWindow.sessionApi(window) is api


@pytest.mark.ui
def test_a_start_window_holding_nothing_answers_no_api():
    """Half a start window is a normal state during the start-up sequence, so the
    chain is reached with ``getattr`` and answers None rather than an
    ``AttributeError`` in a close event."""
    class Nothing:
        def centralWidget(self):
            return None

    window = AWindow()
    window.startWindow = Nothing()

    assert QVizMainWindow.sessionApi(window) is None
