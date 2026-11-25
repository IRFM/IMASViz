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

"""The prompt catalogue on disk: ``VizAgent/prompts.py`` alone.

No IMAS, no Qt, no case: a prompt is a file under ``$HOME/.imasviz``, so the
whole catalogue is answerable with a private ``HOME`` (the pattern
``test_148``/``test_149`` hold for the journals). What is pinned here is what
every face -- the agent's tools, the page, the panel, the CLI -- reads through
the six core gestures, so a rule refused here is refused five times:

* the **file** -- front matter, body, id, and the two ways a file is *not* a
  prompt (a stranger's front matter, a body with nothing to ask);
* the **list** -- category first then name, the category counts, what a query
  narrows, and a prompt a hand wrote in the folder being in the list under
  the name that hand gave it;
* the **name** -- an id or a display name, and two prompts carrying one name
  being a refusal that names both ids rather than the first one reached;
* the **holes** -- a brace is a variable only when it is a bare identifier, a
  declaration that cannot be read costing that prompt's defaults and nothing
  else, a declared hole the body never opens being refused at the write;
* the **two catalogues** -- an unnamed ``SharedPromptsDir`` costing its own
  catalogue and refusing a write that asks for it, never filing it in the
  personal folder instead;
* the **four sources of a value** -- caller, last typed, session, file
  default -- and the sidecar of last values staying in the user's own folder
  whatever catalogue the prompt sits in;
* the **refusals** -- an empty body, a duplicate id, a hole nobody answered,
  a value named for a hole that is not there.
"""

import json
import os

import pytest

from imasviz.VizAgent import prompts
from imasviz.VizAgent.prompts import (
    PromptStore, fillTemplate, parseVariables, renderVariables,
    resolveValues, templateVariables)


@pytest.fixture
def home(monkeypatch, tmp_path):
    """A ``HOME`` of its own: the catalogue and its sidecar are written under
    it, so the real ``~/.imasviz`` is never touched and one test cannot read
    what another left behind. The shared catalogue is left unnamed, which is
    its default state, and the tests that want one name it themselves."""
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setattr('imasviz.VizUtils.QVizPreferences.SharedPromptsDir',
                        '', raising=False)
    return str(tmp_path)


@pytest.fixture
def store(home):
    """The store, always over the private ``HOME`` above: it reads `HOME`
    when it is called, so a test that reaches it without this fixture would
    write into the real `~/.imasviz` of whoever runs the suite."""
    assert home
    return PromptStore


def _write(folder, fileName, text):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, fileName)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    return path


def _shared(monkeypatch, tmp_path, **handWritten):
    """Name a shared folder, optionally with prompts a colleague wrote."""
    folder = tmp_path / 'shared_prompts'
    folder.mkdir(exist_ok=True)
    for fileName, text in handWritten.items():
        _write(str(folder), fileName, text)
    monkeypatch.setattr('imasviz.VizUtils.QVizPreferences.SharedPromptsDir',
                        str(folder), raising=False)
    return str(folder)


# ------------------------------------------------------------------ the file

def test_a_prompt_is_a_file_the_catalogue_reads_back(store, home):
    entry = store.add_prompt(
        'Trace les profils de {ids} du cas ouvert.', name='Profils du plat-top',
        category='profils', description='Les profils d un IDS de profils.',
        variables={'ids': 'core_profiles'})
    path = os.path.join(home, '.imasviz', 'prompts', 'profils-du-plat-top.md')
    assert entry.path == path and os.path.isfile(path)
    with open(path, encoding='utf-8') as f:
        written = f.read()
    assert written.splitlines()[:4] == [
        'name: Profils du plat-top',
        'category: profils',
        'description: Les profils d un IDS de profils.',
        'variables: ids=core_profiles',
    ]
    assert written.strip().endswith(
        'Trace les profils de {ids} du cas ouvert.')
    # A catalogue line is not a body: only the whole read carries the text.
    assert 'text' not in entry.asLine()
    assert entry.asDict()['text'] == 'Trace les profils de {ids} du cas ouvert.'


def test_the_author_is_the_writer_of_the_run(store, monkeypatch):
    monkeypatch.setenv('USER', 'g2lfleur')
    entry = store.add_prompt('Que voit la figure {figure} ?', name='Figure')
    assert entry.author == 'g2lfleur'


