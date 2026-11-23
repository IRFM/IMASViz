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

"""The prompt catalogue on the page -- and the route that does not exist.

The catalogue has no route of its own: the page's Prompts section is
``POST /api/tool {name, args}`` with one of the six tool names, exactly the
call the agent's own tools make, so the page, the panel, the CLI and the
model read and write one catalogue. ``viz_web/server.py`` grows no endpoint
for it and ``WebSession`` no method: ``callGesture`` runs
``AgentLoop._dispatch``, which resolves the name on the core and refuses by
name an argument the tool does not offer. Hence the requests here are driven
the way ``test_120`` drives them -- the request from a worker that does not
pump, ``qapp`` pumped from this thread -- because a gesture goes through the
GUI-thread dispatcher and a thread that never pumps gets the 300 s answer.

What is pinned:

* the **page** carries the section, its two asks, and the six tool names it
  spells -- a name the page spells that no tool offers is a click that
  answers nothing;
* the **listing** a reload of that section gets: the lines, the category
  counts, and the ``context`` saying what this session would answer for free;
* the **preview** of one prompt: its body and, per hole, where today's value
  would come from -- the open case's shot included, which is what the form's
  ``filled from this session`` label stands on;
* the **fill**: the shot goes into the text, and a hole nobody answered comes
  back as a refusal naming it, not as a prompt with ``{shot}`` still in it;
* the **write**: the text of a turn filed, read back, edited, deleted;
* the **half that is missing**: a shared catalogue with no folder named is
  said in the answer, and a parameter the tool does not offer is refused
  before it reaches the core.
"""

import os
import threading
import time

import pytest

from imasviz.VizAgent.core import McpGuiCore

from starlette.testclient import TestClient

from viz_web.server import buildApp
from viz_web.web_session import WebSession

CASE_URI = ('imas:hdf5?path='
            '/afs/eufus.eu/g2itmdev/user/g2lfleur/public/imasdb/west/3/54924/0')
PAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'viz_web', 'static', 'index.html')

PROMPT_TOOLS = ('list_prompts', 'prompt_detail', 'fill_prompt', 'save_prompt',
                'edit_prompt', 'delete_prompt')


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
    def sessionApi(self):
        return None

    def hide(self):
        pass


def _core(uris=(CASE_URI,)):
    """The real core, on a session whose one open case is spelled by a URI:
    the catalogue gestures ask nothing of a window, and the case values come
    off the URI, so no Access Layer is reached."""
    made = McpGuiCore.__new__(McpGuiCore)
    made.api = _Api(list(uris))
    made.list_windows = lambda: []
    return made


class _NoCall:
    """The endpoint stand-in: only gestures run here, so a chat call is a
    failure of the test rather than a request out."""
    endpoint = 'http://127.0.0.1:65531/v1'
    model = 'unused'
    api_key = ''

    def chat(self, messages, tools=None, **kwargs):
        raise AssertionError('no turn runs in this file')


def _pumped(qapp, work):
    """The `test_120` shape: the request runs on a worker that does not pump
    events, this thread pumps them, so a gesture the dispatcher hands to the
    GUI thread is served instead of timing out."""
    box = {'done': threading.Event()}

    def _run():
        try:
            box['resp'] = work()
        except BaseException as e:
            box['e'] = e
        finally:
            box['done'].set()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    deadline = time.time() + 30.0
    while not box['done'].is_set():
        if time.time() > deadline:
            raise AssertionError('the page request did not answer in 30 s')
        qapp.processEvents()
        time.sleep(0.01)
    thread.join(timeout=5)
    if 'e' in box:
        raise box['e']
    return box['resp']


class _Page:
    """The page's two asks: a tool by name, and a route."""

    def __init__(self, http, qapp):
        self.http = http
        self.qapp = qapp

    def tool(self, name, args=None):
        return _pumped(self.qapp, lambda: self.http.post(
            '/api/tool', json={'name': name, 'args': args or {}}))

    def get(self, path):
        return _pumped(self.qapp, lambda: self.http.get(path))


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    monkeypatch.setattr('imasviz.VizUtils.QVizPreferences.SharedPromptsDir',
                        '', raising=False)
    return tmp_path


def _web(tmp_path, qapp, uris=(CASE_URI,)):
    from viz_cli.session import Client
    session = WebSession(app=None, window=FakeWindow(), core=_core(uris),
                         client=Client(_NoCall()),
                         shots_dir=str(tmp_path / 'web'), max_turns=4)
    return _Page(TestClient(buildApp(session), base_url='http://t'), qapp)


# --------------------------------------------------------------------- the page

