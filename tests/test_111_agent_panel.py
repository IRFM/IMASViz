# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The agent panel: a window the user talks to, in the *Windows* menu.

What it pins, on a scripted agent (no real LLM):

* the panel is registered in ``figureframes`` under ``Agent:1``;
* typing a prompt and clicking "Tourner" produces transcript lines
  that include the scripted LLM answer;
* a refusal from the scripted agent is visible in the transcript with
  its ``REFUSAL`` prefix;
* the *Windows* menu can reach the panel (it is in the session's
  ``figureframes``).
"""

import pytest

from imasviz.Viz_API import Viz_API
from imasviz.VizAgent.agent import AgentLoop
from imasviz.VizAgent.llm_client import LLMResponse
from imasviz.VizUtils import FigureTypes, QVizGlobalValues


class FakeLLMClient:
    """A scripted LLM: returns the next response in its queue."""
    def __init__(self, responses):
        self.responses = list(responses)

    def chat(self, messages, tools=None, **kwargs):
        if not self.responses:
            raise AssertionError('FakeLLMClient: no more scripted responses')
        return self.responses.pop(0)


class FakeCore:
    """A stand-in for McpGuiCore."""
    def list_cases(self):
        return [{'uri': 'fake', 'dd_version': '3.35.0'}]


class FakeDispatcher:
    """A synchronous dispatcher."""
    def call(self, function, timeout=300.0):
        return function()


def make_api(qapp):
    """A bare Viz_API for the test, no case open."""
    return Viz_API(None)


def test_panel_registered_in_figureframes(qapp):
    """The panel is in the session's figureframes under Agent:1."""
    from imasviz.VizAgent.panel import QVizAgentPanel
    from imasviz.VizAgent.llm_client import LLMResponse

    llm = FakeLLMClient([
        LLMResponse(content='Hello.', tool_calls=None, finish_reason='stop')
    ])
    agent = AgentLoop(
        core=FakeCore(), llm=llm, dispatcher=FakeDispatcher())
    api = make_api(qapp)
    panel = QVizAgentPanel(main_window=None, api=api, agent=agent)
    try:
        # The panel is registered in figureframes under its key.
        key = panel.figureKey
        assert key.startswith('Agent:')
        assert key in api.figureframes
    finally:
        if key in api.figureframes:
            del api.figureframes[key]


def test_panel_transcript_shows_final_answer(qapp):
    """Typing a prompt and running the agent shows the LLM answer."""
    from imasviz.VizAgent.panel import QVizAgentPanel

    llm = FakeLLMClient([
        LLMResponse(content='The case is open with 71 IDSs.',
                    tool_calls=None, finish_reason='stop')
    ])
    agent = AgentLoop(
        core=FakeCore(), llm=llm, dispatcher=FakeDispatcher())
    api = make_api(qapp)
    panel = QVizAgentPanel(main_window=None, api=api, agent=agent)
    try:
        panel.setPrompt('open the case')
        panel.runAgent()  # Synchronous: blocks until the loop is done.
        text = panel.transcriptText()
        assert 'The case is open with 71 IDSs.' in text
        assert 'REFUSAL' not in text
    finally:
        key = panel.figureKey
        if key in api.figureframes:
            del api.figureframes[key]


def test_panel_transcript_shows_refusal(qapp):
    """A refusal from the agent is visible in the transcript."""
    from imasviz.VizAgent.panel import QVizAgentPanel

    # The LLM asks for a tool that will refuse.
    llm = FakeLLMClient([
        LLMResponse(content='',
                    tool_calls=[{'name': 'nonexistent_tool', 'args': {}}],
                    finish_reason='tool_calls'),
        LLMResponse(content='That was refused.',
                    tool_calls=None, finish_reason='stop'),
    ])
    core = FakeCore()
    # FakeCore has no 'nonexistent_tool' method → AgentLoop._dispatch
    # raises a ValueError → the refusal is named.
    agent = AgentLoop(
        core=core, llm=llm, dispatcher=FakeDispatcher())
    api = make_api(qapp)
    panel = QVizAgentPanel(main_window=None, api=api, agent=agent)
    try:
        panel.setPrompt('do a nonexistent thing')
        panel.runAgent()
        text = panel.transcriptText()
        assert 'REFUSAL' in text
        assert 'nonexistent_tool' in text
    finally:
        key = panel.figureKey
        if key in api.figureframes:
            del api.figureframes[key]


def test_panel_figureKey_is_agenttype(qapp):
    """The panel's key starts with the AGENTTYPE prefix."""
    from imasviz.VizAgent.panel import QVizAgentPanel

    llm = FakeLLMClient([
        LLMResponse(content='ok', tool_calls=None, finish_reason='stop')
    ])
    agent = AgentLoop(
        core=FakeCore(), llm=llm, dispatcher=FakeDispatcher())
    api = make_api(qapp)
    panel = QVizAgentPanel(main_window=None, api=api, agent=agent)
    try:
        assert panel.figureKey.startswith(FigureTypes.AGENTTYPE)
    finally:
        key = panel.figureKey
        if key in api.figureframes:
            del api.figureframes[key]
