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
"""The agent does not claim work on a figure that did not run this request.

The field shape the existing guards do not cross-check: the figure
**stands** (Plot1 is open, the fabricated-artifact guard therefore
passes it), yet the answer says a change landed on it that no call of
this request performed -- "j'ai ajouté la courbe de température sur
Plot1" with no ``plot_one`` called, or "la courbe est multipliée par 3"
after the ``scale_curve`` the loop ran was **refused** (empty curve,
values crossing zero, whatever the named reason is). The loop then
hands the turn back to the user, the user answers "la courbe n'est pas
là", and the model apologizes -- the claim and the apology in two
turns instead of one honest answer.

The ground a claim stands on is a call of **this request**: a write to
the figure (a draw into it, a curve transform, an axis move) or a read
back of it (``curve_stats``, ``export_curve``) -- the state of a figure
is what those answer, not what was said. A negation or a refusal word
near the claim ("refusée", "n'a pas été ajouté", "impossible") is the
honest report the guard must let stand, on whatever key; a description
("Plot1 montre la pression") is not an assertion of work, and it stays
out of this guard's reach the way it is out of the fabricated one's
until a content word says otherwise.

Same shape as the rest of ``ask``: refused by name, re-anchored once to
do the work or read it, refused again on a second ungrounded claim.
"""

import pytest

from imasviz.VizAgent.agent import (
    AgentLoop, _groundedFigureKeys, unperformedWorkOn)
from imasviz.VizAgent.llm_client import LLMResponse

from test_110_agent_loop import FakeDispatcher


class Core:
    """A stand-in core that owns its figure registry, answering exactly
    what the loop reads to ground a claim of work: the open figure keys
    (``list_windows``), the key a draw or a mutation worked on (the
    ``figure`` / ``window`` field of the answer), and the state a read
    reports (``curve_stats``). A tool that cannot run is refused by
    name, the way the real core does."""

    def __init__(self):
        self._open = set()
        self.calls = []
        self.refuse_scale = False

    def list_windows(self):
        return [{'kind': 'Plot', 'label': k, 'key': k,
                 'visible': True, 'cases': []} for k in sorted(self._open)]

    def run_plugin(self, uri=None, plugin=None, entry=None, **kwargs):
        """One entry of a plugin, drawing a window of its own.

        It answers `drawn` with the windows the entry registered and
        `windows` with the whole screen: the first is what this request
        drew, the second is what stands now. The guard reads the first --
        a claim grounded on every open window would ground anything.
        """
        self.calls.append('run_plugin')
        number = max([int(k[len('EquiSurfaces:'):])
                      for k in self._open
                      if k.startswith('EquiSurfaces:')] or [0]) + 1
        key = 'EquiSurfaces:%d' % number
        self._open.add(key)
        return {'ran': {'plugin': plugin, 'entry': entry},
                'drawn': [key],
                'windows': self.list_windows()}

    def plot_one(self, uri=None, path=None, into_figure_key=None, **kwargs):
        self.calls.append('plot_one')
        if into_figure_key:
            if into_figure_key not in self._open:
                raise ValueError(
                    'No window holds the key "%s" any more -- '
                    'list_windows names what is open.' % into_figure_key)
            return {'figure': into_figure_key, 'curves': ['pressure', 'temperature']}
        number = max([int(k[4:]) for k in self._open
                      if k.startswith('Plot')] or [0]) + 1
        key = 'Plot%d' % number
        self._open.add(key)
        return {'figure': key, 'curves': [path]}

    def scale_curve(self, figure_key, factor, curve=None, **kwargs):
        self.calls.append('scale_curve')
        if figure_key not in self._open:
            raise ValueError(
                'No window holds the key "%s" any more' % figure_key)
        if self.refuse_scale:
            raise ValueError(
                'The 1 curve(s) of "%s" hold no number to multiply, every '
                'one being empty as it stands.' % figure_key)
        return {'window': figure_key, 'factor': float(factor),
                'curves': ['pressure']}

    def curve_stats(self, figure_key, curve=None, **kwargs):
        self.calls.append('curve_stats')
        if figure_key not in self._open:
            raise ValueError(
                'No window holds the key "%s" any more' % figure_key)
        return {'window': figure_key, 'count': 1,
                'curves': [{'name': 'pressure', 'n': 100}]}


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    """The loop here never reads a preference (``tools_mode`` is pinned
    on every agent), but a file left behind by an unpinned test would
    reach the user's real folder -- the pattern ``test_143`` keeps."""
    monkeypatch.setenv('HOME', str(tmp_path))


