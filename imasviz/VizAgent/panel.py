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

Showing a figure is the user's own command: the loop draws what it is
asked, and the panel raises nothing -- a figure the turn drew or named
is in the *Windows* menu, where a raise keeps the place and the size
the user gave the window. A show the user asks of the agent ("montre-moi
Plot1") is an explicit gesture the loop runs like every other
(``focus_window``), not a side effect of an accepted answer.

The catalogue box and the *Prompts…* window are the two folders the page
and the client read and write (``~/.imasviz/prompts`` and
``SharedPromptsDir``), asked through the core's ``*_prompt`` gestures
like every other surface asks them: a prompt chosen here arrives in the
box with the holes this session already answered -- its open case, its
open window -- and the source of each named. Filling is not running: the
box is what is asked, through the same *Run* as any other prompt.
"""

import threading

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from imasviz.VizAgent import rich
from imasviz.VizAgent.QVizPromptCatalog import NO_PROMPT, QVizPromptManager
from imasviz.VizAgent.QVizPromptHistory import QVizPromptHistory

from imasviz.Viz_API import QVizClosableWindow
from imasviz.VizUtils import FigureTypes, QVizGlobalValues

# The width the panel's WINDOW must not exceed (pixels).
#
# The transcript is a ``QTextBrowser`` in ``NoWrap``, and a long single
# line -- a REFUSAL sentence, a ``verbose`` tool line, an answer that
# arrives without newlines -- carries the width it asks to its top level:
# on a running display the panel widens to the widest line it has shown
# and stays there, while offscreen does not propagate size hints and
# cannot show it. Capping the window is the repair; keeping the transcript
# ``NoWrap`` is what keeps that line readable -- it scrolls horizontally
# instead of wrapping a tool output the user wanted to compare.
MAX_WIDTH = 1000

# The transcript is kept to this many visible lines: the oldest lines leave
# the window, the newest the reader is looking at stay. The transcript the
# client writes to disk is not touched by this cap -- it stays the whole
# record of the run; only the window scrolls through what the user
# actually reads, and the window does not grow with the session past this
# ceiling.
TRANSCRIPT_MAX_LINES = 500


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
        # The catalogue window, held here: a window no Python reference
        # holds dies with the wrapper that made it, and this one is opened
        # from a button.
        self.promptManager = None

        # The key: the next available Agent: number in the session.
        self.figureKey = self._nextKey(api)

        # --- layout -----------------------------------------------------
        # The transcript is on top and the input box is below it: the
        # answer scrolls into sight while the prompt stays at the bottom
        # of the window, with the button row after the input.
        layout = QVBoxLayout(self)

        # Transcript: a rich document, because the assistant's own words
        # carry markup the reader is meant to see -- bold the idea,
        # italic a node, code a path, and the math the model spells,
        # carried the way the page carries it (the engine this document
        # is painted by composes none of it, measured). A line that is
        # not the assistant's (a tool call, a refusal) lands verbatim.
        self.transcript = QTextBrowser()
        self.transcript.setReadOnly(True)
        self.transcript.setPlaceholderText('The transcript appears here.')
        self.transcript.setLineWrapMode(QTextBrowser.LineWrapMode.NoWrap)
        layout.addWidget(self.transcript)

        # Prompt history: a dropdown of the prompts the run has typed,
        # newest first, so a run that started after a new session reaches
        # them still -- a new session takes this panel off the screen but
        # the list it left behind is what the run asks back.
        self.promptHistoryBox = QComboBox()
        self.promptHistoryBox.activated.connect(self._onHistorySelected)
        layout.addWidget(self.promptHistoryBox)
        self._loadHistory()

        # The prompt catalogue: the prompts the user filed to ask again,
        # grouped by category, each line saying its name and its one line
        # of description. The history box is what this session typed; this
        # one is what the user wrote on purpose, on disk. Choosing a line
        # puts the prompt in the box below with the holes this session
        # already answered filled in ({shot}, {figure}…) -- a hole nothing
        # answers is a refusal naming it, never a value invented for it,
        # and the *Prompts…* window is where such a hole gets typed.
        self.promptCatalogueBox = QComboBox()
        self.promptCatalogueBox.activated.connect(self._onCatalogueSelected)
        layout.addWidget(self.promptCatalogueBox)
        self._loadCatalogue()

        # Prompt
        self.promptEdit = QPlainTextEdit()
        self.promptEdit.setPlaceholderText(
            'Ask the agent to open a case, to plot, to search…')
        self.promptEdit.setMaximumHeight(80)
        layout.addWidget(self.promptEdit)

        # Buttons
        self.buttonRow = QHBoxLayout()
        buttons = self.buttonRow
        self.runButton = QPushButton('Run')
        self.runButton.clicked.connect(self._onRun)
        buttons.addWidget(self.runButton)
        self.stopButton = QPushButton('Stop')
        self.stopButton.setEnabled(False)
        self.stopButton.clicked.connect(self._onStop)
        buttons.addWidget(self.stopButton)
        self.clearButton = QPushButton('Clear')
        self.clearButton.clicked.connect(self._onClear)
        buttons.addWidget(self.clearButton)
        # The catalogue in its own window: the list, the holes of the one
        # chosen, and the two asks -- put the filled prompt in the box, or
        # run it. Non-modal on purpose: the transcript keeps scrolling
        # behind it, and the gestures it makes are the core's, so the page
        # and the client see the same catalogue change.
        self.promptsButton = QPushButton('Prompts…')
        self.promptsButton.clicked.connect(self._onPromptsWindow)
        buttons.addWidget(self.promptsButton)
        # The tools switch. On (the default) the agent runs its gestures and
        # the transcript holds only the answer -- `hide`; off the agent is
        # offered no tool at all, a pure text shape -- `off`. It is the
        # in-session switch: it follows the preference on build and, when the
        # user flips it, follows the choice for the rest of the session. The
        # shape that is reached across a new session is the `AgentToolsMode`
        # file preference, which is also where `off` is written, and which
        # the switch mirrors on build without overwriting it.
        buttons.addStretch(1)
        self.toolsBox = QCheckBox('Tool calls')
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
        # The cap, not a resize: `resize` is where the window opens, and
        # the cap is what a line cannot pass -- a NoWrap transcript
        # widens the top level to its widest line and the window stays
        # there (offscreen cannot show it: no size-hint propagation),
        # and the cap is that ceiling. A line longer than the cap then
        # scrolls in place instead of stretching the window.
        self.setMaximumWidth(MAX_WIDTH)

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
        the run reached this time, and `Clear` leaves that in place so
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

    # ------------------------------------------------------------- catalogue

    def _promptCore(self):
        """The core the catalogue gestures live on.

        The panel holds the ``AgentLoop``, and the loop holds the core --
        the one standing in front of the open case and the open windows,
        which is what answers ``{shot}`` and ``{figure}`` without asking.
        A panel with no agent has no one to ask, and says so in the box
        rather than reading the folders itself: two readers of the
        catalogue, one of them blind to the session, is how a prompt would
        start answering a case that is not the one on screen.
        """
        return getattr(self.agent, 'core', None)

    def _loadCatalogue(self):
        """The box from the two catalogues: category first, then name,
        with the one line of description a reader chooses on. Separators
        group the categories, so a catalogue of forty prompts is read as
        the list the user wrote and not as a wall.

        A shared catalogue with no folder named is not a missing half: the
        personal prompts still answer, and the reason is in the status
        line of the *Prompts…* window.
        """
        box = self.promptCatalogueBox
        box.blockSignals(True)
        box.clear()
        box.addItem(NO_PROMPT)
        core = self._promptCore()
        if core is None:
            box.addItem('(no agent to answer the catalogue)')
        else:
            try:
                answer = core.list_prompts()
            except ValueError as e:
                box.addItem('REFUSAL — %s' % e)
            else:
                last = None
                for entry in answer['prompts']:
                    if last is not None and entry['category'] != last:
                        box.insertSeparator(box.count())
                    last = entry['category']
                    label = '%s — %s' % (entry['category']
                                         or '(no category)', entry['name'])
                    if entry['description']:
                        label += '  ·  %s' % entry['description']
                    box.addItem(label, (entry['scope'], entry['id']))
        box.blockSignals(False)

    def _onCatalogueSelected(self, index):
        """A prompt chosen: the text, with its holes filled by what the
        four sources answer -- what was typed last time for it, this
        session, its own defaults. The transcript says which source
        answered each hole, because a value the user did not type is a
        value they are told about before it is sent.

        The box is filled, not run: choosing from a menu is not an ask to
        start a turn. *Run* stays the ask.
        """
        where = self.promptCatalogueBox.itemData(index)
        if not where:
            return
        scope, prompt_id = where
        core = self._promptCore()
        if core is None:
            self._appendTranscript('ERROR: no agent to answer the catalogue.')
            return
        try:
            answer = core.fill_prompt(name=prompt_id, scope=scope)
        except ValueError as e:
            self._appendTranscript('REFUSAL — catalogue: %s' % e)
            return
        self.promptEdit.setPlainText(answer['text'])
        filled = sorted(name for name, one in answer['values'].items()
                        if one['value'])
        self._appendTranscript('Catalogue — %s : %s' % (
            answer['name'],
            '; '.join('{%s} (%s)' % (name, answer['values'][name]['source'])
                      for name in filled) or 'no hole to fill'))

    def _onPromptsWindow(self):
        """The catalogue in its own window: the list, the holes of the one
        chosen, the write of a new one.

        Non-modal, and raised instead of doubled when it is already on
        screen. It is held here because a window no Python reference holds
        dies with the wrapper that made it.
        """
        if self.promptManager is not None and self.promptManager.isVisible():
            self.promptManager.raise_()
            self.promptManager.activateWindow()
            return
        self.promptManager = QVizPromptManager(
            self._promptCore(), parent=self,
            onInsert=self.setPrompt,
            onRun=self._runFromCatalogue,
            onChanged=self._loadCatalogue)
        self.promptManager.show()
        self.promptManager.refresh()

    def _runFromCatalogue(self, text):
        """A catalogue prompt launched through the panel's own run: the
        transcript, the history and the busy buttons are the panel's, so
        the turn a catalogue prompt starts is the turn the user reads."""
        self.promptEdit.setPlainText(text)
        self._onRun()

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
        """One line from the agent loop, appended to the transcript.

        The assistant's own words (``LLM: …``) are read as the words
        they are -- the markup the model spelled is painted, and the
        math it wrote is carried the way the page carries it; every
        other line -- a tool call, an answer, a refusal -- is the shape
        the loop names, kept verbatim. The page reads its lines the
        same way, and neither reading touches the transcript file the
        client writes, which stays plain.
        """
        cursor = self.transcript.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if rich.isAssistantLine(line):
            cursor.insertHtml(rich.toHtml(line))
        else:
            cursor.insertText(line)
        cursor.insertText('\n')
        # Drop the oldest lines past the cap, then scroll to the bottom
        self._trimTranscript()
        sb = self.transcript.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _trimTranscript(self):
        """Keep the last ``TRANSCRIPT_MAX_LINES`` visible lines.

        The visible lines are what the reader sees, not what the loop
        handed out: an assistant line can carry several of them (the
        ``<br>`` of a line break it wrote is one block with several
        lines; a ``<pre>`` is several blocks). The trim runs at the
        line level -- an appended line is kept together except where
        the boundary falls inside it, which keeps the tail of that line
        and drops the ``<b>LLM:</b>`` lead-in with the rest of it.
        """
        cap = TRANSCRIPT_MAX_LINES
        doc = self.transcript.document()
        lines = doc.toPlainText().splitlines()
        overflow = len(lines) - cap
        if overflow <= 0:
            return
        sublines_before = 0
        keep_pos = None
        block = doc.begin()
        while block.isValid():
            text = block.text()
            n = (1 + text.count('\u2028')) if text else 0
            if sublines_before + n > overflow:
                if text:
                    idx = overflow - sublines_before
                    if idx == 0:
                        keep_pos = block.position()
                    else:
                        offset = 0
                        for _ in range(idx):
                            offset = text.index('\u2028', offset) + 1
                        keep_pos = block.position() + offset
                break
            sublines_before += n
            block = block.next()
        if keep_pos is None:
            # The whole document as one empty block: nothing to delete.
            return
        sel = QTextCursor(doc)
        sel.setPosition(keep_pos)
        sel.movePosition(QTextCursor.MoveOperation.Start,
                         QTextCursor.MoveMode.KeepAnchor)
        sel.removeSelectedText()

    def _onFinished(self, error):
        """The agent loop is done: re-enable the buttons."""
        self.runButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        if error is not None:
            # The refusal was already appended to the transcript by the
            # loop; this is the final state update.
            pass
