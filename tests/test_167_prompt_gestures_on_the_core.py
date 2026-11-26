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

"""The six prompt gestures on the core -- what every face actually calls.

The page has no route of its own for the catalogue: it posts
``/api/tool {name, args}``, ``AgentLoop._dispatch`` does
``getattr(self.core, name)``, and the answer it renders is the one
``McpGuiCore`` gives. The panel, the CLI and the agent's tools ask the same
six methods. So the rules that a user sees -- what the session answers for
free, which catalogue was missing, where a value came from, which holes are
still empty -- live here, and are pinned here once, on a core built with
``__new__`` and a stand-in ``api`` (the pattern ``test_116`` holds). No case
is opened: the case values come from the URI the view carries, which
``_readCaseFromUri`` reads off the string, so no Access Layer is asked.

What is pinned:

* the **context** -- one open case answers ``case``/``uri``/``shot``/``run``/
  ``database``; two open cases answer none of them and say why; the one
  window that is not the agent's answers ``figure``;
* the **list** -- ``total``, ``categories``, the lines without a body, the
  ``truncated`` line, and ``catalogues_unavailable`` naming the shared
  catalogue that has no folder rather than answering a shorter list;
* the **preview** -- ``prompt_detail`` says what the four sources would
  answer and remembers nothing;
* the **fill** -- the session's shot goes into the text with its source
  named, an unfilled hole is a refusal, and what this call names is kept for
  the next one;
* the **writes** -- a turn's text filed as a prompt, its holes read off the
  text when nobody declares them, an edit keeping the id, a delete taking the
  remembered values with it, a shared write refused when the folder is not
  named;
* the **shape** -- the one tool the loop is offered answers six actions, and
  each action's row in the table carries the parameters its method takes, so
  the loop cannot be offered a parameter the gesture refuses.
"""

import inspect
import os

import pytest

from imasviz.VizAgent import prompts
from imasviz.VizAgent.core import McpGuiCore

CASE_URI = ('imas:hdf5?path=/afs/eufus.eu/g2itmdev/user/g2lfleur/public/'
            'imasdb/west/3/54924/0')
OTHER_URI = ('imas:hdf5?path=/afs/eufus.eu/g2itmdev/user/g2lfleur/public/'
             'imasdb/west/3/112932/0')


class _Source:
    def __init__(self, uri):
        self.uri = uri


class _View:
    """The one thing ``_promptContext`` asks of a shot view: the URI of the
    case it shows."""

    def __init__(self, uri):
        self.dataSource = _Source(uri)


class _Api:
    def __init__(self, uris):
        self.DTVlist = [_View(uri) for uri in uris]


@pytest.fixture
def core(monkeypatch, tmp_path):
    """A core with a case of its own and a private ``HOME``: no window, no
    app, no case opened -- the gestures below ask nothing else."""
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setattr('imasviz.VizUtils.QVizPreferences.SharedPromptsDir',
                        '', raising=False)
    made = McpGuiCore.__new__(McpGuiCore)
    made.api = _Api([CASE_URI])
    made.list_windows = lambda: []
    return made


def _windowed(core, keys, kind='PlotView:'):
    core.list_windows = lambda: ([{'key': None, 'kind': 'Agent'}]
                                 + [{'key': k, 'kind': kind} for k in keys])


def _filed(core, text, **fields):
    """``save_prompt`` asked the way every face asks it: the body and the
    name are two named fields, because the page and the loop send a JSON
    object and the CLI spells flags, so no caller reaches for a position."""
    return core.save_prompt(text=text, **fields)


# ------------------------------------------------------------------ the context

def test_the_open_case_answers_its_own_values(core):
    context = core._promptContext()
    assert context['uri'] == CASE_URI
    assert context['case'] == 'west 54924.0'
    assert (context['database'], context['shot'], context['run']) == \
        ('west', '54924', '0')
    # The one thing this stand-in session does not answer is a window, and
    # the note says that -- never which case is meant.
    assert 'no window is open' in context['note']
    assert 'cases are open' not in context['note']


def test_two_open_cases_answer_no_case_value_and_say_why(core):
    core.api = _Api([CASE_URI, OTHER_URI])
    context = core._promptContext()
    for name in ('case', 'uri', 'shot', 'run', 'database'):
        assert name not in context
    assert '2 cases are open' in context['note']
    assert '{shot}' in context['note']


def test_no_open_case_says_so(core):
    core.api = _Api([])
    context = core._promptContext()
    assert 'no case is open' in context['note']
    assert 'shot' not in context


def test_a_view_the_session_cannot_answer_leaves_the_values_out(core):
    """A source that carries no case in its URI is not a guess."""
    core.api = _Api(['imas:mdsplus?user=g2lfleur'])
    context = core._promptContext()
    assert context['uri'] == 'imas:mdsplus?user=g2lfleur'
    assert context['case'] == 'imas:mdsplus?user=g2lfleur'
    assert 'shot' not in context and 'database' not in context


