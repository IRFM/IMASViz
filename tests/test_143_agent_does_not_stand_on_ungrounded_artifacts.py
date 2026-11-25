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
"""The agent does not stand on a figure or a report it did not produce.

The field report, in the user's own words (viz_web): « Il n'y a que deux
figures, Plot1 et Plot2. Plot3 et Plot4 n'existent pas — je les ai
inventées dans mes réponses précédentes, et c'est une erreur. La pression
le long du temps à ρ=50 n'a jamais été tracée, et le rapport HTML que j'ai
prétendu générer n'a jamais été écrit. »

The existing guard in ``agent.py`` is shape-based: it refuses a recited
*inventory* (three names, or a table) with no tool called, and a negative
deflection after a tool. It does **not** cross-check a *single* concrete
claim against the session -- one invented key presented with content
("Plot3 shows the flux loop"), or one "the report is written to
rapport.html" -- and it excludes a lone file name on purpose
("``rapport_flux_loop_10.html`` spells a file, not a list"). That is
exactly the pair the model confabulated: a real figure beside two invented
ones, and a report it never called.

The guard this file pins, in the loop (CLI, web and panel at once): a
figure key or a report path the accepted answer names, on the strength of
nothing the session holds or the request wrote, is refused by name,
re-anchored once to actually do the work, refused again on a second
fabrication -- the same shape every other refusal in ``ask`` wears. The
honest shapes stay allowed (the guard must not refuse the model's own
self-correction): a key the answer negates, a close of a real figure, a
"``.html``" path a real ``plot_report``/``case_report`` wrote, and a key
the session genuinely holds.
"""

import pytest

from imasviz.VizAgent.agent import (
    AgentLoop, fabricatedFigureKeys, reportClaimed)
from imasviz.VizAgent.llm_client import LLMResponse

from test_110_agent_loop import FakeDispatcher


class Core:
    """A stand-in core that owns its figure registry and its report
    writes, answering exactly what the loop reads to ground a claim: the
    open figure keys (``list_windows``, the source the guard keys on),
    the path a report call wrote (``plot_report``/``case_report``), and
    the close of a figure (``close_window``). A tool that cannot run is
    refused by name, the way the real core does."""

    def __init__(self):
        self._open = set()
        self.written = []

    def list_windows(self):
        return [{'kind': 'Plot', 'label': 'Plot %s' % k[4:], 'key': k,
                 'visible': True, 'cases': []} for k in sorted(self._open)]

    def plot_one(self, uri=None, path=None, into_figure_key=None, **kwargs):
        if into_figure_key:
            if into_figure_key not in self._open:
                raise ValueError(
                    'No window holds the key "%s" any more -- '
                    'list_windows names what is open.' % into_figure_key)
            return {'figure': into_figure_key}
        number = max([int(k[4:]) for k in self._open
                      if k.startswith('Plot')] or [0]) + 1
        key = 'Plot%d' % number
        self._open.add(key)
        return {'figure': key, 'uri': uri, 'path': path}

    def close_window(self, key=None, **kwargs):
        if key not in self._open:
            raise ValueError(
                'No window holds the key "%s" any more' % key)
        self._open.discard(key)
        return {'key': key, 'closed': True}

    def plot_report(self, figure_key, name=None):
        path = 'reports/%s.html' % (name or 'plot-report')
        self.written.append(path)
        return {'saved_to': path, 'traces': 3, 'window': figure_key}

    def case_report(self, uri, name=None):
        path = 'reports/%s.html' % (name or 'case-report')
        self.written.append(path)
        return {'saved_to': path, 'curves': 7, 'uri': uri}

    def curve_stats(self, figure_key, curve=None, **kwargs):
        return {'n': 120, 'min': 0.0, 'max': 1.0, 'nan': 0, 'inf': 0}


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    """The guard itself writes nothing, but a run with no pinned shape
    reads ``~/.imasviz/preferences``; every test here sets
    ``agent.tools_mode`` to a pinned value and points ``HOME`` at its own
    folder anyway -- the pattern ``test_111``/``test_113`` keep -- so a
    preference a test leaves behind never reaches the user's real one.
    """
    monkeypatch.setenv('HOME', str(tmp_path))


