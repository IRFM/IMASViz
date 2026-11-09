# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The routes the page talks to, answered by one `WebSession`.

Nothing here opens a socket: `starlette.testclient.TestClient` drives the
`Starlette` app `buildApp` returns, and every request that reaches a gesture
is answered the way the session answers it -- the same `callGesture` a turn
uses, so a refusal reads the same in the JSON the page prints.

What it pins, the way the shapes are refused:

* the page itself (`/` answers the HTML it ships), the health of the running
  session (`/api/health`), and the tools the page lists (`/api/tools`) --
  the same `TOOLS` table the loop offers the model;
* the agent's turn as a stream (`/api/agent`, `text/event-stream`): the
  transcript lines come down in the order the loop writes them and the images
  at the end, and an empty prompt is refused by name before a loop is built;
* a gesture by name (`/api/tool`) answered, and an argument the tool does
  not take refused by name, as `test_119` pins through `callGesture`;
* the running parameters (`/api/llm`, GET and POST), and the refusal of a
  field the client does not answer;
* one turn's history read back: the image the turn left, and the name its
  image list holds.

The one that reaches the widgets is never the route -- it is the
`GuiDispatcher`, on the GUI thread. So the request is made from a worker
thread that does not pump, and the `qapp` of the `qapp` fixture is pumped
from this thread: the mirror of the run, where uvicorn's workers call in
and `app.exec_()` is what answers them. A request made on the pumping thread
would wait on a delivery that same thread has to make, and this suite hangs --
the same shape `test_119`'s worker takes, and the reason the run is built the
way it is.
"""

import base64
import json
import os
import threading
import time

import pytest

from starlette.testclient import TestClient

from imasviz.VizAgent.llm_client import LLMResponse

from viz_web.server import buildApp
from viz_web.web_session import WebSession

PNG_1x1 = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ'
    'AAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')

CASE_URI = ('imas:hdf5?path='
            '/afs/eufus.eu/g2itmdev/user/g2lfleur/public/imasdb/west/3/54924/0')

DEAD_ENDPOINT = 'http://127.0.0.1:65531/v1'


class ScriptedLLM:
    """One scripted LLM with the running parameters `llmFields` reads off.

    A scripted `chat` (the loop's) beside the fields `/llm` asks: the same
    shape a real `Client` over a `LLMClient` answers, minus the endpoint
    call -- which a route test does not make."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.endpoint = DEAD_ENDPOINT
        self.model = 'stub'
        self.key = None
        self.temperature = 0.2
        self.max_tokens = 2048

    def chat(self, messages, tools=None, **kwargs):
        self.calls.append(list(messages))
        if not self.responses:
            raise AssertionError('ScriptedLLM: no scripted responses left')
        return self.responses.pop(0)

    def apply(self):
        # `/llm` never asks it: the fields the page can set are answered
        # without an endpoint call.
        pass


class FakeCore:
    """The handful of gestures a route answers, and the images `saveShots`
    asks, the shape `test_119`'s core carries."""

    def list_windows(self):
        return [{'kind': 'SlicesPlot', 'label': 'SlicesPlot 1',
                 'key': 'SlicesPlot1', 'visible': True, 'cases': []}]

    def screenshot(self, window):
        if window not in ('app', 'SlicesPlot1'):
            raise ValueError('no such window: %r' % window)
        return PNG_1x1

    def list_cases(self):
        return [{'uri': CASE_URI, 'dd_version': '3.35.0',
                 'loaded': {'equilibrium': [0]}, 'signals': 33}]

    def list_case_idss(self, uri):
        return [{'name': 'equilibrium', 'occurrences': [0]}]

    def get_signal(self, uri, path, **kwargs):
        return {'x': [0, 1, 2], 'y': [10, 20, 30]}

    def plot_one(self, uri, path, **kwargs):
        return {'plotted': path}

    def plot_report(self, figure_key, name=None):
        # The one half a turn test needs of the core's own
        # `plot_report`: the file under the $HOME the test names, the
        # folder its `_namedReport` resolves.
        folder = os.path.join(
            os.environ['HOME'], '.imasviz', 'reports')
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, (name or 'fake_report') + '.html')
        with open(path, 'w') as f:
            f.write('<!doctype html><title>fake</title></html>')
        return {'saved_to': path, 'traces': 3, 'window': figure_key}


