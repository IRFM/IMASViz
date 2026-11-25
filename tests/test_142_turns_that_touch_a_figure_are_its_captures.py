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
figure » then « multiplie la première courbe par 3 » (a
`transform_curve` whose `operation` is `scale`).
Before the fix the second prompt left a transcript and nothing else:
that call changes what the figure SHOWS without redrawing it, so it
was neither the figure the turn drew (the key was held before and after)
nor a window the turn asked to see -- the figure reached the screen only
if the model decided to call `focus_window` on top, with the key exactly
right, and it often did not.

The rule now, mechanical and the same on the three surfaces: a turn's
captures are the figures it drew, the figures its gestures moved
(`captureAsk` reads their `figure_key` as the ask), and the windows it
asked to be captured (`get_screenshot`, or a `focus_window` the user's
"montre-moi" reached). A figure the accepted answer only NAMES is not
among them: showing a figure is the user's command, not the model's
standing duty -- the figure is in the *Windows* menu, and a show the
user asks is the gesture the loop runs when the user asks it
(`test_136` pins its guard, `test_111` the panel). So a move of a curve
is a capture of the figure it moved, on the CLI and on the web, and a
mention of a held figure in the answer is the answer alone.
"""

import base64
import os

import pytest

from imasviz.VizAgent.llm_client import LLMResponse
from mcp_server.agent_mode import FIGURE_MUTATIONS, captureAsk

from test_113_viz_cli import (
    CASE_URI, FakeCore as CliFakeCore, FakeWindow as CliFakeWindow,
    FakeLLMClient as CliLLMClient, PNG_1x1 as CLI_PNG)
from test_119_viz_web_session import (
    CASE_URI as WEB_CASE_URI, FakeCore as WebFakeCore, FakeLLMClient,
    build, inWorker, PNG_1x1)


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
    """The ten gestures that change what a figure shows without
    redrawing it are all capture asks, on the figure they work on --
    and the two READS (`curve_stats`, `export_curve`) are not: they
    answer numbers, they do not move the picture the user sees."""
    assert set(FIGURE_MUTATIONS) == {
        'scale_curve', 'shift_curve', 'normalize_curve', 'reset_curve',
        'remove_curve', 'set_axis_range', 'set_image_window',
        'set_slice_index', 'set_log_scale', 'invert_axis'}
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
    # The same two shapes spelled as a turn spells them today: a merged
    # group answers one name and a discriminant, while the rule above is
    # written gesture by gesture. A ``plot(mode="single")`` that reached a
    # different answer than the ``plot_one`` it means is a turn that leaves
    # the user a transcript and no picture.
    assert captureAsk('plot', {'mode': 'single', 'uri': CASE_URI,
                               'path': 'core.ion[0].temp'}) is None
    assert captureAsk('plot', {'mode': 'single', 'uri': CASE_URI,
                               'path': 'core.ion[0].temp',
                               'into_figure_key': 'SlicesPlot1'}) \
        == 'SlicesPlot1'
    assert captureAsk('plot', {'mode': 'slice', 'uri': CASE_URI,
                               'path': 'core.ion[0].temp',
                               'time': 3.0}) is None
    assert captureAsk('get_screenshot', {'window': 'SlicesPlot1'}) \
        == 'SlicesPlot1'
    assert captureAsk('get_screenshot', {}) == 'app'
    assert captureAsk('get_screenshot', None) == 'app'
    assert captureAsk('focus_window', {}) == 'app'
    assert captureAsk('focus_window', None) == 'app'
    assert captureAsk('focus_window', {'window': 'SlicesPlot1'}) \
        == 'SlicesPlot1'
    assert captureAsk('scale_curve', None) is None
    assert captureAsk('a_gesture_not_here', {'figure_key': 'Plot1'}) \
        is None


# ------------------------------------------------------------------- the CLI

class MutatingCliCore(CliFakeCore):
    """The stand-in core plus the two gestures this file drives: it
    moves the figure it holds (the field report's `scale_curve`), and it
    shows it the way the real `focus_window` shows it -- a held key is
    brought to the front and answers its own size, a key it does not
    hold is refused by the name the real core answers."""

    def scale_curve(self, figure_key, factor=1.0, curve=None):
        if any(record['key'] == figure_key for record in self._windows):
            return {'figure': figure_key, 'factor': factor}
        raise ValueError('No window holds the key "%s" any more' % figure_key)

    def focus_window(self, window='app', width=None, height=None):
        if window == 'app':
            return {'window': 'app', 'visible': True, 'size': [800, 600]}
        if any(record['key'] == window for record in self._windows):
            return {'window': window, 'visible': True, 'size': [800, 600]}
        raise ValueError('No window holds the key "%s" any more' % window)


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
            {'name': 'plot',
             'args': {'mode': 'single', 'uri': CASE_URI, 'path': 'core.ion[0].temp'}}],
            content=''),
        LLMResponse(content='Les deux boucles sont tracées.',
                    finish_reason='stop'),
        LLMResponse(tool_calls=[
            {'name': 'transform_curve',
             'args': {'figure_key': 'SlicesPlot1', 'operation': 'scale',
                      'factor': 3}}],
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


def test_a_prompt_that_only_named_a_figure_saves_the_answer_alone(
        qapp, tmp_path):
    """The direction this rule now owes to the mention: the turn draws
    nothing, moves nothing, and the accepted answer NAMES the held
    figure -- a show is the prompt's own command ("montre-moi
    SlicesPlot1"), and a mention is neither, so the prompt saves the
    transcript alone. The figure stays in the directory of the prompt
    that drew it, where the user already has it."""
    llm = CliLLMClient([
        LLMResponse(tool_calls=[
            {'name': 'plot',
             'args': {'mode': 'single', 'uri': CASE_URI, 'path': 'core.ion[0].temp'}}],
            content=''),
        LLMResponse(content='La figure est tracée.',
                    finish_reason='stop'),
        LLMResponse(content='La courbe est stable dans SlicesPlot1.',
                    finish_reason='stop'),
    ])
    session, _ = buildCli(qapp, tmp_path, llm, MutatingCliCore())
    first = session.runPrompt('trace une boucle')
    assert os.path.isfile(first['dir'] + '/SlicesPlot1.png'), \
        'the figure the prompt drew is not in the directory of the ' \
        'prompt that drew it'
    second = session.runPrompt('est-ce que la courbe bouge ?')
    assert second['refusal'] is None
    assert second['refused'] == []
    files = os.listdir(second['dir'])
    assert 'SlicesPlot1.png' not in files, \
        'a figure the answer only named is captured again: the mention ' \
        'is a show again -- %r' % files
    assert 'transcript.txt' in files


def test_an_explicit_show_of_a_held_figure_is_a_capture(qapp, tmp_path):
    """The half this rule still owes to the user: when the prompt
    ASKS to see the held figure — the "montre-moi SlicesPlot1" that
    reaches it — the focus it earned is the capture ask, and
    the figure is in this prompt's directory like any other ask."""
    llm = CliLLMClient([
        LLMResponse(tool_calls=[
            {'name': 'plot',
             'args': {'mode': 'single', 'uri': CASE_URI, 'path': 'core.ion[0].temp'}}],
            content=''),
        LLMResponse(content='La figure est tracée.',
                    finish_reason='stop'),
        LLMResponse(tool_calls=[
            {'name': 'manage_window',
             'args': {'action': 'focus', 'window': 'SlicesPlot1'}}],
            content='C’est devant.',
        ),
        LLMResponse(content='C’est devant.', finish_reason='stop'),
    ])
    session, _ = buildCli(qapp, tmp_path, llm, MutatingCliCore())
    session.runPrompt('trace une boucle')
    second = session.runPrompt('montre-moi SlicesPlot1')
    assert second['refusal'] is None
    files = os.listdir(second['dir'])
    assert 'SlicesPlot1.png' in files, \
        'an explicit show of a held figure is not a capture ask: %r' % files


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
    in the turn that moved its curve -- the transform asking nothing --
    and a mention the turn does not act on is neither a picture nor a
    refusal, as in the REPL."""
    llm = FakeLLMClient([
        LLMResponse(tool_calls=[
            {'name': 'plot',
             'args': {'mode': 'single', 'uri': WEB_CASE_URI, 'path': 'core.ion[0].temp'}}],
            content=''),
        LLMResponse(content='La figure est tracée.', finish_reason='stop'),
        LLMResponse(tool_calls=[
            {'name': 'transform_curve',
             'args': {'figure_key': 'SlicesPlot1', 'operation': 'scale',
                      'factor': 3}}],
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
    assert third['image_files'] == [], \
        'a figure the answer only named is captured again on the web: ' \
        'the mention is a show again'
    assert third['refusals'] == []
