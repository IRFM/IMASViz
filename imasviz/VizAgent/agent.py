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

    def ask(self, user_prompt, max_turns=8):
        """Run the agent loop, blocking until it is done.

        The caller decides what thread to call this from. In the panel,
        it is called from a worker thread and the caller waits for the
        ``askFinished`` signal. In the test, it is called synchronously
        from the test thread.
        """
        self._stop_requested = False
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
                    except Exception as e:
                        self.transcriptLine.emit(
                            '  ← %s: REFUSAL — %s' % (name, e))
                        tool_result = {'result': None, 'error': str(e)}
                    messages.append({
                        'role': 'tool',
                        'tool_call_id': 'call_%d' % i,
                        'name': name,
                        'content': json.dumps(tool_result),
                    })
                continue

            # --- Final answer -----------------------------------------------
            refusal = None if called_a_tool \
                else self._unfoundedIdsRefusal(response.content)
            if refusal is not None:
                # The answer recites an inventory instead of reading it from
                # the case: refuse it by name, the way a refused gesture is
                # named, and point at the call that would ground it.
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
        self.transcriptLine.emit(
            'Stopped: max_turns reached (%d).' % max_turns)
        self.askFinished.emit('max_turns reached (%d)' % max_turns)

    def _unfoundedIdsRefusal(self, content):
        """A final answer that presents an inventory of case identifiers with
        no case tool called in this request is refused by name.

        Returns the reason to refuse, or None when the answer may stand. The
        signals are the *shapes* of an ungrounded inventory, not a claim
        about any specific name: three or more snake_case identifiers (the
        spelling of an IDS name or an IMAS path), or a markdown table of
        three or more data rows. A recited name such as "equilibrium" is as
        much a confabulation as a made-up one, so the guard keys on the
        list shape with no call to ground it, and does not try to match
        names.
        """
        text = content or ''
        identifiers = re.findall(
            r'\b[a-z][0-9a-z]*(?:_[0-9a-z]+)+\b', text.lower())
        # A markdown row is a line whose first non-space char is a pipe, and
        # which is neither blank nor the all-pipe separator row.
        table_rows = [
            line for line in text.splitlines()
            if line.strip().startswith('|')
            and not re.fullmatch(r'\|[\s:|-]+\|?', line.strip())
        ]
        if len(identifiers) < 3 and len(table_rows) < 3:
            return None
        return (
            'your answer presents a list of case names, but no case tool was '
            'called this request; a list you recite is not the case\'s '
            'truth. Open the case and read it back with list_case_idss(uri) '
            'or list_idss(uri), and answer only from the names and '
            'occurrences that call returns.')

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
