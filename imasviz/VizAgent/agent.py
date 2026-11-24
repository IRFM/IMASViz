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
import logging
import re
import threading
from collections.abc import Mapping, Sequence

from PySide6.QtCore import QObject, Signal

from imasviz.VizAgent.tools import (
    SYSTEM_INSTRUCTIONS,
    CHAT_INSTRUCTIONS,
    TOOLS,
    TOOL_PARAMETERS,
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


# The loop's own surface: the tool names the model quotes to point the user
# at a gesture (restore_session in `restore_session(name="from_web")`)
# are the agent's own vocabulary, not names it recites from the case.
# `_unfoundedIdsRefusal` keeps them out of its count for exactly that
# reason: a "how do I do it later" answer is not a list.
_TOOL_NAMES = frozenset(t['function']['name'] for t in TOOLS)


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
                        if (name in ('plot_report', 'case_report',
                                    'case_ids_report')
                                and isinstance(result, dict)
                                and result.get('saved_to')):
                            reports_written.add(result['saved_to'])
                        if name == 'close_window':
                            key = (args or {}).get('key')
                            if key:
                                closed_figures.add(key)
                        # The journal line, on the strength of the call that
                        # earned it: a note the answer may say was written,
                        # because a call of this request wrote it -- a note
                        # no call wrote is what the guard refuses. Grounded
                        # on the success -- a refused call grounds nothing.
                        if name in SHARED_JOURNAL_GESTURES:
                            journals_written.add(name)
                        # The work and the reads of the request, per
                        # figure: a claim of a change on a figure stands
                        # on a successful call that did it (a draw into
                        # the figure, a transform, an axis move) or one
                        # that read it back -- grounded on the success,
                        # the way the report path is: a refused call
                        # grounds nothing.
                        if name in _WORK_GESTURES:
                            acted_on.update(
                                _groundedFigureKeys(args, result))
                        elif name in _READ_GESTURES:
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
            # that changed it, or curve_stats, answers, not what was said.
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
        return (
            'your answer presents a list of names, or a figure and a '
            'table of values, but no tool was called this request to '
            'ground it; a list, curve or number you recite is not the '
            'truth of this session. Ground it: the case\'s IDS with '
            'list_case_idss(uri) or list_idss(uri), the saved sessions '
            'with list_sessions(), the profile\'s arrays with '
            'get_signal(uri, path, ...) -- and show its curve with '
            'plot_one(uri, path, ...) -- and answer only from what those '
            'calls return.')

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
        arrays with ``get_signal``, draw the figure with ``plot_one`` --
        and answer only from what those calls return, so the next turn is
        either a real, tool-grounded answer or a repeated fabrication that
        the named refusal below finally turns away.
        """
        return (
            '[SYSTEM FEEDBACK] That answer named lists, figures, or '
            'values this request never read. Do the work: read the arrays '
            'with get_signal(uri, path, ...) and draw the owed curves '
            'with plot_one(uri, path, ...), and answer only from what '
            'those calls return. Request: "%s".' % user_prompt)

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
                'names was never produced. Write it: call '
                'plot_report(figure_key), case_report(uri) or '
                'case_ids_report(uri) and answer with the path that '
                'call returns.')
        # Only when the core can say which figures stand: with no ground
        # truth to answer against, a figure claim cannot be accused. A
        # core that can list but holds none (a fresh session) still does
        # ground a claim against it, and is not excluded here.
        if held is not None:
            invented = fabricatedFigureKeys(content, held, closed)
            if invented:
                return (
                    'the answer presents %s with a curve it does not '
                    'hold: the session has no such figure open -- '
                    'list_windows() names what is, and it is not among '
                    'them. Draw it: call plot_one(uri, path, ...), '
                    'pill it onto its figure with into_figure_key where '
                    'a curve belongs, and answer from what that call '
                    'returns.' % ' and '.join(sorted(invented)))
        return None

    def _artifactReanchor(self, user_prompt):
        """The one re-anchor for a claimed-but-undone figure or report:
        do the work, and answer from the calls, not from the claim.
        """
        return (
            '[SYSTEM FEEDBACK] That figure or report does not stand: '
            'no call of this request produced it. Do the work -- '
            'plot_one(uri, path, ...) for the figure, or '
            'plot_report(figure_key) / case_report(uri) / '
            'case_ids_report(uri) for the report -- and answer '
            'only from what those calls return. Request: "%s".'
            % user_prompt)

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
            'that changed it, or curve_stats, answers -- not what was '
            'said. If the call ran and was refused, report the refusal '
            'it named; otherwise do the work -- plot_one(uri, path, '
            '...) with into_figure_key to add the curve, '
            'scale_curve / shift_curve / normalize_curve for a '
            'transform, set_axis_range / set_log_scale / invert_axis '
            'for the axes -- or read it back with curve_stats, and '
            'answer only from what those calls return.' % keys)

    def _workReanchor(self, user_prompt):
        """The one re-anchor for a claimed-but-unperformed work on a
        standing figure: do the work or read it, then answer from the
        calls.
        """
        return (
            '[SYSTEM FEEDBACK] That work on the figure did not run, '
            'and no read verified it. Do it -- plot_one(uri, path, '
            '...) with into_figure_key, the curve transforms, the axis '
            'tools -- or read it back with curve_stats(figure_key), '
            'and answer only from what those calls return. '
            'Request: "%s".' % user_prompt)

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

        Returns the refusal reason, or None when the answer may stand.
        """
        if journals_written:
            return None
        if not noteClaimed(content):
            return None
        return (
            'the answer says a note was added to the journal, but no '
            'call of this request wrote one: add_note, edit_note and '
            'delete_note did not run this turn, so the line is not in '
            'the journal -- the user will look for it and not find it. '
            'Do the work instead: write it with add_note(scope, text, '
            'author=..., ...) or change it with edit_note(scope, '
            'note_id, ...) -- and answer only from what that call '
            'returns. If the call was refused, report the refusal it '
            'named.')

    def _noteReanchor(self, user_prompt):
        """The one re-anchor for a claimed-but-unwritten journal line:
        write it or edit it, then answer from the call.
        """
        return (
            '[SYSTEM FEEDBACK] That line is not in the journal: no '
            'call of this request wrote it. Write it -- add_note('
            'scope, text, ...) or edit_note(scope, note_id, ...) -- '
            'and answer only from what that call returns. '
            'Request: "%s".' % user_prompt)

    def _destructiveRefusal(self, name, user_prompt):
        """The named refusal a destructive gesture receives on a request
        that does not ask for it.

        The rule the model sees, in the shape ``test_115``'s refusals
        wear: who is refused (the gesture, by name), what it costs
        (the figure, the case and its own figures, or the whole session),
        that the refusal did not run the gesture (the same thing the user
        sees on screen still stands), and the one word that unblocks it
        (an ask in the user's own words, either language). The field
        report it answers: a figure that "created and then disappears"
        -- a close the model ran, on a request that did not name one.
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
            'what that call returns.' % (name, taken, user_prompt))

    def _sharedJournalRefusal(self, name, user_prompt):
        """The named refusal a shared-journal write receives on a
        request that does not ask for it.

        The rule the model sees, in the shape the rest of this file's
        refusals wear: who is refused (the gesture, by name), where the
        write would land (the shared journal the writers all read --
        the note the user sees in the application, the viz_web page
        and the other writers' sessions), that the refusal did not run
        the gesture (the line is not in the journal), and the one word
        that unblocks it (an ask in the user's own words). The write
        the model reaches for on a "note down what I said" goes to
        the PERSONAL journal.
        """
        taken = {
            'add_note': 'a line the writers all read',
            'edit_note': 'a line the writers all read',
            'delete_note': 'a line the writers all read',
            'reindex_journals': 'an index the writers all read',
        }[name]
        return (
            'the %s gesture writes to the shared journal, and this '
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
            'returns.' % (name, user_prompt))

    def _dispatch(self, name, args, requested_by='model', user_prompt=''):
        """Run one tool by name on the calling thread (the GUI thread,
        when reached through ``GuiDispatcher``).

        Before the call, the arguments are checked against the tool's own
        schema: an argument the tool does not take is refused by naming the
        parameter that is not there and the ones that are, so the model
        can correct the call. This is what a bare ``TypeError`` from
        Python would not do: it says "unexpected keyword argument", not
        which ones are expected.

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
        """
        method = getattr(self.core, name, None)
        if method is None:
            raise ValueError(
                'the tool "%s" is not a gesture of this session' % name)
        unknown = unknownParameters(name, args or {})
        if unknown:
            allowed = ', '.join(sorted(
                TOOL_PARAMETERS[name].get('properties', {})))
            raise ValueError(
                '"%s" is not a parameter of the %s tool: it takes %s. '
                'Answer with the parameters the tool names.'
                % (unknown[0], name, allowed))
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
        self.gestureIssued.emit(name, args or {})
        result = method(**args)
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


def _bareNames(text):
    """The snake_case names that stand on their own in that text.

    A name that is a segment of a longer spelling is not one of them --
    ``magnetics.flux_loop[0].flux.data`` is a path, ``west/3/54924`` a
    branch of one, ``rapport_flux_loop_10.html`` a file (a dot followed
    by two or more letters: an extension, not the period of the
    sentence, which is why ``equilibrium_time`` at the end of one still
    counts). Nor is the loop's own tool vocabulary: the names in
    ``TOOLS`` are quoted to point the user at a gesture, not recited
    from the case. What is left is the set of names the text is
    presenting, if it is presenting any.
    """
    names = set()
    for m in re.finditer(r'\b[a-z][0-9a-z]*(?:_[0-9a-z]+)+\b',
                         text.lower()):
        name = m.group(0)
        if name in _TOOL_NAMES:
            continue
        before = text[m.start() - 1] if m.start() else ''
        after = text[m.end()] if m.end() < len(text) else ''
        if before in './':
            continue
        if after == '/':
            continue
        if after == '.' and re.match(r'[A-Za-z]{2,}', text[m.end() + 1:]):
            continue
        names.add(name)
    return names


# The word families the fabricated-artifact guard uses to tell the
# *claim* (the fabrication it refuses) from the *honest mention* (the
# self-correction it must allow). A content word says the answer
# presents the figure with data ("Plot3 shows a curve"), not just names
# it ("Plot3 was closed" is in the ground set, "Plot3 does not exist"
# is negated, "compare Plot1 and Plot5" names Plot5 with no content,
# so none of those stand as a fabrication). A negation within the same
# clause is the honest shape ("the report was never written").
# The figure-key spellings a session can produce (the ``FigureTypes``
# kinds without their trailing number): the guard scans these even while
# no figure is open, so a fabrication on a fresh session is caught. They
# mirror ``FigureTypes`` in ``imasviz/VizUtils/QVizGlobalValues.py``; the
# agent panel prefix is not a data figure and is not listed here.
_FIGURE_KEY_PREFIXES = (
    'StackedPlotView:', 'TablePlotView:', 'EquiPlotView:', 'PlotView:',
    'EquiSurfaces:', 'Image', 'Plot',
)
_FIGURE_CONTENT_WORDS = (
    'shows', 'holds', 'contains', 'displays', 'value', 'values',
    'sample', 'samples', 'curve', 'curves', 'points', 'point',
    'data', 'tracé', 'trace', 'montre', 'contient', 'valeur',
    'valeurs', 'échantillon', 'échantillons', 'courbe', 'courbes',
    'donnée', 'données', 'figure', 'graphe',
)
# A *claim* is a first-person or present-assertion voice near the report
# reference: "j'ai généré", "le rapport est prêt", "I generated the
# report". A past participle alone -- "``rapport_flux.html`` généré" in a
# quoted log, "``[INFO]`` Rapport HTML généré:" as a log line label -- is
# a description or a quotation, not a claim, and stays allowed (the
# honest "le rapport n'a jamais été écrit" is negated into the refusal
# below, the quoted log simply has no agent voice to key on).
_AGENT_VOICE = (
    "j'ai", "j' ai", "est prêt", "est généré", "est écrit",
    "est produit", "est ready", "i generated", "i wrote", "i saved",
    "i created", "i have", "the report is", "we generated", "we saved",
    "we wrote", "generated the report", "wrote the report",
    "saved the report",
)
_NEGATIONS = (
    'not', "n't", 'never', 'no report', 'no html',
    'n\'ai pas', "n'a pas", "n'a jamais", 'jamais',
    'n\'existe', "n'existe", 'n\'existent', "n'existent",
    'inexistant', 'impossible', 'sans rapport', 'sans html',
    'invented', 'inventée', 'inventées', 'inventé', 'inventés',
)


def reportClaimed(text):
    """Whether the text asserts -- in the agent's own voice -- that a
    report was written.

    A ``.html`` path or the report noun is only a *reference*; it becomes
    a *claim* when a first-person or present-assertion voice sits near it
    ("j'ai généré", "le rapport est prêt", "I generated the report"). A
    quoted log ("``Rapport`` : rapport_…html généré"), a past participle
    with no agent subject, and a negation ("le rapport n'a jamais été
    écrit") are descriptions or self-corrections, not claims -- this
    answers False for each, and the guard lets them stand.
    """
    text = (text or '').lower()
    # The one reference the guard can key on: a ``.html`` file on disk, or
    # the report noun. Without either there is no report to claim.
    if not (re.search(r'report|rapport|\.html', text)):
        return False
    # A claim is a reference with an agent voice near it and no negation.
    for m in re.finditer(r'rapport|report|\.html', text):
        window = text[max(0, m.start() - 70):m.end() + 40]
        if not any(voice in window for voice in _AGENT_VOICE):
            continue
        if any(neg in window for neg in _NEGATIONS):
            continue
        return True
    return False


# A note is a *line in a journal*, and the one reference the guard
# keys on is that noun: "note", "cahier", "journal", "mémo". A claim is
# a noun with a *write verb* near it and no negation -- the same
# apartness the fabricated-artifact guard keeps between a report
# claimed and one that was refused. The voice is a verb at a word
# boundary (not a bare substring): "node"/"nodes" (tree paths) and
# "address" do not read as "note" or "add", and "j'ai lu tes notes" is a
# read with no write verb near the noun, so both stand out of the guard.
# A negation near the noun -- "n'ai pas", "n'avais pas", "refusée",
# and in English "not"/"never" -- is the honest refusal or
# self-correction the guard lets stand.
_NOTE_NOUN_RE = re.compile(
    r'\bnotes?\b|\bcahier\b|\bjournal\b|\bmémo\b|\bmemo\b')
_NOTE_VOICE_RE = re.compile(r'''
    # French write verbs, as stems so the -ée / -és forms land
    \bajout\w*
  | \bnot(?:é|ée|er)\w*
  | \binscrit\w*
  | \benregistr\w*
  | \bconsign\w*
  | \brang(?:é|ée)s?
  # English write verbs, at a word boundary so "add" is not "address"
  | \badd(?:ed|ing)?\b
  | \blogged\b
  | \brecord(?:ed|ing)?\b
  | \bnoted\b
  | \b(?:kept|keep)s?\s+a\s+note\b
  | \bsaved?\s+the\s+note\b
  | \bwrote\b
''', re.VERBOSE)
_NOTE_NEGATION_RE = re.compile(
    r'\bpas\b|\bnot\b|\bnever\b|\brefus\w*|\bimpossible\b')


def noteClaimed(text):
    """Whether the text asserts -- in the agent's own voice -- that a
    note / a journal line was written, edited, or deleted.

    A ``note`` / ``cahier`` / ``journal`` noun near a write verb and no
    negation is the claim the guard refuses; a read ("j'ai lu tes
    notes", "ton cahier contient déjà une note sur le flux"), a refusal
    ("je n'ai pas pu la noter", "la note n'a pas été ajoutée", "la
    publication au journal partagé a été refusée"), and a
    self-correction ("je n'avais pas ajouté") are honest shapes and
    stand out of the guard the way a report that was never written does.
    """
    text = (text or '').lower()
    for m in _NOTE_NOUN_RE.finditer(text):
        window = text[max(0, m.start() - 70):m.end() + 40]
        if not _NOTE_VOICE_RE.search(window):
            continue
        if _NOTE_NEGATION_RE.search(window):
            continue
        return True
    return False


def _figureKeyMentions(text, known):
    """[(spelling, start, end)] of each figure key the text spells.

    The kinds the session can produce are scanned (so a key on a fresh
    session is read), then the keys the session names in ``known`` in
    their own spelling. Longest kind first, and a boundary before the
    stem and a digit after it, so a short stem ("plot") does not match
    inside a longer key ("tableplotview:1") and "plot-view" is not a
    key. The text is read lowercased, and the spellings are the ones
    the session uses. Shared by the two claim guards, so the two read
    the same key out of the same sentence.
    """
    text = (text or '').lower()
    canonical = {}
    for prefix in _FIGURE_KEY_PREFIXES:
        canonical.setdefault(prefix.lower(), prefix)
    for key in set(known or set()):
        if key:
            stem = re.sub(r'[0-9]+$', '', key)
            if stem:
                canonical.setdefault(stem.lower(), stem)
    if not canonical:
        return []
    mentions = []
    for stem, spelling in sorted(canonical.items(),
                                 key=lambda pair: len(pair[1]),
                                 reverse=True):
        pat = r'(?<![0-9A-Za-z_])' + re.escape(stem) + \
            r'\d+(?![0-9A-Za-z_])'
        for m in re.finditer(pat, text):
            mentions.append((spelling + m.group(0)[len(stem):],
                             m.start(), m.end()))
    return mentions


def fabricatedFigureKeys(text, held, closed):
    """The figure keys the session does not hold and the answer presents
    with a content word, un-negated.

    The keys the session actually holds now (``held``) and the ones a
    close this request ran (``closed``) form the ground set: a figure
    the loop never drew and never closed is not grounded. The kinds the
    session can produce are scanned (so a fabrication on a fresh session
    is caught, not just the invented keys beside real ones), matched
    case-insensitively against the answer and reported back in the
    canonical spelling the session uses. A content word, no negation
    nearby, and a key outside the ground set is what the guard refuses.
    """
    text = (text or '').lower()
    ground = {k.lower() for k in (set(held or set()) | set(closed or set()))
              if k}
    if not any(word in text for word in _FIGURE_CONTENT_WORDS):
        return set()
    found = set()
    for spelling, start, end in _figureKeyMentions(
            text, set(held or set()) | set(closed or set())):
        if spelling.lower() in ground:
            continue
        window = text[max(0, start - 40):end + 40]
        if any(neg in window for neg in _NEGATIONS):
            continue
        found.add(spelling)
    return found


# The change-claim words the work guard cross-checks against the calls
# of the request: a verb the answer uses to say a draw, a curve
# transform or an axis state LANDED on a figure -- "j'ai ajouté",
# "tracée", "multipliée par 3", "en log", "pinned", "reset". These say
# work is done, and the guard asks of the loop what call of this
# request did the work on that figure, or read it back. A *description*
# word ("montre", "contient") is not in this family on purpose:
# describing a standing figure is what a read answers for, and the
# ground it applies to is the read, not the write -- the same apartness
# the content word and the assertion keep in the fabricated-artifact
# guard. The French forms are matched as the accented stem they all
# carry ("ajouté" is in "ajoutée"/"ajoutés"/"ajoutées" and not in
# "ajouter"; "tracé" is not in "trace"), the English as word forms, so
# "trace" (the noun) is not "traced" (the voice).
_CHANGE_CLAIM_SUBSTRINGS = (
    'ajout', 'tracé', 'multiplié', 'décalé', 'normalisé',
    'réinitialisé', 'retiré', 'supprimé', 'inversé', 'restauré',
    'échelle log', 'en log', 'logarithmique', 'borné',
)
_CHANGE_CLAIM_RE = re.compile(
    r'\badded?\b|\btraced?\b|\bmultiplied\b|\bshifted?\b|'
    r'\bnormalized?\b|\breset\b|\brestored?\b|\bremoved?\b|'
    r'\binverted?\b|\bscaled?\b|\bpinned?\b|\blog\s?axis\b|\blog\s?scale\b')
# A refusal or a failure word near the claim is the report of the loop
# itself ("a été refusée", "n'a pas pu", "not able to") and stands on
# whatever the figure is: the guard refuses the work *done*, not the
# reason it was not. "n't" keeps its accent-free shape; "not" and
# "pas" are worded, because "note" and "passer" carry them unaided.
_CLAIM_NEGATIONS = tuple(neg for neg in _NEGATIONS if neg != 'not') + (
    'refusé', 'échou', 'failed', 'could not', 'not able')
_CLAIM_NEGATION_RE = re.compile(r'\bnot\b|\bpas\b|\bnever\b')
# The gestures whose success grounds a claim of work on, or a read
# back of, the figure they name: the draws (a curve into the figure, a
# window of its own) and the curve transforms and the axis moves on
# one side, the reads that answer for what a figure holds on the
# other. A success is one that found its figure (`_windowForKey` is
# what refuses a key it does not hold), so the ask of such a call is as
# grounded as its answer.
_WORK_GESTURES = frozenset((
    'plot_one', 'plot_slice', 'plot_selection',
    'plot_table', 'plot_stacked', 'equilibrium_surfaces',
    'equilibrium_at_time', 'scale_curve', 'shift_curve',
    'normalize_curve', 'reset_curve', 'remove_curve', 'set_axis_range',
    'set_log_scale', 'invert_axis'))
# `list_windows` is a read of the session's own figures: the answer is
# the standing windows, and a claim of a state on one of them that the
# read answered for stands the way a `curve_stats` read does.
_READ_GESTURES = frozenset(('curve_stats', 'export_curve', 'list_windows'))


def _groundedFigureKeys(args, result):
    """The figure keys a successful call stands behind.

    The key the answer spells (``figure`` / ``window`` / ``figures``)
    and the key the call asked of (``figure_key``, ``into_figure_key``):
    a gesture that answered is one that found its figure, and a read
    whose answer does not spell it (``export_curve`` names its file) is
    grounded on the ask alone.
    """
    keys = []
    for ask in ('figure_key', 'into_figure_key'):
        value = (args or {}).get(ask)
        if isinstance(value, str) and value:
            keys.append(value)
    if isinstance(result, dict):
        for field in ('figure', 'window'):
            value = result.get(field)
            if isinstance(value, str) and value:
                keys.append(value)
        for value in result.get('figures') or ():
            if isinstance(value, str):
                keys.append(value)
    # A list result is the window list `list_windows` answers: each entry
    # carries the key of the window it is, and a claim on one of them
    # stands on that read the way a `curve_stats` read does.
    if isinstance(result, list):
        for entry in result:
            if isinstance(entry, dict) and isinstance(entry.get('key'), str):
                keys.append(entry['key'])
    return set(keys)


def _changeClaimNear(text, start, end):
    """Whether an un-negated change claim sits within reach of the
    span [start, end) -- the sentence between the key and the verb is
    what "sur Plot1, j'ai ajouté la température" reads as."""
    mid = (start + end) / 2.0
    claims = []
    for token in _CHANGE_CLAIM_SUBSTRINGS:
        i = 0
        while True:
            i = text.find(token, i)
            if i < 0:
                break
            claims.append((i, i + len(token)))
            i += 1
    for m in _CHANGE_CLAIM_RE.finditer(text):
        claims.append((m.start(), m.end()))
    for claim_start, claim_end in claims:
        if min(abs(claim_start - mid), abs(claim_end - mid)) > 60:
            continue
        window = text[max(0, claim_start - 40):claim_end + 40]
        if any(neg in window for neg in _CLAIM_NEGATIONS) or \
                _CLAIM_NEGATION_RE.search(window):
            continue
        return True
    return False


def unperformedWorkOn(text, ground):
    """The figure keys the answer presents with a change claim -- a
    curve added, a transform applied, an axis moved -- that no call of
    the request stands behind.

    ``ground`` is the union of the keys a call of this request worked
    on (a draw into the figure, a curve transform, an axis move), read
    back (``curve_stats``, ``export_curve``), or closed. A claim near a
    grounded key stands; the rest is a claim of work the tools did not
    do -- and it is refused by name, re-anchored once to do the work or
    read it, refused again on a second claim. A refusal or a failure
    word near the claim is the honest report of the call that was
    refused, and it stands on whatever the figure is. A description
    word is not in the claim family on purpose: "Plot1 montre la
    pression" says a state, and the loop that says it is the one that
    read it, not one that invented it.
    """
    text = (text or '').lower()
    if not any(token in text for token in _CHANGE_CLAIM_SUBSTRINGS) and \
            not _CHANGE_CLAIM_RE.search(text):
        return set()
    ground_low = {k.lower() for k in (ground or set()) if k}
    found = set()
    for spelling, start, end in _figureKeyMentions(text, ground):
        if spelling.lower() in ground_low:
            continue
        if _changeClaimNear(text, start, end):
            found.add(spelling)
    return found


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
