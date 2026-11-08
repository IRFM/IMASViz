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

from PySide6.QtCore import QObject, Signal

from imasviz.VizAgent.tools import (
    SYSTEM_INSTRUCTIONS,
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

# The loop's own surface: the tool names the model quotes to point the user
# at a gesture (restore_session in `restore_session(name="from_web")`)
# are the agent's own vocabulary, not names it recites from the case.
# `_unfoundedIdsRefusal` keeps them out of its count for exactly that
# reason: a "how do I do it later" answer is not a list.
_TOOL_NAMES = frozenset(t['function']['name'] for t in TOOLS)


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
    askFinished = Signal(object)

    def __init__(self, core, llm, dispatcher, main_window=None, api=None):
        super(AgentLoop, self).__init__()
        self.core = core
        self.llm = llm
        self.dispatcher = dispatcher
        self.main_window = main_window
        self.api = api
        self.history = []
        self._stop_requested = False

    def ask(self, user_prompt, max_turns=12):
        """Run the agent loop, blocking until it is done.

        The caller decides what thread to call this from. In the panel,
        it is called from a worker thread and the caller waits for the
        ``askFinished`` signal. In the test, it is called synchronously
        from the test thread.
        """
        self._stop_requested = False
        # A deflected final answer (the work handed back to the user) is
        # re-anchored once and then refused; a new ask restarts the budget, so
        # each request gets its own single re-anchor instead of a shared one.
        self._reanchors = 0
        try:
            self._run(user_prompt, max_turns)
        except Exception as e:
            self.transcriptLine.emit('ERROR: %s' % e)
            self.askFinished.emit(str(e))
        # askFinished was already emitted by _run; this is the safety
        # net for an unexpected exception.

    def stop(self):
        """Request the loop to stop at the next turn boundary."""
        self._stop_requested = True

    def _run(self, user_prompt, max_turns):
        """The actual loop. Runs in whatever thread called ``ask``."""
        messages = [{'role': 'system', 'content': SYSTEM_INSTRUCTIONS}]
        messages += list(self.history)
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

        for turn in range(max_turns):
            if self._stop_requested:
                self.transcriptLine.emit(
                    'Stopped: user requested stop before turn %d.' % turn)
                self.askFinished.emit('user requested stop')
                return

            # --- LLM call ---------------------------------------------------
            try:
                response = self.llm.chat(messages, tools=TOOLS)
            except ValueError as e:
                # LLMClient raises ValueError for truncation and empty content
                # (the named refusal); the test stand-in returns the
                # LLMResponse and the checks below catch the same cases.
                self.transcriptLine.emit(
                    'REFUSAL: %s (turn %d)' % (e, turn))
                self.askFinished.emit(str(e))
                return
            except Exception as e:
                self.transcriptLine.emit(
                    'REFUSAL: LLM call failed — %s' % e)
                self.askFinished.emit(str(e))
                return

            # Named refusals, checked here so a stand-in LLM that returns
            # the LLMResponse directly (without raising) is caught too:
            if response.finish_reason == 'length':
                self.transcriptLine.emit(
                    'REFUSAL: response truncated by max_tokens (turn %d)'
                    % turn)
                self.askFinished.emit(
                    'response truncated by max_tokens (turn %d)' % turn)
                return
            if not response.content and not response.tool_calls:
                self.transcriptLine.emit(
                    'REFUSAL: LLM returned empty content (turn %d)' % turn)
                self.askFinished.emit(
                    'LLM returned empty content (turn %d)' % turn)
                return

            if response.content:
                self.transcriptLine.emit('LLM: %s' % response.content)

            # --- Tool calls -------------------------------------------------
            if response.tool_calls:
                called_a_tool = True
                messages.append({
                    'role': 'assistant', 'content': None,
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
                    self.transcriptLine.emit('  → %s(%s)' % (
                        name, json.dumps(args)[:80]))
                    try:
                        result = self.dispatcher.call(
                            lambda n=name, a=args: self._dispatch(n, a))
                        summary = _summarize(result)
                        self.transcriptLine.emit(
                            '  ← %s: %s' % (name, summary))
                        tool_result = {'result': result, 'error': None}
                        last_action = '%s: %s' % (name, summary)
                    except Exception as e:
                        self.transcriptLine.emit(
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
            if not called_a_tool:
                refusal = self._unfoundedIdsRefusal(response.content)
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
                    self.transcriptLine.emit('REFUSAL: %s' % refusal)
                    messages.append({
                        'role': 'user',
                        'content': self._reanchor(user_prompt, last_action),
                    })
                    continue
            if refusal is not None:
                # Either it recites a case inventory it never read (the
                # unfounded guard), or it deflects off the work it already did
                # and the one re-anchor did not cure it. In both cases refuse
                # by name, the way a refused gesture is named.
                self.transcriptLine.emit('REFUSAL: %s' % refusal)
                self.askFinished.emit(refusal)
                return
            self.history.append({'role': 'user', 'content': user_prompt})
            self.history.append({
                'role': 'assistant', 'content': response.content,
            })
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
        self.transcriptLine.emit(stopped)

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
            'your answer presents a list of names, but no tool was called '
            'this request to ground it; a list you recite is not the '
            'truth of this session. Ground it: the case\'s IDS with '
            'list_case_idss(uri) or list_idss(uri), the saved sessions '
            'with list_sessions() -- and answer only from what that call '
            'returns.')

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
        request it was given and the work it produced, after a deflection."""
        return (
            'You already ran the tools for this request: the last one was '
            '"%s". The request was: "%s". Give your final answer now, '
            'grounded in what those tools returned. Do not ask the user to '
            'restate the request, and do not say nothing was done when it '
            'was.' % (last_action, user_prompt))

    def _dispatch(self, name, args):
        """Run one tool by name on the calling thread (the GUI thread,
        when reached through ``GuiDispatcher``).

        Before the call, the arguments are checked against the tool's own
        schema: an argument the tool does not take is refused by naming the
        parameter that is not there and the ones that are, so the model
        can correct the call. This is what a bare ``TypeError`` from
        Python would not do: it says "unexpected keyword argument", not
        which ones are expected.
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
        return method(**args)


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
