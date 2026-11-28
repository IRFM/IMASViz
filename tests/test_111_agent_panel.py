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
* typing a prompt and clicking "Run" produces transcript lines
  that include the scripted LLM answer;
* the input box sits below the transcript, so a scrolling answer stays
  readable;
* the window is capped at ``MAX_WIDTH``: a long NoWrap line of the
  transcript scrolls in place instead of stretching the window past
  the reading width it opened at;
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
    """A stand-in for McpGuiCore.

    It carries ``list_prompts`` because the panel asks the catalogue while
    it is being built: the prompt box is filled from that answer, so a
    core that cannot answer it is a panel that cannot be built. What the
    core itself answers is pinned by ``test_167``; here the shelf is empty.
    """
    def list_cases(self):
        return [{'uri': 'fake', 'dd_version': '3.35.0'}]

    def list_prompts(self, scope=None, category=None, query=None,
                     limit=None):
        return {'prompts': [], 'total': 0, 'categories': {},
                'context': {'note': 'no case is open'}}


class FakeDispatcher:
    """A synchronous dispatcher."""
    def call(self, function, timeout=300.0):
        return function()


def make_api(qapp):
    """A bare Viz_API for the test, no case open."""
    return Viz_API(None)


@pytest.fixture(autouse=True)
def _agent_home(tmp_path, monkeypatch):
    """The panel reads the prompt history from ``$HOME/.imasviz`` when it
    is built and when a run records into it, so a test that constructs
    the panel points ``HOME`` at its own folder rather than the user's
    real one -- the pattern ``tests/test_39*`` keeps for a configuration
    the application writes. The loop the panel drives does not touch the
    file, so isolating ``HOME`` here is what keeps a test from reading the
    user's own prompt history, not the loop.
    """
    monkeypatch.setenv('HOME', str(tmp_path))


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


def test_panel_input_sits_below_the_transcript(qapp):
    """The transcript is on top and the input box sits below it, so the
    answer scrolls into sight while the prompt stays at the bottom of the
    window -- the button row follows the input. Pinning the order is the
    guard: an input above a scrolling transcript is exactly what the user
    could not read past, and nothing else in this file checks geometry."""
    from imasviz.VizAgent.panel import QVizAgentPanel

    llm = FakeLLMClient([
        LLMResponse(content='ok', tool_calls=None, finish_reason='stop')
    ])
    agent = AgentLoop(
        core=FakeCore(), llm=llm, dispatcher=FakeDispatcher())
    api = make_api(qapp)
    panel = QVizAgentPanel(main_window=None, api=api, agent=agent)
    try:
        layout = panel.layout()

        # ``layout.itemAt(i)`` answers a QLayoutItem, which is never
        # ``is`` of the widget or sublayout it carries: the item is asked
        # for ``.widget()`` and ``.layout()`` and the identity is checked
        # there (``QLayout.indexOfLayout`` is not exposed on PySide6 6.6,
        # and the button row is named on the panel as ``panel.buttonRow``).
        def indexOf(item):
            for i in range(layout.count()):
                it = layout.itemAt(i)
                if it is not None and (it.widget() is item or it.layout() is item):
                    return i
            raise AssertionError('not in the panel layout: %r' % item)

        assert indexOf(panel.transcript) < indexOf(panel.promptEdit)
        assert indexOf(panel.promptEdit) < indexOf(panel.buttonRow)
    finally:
        key = panel.figureKey
        if key in api.figureframes:
            del api.figureframes[key]


def test_panel_width_is_capped(qapp):
    """The panel's window is capped at ``MAX_WIDTH``.

    The transcript is ``NoWrap``: a long single line -- a REFUSAL
    sentence, a ``verbose`` tool line, an answer that arrives without
    newlines -- is the line the window is reported to have widened to
    in the field. The cap is that line's ceiling; a line past it
    scrolls in place and the window keeps the width it opened at
    (640). Offscreen cannot show the widening itself -- the platform
    does not propagate size hints -- so what is pinned is the cap and
    that a line past it still lands in the transcript and leaves the
    width within it.
    """
    from imasviz.VizAgent.panel import QVizAgentPanel, MAX_WIDTH

    llm = FakeLLMClient([
        LLMResponse(content='ok', tool_calls=None, finish_reason='stop')
    ])
    agent = AgentLoop(
        core=FakeCore(), llm=llm, dispatcher=FakeDispatcher())
    api = make_api(qapp)
    panel = QVizAgentPanel(main_window=None, api=api, agent=agent)
    try:
        # The cap is set on the panel itself, whatever the display.
        assert MAX_WIDTH >= 640
        assert panel.maximumWidth() == MAX_WIDTH
        assert panel.width() <= MAX_WIDTH
        # The line that reported it: wider than the cap, in the
        # transcript, and the width kept within the ceiling.
        line = 'REFUSAL — ' + ('un mot ' * 800).strip()
        panel._appendTranscript(line)
        assert line in panel.transcriptText()
        assert panel.maximumWidth() == MAX_WIDTH
        assert panel.width() <= MAX_WIDTH
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


def test_panel_transcript_is_capped_to_the_last_lines(qapp, monkeypatch):
    """Appending beyond the cap drops the oldest lines, keeping the newest.

    The transcript keeps its last ``TRANSCRIPT_MAX_LINES`` visible lines:
    a long session is a page the reader scrolls, not a window that grows
    for ever. What is pinned is the boundary, not the number -- the cap
    is patched to a small one -- so the test runs in any order and does
    not care what the window would hold.
    """
    import imasviz.VizAgent.panel as panel_module
    from imasviz.VizAgent.panel import QVizAgentPanel

    monkeypatch.setattr(panel_module, 'TRANSCRIPT_MAX_LINES', 3)
    llm = FakeLLMClient([
        LLMResponse(content='ok', tool_calls=None, finish_reason='stop')
    ])
    agent = AgentLoop(
        core=FakeCore(), llm=llm, dispatcher=FakeDispatcher())
    api = make_api(qapp)
    panel = QVizAgentPanel(main_window=None, api=api, agent=agent)
    try:
        for i in range(6):
            panel._appendTranscript('line%d' % i)
        text = panel.transcriptText()
        lines = text.splitlines()
        assert len(lines) == 3
        assert 'line3' in lines and 'line4' in lines and 'line5' in lines
        assert 'line0' not in lines and 'line1' not in lines
        assert 'line2' not in lines

        # The boundary falls inside an assistant line that carries several
        # visible lines: the tail of that line is kept, its lead-in dropped.
        monkeypatch.setattr(panel_module, 'TRANSCRIPT_MAX_LINES', 2)
        panel._appendTranscript('LLM: a\nb\nc')
        text = panel.transcriptText()
        lines = text.splitlines()
        assert len(lines) == 2
        assert lines == ['b', 'c']
    finally:
        key = panel.figureKey
        if key in api.figureframes:
            del api.figureframes[key]
