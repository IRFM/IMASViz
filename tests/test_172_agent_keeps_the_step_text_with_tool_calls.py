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
"""The assistant message that carries tool calls keeps the step text.

Many models (the reasoning ones in particular, and the OpenAI / vLLM /
llama.cpp servers this loop is pointed at) write the step they are about
to take in the SAME response as the call -- "Je vais d'abord vérifier
les IDS disponibles" beside the ``tool_calls``. The loop used to force
``content: None`` on that message, which cut the thread of the exchange
between the call and the result the model is about to read, and dropped
the half of the turn the model had actually said.

What this file pins, scripted, off the case: the assistant message that
carries the tool calls keeps the step text it was written with -- in the
messages the second call receives, and in the history the next ask
reads -- and stays ``None`` when the model said nothing beside the
call.
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
    """The one gesture this file drives: it answers, so the call the
    turn makes is a success the loop can ground on."""
    def list_cases(self):
        return [{'uri': 'imas:hdf5?path=/fake', 'dd_version': '3.35.0'}]


class FakeDispatcher:
    """A synchronous dispatcher: it runs the function on the calling thread."""
    def call(self, function, timeout=300.0):
        return function()


def _build(llm):
    return AgentLoop(core=FakeCore(), llm=llm, dispatcher=FakeDispatcher(),
                     main_window=None, api=None)


def test_the_step_text_stands_beside_the_tool_call(qapp):
    """The text the model wrote beside its call is what the exchange
    carries: the second call receives it on the assistant message, and
    the history the next ask reads keeps it."""
    step = "Je vais d'abord lister les cas de la session."
    llm = FakeLLMClient([
        LLMResponse(content=step,
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

    second = llm.calls[1]['messages']
    msg = next((m for m in second
                if m.get('role') == 'assistant' and m.get('tool_calls')),
               None)
    assert msg is not None
    assert msg['content'] == step, \
        'the step text the model wrote beside its call is cut from the ' \
        'exchange: the thread between the call and the result is lost'

    hist = next((m for m in agent.history
                 if m.get('role') == 'assistant' and m.get('tool_calls')),
                None)
    assert hist is not None
    assert hist['content'] == step, \
        'the history the next ask reads lost the step text of the call'


def test_the_content_stays_none_when_the_model_said_nothing(qapp):
    """A call with no text beside it keeps ``content: None`` -- the
    shape the providers expect, and the one that keeps an empty string
    out of the record."""
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

    second = llm.calls[1]['messages']
    msg = next((m for m in second
                if m.get('role') == 'assistant' and m.get('tool_calls')),
               None)
    assert msg is not None
    assert msg['content'] is None, \
        'an empty step text must stay None, not become an empty string ' \
        'in the record the providers read'
