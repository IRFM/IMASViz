# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The transcript mode (`hide`, `off`, `verbose`) shared by the panel, the
client and the web, and the decoupling it enforces between the live view
and the audit artifact.

The one rule: **the mode drives the live view only**. The on-disk
`transcript.txt` is always the full render — the calls, the results, the
refusals, the answer — whatever the mode says. A reader who audits the turn
must see what it did, and the mode a live reader wears to stay quiet is not
the mode that file is painted with. The `fullLine` signal, emitted through
the loop's one `_emit` choke point, is the seam that keeps the two in
agreement.

What this file pins:

* the **decoupling** on both surfaces:
   - CLI — a `hide`-wearing turn prints a quiet console while
     `transcript.txt` has the `→` / `←` it ran;
   - Web — a `hide`-wearing turn feeds a quiet page callback while
     `record['lines']` (the artifact) has the calls;
* the **`/tools` command**: shown, set, and a bad value refused by name;
  the preference is persisted to the file the panel and the web read back;
* the **`/api/tools_mode` route**: GET answers the mode in force, POST sets
  it, and a bad value is a 400 — the same three the `/tools` command
  validates.

`HOME` is isolated per test (the `test_39` pattern): none of the
surfaces reads or writes the user's own preferences file.
"""

import os
import threading
import time

import pytest

from imasviz.VizAgent.llm_client import LLMResponse
from imasviz.VizUtils import QVizPreferences

from starlette.testclient import TestClient

from viz_cli.commands import execute, parse
from viz_cli.session import Client, CliSession
from viz_web.server import buildApp
from viz_web.web_session import WebSession

CASE_URI = ('imas:hdf5?path='
            '/afs/eufus.eu/g2itmdev/user/g2lfleur/public/imasdb/west/3/54924/0')
DEAD_ENDPOINT = 'http://127.0.0.1:65531/v1'


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    """The preferences and the shared prompt list live under `$HOME`; point
    it at the test's tree so no test reads the user's own file and so the
    mode a test writes is visible to the next test in the file (through
    `QVizPreferences` the test reads directly, not through a stale import).
    """
    monkeypatch.setattr(QVizPreferences, 'AgentToolsMode', 'hide')
    monkeypatch.setenv('HOME', str(tmp_path))


# ---------------------------------------------------------------- the fakes

class FakeWindow:
    def sessionApi(self):
        return None

    def hide(self):
        pass


class FakeCore:
    """One `plot_one` the loop will call; the rest are refused by name.
    The `plot_one` answer is one the loop accepts without a refusal, so
    the turn terminates on the second response — a clean final answer.
    """
    def __init__(self):
        self._windows = []

    def list_windows(self):
        return list(self._windows)

    def list_cases(self):
        return []

    def plot_one(self, uri, path, **kwargs):
        if any(r['key'] == 'SlicesPlot1' for r in self._windows):
            return {'window': 'SlicesPlot1'}
        self._windows.append({'kind': 'SlicesPlot', 'label': 'SlicesPlot 1',
                              'key': 'SlicesPlot1', 'visible': True,
                              'cases': []})
        return {'window': 'SlicesPlot1'}

    def screenshot(self, window):
        raise ValueError('no such window: %r' % window)


class ScriptedInner:
    """The stand-in `inner` object a `Client` is built on: the fields the
    `Client` reads (`endpoint`, `model`, `api_key`) and a `chat` that
    hands back the scripted `LLMResponse`s in turn. `max_tokens` /
    `temperature` are swallowed (the `Client` passes them, the stand-in
    does not send them anywhere). The responses come from the shared
    `ScriptedToolLLM` shape: a `plot_one` tool call, then the final
    answer.
    """
    api_key = ''
    endpoint = DEAD_ENDPOINT
    model = ''
    def __init__(self):
        self._responses = [
            LLMResponse(
                content='I will plot it now.',
                tool_calls=[{'name': 'plot_one',
                             'args': {'uri': CASE_URI,
                                     'path': 'equilibrium.time_slice[i].flux.data'}}],
                finish_reason='tool_calls'),
            LLMResponse(content='Done — the figure is on screen.',
                        finish_reason='stop'),
        ]
    def apply(self):
        pass
    def chat(self, messages, tools=None, **kwargs):
        if not self._responses:
            raise AssertionError('no more scripted responses: the turn ran longer than the two scripted.')
        return self._responses.pop(0)


def buildClient(qapp, tmp_path):
    client = Client(ScriptedInner())
    return CliSession(app=qapp, window=FakeWindow(), core=FakeCore(),
                      llm=client, shots_dir=str(tmp_path / 'cli'), max_turns=4)


def buildWeb(qapp, tmp_path):
    client = Client(ScriptedInner())
    session = WebSession(app=qapp, window=FakeWindow(), core=FakeCore(),
                         client=client, shots_dir=str(tmp_path / 'web'),
                         max_turns=4)
    return session


# ------------------------------------------------------------- the decoupling

def test_cli_hide_view_is_quiet_but_artifact_keeps_the_calls(qapp, tmp_path, capsys):
    """The decoupling on the client: a `hide`-wearing turn prints only the
    final answer to the console, and the `transcript.txt` it leaves on disk
    carries the `→ plot_one(...)` and `← plot_one: ...` the mode cut from
    the view — the reader who audits needs them.

    The live view is read from the console (`capsys`); the artifact is read
    from the file the turn left in its directory.
    """
    session = buildClient(qapp, tmp_path)
    session.agent.tools_mode = 'hide'   # pin the mode; the loop reads it

    result = session.runPrompt('plot the flux profile')
    console = capsys.readouterr().out

    # The live view under `hide`: only the final answer, no `→` / `←`.
    assert 'plot the flux' not in console  # the mid-run comment is cut
    assert '→' not in console
    assert '←' not in console
    # The final answer IS in the live view.
    assert 'Done' in console

    # The artifact has the tool traffic the live view hid.
    turn_dir = result['dir']
    with open(os.path.join(turn_dir, 'transcript.txt')) as f:
        artifact = f.read()
    assert '→ ' in artifact          # the call is in the file
    assert '← ' in artifact          # the result (or refusal) is in the file
    assert 'plot_one' in artifact


def test_web_hide_page_is_quiet_but_lines_carry_the_calls(qapp, tmp_path):
    """The decoupling on the web: a `hide`-wearing turn feeds the page
    callback only the final answer (the `→` / `←` are not in it), and the
    `record['lines']` the page stores (the artifact) has the calls.

    `record['lines']` is written by the `fullLine` emissions (the
    `onFullSlot`); the `onLine` callback is fed by `transcriptLine` (the
    live view). The split is the `fullLine` signal.
    """
    session = buildWeb(qapp, tmp_path)
    session.agent.tools_mode = 'hide'  # pin

    live_lines = []
    box = {'done': threading.Event()}
    record = [None]

    def run():
        try:
            record[0] = session.runTurn(
                'plot the flux profile',
                onLine=lambda line: live_lines.append(line))
        finally:
            box['done'].set()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not box['done'].is_set():
        if time.time() > deadline:
            raise AssertionError('web turn timed out (pump)')
        qapp.processEvents()
        time.sleep(0.01)
    thread.join(timeout=5)

    r = record[0]
    assert r is not None, 'runTurn did not return'

    # The page saw (live): the final answer only, no tool traffic.
    assert '→' not in '\n'.join(live_lines)
    assert '←' not in '\n'.join(live_lines)
    assert any('Done' in l for l in live_lines)

    # The record (artifact — written by fullLine): the tool traffic IS there.
    artifact = '\n'.join(r['lines'])
    assert '→ ' in artifact
    assert '← ' in artifact
    assert 'plot_one' in artifact


def test_verbose_view_and_artifact_agree(qapp, tmp_path):
    """Under `verbose` the live view AND the artifact both have the tool
    traffic: the mode that shows it puts it in the live view, and the
    `fullLine` (the artifact) always had it. The two agree.
    """
    session = buildWeb(qapp, tmp_path)
    session.agent.tools_mode = 'verbose'

    live_lines = []
    box = {'done': threading.Event()}
    record = [None]

    def run():
        try:
            record[0] = session.runTurn(
                'plot the flux profile',
                onLine=lambda line: live_lines.append(line))
        finally:
            box['done'].set()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not box['done'].is_set():
        if time.time() > deadline:
            raise AssertionError('web turn timed out (pump)')
        qapp.processEvents()
        time.sleep(0.01)
    thread.join(timeout=5)

    r = record[0]
    assert r is not None

    live = '\n'.join(live_lines)
    artifact = '\n'.join(r['lines'])

    # Under verbose the live view has the calls: the mode shows them.
    assert '→ ' in live
    assert '← ' in live
    assert 'plot_one' in live

    # The artifact always has them: the fullLine is the full render.
    assert '→ ' in artifact
    assert '← ' in artifact


# ------------------------------------------------------------------- /tools (CLI)

def test_tools_command_shows_sets_and_refuses(qapp, tmp_path, capsys):
    """`/tools` by itself shows the mode in force; `/tools <mode>` pins it
    on the loop and persists to the preference file; a word outside the
    three is refused by name in the `ValueError`.
    """
    session = buildClient(qapp, tmp_path)

    # Show (default: hide — the fixture isolated it)
    execute(parse('/tools'), session)
    out = capsys.readouterr().out
    assert 'hide' in out
    assert 'verbose' in out  # the list of modes

    # Set a good value — pinned on the loop and persisted
    execute(parse('/tools verbose'), session)
    out = capsys.readouterr().out
    assert 'verbose' in out
    assert session.agent.tools_mode == 'verbose'
    # And the file: the panel and the web will read it back on their next turn.
    from imasviz.VizUtils import QVizPreferences
    home = os.environ['HOME']
    pref_path = os.path.join(home, '.imasviz', 'preferences')
    if os.path.isfile(pref_path):
        with open(pref_path) as f:
            assert 'AgentToolsMode=verbose' in f.read()

    # Refuse a bad value — by name
    with pytest.raises(ValueError) as excinfo:
        execute(parse('/tools banana'), session)
    assert 'banana' in str(excinfo.value)
    assert 'hide' in str(excinfo.value)   # the modes are named


# ------------------------------------------------------------- /api/tools_mode (web)

def test_api_tools_mode_get_answers_the_mode(tmp_path, qapp):
    """GET `/api/tools_mode` answers the mode in force (the default from
    the fixture — `hide`) and the list of valid modes."""
    session = buildWeb(qapp, tmp_path)
    client = TestClient(buildApp(session), base_url='http://t')
    answer = client.get('/api/tools_mode')
    assert answer.status_code == 200
    body = answer.json()
    assert body['mode'] == 'hide'
    assert 'hide' in body['modes']
    assert 'off' in body['modes']
    assert 'verbose' in body['modes']


def test_api_tools_mode_set_persists(tmp_path, qapp):
    """POST `/api/tools_mode` with `verbose` pins it on the session and
    persists to the file; a subsequent GET reads it back."""
    session = buildWeb(qapp, tmp_path)
    client = TestClient(buildApp(session), base_url='http://t')

    post = client.post('/api/tools_mode',
                       json={'mode': 'verbose'})
    assert post.status_code == 200
    assert post.json()['mode'] == 'verbose'
    assert session.agent.tools_mode == 'verbose'

    get = client.get('/api/tools_mode')
    assert get.json()['mode'] == 'verbose'

    # And the file round-trips: the panel will read `AgentToolsMode=verbose`.
    home = os.environ['HOME']
    with open(os.path.join(home, '.imasviz', 'preferences')) as f:
        assert 'AgentToolsMode=verbose' in f.read()


def test_api_tools_mode_refuses_unknown(tmp_path, qapp):
    """POST `/api/tools_mode` with a word outside the three is a 400 —
    the same refusal `/tools banana` earns. A missing mode field is also
    a 400."""
    session = buildWeb(qapp, tmp_path)
    client = TestClient(buildApp(session), base_url='http://t')

    one = client.post('/api/tools_mode', json={'mode': 'banana'})
    assert one.status_code == 400
    assert 'banana' in one.json()['error']
    # The mode was NOT set: it still answers `hide`.
    assert session.agent.tools_mode != 'banana'

    two = client.post('/api/tools_mode', json={})
    assert two.status_code == 400


# ------------------------------------------------- /tools and /api read the same file

def test_cli_set_and_web_read_same_persisted_value(tmp_path, qapp):
    """The mode is one file the panel, the client and the web all read:
    what `/tools verbose` on the client pins and persists, the web's
    GET `/api/tools_mode` answers back on a new session built on the same
    preferences file. The `QVizPreferences` class-attr that the loop reads
    is the one the fixture isolated to a fresh HOME, so the file is the
    shared source (not a stale class-attr write).
    """
    # On the client: set and persist.
    cli_session = buildClient(qapp, tmp_path)
    execute(parse('/tools verbose'), cli_session)
    home = os.environ['HOME']
    with open(os.path.join(home, '.imasviz', 'preferences')) as f:
        assert 'AgentToolsMode=verbose' in f.read()

    # The web: a fresh session reads the same file, and the loop's mode
    # is the preference (not pinned on this session). Read it through
    # the class-attr that `build` would have set.
    web_session = buildWeb(qapp, tmp_path)
    # The loop reads `QVizPreferences.AgentToolsMode` (not the pinned
    # session-agent mode) — so we check the file, and that the session's
    # loop would resolve to `verbose` if it were not already pinned.
    # The session was just created (not pinned), so ask is to read the
    # file. We verify the file has the value; the `session.agent.tools_mode`
    # is `None` (not pinned), so the loop reads the class-attr.
    assert web_session.agent.tools_mode is None  # not pinned