def test_a_file_that_is_not_a_prompt_is_not_in_the_list(store, home):
    folder = store.personalDirectory()
    _write(folder, 'README.md', 'Des prompts de l équipe.\n')
    _write(folder, 'note.md', 'title: un fichier d ailleurs\n\ncorps\n')
    _write(folder, 'sans_corps.md', 'name: rien\ncategory: vide\n')
    assert store.list_prompts(scope='personal') == []
    store.add_prompt('Le seul prompt.', name='Seul')
    assert [e.id for e in store.list_prompts(scope='personal')] == ['seul']
    refused = pytest.raises(ValueError, store.read_prompt, 'personal', 'note')
    assert 'is not a prompt this shape answers' in str(refused.value)


# -------------------------------------------------------------------- the list

def test_the_list_is_category_first_and_then_name(store):
    store.add_prompt('un', name='Zébrures', category='spectro')
    store.add_prompt('deux', name='Alpha', category='spectro')
    store.add_prompt('trois', name='Sans catégorie')
    store.add_prompt('quatre', name='Profils', category='profils')
    assert [(e.category, e.name) for e in store.list_prompts()] == [
        ('profils', 'Profils'), ('spectro', 'Alpha'), ('spectro', 'Zébrures'),
        ('', 'Sans catégorie')]


def test_categories_counts_the_prompts_of_each_category(store):
    store.add_prompt('un', name='A', category='profils')
    store.add_prompt('deux', name='B', category='profils')
    store.add_prompt('trois', name='C')
    assert store.categories() == {'profils': 2, '': 1}
    assert store.categories(scope='personal') == {'profils': 2, '': 1}
    assert store.categories(scope='shared') == {}


def test_a_category_and_a_query_narrow_the_list(store):
    store.add_prompt('un', name='Profils 1D', category='profils',
                     description='les profils radiaux')
    store.add_prompt('deux', name='Spectrogramme', category='spectro',
                     description='une transformée temps fréquence')
    assert [e.name for e in store.list_prompts(category='PROFILS')] == \
        ['Profils 1D']
    assert [e.name for e in store.list_prompts(query='fréquence')] == \
        ['Spectrogramme']
    assert [e.name for e in store.list_prompts(query='spectro')] == \
        ['Spectrogramme']
    assert store.list_prompts(category='absente') == []


def test_a_prompt_written_by_hand_is_in_the_list_under_that_name(store, home):
    """The folder is the catalogue: the guard refuses a name that escapes it,
    not a name this writer would not have given a file."""
    path = _write(store.personalDirectory(), 'Mon_Prompt_2026.md',
                  'name: Mon prompt\n\ndessine {rho}\n')
    assert [e.id for e in store.list_prompts(scope='personal')] == \
        ['Mon_Prompt_2026']
    assert os.path.realpath(store.read_prompt('personal',
                                              'Mon_Prompt_2026').path) \
        == os.path.realpath(path)
    assert store.find('Mon_Prompt_2026').name == 'Mon prompt'


def test_a_name_that_escapes_the_folder_is_refused(store):
    store.personalDirectory()
    for spelling in ('../evil', '..', 'a/b', '.cache'):
        with pytest.raises(ValueError):
            store.read_prompt('personal', spelling)
        with pytest.raises(ValueError):
            store.add_prompt('corps', name='x', prompt_id=spelling)


# -------------------------------------------------------------------- the name

def test_a_prompt_is_found_by_its_id_or_by_its_name(store):
    entry = store.add_prompt('un', name='Profils du plat-top',
                             category='profils')
    assert store.find('profils-du-plat-top').id == entry.id
    assert store.find('PROFILS DU PLAT-TOP').id == entry.id
    assert store.find('  Profils du plat-top  ').id == entry.id


def test_two_prompts_under_one_name_are_refused_naming_both_ids(store):
    store.add_prompt('un', name='Bilan du pulse', category='profils')
    store.add_prompt('deux', name='Bilan du pulse', category='spectro',
                     prompt_id='autre')
    refused = pytest.raises(ValueError, store.find, 'bilan du pulse')
    message = str(refused.value)
    assert 'bilan-du-pulse (personal)' in message and 'autre (personal)' \
        in message
    assert 'name the one you mean by its id' in message


def test_no_such_prompt_lists_the_ones_the_catalogue_holds(store):
    store.add_prompt('un', name='Profils 1D', prompt_id='profils-1d')
    refused = pytest.raises(ValueError, store.find, 'ce-qui-n-existe-pas')
    assert 'profils-1d (personal)' in str(refused.value)
    with pytest.raises(ValueError):
        store.find('   ')


# ------------------------------------------------------------------- the holes

