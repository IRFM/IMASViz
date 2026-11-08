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
"""The agent is refused when it recites an IDS inventory from memory.

A small local model, asked what a case holds before calling any case tool,
answers "from memory": a table of a dozen plausible-sounding IDS names, most
of them not in the data dictionary at all. That is a confabulation, and it is
refused by name the way every other refusal is, instead of standing as a
grounded answer. This file pins the guard:

* a final answer shaped like an inventory -- a markdown table of a few
  rows, or three or more distinct snake_case names standing on their own
  (a name inside a path or a file does not stand, and neither does the
  loop's own tool vocabulary) -- with no case tool called this request
  is refused, and ``askFinished`` carries the reason, naming the calls
  that would ground the list it could be;
* the same inventory is let stand once a case tool has been called, so a
  real "list_case_idss then answer" flow is not second-guessed;
* a plain conversational answer with no list shape stands -- as does an
  answer that repeats one name through its paths, or that names the
  loop's tools and a session it was handed, because spelling and quoting
  are not listing.

The core method that grounds such answers (``list_case_idss``) is pinned
against the real case in ``tests/test_100_mcp_core_offscreen.py``.
"""

import pytest

from imasviz.VizAgent.agent import AgentLoop
from imasviz.VizAgent.llm_client import LLMResponse


class FakeLLMClient:
    """A scripted LLM: the next response in its queue, in order."""
    def __init__(self, responses):
        self.responses = list(responses)

    def chat(self, messages, tools=None, **kwargs):
        if not self.responses:
            raise AssertionError('FakeLLMClient: no more scripted responses')
        return self.responses.pop(0)


class FakeCore:
    """A stand-in core: a fixed, small inventory for the list tools."""
    _HELD = [
        {'name': 'equilibrium', 'occurrences': [0, 1, 2, 3]},
        {'name': 'magnetics', 'occurrences': [0]},
    ]
    def list_idss(self, uri):
        return self._HELD
    def list_case_idss(self, uri):
        return self._HELD
    def list_cases(self):
        return [{'uri': 'imas:hdf5?path=/fake', 'dd_version': '3.35.0'}]


class FakeDispatcher:
    """A synchronous dispatcher: it runs the function on the calling thread."""
    def call(self, function, timeout=300.0):
        return function()


CONFABULATED = """**IDS disponibles** (13) :
| IDS | Occurrences |
|---|---|
| bpol_probe | 1 |
| equilibrium | 1 |
| equilibrium_fit | 1 |
| equilibrium_reconstruction | 1 |
| equilibrium_time | 1 |
| magnetics | 1 |
| plasma_boundary | 1 |
| plasma_current | 1 |
| plasma_disruption | 1 |
| plasma_electron | 1 |
| plasma_operating_point | 1 |
| plasma_performance | 1 |
| plasma_wall | 1 |"""

# The two answers the guard wrongly refused in the field (one refusal per
# answer, each printed twice on the web page). What each one does that
# the inventories above do not: repeat one name through its paths, or mix
# one path segment with one session name and one file name. Both must
# stand.

PLOT3_ANSWER = """Le dernier plot est **Plot3**, qui contient les 17 signaux `flux_loop[i].flux.data` (i = 0 à 16) de l'occurrence 0 de l'IDS magnetics.

**Détails** :
- **Figure** : Plot3
- **Traces** : 17 courbes (une par boucle, en Wb)
- **Sélection** : `magnetics.flux_loop[0].flux.data` … `magnetics.flux_loop[16].flux.data`

La figure est visible à l'écran. Que veux-tu faire ensuite ?"""

