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

"""The surface that reads events off a case and marks them on a figure.

The math is pinned in `test_152` on a synthetic signal; this pins the wiring
around it, on the one read the surface already holds:

* the **read** -- `detect_events` answers on the same read `get_signal`
  does, so the leaf that answers more than one axis is refused by name, and
  a parameter a kind does not take is refused the way the detector refuses;
* the **mark** -- one vertical per event on a curve figure, capped: past the
  cap the lines are a wall and the report is the shape that many wants, so
  the cap is a refusal with the report named, not a silent figure;
* the **clear** -- the marks come back off the frame, and it is safe when
  the figure holds none; and
* the **report** -- the same read and detection, the events in a table, on
  the one report page the other reports keep.

The stand-in parts need no case at all (the cap, the clear, a refusal the
read answers); the case parts run on the reference case and skip when it is
not reachable, the way `test_132` does.
"""

import types

import pyqtgraph as pg
import pytest

from mcp_server.core import McpGuiCore

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI,
                      case_uri_or_skip)

PRESSURE_PATH = 'equilibrium.time_slice[0].profiles_1d.pressure'
IDS_NAME = 'equilibrium'

pytestmark = [pytest.mark.case, pytest.mark.ui]


class FakePlot:
    """The one a stand-in curve figure keeps: it takes and drops markers."""

    def __init__(self):
        self.items = []

    def addItem(self, line):
        self.items.append(line)

    def removeItem(self, line):
        self.items.remove(line)


def _fakeCurveFigure():
    frame = types.SimpleNamespace()
    frame.pgPlotWidget = FakePlot()
    frame._eventMarkers = []
    return frame


def _block(kind, count):
    return {'kind': kind, 'count': count,
            'events': [{'index': i, 't': float(2 * i + 1),
                        'value': float(10 - i),
                        'prominence': float(9 - i)}
                       for i in range(count)],
            'period': {'count': count, 'span': float(2 * (count - 1) + 1)
                       if count else None}}


@pytest.fixture(scope='module')
def core(qapp, tmp_path_factory):
    """One self-contained session: the case open and equilibrium loaded.

    Stand-in parts (the cap, the clear, a read refusal) run against the
    same instance with its window and read stood in; the case parts run on
    the reference case. HOME is patched for the module and undone on the
    way out, and any figure left is closed, the way `test_132` keeps the
    session clean.
    """
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    home = tmp_path_factory.mktemp('eventDetectionHome')
    patch = pytest.MonkeyPatch()
    patch.setenv('HOME', str(home))
    session = McpGuiCore()
    session.open_case(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
    session.load_ids(CASE_URI, IDS_NAME, 0)
    try:
        yield session
    finally:
        for key in list(getattr(session.api, 'figureframes', []) or {}):
            try:
                session.close_window(key)
            except Exception:
                pass
        patch.undo()


# ---------------------------------------------------------------------------
# the read: the same one get_signal holds
# ---------------------------------------------------------------------------

def test_the_read_is_the_one_get_signal_answers(core):
    old = core.get_signal
    core.get_signal = lambda *a, **k: {'kind': 'other', 'x': None, 'y': None}
    try:
        with pytest.raises(ValueError, match='multi-array'):
            core._readSignalForEvents(CASE_URI, 'any.leaf', None, None)
    finally:
        core.get_signal = old


def test_a_parameter_the_kind_does_not_take_is_refused(core):
    # `direction` is an L-H gate: an ELM asked for it is refused by name,
    # the way the detector refuses, not a bare TypeError
    with pytest.raises(ValueError, match='not among them'):
        core.detect_events(CASE_URI, PRESSURE_PATH, 'elm', direction='up')


def test_detect_events_reads_off_the_leaf_and_shapes(core):
    out = core.detect_events(CASE_URI, PRESSURE_PATH, 'elm', prominence=1e-6)
    assert isinstance(out['count'], int)
    assert isinstance(out['events'], list)
    for event in out['events']:
        assert 't' in event and 'value' in event
    assert 'period' in out
    assert out['period']['count'] == out['count']


# ---------------------------------------------------------------------------
# the mark: capped so a wall does not come across the curve
# ---------------------------------------------------------------------------

def test_past_the_cap_the_report_is_named_not_a_figure(core):
    with pytest.raises(ValueError, match='report'):
        core._addEventMarkers(_fakeCurveFigure(), 'PlotNo', _block('elm', 41))


def test_within_the_cap_every_event_gets_a_mark(core):
    frame = _fakeCurveFigure()
    count = core._addEventMarkers(frame, 'PlotYes', _block('elm', 5))
    assert count == 5
    assert len(frame._eventMarkers) == 5
    assert len(frame.pgPlotWidget.items) == 5


# ---------------------------------------------------------------------------
# the clear: the marks come off, and it is safe when there are none
# ---------------------------------------------------------------------------

def test_clear_event_marks_is_safe(core):
    frame = _fakeCurveFigure()
    pen = pg.mkPen((255, 122, 40), width=2)
    for i in range(3):
        line = pg.InfiniteLine(pos=float(i), pen=pen, movable=False)
        frame.pgPlotWidget.addItem(line)
        frame._eventMarkers.append(line)
    record = types.SimpleNamespace(cases=[CASE_URI])
    old = core._windowForKey
    core._windowForKey = lambda key: (record, frame)
    try:
        first = core.clear_event_marks('PlotX')
        second = core.clear_event_marks('PlotX')
    finally:
        core._windowForKey = old
    assert first['cleared'] == 3
    assert frame._eventMarkers == []
    assert len(frame.pgPlotWidget.items) == 0
    assert second['cleared'] == 0


# ---------------------------------------------------------------------------
# the report: one page, the events in a table
# ---------------------------------------------------------------------------

def test_events_report_is_a_page_that_keeps_the_events(core):
    out = core.events_report(CASE_URI, PRESSURE_PATH, 'elm',
                             name='t153_events')
    path = out['saved_to']
    assert path.endswith('t153_events.html')
    with open(path) as file:
        text = file.read()
    assert PRESSURE_PATH in text
    assert 'event' in text.lower()
    # the timing is the report's own footer: the count and the mean spacing
    assert 'count' in text.lower()
    assert 'mean' in text.lower()