def runTurn(core, responses, prompt, max_turns=12):
    """One scripted ask on a ``hide``-shape loop, with the transcript
    and the finish of the loop captured. The stand-in LLM pops its
    responses in order and ignores the re-anchors the loop hands it --
    the way a model that re-answers in the same shape shows up here;
    the tests that end accepted hand it an honest answer instead."""
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

def test_an_add_claimed_on_a_held_figure_without_a_call_is_refused(qapp):
    """Plot1 stands, the answer says a curve was added into it, and no
    call ran: the claim is refused by name, naming the figure, and a
    second claim of the same shape is the final refusal -- the user
    never reads the add as a fact. The model never called a tool on the
    way, which is what the claim stands on nothing."""
    core = Core()
    core._open = {'Plot1'}
    claim = 'J\'ai ajouté la courbe de température sur Plot1.'
    out = runTurn(core, [
        LLMResponse(content=claim, tool_calls=None, finish_reason='stop'),
        LLMResponse(content=claim, tool_calls=None, finish_reason='stop'),
    ], 'ajoute la température sur Plot1')
    assert out['finished'][0] is not None
    assert 'Plot1' in out['finished'][0], 'the refusal must name the figure'
    assert 'REFUSAL' in ' '.join(out['lines'])
    assert core.calls == [], 'the claim must not have earned a call'


def test_a_real_add_on_a_held_figure_stands(qapp):
    """The work ran: a drawing into Plot1 succeeded, and the answer
    says exactly that. The claim stands on the call that did it -- the
    guard must not refuse a true statement, or it would refuse every
    good answer. The call is spelled as it is offered (``plot`` with its
    "single" mode); what the stand-in records is the gesture that ran."""
    core = Core()
    core._open = {'Plot1'}
    out = runTurn(core, [
        LLMResponse(tool_calls=[{
            'name': 'plot',
            'args': {'mode': 'single', 'uri': 'imas:hdf5',
                     'path': 'core.temperature',
                     'into_figure_key': 'Plot1'}}],
            content=''),
        LLMResponse(content='J\'ai ajouté la courbe de température sur '
                            'Plot1.',
                    tool_calls=None, finish_reason='stop'),
    ], 'ajoute la température sur Plot1')
    assert out['finished'] == [None]
    assert 'REFUSAL' not in ' '.join(out['lines'])
    assert core.calls == ['plot_one']


def test_a_refused_transform_claimed_done_is_reanchored_then_reported(qapp):
    """The ``scale_curve`` this request ran was **refused**, and the
    first answer says the transform is on. The claim is refused by
    name; the honest report of the refusal -- the reason the call
    answered -- then stands. The apology is not two turns after the
    claim, it is the claim's own refusal."""
    core = Core()
    core._open = {'Plot1'}
    core.refuse_scale = True
    out = runTurn(core, [
        LLMResponse(tool_calls=[
            {'name': 'scale_curve', 'args': {'figure_key': 'Plot1',
                                             'factor': 3}}],
            content=''),
        LLMResponse(content='La courbe de Plot1 est maintenant '
                            'multipliée par 3.',
                    tool_calls=None, finish_reason='stop'),
        LLMResponse(content='La multiplication a été refusée: la courbe '
                            'de Plot1 ne tient aucune valeur -- '
                            'désolé pour la confusion.',
                    tool_calls=None, finish_reason='stop'),
    ], 'multiplie la courbe de Plot1 par 3')
    assert out['finished'] == [None]
    # The call's own refusal line ("← scale_curve: REFUSAL — …") stands in
    # the transcript whatever -- it is the answer the tools gave -- what
    # is counted here is the guard's line, the one that led the model back
    # from claiming the transform.
    refusals = [line for line in out['lines']
                if line.startswith('REFUSAL')]
    assert len(refusals) == 1, 'one re-anchor, not a fight'
    assert 'Plot1' in refusals[0], 'the refusal must name the figure'


