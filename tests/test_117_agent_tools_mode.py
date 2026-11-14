# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The agent's tools mode: `hide` (the default, tools run with the traffic cut),
`off` (a pure text shape, no tools offered), and `verbose` (the traffic shown).

What it pins, on a scripted LLM:

* `off`: the model is offered no tools at all -- `chat` is called with
  `tools=None`, no gesture is reached, and the "ground it with a tool" guard
  is skipped: the same list-shaped answer that `hide` (and `tests/test_115`)
  refuse with a re-anchor stands in `off`, because in that shape there is no
  tool it could have grounded it with.
* `hide`: the gestures still run (the core is reached) but the transcript
  carries only the prompt, the final answer and the refusals -- neither the
  `-> tool` line nor the `<- result` line, which is the verbos cut without
  cutting the work.
* `verbose`: the transcript carries the whole tool traffic, the shape the
  loop wore before `hide` took the default.

Also pinned: the preference default (`hide`) and the file's named refusal for
a shape the preference does not hold, and the panel's box mirrors the
preference on build and follows the agent's mode on toggle.
"""

import pytest

from imasviz.Viz_API import Viz_API
from imasviz.VizAgent.agent import AgentLoop
from imasviz.VizAgent.llm_client import LLMResponse
from imasviz.VizUtils import QVizPreferences


class FakeLLMClient:
    """A scripted LLM that records what was offered, for the mode asserts."""
    def __init__(self, responses):
        self.responses = list(responses)
        self.offered = []

    def chat(self, messages, tools=None, **kwargs):
        self.offered.append(tools)
        if not self.responses:
            raise AssertionError('FakeLLMClient: no more scripted responses')
        return self.responses.pop(0)


class RecordingCore:
    """A core that records that it was reached: a gesture the agent asked."""
    def __init__(self):
        self.called = []

    def list_cases(self):
        self.called.append('list_cases')
        return [{'uri': 'imas:hdf5?path=/fake', 'dd_version': '3.35.0'}]


class FakeDispatcher:
    """A synchronous dispatcher, like the rest of the agent suite."""
    def call(self, function, timeout=300.0):
        return function()


@pytest.fixture(autouse=True)
def restore_mode():
    """The mode is a class attribute shared across the process; leave it as
    it was, so a test that pins one shape does not leak into the rest of the
    suite -- the same shape the `restore_theme`-class fixtures keep in the
    rest of the tests."""
    saved = QVizPreferences.AgentToolsMode
    yield
    QVizPreferences.AgentToolsMode = saved


@pytest.fixture
def agent_kwargs(qapp):
    return {'main_window': None, 'api': None}


def _run(agent, prompt):
    lines, errors = [], []
    agent.transcriptLine.connect(lines.append)
    agent.askFinished.connect(errors.append)
    agent.ask(prompt)
    return ' '.join(lines), errors


def _make_call_and_answer():
    call = LLMResponse(
        content='',
        tool_calls=[{'name': 'list_cases', 'args': {}}],
        finish_reason='tool_calls')
    final = LLMResponse(
        content='Here are the cases you asked for.',
        tool_calls=None, finish_reason='stop')
    return call, final


# Five distinct, standalone snake_case names: the shape the unfounded guard
# in `hide`/`verbose` refuses, and the same shape `off` lets stand, because
# in that shape there is no tool it could have grounded it with.
LIST_ANSWER = ('This case holds five IDSs: bpol_probe, plasma_boundary, '
               'plasma_current, pulse_schedule and plasma_electron.')


# --------------------------------------------------------------------- modes

def test_off_offers_no_tools_to_the_model(qapp, agent_kwargs):
    """``off``: the model is offered no tools at all, and no gesture is
    reached -- `ask` reaches the LLM once and takes the answer, without
    going back for a call it was not offered."""
    answer = LLMResponse(content='A plain text answer.',
                         tool_calls=None, finish_reason='stop')
    llm = FakeLLMClient([answer])
    core = RecordingCore()
    agent = AgentLoop(core=core, llm=llm, dispatcher=FakeDispatcher(),
                      **agent_kwargs)
    agent.tools_mode = 'off'
    joined, errors = _run(agent, 'list the cases')
    assert errors == [None]
    assert llm.offered, 'the model was asked'
    assert llm.offered[0] is None, \
        'off: the model is offered no tools to call'
    assert core.called == [], 'off: no gesture is reached'
    assert 'A plain text answer.' in joined


def test_off_skips_the_unfounded_ids_guard(qapp, agent_kwargs):
    """The one that distinguishes `off` from `hide`: the same list-shaped
    answer that `tests/test_115_agent_no_confabulation.py` refuses -- a
    recited inventory with no tool to ground it -- stands in `off`, because
    in that shape there is no tool the answer could have been grounded on.
    Re-anchoring at a call the model cannot make is a refusal that cannot be
    acted on, so the answer is what it is.
    """
    answer = LLMResponse(content=LIST_ANSWER, tool_calls=None,
                         finish_reason='stop')
    llm = FakeLLMClient([answer])
    core = RecordingCore()
    agent = AgentLoop(core=core, llm=llm, dispatcher=FakeDispatcher(),
                      **agent_kwargs)
    agent.tools_mode = 'off'
    joined, errors = _run(agent, 'list the ids in the case')
    assert errors == [None], \
        'off: a list-shape answer has no tool it could ground with, so it stands'
    assert 'REFUSAL' not in joined
    assert 'bpol_probe' in joined, \
        'the list in the answer is what the user reads, not a refusal'


def test_hide_runs_tools_but_hides_the_traffic(qapp, agent_kwargs):
    """The default the shape is: the work is still done (the core is reached)
    and the answer still reaches the user -- but the tool traffic is out of
    the transcript, which is the point of the shape and the one a test here
    has to pin against both of the other modes."""
    call, final = _make_call_and_answer()
    llm = FakeLLMClient([call, final])
    core = RecordingCore()
    agent = AgentLoop(core=core, llm=llm, dispatcher=FakeDispatcher(),
                      **agent_kwargs)
    agent.tools_mode = 'hide'
    joined, errors = _run(agent, 'list the cases')
    assert errors == [None]
    assert 'list_cases' in core.called, \
        'hide still runs the agent\'s gesture'
    assert 'list_cases' not in joined, \
        'hide cuts the tool traffic from the transcript'
    assert 'Here are the cases you asked for.' in joined, \
        'the final answer still reaches the user'


def test_verbose_shows_the_traffic(qapp, agent_kwargs):
    """The shape the loop wore before `hide` took the default: the transcript
    carries the call, and the final answer alongside it. The assertion
    `test_110_agent_loop.py::test_tool_call_then_final` pins, named and in
    this shape; pinned here for the mode test's own file too."""
    call, final = _make_call_and_answer()
    llm = FakeLLMClient([call, final])
    core = RecordingCore()
    agent = AgentLoop(core=core, llm=llm, dispatcher=FakeDispatcher(),
                      **agent_kwargs)
    agent.tools_mode = 'verbose'
    joined, errors = _run(agent, 'list the cases')
    assert errors == [None]
    assert 'list_cases' in core.called, 'verbose still runs the agent\'s gesture'
    assert 'list_cases' in joined, 'verbose shows the tool traffic'
    assert 'Here are the cases you asked for.' in joined


