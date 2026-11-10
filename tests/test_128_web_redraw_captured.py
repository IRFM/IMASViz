"""`WebSession`: the capture of a turn when the agent redrew onto a figure
it already held -- the "je ne vois plus les autres figures" case.

The user's session was: "trace X" then "trace X at psi=50". The agent
correctly answered the second with `plot_one(into_figure_key=Plot1)` onto
the first's figure (superposition). In that turn, no new key was added:
the delta `figure_keys_now - figure_keys_before` is empty (the key was
in both). If the web session captured only the delta, the page would
render nothing for a turn the loop printed as traced. The fix pins that
`plot_one` with `into_figure_key` set is a capture ask -- the redraw
names its target, and it is the one the turn draws.
"""

import os

import pytest
from imasviz.VizAgent.llm_client import LLMResponse

from test_119_viz_web_session import (
    CASE_URI, PNG_1x1, FakeLLMClient, FakeWindow, inWorker)
from viz_web.web_session import WebSession


class CoexistingCore:
    """A core whose `plot_one` honours `into_figure_key`: it returns the
    existing window for a redraw, and allocates a new key for a fresh
    figure -- the way the real core coexists when it has a
    `QVizMainWindow`."""

    def __init__(self):
        self._windows = []
        self._next = 1
        self.saved = []
        self.restored = []

    def list_windows(self):
        return list(self._windows)

    def screenshot(self, window):
        if window == 'app' or any(r['key'] == window for r in self._windows):
            return PNG_1x1
        raise ValueError('no such window: %r' % window)

    def get_screenshot(self, window='app'):
        return self.screenshot(window)

    def list_cases(self):
        return [{'uri': CASE_URI, 'dd_version': '3.35.0',
                 'loaded': {'equilibrium': [0]}, 'signals': 33}]

    def list_case_idss(self, uri):
        return [{'name': 'equilibrium', 'occurrences': [0]}]

    def get_signal(self, uri, path, **kwargs):
        return {'x': [0, 1, 2], 'y': [10, 20, 30]}

    def plot_one(self, uri, path, into_figure_key=None, **kwargs):
        # The redraw: the agent names a window it already holds and
        # draws onto it, and the key stays the same. That is the "trace
        # X" then "trace X at psi=50" pattern: the second call names the
        # first figure.
        if into_figure_key and any(r['key'] == into_figure_key
                                   for r in self._windows):
            return {'window': into_figure_key,
                    'kind': 'QVizCurvePlot', 'drawing': True}
        key = 'Plot%d' % self._next
        self._next += 1
        self._windows.append({'kind': 'SlicesPlot',
                              'label': key,
                              'key': key,
                              'visible': True,
                              'cases': []})
        return {'window': key, 'kind': 'QVizCurvePlot', 'drawing': True}

    def focus_window(self, window='app', width=None, height=None):
        if any(r['key'] == window for r in self._windows):
            return {'window': window, 'visible': True,
                    'size': [width or 1280, height or 800]}
        raise ValueError('no such window: %r' % window)

    def plot_report(self, figure_key, name=None):
        folder = os.path.join(os.environ['HOME'], '.imasviz', 'reports')
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, (name or 'fake_report') + '.html')
        with open(path, 'w') as f:
            f.write('<!doctype html></html>')
        return {'saved_to': path, 'traces': 3, 'window': figure_key}

    def save_session(self, name=None, path=None):
        self.saved.append(name)
        return {'saved_to': '/preferences/%s.vsess' % name}


@pytest.fixture
def coexisting(qapp, tmp_path):
    os.environ['HOME'] = str(tmp_path / 'home')
    from viz_cli.session import Client
    from imasviz.VizAgent.llm_client import LLMClient
    DEAD = 'http://127.0.0.1:65531/v1'
    core = CoexistingCore()
    session = WebSession(app=None, window=FakeWindow(), core=core,
                         client=Client(LLMClient(endpoint=DEAD,
                                                 model='stub', timeout=2.0)),
                         shots_dir=str(tmp_path / 'shots'),
                         max_turns=12)
    return session, core


