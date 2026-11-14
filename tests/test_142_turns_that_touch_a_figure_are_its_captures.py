# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""A turn that touches a figure is a capture of it.

The field report, in the user's words: « L'agent montre d'office les
figures qu'il trace OU NOMME -- ce n'est pas toujours vrai. il faut
souvent que je dise que je ne vois pas le plot pour que cela déclenche
une capture (et ca n'a marche pas tout le temps même en disant ça). »

The repro this file pins, word for word: « trace 2 boucles sur la même
figure » then « multiplie la première courbe par 3 » (a `scale_curve`).
Before the fix the second prompt left a transcript and nothing else:
`scale_curve` changes what the figure SHOWS without redrawing it, so it
was neither the figure the turn drew (the key was held before and after)
nor a window the turn asked to see -- the figure reached the screen only
if the model decided to call `focus_window` on top, with the key exactly
right, and it often did not.

The rule now, mechanical and the same on the three surfaces: a turn's
captures are the figures it drew, the figures its gestures moved
(`captureAsk` reads their `figure_key` as the ask), the windows it asked
to be captured, and -- the « ou nomme » half -- the figures the ACCEPTED
final answer names, the loop saying so on `finalAnswer` and each
surface reading `figuresNamedIn` over the keys the session still holds.
So a move of a curve is a capture of the figure it moved, and a final
answer that names a held figure captures it, on the CLI, on the web,
and the panel raises what the answer named. A figure the session does
not hold cannot be captured that way: the scan walks the held keys, so
an invented or a closed key is not a capture ask and earns no refusal of
its own (that refusal stays the core's, `test_132`'s close turn).
"""

import base64
import os

import pytest

from imasviz.VizAgent.agent import AgentLoop, figuresNamedIn
from imasviz.VizAgent.llm_client import LLMResponse
from mcp_server.agent_mode import FIGURE_MUTATIONS, captureAsk

from test_110_agent_loop import FakeCore as BaseCore, FakeDispatcher
from test_111_agent_panel import FakeLLMClient as PanelLLMClient
from test_113_viz_cli import (
    CASE_URI, FakeCore as CliFakeCore, FakeWindow as CliFakeWindow,
    FakeLLMClient as CliLLMClient, PNG_1x1 as CLI_PNG)
from test_119_viz_web_session import (
    CASE_URI as WEB_CASE_URI, FakeCore as WebFakeCore, FakeLLMClient,
    build, inWorker, PNG_1x1)

DEAD_ENDPOINT = 'http://127.0.0.1:65531/v1'


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    """A turn lands in the one prompt history the application shares,
    under ``$HOME/.imasviz``, and the panel reads it at build: every
    test here points ``HOME`` at its own folder rather than the user's
    real one -- the pattern ``test_113`` and ``test_111`` keep.
    """
    monkeypatch.setenv('HOME', str(tmp_path))


# ------------------------------------------------------------------- captureAsk

def test_captureAsk_reads_the_figure_of_the_mutation_gestures():
    """The eight gestures that change what a figure shows without
    redrawing it are all capture asks, on the figure they work on --
    and the two READS (`curve_stats`, `export_curve`) are not: they
    answer numbers, they do not move the picture the user sees."""
    assert set(FIGURE_MUTATIONS) == {
        'scale_curve', 'shift_curve', 'normalize_curve', 'reset_curve',
        'remove_curve', 'set_axis_range', 'set_log_scale', 'invert_axis'}
    for name in FIGURE_MUTATIONS:
        assert captureAsk(name, {'figure_key': 'SlicesPlot1'}) \
            == 'SlicesPlot1', name
    for name in ('curve_stats', 'export_curve'):
        assert captureAsk(name, {'figure_key': 'SlicesPlot1'}) is None, \
            'a read is not a figure the user must see: %s' % name


def test_captureAsk_reads_the_other_ask_shapes_and_the_absences():
    """The other asks keep their shapes (the window, the redraw's
    target), and a gesture with no figure to point at is not an ask:
    no name, no arguments, a read's arguments, an unknown name -- all
    of them answer ``None`` rather than a guess."""
    assert captureAsk('plot_one',
                      {'uri': CASE_URI, 'path': 'core.ion[0].temp'}) \
        is None
    assert captureAsk('plot_one',
                      {'uri': CASE_URI, 'path': 'core.ion[0].temp',
                       'into_figure_key': 'SlicesPlot1'}) == 'SlicesPlot1'
    assert captureAsk('get_screenshot', {'window': 'SlicesPlot1'}) \
        == 'SlicesPlot1'
    assert captureAsk('get_screenshot', {}) == 'app'
    assert captureAsk('get_screenshot', None) == 'app'
    assert captureAsk('focus_window', {}) == 'app'
    assert captureAsk('focus_window', None) == 'app'
    assert captureAsk('scale_curve', None) is None
    assert captureAsk('a_gesture_not_here', {'figure_key': 'Plot1'}) \
        is None


# ------------------------------------------------------------------- figuresNamedIn

def test_a_key_is_not_named_inside_a_longer_key():
    """A name standing inside another spelling is not the name: the
    tail of a longer key is the longer key, and the 12th figure is not
    the first. The scan is the whole rule, so it is pinned against the
    two shapes it must not break."""
    assert figuresNamedIn(
        'voilà EquiPlotView:1',
        ['PlotView:1', 'EquiPlotView:1']) == ['EquiPlotView:1']
    assert figuresNamedIn(
        'la figure est SlicesPlot12',
        ['SlicesPlot1', 'SlicesPlot12']) == ['SlicesPlot12']
    assert figuresNamedIn(
        'voir SlicesPlot1, puis SlicesPlot12',
        ['SlicesPlot1', 'SlicesPlot12']) == ['SlicesPlot1',
                                             'SlicesPlot12']


def test_the_names_come_back_in_the_order_asked():
    """Whatever the order the text met the keys, the answer walks the
    keys as they were asked -- the callers ask a sorted list, so the
    set the surfaces save is deterministic."""
    assert figuresNamedIn("d'abord B, puis A", ['A', 'B']) == ['A', 'B']
    assert figuresNamedIn("d'abord B, puis A", ['B', 'A']) == ['B', 'A']
    assert figuresNamedIn('rien ici', ['SlicesPlot1', 'PlotView:3']) == []


def test_an_empty_answer_or_no_keys_names_nothing():
    """``None`` and the empty answer name nothing; a candidate list with
    an empty entry skips it instead of asking Qt for `''`."""
    assert figuresNamedIn(None, ['SlicesPlot1']) == []
    assert figuresNamedIn('', ['SlicesPlot1']) == []
    assert figuresNamedIn('SlicesPlot1', []) == []
    assert figuresNamedIn('C est dans SlicesPlot1.', ['']) == []
    assert figuresNamedIn('SlicesPlot1.', ['', 'SlicesPlot1']) \
        == ['SlicesPlot1']


# ------------------------------------------------------------------- finalAnswer

def test_final_answer_carries_the_accepted_text(qapp):
    """The one signal the surfaces read the named figures from: emitted
    once, on the path that accepts, with the answer exactly as it
    stands -- no prefix, no transcript formatting."""
    llm = PanelLLMClient(
        [LLMResponse(content="C'est fait, la courbe est triplée.",
                     tool_calls=None, finish_reason='stop')])
    agent = AgentLoop(core=BaseCore(), llm=llm, dispatcher=FakeDispatcher())
    finals = []
    agent.finalAnswer.connect(finals.append)
    errors = []
    agent.askFinished.connect(errors.append)
    agent.ask('multiplie la courbe par 3')
    assert errors == [None]
    assert finals == ["C'est fait, la courbe est triplée."]


def test_a_refused_answer_is_not_final(qapp):
    """The two refusals that carry text in -- the truncation and the
    empty answer -- never reach the surfaces: no `finalAnswer`, so a
    truncated answer cannot name a figure into a capture."""
    for content in ('partiel...', ''):
        llm = PanelLLMClient(
            [LLMResponse(content=content, tool_calls=None,
                         finish_reason=('length' if content else 'stop'))])
        agent = AgentLoop(core=BaseCore(), llm=llm,
                          dispatcher=FakeDispatcher())
        finals = []
        agent.finalAnswer.connect(finals.append)
        errors = []
        agent.askFinished.connect(errors.append)
        agent.ask('réponds')
        assert errors and errors[0] is not None
        assert finals == [], content


# ------------------------------------------------------------------- the CLI

class MutatingCliCore(CliFakeCore):
    """The stand-in core plus the one gesture the field report drove:
    it moves the figure it holds, and a key it does not hold is refused
    by the name the real core answers."""

    def scale_curve(self, figure_key, factor=1.0, curve=None):
        if any(record['key'] == figure_key for record in self._windows):
            return {'figure': figure_key, 'factor': factor}
        raise ValueError('No window holds the key "%s" any more' % figure_key)


def buildCli(qapp, tmp_path, llm, core):
    """One REPL session on stand-ins, the `buildSession` of `test_113`
    with a core the test names -- the scripted LLM goes straight in,
    the way that builder does."""
    from viz_cli.session import CliSession, Client
    from imasviz.VizAgent.llm_client import LLMClient
    session = CliSession(
        app=qapp, window=CliFakeWindow(), core=core, llm=llm,
        shots_dir=str(tmp_path / 'shots' / 'default'), max_turns=8)
    return session, core


def test_a_prompt_that_moved_a_figure_keeps_its_capture(qapp, tmp_path):
    """The field repro, pinned: after the figure is drawn, « multiplie
    la courbe par 3 » is a `scale_curve` that changes what it shows
    without redrawing it -- held before, held after, never asked -- and
    the answer says nothing about the figure. Before the fix this
    prompt left a transcript and nothing else; now the gesture's
    `figure_key` is the capture ask, and the figure is in the prompt's
    directory, the PNG the user acts on."""
    llm = CliLLMClient([
        LLMResponse(tool_calls=[
            {'name': 'plot_one',
             'args': {'uri': CASE_URI, 'path': 'core.ion[0].temp'}}],
            content=''),
        LLMResponse(content='Les deux boucles sont tracées.',
                    finish_reason='stop'),
        LLMResponse(tool_calls=[
            {'name': 'scale_curve',
             'args': {'figure_key': 'SlicesPlot1', 'factor': 3}}],
            content=''),
        LLMResponse(content='C\'est fait, la courbe est triplée.',
                    finish_reason='stop'),
    ])
    core = MutatingCliCore()
    session, _ = buildCli(qapp, tmp_path, llm, core)
    first = session.runPrompt('trace 2 boucles sur la même figure')
    assert first['refusal'] is None
    assert os.path.isfile(first['dir'] + '/SlicesPlot1.png')

    second = session.runPrompt('multiplie la première courbe par 3')
    assert second['refusal'] is None
    files = os.listdir(second['dir'])
    assert 'SlicesPlot1.png' in files, \
        'the figure the gesture moved is not in the prompt that moved ' \
        'it: %r' % files
    with open(second['dir'] + '/SlicesPlot1.png', 'rb') as f:
        assert f.read() == CLI_PNG


def test_a_prompt_that_only_named_a_figure_keeps_its_capture(qapp, tmp_path):
    """The « ou nomme » half, mechanical: the turn draws nothing, asks
    nothing, and the ACCEPTED final answer names the held figure -- the
    scan of `finalAnswer` is what the figures the answer shows come
    from, not a focus_window the model must remember to call."""
    llm = CliLLMClient([
        LLMResponse(tool_calls=[
            {'name': 'plot_one',
             'args': {'uri': CASE_URI, 'path': 'core.ion[0].temp'}}],
            content=''),
        LLMResponse(content='La figure est tracée.',
                    finish_reason='stop'),
        LLMResponse(content='La courbe est stable dans SlicesPlot1.',
                    finish_reason='stop'),
    ])
    session, _ = buildCli(qapp, tmp_path, llm, MutatingCliCore())
    session.runPrompt('trace une boucle')
    third = session.runPrompt('est-ce que la courbe bouge ?')
    assert third['refusal'] is None
    assert os.path.isfile(third['dir'] + '/SlicesPlot1.png'), \
        'the figure the final answer named is not in the prompt that ' \
        'named it'


def test_a_prompt_that_names_a_held_key_inside_a_longer_one_saves_the_longer(
        qapp, tmp_path):
    """The boundary the scan owes to a session that holds both: the
    answer names the 12th figure, the first sits inside its spelling,
    and it is the 12th that is saved."""
    core = MutatingCliCore()
    core._windows.append({'kind': 'SlicesPlot', 'label': 'SlicesPlot 12',
                          'key': 'SlicesPlot12', 'visible': True,
                          'cases': []})
    llm = CliLLMClient([
        LLMResponse(content='Elle est dans SlicesPlot12.',
                    finish_reason='stop'),
    ])
    session, _ = buildCli(qapp, tmp_path, llm, core)
    out = session.runPrompt('où est la courbe ?')
    assert 'SlicesPlot12.png' in os.listdir(out['dir'])
    assert 'SlicesPlot1.png' not in os.listdir(out['dir'])


def test_a_prompt_that_names_a_figure_the_session_does_not_hold_saves_nothing(
        qapp, tmp_path):
    """A name the session does not hold cannot become a capture: the
    scan walks the held keys, so the answer names nothing and the
    prompt saves the transcript alone -- and it saves it without a
    REFUSAL of its own, because this is not the ask of a figure the
    core would have to refuse (the refusal stays the close-turn's,
    `test_132`)."""
    llm = CliLLMClient([
        LLMResponse(tool_calls=[
            {'name': 'plot_one',
             'args': {'uri': CASE_URI, 'path': 'core.ion[0].temp'}}],
            content=''),
        LLMResponse(content='La figure est tracée.',
                    finish_reason='stop'),
        LLMResponse(content='Elle est dans SlicesPlot9.',
                    finish_reason='stop'),
    ])
    session, _ = buildCli(qapp, tmp_path, llm, MutatingCliCore())
    session.runPrompt('trace une boucle')
    fourth = session.runPrompt('où est la courbe ?')
    assert fourth['refusal'] is None
    assert fourth['refused'] == []
    files = os.listdir(fourth['dir'])
    assert 'SlicesPlot9.png' not in files
    assert 'SlicesPlot1.png' not in files


# ------------------------------------------------------------------- the web

class MutatingWebCore(WebFakeCore):
    """The web stand-in plus the gesture the field report was reported
    on: the same one the CLI tests drive, against the same stand-in it
    inherited."""

    def scale_curve(self, figure_key, factor=1.0, curve=None):
        if any(record['key'] == figure_key for record in self._windows):
            return {'figure': figure_key, 'factor': factor}
        raise ValueError('No window holds the key "%s" any more' % figure_key)


def test_the_web_turn_that_moved_a_figure_keeps_its_capture(qapp, tmp_path):
    """The same hole reported on the web surface, the one the user
    tested: the figure is captured in the turn that drew it, and AGAIN
    in the turn that moved its curve -- `scale_curve` asking nothing --
    and a name the turn does not hold is neither a picture nor a
    refusal, as in the REPL."""
    llm = FakeLLMClient([
        LLMResponse(tool_calls=[
            {'name': 'plot_one',
             'args': {'uri': WEB_CASE_URI, 'path': 'core.ion[0].temp'}}],
            content=''),
        LLMResponse(content='La figure est tracée.', finish_reason='stop'),
        LLMResponse(tool_calls=[
            {'name': 'scale_curve',
             'args': {'figure_key': 'SlicesPlot1', 'factor': 3}}],
            content=''),
        LLMResponse(content='La courbe est triplée.',
                    finish_reason='stop'),
        LLMResponse(content='Elle est dans SlicesPlot9.',
                    finish_reason='stop'),
    ])
    session, core = build(qapp, tmp_path, llm=llm, core=MutatingWebCore())

    first = inWorker(
        lambda: session.runTurn('trace 2 boucles sur la même figure'), qapp)
    assert first['error'] is None
    assert first['image_files'] == ['SlicesPlot1.png']
    assert first['refusals'] == []

    second = inWorker(
        lambda: session.runTurn('multiplie la première courbe par 3'), qapp)
    assert second['error'] is None
    assert second['image_files'] == ['SlicesPlot1.png'], \
        'the web turn that moved the figure no longer keeps its capture: ' \
        '%r' % second['image_files']
    png = next(im for im in second['images']
               if im['name'] == 'SlicesPlot1.png')
    assert png['window'] == 'SlicesPlot1'
    assert base64.b64decode(png['b64']) == PNG_1x1

    third = inWorker(lambda: session.runTurn('où est la courbe ?'), qapp)
    assert third['error'] is None
    assert third['image_files'] == []
    assert third['refusals'] == []


# ------------------------------------------------------------------- the panel

class FocusCore(BaseCore):
    """A core that shows: it records the raises it is asked for, and
    answers the size the real `focus_window` answers."""

    def __init__(self):
        self.focusCalls = []

    def focus_window(self, window='app', width=None, height=None):
        self.focusCalls.append(window)
        return {'window': window, 'visible': True,
                'size': [width or 1280, height or 800]}


class RefusingFocusCore(BaseCore):
    """The window went away between the answer and the raise: the core
    earns its named refusal, and the panel says it in the transcript."""

    def focus_window(self, window='app', width=None, height=None):
        raise ValueError('No window holds the key "%s" any more' % window)


def test_the_panel_raises_the_figure_the_answer_named(qapp):
    """The panel's half of the promise: the ACCEPTED answer names the
    figure the session holds, and the panel raises it -- the user sees
    what the answer named, on the same mechanical rule the CLI and the
    web capture it."""
    from imasviz.VizAgent.panel import QVizAgentPanel
    from imasviz.Viz_API import Viz_API

    llm = PanelLLMClient(
        [LLMResponse(
            content='C\'est stable dans SlicesPlot1.',
            tool_calls=None, finish_reason='stop')])
    core = FocusCore()
    agent = AgentLoop(core=core, llm=llm, dispatcher=FakeDispatcher())
    api = Viz_API(None)
    panel = QVizAgentPanel(main_window=None, api=api, agent=agent)
    key = panel.figureKey
    api.figureframes['SlicesPlot1'] = object()
    try:
        panel.setPrompt('est-ce que la courbe bouge ?')
        panel.runAgent()  # Synchronous: the raise runs before it returns.
        assert core.focusCalls == ['SlicesPlot1'], \
            'the panel did not raise the figure the answer named: %r' \
            % core.focusCalls
        # The panel itself owns that window: its key is filtered out of
        # the answer's names, and a raise of it is the answer naming the
        # panel, not a figure.
        assert key not in core.focusCalls
    finally:
        api.figureframes.pop('SlicesPlot1', None)
        if key in api.figureframes:
            del api.figureframes[key]


def test_the_panel_does_not_raise_a_figure_it_does_not_hold(qapp):
    """The answer names a key the session does not hold: the scan walks
    the held keys, so the raise is not the one the panel asks -- a
    raise of a held key is a raise of a real window, and an invented
    name does not dress the transcript as a REFUSAL."""
    from imasviz.VizAgent.panel import QVizAgentPanel
    from imasviz.Viz_API import Viz_API

    llm = PanelLLMClient(
        [LLMResponse(content='Elle est dans SlicesPlot9.',
                     tool_calls=None, finish_reason='stop')])
    core = FocusCore()
    agent = AgentLoop(core=core, llm=llm, dispatcher=FakeDispatcher())
    api = Viz_API(None)
    panel = QVizAgentPanel(main_window=None, api=api, agent=agent)
    key = panel.figureKey
    api.figureframes['SlicesPlot1'] = object()
    try:
        panel.setPrompt('où est la courbe ?')
        panel.runAgent()
        assert core.focusCalls == []
        assert 'REFUSAL' not in panel.transcriptText()
    finally:
        api.figureframes.pop('SlicesPlot1', None)
        if key in api.figureframes:
            del api.figureframes[key]


def test_a_core_without_a_focus_gesture_is_skipped(qapp):
    """The stand-ins of this suite hold no raise of their own: a core
    that cannot show a figure skips the raise silently -- there is no
    figure to show, and a refusal the core would not earn is not a line
    the transcript writes."""
    from imasviz.VizAgent.panel import QVizAgentPanel
    from imasviz.Viz_API import Viz_API

    llm = PanelLLMClient(
        [LLMResponse(content='Elle est dans SlicesPlot1.',
                     tool_calls=None, finish_reason='stop')])
    assert not hasattr(BaseCore(), 'focus_window')
    agent = AgentLoop(core=BaseCore(), llm=llm, dispatcher=FakeDispatcher())
    api = Viz_API(None)
    panel = QVizAgentPanel(main_window=None, api=api, agent=agent)
    key = panel.figureKey
    api.figureframes['SlicesPlot1'] = object()
    try:
        panel.setPrompt('où est la courbe ?')
        panel.runAgent()
        text = panel.transcriptText()
        assert 'Elle est dans SlicesPlot1.' in text
        assert 'REFUSAL' not in text
    finally:
        api.figureframes.pop('SlicesPlot1', None)
        if key in api.figureframes:
            del api.figureframes[key]


def test_a_refused_raise_is_named_in_the_transcript(qapp):
    """The one case between the two: the session held the key when the
    answer came, and let it go before the raise ran -- the core earns
    its named refusal, and the panel says it where the user reads the
    turn, not the silence."""
    from imasviz.VizAgent.panel import QVizAgentPanel
    from imasviz.Viz_API import Viz_API

    llm = PanelLLMClient(
        [LLMResponse(content='Elle est dans SlicesPlot1.',
                     tool_calls=None, finish_reason='stop')])
    agent = AgentLoop(core=RefusingFocusCore(), llm=llm,
                      dispatcher=FakeDispatcher())
    api = Viz_API(None)
    panel = QVizAgentPanel(main_window=None, api=api, agent=agent)
    key = panel.figureKey
    api.figureframes['SlicesPlot1'] = object()
    try:
        panel.setPrompt('où est la courbe ?')
        panel.runAgent()
        text = panel.transcriptText()
        assert 'REFUSAL' in text
        assert 'focus' in text
        assert 'SlicesPlot1' in text
    finally:
        api.figureframes.pop('SlicesPlot1', None)
        if key in api.figureframes:
            del api.figureframes[key]