LOG_ANSWER = """Voici le log de la session (dernières 50 lignes) :

```
[INFO]  Session from_web restaurée
[INFO]  Cas ouvert: imas:hdf5?path=/afs/eufus.eu/user/g/g2lfleur/public/imasdb/west/3/54924/0
[INFO]  Dictionnaire de données: 3.35.0
[INFO]  IDS magnetics[0] chargé: 6058 signaux
[INFO]  IDS magnetics[1] chargé: 8039 signaux
[INFO]  Sélection: 17 signaux flux_loop[i].flux.data (i=0..16)
[INFO]  Figure Plot1 créée
[INFO]  Figure Plot2 créée
[INFO]  Figure Plot3 créée
[INFO]  Rapport HTML généré: ~/.imasviz/reports/rapport_flux_loop_10.html
[INFO]  Session fermée
[INFO]  Session from_web restaurée
```

**Résumé** :
- **Cas** : WEST 54924 (dictionnaire 3.35.0)
- **IDS** : magnetics (occurrences 0 et 1)
- **Sélection** : 17 signaux flux_loop
- **Figures** : Plot1, Plot2, Plot3
- **Rapport** : rapport_flux_loop_10.html généré

Aucune erreur ni refus dans le log. Que veux-tu faire ensuite ?"""


@pytest.fixture
def agent_kwargs(qapp):
    """The common kwargs for building an AgentLoop without the GUI."""
    return {'main_window': None, 'api': None}


def _ask(agent, prompt):
    """Run one ask and return (the transcript joined, the askFinished reason)."""
    lines, errors = [], []
    agent.transcriptLine.connect(lines.append)
    agent.askFinished.connect(errors.append)
    agent.ask(prompt)
    return ' '.join(lines), errors


def test_an_unfounded_inventory_is_refused(qapp, agent_kwargs):
    """The farfelus 13-name table, no case tool called: the refusal is named
    and points at the call that would ground the list."""
    llm = FakeLLMClient([
        LLMResponse(content=CONFABULATED, tool_calls=None,
                    finish_reason='stop'),
    ])
    agent = AgentLoop(core=FakeCore(), llm=llm,
                      dispatcher=FakeDispatcher(), **agent_kwargs)
    joined, errors = _ask(agent, 'what ids are in this case?')
    assert errors and errors[0] is not None, 'an unfounded list must be refused'
    assert 'REFUSAL' in joined
    assert 'list_case_idss' in errors[0], 'the refusal names the grounding tool'
    assert 'bpol_probe' not in errors[0], 'the refusal is not the list itself'


def test_a_list_of_identifiers_is_refused_without_a_tool(qapp, agent_kwargs):
    """Not a table, but three-plus snake_case names with no tool: refused."""
    answer = ('this case holds core_profiles, pulse_schedule, magnetics, and '
              'equilibrium_time.')
    llm = FakeLLMClient([
        LLMResponse(content=answer, tool_calls=None, finish_reason='stop'),
    ])
    agent = AgentLoop(core=FakeCore(), llm=llm,
                      dispatcher=FakeDispatcher(), **agent_kwargs)
    joined, errors = _ask(agent, 'list the ids')
    assert errors and errors[0] is not None
    assert 'REFUSAL' in joined


def test_an_inventory_stands_after_a_case_tool(qapp, agent_kwargs):
    """A case tool called first: the same inventory is not second-guessed, so
    a real "list_case_idss then answer" flow reaches the user."""
    llm = FakeLLMClient([
        LLMResponse(content='', tool_calls=[
            {'name': 'list_case_idss', 'args': {'uri': 'x'}}],
            finish_reason='tool_calls'),
        LLMResponse(content=CONFABULATED, tool_calls=None,
                    finish_reason='stop'),
    ])
    agent = AgentLoop(core=FakeCore(), llm=llm,
                      dispatcher=FakeDispatcher(), **agent_kwargs)
    joined, errors = _ask(agent, 'list the ids in the case')
    assert errors == [None], 'a tool-grounded answer must stand'
    assert 'list_case_idss' in joined, 'the grounding call showed in the log'


def test_a_conversational_answer_stands(qapp, agent_kwargs):
    """No list shape and no tool: an ordinary answer is not mistaken for a
    recited inventory."""
    llm = FakeLLMClient([
        LLMResponse(content='Ok, the case is open.', tool_calls=None,
                    finish_reason='stop'),
    ])
    agent = AgentLoop(core=FakeCore(), llm=llm,
                      dispatcher=FakeDispatcher(), **agent_kwargs)
    joined, errors = _ask(agent, 'is the case open?')
    assert errors == [None]
    assert 'REFUSAL' not in joined