def test_a_real_transform_stands(qapp):
    """The transform ran and the answer says it, in the shape the core
    answered (the same window, the same factor). Grounded this request
    -- no REFUSAL."""
    core = Core()
    core._open = {'Plot1'}
    out = runTurn(core, [
        LLMResponse(tool_calls=[
            {'name': 'scale_curve', 'args': {'figure_key': 'Plot1',
                                             'factor': 3}}],
            content=''),
        LLMResponse(content='J\'ai multiplié la courbe de Plot1 par 3.',
                    tool_calls=None, finish_reason='stop'),
    ], 'multiplie la courbe de Plot1 par 3')
    assert out['finished'] == [None]
    assert 'REFUSAL' not in ' '.join(out['lines'])
    assert core.calls == ['scale_curve']


def test_a_state_claim_verified_by_a_read_stands(qapp):
    """Work of an earlier request (the curve is genuinely on Plot1),
    restated after a read back this request: ``curve_stats`` answered
    for Plot1, so the state claim stands on the read. That is the shape
    of the honest "elle est toujours là", with the evidence in the
    transcript."""
    core = Core()
    core._open = {'Plot1'}
    out = runTurn(core, [
        LLMResponse(tool_calls=[
            {'name': 'curve_stats', 'args': {'figure_key': 'Plot1'}}],
            content=''),
        LLMResponse(content='Plot1 est là: la pression y est tracée, '
                            '100 points.',
                    tool_calls=None, finish_reason='stop'),
    ], 'la pression est toujours sur Plot1 ?')
    assert out['finished'] == [None]
    assert 'REFUSAL' not in ' '.join(out['lines'])
    assert core.calls == ['curve_stats']


def test_a_report_of_a_refusal_with_no_work_word_stands(qapp):
    """The honest shape with no call at all: the user asked for a log
    axis, the answer reports why it cannot stand ("les valeurs
    croisent zéro") instead of claiming it. A refusal word near the
    claim is what lets it through -- the guard must not refuse the
    model's own honest report."""
    core = Core()
    core._open = {'Plot1'}
    out = runTurn(core, [
        LLMResponse(content='La mise en log de Plot1 a été refusée: des '
                            'valeurs croisent zéro, ce que log ne définit '
                            'pas.',
                    tool_calls=None, finish_reason='stop'),
    ], 'passe l\'axe en log')
    assert out['finished'] == [None]
    assert 'REFUSAL' not in ' '.join(out['lines'])
    assert core.calls == []


def test_a_self_correction_stands(qapp):
    """The model admitting the claim was a claim: "désolé, je n'avais
    pas ajouté la courbe, je l'ai dite sans l'avoir faite". Every
    honest shape is allowed -- this one negates the work near the key,
    on a figure the session holds."""
    core = Core()
    core._open = {'Plot1'}
    out = runTurn(core, [
        LLMResponse(content='Désolé: je n\'avais pas ajouté la courbe de '
                            'température sur Plot1, je l\'ai dite sans '
                            'l\'avoir faite.',
                    tool_calls=None, finish_reason='stop'),
    ], 'la température est sur Plot1 ?')
    assert out['finished'] == [None]
    assert 'REFUSAL' not in ' '.join(out['lines'])


def test_a_window_a_plugin_entry_drew_grounds_the_draw_claimed_on_it(qapp):
    """The user asked for the plugin, the entry ran, and the answer says the
    surfaces are traced in the window it opened. That is the truth of the
    turn, and until now it was refused: a plugin entry named no window it
    drew, so the guard had seen no work on `EquiSurfaces:1` -- and its
    re-anchor, "do the work: draw it", is what sent the model to
    `equilibrium_surfaces`. The second, identical window the user reported
    is that re-anchor arriving on the screen. The entry answers the keys it
    opened as `drawn`, and the claim stands on them."""
    core = Core()
    out = runTurn(core, [
        LLMResponse(tool_calls=[
            {'name': 'run_plugin',
             'args': {'uri': 'imas:hdf5?path=x',
                      'plugin': 'equilibriumsurfaces', 'entry': 0}}],
            content=''),
        LLMResponse(content='J\'ai tracé les surfaces de flux sur '
                            'EquiSurfaces:1.',
                    tool_calls=None, finish_reason='stop'),
    ], 'appelle le plugin equilibriumsurfaces')
    assert out['finished'] == [None]
    assert 'REFUSAL' not in ' '.join(out['lines'])
    assert core.calls == ['run_plugin'], \
        'the claim must not earn a second draw of the same window'


