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
"""The loop does not let a deflected final answer abandon the work it did.

The 2026-11-08 run shows the shape: the tools ran (``plot_one`` drew
``Plot1``, ``get_signal`` read 17344 samples of ``bpol_probe[2].field``),
and then the final answer came back "I don't have a pending task… give me
the case URI and what you'd like to see" -- the small local model lost the
original request at exactly the moment it had to report it, and on a
follow-up it even claimed it had "not yet traced" anything that was in
front of it. That is the opposite of the loop's contract: a gesture that
ran is a delivered fact, and an answer that says none of it happened and
hands the request back to the user does not stand.

This file pins the guard, the mirror image of ``test_115`` (which refuses
an *unfounded* list):

* after a tool has run, a final answer that says none of it was done and
  asks the user to restate the request is a named refusal naming the
  delivered work -- not a silent green answer;
* the loop then re-anchors on what the tools produced and gives one re-
  anchored turn, so an honest answer on the next pass stands (``a pending
  task in front of it is not abandoned``);
* an honest final answer after a tool is not second-guessed -- no refusal,
  and the LLM is not called a third time;
* two deflections in a row is still a named refusal, and it stops there:
  the loop does not re-anchor the same turn twice.
"""

import pytest

from imasviz.VizAgent.agent import AgentLoop
from imasviz.VizAgent.llm_client import LLMResponse


class FakeLLMClient:
    """A scripted LLM: the next response in its queue, in order, counting
    how often it was called -- so a test can assert the re-anchor did not
    fire, or that it fired exactly once."""
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def chat(self, messages, tools=None, **kwargs):
        if not self.responses:
            raise AssertionError('FakeLLMClient: no more scripted responses')
        self.calls += 1
        return self.responses.pop(0)


class FakeCore:
    def plot_one(self, uri, path, along_time=None, into_figure_key=None,
                 time=None, time_interp=None):
        return {'figure': 'Plot1', 'kind': 'QVizCurvePlot', 'drawing': True}

    def list_cases(self):
        return [{'uri': 'imas:hdf5?path=/fake'}]


class FakeDispatcher:
    def call(self, function, timeout=300.0):
        return function()


@pytest.fixture
def agent_kwargs(qapp):
    return {'main_window': None, 'api': None}


def _ask(agent, prompt, max_turns=12):
    lines, errors = [], []
    agent.transcriptLine.connect(lines.append)
    agent.askFinished.connect(errors.append)
    agent.ask(prompt, max_turns=max_turns)
    return ' '.join(lines), errors


def _plotTurn():
    return LLMResponse(
        content='', tool_calls=[
            {'name': 'plot_one',
             'args': {'uri': 'x',
                      'path': 'magnetics.bpol_probe[2].field.data'}}],
        finish_reason='tool_calls')


def test_a_deflected_answer_after_a_tool_is_reanchored_then_stands(qapp,
                                                                  agent_kwargs):
    """The repro: it drew, then said it had "no pending task" and asked for
    the URI. That deflection is refused by name -- naming the delivered
    work -- re-anchored on it, and the honest answer on the next pass is
    what the user finally gets. The work is not abandoned."""
    llm = FakeLLMClient([
        _plotTurn(),
        LLMResponse(
            content="I don't have a pending task to continue -- give me the "
                    "case URI and what you'd like to see.",
            tool_calls=None, finish_reason='stop'),
        LLMResponse(content='Plot1 shows the B-pol field of probe 2, '
                            '17344 samples.', tool_calls=None,
                    finish_reason='stop'),
    ])
    agent = AgentLoop(core=FakeCore(), llm=llm, dispatcher=FakeDispatcher(),
                      **agent_kwargs)
    transcript, errors = _ask(agent, 'trace le signal bpol_probe sonde 2')
    assert errors == [None], 'the honest re-anchored answer must stand'
    assert 'REFUSAL' in transcript, 'the deflection must be named in the log'
    assert 'plot_one' in transcript, 'the delivered work is named in it'
    assert 'probe 2' in transcript.lower(), 'the standing answer is the honest one'
    assert llm.calls == 3, 'one re-anchored turn, then the answer stands'


def test_a_honest_answer_after_a_tool_stands_without_a_reanchor(qapp,
                                                                agent_kwargs):
    """A final answer that reports the work (not one that loses it) is
    accepted on the spot: no refusal in the log, and the LLM is not called
    a third time -- the re-anchor must not fire on a good answer."""
    llm = FakeLLMClient([
        _plotTurn(),
        LLMResponse(content='Plot1 shows the field of the probe over time.',
                    tool_calls=None, finish_reason='stop'),
    ])
    agent = AgentLoop(core=FakeCore(), llm=llm, dispatcher=FakeDispatcher(),
                      **agent_kwargs)
    transcript, errors = _ask(agent, 'trace le signal bpol_probe sonde 2')
    assert errors == [None]
    assert 'REFUSAL' not in transcript, 'a good answer is not second-guessed'
    assert llm.calls == 2, 'no re-anchor for a good final answer'


def test_two_deflections_is_a_named_refusal_and_stops(qapp, agent_kwargs):
    """If the re-anchor does not cure it either, the loop still refuses by
    name -- naming the delivered work -- and stops there, instead of
    re-anchoring the same turn for ever."""
    llm = FakeLLMClient([
        _plotTurn(),
        LLMResponse(content='I have no pending task; give me the case URI.',
                    tool_calls=None, finish_reason='stop'),
        LLMResponse(content='There is no question attached; what would you '
                            'like to do?', tool_calls=None,
                    finish_reason='stop'),
    ])
    agent = AgentLoop(core=FakeCore(), llm=llm, dispatcher=FakeDispatcher(),
                      **agent_kwargs)
    transcript, errors = _ask(agent, 'trace le signal bpol_probe sonde 2')
    assert errors and errors[0] is not None, 'two deflections must be refused'
    assert 'plot_one' in errors[0], 'the refusal still names the work that ran'
    assert llm.calls == 3, 'it re-anchored once and then stopped, never twice'


def test_a_french_deflection_is_caught_the_same_way(qapp, agent_kwargs):
    """The model answers in French as in the user's session; "je n'ai encore
    rien tracé" is the same deflection as the English one and is refused by
    name against the tool that already traced it."""
    llm = FakeLLMClient([
        _plotTurn(),
        LLMResponse(content="je n'ai encore rien tracé pour l'instant ; "
                            'quelle uri de cas ?',
                    tool_calls=None, finish_reason='stop'),
        LLMResponse(content='Plot1 montre le champ B, 17344 échantillons.',
                    tool_calls=None, finish_reason='stop'),
    ])
    agent = AgentLoop(core=FakeCore(), llm=llm, dispatcher=FakeDispatcher(),
                      **agent_kwargs)
    transcript, errors = _ask(agent, 'trace le champ bpol_probe')
    assert errors == [None]
    assert 'REFUSAL' in transcript, 'the French deflection is named too'
    assert 'plot_one' in transcript