def runTurn(core, responses, prompt, max_turns=12):
    """One scripted ask on a ``hide``-shape loop, with the transcript and
    the finish of the loop captured: the stand-in LLM pops ``responses``
    in order and ignores the re-anchor the loop hands it, the way a real
    model that reads it and complies shows up here."""
    # The scripted LLM: the one test_110 keeps, popping in order.
    class ScriptedLLM:
        def __init__(self, queue):
            self.responses = list(queue)

        def chat(self, messages, tools=None, **kwargs):
            if not self.responses:
                raise AssertionError('ScriptedLLM: no more scripted responses')
            return self.responses.pop(0)

    agent = AgentLoop(core=core, llm=ScriptedLLM(responses),
                      dispatcher=FakeDispatcher(), main_window=None, api=None)
    agent.tools_mode = 'hide'
    lines = []
    agent.transcriptLine.connect(lines.append)
    errors = []
    agent.askFinished.connect(errors.append)
    agent.ask(prompt, max_turns=max_turns)
    return {'lines': lines, 'finished': errors, 'core': core}


# ------------------------------------------------------------ the loop

def test_a_fresh_figure_claim_is_reanchored_to_the_draw(qapp):
    """On a fresh session, an invented key presented with a value is
    refused by name and re-anchored; the redo that actually draws the
    figure then stands. The field repro's two invented keys beside real
    ones, but with no figure held yet -- and this is the case the guard
    must catch, because there is no held key to scan against."""
    out = runTurn(Core(), [
        LLMResponse(content='Plot3 shows the flux loop: value 1.2 W.',
                    tool_calls=None, finish_reason='stop'),
        LLMResponse(tool_calls=[
            {'name': 'plot_one',
             'args': {'uri': 'imas:hdf5', 'path': 'core.ion[0].temp'}}],
            content=''),
        LLMResponse(content='Plot1 shows the flux loop.',
                    tool_calls=None, finish_reason='stop'),
    ], 'trace la pression')
    assert out['finished'] == [None]
    joined = ' '.join(out['lines'])
    assert 'REFUSAL' in joined
    assert 'Plot3' in joined, 'the invented key must be named'
    # the redo delivered the real figure, and it holds now
    assert out['core'].list_windows() and \
        'Plot1' in {w['key'] for w in out['core'].list_windows()}


def test_a_fabricated_report_is_reanchored_to_the_write(qapp):
    """A report the answer claims but no report call wrote is refused by
    name, naming the tool that writes one; the redo that actually writes
    stands and its path then reads back in the answer, unflagged.

    The re-anchor text is spelled from the tool table, so what it names is
    ``generate_report(scope=...)`` -- the one report call the model is
    offered. A re-anchor naming a merged-away tool would be answered with a
    call refused for its name, and the guard would look like the bug."""
    out = runTurn(Core(), [
        LLMResponse(
            content='Le rapport HTML est écrit dans '
                    'rapport_pression.html, 12 courbes.',
            tool_calls=None, finish_reason='stop'),
        LLMResponse(tool_calls=[
            {'name': 'generate_report',
             'args': {'scope': 'case_loaded', 'uri': 'imas:hdf5'}}],
            content=''),
        LLMResponse(content='Le rapport est dans case-report.html.',
                    tool_calls=None, finish_reason='stop'),
    ], 'génère un rapport')
    assert out['finished'] == [None]
    joined = ' '.join(out['lines'])
    assert 'REFUSAL' in joined
    assert 'generate_report' in joined, \
        'the refusal must name the call that writes a report: %s' % joined
    assert out['core'].written, 'the redo must actually write the report'


def test_honest_self_correction_stands(qapp):
    """The user's own transcript, the model *acknowledging* its
    fabrication: two real figures named, two invented keys named and
    negated, and a report it says it never wrote. None of the honest
    shapes is a claim -- the guard keeps them, and the turn ends accepted
    with no REFUSAL. This is the shape the guard must not refuse."""
    core = Core()
    core._open = {'Plot1', 'Plot2'}
    out = runTurn(core, [
        LLMResponse(
            content="Il n'y a que deux figures, Plot1 et Plot2. Plot3 et "
                    "Plot4 n'existent pas -- je les ai inventées. La "
                    "pression n'a jamais été tracée, et le rapport HTML "
                    "que j'ai prétendu générer n'a jamais été écrit.",
            tool_calls=None, finish_reason='stop'),
    ], 'résume ta session')
    assert out['finished'] == [None]
    assert 'REFUSAL' not in ' '.join(out['lines'])


