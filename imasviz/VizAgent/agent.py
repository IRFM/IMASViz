# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The agent loop: LLM → tool → LLM → … → final answer.

The loop runs in a worker thread: the LLM call can take seconds and the
GUI must stay responsive during that time. The gestures themselves
(``McpGuiCore`` methods) run on the GUI thread through the
``GuiDispatcher`` -- the same bridge the MCP surface uses, the same
rule that a thread that does not own a widget must not touch one.

Refusals are named and surfaced in the transcript, the style of this
repository: a ``ValueError`` from a gesture, a truncated LLM response,
an empty answer, or the ``max_turns`` limit is all emitted as a
``REFUSAL`` line, and ``askFinished`` carries the reason.
"""

import json
import re
from collections.abc import Mapping, Sequence

from PySide6.QtCore import QObject, Signal

from imasviz.VizAgent.tools import (
    SYSTEM_INSTRUCTIONS,
    CHAT_INSTRUCTIONS,
    TOOLS,
    argumentsForMember,
    callSpelling,
    callSpellings,
    gestureOf,
    missingParameterRefusal,
    missingParameters,
    offerHead,
    resolveCall,
    unknownParameterRefusal,
    unknownParameters,
)

# The shapes of a final answer that, after a successful tool, gives the work
# the loop just did back to the user: it names no pending work, says it has
# done none yet, or says no request was even attached. Keyed on the negative
# claim -- not on "what would you like to do next", which a *correct* answer
# may well offer -- so a good final answer is never mistaken for this.
_DEFLLECTION_MARKERS = (
    'no pending task', 'a pending task',
    'i don\'t know what to do', 'i don\'t know what you',
    'haven\'t drawn', 'have not drawn',
    'haven\'t traced', 'have not traced',
    'haven\'t plotted', 'have not plotted',
    'haven\'t done', 'have not done',
    'no question or instruction', 'no question attached',
    'there was no question',
    'je n\'ai pas de tâche', 'je n\'ai encore rien',
    'je n\'ai rien tracé', 'je n\'ai rien fait',
    'je ne sais pas quoi faire',
)

# The three gestures that erase bookkeeping: a figure, a case and its
# own figures, or the whole session. The loop runs one of them only
# when the user's own request asks for it, or when the caller IS the
# user (the page's button, `requested_by='user'`) -- `_dispatch` asks
# the question, and it is the one choke point both callers reach.
DESTRUCTIVE_GESTURES = ('close_window', 'close_case', 'new_session')

# The three gestures that write a line in one of the journals, and the
# one that names the shared journal is the one this gate applies: a
# visible line the writers all read (a new one, an erased one, or one
# changed in place), and the loop runs it only when the user's own
# request names the journal to put it in. A gesture the model reaches
# for on a request that does not name the journal is refused by name,
# the same rule DESTRUCTIVE_GESTURES applies.
SHARED_JOURNAL_GESTURES = ('add_note', 'edit_note', 'delete_note',
                           'reindex_journals')

# A word (or pair) the user's request carries when it asks for a close
# or a reset, in either language. Kept narrow on purpose: a gesture
# that erases a figure is refused by a prompt that does not name it,
# and a word that is a normal request word ("fresh data", "remove the
# noise") is not what this gate is for. The French close verb is the
# one word of the list that is not a substring but a whole word -- the
# stem "ferm" also matched inside other words the request could
# carry, and only the close verbs themselves open the gate.
_CLOSURE_WORDS = (
    'close', 'suppr', 'delete',
    'new session', 'nouvelle session',
    'reset', 'réinitialis', 'reinitialis',
    'restart', 'recommenc', 'nettoy', 'wipe', 'purge',
)
_CLOSURE_RE = re.compile(r'\bferm(e|er|ez)\b')

# The same shape, for a write to the shared journal: the word the user
# would give before the journal it wants a line in ("publier au
# journal partagé", "share this", "write it to the shared journal").
# Kept narrow, as _CLOSURE_WORDS is: the word a model recites is not
# the ask, and the ask the model did not give a word for is one the
# loop does not run.
_PUBLISH_WORDS = (
    'publier', 'partager', 'share',
    'journal partagé', 'journal commun', 'journal de manip',
    'shared journal', 'cahier de manip',
)


# --- Bounded history ────────────────────────────────────────────────────────
#
# The history the loop carries is read back at the start of every ask, so
# an unbounded one grows with the session: every turn is re-sent whole to
# the model. The keep window is a count of turns -- a single turn can carry
# a big tool result, so bytes are not the unit -- with a byte budget on
# top of it: an ask that folds away old turns still keeps its own last
# turns exactly as they were, tool traffic and all.
MAX_HISTORY_TURNS = 6
MAX_HISTORY_CHARS = 64 * 1024
_SUMMARY_MARK = '[Earlier turns:'
_SUMMARY_DIGEST_RE = re.compile(r'(\d+) turns? folded')


def _turnsOf(messages):
    """The flat history, split into turns: a user message starts one, and
    the turn holds everything up to the next user message (or the end) --
    the ask, the assistant's tool calls with their step text, the tool
    results, the final answer. That is the unit the loop appends in one
    block, and the unit the fold works on."""
    turns = []
    current = []
    for m in messages:
        if m.get('role') == 'user' and current:
            turns.append(current)
            current = []
        current.append(m)
    if current:
        turns.append(current)
    return turns


def _isSummaryTurn(turn):
    """A folded summary is one bracketed user message, and is never folded
    again itself -- it carries its own count, and a new fold re-derives the
    line from the turns themselves, not from the old gists."""
    return (len(turn) == 1 and turn[0].get('role') == 'user'
            and (turn[0].get('content') or '')
            .lstrip().startswith(_SUMMARY_MARK))


def _summaryCount(text):
    match = _SUMMARY_DIGEST_RE.search(text or '')
    return int(match.group(1)) if match else 0


def _shorten(text, limit):
    text = ' '.join((text or '').split())
    return text if len(text) <= limit else text[:limit].rstrip() + '…'


def _gist(turn):
    """The ask and the final answer of one turn, truncated: the gist a
    folded turn keeps. The tool traffic of the turn is what the fold drops."""
    ask = final = None
    for m in turn:
        if m.get('role') == 'user' and m.get('content'):
            ask = m['content']
        if (m.get('role') == 'assistant' and not m.get('tool_calls')
                and m.get('content')):
            final = m['content']
    if not ask and not final:
        return '(empty turn)'
    return '%s -> %s' % (_shorten(ask, 120), _shorten(final, 160))


def _flatten(turns):
    """The kept turns as the flat message list the next ask appends."""
    return [m for t in turns for m in t]


def _compactHistory(messages):
    """Fold the oldest turns past the window into one summary line.

    The kept turns stay whole -- the next ask reads the last turns
    exactly as they were. What stands behind them is one bracketed user
    message: how many turns this session has folded (a count, never a
    re-nesting of gists), and the asks and final answers of the newest
    three of the turns it stands for.
    """
    turns = _turnsOf(messages)
    if len(turns) <= MAX_HISTORY_TURNS:
        return messages
    summary_msg = None
    if _isSummaryTurn(turns[0]):
        summary_msg = turns.pop(0)[0]
    folded = _summaryCount(summary_msg.get('content')) if summary_msg else 0
    if len(turns) <= MAX_HISTORY_TURNS:
        return [summary_msg] + _flatten(turns) if summary_msg else messages
    old, kept = turns[:-MAX_HISTORY_TURNS], turns[-MAX_HISTORY_TURNS:]
    gists = [_gist(t) for t in old]
    folded += len(old)
    # The byte budget is the hard cap on the kept window: fold the oldest
    # kept turn in until the window fits. The final turn is never folded
    # away -- it is the one the next ask reads back.
    while len(kept) > 1 and _chars(_flatten(kept)) + 200 * len(gists[-3:]) + 400 \
            > MAX_HISTORY_CHARS:
        gists.append(_gist(kept.pop(0)))
        folded += 1
    summary = '%s %d turn%s folded this session, the oldest first (%s). ' \
        'The last turns are kept whole.]' % (
            _SUMMARY_MARK, folded,
            's' if folded != 1 else '',
            ' | '.join(gists[-3:]) if gists else 'none')
    return [{'role': 'user', 'content': summary}] + _flatten(kept)


def _chars(messages):
    return sum(len(json.dumps(m)) for m in messages)


def _userAskedForAClosure(user_prompt):
    """Whether the user's own request asks for a close or a reset.

    Asked is carried by the user's words, not by the model's intent:
    the same call the model reaches for on a "trace la pression" is
    the ask for the "ferme Plot2" that names the figure it erases.
    The French close verb is matched on the whole word (ferme, fermer,
    fermez), not on its stem: the stem also sat inside other words the
    request could carry, and that is the false positive the gate must
    not give the model.
    """
    text = (user_prompt or '').lower()
    return _CLOSURE_RE.search(text) is not None \
        or any(word in text for word in _CLOSURE_WORDS)


def _userAskedForAPublish(user_prompt):
    """Whether the user's own request asks for a write to the shared
    journal. The same shape as ``_userAskedForAClosure``: the words on
    the ask, in the user's own hand, and the write the model reaches
    for in a shared write runs only when the user's ask names the
    journal it will put a line in.
    """
    text = (user_prompt or '').lower()
    return any(word in text for word in _PUBLISH_WORDS)

# The one gesture that draws a window nobody asked for: a plugin entry,
# which opens a window of its own -- an equilibrium chart, a profiles
# panel, a flux-surface figure -- over whatever the ask was drawing. The
# field report: « charge l'équilibre, trace la pression pour psi=0, 30 60
# et 100 sur une nouvelle figure » came back with an Equilibriumcharts
# window beside the four curves. Nothing in the application opens one on
# a load -- ``manage_idss(action="load")`` runs ``QVizLoadOccurrence`` and
# no plugin -- so that window was the model reaching for the entry.
#
# The gate is keyed on the RUN, not on the group: reading what a case
# offers (``plugin(action="list")``) costs no window and is asked before
# the ask is settled, so it is never refused. The ask word is narrower
# than the closure list on purpose -- see ``_userAskedForAPluginWindow``.
PLUGIN_WINDOW_GESTURES = ('run_plugin',)

# The words a plugin window is asked under, in either language. The name of
# the plugin itself opens the gate too, matched in ``_userAskedForAPluginWindow``
# on what the CALL names. What is kept out of both is the generic noun for
# what such a window shows: a "graphique", a "profil", a "courbe" or a
# "surface" is what ``plot`` and ``equilibrium(action="surfaces")`` already
# answer, and a gate that opened on those words would let the reported ask
# through -- which is what the report was.
_PLUGIN_ASK_WORDS = ('plugin', 'extension')


def _askKey(text):
    """A user's wording or a plugin name, in the one spelling the gates
    compare: lowercase, letters and digits only. So a plugin named
    ``VizProfiles_plugin`` answers an ask that spells it with a space, and
    an ask does not have to keep the punctuation a name carries."""
    return ''.join(ch for ch in (text or '').lower() if ch.isalnum())


def _userAskedForAPluginWindow(user_prompt, plugin=''):
    """Whether the user's own request asks for the window of the plugin the
    call addresses.

    Asked is carried by the user's words, as ``_userAskedForAClosure``
    reads it: the ``plugin(action="run")`` a model reaches for on « charge
    l'équilibre, trace la pression » is not the ask for the window that
    entry draws. Two spellings open the gate:

      * the word a plugin window is asked under, in either language -- "le
        plugin", "l'extension", "the plugin";
      * the exact name of the plugin **the call itself** addresses, with its
        separators off ("ouvre VizProfiles plugin" answers
        ``VizProfiles_plugin``).

    The called name and not any registered one: an ask that names
    ``VizSpectral`` does not license a run of ``equilibriumcharts`` -- and a
    registered list is not something a gate could read without importing
    what it names, the shipped set being where matplotlib comes in.
    """
    text = _askKey(user_prompt)
    if any(word in text for word in _PLUGIN_ASK_WORDS):
        return True
    name = _askKey(plugin)
    return bool(name) and name in text


# The claims guards live in ``imasviz/VizAgent/agent_guards.py`` -- the
# regexes and the tests a final answer stands on. Imported back here so
# ``from imasviz.VizAgent.agent import ...`` keeps its meaning.
from imasviz.VizAgent.agent_guards import (
    _bareNames,
    _groundedFigureKeys,
    _READ_GESTURES,
    _WORK_GESTURES,
    fabricatedFigureKeys,
    noteClaimed,
    reportClaimed,
    unperformedWorkOn,
)


def _serialisable(value):
    """A tool result on its way to the model: the bytes it carries become
    a named confirmation, not a `json.JSONDecodeError` at the dumps.

    `get_screenshot` answers the window's PNG, and the model is asked
    nothing from it -- what it needs is to know the capture happened and
    how big, which `json.dumps` cannot say of a `bytes` object. The
    answer names the size instead, and a list or mapping the gesture
    returned is walked the same way, so one binary leaf among the data
    is the same refusal the result alone would be.
    """
    if isinstance(value, (bytes, bytearray, memoryview)):
        return 'captured: %d bytes' % len(value)
    if isinstance(value, Mapping):
        return {str(key): _serialisable(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_serialisable(item) for item in value]
    return value


class AgentLoop(QObject):
    """One agent session: its LLM, its gestures, and the loop.

    ``core`` is the ``McpGuiCore`` instance (the 24 gestures).
    ``llm`` is the ``LLMClient`` (or a stand-in in tests).
    ``dispatcher`` is the ``GuiDispatcher`` (or a stand-in in tests).
    ``main_window`` is the ``QVizMainWindow``, or None in the test suite.
    ``api`` is the ``Viz_API`` the gestures drive -- the session's own
    when this loop is the in-app agent, so the *Windows* menu sees the
    agent's figures alongside the user's.
    """

    transcriptLine = Signal(str)
    # The full render of every transcript line, regardless of the mode that
    # `transcriptLine` paints. A surface whose transcript is an ARTIFACT (the
    # client, the web -- the file that is audited) listens to this so that a
    # run wearing `hide` still lands the tool traffic it ran, while the panel
    # -- whose transcript IS its live view -- keeps listening to
    # `transcriptLine` alone. Emitted by `_emit`, the one place every line
    # passes, so the two can never drift apart in what a line says.
    fullLine = Signal(str)
    askFinished = Signal(object)
    # The gesture the loop is about to run, by its tool name and the
    # arguments it passed validation with -- emitted by `_dispatch`,
    # before the call, so a session that listens can say which windows a
    # turn asked to be captured (`get_screenshot`) and save them beside
    # its figures at the turn's end. A loop with no listener is
    # unchanged: an emission with no receiver is a no-op in Qt.
    gestureIssued = Signal(str, object)

    def __init__(self, core, llm, dispatcher, main_window=None, api=None):
        super(AgentLoop, self).__init__()
        self.core = core
        self.llm = llm
        self.dispatcher = dispatcher
        self.main_window = main_window
        self.api = api
        self.history = []
        self._stop_requested = False
        # `None` means "read it from the preference each ask". The panel (or a
        # test) sets it to one of ``QVizPreferences.AGENT_TOOLS_MODES`` to pin
        # the shape for every turn without re-reading the file in between.
        self.tools_mode = None
        # The token accounting of the ask in flight: the server reports a
        # per-call usage, and the loop sums it so the transcript and the
        # surfaces read the same one number. The counters are reset by the
        # start of every `ask` and reported once, at its end, by
        # `_reportUsage` -- a stand-in LLM that answers no usage is
        # unmeasured, never zero.
        self.last_usage = None
        self._usage_prompt = 0
        self._usage_completion = 0
        self._usage_total = 0
        self._turns_used = 0
        self._usage_measured = False

    def _emit(self, line, live=True):
        """Every transcript line passes through here: the full render goes to
        `fullLine` always, and the live view (`transcriptLine`) only when the
        current mode says this line is one it carries. A single choke point is
        what keeps the two surfaces -- the live view and the audited artifact
        -- agreeing on what a line says while disagreeing on which lines they
        show.
        """
        self.fullLine.emit(line)
        if live:
            self.transcriptLine.emit(line)

    def ask(self, user_prompt, max_turns=12, tools_mode=None):
        """Run the agent loop, blocking until it is done.

        The caller decides what thread to call this from. In the panel,
        it is called from a worker thread and the caller waits for the
        ``askFinished`` signal. In the test, it is called synchronously
        from the test thread.

        ``tools_mode`` is one of ``QVizPreferences.AGENT_TOOLS_MODES``
        (``hide`` by default, the answer on the transcript with the work in
        between cut; ``off`` for a pure text shape with no gesture offered;
        ``verbose`` for the whole tool traffic). Left out, or ``self.tools_mode``
        is ``None``, the preference is read in, so the shape a run wears is
        the one ``~/.imasviz/preferences`` says, not one the loop picked.
        """
        self._stop_requested = False
        # A deflected final answer (the work handed back to the user) is
        # re-anchored once and then refused; a new ask restarts the budget, so
        # each request gets its own single re-anchor instead of a shared one.
        self._reanchors = 0
        mode = tools_mode if tools_mode is not None else self.tools_mode
        if mode is None:
            from imasviz.VizUtils import QVizPreferences
            mode = QVizPreferences.AgentToolsMode
        try:
            self._run(user_prompt, max_turns, mode)
        except Exception as e:
            self._emit('ERROR: %s' % e)
            self.askFinished.emit(str(e))
        # askFinished was already emitted by _run; this is the safety
        # net for an unexpected exception.

    def stop(self):
        """Request the loop to stop at the next turn boundary."""
        self._stop_requested = True

    def _run(self, user_prompt, max_turns, tools_mode):
        """Run the loop and report the tokens it spent, whatever happens.

        The counters are reset at every ask -- a run reads them to say what
        it costs, and a session that lives through several asks never reads
        one ask's total as another's. The report is emitted in the same
        place every exit lands (the `finally`), so an ask finished on a
        refused turn reports its tokens too; a loop that dies on an
        unexpected exception still says what it measured.
        """
        self._usage_prompt = 0
        self._usage_completion = 0
        self._usage_total = 0
        self._usage_measured = False
        self._turns_used = 0
        self.last_usage = None
        try:
            self._loop(user_prompt, max_turns, tools_mode)
        finally:
            self._reportUsage(live=tools_mode == 'verbose')

    def _reportUsage(self, live):
        """The tokens this ask spent, on the transcript and on the loop.

        The line is the one the callers can say out loud -- ``last_usage``
        is the number they want from the call itself, the line is what
        the surface shows. A stand-in LLM that answers no usage is
        unmeasured, never zero: nothing is said either way.
        """
        if not self._usage_measured:
            self.last_usage = None
            return
        self.last_usage = {
            'prompt': self._usage_prompt,
            'completion': self._usage_completion,
            'total': self._usage_total,
            'turns': self._turns_used,
        }
        self._emit(
            'Tokens: prompt %d / completion %d (total %d) over %d turn%s'
            % (self._usage_prompt, self._usage_completion, self._usage_total,
               self._turns_used, 's' if self._turns_used != 1 else ''),
            live=live)

    def _loop(self, user_prompt, max_turns, tools_mode):
        """The actual loop. Runs in whatever thread called ``ask``.

        ``tools_mode`` is the shape this run wears. ``off`` sends
        ``CHAT_INSTRUCTIONS`` and offers no gesture: the answer is a pure
        text shape and nothing it says can be grounded on a call. ``hide``
        and ``verbose`` send ``SYSTEM_INSTRUCTIONS`` and offer the gestures,
        and differ only in the transcript -- ``hide`` keeps the prompt, the
        final answer and the refusals and cuts the traffic in between;
        ``verbose`` shows it all.
        """
        system = CHAT_INSTRUCTIONS if tools_mode == 'off' else SYSTEM_INSTRUCTIONS
        tools_arg = None if tools_mode == 'off' else TOOLS
        messages = [{'role': 'system', 'content': system}]
        messages += list(self.history)
        # The first message the loop adds itself: everything from here on
        # is the turn, and the acceptance extends `self.history` with it --
        # the tool traffic included. A history that cannot see the calls
        # its own last turn made is the amnesia a follow-up confabulation
        # stands on: the model reads its last answer and answers on that
        # momentum, with no record that it had tools and used them.
        turn_index = len(messages)
        messages.append({'role': 'user', 'content': user_prompt})

        # A final answer that names case identifiers on the strength of no
        # call to a case tool is the confabulation pattern: the list is
        # recalled, not read from the case. ``called_a_tool`` is what tells
        # the guard apart from a real, tool-grounded answer.
        called_a_tool = False
        # The last tool the loop attempted, with what it answered (or the
        # refusal it was met with). The max-turns stop below names it: a
        # run that stops on the budget may have delivered everything (the
        # report written, the figure drawn), and the user must find that
        # in the refusal instead of reading the stop as a failure.
        last_action = None
        # The artifacts a successful call delivered this request, so the
        # accepted answer may name them without the fabricated-artifact
        # guard misreading a truthful reference as an invention: the report
        # paths a `plot_report`/`case_report` wrote, and the figure a
        # `close_window` closed. Both empty while no such call ran -- the
        # state the guard below keys on.
        reports_written = set()
        closed_figures = set()
        # The journal-line gestures (`add_note` / `edit_note` / `delete_note`)
        # that a call of this request actually ran, so the accepted answer
        # may say a note was written without the note guard misreading a
        # truthful reference as the confabulation it refuses. It stays empty
        # while no such call ran -- the state the guard keys on.
        journals_written = set()
        # The figures this request's successful calls did work on (a
        # draw into them, a curve transform, an axis move), and the ones
        # they read back (`curve_stats`, `export_curve`). A claim of work
        # on a standing figure stands on one of the two, whatever the
        # figure itself holds -- the fabricated-artifact guard keys on
        # the figure's existence, which this one does not.
        acted_on = set()
        read_from = set()
        # The re-anchor messages the loop appends to pull a refused answer
        # back on to the request, tracked by object identity: the
        # acceptance keeps the turn in `self.history` without them -- a
        # re-anchor is a loop-internal nudge, not a line of the
        # conversation the next ask should read back.
        anchor_ids = set()

        for turn in range(max_turns):
            if self._stop_requested:
                self._emit(
                    'Stopped: user requested stop before turn %d.' % turn)
                self.askFinished.emit('user requested stop')
                return

            # --- LLM call ---------------------------------------------------
            try:
                response = self.llm.chat(messages, tools=tools_arg)
            except ValueError as e:
                # LLMClient raises ValueError for truncation and empty content
                # (the named refusal); the test stand-in returns the
                # LLMResponse and the checks below catch the same cases.
                self._emit(
                    'REFUSAL: %s (turn %d)' % (e, turn))
                self.askFinished.emit(str(e))
                return
            except Exception as e:
                self._emit(
                    'REFUSAL: LLM call failed — %s' % e)
                self.askFinished.emit(str(e))
                return

            # The tokens this call spent, summed over the whole ask: the
            # server reports them per call, the loop turns them into the
            # one number the transcript and ``last_usage`` read. A stand-in
            # LLM that answers no usage is unmeasured, never zero.
            usage = response.usage
            if isinstance(usage, Mapping):
                prompt = usage.get('prompt_tokens') or 0
                completion = usage.get('completion_tokens') or 0
                total = usage.get('total_tokens')
                if total is None:
                    total = prompt + completion
                self._usage_prompt += prompt
                self._usage_completion += completion
                self._usage_total += total
                self._usage_measured = True
            self._turns_used += 1

            # Named refusals, checked here so a stand-in LLM that returns
            # the LLMResponse directly (without raising) is caught too:
            if response.finish_reason == 'length':
                self._emit(
                    'REFUSAL: response truncated by max_tokens (turn %d)'
                    % turn)
                self.askFinished.emit(
                    'response truncated by max_tokens (turn %d)' % turn)
                return
            if not response.content and not response.tool_calls:
                self._emit(
                    'REFUSAL: LLM returned empty content (turn %d)' % turn)
                self.askFinished.emit(
                    'LLM returned empty content (turn %d)' % turn)
                return

            if response.content:
                # In `hide`, an answer that still ends in a tool call is the
                # mid-run chatter the mode exists to cut: it stays in the
                # artifact (the `fullLine`), it is cut from the live view.
                # `off` has no tools and `verbose` shows the traffic, so the
                # line stands in both.
                self._emit('LLM: %s' % response.content,
                           live=not (tools_mode == 'hide'
                                     and response.tool_calls))

            # --- Tool calls -------------------------------------------------
            if response.tool_calls:
                called_a_tool = True
                # The step text the model wrote beside the call (the
                # reasoning models say "I'll first check the available
                # IDSs" on the same turn they call) is part of the
                # exchange: dropping it cut the thread between the call
                # and the result the model is about to read.
                messages.append({
                    'role': 'assistant', 'content': response.content or None,
                    'tool_calls': [{'id': 'call_%d' % i,
                                    'type': 'function',
                                    'function': {
                                        'name': tc['name'],
                                        'arguments': json.dumps(tc['args'])
                                    }}
                                   for i, tc in enumerate(
                                       response.tool_calls)],
                })
                for i, tc in enumerate(response.tool_calls):
                    name = tc['name']
                    args = tc['args']
                    # Two vocabularies, and the line between them is which
                    # reader is on the other side. Everything the MODEL
                    # reads back -- these two transcript lines, `last_action`
                    # in the max-turns message, the `name` of the tool result
                    # -- is spelled as the call was made: a model that is
                    # answered in a vocabulary it was never offered answers
                    # in that vocabulary next turn, and the next turn's call
                    # is refused. Everything the loop's own guards ask --
                    # which report wrote a file, which close took a figure
                    # away, which note a journal line stands on, which figure
                    # a turn worked on -- is asked about the GESTURE, because
                    # that is what ran: `generate_report(scope="plot")`
                    # grounded a `plot_report`, and a guard reading the group
                    # name would refuse an honest answer about a file that
                    # stands on disk. The guards' vocabulary is unchanged by
                    # this; only how a call reaches them is.
                    gesture = gestureOf(name, args)
                    # The call and its result are the traffic a `hide` run
                    # runs and hides: they stay in the artifact (the
                    # `fullLine`), they are cut from the live view. In
                    # `verbose` they stand in both.
                    self._emit('  → %s(%s)' % (
                        name, json.dumps(args)[:80]),
                        live=tools_mode == 'verbose')
                    try:
                        result = self.dispatcher.call(
                            lambda n=name, a=args: self._dispatch(
                                n, a, user_prompt=user_prompt))
                        summary = _summarize(result)
                        self._emit(
                            '  ← %s: %s' % (name, summary),
                            live=tools_mode == 'verbose')
                        tool_result = {'result': _serialisable(result),
                                      'error': None}
                        last_action = '%s: %s' % (name, summary)
                        # The deliverables, on the strength of the call
                        # that earned them: a report path the answer may
                        # name, a figure the close ran. Grounded by a
                        # success -- a refused call is not a deliverable.
                        if (gesture in ('plot_report', 'case_report',
                                        'case_ids_report')
                                and isinstance(result, dict)
                                and result.get('saved_to')):
                            reports_written.add(result['saved_to'])
                        if gesture == 'close_window':
                            # The key is read under the word the CALL spells
                            # it: the windows group asks for a `window` and
                            # the gesture behind it has always taken a `key`
                            # (`ACTION_RENAMES`), and these are the arguments
                            # the model typed, not the ones the core was
                            # handed. A reader of `key` here would record no
                            # figure and refuse an honest "Plot2 est fermée".
                            key = (args or {}).get('window')
                            if key:
                                closed_figures.add(key)
                        # The journal line, on the strength of the call that
                        # earned it: a note the answer may say was written,
                        # because a call of this request wrote it -- a note
                        # no call wrote is what the guard refuses. Grounded
                        # on the success -- a refused call grounds nothing.
                        if gesture in SHARED_JOURNAL_GESTURES:
                            journals_written.add(gesture)
                        # The work and the reads of the request, per
                        # figure: a claim of a change on a figure stands
                        # on a successful call that did it (a draw into
                        # the figure, a transform, an axis move) or one
                        # that read it back -- grounded on the success,
                        # the way the report path is: a refused call
                        # grounds nothing.
                        if gesture in _WORK_GESTURES:
                            acted_on.update(
                                _groundedFigureKeys(args, result))
                        elif gesture in _READ_GESTURES:
                            read_from.update(
                                _groundedFigureKeys(args, result))
                    except Exception as e:
                        # The one call line that never hides, in any shape:
                        # it is the refusal the gesture names, and the mode
                        # that cuts the noise is not the one that cuts the
                        # reason an answer turned out the way it did.
                        self._emit(
                            '  ← %s: REFUSAL — %s' % (name, e))
                        tool_result = {'result': None, 'error': str(e)}
                        last_action = '%s: REFUSAL — %s' % (name, e)
                    messages.append({
                        'role': 'tool',
                        'tool_call_id': 'call_%d' % i,
                        'name': name,
                        'content': json.dumps(tool_result),
                    })
                continue

            # --- Final answer -----------------------------------------------
            # A figure or report the answer names, but that this request
            # neither drew nor wrote, is the single-artifact confabulation:
            # one invented key presented with content ("Plot3 shows the
            # flux loop"), or "the report is written to rapport.html" when
            # no plot_report ran -- the field run drew a real figure and
            # then invented two more beside it. This runs in either branch
            # (tools ran and tools did not), so it is not folded into
            # _unfoundedIdsRefusal, which is only entered when no tool ran.
            # The refusal wears the same shape as every refusal in this
            # loop: named, re-anchored once to do the work, refused the
            # second time, and the accepted answer never carries the
            # fabrication.
            if tools_mode != 'off':
                held = self._heldFigureKeys()
                fab_refusal = self._fabricatedArtifactRefusal(
                    response.content, held, closed_figures,
                    reports_written)
                if fab_refusal is not None and self._reanchors == 0:
                    self._reanchors += 1
                    self._emit('REFUSAL: %s' % fab_refusal)
                    anchor = {'role': 'user',
                              'content': self._artifactReanchor(user_prompt)}
                    anchor_ids.add(id(anchor))
                    messages.append(anchor)
                    continue
                if fab_refusal is not None:
                    self._emit('REFUSAL: %s' % fab_refusal)
                    self.askFinished.emit(fab_refusal)
                    return
            # A note the answer says was written, but that no call of this
            # request wrote (add_note / edit_note / delete_note), is the
            # journal-line confabulation: "j'ai ajouté la note au cahier",
            # "I've added it to the journal" -- the line is said, not in the
            # journal the user then looks for. Run in either branch (a journal
            # gesture ran and none of them, or a read ran and no write), so it
            # is not folded into the figure guard, which does not see a note.
            if tools_mode != 'off':
                note_refusal = self._unmadeNoteRefusal(
                    response.content, journals_written)
                if note_refusal is not None and self._reanchors == 0:
                    self._reanchors += 1
                    self._emit('REFUSAL: %s' % note_refusal)
                    anchor = {'role': 'user',
                              'content': self._noteReanchor(user_prompt)}
                    anchor_ids.add(id(anchor))
                    messages.append(anchor)
                    continue
                if note_refusal is not None:
                    self._emit('REFUSAL: %s' % note_refusal)
                    self.askFinished.emit(note_refusal)
                    return
            if not called_a_tool:
                if tools_mode == 'off':
                    # The chat shape has no gesture it could have called, so
                    # grounding a list with one is a refusal the model
                    # cannot act on: re-anchoring at a call it cannot make
                    # is not a fix, it is a dead end. The answer stands on
                    # its own wording, and `CHAT_INSTRUCTIONS` is what tells
                    # it to say so rather than to recite.
                    refusal = None
                else:
                    refusal = self._unfoundedIdsRefusal(response.content)
                if refusal is not None and self._reanchors == 0:
                    # The repro (a field run): a made-up figure and its value
                    # table -- no draw or read tool called this request --
                    # surfaced as *the* answer, a refusal bolted on after the
                    # fact. The work the user asked for (a plotted profile)
                    # was never done, so a refusal note does not fix it. Name
                    # it, and hand the model back once with the instruction to
                    # actually call get_signal / plot_one and answer only
                    # from what those return. A second fabrication of the same
                    # shape still falls to the named refusal below.
                    self._reanchors += 1
                    self._emit('REFUSAL: %s' % refusal)
                    anchor = {'role': 'user',
                              'content': self._groundReanchor(user_prompt)}
                    anchor_ids.add(id(anchor))
                    messages.append(anchor)
                    continue
            else:
                # The tools ran. An answer that says none of it happened and
                # hands the request back to the user does not stand on top of
                # the work the loop just delivered; one that reports the work
                # is not second-guessed.
                refusal = self._deflectionRefusal(response.content,
                                                  last_action)
                if refusal is not None and self._reanchors == 0:
                    # The repro: it drew, and then said "no pending task,
                    # give me the case URI and what to do". The work is done,
                    # so name the refusal, re-anchor the model on what the
                    # tools produced and the request it was given, and hand it
                    # back one turn instead of abandoning the work.
                    self._reanchors += 1
                    self._emit('REFUSAL: %s' % refusal)
                    anchor = {'role': 'user',
                              'content': self._reanchor(
                                  user_prompt, last_action)}
                    anchor_ids.add(id(anchor))
                    messages.append(anchor)
                    continue
            # The claim of work on a figure that **stands**: the guards
            # above passed it -- the key exists, and the answer does not
            # wear the shape of a recited inventory -- yet no call of this
            # request did the work the answer reports, and no read of the
            # figure checked it: the state of a figure is what the call
            # that changed it, or read_figure(action="stats"), answers,
            # not what was said.
            # It runs after them, so a fabricated figure with its value
            # table is met by the guard whose re-anchor sends the model to
            # the read that would ground it first, and the claim of a
            # change that never ran -- on a figure the session holds --
            # is what falls to this one.
            if tools_mode != 'off':
                work_refusal = self._unperformedWorkRefusal(
                    response.content, acted_on, read_from,
                    closed_figures)
                if work_refusal is not None and self._reanchors == 0:
                    self._reanchors += 1
                    self._emit('REFUSAL: %s' % work_refusal)
                    anchor = {'role': 'user',
                              'content': self._workReanchor(user_prompt)}
                    anchor_ids.add(id(anchor))
                    messages.append(anchor)
                    continue
                if work_refusal is not None:
                    self._emit('REFUSAL: %s' % work_refusal)
                    self.askFinished.emit(work_refusal)
                    return
            if refusal is not None:
                # Either it recites a case inventory it never read (the
                # unfounded guard), or it deflects off the work it already did
                # and the one re-anchor did not cure it. In both cases refuse
                # by name, the way a refused gesture is named.
                self._emit('REFUSAL: %s' % refusal)
                self.askFinished.emit(refusal)
                return
            # The whole turn stands in the history -- the user's ask, the
            # assistant's tool calls with their step text, the tool
            # results -- not just the ask and the final line: a follow-up
            # that cannot see the calls its own last turn made cannot
            # ground on them, and the re-anchors the loop threw in between
            # are loop-internal, not conversation, so they stay out.
            self.history.extend(
                m for m in messages[turn_index:] if id(m) not in anchor_ids)
            self.history.append({
                'role': 'assistant', 'content': response.content,
            })
            # The history is read back whole at the start of the next ask,
            # so it is folded: the last turns stand exactly as they were, the
            # older ones become one bounded summary line rather than an
            # ever-growing re-send.
            self.history = _compactHistory(self.history)
            # The accepted answer, as it stands: a refused or re-anchored
            # answer never reaches this line -- the path above returns or
            # continues instead. A show of a figure is not one of the
            # side effects an accepted answer runs: it is the user's own
            # command, and `askFinished` is what the surfaces read the
            # acceptance from.
            self.askFinished.emit(None)
            return

        # max_turns exhausted
        if last_action is None:
            stopped = ('Stopped: max_turns reached (%d).' % max_turns)
            self.askFinished.emit('max_turns reached (%d)' % max_turns)
        else:
            # The budget ran out, but the loop may have delivered: name
            # the last action and what it answered (or was refused with),
            # so the user finds the artifact in the stop instead of
            # reading the stop as a failure with nothing behind it.
            stopped = ('Stopped: max_turns reached (%d); the last action '
                       'was %s.' % (max_turns, last_action))
            self.askFinished.emit(
                'max_turns reached (%d); the last action was %s.'
                % (max_turns, last_action))
        self._emit(stopped)

    def _unfoundedIdsRefusal(self, content):
        """A final answer that presents an inventory of names, with no tool
        called in this request to ground it, is refused by name.

        Returns the reason to refuse, or None when the answer may stand.
        The trigger is the *shape* of a bare recited inventory, and it
        stays narrow on what counts:

        * three or more **distinct** names that **stand on their own** --
          a name that is a segment of a longer spelling does not stand:
          ``magnetics.flux_loop[0].flux.data`` spells a path, and
          ``rapport_flux_loop_10.html`` spells a file, not a list; nor
          does the loop's own tool vocabulary, which the model quotes to
          point the user at a gesture, recite the case;
        * a markdown table of three or more data rows -- the shape the
          recited inventories actually came in, and the one that stays
          refused whatever its cells hold.

        What this does *not* do, deliberately: it does not count the
        occurrences of one name (an answer that spells ``flux_loop[i].flux.data``
        and ``magnetics.flux_loop[0..16].flux.data`` repeats a single name,
        it does not list three), and it does not match any specific name:
        a recited "equilibrium" is as much a confabulation as a made-up
        one, so the guard keys on the list shape with no tool to ground
        it. One consequence, stated on purpose: an answer that names
        three or more paths only (every name one of many segments)
        stands even without a tool -- it spells, it does not list.
        """
        text = content or ''
        names = _bareNames(text)
        # A markdown row is a line whose first non-space char is a pipe, and
        # which is neither blank nor the all-pipe separator row.
        table_rows = [
            line for line in text.splitlines()
            if line.strip().startswith('|')
            and not re.fullmatch(r'\|[\s:|-]+\|?', line.strip())
        ]
        if len(names) < 3 and len(table_rows) < 3:
            return None
        # The calls this names are spelled from the table, not by hand: an
        # instruction naming a tool the model is no longer offered is a
        # refusal that manufactures the next refused call.
        return (
            'your answer presents a list of names, or a figure and a '
            'table of values, but no tool was called this request to '
            'ground it; a list, curve or number you recite is not the '
            'truth of this session. Ground it: the case\'s IDS with '
            '%s or %s, the saved sessions '
            'with %s, the profile\'s arrays with '
            'get_signal(uri, path, ...) -- and show its curve with '
            '%s -- and answer only from what those '
            'calls return.' % (callSpelling('list_case_idss'),
                               callSpelling('list_idss'),
                               callSpelling('list_sessions'),
                               callSpelling('plot_one')))

    def _deflectionRefusal(self, content, last_action):
        """A final answer, after a successful tool, that gives the work back
        to the user is refused by name and re-anchored, instead of standing.

        Returns the refusal reason, or None when the answer may stand. The
        guard fires only when there was a delivered action to point at
        (``last_action`` set) and the content carries one of the negative
        shapes in ``_DEFLLECTION_MARKERS`` -- "no pending task", "haven't yet
        traced", "no question was attached" -- which is the exact failure that
        made the model abandon a figure it had drawn and, on a follow-up,
        claim it had done nothing. It is deliberately not keyed on "what
        would you like to do next", which a correct answer may well offer;
        an honest final answer after a tool is not second-guessed.
        """
        if last_action is None:
            return None
        text = (content or '').lower()
        if not any(marker in text for marker in _DEFLLECTION_MARKERS):
            return None
        return (
            'the tools already produced "%s", but the answer says none of it '
            'was done and asks the user to restate the request; the work is '
            'done, so the answer must be drawn from it, not handed back.'
            % last_action)

    def _reanchor(self, user_prompt, last_action):
        """The one message the loop appends to pull an answer back on to the
        request it was given and the work it produced, after a deflection.

        Every re-anchor in this file wears the same shape: the
        ``[SYSTEM FEEDBACK]`` prefix -- the loop is speaking, not the user
        (a mid-turn ``system`` role is not one the ChatML template of the
        model in use admits, so the prefix is what marks the voice) -- and
        the bare minimum: the refusal the guard named, the work it owes,
        the request it was given. Nothing else for the model to read."""
        return (
            '[SYSTEM FEEDBACK] The tools already ran for this request '
            '(last: "%s"). Answer now from what they returned; do not '
            'ask the user to restate. Request: "%s".'
            % (last_action, user_prompt))

    def _groundReanchor(self, user_prompt):
        """The one message the loop appends when an answer presented a list,
        figure or value table on the strength of no tool call this request.

        This is the confabulation branch of ``ask``: the work behind the
        claim was never done. The instruction is to *do* it -- read the
        arrays with ``get_signal``, draw the figure with ``plot`` --
        and answer only from what those calls return, so the next turn is
        either a real, tool-grounded answer or a repeated fabrication that
        the named refusal below finally turns away.
        """
        return (
            '[SYSTEM FEEDBACK] That answer named lists, figures, or '
            'values this request never read. Do the work: read the arrays '
            'with get_signal(uri, path, ...) and draw the owed curves '
            'with %s, and answer only from what '
            'those calls return. Request: "%s".'
            % (callSpelling('plot_one'), user_prompt))

    def _heldFigureKeys(self):
        """The figure keys the session holds now, through the
        dispatcher (a Qt walk). ``None`` when the core cannot report
        them -- a stand-in, or the ``off`` shape with no gesture: with
        no ground truth to answer against, a figure claim cannot be
        accused (the unfounded guard is what applies there). A core that
        can list but holds none answers the *empty* set, which does
        ground a claim against it -- a fabrication on a fresh session is
        then caught.
        """
        method = getattr(self.core, 'list_windows', None)
        if method is None:
            return None
        try:
            windows = self.dispatcher.call(lambda: method())
        except Exception:
            return None
        return {w['key'] for w in (windows or [])
                if isinstance(w, dict) and w.get('key')}

    def _fabricatedArtifactRefusal(self, content, held, closed,
                                   reports_written):
        """A figure or report the answer names, that this request
        neither drew nor wrote, is refused by name.

        The single-artifact shape the unfounded guard does not cover:
        one invented key presented with a content word ("Plot3 shows a
        curve"), or a report claim with no report call to back it. A
        close of a real figure, an honest self-correction
        ("Plot3 does not exist", "Plot3 et Plot4 n'existent pas"), or
        the acknowledgement that a key was invented are not flagged:
        the content-word and negation checks in
        :func:`fabricatedFigureKeys` / :func:`reportClaimed` are what
        keep the honest shape allowed.

        Returns the refusal reason, or None when the answer may stand.
        """
        # The report first: it is unambiguous and the field failure the
        # user reported most clearly.
        if reportClaimed(content) and not reports_written:
            return (
                'the answer says a report was written, but no '
                'report call succeeded this request -- the file it '
                'names was never produced. Write it: call %s and '
                'answer with the path that call returns.'
                % callSpellings('the reports'))
        # Only when the core can say which figures stand: with no ground
        # truth to answer against, a figure claim cannot be accused. A
        # core that can list but holds none (a fresh session) still does
        # ground a claim against it, and is not excluded here.
        if held is not None:
            invented = fabricatedFigureKeys(content, held, closed)
            if invented:
                return (
                    'the answer presents %s with a curve it does not '
                    'hold: the session has no such figure open -- %s '
                    'names what is, and it is not among '
                    'them. Draw it: call %s, '
                    'pill it onto its figure with into_figure_key where '
                    'a curve belongs, and answer from what that call '
                    'returns.'
                    % (' and '.join(sorted(invented)),
                       callSpelling('list_windows'),
                       callSpelling('plot_one')))
        return None

    def _artifactReanchor(self, user_prompt):
        """The one re-anchor for a claimed-but-undone figure or report:
        do the work, and answer from the calls, not from the claim.
        """
        return (
            '[SYSTEM FEEDBACK] That figure or report does not stand: '
            'no call of this request produced it. Do the work -- '
            '%s for the figure, or %s for the '
            'report -- and answer only from what those calls return. '
            'Request: "%s".'
            % (callSpelling('plot_one'),
               callSpellings('the reports'), user_prompt))

    def _unperformedWorkRefusal(self, content, acted_on, read_from,
                                closed_figures):
        """A change claimed on a figure this request neither worked on
        nor read back is refused by name.

        The shape the claims guards above do not reach: the figure
        **stands**, so the fabricated-artifact guard passes the key,
        yet the answer says a change landed on it that no call of this
        request performed -- the field repro of a curve "added" to a
        standing figure with no call at all, or a transform claimed
        done after the call that would have done it was refused. The
        ground a claim of work stands on is a call of the request: a
        write that did it (``acted_on``) or a read that checked it
        (``read_from``) -- a work the tools did not perform and a state
        they did not read back are not facts of this session. The
        honest shapes stand: a refusal reported for itself ("a été
        refusée"), a self-correction ("je n'avais pas ajouté"), and a
        state a read answered for.

        Returns the refusal reason, or None when the answer may stand.
        """
        ungrounded = unperformedWorkOn(
            content, set(acted_on) | set(read_from) | set(closed_figures))
        if not ungrounded:
            return None
        keys = ', '.join(sorted(ungrounded))
        return (
            'the answer says work landed on %s -- a curve added, a '
            'transform applied, an axis moved -- but no call of this '
            'request did that work on that figure, and no read of the '
            'figure checked it: the state of a figure is what the call '
            'that changed it, or read_figure(action="stats"), answers -- '
            'not what was said. If the call ran and was refused, report '
            'the refusal it named; otherwise do the work -- %s '
            'with into_figure_key to add the curve, '
            'transform_curve(operation=...) for a transform, '
            'configure_axes(operation=...) '
            'for the axes -- or read it back with '
            'read_figure(action="stats"), and '
            'answer only from what those calls return.'
            % (keys, callSpelling('plot_one')))

    def _workReanchor(self, user_prompt):
        """The one re-anchor for a claimed-but-unperformed work on a
        standing figure: do the work or read it, then answer from the
        calls.
        """
        return (
            '[SYSTEM FEEDBACK] That work on the figure did not run, '
            'and no read verified it. Do it -- %s with into_figure_key '
            'to add a curve, the curve transforms, the axis '
            'tools -- or read it back with '
            'read_figure(action="stats", figure_key), '
            'and answer only from what those calls return. '
            'Request: "%s".' % (callSpelling('plot_one'), user_prompt))

    def _unmadeNoteRefusal(self, content, journals_written):
        """A journal line claimed but not written this request, refused
        by name.

        The shape the figure and report guards do not reach: a note the
        answer says is in the journal -- "j'ai ajouté la note au
        cahier", "I've added it to the journal" -- but no call of this
        request wrote it (``add_note`` / ``edit_note`` / ``delete_note``
        all absent from ``journals_written``). The ground a claim of a
        note stands on is a call of the request that wrote it, the way
        a report stands on the ``plot_report`` that named its path; a
        note no call wrote is the same kind of single-artifact
        confabulation the report guard refuses. The honest shapes stand:
        a note that was written (``journals_written`` non-empty), a
        refusal reported for itself ("a été refusée", "je n'ai pas pu")
        and a self-correction ("je n'avais pas ajouté") -- the negations
        and the refusal words the other guards keep out are the same
        ones ``noteClaimed`` reads.

        The prose names the CALL the model can still type: the notebook
        answers one tool whose ``action`` says which write is meant, so
        the spelling comes from the table rather than from the gesture.

        Returns the refusal reason, or None when the answer may stand.
        """
        if journals_written:
            return None
        if not noteClaimed(content):
            return None
        return (
            'the answer says a note was added to the journal, but no '
            'call of this request wrote one: %s, %s and %s did not run '
            'this turn, so the line is not in the journal -- the user '
            'will look for it and not find it. Do the work instead: '
            'write it with %s -- author, title and the rest being '
            'optional -- or change it with %s, and answer only from '
            'what that call returns. If the call was refused, report '
            'the refusal it named.'
            % (offerHead('add_note'), offerHead('edit_note'),
               offerHead('delete_note'), callSpelling('add_note'),
               callSpelling('edit_note')))

    def _noteReanchor(self, user_prompt):
        """The one re-anchor for a claimed-but-unwritten journal line:
        write it or edit it, then answer from the call.
        """
        return (
            '[SYSTEM FEEDBACK] That line is not in the journal: no '
            'call of this request wrote it. Write it -- %s -- or edit '
            'it -- %s -- and answer only from what that call returns. '
            'Request: "%s".' % (callSpelling('add_note'),
                                callSpelling('edit_note'), user_prompt))

    def _destructiveRefusal(self, name, user_prompt):
        """The named refusal a destructive gesture receives on a request
        that does not ask for it.

        The rule the model sees, in the shape ``test_115``'s refusals
        wear: who is refused (the call it made, spelled as the tool set
        offers it), what it costs (the figure, the case and its own
        figures, or the whole session), that the refusal did not run the
        gesture (the same thing the user sees on screen still stands), and
        the one word that unblocks it (an ask in the user's own words,
        either language). The field report it answers: a figure that
        "created and then disappears" -- a close the model ran, on a
        request that did not name one.

        The guard is asked about the GESTURE (``DESTRUCTIVE_GESTURES``) and
        the words name the CALL: the windows group answers
        ``manage_window(action="close")``, and a refusal naming
        ``close_window`` would send the model to a name it is refused for
        asking.
        """
        taken = {
            'close_window': 'the figure it names',
            'close_case': 'the case it names and the figures that serve '
                          'it alone',
            'new_session': 'every case of the session and every figure',
        }[name]
        return (
            'the %s gesture takes %s away for good, and this request '
            'does not ask for it: "%s" names no figure or case to close '
            'and no reset. A figure is gone when it is closed -- a close '
            'is asked for, not taken. Nothing was closed by this call: '
            'the window and the session still stand. Run it only once '
            'the user asks for it in their own words ("close Plot5", '
            '"ferme la figure", "nouvelle session"), and answer from '
            'what that call returns.' % (offerHead(name), taken,
                                         user_prompt))

    def _sharedJournalRefusal(self, name, user_prompt):
        """The named refusal a shared-journal write receives on a
        request that does not ask for it.

        The rule the model sees, in the shape the rest of this file's
        refusals wear: who is refused, where the write would land (the
        shared journal the writers all read -- the note the user sees in
        the application, the viz_web page and the other writers'
        sessions), that the refusal did not run the gesture (the line is
        not in the journal), and the one word that unblocks it (an ask in
        the user's own words). The write the model reaches for on a "note
        down what I said" goes to the PERSONAL journal.

        The two vocabularies of a merged group apply here: the gate is
        asked about the GESTURE (``SHARED_JOURNAL_GESTURES`` holds
        members, and it is the gesture that wrote the line), while the
        words name the CALL -- the journals answer one name and their
        ``action`` says which write is meant, so a refusal naming
        ``add_note`` would send the model to a name it is refused for
        asking.
        """
        taken = {
            'add_note': 'a line the writers all read',
            'edit_note': 'a line the writers all read',
            'delete_note': 'a line the writers all read',
            'reindex_journals': 'an index the writers all read',
        }[name]
        return (
            'the %s gesture writes %s to the shared journal, and this '
            'request does not ask for it: "%s" does not name a '
            'journal to put a line in -- not a "publier au journal '
            'partagé", not a "share this", not a "cahier de manip". '
            'A shared journal is visible to the writers all read: '
            'every session and every writer on this machine, '
            'and the line stays. Nothing was written by this call: '
            'the shared journal still stands. Run it only once '
            'the user asks for it in their own words ('
            '("publier au journal partagé", "share this", '
            '"cahier de manip"), and answer from what that call '
            'returns.' % (offerHead(name), taken, user_prompt))

    def _pluginWindowRefusal(self, name, plugin, user_prompt):
        """The named refusal a plugin entry receives on a request that asks
        for no plugin window.

        The shape the other two gates' refusals wear: the call as the tool
        set offers it (``plugin(action="run")``, not the ``run_plugin``
        gesture behind it), what the call would have opened (a window of its
        own, over what the ask was drawing), that the refusal drew nothing,
        and the one word that unblocks it -- the plugin named in the user's
        own ask, in either language.

        It says what the ask did ask for, because the honest reading of the
        report is that a plugin window was believed to come with loading an
        IDS: it does not, and the report is the proof. When the user wanted
        that window in words that name no plugin, the answer is to name the
        entries ``plugin(action="list")`` gave and ask which one they mean
        -- not to take the window.
        """
        return (
            'the %s gesture draws the window of the plugin "%s" -- a window '
            'of its own, over what this request was drawing, and nothing '
            'here asked for it: "%s" names no plugin and no plugin window. '
            'Loading an IDS never opens one. Nothing was drawn by this '
            'call: the figures that stand still stand. Run it once the user '
            'asks in their own words ("lance le plugin %s", "ouvre '
            'l\'extension %s", or the plugin named as plugin(action="list") '
            'spelled it). If they asked for that window another way, name '
            'the entries that list answered and ask which one they mean.'
            % (offerHead(name), plugin, user_prompt, plugin, plugin))

    def _dispatch(self, name, args, requested_by='model', user_prompt=''):
        """Run one tool by name on the calling thread (the GUI thread,
        when reached through ``GuiDispatcher``).

        Before the call, the arguments are checked against the tool's own
        schema: an argument the tool does not take is refused by naming the
        parameter that is not there and the ones that are, so the model
        can correct the call. This is what a bare ``TypeError`` from
        Python would not do: it says "unexpected keyword argument", not
        which ones are expected. And when a neighbour of the same group
        (``tools.FAMILIES``) does take the stray, the refusal names that
        neighbour: a ``columns`` put on ``plot_one`` is a table asked with
        a single quantity's call, and pointing at ``plot_table`` is the
        short way back.

        And the destructive ones -- the three that erase bookkeeping,
        ``close_window`` / ``close_case`` / ``new_session`` -- are asked,
        not taken: a gesture the MODEL reaches for is refused when the
        user's request names no figure, case or session to close, no
        reset. The gesture the USER reaches for (``requested_by='user'``,
        the page's own button through ``callGesture``) owes no word: the
        click is the ask. A refusal never runs the gesture -- the figure,
        the case and the session it names still stand after a refused
        turn -- and it names the gesture and the rule, in the shape the
        rest of this file's refusals wear.

        The same asking covers the two other gestures that leave something
        on the screen the user never reached for: a write to the journal the
        writers all read (``SHARED_JOURNAL_GESTURES``) and the window a
        plugin entry draws (``PLUGIN_WINDOW_GESTURES``).
        """
        name, args = resolveCall(name, args or {})
        method = getattr(self.core, name, None)
        if method is None:
            raise ValueError(
                'the tool "%s" is not a gesture of this session' % name)
        unknown = unknownParameters(name, args)
        if unknown:
            raise ValueError(unknownParameterRefusal(name, unknown))
        missing = missingParameters(name, args)
        if missing:
            raise ValueError(missingParameterRefusal(name, missing))
        if (name in DESTRUCTIVE_GESTURES
                and requested_by == 'model'
                and not _userAskedForAClosure(user_prompt)):
            raise ValueError(self._destructiveRefusal(name, user_prompt))
        # The shared-journal write is the same shape asked a different
        # way: a gesture the MODEL reaches for, in a prompt that does not
        # name the journal it will put a line in, is refused by name.
        # The gesture the USER reaches for (``requested_by='user'``, the
        # page's button through ``callGesture``) is the ask. A write to
        # the PERSONAL journal does not answer this question: a note in
        # the user's own file is not put into the hands of the writers
        # all read, and the same call the model reaches for on
        # "note down what I said" is the one to run there.
        if (name in SHARED_JOURNAL_GESTURES
                and args.get('scope') == 'shared'
                and requested_by == 'model'
                and not _userAskedForAPublish(user_prompt)):
            raise ValueError(self._sharedJournalRefusal(name, user_prompt))
        # The third gate, on the same shape and a narrower word list: a
        # plugin entry draws a window of its own, and the report it answers
        # is a « charge l'equilibre, trace la pression » that came back with
        # an Equilibriumcharts window nobody asked for. Nothing else in the
        # application opens one -- a load runs ``QVizLoadOccurrence`` and no
        # plugin -- so the window was this call. The READ of what a case
        # offers is not asked about: ``plugin(action="list")`` opens nothing
        # and is asked before the ask is settled, which is why the gate is
        # keyed on the run and not on the group. Here the ask is not a
        # generic noun for what the window shows -- a "graphique" or a
        # "profil" is what ``plot`` already answers -- but the plugin named
        # as the call names it, or the word a plugin is asked under.
        if (name in PLUGIN_WINDOW_GESTURES
                and requested_by == 'model'
                and not _userAskedForAPluginWindow(user_prompt,
                                                   args.get('plugin', ''))):
            raise ValueError(
                self._pluginWindowRefusal(name, args.get('plugin', ''),
                                          user_prompt))
        # The last step of the seam, and the only one that leaves the
        # offered vocabulary: a merged group is offered one spelling for an
        # idea its gestures were written under another (`plot` asks every
        # mode for a `path`; the slice gesture has always taken a `leaf`).
        # The checks above ran on the spelling the MODEL typed, so a refusal
        # never names a parameter it was never offered; the core is handed
        # the one it takes.
        spelled = argumentsForMember(name, args)
        self.gestureIssued.emit(name, spelled)
        result = method(**spelled)
        if name == 'new_session':
            # A new session is a clean slate for the loop's own memory too,
            # not just for the core it closed. The core answered the reset
            # (every case view and figure gone); a loop that still carried
            # the turns it served would recite them on the next one -- the
            # "is a case open?" answered from memory that the field sent
            # back, and the missing figures after (a model that believes it
            # already drew a curve does not re-issue plot_one). This is the
            # one choke point both the page's New session button and the
            # agent's own new_session call pass through, so the reset lives
            # here and only after the core answered it: a new_session the
            # core refused never clears the memory.
            self.history = []
        return result


def _summarize(result, limit=120):
    """One line for the transcript: the value of the result, truncated."""
    if result is None:
        return '(no value)'
    if isinstance(result, dict):
        parts = []
        for key in list(result.keys())[:4]:
            val = str(result[key])[:30]
            parts.append('%s=%s' % (key, val))
        text = ', '.join(parts)
        if len(result) > 4:
            text += ' …(%d keys)' % len(result)
        return text[:limit]
    text = str(result)
    return text[:limit]