class FakeWindow:
    def sessionApi(self):
        return None

    def hide(self):
        pass


def build(qapp, tmp_path, llm=None):
    llm = llm or ScriptedLLM([])
    session = WebSession(app=None, window=FakeWindow(), core=FakeCore(),
                         client=llm, shots_dir=str(tmp_path / 'shots'),
                         max_turns=8)
    return session, llm


def makeRequest(client, qapp, method, path, json=None, headers=None):
    """One request, from a worker that does not pump, while `qapp` is pumped
    from this thread -- the shape the run takes and the reason it is built
    that way. Returns the `Response`; the caller reads its status and body."""
    box = {'done': threading.Event()}

    def _work():
        try:
            box['resp'] = client.request(method, path, json=json,
                                         headers=headers)
        except BaseException as e:  # surfaced below, named
            box['e'] = e
        finally:
            box['done'].set()

    t = threading.Thread(target=_work, daemon=True)
    t.start()
    deadline = time.time() + 20.0
    while not box['done'].is_set():
        if time.time() > deadline:
            raise AssertionError('route %s %s did not answer in 20 s'
                                 % (method, path))
        qapp.processEvents()
        time.sleep(0.01)
    t.join(timeout=5)
    if 'e' in box:
        raise box['e']
    return box['resp']


def parseSSE(event_block_text):
    """The blocks `runAgent` streams, split at the `\\n\\n` the page splits on."""
    blocks = []
    for block in event_block_text.split('\n\n'):
        if not block.strip():
            continue
        event = 'message'
        data = None
        for line in block.split('\n'):
            if line.startswith('event: '):
                event = line[len('event: '):]
            elif line.startswith('data: '):
                try:
                    data = json.loads(line[len('data: '):])
                except ValueError:
                    data = line[len('data: '):]
        blocks.append((event, data))
    return blocks


# --------------------------------------------------------------------- the page

def test_index_hands_out_the_page(qapp, tmp_path):
    session, _ = build(qapp, tmp_path)
    client = TestClient(buildApp(session), base_url='http://t')
    resp = makeRequest(client, qapp, 'GET', '/')
    assert resp.status_code == 200
    assert 'text/html' in resp.headers.get('content-type', '')
    assert 'IMASViz' in resp.text
    # The tokens the page wears, and the markers a guard refuses the drift on.
    assert 'tokens:begin' in resp.text
    assert 'tokens:end' in resp.text


def test_health_answers_the_session(qapp, tmp_path):
    session, _ = build(qapp, tmp_path)
    client = TestClient(buildApp(session), base_url='http://t')
    resp = makeRequest(client, qapp, 'GET', '/api/health')
    assert resp.status_code == 200
    body = resp.json()
    assert body['ok'] is True
    assert body['turns'] == 0
    assert any(c['uri'] == CASE_URI for c in body['cases'])
    # The running parameters the page prints beside the state.
    assert body['llm']['endpoint'] == DEAD_ENDPOINT
    assert body['llm']['model'] == 'stub'


def test_tools_lists_the_tables_the_loop_offers(qapp, tmp_path):
    from imasviz.VizAgent.tools import TOOLS
    session, _ = build(qapp, tmp_path)
    client = TestClient(buildApp(session), base_url='http://t')
    resp = makeRequest(client, qapp, 'GET', '/api/tools')
    assert resp.status_code == 200
    tools = resp.json()['tools']
    assert {t['name'] for t in tools} == {t['function']['name'] for t in TOOLS}
    by_name = {t['name']: t for t in tools}
    assert 'plot_one' in by_name
    assert by_name['plot_one']['parameters']['required'] == ['uri', 'path']


# ---------------------------------------------------------------------- the agent