def test_a_plugin_entry_grounds_nothing_on_a_window_it_did_not_draw(qapp):
    """Non-vacuity of the answer above. `run_plugin` reports the whole
    screen as `windows` and only its own openings as `drawn`; reading the
    first would ground a claim on a figure that already stood. Plot1 stood
    before the entry ran, and a draw claimed on it has nothing behind it."""
    core = Core()
    core._open = {'Plot1'}
    claim = 'J\'ai tracé la pression sur Plot1.'
    out = runTurn(core, [
        LLMResponse(tool_calls=[
            {'name': 'run_plugin',
             'args': {'uri': 'imas:hdf5?path=x',
                      'plugin': 'equilibriumsurfaces', 'entry': 0}}],
            content=''),
        LLMResponse(content=claim, tool_calls=None, finish_reason='stop'),
        LLMResponse(content=claim, tool_calls=None, finish_reason='stop'),
    ], 'trace la pression sur Plot1')
    assert out['finished'][0] is not None
    assert 'Plot1' in out['finished'][0], 'the refusal names the figure'


# ------------------------------------------------------------ the detector

def test_unperformedWorkOn_a_claims_shape():
    """A change word near a key, un-negated, with no grounded call, is
    the flag; a grounded key, a negated claim, or a description without
    a change word is not."""
    assert unperformedWorkOn("j'ai ajouté la température sur Plot1",
                             set()) == {'Plot1'}
    assert unperformedWorkOn("j'ai ajouté la température sur Plot1",
                             {'Plot1'}) == set()
    assert unperformedWorkOn("l'ajout sur Plot1 a été refusé", set()) == set()
    assert unperformedWorkOn("Plot1 montre la pression", set()) == set()


def test_unperformedWorkOn_the_english_shapes():
    assert unperformedWorkOn('I added the temperature curve to Plot2',
                             set()) == {'Plot2'}
    assert unperformedWorkOn('I added the temperature curve to Plot2',
                             {'Plot2'}) == set()
    assert unperformedWorkOn('I did not add anything to Plot2',
                             set()) == set()
    assert unperformedWorkOn('I multiplied the curve of Plot3 by 10',
                             set()) == {'Plot3'}
    assert unperformedWorkOn('Plot3 shows the pressure', set()) == set()


def test_unperformedWorkOn_the_axis_shapes():
    """A log axis or a pinned range claimed the same way: a change
    word, a key, no grounded call."""
    assert unperformedWorkOn('l\'axe y de Plot1 est maintenant en log',
                             set()) == {'Plot1'}
    assert unperformedWorkOn('l\'axe y de Plot1 a été mis en log',
                             {'Plot1'}) == set()
    assert unperformedWorkOn('l\'axe y de Plot1 n\'a pas pu être mis en '
                             'log: les valeurs croisent zéro',
                             set()) == set()
    assert unperformedWorkOn('I set the y axis of Plot4 to log scale',
                             set()) == {'Plot4'}


def test_unperformedWorkOn_the_entry_answers_the_window_it_drew():
    """The reading of a plugin answer, both halves.

    `drawn` is what the entry registered, `windows` is every window of the
    session. Only the first grounds a claim: measuring on the real answer
    of `run_plugin`, the key it drew stands and a key that merely stands
    beside it is still an unperformed claim.
    """
    entry = {'ran': {'plugin': 'equilibriumsurfaces', 'entry': 0,
                     'ids': 'equilibrium', 'occurrence': 0, 'time': None},
             'drawn': ['EquiSurfaces:1'],
             'windows': [{'key': 'EquiSurfaces:1'}, {'key': 'Plot1'}]}
    ground = _groundedFigureKeys({'uri': 'imas:hdf5?path=x', 'plugin':
                                  'equilibriumsurfaces', 'entry': 0}, entry)
    assert ground == {'EquiSurfaces:1'}, ground
    assert unperformedWorkOn('j\'ai tracé les surfaces de flux sur '
                             'EquiSurfaces:1', ground) == set()
    assert unperformedWorkOn('j\'ai tracé la pression sur Plot1',
                             ground) == {'Plot1'}
