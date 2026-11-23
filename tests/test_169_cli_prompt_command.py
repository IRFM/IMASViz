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

"""The prompt catalogue on the client's line.

``/prompt`` asks the same six gestures the panel, the page and the model
ask -- ``list_prompts``, ``prompt_detail``, ``fill_prompt``,
``save_prompt``, ``edit_prompt``, ``delete_prompt`` -- read raw into the
console with no LLM in between, exactly as ``/ids`` and ``/note`` read
theirs. What is specific to this surface is the last step of ``/prompt
run``: the filled text goes to the session's own ``runPrompt``, so the
turn, its transcript and the prompt history the whole application shares
are what any typed line leaves. The one thing a filed prompt costs is the
typing of the holes this session does not already know.

The core here is the real one, on a session whose single open case is
spelled by a URI (``test_167``, ``test_168``): the catalogue gestures ask
nothing of a window and the case values come off the URI string, so no
Access Layer is reached and the shot of the reference case is the value
the listing advertises for free. The model is scripted and ends on a plain
answer, so ``runPrompt`` records a turn without a gesture and without an
endpoint.

Two shapes of this client decide the assertions. ``parse`` is a plain
``split()``, so a ``--flag`` value is one word -- which is why the
declaration is spelled ``ids=core_profiles;shot=`` here and a description
one word. And the holes a run still owes are asked on the line with
``input``: what is answered there is remembered for the next run, and what
is left empty is not an answer -- the fill refuses by name rather than
send a prompt with ``{rho}`` still in it.
"""

import os
import re

import pytest

from imasviz.VizAgent import prompts as promptStore
from imasviz.VizAgent.core import McpGuiCore
from imasviz.VizAgent.llm_client import LLMResponse
from imasviz.VizAgent.QVizPromptHistory import QVizPromptHistory

from viz_cli import commands
from viz_cli.session import Client, CliSession

CASE_URI = ('imas:hdf5?path='
            '/afs/eufus.eu/g2itmdev/user/g2lfleur/public/imasdb/west/3/54924/0')


class _Source:
    def __init__(self, uri):
        self.uri = uri


class _View:
    def __init__(self, uri):
        self.dataSource = _Source(uri)


class _Api:
    def __init__(self, uris):
        self.DTVlist = [_View(uri) for uri in uris]


class FakeWindow:
    """What the session asks of the window: the api, and a hide at exit."""

    def sessionApi(self):
        return None

    def hide(self):
        pass


class ScriptedLLM:
    """Ends a turn on a plain answer -- no tool call, so the turn is
    recorded and nothing is handed to a GUI thread that is not running
    here. Its ``messages`` are what the model was fed, which is where the
    filled text of a run is read back."""

    def __init__(self):
        self.messages = []

    def chat(self, messages, tools=None, **kwargs):
        self.messages.append(list(messages))
        return LLMResponse(content='ok', tool_calls=None, finish_reason='stop')


def _core(uris=(CASE_URI,)):
    made = McpGuiCore.__new__(McpGuiCore)
    made.api = _Api(list(uris))
    made.list_windows = lambda: []
    return made


def buildSession(tmp_path, qapp, uris=(CASE_URI,)):
    """One client session: the real loop and the real catalogue gestures,
    a scripted model, no window. The pump of ``runPrompt`` needs a live Qt
    application -- ``app=None`` answers a turn with an AttributeError on
    ``processEvents``, which is why the ``qapp`` fixture is asked here."""
    llm = ScriptedLLM()
    session = CliSession(app=qapp, window=FakeWindow(), core=_core(uris),
                         llm=Client(llm), shots_dir=str(tmp_path / 'cli'),
                         max_turns=4)
    return session, llm


def askEveryValue(*answers):
    """The line answers what it is asked, in order. An exhausted list is a
    failure of the test: more holes were owed than this file meant to ask."""
    owed = list(answers)

    def ask(text):
        if not owed:
            raise AssertionError('the line was asked %s with nothing left '
                                 'to answer' % text)
        return owed.pop(0)
    return ask


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    """The catalogue, the remembered values and the shared prompt history
    all live under ``$HOME/.imasviz``, so ``HOME`` answers for itself (the
    ``test_39`` pattern) and the shared catalogue is refused by name rather
    than inherited from the user's own preferences."""
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    monkeypatch.setattr('imasviz.VizUtils.QVizPreferences.SharedPromptsDir',
                        '', raising=False)
    return tmp_path