def test_the_page_holds_a_catalogue_section():
    page = open(PAGE, encoding='utf-8').read()
    for element in ('id="prompts"', 'id="promptsStats"', 'id="promptsTabs"',
                    'id="promptsChips"', 'id="promptsList"',
                    'id="promptRun"', 'id="promptForm"'):
        assert element in page, 'the page has no %s' % element
    assert '<h2>Prompts</h2>' in page


def test_the_page_asks_the_catalogue_by_its_six_tool_names():
    """A page that spells a name no tool offers is a click that answers
    nothing, and the loop's refusal is all the user ever sees. The two
    writes share one ask: the page picks which one by what it is editing."""
    page = open(PAGE, encoding='utf-8').read()
    for name in PROMPT_TOOLS:
        assert ("'%s'" % name) in page, 'the page never spells %s' % name
    assert "var tool = promptsEditing ? 'edit_prompt' : 'save_prompt';" \
        in page
    assert 'notesFetch(tool, args)' in page
    asked = [one for one in PROMPT_TOOLS if ("notesFetch('%s'" % one) in page]
    assert asked == ['list_prompts', 'prompt_detail', 'fill_prompt',
                     'delete_prompt']


def test_the_page_fills_the_box_and_can_run_what_it_filled():
    """The two asks of a catalogue entry, and the one thing the page does not
    do on its own: it puts the filled text in the prompt box, and only the
    *Run* ask sends it as a turn."""
    page = open(PAGE, encoding='utf-8').read()
    assert "byId('prompt').value = r.text;" in page
    assert 'if (thenRun) runAgent(r.text);' in page
    assert "['Put in the box']" in page
    assert "'Save as prompt'" in page


def test_the_page_names_where_each_value_came_from():
    """A value the user did not type is a value they are shown the source
    of."""
    page = open(PAGE, encoding='utf-8').read()
    assert "'} from ' + r.values[name].source" in page
    assert 'filled from' in page


# ------------------------------------------------------------------ the listing

def test_the_listing_is_the_catalogue_the_store_reads(home, tmp_path, qapp):
    page = _web(tmp_path, qapp)
    filed = page.tool('save_prompt',
                      {'name': 'Profils 1D', 'text': 'trace {ids} de {shot}',
                       'category': 'profils', 'description': 'une ligne',
                       'variables': 'ids=core_profiles; shot='})
    assert filed.status_code == 200
    page.tool('save_prompt', {'name': 'Bilan', 'text': 'le bilan'})

    answer = page.tool('list_prompts')
    assert answer.status_code == 200
    result = answer.json()['result']
    assert result['total'] == 2
    assert result['categories'] == {'profils': 1, '': 1}
    assert [one['id'] for one in result['prompts']] == ['profils-1d', 'bilan']
    line = result['prompts'][0]
    assert line['scope'] == 'personal' and line['holes'] == ['ids', 'shot']
    assert 'text' not in line
    assert result['context']['shot'] == '54924'
    assert 'SharedPromptsDir' in result['catalogues_unavailable']['shared']


def test_a_narrowed_listing_and_a_cut_one_are_both_said(home, tmp_path, qapp):
    page = _web(tmp_path, qapp)
    for n in range(3):
        page.tool('save_prompt', {'name': 'Prompt %d' % n,
                                  'text': 'un %d' % n})
    names = [one['name'] for one in
             page.tool('list_prompts', {'query': 'Prompt 2'})
             .json()['result']['prompts']]
    assert names == ['Prompt 2']
    cut = page.tool('list_prompts', {'limit': 1}).json()['result']
    assert cut['total'] == 3 and len(cut['prompts']) == 1
    assert '1 of 3 prompts are answered' in cut['truncated']


# ------------------------------------------------------------------- the preview

def test_the_preview_says_where_todays_value_would_come_from(home, tmp_path,
                                                             qapp):
    page = _web(tmp_path, qapp)
    page.tool('save_prompt', {'name': 'Trois trous',
                              'text': 'trace {ids} de {shot} à {rho}',
                              'variables': 'ids=core_profiles; shot='})
    detail = page.tool('prompt_detail', {'name': 'Trois trous'})
    assert detail.status_code == 200
    result = detail.json()['result']
    assert result['text'] == 'trace {ids} de {shot} à {rho}'
    values = result['values']
    assert values['ids'] == {'value': 'core_profiles',
                             'source': "the prompt's own default"}
    assert values['shot'] == {'value': '54924', 'source': 'this session'}
    assert values['rho'] == {'value': None, 'source': None}


def test_the_preview_of_a_name_the_catalogue_does_not_hold_is_a_refusal(
        home, tmp_path, qapp):
    page = _web(tmp_path, qapp)
    answer = page.tool('prompt_detail', {'name': 'inexistant'})
    assert answer.status_code == 400
    assert 'no prompt "inexistant"' in answer.json()['error']