def test_agent_streams_the_turn_then_the_images(qapp, tmp_path):
    llm = ScriptedLLM([
        LLMResponse(tool_calls=[{'name': 'list_cases', 'args': {}}], content=''),
        LLMResponse(content='Le cas est ouvert.', finish_reason='stop'),
    ])
    session, _ = build(qapp, tmp_path, llm=llm)
    client = TestClient(buildApp(session), base_url='http://t')
    resp = makeRequest(client, qapp, 'POST', '/api/agent',
                       json={'prompt': 'liste les cas'})
    assert resp.status_code == 200
    assert 'text/event-stream' in resp.headers.get('content-type', '')

    blocks = parseSSE(resp.text)
    events = [event for event, _ in blocks]
    # One `begin`, the lines the loop wrote, one `done`.
    assert events[0] == 'begin'
    assert events[-1] == 'done'
    # The lines, in order: the gesture the loop ran and its answer, then the
    # answer the loop gives.
    data_texts = [d.get('text') for event, d in blocks if event == 'line']
    joined = '\n'.join(data_texts)
    assert 'list_cases' in joined
    assert 'Le cas est ouvert.' in joined

    # The `done` event carries the images the page draws and where they
    # live: the figure the turn drew, and not the application the turn
    # did not ask for -- the capture of a turn is its plots, the way
    # `test_119` pins it on the session.
    done = next(d for e, d in blocks if e == 'done')
    names = [im['name'] for im in done['images']]
    assert names == ['SlicesPlot1.png']
    for im in done['images']:
        assert base64.b64decode(im['b64']) == PNG_1x1
    assert done['error'] is None

    # And the session now holds the one turn the stream answered.
    assert len(session.turns) == 1


def test_agent_turn_that_writes_a_report_names_it_in_the_done_event(
        qapp, tmp_path, monkeypatch):
    """The repro the page had: a turn whose loop writes a report leaves
    the file on disk and says nothing to the page -- the `done` event
    carries the images the turn drew and now must carry the report it
    wrote, which is what the Reports section fills. Also pinned on the
    history read back, `GET /api/turns/<n>`, the key the record holds."""
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    llm = ScriptedLLM([
        LLMResponse(tool_calls=[{'name': 'plot_report',
                                 'args': {'figure_key': 'SlicesPlot1',
                                          'name': 'agent_report'}}],
                     content=''),
        LLMResponse(content='Le rapport est écrit.', finish_reason='stop'),
    ])
    session, _ = build(qapp, tmp_path, llm=llm)
    client = TestClient(buildApp(session), base_url='http://t')
    resp = makeRequest(client, qapp, 'POST', '/api/agent',
                       json={'prompt': 'écris le rapport du cas'})
    assert resp.status_code == 200

    blocks = parseSSE(resp.text)
    done = next(d for e, d in blocks if e == 'done')
    assert done['reports'] == ['agent_report.html']

    one = makeRequest(client, qapp, 'GET', '/api/turns/1')
    assert one.status_code == 200
    assert one.json()['reports'] == ['agent_report.html']


def test_agent_turn_that_writes_no_report_names_none(qapp, tmp_path, monkeypatch):
    """A turn that writes no report answers the empty list on the same
    key -- the page fills the section from `data.reports`, and a missing
    key is what it had to guess at before this."""
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    llm = ScriptedLLM([
        LLMResponse(tool_calls=[{'name': 'list_cases', 'args': {}}], content=''),
        LLMResponse(content='Le cas est ouvert.', finish_reason='stop'),
    ])
    session, _ = build(qapp, tmp_path, llm=llm)
    client = TestClient(buildApp(session), base_url='http://t')
    resp = makeRequest(client, qapp, 'POST', '/api/agent',
                       json={'prompt': 'liste les cas'})
    assert resp.status_code == 200
    blocks = parseSSE(resp.text)
    done = next(d for e, d in blocks if e == 'done')
    assert done['reports'] == []


def test_agent_refuses_an_empty_prompt_by_name(qapp, tmp_path):
    session, _ = build(qapp, tmp_path)
    client = TestClient(buildApp(session), base_url='http://t')
    resp = makeRequest(client, qapp, 'POST', '/api/agent', json={'prompt': '   '})
    assert resp.status_code == 400
    assert 'no prompt' in resp.json()['error']
    # Nothing was built: no turn was started, and therefore no loop ran.
    assert session.turns == []