def test_a_turn_that_only_redrew_a_figure_is_a_capture_of_that_figure(
        coexisting, qapp):
    """The user's "je ne vois plus les autres figures" case, pinned.

    Turn 1 opens a new figure (Plot1), and the turn's capture is that
    figure -- the delta `figure_keys_now - figure_keys_before` covers it.

    Turn 2 draws onto Plot1 (the agent says `plot_one(into_figure_key=
    Plot1)` -- superposition). No new key is added: the delta is empty.
    Before the fix, the page would render nothing for that turn -- the
    loop printed "tracé sur Plot1" and the gallery stayed the same. The
    fix reads the redraw's `into_figure_key` as a capture ask; Turn 2
    keeps Plot1, and the page shows it for the turn that drew it.
    """
    session, core = coexisting

    # Turn 1: open Plot1.
    session.agent.llm = FakeLLMClient([
        LLMResponse(tool_calls=[
            {'name': 'plot_one',
             'args': {'uri': CASE_URI, 'path': 'equilibrium.time_slice[0].'
                     'profiles_1d.j_tor'}}],
            content=''),
        LLMResponse(content='tracé', finish_reason='stop'),
    ])
    first = inWorker(lambda: session.runTurn('trace la pression'), qapp)
    assert first['error'] is None, first['error']
    assert first['image_files'] == ['Plot1.png'], first['image_files']
    by_file = {w['name']: w for w in first['image_windows']}
    assert by_file['Plot1.png']['window'] == 'Plot1'

    # Turn 2: redraw onto Plot1 (no new key).
    session.agent.llm = FakeLLMClient([
        LLMResponse(tool_calls=[
            {'name': 'plot_one',
             'args': {'uri': CASE_URI,
                      'path': 'equilibrium.time_slice[0].'
                     'profiles_1d.j_tor',
                      'into_figure_key': 'Plot1'}}],
            content=''),
        LLMResponse(content='tracé sur Plot1 (psi=50)',
                    finish_reason='stop'),
    ])
    second = inWorker(lambda: session.runTurn('trace la pression psi=50'),
                      qapp)
    assert second['error'] is None, second['error']
    # The redraw did not add a key, so the delta is empty. The capture
    # came from the redraw's `into_figure_key` being read as the ask:
    # without it, `image_files` would be `[]` and the page would stay
    # silent for the turn the loop printed as traced.
    assert second['image_files'] == ['Plot1.png'], second['image_files']
    by_file = {w['name']: w for w in second['image_windows']}
    assert by_file['Plot1.png']['window'] == 'Plot1'


def test_a_redraw_is_one_capture_not_two(coexisting, qapp):
    """A turn that both redrew a figure and asked `get_screenshot` of
    it keeps one file, not two: the ask of a capture is the window, and
    the redraw's `into_figure_key` and the screenshot's `window` name
    the same one, so they deduplicate into a single PNG -- the way a
    focus and a screenshot of the same window already do."""
    session, _ = coexisting

    # Turn 1: open Plot1.
    session.agent.llm = FakeLLMClient([
        LLMResponse(tool_calls=[
            {'name': 'plot_one',
             'args': {'uri': CASE_URI, 'path': 'equilibrium.time_slice[0].'
                     'profiles_1d.j_tor'}}],
            content=''),
        LLMResponse(content='tracé', finish_reason='stop'),
    ])
    inWorker(lambda: session.runTurn('trace'), qapp)

    # Turn 2: redraw + ask the screenshot of Plot1 in the same turn.
    session.agent.llm = FakeLLMClient([
        LLMResponse(tool_calls=[
            {'name': 'plot_one',
             'args': {'uri': CASE_URI,
                      'path': 'equilibrium.time_slice[0].'
                     'profiles_1d.j_tor',
                      'into_figure_key': 'Plot1'}}],
            content=''),
        LLMResponse(tool_calls=[
            {'name': 'get_screenshot', 'args': {'window': 'Plot1'}}],
            content=''),
        LLMResponse(content='tracé, et voilà.', finish_reason='stop'),
    ])
    second = inWorker(lambda: session.runTurn('trace + screenshot'), qapp)
    assert second['error'] is None, second['error']
    # One capture of Plot1, addressed to it, not two.
    assert second['image_files'] == ['Plot1.png'], second['image_files']
    assert [w['window'] for w in second['image_windows']] == ['Plot1']


if __name__ == '__main__':
    import sys
    sys.exit(pytest.main([__file__, '-v']))