def test_the_holes_are_the_declared_ones_plus_the_ones_the_body_opens(store):
    entry = store.add_prompt('trace {ids} à {rho} pour le shot {shot}',
                             name='Trou', variables='ids=core_profiles; shot=')
    assert entry.holes() == ['ids', 'shot', 'rho']
    assert entry.variables == {'ids': 'core_profiles', 'shot': ''}
    assert not entry.variables_refusal


def test_a_hole_the_body_never_opens_is_refused_at_the_write(store):
    """Asked of both spellings of a declaration: a declared hole the body
    does not open is one ``holes()`` keeps asking for and a fill never
    fills, whoever spelled the declaration."""
    refused = pytest.raises(ValueError, store.add_prompt, 'trace {ids}',
                            name='Trop', variables='ids=core_profiles; rho=0.5')
    assert 'the prompt asks none of {rho}' in str(refused.value)
    assert pytest.raises(ValueError, store.add_prompt, 'trace {ids}',
                         name='Trop',
                         variables={'ids': 'core_profiles', 'rho': '0.5'})
    assert store.list_prompts(scope='personal') == []


def test_a_declaration_that_cannot_be_read_costs_only_its_own_defaults(store,
                                                                      home):
    """The prompt the user is mid-way through editing stays in the list: its
    holes still answer, only its defaults are gone."""
    _write(store.personalDirectory(), 'a-moitie.md',
           'name: À moitié\nvariables: ids,\n\ntrace {ids} de {shot}\n')
    entries = store.list_prompts(scope='personal')
    assert len(entries) == 1
    entry = entries[0]
    assert entry.variables == {}
    assert 'is not the declaration of a variable' in entry.variables_refusal
    assert entry.holes() == ['ids', 'shot']
    assert entry.asLine()['variables_refusal'] == entry.variables_refusal


def test_a_brace_that_is_not_a_bare_name_is_text_the_prompt_says():
    body = ('le JSON {"a": 1}, le vecteur {x.y}, la note {Mauvais nom} '
            'et le trou {shot}')
    assert templateVariables(body) == ['shot']
    assert fillTemplate(body, {'shot': '54924'}) == \
        ('le JSON {"a": 1}, le vecteur {x.y}, la note {Mauvais nom} '
         'et le trou 54924')


def test_the_declaration_round_trips_through_its_spelling():
    assert parseVariables('ids=core_profiles; shot=; rho=0.85') == \
        {'ids': 'core_profiles', 'shot': '', 'rho': '0.85'}
    assert parseVariables('shot') == {'shot': ''}
    assert parseVariables('') == {}
    for bad in ('=0.85', 'Shot=1', 'a b=1'):
        with pytest.raises(ValueError):
            parseVariables(bad)
    assert renderVariables({'shot': '', 'rho': '0.85'}) == 'shot=; rho=0.85'


def test_a_hole_nobody_answered_refuses_the_fill_naming_it():
    refused = pytest.raises(ValueError, fillTemplate, 'trace {ids} de {shot}',
                            {'ids': 'core_profiles'})
    assert '{shot}' in str(refused.value) and '1 hole' in str(refused.value)


# -------------------------------------------------------------- two catalogues

def test_an_unnamed_shared_catalogue_costs_its_own_half_only(store):
    refused = pytest.raises(ValueError, store.sharedDirectory)
    assert 'SharedPromptsDir' in str(refused.value)
    store.add_prompt('un', name='Perso')
    assert [e.scope for e in store.list_prompts()] == ['personal']
    assert 'SharedPromptsDir' in store.unavailable()['shared']
    assert store.unavailable(scope='personal') == {}


def test_a_write_that_asks_for_the_shared_catalogue_is_refused_not_filed_in_the_other_one(
        store, home):
    """A prompt believed shared and filed personally is one nobody else
    reads."""
    refused = pytest.raises(ValueError, store.add_prompt, 'un', name='Équipe',
                            scope='shared')
    assert 'no folder named' in str(refused.value)
    assert store.list_prompts() == []