def test_agent_stop_is_answered(qapp, tmp_path):
    session, _ = build(qapp, tmp_path)
    client = TestClient(buildApp(session), base_url='http://t')
    resp = makeRequest(client, qapp, 'POST', '/api/agent/stop')
    assert resp.status_code == 200
    assert 'stop' in resp.json()


# ---------------------------------------------------------------------- one tool

def test_tool_answers_a_gesture(qapp, tmp_path):
    session, _ = build(qapp, tmp_path)
    client = TestClient(buildApp(session), base_url='http://t')
    resp = makeRequest(client, qapp, 'POST', '/api/tool',
                       json={'name': 'get_signal',
                             'args': {'uri': CASE_URI,
                                      'path': 'equilibrium.time'}})
    assert resp.status_code == 200
    body = resp.json()
    assert body['name'] == 'get_signal'
    assert body['result']['y'] == [10, 20, 30]


def test_tool_refuses_no_name_by_name(qapp, tmp_path):
    session, _ = build(qapp, tmp_path)
    client = TestClient(buildApp(session), base_url='http://t')
    resp = makeRequest(client, qapp, 'POST', '/api/tool', json={'args': {}})
    assert resp.status_code == 400
    assert 'name' in resp.json()['error']


def test_tool_refuses_an_unknown_parameter_by_name(qapp, tmp_path):
    session, _ = build(qapp, tmp_path)
    client = TestClient(buildApp(session), base_url='http://t')
    resp = makeRequest(client, qapp, 'POST', '/api/tool',
                       json={'name': 'plot_one',
                             'args': {'uri': CASE_URI, 'path': 'x',
                                      'timeindex': 7}})
    assert resp.status_code == 400
    body = resp.json()
    assert 'timeindex' in body['error']
    # The names it holds, the way `test_119`'s `callGesture` refusal reads.
    for allowed in ('uri', 'path', 'along_time'):
        assert allowed in body['error']


# --------------------------------------------------------------------- reports

def test_reports_route_lists_the_folder_by_name(qapp, tmp_path, monkeypatch):
    """`GET /api/reports` -- the section the page fills at load and
    after every request: what the reports folder holds, by name,
    whatever turn or session wrote it (the page reload was losing
    exactly that), and the folder it came from -- the page names it, so
    a report the user asked for that is not among the names is one a
    tool did not write there. The folder the core's `_namedReport`
    resolves is under $HOME, so the test points HOME at its own tree;
    the state before the core's first write -- no folder -- is the empty
    list, not a 500 the page would have to read as failure; and a
    subdirectory is not a report, so it is not among the names."""
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    session, _ = build(qapp, tmp_path)
    client = TestClient(buildApp(session), base_url='http://t')

    resp = makeRequest(client, qapp, 'GET', '/api/reports')
    assert resp.status_code == 200
    body = resp.json()
    assert body['reports'] == []
    # The folder, named so the page can say where a report either is or
    # is not.
    expected_folder = os.path.realpath(
        os.path.join(str(tmp_path / 'home'), '.imasviz', 'reports'))
    assert body['folder'] == expected_folder

    folder = os.path.join(str(tmp_path / 'home'), '.imasviz', 'reports')
    os.makedirs(folder)
    for name in ('old_report.html', 'a_report.html'):
        with open(os.path.join(folder, name), 'w') as f:
            f.write('<!doctype html>')
    # A place, not a report: the listing keeps the files.
    os.makedirs(os.path.join(folder, 'a_folder'))
    resp = makeRequest(client, qapp, 'GET', '/api/reports')
    assert resp.status_code == 200
    # By name, and one name per file -- the section is the folder.
    assert resp.json() == {
        'folder': expected_folder,
        'reports': ['a_report.html', 'old_report.html']}