def test_a_repeated_name_in_paths_stands(qapp, agent_kwargs):
    """The answer that was refused in the field: one name, ``flux_loop``,
    repeated through the paths that spell it. Repetition is not an
    inventory, and the guard must not count occurrences of one name."""
    llm = FakeLLMClient([
        LLMResponse(content=PLOT3_ANSWER, tool_calls=None,
                    finish_reason='stop'),
    ])
    agent = AgentLoop(core=FakeCore(), llm=llm,
                      dispatcher=FakeDispatcher(), **agent_kwargs)
    joined, errors = _ask(agent, "le dernier plot, c'est lequel ?")
    assert errors == [None], 'a repeated name in its paths must stand'
    assert 'REFUSAL' not in joined


def test_a_log_answer_with_mixed_names_stands(qapp, agent_kwargs):
    """The other answer that was refused in the field: one session name
    (``from_web``), one path segment (``flux_loop``) and one file name
    (``rapport_flux_loop_10.html``), mixed across registres. That is not a
    list of three names; it is a log that was quoted."""
    llm = FakeLLMClient([
        LLMResponse(content=LOG_ANSWER, tool_calls=None,
                    finish_reason='stop'),
    ])
    agent = AgentLoop(core=FakeCore(), llm=llm,
                      dispatcher=FakeDispatcher(), **agent_kwargs)
    joined, errors = _ask(agent, 'montre-moi le log de la session')
    assert errors == [None], 'a quoted log with mixed names must stand'
    assert 'REFUSAL' not in joined


def test_tool_name_mentions_stand(qapp, agent_kwargs):
    """An answer that quotes the loop's own tools to point the user at the
    gesture is not a recited inventory: the tool names are the agent's
    vocabulary, and the one session name it carries does not list."""
    answer = ('Tu peux restaurer cette session plus tard avec '
              '`restore_session(name="from_web")`; `save_session` en '
              'écrit une nouvelle et `list_sessions` répond celles qui '
              'sont déjà là.')
    llm = FakeLLMClient([
        LLMResponse(content=answer, tool_calls=None, finish_reason='stop'),
    ])
    agent = AgentLoop(core=FakeCore(), llm=llm,
                      dispatcher=FakeDispatcher(), **agent_kwargs)
    joined, errors = _ask(agent, 'est-ce que la session est bien sauvée ?')
    assert errors == [None], 'tool names do not count as a recited list'
    assert 'REFUSAL' not in joined


def test_an_inventory_named_by_plain_words_is_still_refused(qapp, agent_kwargs):
    """The shape that must keep falling: three or more distinct names that
    stand on their own -- even when spelled out in ordinary prose -- and
    no tool called this request."""
    answer = ('this case holds core_profiles, pulse_schedule, wall and '
              'equilibrium_time.')
    llm = FakeLLMClient([
        LLMResponse(content=answer, tool_calls=None, finish_reason='stop'),
    ])
    agent = AgentLoop(core=FakeCore(), llm=llm,
                      dispatcher=FakeDispatcher(), **agent_kwargs)
    joined, errors = _ask(agent, 'list the ids')
    assert errors and errors[0] is not None, (
        'a bare list of distinct names must still be refused')


def test_the_refusal_points_at_the_grounding_tools(qapp, agent_kwargs):
    """The refusal names the call that grounds each list it could be:
    the case's IDS and the saved sessions, not the case alone -- the old
    words sent the model to list_case_idss for what may be a list of
    sessions, a repair that answers the other question."""
    llm = FakeLLMClient([
        LLMResponse(content=CONFABULATED, tool_calls=None,
                    finish_reason='stop'),
    ])
    agent = AgentLoop(core=FakeCore(), llm=llm,
                      dispatcher=FakeDispatcher(), **agent_kwargs)
    joined, errors = _ask(agent, 'what ids are in this case?')
    assert errors and errors[0] is not None
    assert 'list_case_idss' in errors[0]
    assert 'list_idss' in errors[0]
    assert 'list_sessions' in errors[0]