# ---------------------------------------------------------------------- the fill

def test_the_fill_puts_the_open_shot_in_the_text(home, tmp_path, qapp):
    page = _web(tmp_path, qapp)
    page.tool('save_prompt', {'name': 'Spectro',
                              'text': 'le spectrogramme du {shot}',
                              'variables': 'shot='})
    answer = page.tool('fill_prompt', {'name': 'Spectro'})
    assert answer.status_code == 200
    result = answer.json()['result']
    assert result['text'] == 'le spectrogramme du 54924'
    assert result['values']['shot']['source'] == 'this session'


def test_two_open_cases_are_said_rather_than_one_of_them_guessed(home, tmp_path,
                                                                qapp):
    page = _web(tmp_path, qapp,
                uris=(CASE_URI, CASE_URI.replace('54924', '112932')))
    page.tool('save_prompt', {'name': 'Spectro',
                              'text': 'le spectrogramme du {shot}',
                              'variables': 'shot='})
    answer = page.tool('fill_prompt', {'name': 'Spectro'})
    assert answer.status_code == 400
    assert 'nobody answered' in answer.json()['error']
    context = page.tool('list_prompts').json()['result']['context']
    assert '2 cases are open' in context['note']
    assert 'shot' not in context


def test_a_hole_nobody_answered_refuses_the_fill_from_the_page(home, tmp_path,
                                                              qapp):
    page = _web(tmp_path, qapp)
    page.tool('save_prompt', {'name': 'Rho', 'text': 'trace à {rho}'})
    answer = page.tool('fill_prompt', {'name': 'Rho'})
    assert answer.status_code == 400
    assert '{rho}' in answer.json()['error']
    # Typed from the form, the same fill answers.
    filled = page.tool('fill_prompt', {'name': 'Rho',
                                       'values': {'rho': '0.4'}})
    assert filled.status_code == 200
    assert filled.json()['result']['text'] == 'trace à 0.4'
    again = page.tool('prompt_detail', {'name': 'Rho'}).json()['result']
    assert again['values']['rho'] == {'value': '0.4',
                                      'source': 'the last value you typed '
                                                'for this prompt'}


# -------------------------------------------------------- the writes a page makes

def test_a_turn_of_the_page_can_be_filed_read_back_edited_and_deleted(
        home, tmp_path, qapp):
    page = _web(tmp_path, qapp)
    filed = page.tool('save_prompt',
                      {'name': 'Comparaison',
                       'text': 'compare {ids} de {case} avec la figure '
                               '{figure}',
                       'category': 'bilan',
                       'description': 'une comparaison'}).json()['result']
    assert filed['holes'] == ['ids', 'case', 'figure']
    assert filed['variables'] == {'ids': '', 'case': '', 'figure': ''}

    edited = page.tool('edit_prompt',
                       {'name': 'Comparaison', 'text': 'compare {ids}',
                        'variables': 'ids=core_profiles'})
    assert edited.status_code == 200
    assert edited.json()['result']['id'] == filed['id']
    assert edited.json()['result']['holes'] == ['ids']

    gone = page.tool('delete_prompt', {'name': 'Comparaison'})
    assert gone.json()['result'] == {'deleted': filed['id'],
                                     'scope': 'personal', 'path': filed['path']}
    assert page.tool('list_prompts').json()['result']['prompts'] == []


def test_a_shared_write_the_node_cannot_answer_is_refused_where_the_page_reads_it(
        home, tmp_path, qapp):
    page = _web(tmp_path, qapp)
    answer = page.tool('save_prompt', {'name': 'Équipe', 'text': 'un',
                                       'scope': 'shared'})
    assert answer.status_code == 400
    assert 'SharedPromptsDir' in answer.json()['error']
    assert page.tool('list_prompts').json()['result']['prompts'] == []


# ------------------------------------------------------------------- the guards

def test_a_parameter_the_tool_does_not_offer_is_refused_before_the_core(
        home, tmp_path, qapp):
    """The tool schema is the contract: the page cannot reach a core method
    with a word the tool never offered."""
    page = _web(tmp_path, qapp)
    answer = page.tool('fill_prompt', {'name': 'x', 'coucou': 'y'})
    assert answer.status_code == 400
    assert 'coucou' in answer.json()['error']


def test_the_six_names_are_the_tools_the_page_is_offered(home, tmp_path, qapp):
    page = _web(tmp_path, qapp)
    offered = {one['name'] for one in page.get('/api/tools').json()['tools']}
    assert set(PROMPT_TOOLS) <= offered