def run(line, session):
    """One ``/prompt`` line, parsed the way the REPL parses it."""
    return commands.execute(commands.parse(line), session)


# ------------------------------------------------------------------- the listing

def test_prompt_alone_lists_the_catalogue_and_what_this_session_answers(
        tmp_path, qapp, capsys):
    session, _ = buildSession(tmp_path, qapp)
    run('/prompt save Profils trace {ids} de {shot} --category profils '
        '--description une_ligne', session)
    run('/prompt save Bilan le bilan energetique', session)
    capsys.readouterr()

    assert run('/prompt', session)
    out = capsys.readouterr().out
    assert '2 prompt(s)' in out
    assert 'categories : (none) (1), profils (1)' in out
    # Category first, then name: the order a reader scans for.
    entries = [one for one in out.splitlines()
               if one.startswith('  profils') or one.startswith('  bilan')]
    assert len(entries) == 2 and entries[0].startswith('  profils')
    # The holes are shown as they will be asked: a default spelled, an
    # open hole bare.
    assert '{ids} {shot}' in out
    assert '(no hole)' in out
    assert 'une_ligne' in out
    # And the values this session knows are said: that is the whole point
    # of re-running a filed prompt instead of retyping it.
    assert 'this session answers:' in out
    assert '{shot}=54924' in out and '{case}=west 54924.0' in out


def test_the_listing_which_holds_nothing_says_how_to_file_one(
        tmp_path, qapp, capsys):
    session, _ = buildSession(tmp_path, qapp)
    assert run('/prompt', session)
    out = capsys.readouterr().out
    assert '0 prompt(s)' in out
    assert '(none: /prompt save NAME TEXT files one' in out
    # The shared catalogue this node cannot answer is said, not hidden:
    # a shorter list without the reason reads as an empty shelf.
    assert 'shared :' in out and 'SharedPromptsDir' in out


def test_an_unknown_sub_command_is_refused_with_the_four_shapes(tmp_path, qapp):
    session, _ = buildSession(tmp_path, qapp)
    with pytest.raises(ValueError) as exc:
        run('/prompt effacer bilan', session)
    msg = str(exc.value)
    assert 'effacer' in msg
    for shape in ('/prompt list', '/prompt show', '/prompt run',
                  '/prompt save'):
        assert shape in msg


def test_a_narrowed_listing_a_cut_one_and_a_refused_limit(tmp_path, qapp, capsys):
    session, _ = buildSession(tmp_path, qapp)
    for n in range(3):
        run('/prompt save Prompt%d un %d' % (n, n), session)
    capsys.readouterr()

    assert run('/prompt list Prompt1', session)
    out = capsys.readouterr().out
    assert '1 prompt(s)' in out and '  prompt1' in out
    assert 'prompt0' not in out and 'prompt2' not in out

    assert run('/prompt list --limit 1', session)
    cut = capsys.readouterr().out
    assert '3 prompt(s)' in cut
    assert '1 of 3 prompts are answered' in cut

    for line, word in (('/prompt list --limit 0', '0'),
                       ('/prompt list --limit deux', 'deux')):
        with pytest.raises(ValueError) as exc:
            run(line, session)
        assert word in str(exc.value)

    assert run('/prompt list --scope personal', session)
    assert '3 prompt(s)' in capsys.readouterr().out


def test_a_flag_this_command_does_not_hold_is_refused_by_name(tmp_path, qapp):
    """``/note`` and ``/prompt`` answer different flags, and the refusal
    lists the ones of the command asked -- not the other's."""
    session, _ = buildSession(tmp_path, qapp)
    with pytest.raises(ValueError) as exc:
        run('/prompt list --machine WEST', session)
    msg = str(exc.value)
    assert '--machine' in msg
    for held in ('--scope', '--category', '--variables', '--limit',
                 '--description'):
        assert held in msg
    assert '--shot' not in msg