def test_a_shared_prompt_is_read_and_written_when_its_folder_is_named(store,
                                                                     home,
                                                                     monkeypatch,
                                                                     tmp_path):
    folder = _shared(monkeypatch, tmp_path, **{
        'par_un_collegue.md': 'name: Bilan du pulse\ncategory: bilan\n'
                              'description: écrit par l équipe\n\n'
                              'le bilan du {shot}\n'})
    store.add_prompt('le mien {shot}', name='Perso')
    assert [(e.scope, e.id) for e in store.list_prompts()] == [
        ('shared', 'par_un_collegue'), ('personal', 'perso')]
    written = store.add_prompt('Écrit depuis l autre node {shot}',
                               name='Partagé', scope='shared',
                               prompt_id='partage')
    assert written.scope == 'shared'
    assert os.path.isfile(os.path.join(folder, 'partage.md'))
    assert not os.path.isfile(os.path.join(home, '.imasviz', 'prompts',
                                           'partage.md'))
    assert store.categories() == {'bilan': 1, '': 2}
    assert store.find('Bilan du pulse').scope == 'shared'


def test_an_unreadable_shared_folder_is_named(store, monkeypatch, tmp_path):
    monkeypatch.setattr('imasviz.VizUtils.QVizPreferences.SharedPromptsDir',
                        str(tmp_path / 'n_existe_pas'), raising=False)
    assert 'is not a' in str(pytest.raises(ValueError,
                                           store.sharedDirectory).value)
    assert store.unavailable()['shared']
    assert store.list_prompts() == []


def test_an_unknown_scope_is_refused(store):
    for scope in (' Shared', 'les_deux', 'public'):
        with pytest.raises(ValueError):
            store.list_prompts(scope=scope)
        with pytest.raises(ValueError):
            store.add_prompt('un', name='x', scope=scope)


# ------------------------------------------------------------------ the writes

def test_a_write_over_a_prompt_the_catalogue_holds_is_refused(store):
    store.add_prompt('un', name='Profils 1D', prompt_id='profils-1d')
    refused = pytest.raises(ValueError, store.add_prompt, 'deux',
                            name='Profils 1D bis', prompt_id='profils-1d')
    assert 'already holds a prompt "profils-1d"' in str(refused.value)
    # The way back is spelled as a face may type it: the old name is refused
    # on its own now, so a refusal naming it would answer a dead call.
    assert 'manage_prompt(action="edit")' in str(refused.value)


def test_a_prompt_with_nothing_to_ask_is_refused(store):
    for body in ('', '   ', None):
        with pytest.raises(ValueError):
            store.add_prompt(body, name='Vide')


def test_an_edit_keeps_the_id_and_what_it_did_not_name(store):
    entry = store.add_prompt('trace {ids}', name='Profils 1D',
                             category='profils', description='une ligne',
                             variables='ids=core_profiles',
                             prompt_id='profils-1d')
    changed = store.edit_prompt('personal', 'profils-1d',
                                body='trace {ids} à {rho}')
    assert changed.id == entry.id and changed.path == entry.path
    assert changed.name == 'Profils 1D'
    assert changed.category == 'profils'
    assert changed.description == 'une ligne'
    assert changed.body == 'trace {ids} à {rho}'
    assert changed.holes() == ['ids', 'rho']
    # An empty string clears a field; leaving it out keeps it.
    cleared = store.edit_prompt('personal', 'profils-1d', description='')
    assert cleared.description == '' and cleared.category == 'profils'


def test_an_edit_that_takes_a_hole_out_of_the_body_answers_for_it(store):
    """The declaration an edit keeps is asked the same question as one it
    names: a stale declaration is a hole the next fill would ask for and
    never fill."""
    store.add_prompt('trace {ids} à {rho}', name='Un', prompt_id='un',
                     variables='ids=core_profiles; rho=0.85')
    refused = pytest.raises(ValueError, store.edit_prompt, 'personal', 'un',
                            body='trace {ids}')
    assert 'the prompt asks none of {rho}' in str(refused.value)
    assert store.read_prompt('personal', 'un').body == 'trace {ids} à {rho}'
    # Said again with the declaration that goes with the new body: the edit
    # goes through, and its id is untouched.
    changed = store.edit_prompt('personal', 'un', body='trace {ids}',
                                variables='ids=core_profiles')
    assert changed.id == 'un' and changed.holes() == ['ids']


def test_an_edit_that_empties_the_body_is_refused(store):
    store.add_prompt('trace', name='Un', prompt_id='un')
    assert 'empty body' in str(pytest.raises(ValueError, store.edit_prompt,
                                             'personal', 'un',
                                             body='  ').value)
    assert store.read_prompt('personal', 'un').body == 'trace'


def test_an_edit_of_a_prompt_that_is_not_there_is_refused(store):
    assert 'No prompt "absent"' in str(pytest.raises(
        ValueError, store.edit_prompt, 'personal', 'absent', body='x').value)


