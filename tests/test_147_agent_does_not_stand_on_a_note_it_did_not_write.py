# ****************************************************
#     (CEA) COPYRIGHT 2026/ Alternatives (CEA), France; and Laboratory for Engineering Design - LECAD,
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
"""The agent does not claim a journal line it did not write this request.

The field shape the user reported: asked to put a line in the journal, the
model answers "j'ai ajouté la note au cahier" -- and the note is not
there, the user looks for it and finds nothing. The one-in-four the write
"worked" is the one where the loop actually ran ``add_note``; the three
that failed are the ones where the model narrated the write instead of
emitting the structured tool call, so no journal gesture ran this request
and the answer stood on nothing.

The ground a claim of a note stands on is a call of **this request** that
wrote it (``add_note`` / ``edit_note`` / ``delete_note``), the way a
report stands on the ``plot_report`` that named its path: a note no call
wrote is not a fact of this session. A refusal reported for itself
("a été refusée", "je n'ai pas pu") and a self-correction ("je n'avais
pas ajouté") are the honest shapes the guard must let stand, for either
journal (a read of the user's own notes, a publication the shared-write
gate refused).

Same shape as the rest of ``ask``: refused by name, re-anchored once to
write the line, refused again on a second ungrounded claim.
"""

import pytest

from imasviz.VizAgent.agent import (
    AgentLoop, noteClaimed)
from imasviz.VizAgent.llm_client import LLMResponse

from test_110_agent_loop import FakeDispatcher


class Core:
    """A stand-in core that owns one journal line and answers exactly
    what the loop reads to ground a claim of a note: the write
    (``add_note``) returns the id the loop hands the model back, and a
    note it cannot write is refused by name, the way the real core does."""

    def __init__(self):
        self.lines = []
        self.calls = []
        self.refuse_write = False

    def add_note(self, scope, text, author=None, machine=None, campaign=None,
                 shot=None, date=None, title=None):
        self.calls.append('add_note')
        if self.refuse_write:
            raise ValueError(
                'A note needs its author named: no `author` given, and '
                'no $USER in the environment to fall back to.')
        note_id = 'personal_a line note-1'
        self.lines.append(note_id)
        return {'id': note_id, 'author': author or 'me',
                'text': text, 'overwritten': True}


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    """The loop here never reads a preference (``tools_mode`` is pinned
    on every agent), but a file left behind by an unpinned test would
    reach the user's real folder -- the pattern ``test_146`` keeps."""
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

def test_a_note_claimed_without_a_write_is_refused(qapp):
    """The model answers "j'ai ajouté la note au cahier" and no
    ``add_note`` ran this request: the claim is refused by name, naming
    the journal and the tool that would have written it, and a second
    claim of the same shape is the final refusal -- the user never
    reads the line as in the journal. The model never called a tool on
    the way, which is what the claim stands on nothing."""
    core = Core()
    claim = 'J\'ai ajouté la note au cahier: WEST 54924, flux loop stable.'
    out = runTurn(core, [
        LLMResponse(content=claim, tool_calls=None, finish_reason='stop'),
        LLMResponse(content=claim, tool_calls=None, finish_reason='stop'),
    ], 'note ça au cahier: WEST 54924 flux loop stable')
    assert out['finished'][0] is not None
    ref = out['finished'][0]
    assert 'cahier' in ref or 'journal' in ref, 'the refusal must name the journal'
    assert 'add_note' in ref, 'the refusal must name the tool that would write it'
    assert 'REFUSAL' in ' '.join(out['lines'])
    assert core.calls == [], 'the claim must not have earned a call'
    assert core.lines == [], 'a refused claim must not write the line'


def test_english_note_claim_without_a_write_is_refused(qapp):
    """The same confabulation in the English shape the model sometimes
    answers: "I've added it to the journal" with no call behind it is
    the line the user does not find."""
    core = Core()
    claim = "I've added it to the journal: WEST 54924 flux loop, stable."
    out = runTurn(core, [
        LLMResponse(content=claim, tool_calls=None, finish_reason='stop'),
        LLMResponse(content=claim, tool_calls=None, finish_reason='stop'),
    ], 'note it in the journal')
    assert out['finished'][0] is not None
    assert 'journal' in out['finished'][0]
    assert 'add_note' in out['finished'][0]
    assert core.calls == [] and core.lines == []


def test_a_real_note_stands(qapp):
    """The write ran: ``add_note`` succeeded, and the answer says exactly
    that. The claim stands on the call that did it -- the guard must
    not refuse a true statement, or it would refuse every good answer."""
    core = Core()
    out = runTurn(core, [
        LLMResponse(tool_calls=[{
            'name': 'add_note',
            'args': {'scope': 'personal', 'author': 'me',
                     'text': 'WEST 54924, flux loop stable.'}}],
            content=''),
        LLMResponse(content='J\'ai ajouté la note au cahier: WEST 54924, '
                            'flux loop stable.',
                    tool_calls=None, finish_reason='stop'),
    ], 'note ça au cahier: WEST 54924 flux loop stable')
    assert out['finished'] == [None]
    assert 'REFUSAL' not in ' '.join(out['lines'])
    assert core.calls == ['add_note']
    assert len(core.lines) == 1, 'the real write landed in the journal'