def test_report_route_serves_the_file_and_names_the_absent(
        qapp, tmp_path, monkeypatch):
    """`GET /api/reports/<name>` serves the file as HTML (the section's
    links are to it), and a name the folder does not hold is refused by
    name, in the words the route's sibling routes use -- a path a name
    cannot hold is refused where the page reads it, before it is
    resolved."""
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    folder = os.path.join(str(tmp_path / 'home'), '.imasviz', 'reports')
    os.makedirs(folder)
    with open(os.path.join(folder, 'served.html'), 'w') as f:
        f.write('<!doctype html><h1>bonjour</h1>')
    session, _ = build(qapp, tmp_path)
    client = TestClient(buildApp(session), base_url='http://t')

    resp = makeRequest(client, qapp, 'GET', '/api/reports/served.html')
    assert resp.status_code == 200
    assert 'text/html' in resp.headers.get('content-type', '')
    assert '<h1>bonjour</h1>' in resp.text

    missing = makeRequest(client, qapp, 'GET', '/api/reports/absent.html')
    assert missing.status_code == 404
    assert 'absent.html' in missing.json()['error']


# ------------------------------------------------------------------------ /llm

def test_llm_get_reports_the_running_parameters(qapp, tmp_path):
    session, llm = build(qapp, tmp_path)
    client = TestClient(buildApp(session), base_url='http://t')
    resp = makeRequest(client, qapp, 'GET', '/api/llm')
    assert resp.status_code == 200
    body = resp.json()
    assert body['endpoint'] == DEAD_ENDPOINT
    assert body['model'] == 'stub'
    assert body['key'] is False
    assert body['max_turns'] == 8
    assert 'temperature' in body and 'max_tokens' in body


def test_llm_set_max_turns(qapp, tmp_path):
    session, _ = build(qapp, tmp_path)
    client = TestClient(buildApp(session), base_url='http://t')
    resp = makeRequest(client, qapp, 'POST', '/api/llm',
                       json={'field': 'max_turns', 'value': 3})
    assert resp.status_code == 200
    assert session.max_turns == 3
    assert resp.json()['max_turns'] == 3


def test_llm_set_refuses_a_field_the_client_does_not_answer(qapp, tmp_path):
    session, _ = build(qapp, tmp_path)
    client = TestClient(buildApp(session), base_url='http://t')
    resp = makeRequest(client, qapp, 'POST', '/api/llm',
                       json={'field': 'banana', 'value': 1})
    assert resp.status_code == 400
    assert 'banana' in resp.json()['error']


def test_llm_set_max_turns_refused_when_below_the_floor(qapp, tmp_path):
    session, _ = build(qapp, tmp_path)
    client = TestClient(buildApp(session), base_url='http://t')
    resp = makeRequest(client, qapp, 'POST', '/api/llm',
                       json={'field': 'max_turns', 'value': 0})
    assert resp.status_code == 400
    # Named the way the loop's own floor is named: the value, and the
    # range it takes -- not a silence the page has to guess at.
    assert '0' in resp.json()['error']


# ---------------------------------------------------------------------- the turns

def test_turn_history_and_shot_read_back(qapp, tmp_path):
    llm = ScriptedLLM([
        LLMResponse(tool_calls=[{'name': 'list_cases', 'args': {}}], content=''),
        LLMResponse(content='Le cas est ouvert.', finish_reason='stop'),
    ])
    session, _ = build(qapp, tmp_path, llm=llm)
    client = TestClient(buildApp(session), base_url='http://t')
    makeRequest(client, qapp, 'POST', '/api/agent', json={'prompt': 'liste'})

    # The one turn, with the two images it left.
    listing = makeRequest(client, qapp, 'GET', '/api/turns').json()
    assert len(listing['turns']) == 1
    assert 'SlicesPlot1.png' in listing['turns'][0]['image_files']

    one = makeRequest(client, qapp, 'GET', '/api/turns/1')
    assert one.status_code == 200
    assert one.json()['n'] == 1

    # The image the turn drew, read back as the bytes it is.
    shot = makeRequest(client, qapp, 'GET', '/api/turns/1/shots/SlicesPlot1.png')
    assert shot.status_code == 200
    assert shot.content == PNG_1x1
    assert 'image/png' in shot.headers.get('content-type', '')

    # The one it refuses, by name: this turn holds no such image.
    missing = makeRequest(client, qapp, 'GET', '/api/turns/1/shots/none.png')
    assert missing.status_code == 404

    # And a turn the session does not hold.
    ghost = makeRequest(client, qapp, 'GET', '/api/turns/9')
    assert ghost.status_code == 404