def test_deleting_a_prompt_takes_its_file_and_its_values(store):
    entry = store.add_prompt('trace {shot}', name='Un', prompt_id='un',
                             variables='shot=')
    resolveValues(entry, {'shot': '54924'})
    assert prompts.lastValues() == {'personal/un': {'shot': '54924'}}
    assert store.delete_prompt('personal', 'un') == {
        'deleted': 'un', 'scope': 'personal', 'path': entry.path}
    assert not os.path.exists(entry.path)
    assert prompts.lastValues() == {}
    assert 'none at all' in str(pytest.raises(ValueError, store.delete_prompt,
                                              'personal', 'un').value)


# -------------------------------------------------------------------- the values

def test_the_four_sources_answer_in_order(store):
    entry = store.add_prompt('trace {ids} de {shot} à {rho} pour {figure}',
                             name='Sources', prompt_id='sources',
                             variables='ids=core_profiles; shot=; rho=0.85')
    session = {'shot': '54924', 'figure': 'PlotView:1'}
    got = resolveValues(entry, context=session, remember=False)
    assert {name: one['value'] for name, one in got.items()} == \
        {'ids': 'core_profiles', 'shot': '54924', 'rho': '0.85',
         'figure': 'PlotView:1'}
    assert {name: one['source'] for name, one in got.items()} == {
        'ids': "the prompt's own default", 'shot': 'this session',
        'rho': "the prompt's own default", 'figure': 'this session'}

    # What this call names wins over all three, and is all it remembers.
    got = resolveValues(entry, {'shot': '112932', 'ids': 'equilibrium'},
                        context=session)
    assert {name: one['value'] for name, one in got.items()} == \
        {'ids': 'equilibrium', 'shot': '112932', 'rho': '0.85',
         'figure': 'PlotView:1'}
    assert all(one['source'] == 'you named it'
               for name, one in got.items() if name in ('ids', 'shot'))

    # On the next run, the last typed value answers before the session.
    again = resolveValues(entry, context=session, remember=False)
    assert again['shot'] == {'value': '112932', 'source':
                             'the last value you typed for this prompt'}
    assert again['ids']['source'] == 'the last value you typed for this prompt'
    # ... and it never stands in for a hole this call named nothing for.
    assert again['rho']['source'] == "the prompt's own default"
    assert again['figure']['source'] == 'this session'


def test_a_hole_none_of_the_four_answers_comes_back_empty(store):
    entry = store.add_prompt('trace {shot}', name='Un', prompt_id='un',
                             variables='shot=')
    assert resolveValues(entry, remember=False) == \
        {'shot': {'value': None, 'source': None}}


def test_a_value_named_for_a_hole_the_prompt_does_not_open_is_refused(store):
    entry = store.add_prompt('trace {ids}', name='Un', prompt_id='un',
                             variables='ids=core_profiles')
    refused = pytest.raises(ValueError, resolveValues, entry,
                            {'ids': 'core_profiles', 'shot': '54924'})
    assert 'the prompt asks none of shot' in str(refused.value)
    assert prompts.lastValues() == {}


def test_the_last_values_of_a_shared_prompt_stay_in_the_user_folder(store,
                                                                   home,
                                                                   monkeypatch,
                                                                   tmp_path):
    folder = _shared(monkeypatch, tmp_path)
    entry = store.add_prompt('le bilan du {shot}', name='Partagé',
                             scope='shared', prompt_id='bilan')
    resolveValues(entry, {'shot': '54924'})
    sidecar = os.path.join(home, '.imasviz', prompts.VALUES_FILENAME)
    with open(sidecar, encoding='utf-8') as f:
        assert json.load(f) == {'shared/bilan': {'shot': '54924'}}
    assert sorted(os.listdir(folder)) == ['bilan.md']


def test_a_sidecar_that_does_not_parse_costs_the_remembering_only(store, home):
    """The fill the session answers still runs; the fill that asks to keep a
    typed value is refused by what the file is, rather than written over."""
    os.makedirs(os.path.join(home, '.imasviz'), exist_ok=True)
    with open(os.path.join(home, '.imasviz', prompts.VALUES_FILENAME),
              'w', encoding='utf-8') as f:
        f.write('pas du json')
    entry = store.add_prompt('trace {shot}', name='Un', prompt_id='un',
                             variables='shot=42')
    got = resolveValues(entry, context={'shot': '54924'})
    assert got['shot'] == {'value': '54924', 'source': 'this session'}
    refused = pytest.raises(ValueError, resolveValues, entry,
                            {'shot': '112932'})
    assert 'is not the remembered prompt values' in str(refused.value)