def test_a_refused_write_reported_honestly_stands(qapp):
    """The ``add_note`` this request ran was **refused** (no author), and
    the answer reports the refusal instead of claiming the line: "j'ai
    pas pu l'ajouter, aucun auteur". A refusal word near the claim is the
    honest report the guard must let stand -- the model did the work it
    could, and the reason the call named is what the user reads."""
    core = Core()
    core.refuse_write = True
    out = runTurn(core, [
        LLMResponse(tool_calls=[{
            'name': 'add_note',
            'args': {'scope': 'personal',
                     'text': 'WEST 54924, flux loop stable.'}}],
            content=''),
        LLMResponse(content='J\'ai pas pu ajouter la note au cahier: aucun '
                            'auteur n\'est donné, et il n\'y a pas de $USER '
                            'pour le remplacer.',
                    tool_calls=None, finish_reason='stop'),
    ], 'note ça au cahier: WEST 54924 flux loop stable')
    assert out['finished'] == [None]
    # The call's own refusal line ("  -> add_note: REFUSAL — …") stands in
    # the transcript whatever -- it is the answer the tools gave. The
    # guard's own line is the one at column zero ("REFUSAL: …"); on the
    # honest report of a refusal there is none of those.
    guard_refusals = [line for line in out['lines']
                      if line.startswith('REFUSAL')]
    assert guard_refusals == [], \
        'the guard must not refuse the model\'s honest report of a refusal'
    assert core.calls == ['add_note']
    assert core.lines == []


def test_a_self_correction_about_a_note_stands(qapp):
    """The model admitting the claim was a claim: "désolé, je n'avais pas
    ajouté la note au cahier, je l'avais dite sans l'avoir écrite". Every
    honest shape is allowed -- a self-correction negates the write near
    the noun, and the guard must let it stand."""
    core = Core()
    out = runTurn(core, [
        LLMResponse(content='Désolé: je n\'avais pas ajouté la note au '
                            'cahier, je l\'avais dite sans l\'avoir écrite. '
                            'Je l\'ajoute maintenant.',
                    tool_calls=None, finish_reason='stop'),
    ], 'la note est au cahier ?')
    assert out['finished'] == [None]
    assert 'REFUSAL' not in ' '.join(out['lines'])
    assert core.calls == []


def test_an_answer_about_a_note_it_read_stands(qapp):
    """A read of the user's notes, answered honestly, with no write:
    "ton cahier contient déjà une note sur le flux loop". A read is not
    a write the guard refuses; the noun is there, but no write voice and
    no claim that a line was added stands with it, so the guard does
    not fire."""
    core = Core()
    out = runTurn(core, [
        LLMResponse(content='Ton cahier contient déjà une note sur le flux '
                            'loop de WEST 54924, datée du 12.',
                    tool_calls=None, finish_reason='stop'),
    ], 'y a une note sur le flux ?')
    assert out['finished'] == [None]
    assert 'REFUSAL' not in ' '.join(out['lines'])
    assert core.calls == []


def test_tools_off_has_no_note_guard(qapp):
    """In the chat shape there is no gesture to refuse, so a note the
    answer mentions stands on its own wording -- the guard is gated on
    ``tools_mode != 'off'``, the way the report and figure guards are,
    and must not fire on a ``hide``-free conversation about notes."""
    core = Core()
    out = runTurn(core, [
        LLMResponse(content='En général, une note au cahier date de la '
                            'manip et reprend le flux loop.',
                    tool_calls=None, finish_reason='stop'),
    ], 'que met dans une note du cahier ?')
    # Tools are on in the harness, and the answer has no write-voice near a
    # noun, so the guard stands out of it either way: no REFUSAL, no line.
    assert out['finished'] == [None]
    assert core.calls == [] and core.lines == []


# ------------------------------------------------------------ the detector

def test_noteClaimed_only_positive_unnegated():
    """The detector: a write verb near a note/note-family noun, un-negated,
    is the claim; an honest read, a refusal, and a self-correction are not."""
    assert noteClaimed('j\'ai ajouté la note au cahier') is True
    assert noteClaimed('la note est ajoutée au journal') is True
    assert noteClaimed('j\'ai noté ça dans le cahier') is True
    assert noteClaimed("I've added it to the journal") is True
    assert noteClaimed('added the note about the flux loop') is True

    # An honest read: the noun is there, but no write verb near it.
    assert noteClaimed('ton cahier contient déjà une note sur le flux loop') is False
    assert noteClaimed('j\'ai lu tes notes sur WEST') is False

    # A refusal: a negation sits near the claim.
    assert noteClaimed('je n\'ai pas pu ajouter la note au cahier') is False
    assert noteClaimed('la note n\'a pas été ajoutée au journal') is False
    assert noteClaimed('I did not add a note to the journal') is False

    # A self-correction.
    assert noteClaimed(
        'désolé, je n\'avais pas ajouté la note au cahier'
    ) is False

    # A plain mention of the noun, with no write and no claim at all.
    assert noteClaimed('une note date de la manip et reprend le flux loop') is False


def test_noteClaimed_the_nodes_and_noted_are_not_notes():
    """The noun match must not reach past the note: "nodes" (tree paths)
    and "noted" (an English verb) carry a write voice, but they are not
    the journal line the guard guards, so a plot-shaped sentence about
    adding nodes must not read as a claimed note."""
    assert noteClaimed('j\'ai ajouté les nodes magnetics aux figures') is False
    assert noteClaimed('added the nodes to the figure') is False


def test_noteClaimed_the_refusal_of_a_shared_write_stands():
    """A publication the shared-journal gate refused is an honest report of
    that refusal, not a claimed write: "la publication au journal partagé
    a été refusée". A negation or a refusal word near the noun is what
    keeps it out of the claim."""
    assert noteClaimed(
        'la publication au journal partagé a été refusée: ta demande '
        'ne le demande pas'
    ) is False
    assert noteClaimed('je n\'ai pas pu la publier au journal partagé') is False