def test_a_prompt_whose_declaration_does_not_parse_keeps_its_line(
        tmp_path, qapp, capsys):
    """A file the user is mid-way through editing costs its own declaration
    and not the catalogue around it: the line is still listed, with what is
    wrong with it said out loud."""
    folder = promptStore.PromptStore.folderFor('personal')
    with open(os.path.join(folder, 'casse.md'), 'w', encoding='utf-8') as f:
        f.write('name: Case\ncategory: bilan\ndescription: a la main\n'
                'variables: ids,\nauthor: moi\n\ntrace {ids}\n')
    session, _ = buildSession(tmp_path, qapp)
    assert run('/prompt', session)
    out = capsys.readouterr().out
    assert '1 prompt(s)' in out and 'Case' in out
    assert 'REFUSAL —' in out
    capsys.readouterr()
    assert run('/prompt show casse', session)
    assert 'REFUSAL —' in capsys.readouterr().out


# ---------------------------------------------------------------------- the show

def test_prompt_show_answers_its_fields_its_text_and_its_values(
        tmp_path, qapp, capsys):
    session, _ = buildSession(tmp_path, qapp)
    run('/prompt save Spectro le spectrogramme du {shot} a {rho} '
        '--category spectro --description comparaison', session)
    capsys.readouterr()

    assert run('/prompt show spectro', session)
    out = capsys.readouterr().out
    for label in ('id', 'name', 'catalogue', 'category', 'description',
                  'author', 'file'):
        assert re.search(r'^  %s\s*:' % label, out, re.M), \
            'the answer carries no %s line' % label
    assert '  id         : spectro' in out
    assert '  name       : Spectro' in out
    assert '  catalogue  : personal' in out
    assert 'le spectrogramme du {shot} a {rho}' in out
    assert '{shot} : 54924 — this session' in out
    assert '{rho} : nothing answers it yet: a run will ask' in out


def test_prompt_show_of_a_prompt_with_no_hole_says_so(tmp_path, qapp, capsys):
    session, _ = buildSession(tmp_path, qapp)
    run('/prompt save Bilan le bilan energetique du cas', session)
    capsys.readouterr()
    assert run('/prompt show bilan', session)
    assert '(this prompt opens no hole: it is asked as it stands)' \
        in capsys.readouterr().out


def test_prompt_show_refuses_what_it_cannot_pick(tmp_path, qapp, capsys):
    session, _ = buildSession(tmp_path, qapp)
    with pytest.raises(ValueError) as exc:
        run('/prompt show', session)
    assert 'needs the id or the name' in str(exc.value)

    run('/prompt save Un un prompt', session)
    run('/prompt save Deux deux prompts', session)
    capsys.readouterr()
    with pytest.raises(ValueError) as exc:
        run('/prompt show un deux', session)
    assert 'takes one prompt' in str(exc.value)

    with pytest.raises(ValueError) as exc:
        run('/prompt show inexistant', session)
    msg = str(exc.value)
    assert 'no prompt "inexistant"' in msg
    assert 'un (personal)' in msg and 'deux (personal)' in msg, \
        'the refusal lists what the catalogue does hold'


# ----------------------------------------------------------------------- the run

def test_a_run_fills_from_the_session_and_starts_a_turn_with_that_text(
        tmp_path, qapp, capsys, monkeypatch):
    """The session knows the shot, so a filed prompt costs no typing at
    all: the text the model is fed is the body with its hole filled, and
    the turn is a turn like a typed line -- the shared history holds it."""
    monkeypatch.setattr('builtins.input',
                        lambda *a: (_ for _ in ()).throw(
                            AssertionError('no hole is owed here')))
    session, llm = buildSession(tmp_path, qapp)
    run('/prompt save Spectro le spectrogramme du {shot}', session)
    capsys.readouterr()

    assert run('/prompt run spectro', session)
    out = capsys.readouterr().out
    assert '/prompt run Spectro — {shot} from this session' in out
    filled = 'le spectrogramme du 54924'
    assert session.prompts == [filled]
    assert llm.messages[-1][-1]['content'] == filled
    assert filled in QVizPromptHistory.mostRecentFirst()