def test_the_figure_is_the_one_window_that_is_not_the_agent(core):
    _windowed(core, ['PlotView:1'])
    assert core._promptContext()['figure'] == 'PlotView:1'
    _windowed(core, ['PlotView:1', 'TablePlotView:2'])
    context = core._promptContext()
    assert 'figure' not in context
    assert '2 windows are open (PlotView:1, TablePlotView:2)' in \
        context['note']


def test_a_session_without_a_window_answers_no_figure(core):
    assert 'figure' not in core._promptContext()
    assert 'no window is open' in core._promptContext()['note']


# -------------------------------------------------------------------- the list

def test_the_list_carries_what_the_page_and_the_panel_build_from(core):
    _filed(core, 'les profils de {ids}', name='Profils 1D',
           category='profils', description='une ligne',
           variables='ids=core_profiles')
    _filed(core, 'le spectrogramme de {probe}', name='Spectrogramme',
           category='spectro')
    answer = core.list_prompts()
    assert answer['total'] == 2 and len(answer['prompts']) == 2
    assert [one['id'] for one in answer['prompts']] == \
        ['profils-1d', 'spectrogramme']
    assert answer['categories'] == {'profils': 1, 'spectro': 1}
    assert answer['context']['shot'] == '54924'
    line = answer['prompts'][0]
    assert 'text' not in line
    assert line['holes'] == ['ids'] and line['variables'] == \
        {'ids': 'core_profiles'}
    assert line['description'] == 'une ligne' and line['scope'] == 'personal'
    assert 'truncated' not in answer


def test_a_narrowed_list_says_what_it_cut(core):
    for n in range(4):
        _filed(core, 'prompt %d' % n, name='Prompt %d' % n)
    answer = core.list_prompts(limit=2)
    assert answer['total'] == 4 and len(answer['prompts']) == 2
    assert '2 of 4 prompts are answered' in answer['truncated']
    assert [one['name'] for one in core.list_prompts(query='Prompt 3')
            ['prompts']] == ['Prompt 3']
    assert core.list_prompts(category='absente')['prompts'] == []


def test_a_missing_catalogue_is_named_and_not_answered_away(core):
    _filed(core, 'un', name='Perso')
    answer = core.list_prompts()
    assert 'SharedPromptsDir' in answer['catalogues_unavailable']['shared']
    assert answer['total'] == 1
    # Asked for the personal catalogue alone, there is nothing missing to say.
    assert 'catalogues_unavailable' not in core.list_prompts(scope='personal')


# ------------------------------------------------------------------ the preview

def test_prompt_detail_previews_the_values_without_remembering_them(core):
    _filed(core, 'trace {ids} de {shot} à {rho}', name='Trois trous',
           variables='ids=core_profiles; shot=')
    detail = core.prompt_detail('Trois trous')
    assert detail['id'] == 'trois-trous' and detail['scope'] == 'personal'
    assert detail['text'] == 'trace {ids} de {shot} à {rho}'
    values = detail['values']
    assert values['ids'] == {'value': 'core_profiles',
                             'source': "the prompt's own default"}
    assert values['shot'] == {'value': '54924', 'source': 'this session'}
    assert values['rho'] == {'value': None, 'source': None}
    assert prompts.lastValues() == {}
    assert detail['context']['shot'] == '54924'


def test_prompt_detail_refuses_a_name_it_does_not_hold(core):
    refused = pytest.raises(ValueError, core.prompt_detail, 'inexistant')
    assert 'no prompt "inexistant"' in str(refused.value)


# ---------------------------------------------------------------------- the fill

def test_the_fill_puts_the_session_shot_in_the_text_and_says_where_it_came_from(
        core):
    _filed(core, 'le spectrogramme du shot {shot}', name='Spectro',
           variables='shot=')
    answer = core.fill_prompt('Spectro')
    assert answer['text'] == 'le spectrogramme du shot 54924'
    assert answer['values']['shot'] == {'value': '54924',
                                        'source': 'this session'}
    assert answer['id'] == 'spectro' and answer['name'] == 'Spectro'


def test_an_unfilled_hole_refuses_the_fill_naming_it(core):
    _filed(core, 'trace à {rho}', name='Rho')
    refused = pytest.raises(ValueError, core.fill_prompt, 'Rho')
    assert 'nobody answered' in str(refused.value) and '{rho}' in \
        str(refused.value)


def test_what_the_call_named_answers_first_and_is_kept_for_the_next_run(core):
    _filed(core, 'trace {ids} à {rho}', name='Deux',
           variables='ids=core_profiles; rho=0.85')
    answer = core.fill_prompt('Deux', {'ids': 'equilibrium', 'rho': '0.4'})
    assert answer['text'] == 'trace equilibrium à 0.4'
    assert answer['values']['ids']['source'] == 'you named it'
    assert prompts.lastValues() == {'personal/deux': {'ids': 'equilibrium',
                                                      'rho': '0.4'}}
    # The next run types nothing: the last values answer, and the answer says.
    again = core.fill_prompt('Deux')
    assert again['text'] == 'trace equilibrium à 0.4'
    assert again['values']['ids']['source'] == \
        'the last value you typed for this prompt'


