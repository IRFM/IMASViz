# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The one prompt history the web and the client share.

`test_113` pins the client's side -- a turn lands in the shared list, and
the arrows and `/history` read it back -- and `test_118` pins the panel's
(`QVizPromptHistory`). This file pins the thing that makes them the SAME
history, which none of those pins on its own: a prompt one surface ran is
recallable on another.

* a prompt the panel ran is recallable in the client -- its arrows and
  `/history`;
* a prompt the client ran is recallable on the page -- by `newest first` in
  `GET /api/history`, which is what the page's menu fills;
* a turn the page ran lands in that same list, so the panel and the client
  recall it back.

`HOME` is pointed at a test folder for the whole file (the `test_39`
pattern), so none of the surfaces reads the user's own
`~/.imasviz/agent_prompts`.
"""

import threading
import time

import pytest

from imasviz.VizAgent.llm_client import LLMClient, LLMResponse
from imasviz.VizAgent.QVizPromptHistory import QVizPromptHistory

from starlette.testclient import TestClient

from viz_cli.commands import execute, parse
from viz_cli.history import History
from viz_cli.session import Client, CliSession
from viz_web.server import buildApp
from viz_web.web_session import WebSession

CASE_URI = ('imas:hdf5?path='
            '/afs/eufus.eu/g2itmdev/user/g2lfleur/public/imasdb/west/3/54924/0')
DEAD_ENDPOINT = 'http://127.0.0.1:65531/v1'


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    """The shared list lives under `$HOME/.imasviz/agent_prompts`; the
    surfaces here must not read or write the user's own list, so the home
    they work in is the test's.
    """
    monkeypatch.setenv('HOME', str(tmp_path))


class FakeWindow:
    def sessionApi(self):
        return None

    def hide(self):
        pass


class FakeCore:
    """The handful of gestures the turns here drive: an open case and a
    window it can render. A `list_cases` the loop answers and a `plot_one`
    it draws are the two the scripted turns reach; the rest are refused by
    name, as a core that does not hold them is."""
    def __init__(self):
        self._windows = []

    def list_windows(self):
        return list(self._windows)

    def list_cases(self):
        return [{'uri': CASE_URI, 'dd_version': '3.35.0',
                 'loaded': {'equilibrium': [0]}, 'signals': 33}]

    def plot_one(self, uri, path, **kwargs):
        if any(record['key'] == 'SlicesPlot1' for record in self._windows):
            return {'window': 'SlicesPlot1'}
        self._windows.append({'kind': 'SlicesPlot', 'label': 'SlicesPlot 1',
                              'key': 'SlicesPlot1', 'visible': True,
                              'cases': []})
        return {'window': 'SlicesPlot1'}

    def screenshot(self, window):
        raise ValueError('no such window: %r' % window)


class ScriptedLLM:
    """A scripted LLM that ends a turn on a plain answer (no tool, no
    round-trip) -- enough to run a prompt through a turn and record it,
    which is what the shared list is about.
    """
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, messages, tools=None, **kwargs):
        self.calls.append(list(messages))
        if not self.responses:
            raise AssertionError('ScriptedLLM: no more scripted responses')
        return self.responses.pop(0)


def _answerLLM():
    return ScriptedLLM([LLMResponse(content='ok', finish_reason='stop')])


def buildClient(tmp_path):
    llm = Client(_answerLLM())
    return CliSession(app=None, window=FakeWindow(), core=FakeCore(),
                      llm=llm, shots_dir=str(tmp_path / 'cli'), max_turns=4)


def buildWeb(qapp, tmp_path):
    llm = Client(_answerLLM())
    session = WebSession(app=qapp, window=FakeWindow(), core=FakeCore(),
                         client=llm, shots_dir=str(tmp_path / 'web'),
                         max_turns=4)
    return session


# ------------------------------------------------------- the shared store, panel->client, client->web

def test_the_panel_prompt_is_recallable_in_the_client(tmp_path):
    """The panel is what the user types a prompt into, and the client's
    arrows are what they reach it from the terminal: the one list the
    application shares is the one both sides read, so a prompt the panel
    ran stands in the client's history. The arrows read it, and `/history`
    lists it."""
    from viz_cli.commands import parse, execute
    QVizPromptHistory.append('liste les surfaces de flux du cas')
    # The arrows read the very list the panel wrote.
    assert 'liste les surfaces de flux du cas' in History().entries
    # And /history lists it, newest first, as the one surface it shares.
    session = buildClient(tmp_path)
    assert execute(parse('/history'), session)


def test_the_client_prompt_is_recallable_in_the_web(tmp_path, qapp):
    """The client runs a turn, the page has to be able to recall the very
    prompt it asked: `GET /api/history` is newest first, and the prompt the
    client ran is in it, which is what the page's menu would put back in
    the box. This is the shared list read the way the web reads it."""
    QVizPromptHistory.append('trace la pression du cas')
    session = buildWeb(qapp, tmp_path)
    client = TestClient(buildApp(session), base_url='http://t')
    answer = client.get('/api/history')
    assert answer.status_code == 200
    prompts = answer.json()['prompts']
    assert 'trace la pression du cas' in prompts


# --------------------------------------------------------------- the /api/history route

def test_api_history_lists_newest_first(tmp_path, qapp):
    """The list the page's menu fills is newest first -- the order the
    arrows and the panel's menu read it in -- and every prompt it holds
    is there, in the run's order reversed. The one typed last answers
    first, the one first answers last.
    """
    for one in ('le premier', 'le deuxieme', 'le troisieme'):
        QVizPromptHistory.append(one)
    session = buildWeb(qapp, tmp_path)
    client = TestClient(buildApp(session), base_url='http://t')
    answer = client.get('/api/history')
    assert answer.status_code == 200
    assert answer.json()['prompts'] == ['le troisieme', 'le deuxieme',
                                        'le premier']


def test_api_history_limit_bounds_the_list(tmp_path, qapp):
    for one in ('a', 'b', 'c', 'd', 'e'):
        QVizPromptHistory.append(one)
    session = buildWeb(qapp, tmp_path)
    client = TestClient(buildApp(session), base_url='http://t')
    one = client.get('/api/history?limit=2')
    assert one.status_code == 200
    # The newest two: the limit keeps a list that is as far as the menu
    # would show, not more.
    assert one.json()['prompts'] == ['e', 'd']


def test_api_history_refuses_a_limit_that_is_not_a_number(tmp_path, qapp):
    session = buildWeb(qapp, tmp_path)
    client = TestClient(buildApp(session), base_url='http://t')
    answer = client.get('/api/history?limit=x')
    assert answer.status_code == 400
    assert 'limit' in answer.json()['error']
    assert 'number' in answer.json()['error']


def test_api_history_empty_is_an_empty_answer_not_a_refusal(tmp_path, qapp):
    """Before any surface has run a prompt, the list is empty -- the state
    the panel's menu shows. `/api/history` answers the empty list, with a
    200, not a 400: an empty history is a read, not a failure."""
    session = buildWeb(qapp, tmp_path)
    client = TestClient(buildApp(session), base_url='http://t')
    answer = client.get('/api/history')
    assert answer.status_code == 200
    assert answer.json() == {'prompts': []}


# --------------------------------------------------------------- the web records a turn

def test_a_turn_the_page_ran_is_in_the_shared_list(qapp, tmp_path):
    """A turn the page runs lands in the one list the whole application
    shares, so a prompt the user asked on the page is recallable on the
    client and the panel: the same `newest first` list, this time written
    by a page turn. Pinned through the session the page drives; the write
    is the one a `runTurn` does, before the loop runs, so even a turn that
    is later refused has already landed its prompt.

    Run the way the page runs it -- the turn on a worker thread, the
    `qapp` pumped from this one (the dispatcher the loop and its gestures
    are queued on needs the pump, and a runTurn this thread both starts
    and waits on would never be delivered).
    """
    session = buildWeb(qapp, tmp_path)
    box = {'done': threading.Event()}

    def run():
        try:
            box['v'] = session.runTurn('trace la pression du cas', onLine=None)
        finally:
            box['done'].set()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not box['done'].is_set():
        if time.time() > deadline:
            raise AssertionError(
                'pump timed out: the turn was not delivered to the `qapp`')
        qapp.processEvents()
        time.sleep(0.01)
    thread.join(timeout=5)
    record = box['v']
    assert record['error'] is None
    assert QVizPromptHistory.load() == ['trace la pression du cas']
    # And the client recalls it, newest first, through the one list the
    # whole application shares.
    session2 = buildClient(tmp_path)
    assert execute(parse('/history'), session2)
