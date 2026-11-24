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
"""The loop's history carries the tool traffic of the turn it served.

The amnesia the follow-up confabulation stood on: the loop appended only
the user's ask and its final answer to ``agent.history``, so on the next
``ask`` the model read back its last words with no record that it had
tools and used them -- it answered on that momentum, with no grounding
left to stand on. A refusal it had given, or a figure it had drawn, was
not in what it read either.

What this file pins, scripted, off the case:

* an accepted turn with a tool call leaves the WHOLE turn in
  ``agent.history`` -- the user's ask, the assistant message with its
  ``tool_calls``, the ``role: 'tool'`` result, the final answer -- and
  the next ``ask`` reads it back: the first ``chat`` of that next ask
  receives the calls the previous turn made;
* the re-anchor the loop throws in between a refused and an accepted
  answer is loop-internal: it is what it tells the model in the moment,
  and it is not in the history the next ask reads.
"""

from imasviz.VizAgent.agent import AgentLoop
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
    """The one gesture this file drives: it answers, so a tool call of
    the turn is a success the loop can ground on."""
    def list_cases(self):
        return [{'uri': 'imas:hdf5?path=/fake', 'dd_version': '3.35.0'}]


class FakeDispatcher:
    """A synchronous dispatcher: it runs the function on the calling thread."""
    def call(self, function, timeout=300.0):
        return function()


def _build(llm):
    return AgentLoop(core=FakeCore(), llm=llm, dispatcher=FakeDispatcher(),
                     main_window=None, api=None)


def test_an_accepted_turn_leaves_its_tool_traffic_in_the_history(qapp):
    """The ask, the assistant's call, the tool result and the final answer
    all stand in ``agent.history`` after the turn -- not just the ask and
    the last line."""
    llm = FakeLLMClient([
        LLMResponse(content='',
                    tool_calls=[{'name': 'list_cases', 'args': {}}],
                    finish_reason='tool_calls'),
        LLMResponse(content='Here are the cases you asked for.',
                    tool_calls=None, finish_reason='stop'),
    ])
    agent = _build(llm)
    errors = []
    agent.askFinished.connect(errors.append)
    agent.ask('list the cases', tools_mode='hide')
    assert errors == [None]

    history = agent.history
    assert any(m.get('role') == 'user' and m.get('content') == 'list the cases'
               for m in history), \
        'the user ask is gone from the history the next ask reads'
    assistant = next((m for m in history
                      if m.get('role') == 'assistant' and m.get('tool_calls')),
                     None)
    assert assistant is not None, \
        'the assistant message with its tool_calls is the amnesia: ' \
        'the next ask cannot see the call the turn made'
    assert assistant['tool_calls'][0]['function']['name'] == 'list_cases'
    tool = next((m for m in history if m.get('role') == 'tool'), None)
    assert tool is not None, \
        'the tool result is gone from the history: the answer stands on ' \
        'a call the next ask cannot see'
    assert tool['name'] == 'list_cases'
    assert history[-1] == {'role': 'assistant',
                           'content': 'Here are the cases you asked for.'}


def test_the_next_ask_reads_the_previous_turns_calls(qapp):
    """The first ``chat`` of the second ask receives the calls of the
    first -- the grounding a follow-up can stand on, which the amnesia
    had cut away."""
    llm = FakeLLMClient([
        LLMResponse(content='',
                    tool_calls=[{'name': 'list_cases', 'args': {}}],
                    finish_reason='tool_calls'),
        LLMResponse(content='Here are the cases you asked for.',
                    tool_calls=None, finish_reason='stop'),
        LLMResponse(content='And that is all the session holds.',
                    tool_calls=None, finish_reason='stop'),
    ])
    agent = _build(llm)
    agent.ask('list the cases', tools_mode='hide')
    agent.ask('and what else does the session hold?', tools_mode='hide')

    second = llm.calls[2]['messages']
    assert any(m.get('role') == 'tool' and m.get('name') == 'list_cases'
               for m in second), \
        'the second ask does not receive the first turn tool result: ' \
        'the follow-up stands on the amnesia'
    assert any(m.get('role') == 'assistant' and m.get('tool_calls')
               for m in second), \
        'the second ask does not receive the first turn tool call: ' \
        'the model reads its last words with no record that it had ' \
        'tools and used them'


def test_the_reanchor_is_not_in_the_history(qapp):
    """The deflected answer after a successful tool is re-anchored once;
    the anchor is what the loop says to the model in the moment, and it
    is not a line of the conversation -- the history the next ask reads
    must not carry it."""
    llm = FakeLLMClient([
        LLMResponse(content='',
                    tool_calls=[{'name': 'list_cases', 'args': {}}],
                    finish_reason='tool_calls'),
        # The deflection: the work is done, and the answer gives it back.
        LLMResponse(content='No pending task here; give me the case URI '
                            'and I will tell you what to do.',
                    tool_calls=None, finish_reason='stop'),
        LLMResponse(content='The case is open and listed above.',
                    tool_calls=None, finish_reason='stop'),
    ])
    agent = _build(llm)
    errors = []
    agent.askFinished.connect(errors.append)
    agent.ask('list the cases and tell me what they hold',
              tools_mode='hide')
    assert errors == [None], \
        'the honest re-anchored answer must stand'
    assert len(llm.calls) == 3, 'one re-anchored turn, then the answer'
    user_lines = [m.get('content') or '' for m in agent.history
                  if m.get('role') == 'user']
    assert not any(line.startswith('[SYSTEM FEEDBACK]') for line in user_lines), \
        'the re-anchor is loop-internal: it is not a line of the ' \
        'conversation the next ask reads'
