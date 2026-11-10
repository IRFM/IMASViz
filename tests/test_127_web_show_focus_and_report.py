# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""Two web-interface complaints, reproduced on stand-ins.

* **"montre moi le plot4"** -- the agent answers "show me figure N" with
  `focus_window` (the "bring it forward" gesture, the preparation of a
  screenshot). In the desktop app a focus is enough: the figure comes to
  the front of the screen. In the web there is **no screen** -- the only
  way a figure reaches the user is the PNG the turn saves -- so a focus,
  like the `get_screenshot` that follows it, is a capture of a figure. A
  figure an earlier turn drew is not among the ones this turn drew: it is
  captured only if this turn asks for it, and a focus is exactly that ask.
* **"le rapport n'apparait pas"** -- the Reports section of the page is
  driven by the reports folder (`/api/reports` -> `reportOnDisk`): a
  report appears the moment a tool writes it, whether or not the per-turn
  diff names it. So the repro pins the half the web can check on
  stand-ins -- that the report the turn's `plot_report` writes is on disk
  and in the record -- rather than the agent's tool choice, a model
  decision this suite does not drive.

Nothing drives a real case or a real model: the scripted LLM answers the
gestures and `CoreWithFocus` is the `FakeCore` of `test_119` with the
`focus_window` gesture it lacks added.
"""

import base64

from imasviz.VizAgent.llm_client import LLMResponse

from test_119_viz_web_session import (
    CASE_URI, FakeCore, PNG_1x1, build, inWorker)


class CoreWithFocus(FakeCore):
    """`FakeCore` plus `focus_window`, the "bring a window forward" gesture.

    `FakeCore` answers `plot_one`, `get_screenshot` and `plot_report` --
    the three the `test_119` turns need -- but not `focus_window`, and the
    "show me figure N" turn dispatches under exactly that name, so the
    stand-in answers it the way the core does, and refuses a window it
    does not hold the way the core does."""

    def focus_window(self, window='app', width=None, height=None):
        if any(record['key'] == window for record in self._windows):
            return {'window': window, 'visible': True,
                    'size': [width or 1280, height or 800]}
        raise ValueError('no such window: %r' % window)


def _draw(qapp, session):
    """The one figure the session will hold: drawn by a turn whose
    scripted LLM calls `plot_one` and then answers."""
    session.agent.llm = FakeLLM([
        ('plot_one', {'uri': CASE_URI, 'path': 'core.ion[0].temp'}),
        ('say', 'Tracé.'),
    ])
    record = inWorker(lambda: session.runTurn('trace une figure'), qapp)
    assert record['image_files'] == ['SlicesPlot1.png']
    return record


def FakeLLM(scripted):
    """A scripted client for `session.agent.llm`: named gestures, then
    a final line. `say` marks the final answer; a named gesture is a
    `tool_call` with `args`."""
    from test_119_viz_web_session import FakeLLMClient

    built = []
    for item in scripted:
        name = item[0]
        payload = item[1] if len(item) > 1 else None
        if name == 'say':
            built.append(LLMResponse(content=payload, finish_reason='stop'))
        else:
            built.append(LLMResponse(
                tool_calls=[{'name': name, 'args': payload}], content=''))
    return FakeLLMClient(built)


def test_focus_an_older_figure_is_a_capture_the_turn_keeps(qapp, tmp_path):
    """The repro of "montre moi le plot4": the figure is drawn by one turn
    and *shown* by the next, which draws nothing and only asks
    (`focus_window`) for an older figure. The ask is what makes the figure
    a capture of this turn -- the same rule `get_screenshot` of an older
    `SlicesPlot1` already pins. Before the fix `focus_window` was none of
    the gestures `onGestureSlot` read as a capture ask, so the figure the
    turn was told to show was the one it did not keep, and the page had
    nothing to draw. After, the focused figure stands in the turn's files
    and its address, the way the screenshot of it does."""
    session, core = build(qapp, tmp_path, core=CoreWithFocus())
    first = _draw(qapp, session)
    assert first['image_files'] == ['SlicesPlot1.png']

    session.agent.llm = FakeLLM([
        ('focus_window', {'window': 'SlicesPlot1'}),
        ('say', 'Voilà la figure 1.'),
    ])
    second = inWorker(lambda: session.runTurn('show me figure 1'), qapp)

    assert second['error'] is None, second.get('error')
    assert second['image_files'] == ['SlicesPlot1.png'], second['image_files']
    by_file = {w['name']: w for w in second['image_windows']}
    assert by_file['SlicesPlot1.png']['window'] == 'SlicesPlot1'
    png = next(im for im in second['images']
               if im['name'] == 'SlicesPlot1.png')
    assert base64.b64decode(png['b64']) == PNG_1x1


def test_focus_and_screenshot_one_figure_is_one_capture(qapp, tmp_path):
    """A turn that both focuses and screenshots one figure keeps it once.
    `focus_window` is the preparation of the `get_screenshot`, not a
    second picture: the capture is the figure, addressed to it, and
    deduplicated the way the two `get_screenshot` asks of one window
    would be -- not the figure twice."""
    session, _ = build(qapp, tmp_path, core=CoreWithFocus())
    _draw(qapp, session)

    session.agent.llm = FakeLLM([
        ('focus_window', {'window': 'SlicesPlot1'}),
        ('get_screenshot', {'window': 'SlicesPlot1'}),
        ('say', 'Voilà, en grand.'),
    ])
    second = inWorker(lambda: session.runTurn('show me figure 1 big'), qapp)

    assert second['error'] is None, second.get('error')
    assert second['image_files'] == ['SlicesPlot1.png'], \
        second['image_files']
    assert [w['window'] for w in second['image_windows']] == ['SlicesPlot1']


def test_a_report_the_turn_writes_is_on_disk_and_in_the_record(qapp,
                                                                tmp_path,
                                                                monkeypatch):
    """The half the web can check on a report, pinned: the `plot_report`
    the turn writes is **on disk** in the reports folder and named in the
    record -- the two places the page's Reports section reads (the folder
    via `/api/reports`, the turn via its `reports`). A report that is
    neither on disk nor in the turn is one no tool wrote; that is a model
    decision this suite does not make."""
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    session, core = build(qapp, tmp_path, core=CoreWithFocus())
    _draw(qapp, session)

    session.agent.llm = FakeLLM([
        ('plot_report', {'figure_key': 'SlicesPlot1', 'name': 'le-rapport'}),
        ('say', 'Le rapport est écrit.'),
    ])
    record = inWorker(lambda: session.runTurn('rapport de la figure'), qapp)

    assert record['error'] is None, record.get('error')
    # On disk, in the folder the page lists:
    assert (tmp_path / 'home' / '.imasviz' / 'reports'
            / 'le-rapport.html').is_file()
    assert sorted(session.reportsOnDisk()) == ['le-rapport.html']
    # And named in the record the page renders the turn from:
    assert record['reports'] == ['le-rapport.html']
