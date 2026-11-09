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
    QGridLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

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
        layout.addLayout(buttons)

        # Connect the agent signals
        if self.agent is not None:
            self.agent.transcriptLine.connect(self._appendTranscript)
            self.agent.askFinished.connect(self._onFinished)

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
        self._run_thread = threading.Thread(
            target=self.agent.ask, args=(prompt,), daemon=True)
        self._run_thread.start()

    def _onStop(self):
        """Request the agent loop to stop."""
        if self.agent is not None:
            self.agent.stop()

    def _onClear(self):
        """Clear the transcript and the prompt."""
        self.transcript.clear()
        self.promptEdit.clear()
        self.promptEdit.setFocus()

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
