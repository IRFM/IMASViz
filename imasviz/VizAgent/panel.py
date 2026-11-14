# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The agent panel: a window the user talks to, in the *Windows* menu.

A top-level window (not in the MDI area), like the Profiles panel and
the Equilibrium plugin window. It is registered in ``figureframes``
under ``Agent:1`` so the *Windows* menu sees it alongside the other
windows of the session.

The LLM call runs in a worker thread (the GUI must stay responsive
during the call); the gestures run on the GUI thread through
``GuiDispatcher`` (the same bridge the MCP surface uses).

Refusals are shown in the transcript with their ``REFUSAL`` prefix,
the style of this repository: a named refusal is a line the user reads,
not a silent failure.
"""

import threading

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from imasviz.VizAgent.QVizPromptHistory import QVizPromptHistory

from imasviz.Viz_API import QVizClosableWindow
from imasviz.VizUtils import FigureTypes, QVizGlobalValues


class QVizAgentPanel(QVizClosableWindow, QWidget):
    """One agent window: the transcript on top, and below it the prompt
    box and the run button, so a scrolling answer stays readable.

    ``main_window`` is the ``QVizMainWindow``, or None in the test suite.
    ``api`` is the ``Viz_API`` the gestures drive -- the session's own
    when this is the in-app agent, so the *Windows* menu sees the
    panel alongside the user's figures.
    ``agent`` is the ``AgentLoop`` instance that does the work.
    """

    def __init__(self, main_window=None, api=None, agent=None):
        QVizClosableWindow.__init__(self)
        # Top-level, like the Profiles panel (a `QMainWindow` with no parent):
        # it is a window of the session -- in the *Windows* menu -- and not a
        # child widget of the main window, so `main_window` is a reference for
        # context, not a Qt parent (a parent would change what a `show` here is).
        super(QVizClosableWindow, self).__init__()

        self.main_window = main_window
        self.api = api
        self.agent = agent
        self._run_thread = None

        # The key: the next available Agent: number in the session.
        self.figureKey = self._nextKey(api)

        # --- layout -----------------------------------------------------
        # The transcript is on top and the input box is below it: the
        # answer scrolls into sight while the prompt stays at the bottom
        # of the window, with the button row after the input.
        layout = QVBoxLayout(self)

        # Transcript
        self.transcript = QPlainTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setPlaceholderText('Le transcript apparaît ici.')
        self.transcript.setLineWrapMode(QPlainTextEdit.NoWrap)
        layout.addWidget(self.transcript)

        # Prompt history: a dropdown of the prompts the run has typed,
        # newest first, so a run that started after a new session reaches
        # them still -- a new session takes this panel off the screen but
        # the list it left behind is what the run asks back.
        self.promptHistoryBox = QComboBox()
        self.promptHistoryBox.activated.connect(self._onHistorySelected)
        layout.addWidget(self.promptHistoryBox)
        self._loadHistory()

        # Prompt
        self.promptEdit = QPlainTextEdit()
        self.promptEdit.setPlaceholderText(
            'Demandez à l\'agent d\'ouvrir un cas, de tracer, de chercher…')
        self.promptEdit.setMaximumHeight(80)
        layout.addWidget(self.promptEdit)

        # Buttons
        self.buttonRow = QHBoxLayout()
        buttons = self.buttonRow
        self.runButton = QPushButton('Tourner')
        self.runButton.clicked.connect(self._onRun)
        buttons.addWidget(self.runButton)
        self.stopButton = QPushButton('Arrêter')
        self.stopButton.setEnabled(False)
        self.stopButton.clicked.connect(self._onStop)
        buttons.addWidget(self.stopButton)
        self.clearButton = QPushButton('Effacer')
        self.clearButton.clicked.connect(self._onClear)
        buttons.addWidget(self.clearButton)
        # The tools switch. On (the default) the agent runs its gestures and
        # the transcript holds only the answer -- `hide`; off the agent is
        # offered no tool at all, a pure text shape -- `off`. It is the
        # in-session switch: it follows the preference on build and, when the
        # user flips it, follows the choice for the rest of the session. The
        # shape that is reached across a new session is the `AgentToolsMode`
        # file preference, which is also where `off` is written, and which
        # the switch mirrors on build without overwriting it.
        buttons.addStretch(1)
        self.toolsBox = QCheckBox('Appels aux outils')
        buttons.addWidget(self.toolsBox)
        layout.addLayout(buttons)

        # Connect the agent signals
        if self.agent is not None:
            self.agent.transcriptLine.connect(self._appendTranscript)
            self.agent.askFinished.connect(self._onFinished)
            # The switch mirrors the shape the loop wears: checked is a
            # tools-on shape (`hide`/`verbose`), unchecked the chat shape
            # (`off`). It sets the agent's mode but does not write the file --
            # the file is where the shape persists -- so a panel rebuilt after
            # a new session reads the same shape back, and neither overwrites
            # the other.
            from imasviz.VizUtils import QVizPreferences
            self.toolsBox.blockSignals(True)
            self.toolsBox.setChecked(
                QVizPreferences.AgentToolsMode != 'off')
            self.toolsBox.blockSignals(False)
            self.agent.tools_mode = QVizPreferences.AgentToolsMode
            self.toolsBox.toggled.connect(self._onToolsToggled)

        self.setWindowTitle(
            'Agent — %s' % QVizGlobalValues.IMAS_VIZ_VERSION)
        self.resize(640, 520)

        # Register in the session's figureframes (if the api provides it)
        if self.api is not None:
            self._register(api)

    @staticmethod
    def _nextKey(api):
        """The next available Agent: key in the session."""
        if api is None:
            return 'Agent:1'
        prefix = FigureTypes.AGENTTYPE
        used = [k for k in api.figureframes if k.startswith(prefix)]
        numbers = [int(k[len(prefix):]) for k in used]
        next_n = (max(numbers) + 1) if numbers else 1
        return '%s%d' % (prefix, next_n)

    def _register(self, api):
        """Register the panel in the session's figureframes."""
        try:
            api.figureframes[self.figureKey] = self
        except AttributeError:
            # The api does not have figureframes (test stand-in); skip.
            pass

    # ------------------------------------------------------------------ API

    def setPrompt(self, text):
        """Set the prompt text (for tests and programmatic use)."""
        self.promptEdit.setPlainText(text)

    def runAgent(self):
        """Run the agent loop synchronously (blocking).

        In the panel, ``_onRun`` starts a worker thread and calls this
        from there. In the test, it is called directly on the test
        thread, so it blocks until the loop is done.
        """
        if self.agent is None:
            self._appendTranscript('ERROR: no agent to run.')
            return
        prompt = self.promptEdit.toPlainText().strip()
        if not prompt:
            self._appendTranscript('ERROR: no prompt entered.')
            return
        self.runButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self._recordPrompt(prompt)
        self.agent.ask(prompt)

    def transcriptText(self):
        """The full transcript text (for tests)."""
        return self.transcript.toPlainText()

    def windowApi(self):
        """The api this window is registered in -- the one that holds
        the close rule."""
        return self.api

    # --------------------------------------------------------------- slots

    def _onRun(self):
        """Start the agent loop in a worker thread (GUI stays responsive)."""
        if self.agent is None:
            self._appendTranscript('ERROR: no agent configured.')
            return
        prompt = self.promptEdit.toPlainText().strip()
        if not prompt:
            self._appendTranscript('ERROR: no prompt entered.')
            return
        self.runButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self._appendTranscript('User: %s' % prompt)
        self._recordPrompt(prompt)
        self._run_thread = threading.Thread(
            target=self.agent.ask, args=(prompt,), daemon=True)
        self._run_thread.start()

    def _onStop(self):
        """Request the agent loop to stop."""
        if self.agent is not None:
            self.agent.stop()

    def _onClear(self):
        """Clear the transcript and the prompt.

        The history is not cleared: a prompt the run has typed is what
        the run reached this time, and `Effacer` leaves that in place so
        a run does not lose its own past just because it wants a fresh
        box. A panel rebuilt after a run types the same prompts back out,
        which is the one that makes the history matter.
        """
        self.transcript.clear()
        self.promptEdit.clear()
        self.promptEdit.setFocus()

    def _loadHistory(self):
        """The box from disk: newest first. A run that started after a
        new session reaches it still, which is the point of a history
        the run asked for -- what a run reached is not the same as what
        a run asked for.
        """
        self.promptHistoryBox.blockSignals(True)
        self.promptHistoryBox.clear()
        try:
            for entry in QVizPromptHistory.mostRecentFirst(limit=20):
                self.promptHistoryBox.addItem(entry)
        except ValueError:
            pass
        self.promptHistoryBox.blockSignals(False)

    def _onHistorySelected(self, index):
        """A line picked from the box: the prompt the run typed before,
        put back in the box to be re-run, or re-edited, or both. A run
        that starts from a line in the box does not type it again -- it
        types what the line says, and the run it gets is what it asked
        for, not what the line asked of the run."""
        text = self.promptHistoryBox.itemText(index)
        if text:
            self.promptEdit.setPlainText(text)

    def _recordPrompt(self, prompt):
        """The prompt a run types in: it goes in the history, and the box
        refreshes to include it. A run that starts from a line in the box
        re-types what the line says, and a run that types a fresh prompt
        records it -- the run the box holds is the one the run asked for
        and the one it asked of the box, in that order.
        """
        try:
            QVizPromptHistory.append(prompt)
        except ValueError as e:
            # A prompt that cannot be recorded is the prompt a run still
            # runs, and the refusal is the one the user reads in the
            # transcript rather than the one the run reads in the box.
            self._appendTranscript('REFUSAL — history: %s' % e)
            return
        self._loadHistory()
        # The line just typed is the one the box now answers to: point the
        # box at it so the run a reader sees matches the run the reader
        # typed.
        count = self.promptHistoryBox.count()
        if count:
            self.promptHistoryBox.blockSignals(True)
            self.promptHistoryBox.setCurrentIndex(0)
            self.promptHistoryBox.blockSignals(False)

    def _onToolsToggled(self, checked):
        """The tools switch: on is the tools-on shape (`hide`), off the chat
        shape (`off`, no gesture offered).

        It follows the choice for the rest of this session -- a panel
        rebuilt after a new session reads the shape back from the
        `AgentToolsMode` preference, which is where it is reached across a
        new session and where the switch mirrors it on build.
        """
        if self.agent is not None:
            self.agent.tools_mode = 'hide' if checked else 'off'

    def _appendTranscript(self, line):
        """One line from the agent loop, appended to the transcript."""
        self.transcript.appendPlainText(line)
        # Scroll to the bottom
        sb = self.transcript.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _onFinished(self, error):
        """The agent loop is done: re-enable the buttons."""
        self.runButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        if error is not None:
            # The refusal was already appended to the transcript by the
            # loop; this is the final state update.
            pass