def test_default_mode_from_preference_is_hide(qapp, agent_kwargs):
    """The loop's default, read back from the preference: `hide` -- the shape
    a run wears when neither the agent nor a test pins one."""
    answer = LLMResponse(content='A plain text answer.',
                         tool_calls=None, finish_reason='stop')
    llm = FakeLLMClient([answer])
    core = RecordingCore()
    agent = AgentLoop(core=core, llm=llm, dispatcher=FakeDispatcher(),
                      **agent_kwargs)
    # `tools_mode` is `None` at build: `ask` reads it from the preference,
    # which answers its default `hide`.
    assert agent.tools_mode is None
    joined, errors = _run(agent, 'say something')
    assert errors == [None]
    assert llm.offered[0] is not None, \
        'the default `hide` still offers the tools to the model'
    assert 'A plain text answer.' in joined


def test_bad_tools_mode_is_refused(qapp):
    """A line the preference file spells that it does not hold is refused by
    what it says, as every other option in the file is, and the shape stays
    at its default."""
    with pytest.raises(ValueError, match='not a shape'):
        QVizPreferences.toolsMode('bogus')
    assert QVizPreferences.AgentToolsMode == 'hide'


# --------------------------------------------------------------------- panel

def test_panel_tools_box_reflects_the_preference(qapp, agent_kwargs):
    """`off` in the preference is `off` on the box and `off` on the agent:
    the panel mirrors the shape it will run in, so the first click goes
    through without re-asking the user the same choice."""
    from imasviz.VizAgent.panel import QVizAgentPanel

    QVizPreferences.AgentToolsMode = 'off'
    llm = FakeLLMClient([LLMResponse(content='ok', tool_calls=None,
                                     finish_reason='stop')])
    agent = AgentLoop(core=RecordingCore(), llm=llm,
                      dispatcher=FakeDispatcher(), **agent_kwargs)
    api = Viz_API(None)
    panel = QVizAgentPanel(main_window=None, api=api, agent=agent)
    try:
        assert panel.toolsBox.isChecked() is False, \
            'off: the box is unchecked'
        assert agent.tools_mode == 'off', \
            'off: the loop is told to run off'
    finally:
        key = panel.figureKey
        if key in api.figureframes:
            del api.figureframes[key]


def test_panel_tools_box_toggle_sets_the_mode(qapp, agent_kwargs):
    """The switch: off is the chat shape, on is the tools-on shape -- and the
    agent follows it for the rest of the session, so a turn after a toggle
    wears the shape it flipped to. The file is not written (the file is
    where the shape persists; the box is the in-session switch)."""
    from imasviz.VizAgent.panel import QVizAgentPanel

    QVizPreferences.AgentToolsMode = 'hide'
    llm = FakeLLMClient([LLMResponse(content='ok', tool_calls=None,
                                     finish_reason='stop')])
    agent = AgentLoop(core=RecordingCore(), llm=llm,
                      dispatcher=FakeDispatcher(), **agent_kwargs)
    api = Viz_API(None)
    panel = QVizAgentPanel(main_window=None, api=api, agent=agent)
    try:
        assert panel.toolsBox.isChecked() is True, \
            'hide: the box is checked by default'
        panel.toolsBox.setChecked(False)
        assert agent.tools_mode == 'off', \
            'toggle off: the agent runs the chat shape'
        panel.toolsBox.setChecked(True)
        assert agent.tools_mode == 'hide', \
            'toggle on: the agent runs the tools-on shape'
    finally:
        key = panel.figureKey
        if key in api.figureframes:
            del api.figureframes[key]
