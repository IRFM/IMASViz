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
"""The max_turns refusal names the last action -- and the default budget.

In the 2026-11-07 run the loop hit its limit with everything delivered:
the report had been written (``plot_report: saved_to=...`` in the
transcript), yet the turn ended "Stopped: max_turns reached (8)" and the
client saw a refusal with no name for what had just succeeded. Three
parts pin what that stop must say, and the budget it is allowed to need:

* a stop that has a last tool to name says so -- the tool and the
  summary of its answer -- so the artifact a delivered call left behind
  is not lost in the "refusal";
* a stop whose last action was itself a refusal still names the limit and
  the tool that was refused;
* the default budget the loop, the session and the command line are each
  built with answers 12, not 8: 8 is exactly the size of the failed run
  (search, two refused calls, plot, describe, read, report) plus nothing
  for the final answer.
"""

import inspect

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
    def plot_one(self, uri, path, along_time=None, into_figure_key=None):
        return {'figure': 'Plot3', 'drawing': True}

    def plot_report(self, figure_key='Plot3', name=None):
        return {'saved_to': '/tmp/te_profile.html', 'traces': 1,
                'window': figure_key}

    def list_cases(self):
        return [{'uri': 'imas:hdf5?path=/fake'}]


class RefusingCore:
    """Refuses everything it is asked: the last action is then itself a
    refusal, and the stop must still name it as such."""
    def plot_one(self, uri, path, along_time=None, into_figure_key=None):
        raise ValueError('Nothing to plot: the selection is empty.')

    def list_cases(self):
        return [{'uri': 'imas:hdf5?path=/fake'}]


class FakeDispatcher:
    def call(self, function, timeout=300.0):
        return function()


@pytest.fixture
def agent_kwargs(qapp):
    return {'main_window': None, 'api': None}


def _ask(agent, prompt, max_turns=2):
    lines, errors = [], []
    agent.transcriptLine.connect(lines.append)
    agent.askFinished.connect(errors.append)
    agent.ask(prompt, max_turns=max_turns)
    return ' '.join(lines), errors


def test_a_stop_names_the_last_action_and_its_artifact(qapp, agent_kwargs):
    """Two tool calls, no final answer left the budget: the stop is still
    a refusal naming the limit, but it also names the last action -- its
    tool and the summary of its answer -- so the artifact that call wrote
    (the saved report) is not lost in the "max_turns reached"."""
    core = RecordingCore()
    llm = FakeLLMClient([
        LLMResponse(content='', tool_calls=[
            {'name': 'plot_one', 'args': {'uri': 'x', 'path': 'equilibrium.f'}}],
            finish_reason='tool_calls'),
        LLMResponse(content='', tool_calls=[
            {'name': 'plot_report', 'args': {'figure_key': 'Plot3',
                                             'name': 'te_profile'}}],
            finish_reason='tool_calls'),
    ])
    agent = AgentLoop(core=core, llm=llm, dispatcher=FakeDispatcher(),
                      **agent_kwargs)
    transcript, errors = _ask(agent, 'plot and report', max_turns=2)
    assert errors and 'max_turns' in errors[0].lower(), \
        'the stop must still be a refusal naming the limit'
    assert 'plot_report' in errors[0], \
        'the stop must name the last action, so the artifact it left ' \
        'behind is not lost in the "refusal"'
    assert 'saved_to' in errors[0], \
        'the stop must answer what the last action answered'
    assert 'plot_report' in transcript
    assert 'max_turns' in transcript


def test_a_stop_after_a_refused_action_names_it_as_refused(qapp, agent_kwargs):
    """When the last action was itself a refusal, the stop says so: the
    limit, the tool, the refusal -- not just the limit."""
    core = RefusingCore()
    llm = FakeLLMClient([
        LLMResponse(content='', tool_calls=[
            {'name': 'plot_one', 'args': {'uri': 'x', 'path': 'equilibrium.f'}}],
            finish_reason='tool_calls'),
        LLMResponse(content='', tool_calls=[
            {'name': 'plot_one', 'args': {'uri': 'x', 'path': 'equilibrium.f'}}],
            finish_reason='tool_calls'),
    ])
    agent = AgentLoop(core=core, llm=llm, dispatcher=FakeDispatcher(),
                      **agent_kwargs)
    transcript, errors = _ask(agent, 'plot it', max_turns=2)
    assert 'max_turns' in errors[0]
    assert 'plot_one' in errors[0], 'the refused tool must be named'
    assert 'REFUSAL' in errors[0].upper(), \
        'a refused last action must still be a refusal in the stop'
    assert 'selection is empty' in errors[0] or 'REFUSAL' in transcript


def test_the_default_budget_answers_12_in_all_three_places(qapp):
    """The loop, the session and the command line: the same default, 12.
    Eight was exactly the size of the failed 2026-11-07 run, so it left
    no room for the final answer a delivered sequence needs."""
    from viz_cli.session import CliSession
    from viz_cli.run import parseArguments

    assert (inspect.signature(AgentLoop.ask)
            .parameters['max_turns'].default == 12)
    assert (inspect.signature(CliSession.__init__)
            .parameters['max_turns'].default == 12)
    assert parseArguments([]).max_turns == 12
