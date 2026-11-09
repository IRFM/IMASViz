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
  them, the figure it drew as a PNG with the base64 the page needs to
  draw it, and the transcript the turn leaves on disk;
* the capture of a turn is its own: the figure it drew or asked to be
  captured is the one it keeps, and the figures an earlier turn drew
  are not repeated into it -- they stay in the files that turn left,
  and the ask of a capture is what recaptures an older figure;
* the interface is an ask: `app` and the data-tree panel of a case are
  saved in the files of the turn that asked for them, and not in the
  others;
* a refused turn: the refusal **named**, and the figure it drew **still**
  captured -- not a silence the user reads as a failure;
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
    `describe_node` / `get_signal` / `list_cases` the page reads.

    Its figures are the ones it has **drawn** -- `plot_one` is what
    opens the one it draws, `SlicesPlot1`, and it then holds it --
    because a turn's captures are the figures that turn drew or asked
    for, and a stand-in that holds a figure before the turn drew it is
    one the test cannot tell it apart from.
    """

    def __init__(self):
        self.saved = []
        self.restored = []
        self._windows = []

    def list_windows(self):
        return list(self._windows)

    def screenshot(self, window):
        if window == 'app' or any(record['key'] == window
                                  for record in self._windows):
            return PNG_1x1
        raise ValueError('no such window: %r' % window)

    def get_screenshot(self, window='app'):
        # The tool name the loop dispatches under, answering the one the
        # core's own method runs -- the same pair `McpGuiCore` keeps, so
        # a `get_screenshot` of the loop reaches this stand-in too.
        return self.screenshot(window)

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
        # The gesture that draws: the figure it opens once, and a second
        # call finds it already held -- the key the application recycles
        # is the one it already gave, and a stand-in may not invent a
        # second one.
        if any(record['key'] == 'SlicesPlot1' for record in self._windows):
            return {'window': 'SlicesPlot1'}
        self._windows.append({'kind': 'SlicesPlot', 'label': 'SlicesPlot 1',
                              'key': 'SlicesPlot1', 'visible': True,
                              'cases': []})
        return {'window': 'SlicesPlot1'}

    def plot_report(self, figure_key, name=None):
        # The one half the turn tests need of the core's own
        # `plot_report`: the file under $HOME/.imasviz/reports, the folder
        # its `_namedReport` resolves. The statistics it computes are what
        # `test_100` drives on a real window, not this stand-in.
        import os
        folder = os.path.join(os.environ['HOME'], '.imasviz', 'reports')
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

def test_an_answered_turn_keeps_the_figure_it_drew(qapp, tmp_path):
    """An answered loop: the lines in the order the loop writes them,
    the figure the turn drew on disk as a PNG (with the base64 the page
    needs to draw it), the transcript beside it on disk -- and nothing
    but it. A capture of a turn is the figure it drew and the ones it
    asked to be captured: the application shell and the data-tree panel
    of a case are the captures that show the interface, and their saving
    is the ask (a `get_screenshot` of the loop, or an `EXTRA_SHOTS` of
    the one-shot), not the by-product of the turn. The figure the turn
    drew is addressed, and the one the turn did not ask for is not among
    its files -- here the figure is the one its own `plot_one` opened
    in the same turn, and the stand-in held none before it."""
    llm = FakeLLMClient([
        LLMResponse(tool_calls=[
            {'name': 'plot_one',
             'args': {'uri': CASE_URI, 'path': 'core.ion[0].temp'}}],
            content=''),
        LLMResponse(content='La figure est tracée.', finish_reason='stop'),
    ])
    session, core = build(qapp, tmp_path, llm=llm)
    record = inWorker(lambda: session.runTurn('trace une courbe du cas'), qapp)

    text = '\n'.join(record['lines'])
    assert 'La figure est tracée.' in text
    assert 'plot_one' in text

    # The figure is on disk under a directory the session names, and its
    # base64 is in the record -- the `data:` URI the page draws from.
    assert record['dir'].startswith(str(tmp_path / 'shots'))
    assert record['image_files'] == ['SlicesPlot1.png']
    fig_png = next(im for im in record['images'] if im['name'] == 'SlicesPlot1.png')
    assert base64.b64decode(fig_png['b64']) == PNG_1x1
    assert (tmp_path / 'shots' / record['dir'].split('shots/')[-1]
            / 'SlicesPlot1.png').is_file()

    # The picture is also an address: the name the page's Focus and
    # Screenshot buttons send to focus_window and get_screenshot.
    by_file = {entry['name']: entry for entry in record['image_windows']}
    assert by_file['SlicesPlot1.png']['window'] == 'SlicesPlot1'
    # The base64 the page draws carries the address with it.
    assert fig_png['window'] == 'SlicesPlot1'
    # And the interface capture the turn did not ask for is the one that
    # is not there: the turn drew a figure, and said nothing about the
    # application, so the application is not in its files.
    assert '00_app.png' not in record['image_files']


def test_a_turn_captures_what_it_drew_or_asked_and_only_that(qapp, tmp_path):
    """The capture of a turn is its own, not the session's: the figures
    it drew and the windows it asked to be captured are the ones it
    keeps, and a figure an earlier turn drew is not repeated into it --
    it stays in the files that turn left. The ask of a capture is what
    recaptures an older figure, into the turn that asks. What it pins,
    on the **same** session whose core keeps the figure the first turn
    opened: the one that drew a figure and asked the interface keeps
    the two; the one that drew nothing and asked for nothing keeps
    **none** -- not a wall of the same picture in every request; and
    the one that asks a capture of the older figure gets it again. One
    scripted LLM for the three turns -- the loop keeps its history
    between them, the way the context test pins -- and the stand-in
    holds the figure from the turn that drew it."""
    llm = FakeLLMClient([
        # First: the figure is drawn, then the interface is asked.
        LLMResponse(tool_calls=[
            {'name': 'plot_one',
             'args': {'uri': CASE_URI, 'path': 'core.ion[0].temp'}}],
            content=''),
        LLMResponse(tool_calls=[
            {'name': 'get_screenshot', 'args': {'window': 'app'}}],
            content=''),
        LLMResponse(content='La figure est tracée, et l''interface.',
                    finish_reason='stop'),
        # Second: nothing is drawn and nothing is asked.
        LLMResponse(tool_calls=[{'name': 'list_cases', 'args': {}}], content=''),
        LLMResponse(content='Le cas est ouvert.', finish_reason='stop'),
        # Third: the capture of the older figure is asked.
        LLMResponse(tool_calls=[
            {'name': 'get_screenshot', 'args': {'window': 'SlicesPlot1'}}],
            content=''),
        LLMResponse(content='La capture est refaite.', finish_reason='stop'),
    ])
    session, core = build(qapp, tmp_path, llm=llm)

    first = inWorker(
        lambda: session.runTurn('trace une figure et donne-moi l''interface'),
        qapp)
    assert first['error'] is None
    assert sorted(first['image_files']) == ['00_app.png', 'SlicesPlot1.png']
    # The figure the turn drew and the interface it asked for are both
    # its captures, addressed as they are.
    by_file = {entry['name']: entry for entry in first['image_windows']}
    assert by_file['00_app.png']['window'] == 'app'
    assert by_file['SlicesPlot1.png']['window'] == 'SlicesPlot1'
    assert (tmp_path / 'shots' / first['dir'].split('shots/')[-1]
            / '00_app.png').is_file()

    second = inWorker(lambda: session.runTurn('liste les cas'), qapp)
    assert second['error'] is None
    # The figure the first turn drew is not repeated here: it stays in
    # the files that turn left, and this one drew nothing and asked for
    # nothing. This is the turn whose page used to re-show the captures
    # of the ones before it.
    assert second['image_files'] == []

    third = inWorker(
        lambda: session.runTurn('donne-moi la capture de la figure'), qapp)
    assert third['error'] is None
    # An ask for a figure is what recaptures it, into the turn that asks.
    assert third['image_files'] == ['SlicesPlot1.png']


def test_a_turn_that_writes_a_report_names_it_in_the_record(qapp, tmp_path, monkeypatch):
    """The self-contained HTML the turn's `plot_report` writes is named
    in the record -- the `done` event the page reads, and what the
    Reports section fills from -- not a file the user has to find on
    disk themselves. The folder the core's `_namedReport` resolves is
    under $HOME, so pointing HOME at the test's own tree points it there
    too (the pattern `test_39` applies to the configuration files)."""
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    llm = FakeLLMClient([
        LLMResponse(tool_calls=[{'name': 'plot_report',
                                 'args': {'figure_key': 'SlicesPlot1',
                                          'name': 'tour_report'}}],
                     content=''),
        LLMResponse(content='Le rapport est écrit.', finish_reason='stop'),
    ])
    session, core = build(qapp, tmp_path, llm=llm)
    record = inWorker(lambda: session.runTurn('écris le rapport du cas'), qapp)
    assert record['error'] is None
    assert record['reports'] == ['tour_report.html']
    # And the file is where the service route serves it from: the folder
    # under the HOME the test named, not a path the page cannot reach.
    assert (tmp_path / 'home' / '.imasviz' / 'reports'
            / 'tour_report.html').is_file()


def test_a_turn_that_writes_no_report_names_none(qapp, tmp_path, monkeypatch):
    """A turn that writes no report is not silent about it either: the
    record holds the empty list -- the key the page fills the section
    from -- not a missing key the page would have to guess at."""
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    llm = FakeLLMClient([
        LLMResponse(tool_calls=[{'name': 'list_cases', 'args': {}}], content=''),
        LLMResponse(content='Le cas est ouvert.', finish_reason='stop'),
    ])
    session, core = build(qapp, tmp_path, llm=llm)
    record = inWorker(lambda: session.runTurn('liste les cas ouverts'), qapp)
    assert record['error'] is None
    assert record['reports'] == []


def test_a_refused_turn_is_named_and_still_saves(qapp, tmp_path):
    """The refusal (the truncation here) is not a silence: it is in the
    record's error and the transcript, and the figure the turn drew before
    it was refused still comes to disk -- a capture of a turn is what it
    drew or asked, and it drew one first. The refusal keeps the work:
    the shape `test_112` pins for the one-shot and `test_113` for the
    REPL. The stand-in holds no figure before the turn, so the one the
    turn has is the one its `plot_one` opened in it."""
    llm = FakeLLMClient([
        LLMResponse(tool_calls=[
            {'name': 'plot_one',
             'args': {'uri': CASE_URI, 'path': 'core.ion[0].temp'}}],
            content=''),
        LLMResponse(content='partial...', finish_reason='length'),
    ])
    session, core = build(qapp, tmp_path, llm=llm)
    record = inWorker(lambda: session.runTurn('trace une figure et continue'), qapp)
    assert record['error'] is not None
    text = '\n'.join(record['lines'])
    assert 'REFUSAL' in text
    assert 'truncated' in text
    assert record['image_files'] == ['SlicesPlot1.png']   # what it drew is kept


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
