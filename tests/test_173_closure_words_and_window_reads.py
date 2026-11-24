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
"""The closure gate on whole words, and a window read that grounds a claim.

Two targeted fixes of the guard false positives the field run named:

* the French close verb of the destructive gate was the stem ``ferm``,
  a substring, so it matched inside other words the request could carry.
  The gate now opens on the close verbs as whole words only -- ``ferme``,
  ``fermer``, ``fermez`` -- and the rest of the gate (close, delete,
  nouvelle session, reset, …) stands as it was.

* ``list_windows`` was in neither ``_WORK_GESTURES`` nor ``_READ_GESTURES``
  (``curve_stats`` and ``export_curve`` only), and the window list it
  answers was not a shape ``_groundedFigureKeys`` could read. So an
  answer that named a truth the model had just read -- "Plot1 holds the
  pressure curve", after a ``list_windows`` that answered for it -- was
  refused as an unperformed work, while the same claim after a
  ``curve_stats`` read stood. The read now grounds the claim the way the
  other window reads do.

Pinned scripted, off the case, in the refusal order the loop answers
them.
"""

from imasviz.VizAgent.agent import (
    AgentLoop,
    _userAskedForAClosure,
)
from imasviz.VizAgent.llm_client import LLMResponse


class FakeDispatcher:
    """A synchronous dispatcher: it runs the function on the calling thread."""
    def call(self, function, timeout=300.0):
        return function()


class Core:
    """One standing figure: the read ``list_windows`` answers it, and
    the claim the loop polices is on it."""
    def list_windows(self):
        return [{'kind': 'Plot', 'label': 'Plot 1', 'key': 'Plot1',
                 'visible': True, 'cases': []}]

    def plot_one(self, uri=None, path=None, into_figure_key=None, **kwargs):
        return {'figure': into_figure_key or 'Plot1',
                'curves': ['pressure']}


# -------------------------------------------------------- the closure gate

def test_the_stem_inside_a_word_does_not_open_the_gate(qapp):
    """The old substring matched the stem inside other words the request
    could carry; a whole-word reading does not open the gate on them."""
    assert not _userAskedForAClosure('ouvre le fermoir de la vanne'), \
        'the stem matched inside "fermoir": the gate is a substring again'
    assert not _userAskedForAClosure('trace la pression du flux'), \
        'a request that names no close must not open the gate'


def test_the_close_verbs_open_the_gate(qapp):
    """The verbs the user gives to close a window, as whole words, are
    the ask the gate waits for."""
    for ask in ('ferme Plot2', 'fermer la figure', 'fermez la fenêtre'):
        assert _userAskedForAClosure(ask), \
            'the whole-word close verb %r no longer opens the gate' % ask


def test_the_rest_of_the_gate_stands(qapp):
    """The other words of the gate, in either language, are unchanged:
    the fix narrowed the French verb, not the rule."""
    for ask in ('close Plot1', 'delete the case', 'nouvelle session',
                'reset the session', 'recommence à zéro'):
        assert _userAskedForAClosure(ask), \
            'the gate word %r is gone' % ask


# ------------------------------------------------- the window read as ground

def runTurn(responses, prompt, max_turns=12):
    """One scripted ask on a ``hide``-shape loop, with the transcript
    and the finish of the loop captured. The stand-in LLM pops its
    responses in order and ignores the re-anchors the loop hands it."""
    class ScriptedLLM:
        def __init__(self, queue):
            self.responses = list(queue)

        def chat(self, messages, tools=None, **kwargs):
            if not self.responses:
                raise AssertionError('ScriptedLLM: no more scripted responses')
            return self.responses.pop(0)

    agent = AgentLoop(core=Core(), llm=ScriptedLLM(responses),
                      dispatcher=FakeDispatcher(),
                      main_window=None, api=None)
    agent.tools_mode = 'hide'
    lines = []
    agent.transcriptLine.connect(lines.append)
    errors = []
    agent.askFinished.connect(errors.append)
    agent.ask(prompt, max_turns=max_turns)
    return {'lines': lines, 'finished': errors}


def test_a_claim_grounded_on_the_list_windows_read_stands(qapp):
    """The model read the session's figures (``list_windows`` answered
    for Plot1), and the answer says the work is on that figure. The
    read grounds the claim the way ``curve_stats`` does: no REFUSAL,
    the answer stands. Before the fix, ``list_windows`` was in neither
    ``_WORK_GESTURES`` nor ``_READ_GESTURES`` and its window-list answer
    was not a shape ``_groundedFigureKeys`` could read, so the same true
    statement was refused as an unperformed work."""
    claim = 'J\'ai ajouté la courbe de pression sur Plot1.'
    out = runTurn([
        LLMResponse(tool_calls=[{'name': 'list_windows', 'args': {}}],
                    content=''),
        LLMResponse(content=claim, tool_calls=None, finish_reason='stop'),
    ], 'ajoute la pression sur Plot1')
    assert out['finished'] == [None], \
        'a claim the list_windows read answered for must stand, and it ' \
        'was refused: %r' % (out['finished'],)
    assert 'REFUSAL' not in ' '.join(out['lines']), \
        'the read that answered for the figure is not grounding the ' \
        'claim: %r' % out['lines']