def test_a_run_asks_only_the_hole_nobody_answers_and_remembers_it(
        tmp_path, qapp, capsys, monkeypatch):
    asked = []

    def ask(text):
        asked.append(text)
        return '0.4'

    monkeypatch.setattr('builtins.input', ask)
    session, _ = buildSession(tmp_path, qapp)
    run('/prompt save Rho trace a {rho} de {shot}', session)
    capsys.readouterr()

    assert run('/prompt run rho', session)
    assert asked == ['  {rho} ? '], 'only the hole nobody knows is asked'
    out = capsys.readouterr().out
    assert '{rho} from you named it' in out
    assert '{shot} from this session' in out
    assert session.prompts == ['trace a 0.4 de 54924']

    # The value typed on the line is the value of the next run, and it is
    # said as such: the second run costs no typing.
    capsys.readouterr()
    assert run('/prompt run rho', session)
    assert asked == ['  {rho} ? ']
    assert '{rho} from the last value you typed for this prompt' \
        in capsys.readouterr().out


def test_a_value_on_the_line_spares_the_ask(tmp_path, qapp, capsys, monkeypatch):
    monkeypatch.setattr('builtins.input',
                        lambda *a: (_ for _ in ()).throw(
                            AssertionError('a named value asks nothing')))
    session, _ = buildSession(tmp_path, qapp)
    run('/prompt save Rho trace a {rho}', session)
    capsys.readouterr()
    assert run('/prompt run rho rho=0.85', session)
    assert '{rho} from you named it' in capsys.readouterr().out
    assert session.prompts == ['trace a 0.85']


def test_an_answer_left_empty_at_the_ask_is_not_an_answer(tmp_path, qapp,
                                                          capsys, monkeypatch):
    """The prompt is not sent with ``{rho}`` in it and not sent with a
    guess in its place: the fill refuses by name what nobody gave, and the
    turn never starts."""
    monkeypatch.setattr('builtins.input', lambda *a: '   ')
    session, _ = buildSession(tmp_path, qapp)
    run('/prompt save Rho trace a {rho}', session)
    capsys.readouterr()
    with pytest.raises(ValueError) as exc:
        run('/prompt run rho', session)
    assert '{rho}' in str(exc.value)
    assert session.prompts == []


def closedLine(text):
    raise EOFError


def test_a_closed_line_names_the_hole_still_owed(tmp_path, qapp, capsys,
                                                 monkeypatch):
    monkeypatch.setattr('builtins.input', closedLine)
    session, _ = buildSession(tmp_path, qapp)
    run('/prompt save Rho trace a {rho}', session)
    capsys.readouterr()
    with pytest.raises(ValueError) as exc:
        run('/prompt run rho', session)
    msg = str(exc.value)
    assert '{rho}' in msg and 'rho=…' in msg
    assert session.prompts == []


def test_a_word_that_is_not_a_value_is_refused_before_anything_is_asked(
        tmp_path, qapp, capsys, monkeypatch):
    monkeypatch.setattr('builtins.input',
                        lambda *a: (_ for _ in ()).throw(
                            AssertionError('nothing is asked yet')))
    session, _ = buildSession(tmp_path, qapp)
    run('/prompt save Rho trace a {rho}', session)
    capsys.readouterr()
    for line, word in (('/prompt run rho rho', 'rho'),
                       ('/prompt run rho =0.4', 'no hole before the =')):
        with pytest.raises(ValueError) as exc:
            run(line, session)
        assert word in str(exc.value)
    with pytest.raises(ValueError) as exc:
        run('/prompt run', session)
    assert 'needs the id or the name' in str(exc.value)


