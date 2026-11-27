# Copyright holders : Commissariat à l'Energie Atomique et aux Energies
# Alternatives (CEA), France; and Laboratory for Engineering Design - LECAD,
# University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C
# open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted
# upon downloading the software and/or exercising any of the rights granted
# under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The agent's cost accounting and the bounded history.

The loop carries its own memory across asks, and every ask re-sends it to
the model -- so an unbounded history grows with the session while the
user sees nothing of it. What this file pins, scripted, off the case:

* the token accounting: a server that reports a per-call usage is read
  into the transcript (one line per ask) and into ``loop.last_usage`` --
  prompt / completion / total / turns, summed over the ask; a stand-in
  that answers no usage is unmeasured, never zero, and says nothing;
* the bounded history: the last turns stand exactly as they were, tool
  traffic and all, and the older ones fold into one bracketed summary
  line; the fold is idempotent (a summary is never re-nested or
  re-counted), the final turn of the ask is never folded away, and the
  byte budget is the hard cap.
"""

import json

from imasviz.VizAgent.agent import (
    MAX_HISTORY_CHARS,
    MAX_HISTORY_TURNS,
    AgentLoop,
    _compactHistory,
)
from imasviz.VizAgent.llm_client import LLMResponse


class FakeLLMClient:
    """A scripted LLM: it returns the next response in its queue, and
    records every message list it was handed, in order."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, messages, tools=None, **kwargs):
        self.calls.append({'messages': list(messages), 'tools': tools})
        if not self.responses:
            raise AssertionError('FakeLLMClient: no more scripted responses')
        return self.responses.pop(0)


class FakeCore:
    """The one gesture the summed-usage test drives: it answers, so a
    tool call of the turn is a success the loop can ground on."""

    def list_cases(self):
        return [{'uri': 'imas:hdf5?path=/fake', 'dd_version': '3.35.0'}]


class FakeDispatcher:
    """A synchronous dispatcher: it runs the function on the calling thread."""

    def call(self, function, timeout=300.0):
        return function()


def _turn(i):
    """One accepted turn, as the loop stores it: the ask and the final answer."""
    return [{'role': 'user', 'content': 'ask %d' % i},
            {'role': 'assistant', 'content': 'answer %d' % i}]


def _history(n):
    return [m for i in range(n) for m in _turn(i)]


def _build(llm, history=None):
    loop = AgentLoop(core=FakeCore(), llm=llm,
                     dispatcher=FakeDispatcher(), main_window=None, api=None)
    loop.history = list(history or [])
    return loop


# ------------------------------------------------------------- usage

def test_the_usage_of_an_ask_is_reported_once(qapp):
    """A server that reports a usage is summed over the ask: the line
    names prompt / completion / total / turns, and ``last_usage`` carries
    the same number."""
    llm = FakeLLMClient([
        LLMResponse(content='answer.', finish_reason='stop',
                    usage={'prompt_tokens': 100, 'completion_tokens': 40,
                           'total_tokens': 140}),
    ])
    loop = _build(llm)
    errors = []
    loop.askFinished.connect(errors.append)
    full = []
    loop.fullLine.connect(full.append)
    loop.ask('read the case', tools_mode='hide')
    assert errors == [None]
    assert loop.last_usage == {'prompt': 100, 'completion': 40,
                               'total': 140, 'turns': 1}
    assert any('Tokens:' in line and 'prompt 100' in line
               and 'completion 40' in line and 'total 140' in line
               and 'over 1 turn' in line
               for line in full), full


def test_the_usage_line_is_cut_from_the_live_view_in_hide_mode(qapp):
    """``hide`` cuts the traffic from the live view; the tokens line is
    chrome, and it is cut the same way. ``verbose`` carries it live."""
    for mode, live_expected in (('hide', False), ('verbose', True)):
        llm = FakeLLMClient([
            LLMResponse(content='answer.', finish_reason='stop',
                        usage={'prompt_tokens': 5, 'completion_tokens': 3,
                               'total_tokens': 8}),
        ])
        loop = _build(llm)
        lines = []
        loop.transcriptLine.connect(lines.append)
        loop.ask('read the case', tools_mode=mode)
        assert any('Tokens:' in line for line in lines) == live_expected, mode


def test_a_stand_in_that_answers_no_usage_says_nothing(qapp):
    """``usage=None`` is unmeasured, never zero: no line, no number."""
    llm = FakeLLMClient([
        LLMResponse(content='answer.', finish_reason='stop'),
    ])
    loop = _build(llm)
    full = []
    loop.fullLine.connect(full.append)
    loop.ask('read the case', tools_mode='hide')
    assert loop.last_usage is None
    assert not any('Tokens:' in line for line in full), full