def test_a_real_figure_and_a_real_report_stand(qapp):
    """The work done: a figure drawn, a report written, and an answer
    that names both. Every claim is grounded this request, so the turn
    ends accepted with no refusal -- the guard must not refuse a true
    statement, or it would refuse every good answer."""
    core = Core()
    out = runTurn(core, [
        LLMResponse(tool_calls=[
            {'name': 'plot_one',
             'args': {'uri': 'imas:hdf5', 'path': 'core.ion[0].temp'}}],
            content=''),
        LLMResponse(tool_calls=[
            {'name': 'generate_report',
             'args': {'scope': 'plot', 'figure_key': 'Plot1'}}],
            content=''),
        LLMResponse(content='Plot1 montre la pression; le rapport est dans '
                            'plot-report.html, 3 courbes.',
                    tool_calls=None, finish_reason='stop'),
    ], 'trace la pression et génère le rapport')
    assert out['finished'] == [None]
    assert 'REFUSAL' not in ' '.join(out['lines'])
    assert core.list_windows() and core.written


def test_a_closed_figure_mentioned_stands(qapp):
    """The close of a real figure is not a fabrication: the model closes
    Plot2 (the user asked for it, so the destructive gate lets it) and
    reports it. Plot2 is in the ground set the loop tracked, so the
    mention stands -- the guard must not refuse an honest close."""
    core = Core()
    core._open = {'Plot1', 'Plot2'}
    out = runTurn(core, [
        LLMResponse(tool_calls=[
            {'name': 'close_window', 'args': {'key': 'Plot2'}}],
            content=''),
        LLMResponse(content='Plot2 est fermée, Plot1 reste ouverte.',
                    tool_calls=None, finish_reason='stop'),
    ], 'ferme Plot2')
    assert out['finished'] == [None]
    assert 'REFUSAL' not in ' '.join(out['lines'])
    assert 'Plot2' not in {w['key'] for w in core.list_windows()}


def test_a_twice_fabricated_artifact_is_refused(qapp):
    """A fabrication the re-anchor does not cure is refused by name, not
    carried: the first invented key earns the re-anchor, a second one of
    the same shape is the final refusal, and the turn ends with a REFUSAL
    carrying the reason -- never a fabrication the user reads as fact."""
    out = runTurn(Core(), [
        LLMResponse(content='Plot5 shows a curve, value 10.',
                    tool_calls=None, finish_reason='stop'),
        LLMResponse(content='Plot6 shows a curve, value 20.',
                    tool_calls=None, finish_reason='stop'),
    ], 'trace la pression')
    assert out['finished'][0] is not None
    assert 'Plot6' in out['finished'][0], \
        'the refusal must name the key that still stands as fact'
    assert 'REFUSAL' in ' '.join(out['lines'])


# ------------------------------------------------------------ the detectors

def test_reportClaimed_only_positive_unnegated():
    """A ``.html`` path, or the noun with a done word, is the claim; a
    negation in the same clause is the honest self-correction. Both must
    be told apart, or the guard refuses the model's own correction or
    passes a fabrication through."""
    assert reportClaimed('the report is written to rapport.html') is True
    assert reportClaimed('le rapport est généré dans x.html') is True
    assert (reportClaimed(
        "la pression n'a jamais été tracée, "
        "le rapport n'a jamais été écrit") is False)
    assert reportClaimed('I did not write a report') is False
    assert reportClaimed('there is no report') is False
    assert reportClaimed('the flux loop is stable') is False


def test_fabricatedFigureKeys_only_ungrounded_with_content():
    """A held key is never flagged; an invented key is flagged only
    when presented with a content word and not negated; a key the loop
    closed is in the ground set and stands. The user's own two-invented
    keys beside two real ones, held, must come back flagged."""
    held = {'Plot1', 'Plot2'}
    assert fabricatedFigureKeys('Plot1 shows a curve', held, set()) == set()
    assert fabricatedFigureKeys('Plot3 shows a curve', held, set()) \
        == {'Plot3'}
    assert fabricatedFigureKeys('Plot3 does not exist', held, set()) \
        == set()
    assert fabricatedFigureKeys('Plot5 has no content word here',
                                held, set()) == set()
    # the close of a real figure is in the ground set, not an invention
    assert fabricatedFigureKeys('Plot2 was closed', {'Plot1'},
                                {'Plot2'}) == set()
    # a fresh session has no held key to scan against, but the known
    # kinds still name the candidate
    assert fabricatedFigureKeys('Plot3 shows a curve', set(), set()) \
        == {'Plot3'}
    assert fabricatedFigureKeys('Plot3 is not real', set(), set()) \
        == set()
    # the user's exact pair, beside the two real figures the case holds
    assert fabricatedFigureKeys(
        'Plot1 et Plot2 sont tracés; Plot3 et Plot4 montrent des '
        'valeur de 1.2 W.', held, set()) == {'Plot3', 'Plot4'}