def test_the_fill_refuses_a_value_named_for_a_hole_there_is_no_such(core):
    _filed(core, 'trace {ids}', name='Un trou', variables='ids=x')
    refused = pytest.raises(ValueError, core.fill_prompt, 'Un trou',
                            {'shot': '54924'})
    assert 'the prompt asks none of shot' in str(refused.value)


# -------------------------------------------------------------------- the writes

def test_a_turn_the_user_files_becomes_a_prompt_with_its_holes_read_off_it(core):
    filed = _filed(core, 'Trace {ids} du cas {case} puis compare avec la '
                         'figure {figure}', name='Comparaison',
                  category='bilan', description='une comparaison')
    assert filed['holes'] == ['ids', 'case', 'figure']
    assert filed['variables'] == {'ids': '', 'case': '', 'figure': ''}
    assert filed['id'] == 'comparaison' and filed['scope'] == 'personal'
    found = core.prompt_detail('Comparaison')
    assert found['id'] == filed['id']
    assert os.path.basename(filed['path']) == 'comparaison.md'
    # The session answers two of the three, so the fill asks for one.
    values = found['values']
    assert values['case'] == {'value': 'west 54924.0', 'source': 'this session'}
    assert values['figure'] == {'value': None, 'source': None}


def test_an_edit_keeps_the_id_and_delete_takes_the_values_with_it(core):
    entry = _filed(core, 'trace {shot}', name='Un', prompt_id='un')
    core.fill_prompt('Un', {'shot': '54924'})
    changed = core.edit_prompt('Un', text='trace le {shot} en {ids}',
                               variables='shot=; ids=core_profiles')
    assert changed['id'] == 'un' and changed['holes'] == ['shot', 'ids']
    assert changed['description'] == ''
    assert prompts.lastValues() == {'personal/un': {'shot': '54924'}}
    assert core.delete_prompt('un') == {
        'deleted': 'un', 'scope': 'personal', 'path': entry['path']}
    assert prompts.lastValues() == {}
    pytest.raises(ValueError, core.prompt_detail, 'un')


def test_a_shared_write_without_a_named_folder_is_refused(core):
    refused = pytest.raises(ValueError, core.save_prompt, text='un',
                            name='Équipe', scope='shared')
    assert 'SharedPromptsDir' in str(refused.value)
    assert core.list_prompts()['total'] == 0


def test_a_shared_prompt_is_read_and_answered_when_the_folder_is_named(
        core, monkeypatch, tmp_path):
    folder = tmp_path / 'shared'
    folder.mkdir()
    with open(str(folder / 'bilan.md'), 'w', encoding='utf-8') as f:
        f.write('name: Bilan\ncategory: bilan\n\nle bilan du {shot}\n')
    monkeypatch.setattr('imasviz.VizUtils.QVizPreferences.SharedPromptsDir',
                        str(folder), raising=False)
    answer = core.list_prompts()
    assert [(one['scope'], one['id']) for one in answer['prompts']] == \
        [('shared', 'bilan')]
    assert 'catalogues_unavailable' not in answer
    assert core.fill_prompt('Bilan')['text'] == 'le bilan du 54924'
    assert core.delete_prompt('bilan')['scope'] == 'shared'
    assert not os.listdir(str(folder))


# --------------------------------------------------------------------- the shape

PROMPT_GESTURES = ('list_prompts', 'prompt_detail', 'fill_prompt',
                   'save_prompt', 'edit_prompt', 'delete_prompt')


def test_the_catalogue_answers_one_name_whose_actions_answer_the_methods(core):
    """The loop offers one tool whose ``action`` picks the ask, the core
    answers six methods: a drift between what an action is offered with and
    what its method takes is a call the loop cannot make correctly. Since the
    merge, the parameters of an action live in the table's row for that
    member, not in a schema of its own -- which is what test_175 checks
    against the offered schema, and what is checked here against the
    signature.
    """
    from imasviz.VizAgent.tools import (ACTION_PARAMETERS, TOOLS, memberNames,
                                        unknownParameters)
    offered = {tool['function']['name'] for tool in TOOLS}
    assert 'manage_prompt' in offered
    for gesture in PROMPT_GESTURES:
        assert gesture not in offered, \
            '%s is offered on its own and as an action' % gesture
        assert gesture in memberNames(), \
            '%s is no longer vocabulary of the loop' % gesture
        declared = set(ACTION_PARAMETERS[gesture][0])
        taken = set(inspect.signature(getattr(core, gesture)).parameters)
        assert declared == taken - {'self'}, \
            '%s: the action is offered with %s, the method takes %s' % (
                gesture, sorted(declared), sorted(taken))
    # A parameter the action does not take is refused before the call.
    assert unknownParameters('fill_prompt', {'name': 'x', 'coucou': 1}) == \
        ['coucou']
    assert unknownParameters('fill_prompt', {'name': 'x', 'values': {}}) == []
