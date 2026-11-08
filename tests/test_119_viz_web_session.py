# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""`WebSession`: the stack of one web turn, on stand-ins.

What it pins, in the order the session must answer:

* one answered turn: the transcript lines in the order the loop writes
  them, the app and its windows as PNGs with the base64 the page needs to
  draw them, and the transcript the turn leaves on disk;
* a refused turn: the refusal **named**, and the images **still** captured
  -- not a silence the user reads as a failure;
* the context survives between two turns of one session: the second chat
  is asked with the first exchange, as `test_113` pins for the REPL;
* the gesture the page asks of the core (`callGesture`) runs through the
  same `AgentLoop._dispatch` the loop uses -- so a name the core does not
  answer, and an argument the tool does not take, are refused by name the
  way `test_116`/`test_117` pin for the loop;
* a turn at a time: two concurrent `runTurn`s do not interleave, the lock
  is what keeps them serial, the way the REPL is serial;
* an empty prompt is refused by name before anything is built.

Nothing here drives a real case, a real model, or a real web socket:
the scripted LLM answers a gesture and a line, the FakeCore answers a PNG
for the app and its one window, and the event loop is the `qapp` of the
`qapp` fixture pumped from this thread -- the same shape `test_112` runs
for the one-shot.
"""

import base64
import threading
import time

import pytest

from imasviz.VizAgent.llm_client import LLMClient, LLMResponse

from viz_cli.session import Client
from viz_web.web_session import WebSession

PNG_1x1 = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ'
    'AAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')

CASE_URI = ('imas:hdf5?path='
            '/afs/eufus.eu/g2itmdev/user/g2lfleur/public/imasdb/west/3/54924/0')

DEAD_ENDPOINT = 'http://127.0.0.1:65531/v1'


class FakeLLMClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, messages, tools=None, **kwargs):
        self.calls.append(list(messages))
        if not self.responses:
            raise AssertionError('FakeLLMClient: no scripted responses left')
        return self.responses.pop(0)


class FakeCore:
    """A core that answers PNGs and the handful of gestures the tests
    drive: the session's bookkeeping, the tree it serves, and the values
    `describe_node` / `get_signal` / `list_cases` the page reads."""

    def __init__(self):
        self.saved = []
        self.restored = []

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

    def save_session(self, name=None, path=None):
        self.saved.append(name)
        return {'saved_to': '/preferences/%s.vsess' % name}

    def get_signal(self, uri, path, **kwargs):
        return {'x': [0, 1, 2], 'y': [10, 20, 30]}

    def plot_one(self, uri, path, **kwargs):
        # Present so a gesture by the tool's own name reaches the loop's
        # unknown-parameter guard; the guard refuses before the body runs.
        return {'plotted': path}


class FakeWindow:
    def sessionApi(self):
        return None

    def hide(self):
        pass


def build(qapp, tmp_path, llm=None, core=None, max_turns=8):
    llm = llm or Client(LLMClient(endpoint=DEAD_ENDPOINT, model='stub', timeout=2.0))
    core = core or FakeCore()
    session = WebSession(app=None, window=FakeWindow(), core=core,
                         client=llm,
                         shots_dir=str(tmp_path / 'shots'),
                         max_turns=max_turns)
    return session, core


def pumpUntil(qapp, condition, timeout=15.0):
    """Pump `qapp` from this thread until `condition()` answers.

    The pump exists for the dispatcher, not the loop's signals: the loop
    (`AgentLoop`) and the gestures build their turn around a `GuiDispatcher`
    that runs on this thread, and that dispatcher is a *queued* signal --
    `qapp.processEvents()` is what drains it and lets the worker's
    `dispatcher.call` answer. The loop's own two `Signal`s
    (`transcriptLine`, `askFinished`) are connected with
    `Qt.DirectConnection` by `WebSession.runTurn` because a queued emission
    would be posted to the loop of the thread the *connect* was made on
    (here a worker thread whose loop nothing ever runs), and the turn would
    hang with the loop already finished. A run that runs longer than
    `timeout` is a hang, and the timeout is named rather than waiting for
    the whole pytest cap."""
    deadline = time.time() + timeout
    while not condition():
        if time.time() > deadline:
            raise AssertionError(
                'pump timed out after %.0f s: the worker did not finish '
                'in the window; the dispatcher was not delivered' % timeout)
        qapp.processEvents()
        time.sleep(0.01)


def inWorker(target, qapp, timeout=15.0):
    """Run `target()` on a worker thread, pumping `qapp` from this thread
    until it returns. This mirrors the shape of the page: the page is the
    worker, a pump thread (the main thread of the run, here this one) keeps
    the event loop, and the two never block each other.

    Returns the value `target()` returns, or raises its exception.
    """
    box = {'done': threading.Event()}
    def _w():
        try:
            box['v'] = target()
        except BaseException as e:
            box['e'] = e
        finally:
            box['done'].set()
    t = threading.Thread(target=_w, daemon=True)
    t.start()
    pumpUntil(qapp, lambda: box['done'].is_set(), timeout=timeout)
    t.join(timeout=5)
    if 'e' in box:
        raise box['e']
    return box.get('v')


# ------------------------------------------------------------------- turns

def test_an_answered_turn_leaves_lines_images_and_transcript(qapp, tmp_path):
    """An answered loop: the lines in the order the loop writes them, the
    app and the figure on disk as PNGs (with the base64 the page needs to
    draw them), the transcript beside them on disk."""
    llm = FakeLLMClient([
        LLMResponse(tool_calls=[{'name': 'list_cases', 'args': {}}], content=''),
        LLMResponse(content='Le cas est ouvert.', finish_reason='stop'),
    ])
    session, core = build(qapp, tmp_path, llm=llm)
    record = inWorker(lambda: session.runTurn('liste les cas ouverts'), qapp)

    text = '\n'.join(record['lines'])
    assert 'Le cas est ouvert.' in text
    assert 'list_cases' in text
    assert 'LLM: Le cas est ouvert.' in record['lines'][-1]

    # The images are on disk under a directory the session names, and their
    # base64 is in the record -- the `data:` URI the page draws from.
    assert record['dir'].startswith(str(tmp_path / 'shots'))
    assert '00_app.png' in record['image_files']
    assert 'SlicesPlot1.png' in record['image_files']
    app_png = next(im for im in record['images'] if im['name'] == '00_app.png')
    assert base64.b64decode(app_png['b64']) == PNG_1x1
    assert (tmp_path / 'shots' / record['dir'].split('shots/')[-1] / '00_app.png').is_file()

    # Every picture is also an address: the name the page's Focus and
    # Screenshot buttons send to focus_window and get_screenshot.
    by_file = {entry['name']: entry for entry in record['image_windows']}
    assert by_file['00_app.png']['window'] == 'app'
    assert by_file['SlicesPlot1.png']['window'] == 'SlicesPlot1'
    # The base64 the page draws carries the address with it.
    assert app_png['window'] == 'app'


def test_a_refused_turn_is_named_and_still_saves(qapp, tmp_path):
    """The refusal (the truncation here) is not a silence: it is in the
    record's error and the transcript, and the turn still leaves its images
    on disk -- the shape `test_112` pins for the one-shot and `test_113`
    pins for the REPL."""
    llm = FakeLLMClient([
        LLMResponse(content='partial...', finish_reason='length'),
    ])
    session, core = build(qapp, tmp_path, llm=llm)
    record = inWorker(lambda: session.runTurn('une requete trop longue'), qapp)
    assert record['error'] is not None
    text = '\n'.join(record['lines'])
    assert 'REFUSAL' in text
    assert 'truncated' in text
    assert record['image_files']   # the images still come


def test_max_turns_stops_the_loop_and_names_it(qapp, tmp_path):
    """The turn stops at the loop's limit, the record names it, and the
    limit is what is named -- not the number of responses the stand-in held
    (here 6, four more than the limit of 2, so a loop that does not stop
    would run them off and the record would carry no error at all)."""
    llm = FakeLLMClient(
        [LLMResponse(tool_calls=[{'name': 'list_cases', 'args': {}}], content='')
         for _ in range(6)])
    session, core = build(qapp, tmp_path, llm=llm, max_turns=2)
    record = inWorker(lambda: session.runTurn('une demande qui ne s''arrête pas'), qapp)
    assert record['error'] is not None
    assert 'max_turns' in record['error']
    # Two turns went, so the scripted LLM kept four.
    assert len(llm.responses) == 4
    # The last action -- the gesture that ran when the budget ran out -- is
    # named in the stop, so the run reads as delivered-and-limited, not failed.
    assert 'list_cases' in record['error']


def test_the_context_survives_between_two_turns(qapp, tmp_path):
    """What a fresh loop per turn could not give: the second turn is
    asked with the first exchange -- its user line and its answer.
    `test_113` pins the same rule for the REPL; this pins it for the session
    the page drives."""
    llm = FakeLLMClient([
        LLMResponse(tool_calls=[{'name': 'list_cases', 'args': {}}], content=''),
        LLMResponse(content='Premier : le cas est ouvert.', finish_reason='stop'),
        LLMResponse(tool_calls=[{'name': 'list_cases', 'args': {}}], content=''),
        LLMResponse(content='Deuxieme : toujours le meme cas.', finish_reason='stop'),
    ])
    session, core = build(qapp, tmp_path, llm=llm)
    r1 = inWorker(lambda: session.runTurn('ouvre le cas de reference'), qapp)
    assert r1['error'] is None
    r2 = inWorker(lambda: session.runTurn('et maintenant le suivant'), qapp)
    assert r2['error'] is None
    # The chat of the second turn is the fifth call: the first turn consumed
    # two (the tool and its answer); the tool then runs again before the
    # second stops.
    second = llm.calls[2]
    contents = [m.get('content') or '' for m in second]
    assert any('et maintenant le suivant' in c for c in contents)
    assert any('Premier : le cas est ouvert.' in c for c in contents)
    assert any('ouvre le cas de reference' in c for c in contents)


# --------------------------------------------------------------- gestures

def test_call_gesture_returns_the_core_value(qapp, tmp_path):
    """The page asks the core a gesture by its tool name, and the value it
    answers comes back. This is the same `AgentLoop._dispatch` the loop
    uses, so an answer of `{'x':…,'y':…}` from `get_signal` is what the
    page prints, not a type error."""
    session, core = build(qapp, tmp_path)
    out = inWorker(lambda: session.callGesture('get_signal',
                                               {'uri': CASE_URI, 'path': 'equilibrium.time'}),
                   qapp)
    assert out['error'] is None
    assert out['result']['y'] == [10, 20, 30]


def test_call_gesture_refuses_an_unknown_tool_by_name(qapp, tmp_path):
    """A name the core does not answer is named where the page reads it,
    the way `test_116` pins for the loop. The refusal reads the same in
    the JSON the page prints as in the transcript a turn leaves."""
    session, _ = build(qapp, tmp_path)
    out = inWorker(lambda: session.callGesture('banana', {'uri': CASE_URI}), qapp)
    assert out['error'] is not None
    assert 'banana' in out['error']
    assert 'not a gesture' in out['error'] or 'core' in out['error'].lower()


def test_call_gesture_refuses_an_unknown_parameter_by_name(qapp, tmp_path):
    """An argument a tool does not take is named, with the names it does
    hold -- the same guard the agent's path takes, because `callGesture`
    runs the loop's `_dispatch`. The page reads the reason, and the gesture
    is not run."""
    from imasviz.VizAgent.tools import TOOLS
    plot_one = next(t for t in TOOLS if t['function']['name'] == 'plot_one')
    allowed = list(plot_one['function']['parameters']['properties'])
    session, _ = build(qapp, tmp_path)
    out = inWorker(lambda: session.callGesture(
        'plot_one', {'uri': CASE_URI, 'path': 'x', 'timeindex': 7}), qapp)
    assert out['error'] is not None
    assert 'timeindex' in out['error']
    for name in allowed:
        assert name in out['error']


# ------------------------------------------------------------- serialization

def test_one_turn_at_a_time_serialized(qapp, tmp_path):
    """Two turns at once run one after the other, not interleaved on the
    one shared tree. The scripted LLM answers one line per turn; if the
    two were to interleave, the order of its calls would not match the
    order of the turns' lines, and the two transcripts would bleed.
    `test_112` pins the seriality of the one-shot by one prompt at a time;
    this pins it of two on the web."""
    llm = FakeLLMClient([
        LLMResponse(content='une.', finish_reason='stop'),
        LLMResponse(content='deux.', finish_reason='stop'),
    ])
    session, _ = build(qapp, tmp_path, llm=llm)

    results = []
    def turn_one():
        results.append(session.runTurn('la premiere'))
    def turn_two():
        results.append(session.runTurn('la deuxieme'))
    t1 = threading.Thread(target=turn_one, daemon=True)
    t2 = threading.Thread(target=turn_two, daemon=True)
    t1.start(); t2.start()
    pumpUntil(qapp, lambda: len(results) == 2)
    t1.join(timeout=5); t2.join(timeout=5)
    assert len(results) == 2
    for rec in results:
        assert rec['error'] is None
    # Each turn leaves its own line; if they had interleaved, one transcript
    # would hold the other's line.
    lines_a = '\n'.join(results[0]['lines'])
    lines_b = '\n'.join(results[1]['lines'])
    assert 'une.' in lines_a and 'deux.' not in lines_a
    assert 'deux.' in lines_b and 'une.' not in lines_b


# ----------------------------------------------------------------- refusal

def test_an_empty_prompt_is_refused_by_name(qapp, tmp_path):
    """Nothing to ask is the refusal of the session, named before anything
    runs -- the way the REPL refuses it, and the way the panel says it."""
    session, _ = build(qapp, tmp_path)
    with pytest.raises(ValueError) as excinfo:
        session.runTurn('   ')
    assert 'no prompt' in str(excinfo.value)


def test_llm_fields_report_the_clients(qapp, tmp_path):
    """The running parameters the loop sends are reported the same way the
    REPL's /llm answers: endpoint, model, key (set or empty), and the three
    parameters. The web shares the one client the REPL reads, so these are
    the same numbers."""
    session, _ = build(qapp, tmp_path)
    fields = session.llmFields()
    assert fields['endpoint'] == DEAD_ENDPOINT
    assert fields['model'] == 'stub'
    assert fields['key'] is False
    assert fields['max_turns'] == 8
    assert 'temperature' in fields and 'max_tokens' in fields