def test_two_open_cases_are_said_and_the_shot_is_then_asked(tmp_path, qapp,
                                                            capsys, monkeypatch):
    """Nothing is guessed between two cases: the listing says what was not
    answered, and the run asks for the value rather than picking a shot."""
    session, _ = buildSession(
        tmp_path, qapp, uris=(CASE_URI, CASE_URI.replace('54924', '112932')))
    run('/prompt save Spectro le spectrogramme du {shot}', session)
    capsys.readouterr()

    assert run('/prompt', session)
    assert '2 cases are open' in capsys.readouterr().out

    monkeypatch.setattr('builtins.input', askEveryValue('54924'))
    assert run('/prompt run spectro', session)
    assert session.prompts == ['le spectrogramme du 54924']


# --------------------------------------------------------------------- the write

def test_a_save_files_what_the_line_types_and_says_where_it_landed(
        tmp_path, qapp, capsys):
    session, _ = buildSession(tmp_path, qapp)
    assert run('/prompt save Comparaison compare {ids} de {case} '
               '--category bilan --description comparaison '
               '--variables ids=core_profiles;case=', session)
    out = capsys.readouterr().out
    assert 'comparaison ->' in out and '(personal)' in out
    assert '--category bilan' in out and '--description comparaison' in out
    assert '--variables ids=core_profiles;case=' in out

    entry = session.core.prompt_detail('comparaison')
    assert entry['text'] == 'compare {ids} de {case}'
    assert entry['variables'] == {'ids': 'core_profiles', 'case': ''}
    assert entry['category'] == 'bilan'

    capsys.readouterr()
    assert run('/prompt', session)
    listed = capsys.readouterr().out
    # A declared default is spelled in the listing, an open hole is bare.
    assert '{ids=core_profiles}' in listed and '{case}' in listed


def test_a_declared_hole_the_body_never_opens_is_refused_by_the_line(
        tmp_path, qapp):
    """The CLI hands the words to the store as typed, and the store refuses
    a declaration of a hole the text never opens: it would be asked for on
    every run and filled by nothing."""
    session, _ = buildSession(tmp_path, qapp)
    with pytest.raises(ValueError) as exc:
        run('/prompt save Comparaison compare {ids} '
            '--variables ids=core_profiles;shot=', session)
    msg = str(exc.value)
    assert '{shot}' in msg and '{ids}' in msg
    assert session.core.list_prompts()['prompts'] == []


def test_a_save_refuses_what_is_not_a_catalogue_line(tmp_path, qapp):
    session, _ = buildSession(tmp_path, qapp)
    with pytest.raises(ValueError) as exc:
        run('/prompt save', session)
    assert 'NAME TEXT' in str(exc.value)

    with pytest.raises(ValueError) as exc:
        run('/prompt save Seul --category bilan', session)
    assert 'no text to file' in str(exc.value)

    with pytest.raises(ValueError) as exc:
        run('/prompt save Seul un texte --scope equipe', session)
    assert 'equipe' in str(exc.value)

    assert session.core.list_prompts()['prompts'] == []


def test_a_shared_save_the_node_cannot_answer_is_refused_rather_than_filed(
        tmp_path, qapp, monkeypatch):
    """The CLI is not a back door: a ``--scope shared`` with no folder
    named is the same refusal the page and the panel read."""
    session, _ = buildSession(tmp_path, qapp)
    with pytest.raises(ValueError) as exc:
        run('/prompt save Equipe un texte --scope shared', session)
    assert 'SharedPromptsDir' in str(exc.value)
    assert session.core.list_prompts()['prompts'] == []


def test_a_run_of_a_prompt_the_catalogue_does_not_hold_is_refused(tmp_path,
                                                                  qapp,
                                                                  capsys):
    session, _ = buildSession(tmp_path, qapp)
    capsys.readouterr()
    with pytest.raises(ValueError) as exc:
        run('/prompt run inexistant', session)
    assert 'no prompt "inexistant"' in str(exc.value)
    assert session.prompts == []


# ----------------------------------------------------------------------- the help

def test_the_help_names_the_shapes_of_the_command():
    """``/prompt`` is a command the user has to find in ``/help``, with its
    four shapes -- the help text is what a first session reads."""
    text = commands.help_text()
    for line in ('/prompt ', '/prompt list', '/prompt show', '/prompt run',
                 '/prompt save'):
        assert line in text
