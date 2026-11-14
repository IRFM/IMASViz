# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The agent loop: LLM → tool → LLM, on a scripted LLM, no network.

What it pins, in the refusal order the loop must answer them:

* a final answer (no tool_calls, non-empty content): the loop stops,
  the answer is in the transcript, `askFinished` is None;
* `finish_reason == 'length'`: the loop stops, the refusal names the
  truncation;
* a tool call that raises a `ValueError`: the refusal is in the
  transcript with the reason, the loop continues to the next turn;
* an empty answer (no tool_calls, empty content): the refusal is named;
* `max_turns` reached: the loop stops, the refusal names the limit.
"""

import pytest

from imasviz.VizAgent.agent import AgentLoop
from imasviz.VizAgent.llm_client import LLMResponse


class FakeLLMClient:
    """A scripted LLM: it returns the next response in its queue, in order.

    `calls` is the record of what was asked, for the assertions that
    check the loop passed the right messages.
    """
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, messages, tools=None, **kwargs):
        self.calls.append({'messages': list(messages), 'tools': tools})
        if not self.responses:
            raise AssertionError('FakeLLMClient: no more scripted responses')
        return self.responses.pop(0)


class FakeCore:
    """A stand-in for McpGuiCore that answers a fixed value for every method."""
    def list_cases(self):
        return [{'uri': 'imas:hdf5?path=/fake', 'dd_version': '3.35.0'}]
    def open_case(self, uri, dd_version=None):
        raise ValueError('no case at %s' % uri)


class RefusingCore(FakeCore):
    """Answers a named ValueError for a specific tool name."""
    def bad_tool(self, **kwargs):
        raise ValueError('the tool "bad_tool" does not exist in the session')


class FakeDispatcher:
    """A synchronous dispatcher: it runs the function on the calling thread."""
    def call(self, function, timeout=300.0):
        return function()


def _transcript(agent):
    """The transcript lines the agent emitted, as a list."""
    lines = []
    return lines


@pytest.fixture
def agent_kwargs(qapp):
    """The common kwargs for building an AgentLoop in a test."""
    return {'main_window': None, 'api': None}


def test_final_answer(qapp, agent_kwargs):
    """LLM answers text without tool_calls: the loop stops cleanly."""
    response = LLMResponse(
        content='Ok, the case is open.',
        tool_calls=None,
        finish_reason='stop',
    )
    llm = FakeLLMClient([response])
    agent = AgentLoop(
        core=FakeCore(), llm=llm,
        dispatcher=FakeDispatcher(),
        **agent_kwargs,
    )
    lines = []
    agent.transcriptLine.connect(lines.append)
    error = []
    agent.askFinished.connect(error.append)
    agent.ask('open a case')
    # Synchronous path: ask() blocks until the loop is done.
    assert error == [None]
    joined = ' '.join(lines)
    assert 'Ok, the case is open.' in joined
    assert 'REFUSAL' not in joined


def test_truncated_response(qapp, agent_kwargs):
    """finish_reason == 'length': the loop stops and names the truncation."""
    response = LLMResponse(
        content='partial answer...',
        tool_calls=None,
        finish_reason='length',
    )
    agent = AgentLoop(
        core=FakeCore(), llm=FakeLLMClient([response]),
        dispatcher=FakeDispatcher(),
        **agent_kwargs,
    )
    lines = []
    agent.transcriptLine.connect(lines.append)
    error = []
    agent.askFinished.connect(error.append)
    agent.ask('do something long')
    assert error[0] is not None
    assert 'truncated' in error[0].lower() or 'length' in error[0].lower()
    joined = ' '.join(lines)
    assert 'REFUSAL' in joined


def test_tool_call_then_final(qapp, agent_kwargs):
    """LLM asks for a tool, the tool runs, the LLM gives the final answer.

    Pinned on `verbose`, whose transcript carries the tool traffic: the
    default `hide` shape cuts those lines by design (pinned in
    `tests/test_117_agent_tools_mode.py`), so this test names the shape it
    asserts on rather than reading the loop's default.
    """
    call = LLMResponse(
        content='',
        tool_calls=[{'name': 'list_cases', 'args': {}}],
        finish_reason='tool_calls',
    )
    final = LLMResponse(
        content='Here are the cases you asked for.',
        tool_calls=None,
        finish_reason='stop',
    )
    agent = AgentLoop(
        core=FakeCore(), llm=FakeLLMClient([call, final]),
        dispatcher=FakeDispatcher(),
        **agent_kwargs,
    )
    agent.tools_mode = 'verbose'
    lines = []
    agent.transcriptLine.connect(lines.append)
    error = []
    agent.askFinished.connect(error.append)
    agent.ask('list the cases')
    assert error == [None]
    joined = ' '.join(lines)
    assert 'list_cases' in joined
    assert 'Here are the cases you asked for.' in joined


def test_tool_refusal_named(qapp, agent_kwargs):
    """A ValueError from a tool is named in the transcript, the loop continues."""
    call = LLMResponse(
        content='',
        tool_calls=[{'name': 'bad_tool', 'args': {}}],
        finish_reason='tool_calls',
    )
    final = LLMResponse(
        content='The tool was refused; here is why.',
        tool_calls=None,
        finish_reason='stop',
    )
    agent = AgentLoop(
        core=RefusingCore(), llm=FakeLLMClient([call, final]),
        dispatcher=FakeDispatcher(),
        **agent_kwargs,
    )
    lines = []
    agent.transcriptLine.connect(lines.append)
    error = []
    agent.askFinished.connect(error.append)
    agent.ask('do the bad thing')
    assert error == [None]
    joined = ' '.join(lines)
    assert 'REFUSAL' in joined
    assert 'bad_tool' in joined
    assert 'does not exist' in joined


def test_max_turns(qapp, agent_kwargs):
    """The loop stops after max_turns; the refusal names the limit."""
    calls = [
        LLMResponse(
            content='',
            tool_calls=[{'name': 'list_cases', 'args': {}}],
            finish_reason='tool_calls',
        )
        for _ in range(10)
    ]
    llm = FakeLLMClient(calls)
    agent = AgentLoop(
        core=FakeCore(), llm=llm,
        dispatcher=FakeDispatcher(),
        **agent_kwargs,
    )
    lines = []
    agent.transcriptLine.connect(lines.append)
    error = []
    agent.askFinished.connect(error.append)
    agent.ask('loop forever', max_turns=3)
    assert error[0] is not None
    assert 'max_turns' in error[0].lower() or 'max' in error[0].lower()
    # Only 3 turns were run, not 10: the queue in the client has 7 left.
    assert len(llm.responses) == 10 - 3


def test_empty_content_no_tools(qapp, agent_kwargs):
    """LLM returns empty content and no tool_calls: the refusal is named."""
    response = LLMResponse(
        content='',
        tool_calls=None,
        finish_reason='stop',
    )
    agent = AgentLoop(
        core=FakeCore(), llm=FakeLLMClient([response]),
        dispatcher=FakeDispatcher(),
        **agent_kwargs,
    )
    lines = []
    agent.transcriptLine.connect(lines.append)
    error = []
    agent.askFinished.connect(error.append)
    agent.ask('do something')
    assert error[0] is not None
    assert 'empty' in error[0].lower()
    joined = ' '.join(lines)
    assert 'REFUSAL' in joined