def test_the_usage_is_summed_across_the_turns_of_an_ask(qapp):
    """Several calls in one ask sum into one number."""
    llm = FakeLLMClient([
        LLMResponse(content='',
                    tool_calls=[{'name': 'manage_case',
                                 'args': {'action': 'list'}}],
                    finish_reason='tool_calls',
                    usage={'prompt_tokens': 30, 'completion_tokens': 5,
                           'total_tokens': 35}),
        LLMResponse(content='answer.', finish_reason='stop',
                    usage={'prompt_tokens': 60, 'completion_tokens': 20,
                           'total_tokens': 80}),
    ])
    loop = _build(llm)
    errors = []
    loop.askFinished.connect(errors.append)
    loop.ask('list the cases', tools_mode='verbose')
    assert errors == [None]
    assert loop.last_usage['prompt'] == 90
    assert loop.last_usage['completion'] == 25
    assert loop.last_usage['total'] == 115
    assert loop.last_usage['turns'] == 2


# ------------------------------------------------------- the history

def test_a_short_history_is_left_alone(qapp):
    """The last turns stand exactly as they were."""
    history = _history(MAX_HISTORY_TURNS)
    assert _compactHistory(history) == history


def test_the_oldest_turns_are_folded_into_one_summary_line(qapp):
    """Past the keep window, the oldest turns become one summary line;
    the kept turns stand whole, and the summary names the fold."""
    history = _history(MAX_HISTORY_TURNS + 3)
    folded = _compactHistory(history)
    summary = folded[0]
    assert summary['role'] == 'user'
    assert summary['content'].startswith('[Earlier turns:')
    assert '3 turns folded' in summary['content']
    assert 'ask 0' in summary['content']
    # The kept window is the LAST turns, whole.
    kept_asks = [m['content'] for m in folded[1:]
                 if m.get('role') == 'user']
    assert kept_asks == ['ask %d' % i
                         for i in range(3, MAX_HISTORY_TURNS + 3)]


def test_the_fold_is_idempotent_no_re_nesting(qapp):
    """Folding a folded history never nests a summary inside a summary and
    never re-counts the fold: the summary stands as it was."""
    history = _history(MAX_HISTORY_TURNS + 1)
    once = _compactHistory(history)
    twice = _compactHistory(once)
    assert twice[0] == once[0]
    marks = sum(1 for m in twice
                if '[Earlier turns:' in (m.get('content') or ''))
    assert marks == 1


def test_a_summary_one_turn_folded_is_read_back_as_one(qapp):
    """The grammar of the summary is the same for one turn and many
    (``1 turn folded`` / ``2 turns folded``); the fold that adds one more
    turn on top must read the old count back as the count it was."""
    history = _history(MAX_HISTORY_TURNS + 1)
    once = _compactHistory(history)
    assert '1 turn folded' in once[0]['content']
    twice = _compactHistory(once + _turn(99))
    assert '2 turns folded' in twice[0]['content']


def test_the_final_turn_is_never_folded_away(qapp):
    """A turn too big to fit the byte budget keeps its own final turn --
    it is the one the next ask reads back."""
    big_ask = 'A' * 40 * 1024
    history = []
    for i in range(MAX_HISTORY_TURNS):
        history += _turn(i)
        history[-1]['content'] = 'B' * 20 * 1024
    history += [{'role': 'user', 'content': big_ask},
                {'role': 'assistant', 'content': 'answer'}]
    folded = _compactHistory(history)
    assert folded[0]['content'].startswith('[Earlier turns:')
    # The big final ask stands, whole.
    assert any(m.get('content') == big_ask for m in folded)
    # The budget is the cap: the kept window stays under it.
    kept_chars = sum(len(json.dumps(m)) for m in folded[1:])
    assert kept_chars <= MAX_HISTORY_CHARS


def test_the_accepted_turn_survives_compaction(qapp):
    """The whole turn is kept after an acceptance: the summary is
    bounded, the new turn is read back whole by the next ask."""
    history = _history(MAX_HISTORY_TURNS + 3)
    llm = FakeLLMClient([
        LLMResponse(content='the new answer.', finish_reason='stop',
                    usage={'prompt_tokens': 1, 'completion_tokens': 1,
                           'total_tokens': 2}),
    ])
    loop = _build(llm, history=history)
    errors = []
    loop.askFinished.connect(errors.append)
    loop.ask('the new ask', tools_mode='hide')
    assert errors == [None]
    kept = loop.history
    assert kept[0]['content'].startswith('[Earlier turns:')
    assert any(m.get('content') == 'the new ask' for m in kept)
    assert any(m.get('content') == 'the new answer.' for m in kept)
    # Bounded: one summary line + the last turns.
    assert sum(1 for m in kept if m.get('role') == 'user') \
        <= MAX_HISTORY_TURNS + 1
