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
"""The dispatch refuses a parameter the tool does not take, by name.

The model invented ``time_index`` on the drawing call in the 2026-11-07
viz_cli run: the schema says ``additionalProperties: false`` and the
call takes ``uri, path, along_time, into_figure_key``. Python's
``TypeError`` (``unexpected keyword argument``) was the refusal that
survived, and it names the wrong thing -- it says the argument is not
expected, not which ones are. The loop's own style, which the rest of
this test file's neighbours use, is a refusal that names the parameter
that is not there and the ones that are, so the model can answer with
the right call instead of re-guessing.

The call is spelled as it is offered: the five drawings answer one name
and a ``mode``, and a parameter is checked against the row of the mode
that was asked, so the stray is refused against ``plot(mode="single")``
-- the spelling the model can type back.
"""

import pytest

from imasviz.VizAgent.agent import AgentLoop
from imasviz.VizAgent.llm_client import LLMResponse


class FakeLLMClient:
    def __init__(self, responses):
        self.responses = list(responses)

    def chat(self, messages, tools=None, **kwargs):
        assert self.responses, 'no more scripted responses'
        return self.responses.pop(0)


class RecordingCore:
    """Answers plot_one by recording the call, and refuses nothing."""
    def __init__(self):
        self.calls = []

    def plot_one(self, uri, path, along_time=None, into_figure_key=None):
        self.calls.append({'uri': uri, 'path': path,
                           'along_time': along_time,
                           'into_figure_key': into_figure_key})
        return {'figure': 'Plot1', 'drawing': True}

    def list_cases(self):
        return [{'uri': 'imas:hdf5?path=/fake'}]


class FakeDispatcher:
    def call(self, function, timeout=300.0):
        return function()


@pytest.fixture
def agent_kwargs(qapp):
    return {'main_window': None, 'api': None}


def _ask(agent, core, prompt):
    lines, errors = [], []
    agent.transcriptLine.connect(lines.append)
    agent.askFinished.connect(errors.append)
    agent.ask(prompt)
    return ' '.join(lines), errors


def test_an_unknown_parameter_is_refused_naming_the_valid_ones(
        qapp, agent_kwargs):
    """``plot(mode="single", time_index=7)`` is refused before Python's
    TypeError: the refusal names the parameter that is not a parameter of
    that mode, and lists the ones that are. The core is never called.
    """
    core = RecordingCore()
    llm = FakeLLMClient([
        LLMResponse(content='', tool_calls=[
            {'name': 'plot',
             'args': {'mode': 'single', 'uri': 'x',
                      'path': 'equilibrium.f', 'time_index': 3}}],
            finish_reason='tool_calls'),
        LLMResponse(content='refused.', tool_calls=None,
                    finish_reason='stop'),
    ])
    agent = AgentLoop(core=core, llm=llm, dispatcher=FakeDispatcher(),
                      **agent_kwargs)
    transcript, errors = _ask(agent, core, 'plot it at t=3')
    assert 'REFUSAL' in transcript
    refusal_line = [ln for ln in transcript.splitlines()
                    if 'REFUSAL' in ln and 'plot:' in ln][0]
    assert 'time_index' in refusal_line, \
        'the refusal must name the parameter that is not there'
    assert 'along_time' in refusal_line, \
        'the refusal must name the parameters that are, so the model can ' \
        'answer with the right call'
    assert core.calls == [], \
        'an unknown parameter must not reach the core'
    assert errors == [None], \
        'the loop continues after a refused parameter: the refusal is a ' \
        'tool result the model corrects against, so the ask ends answered'


def test_a_known_parameter_is_not_refused(qapp, agent_kwargs):
    """The refusal is for parameters the mode does not take, and nothing
    else: a single drawing with its real arguments reaches the core and
    answers a figure, with no REFUSAL line in the transcript."""
    core = RecordingCore()
    llm = FakeLLMClient([
        LLMResponse(content='', tool_calls=[
            {'name': 'plot',
             'args': {'mode': 'single', 'uri': 'x',
                      'path': 'equilibrium.f', 'along_time': 1}}],
            finish_reason='tool_calls'),
        LLMResponse(content='plotted.', tool_calls=None,
                    finish_reason='stop'),
    ])
    agent = AgentLoop(core=core, llm=llm, dispatcher=FakeDispatcher(),
                      **agent_kwargs)
    # This test reads the `←` line back -- the figure the core named -- which
    # the default `hide` mode (tools run, the traffic cut) does not put in the
    # transcript. Pin `verbose`, the shape that shows the traffic, so the
    # assertion is about a figure reaching the transcript, not about the mode.
    agent.tools_mode = 'verbose'
    transcript, errors = _ask(agent, core, 'plot it along time')
    assert core.calls == [{'uri': 'x', 'path': 'equilibrium.f',
                           'along_time': 1, 'into_figure_key': None}], \
        'the core must receive the call with its arguments'
    assert 'REFUSAL' not in transcript
    assert 'Plot1' in transcript, \
        'the figure the core named must reach the transcript'
    assert errors == [None]
