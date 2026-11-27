# Copyright holders : Commissariat à l’Energie Atomique and aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""A session keeps the scale a hand gave the values of a curve.

``test_179`` and ``test_180`` pin the affine itself: a factor kept beside the
values a trace read, re-applied when a slider or a posed row brings other numbers
under it, worn by the error bars that hang over that curve. ``test_66`` pins the
file: a ``<Transform>`` written is a ``<Transform>`` read, and one that cannot be
put back is refused at the file. What neither can pin is the promise they exist
for -- multiply a probe this morning, close the application, open the session
tomorrow, and the probe is still multiplied, its neighbour still not.

So everything here goes through the gestures. The affine is asked the way the tool
surface asks it (`scale_curve`, `shift_curve`, `normalize_curve`, `reset_curve` --
the same four a user reaches through the agent, the MCP service and the CLI), the
session is written by ``QVizSaveSession`` from the api of the run, and it is put
back by ``QVizRestoreSession`` on a **second** api that never saw the window. Each
test gets an api of its own: ``figureframes`` is what the save walks, so a run
shared between tests would write its neighbours' windows into every file, and a
test that says "this file holds no ``<Transform>``" would be reading somebody
else's figure. The case is one record per process, so reopening the view costs the
tree walk and nothing else.

Four things a session may not do, and each is an assertion here:

* it may not dress the neighbour of the curve the hand was on. A figure holds its
  traces in the order they were drawn, which is not an identity, so the affine is
  written under its ``<Quantity>``, ranked among the traces of *that* quantity --
  as a ``<Style>`` is;
* it may not write the curves nobody scaled. An untouched figure writes **0**
  ``<Transform>``, and the run that puts it back leaves every trace at the values
  the case answers. Unlike a pen, an affine is recognisable by its own value, so no
  record of *which* traces were touched is needed to tell a hand from the drawing;
* it may not re-derive a normalisation. A ``normalize_curve`` divides by a
  reference read off the curve at the time the hand asked. Put that back as a
  gesture on the restored curve and the peak is divided twice: a figure of two
  probes normalised to one reference is exactly what would come back broken, so the
  file holds the composed affine and the restored peak is 1, not 1 over the peak;
* it may not draw the error bars at the raw extent. The affine is put back **
  before** the bars are asked for, so a bar that came back at the height of the
  unclosed run is not a bar that has to be redrawn a second time.

A Table Plot View is pinned here too: its panels are filled from a configuration
file the command writes, so the node a panel holds is not the node the gesture
named -- and the affine still has to land on that panel alone.
"""

import numpy as np
import pyqtgraph as pg
import pytest
from PySide6.QtWidgets import QMdiArea

from mcp_server.core import McpGuiCore

from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizGUI.VizConfigurations.QVizSessionFile import QVizSessionFile
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
    import QVizLoadOccurrence
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectNodes \
    import QVizSelectNodes
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsTable \
    import QVizPlotAsTable
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode \
    import QVizPlotOneNode
from imasviz.VizGUI.VizGUICommands.VizSession.QVizRestoreSession \
    import QVizRestoreSession
from imasviz.VizGUI.VizGUICommands.VizSession.QVizSaveSession \
    import QVizSaveSession
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPanel import QVizPanel
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizTablePlot import QVizTablePlot
from imasviz.Viz_API import Viz_API

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip)
from support import ownership

IDS_NAME = 'magnetics'
OCCURRENCE = 0
FIRST = 'magnetics/flux_loop(0)/flux/data'
SECOND = 'magnetics/bpol_probe(0)/field/data'
THIRD = 'magnetics/flux_loop(1)/flux/data'
# A path the tree does not hold at all: the affine has to be named as lost rather
# than put on the trace next to it.
NOT_IN_THE_CASE = 'magnetics/flux_loop(9999)/flux/data'
# The step `test_67` leaves on a session's `<Errors>` line, and the one `test_58`
# measures the bar extent with.
STEP = 10

pytestmark = [pytest.mark.case, pytest.mark.dd, pytest.mark.ui]


class Run:
    """The gestures of one IMASViz run, on one ``Viz_API``.

    The run owns a ``McpGuiCore`` over that same api: the four transforms are a
    tool-surface gesture, and the core looks for a window in the api it was built
    on -- which is the api the session is written from, or the affine the file
    should describe is not the affine the run holds.
    """

    def __init__(self, mdi):
        self.mdi = mdi
        self.api = Viz_API(parent=mdi)
        self.core = McpGuiCore(api=self.api)

    def freshApi(self):
        """An api that never saw the windows being put back: another run."""
        return Viz_API(parent=self.mdi)

    def view(self):
        """The reference case, with `magnetics` loaded in it."""
        source = QVizDataSourceFactory().create(CASE_URI)
        source.dd_version = CASE_DATA_DICTIONARY_VERSION
        if self.api.isDataSourceAlreadyOpened(source):
            view = self.api.GetDTVFor(source.getKey())
        else:
            view = self.api.CreateDataTree(source).dataTreeView
            self.api.ShowDataTree(view)
        if not self.api.IDSDataAlreadyFetched(view, IDS_NAME, OCCURRENCE):
            QVizLoadOccurrence(dataTreeView=view, idsName=IDS_NAME,
                               occurrence=OCCURRENCE, asynch=False).execute()
        return view

    @staticmethod
    def node(view, path):
        for node in view.signalsList:
            if node.getPath() == path:
                return node
        raise AssertionError('"%s" is not a leaf of this tree' % path)

    def figure(self, view, *paths):
        """One curve figure holding those quantities, drawn as the menu draws it."""
        frame = None
        for path in paths:
            frame = QVizPlotOneNode(dataTreeView=view,
                                    treeNode=self.node(view, path),
                                    intoFigureKey=None if frame is None
                                    else frame.figureKey,
                                    alongTime=True).execute()
            assert type(frame) is QVizCurvePlot
        return frame

    def table(self, view, *paths):
        """A Table Plot View, one panel per quantity, drawn as the menu draws it."""
        selector = QVizSelectNodes(view)
        selector.unselectAll()
        for path in paths:
            selector.selectNode(self.node(view, path), view)
        frame = QVizPlotAsTable(view, plotAxis='TIME').execute()
        assert isinstance(frame, QVizTablePlot)
        return frame


@pytest.fixture
def run(qapp, tmp_path, monkeypatch):
    """One run of its own: a $HOME it may write into, one api, one central area.

    The run is kept for the whole session, as the application keeps its windows:
    a shown frame freed by the collector is a frame Qt still owes a paint event.
    """
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    monkeypatch.setenv('HOME', str(tmp_path))
    return ownership.keep(Run(QMdiArea()))


# --------------------------------------------------------------------- helpers

def drawn(frame, source=None):
    """{path: the y values that trace is drawn with} for one window.

    A window of curves answers for itself; a table answers one panel at a time,
    which is what the session walks too -- so this reads the values through the
    same sources the save asks, never through the window's own list.
    """
    sources = [source] if source is not None else \
        ([panel for panel in frame.panels() if isinstance(panel, QVizPanel)]
         if hasattr(frame, 'panels') else [frame])
    values = {}
    for one in sources:
        for treeNode, _rank, curve in one.tracesForStyling():
            values[treeNode.getPath()] = np.asarray(curve.getData()[1],
                                                    dtype=float)
    return values


def affines(frame):
    """{path: (factor, offset)} for every trace a window draws."""
    if hasattr(frame, 'panels'):
        return dict((panel.treeNode.getPath(), panel.transformOf(panel.curves()[0]))
                    for panel in frame.panels()
                    if isinstance(panel, QVizPanel) and panel.curves())
    return dict((treeNode.getPath(), frame.transformOf(curve))
                for treeNode, _rank, curve in frame.tracesForStyling())


def written(session, key):
    """{path: [(trace, factor, offset)]} for the figures of a written session."""
    figure = [one for one in session.figures if one.key == key][0]
    return dict((quantity.path,
                 [(transform.trace, transform.factor, transform.offset)
                  for transform in quantity.transforms])
                for quantity in figure.quantities)


def barsOf(frame):
    return [item for item in frame.pgPlotWidget.getViewBox().addedItems
            if isinstance(item, pg.ErrorBarItem)]


# ------------------------------------------------------------------- a figure

@pytest.mark.ui
def test_a_scaled_curve_comes_back_at_the_scale_the_hand_asked(run):
    """The factor is the state of the window, so it travels with the session.

    Measured here: the dressed trace comes back at its raw values times the factor
    the hand gave it, its neighbour of the same window comes back at the raw
    values, and a session written from the run that received them keeps them --
    a replay goes through `setTransform`, so it is a hand like any other.
    """
    view = run.view()
    frame = run.figure(view, FIRST, SECOND)
    key = frame.figureKey
    raw = drawn(frame)

    run.core.scale_curve(key, 10.0, curve=0)
    assert drawn(frame)[FIRST] == pytest.approx(raw[FIRST] * 10.0, rel=1e-9)
    path = QVizSaveSession(run.api, name='scaled').execute()

    restored = run.freshApi()
    QVizRestoreSession(restored, path=path).execute()
    again = restored.figureframes[key]

    assert drawn(again)[FIRST] == pytest.approx(raw[FIRST] * 10.0, rel=1e-9)
    assert drawn(again)[SECOND] == pytest.approx(raw[SECOND], rel=1e-9)
    assert affines(again) == {FIRST: (10.0, 0.0), SECOND: (1.0, 0.0)}
    writtenTwice = QVizSessionFile.read(
        QVizSaveSession(restored, name='scaled2').execute())
    assert written(writtenTwice, key) == {FIRST: [(0, 10.0, 0.0)], SECOND: []}


@pytest.mark.ui
def test_the_affine_is_written_under_the_quantity_that_drew_the_trace(run):
    """`<Transform>` under its `<Quantity>`, ranked among the traces of *that* one."""
    view = run.view()
    frame = run.figure(view, FIRST, SECOND)
    run.core.scale_curve(frame.figureKey, 10.0, curve=1)
    path = QVizSaveSession(run.api, name='under_quantity').execute()

    assert written(QVizSessionFile.read(path), frame.figureKey) \
        == {FIRST: [], SECOND: [(0, 10.0, 0.0)]}
    with open(path) as handle:
        body = handle.read()
    assert '<Transform trace="0" factor="10' in body, body


@pytest.mark.ui
def test_a_window_nobody_scaled_writes_no_transform(run):
    """An affine is recognisable by its value, so an untouched window says nothing.

    The restored figure draws the values the case answers: had the identity been
    written, a session would be dressing curves the hand never touched, which is
    the mistake the ``<Style>`` rule exists to avoid.
    """
    view = run.view()
    frame = run.figure(view, FIRST, SECOND)
    raw = drawn(frame)
    path = QVizSaveSession(run.api, name='untouched').execute()
    with open(path) as handle:
        body = handle.read()

    assert '<Transform' not in body

    restored = run.freshApi()
    QVizRestoreSession(restored, path=path).execute()
    again = restored.figureframes[frame.figureKey]
    for name in (FIRST, SECOND):
        assert drawn(again)[name] == pytest.approx(raw[name], rel=1e-9)
    assert affines(again) == {FIRST: (1.0, 0.0), SECOND: (1.0, 0.0)}


@pytest.mark.ui
def test_a_normalisation_is_not_divided_twice(run):
    """The reference of the closed run is the reference of the opened one.

    The file holds two numbers, not the gesture: dividing the restored curve by
    its own peak again would answer a peak of 1 over the peak squared where the
    screen left 1, and would make two probes normalised to one reference stop
    being comparable -- which is the only reason to normalise them together.
    """
    view = run.view()
    frame = run.figure(view, FIRST, SECOND)
    key = frame.figureKey
    answer = run.core.normalize_curve(key, mode='max', curve=0)
    reference = answer['reference']
    assert reference != 1.0, 'nothing divided here: the peak was already 1'
    assert max(drawn(frame)[FIRST]) == pytest.approx(1.0, rel=1e-9)

    path = QVizSaveSession(run.api, name='normalised').execute()
    restored = run.freshApi()
    QVizRestoreSession(restored, path=path).execute()
    again = restored.figureframes[key]

    assert max(drawn(again)[FIRST]) == pytest.approx(1.0, rel=1e-9)
    assert drawn(again)[FIRST] == pytest.approx(drawn(frame)[FIRST], rel=1e-9)
    assert drawn(again)[SECOND] == pytest.approx(drawn(frame)[SECOND], rel=1e-9)


@pytest.mark.ui
def test_a_scale_and_a_shift_come_back_as_one_affine(run):
    """The composition is stored, not replayed as two gestures.

    `scale` then `shift` is `(10, -5)`: a session that replayed the two numbers as
    one multiplication and one addition in the order they were asked would get the
    same answer here, but a file that said "multiply by 10" and "add -5" in the
    wrong order would not -- so what is written is the pair, and it is one element.
    """
    view = run.view()
    frame = run.figure(view, FIRST)
    key = frame.figureKey
    raw = drawn(frame)[FIRST]

    run.core.scale_curve(key, 10.0)
    run.core.shift_curve(key, -5.0)
    path = QVizSaveSession(run.api, name='composed').execute()
    body = open(path).read()

    assert body.count('<Transform') == 1, body
    assert written(QVizSessionFile.read(path), key) \
        == {FIRST: [(0, 10.0, -5.0)]}

    restored = run.freshApi()
    QVizRestoreSession(restored, path=path).execute()
    assert drawn(restored.figureframes[key])[FIRST] \
        == pytest.approx(raw * 10. - 5., rel=1e-9)


@pytest.mark.ui
def test_a_curve_reset_before_the_session_writes_nothing(run):
    """`reset_curve` takes the state off, and the file follows the screen.

    The affine is the state, not the values: the reset leaves the numbers where the
    last read left them, and a session written after it draws those numbers again.
    """
    view = run.view()
    frame = run.figure(view, FIRST)
    key = frame.figureKey
    raw = drawn(frame)[FIRST]

    run.core.scale_curve(key, 10.0)
    run.core.reset_curve(key)
    path = QVizSaveSession(run.api, name='reset').execute()
    with open(path) as handle:
        body = handle.read()

    assert '<Transform' not in body
    assert drawn(frame)[FIRST] == pytest.approx(raw, rel=1e-9)

    restored = run.freshApi()
    QVizRestoreSession(restored, path=path).execute()
    assert drawn(restored.figureframes[key])[FIRST] == pytest.approx(raw,
                                                                     rel=1e-9)


@pytest.mark.ui
def test_the_bars_of_a_scaled_curve_come_back_at_the_scaled_extent(run):
    """A bar restored on a dressed curve is drawn once, at its scaled height.

    The affine goes on before the error lines are asked for, which is what the
    order of `applyState` says: put the bars back first and `setTransform` would
    redraw them a second time for nothing -- and a bar that came back at the raw
    extent would be a bar that no longer touches its curve.
    """
    view = run.view()
    frame = run.figure(view, FIRST)
    key = frame.figureKey
    frame.errors.showErrorBars(step=STEP)
    assert len(barsOf(frame)) == 1
    rawTop = barsOf(frame)[0].opts['top'].copy()

    run.core.scale_curve(key, 10.0)
    assert barsOf(frame)[0].opts['top'] == pytest.approx(10. * rawTop,
                                                         rel=1e-9)
    path = QVizSaveSession(run.api, name='bars').execute()

    restored = run.freshApi()
    QVizRestoreSession(restored, path=path).execute()
    again = restored.figureframes[key]

    assert again.errors.errorBarCount() == 1
    assert again.errors.stepUsed() == STEP
    assert barsOf(again)[0].opts['top'] == pytest.approx(10. * rawTop,
                                                         rel=1e-9)
    assert affines(again)[FIRST] == (10.0, 0.0)


@pytest.mark.ui
def test_a_transform_for_a_quantity_the_case_no_longer_holds_is_named(run,
                                                                      caplog):
    """An affine with no trace to dress is said, not put on the trace beside it.

    The quantity of the dressed trace is taken out of the case, as a session
    outliving a re-import of a pulse does it: the file still names it, the tree no
    longer holds it. Half the figure comes back, and the log says which half did
    not and why -- the same shape `test_72` pins for a colour.
    """
    view = run.view()
    frame = run.figure(view, FIRST, SECOND)
    key = frame.figureKey
    raw = drawn(frame)
    run.core.scale_curve(key, 10.0, curve=1)
    path = QVizSaveSession(run.api, name='lost').execute()
    with open(path) as handle:
        body = handle.read()
    with open(path, 'w') as handle:
        handle.write(body.replace('path="%s"' % SECOND,
                                  'path="%s"' % NOT_IN_THE_CASE))

    with caplog.at_level('WARNING'):
        restored = run.freshApi()
        QVizRestoreSession(restored, path=path).execute()

    assert NOT_IN_THE_CASE in caplog.text
    assert 'not put back' in caplog.text
    again = restored.figureframes[key]
    assert affines(again) == {FIRST: (1.0, 0.0)}
    assert drawn(again)[FIRST] == pytest.approx(raw[FIRST], rel=1e-9)


@pytest.mark.ui
def test_a_transform_naming_a_trace_the_window_does_not_draw_is_named(run,
                                                                     caplog):
    """The other half of the same refusal: the quantity is there, the rank is not.

    A quantity read at several rows draws several traces, so a rank is a real
    address, and a file that names a rank past the last this window draws asks for
    a curve that is not on the screen. It costs its own entry: the trace it could
    have dressed by position stays at the values the case answers.
    """
    view = run.view()
    frame = run.figure(view, FIRST, SECOND)
    key = frame.figureKey
    raw = drawn(frame)
    run.core.scale_curve(key, 10.0, curve=0)
    path = QVizSaveSession(run.api, name='past_the_last').execute()
    with open(path) as handle:
        body = handle.read()
    with open(path, 'w') as handle:
        handle.write(body.replace('trace="0"', 'trace="3"'))

    with caplog.at_level('WARNING'):
        restored = run.freshApi()
        QVizRestoreSession(restored, path=path).execute()

    assert 'scales 1 trace(s)' in caplog.text
    again = restored.figureframes[key]
    assert affines(again) == {FIRST: (1.0, 0.0), SECOND: (1.0, 0.0)}
    assert drawn(again)[FIRST] == pytest.approx(raw[FIRST], rel=1e-9)


# ------------------------------------------------------------------- a table

@pytest.mark.ui
def test_a_table_puts_the_affine_back_on_the_panel_it_was_asked_for(run):
    """One panel scaled, its neighbours left at the values the case answers.

    This is the window where the node a panel holds and the node the gesture named
    are two different objects -- the panels are filled from a configuration file the
    command writes -- and the affine still has to find its panel, because the walk
    that saved it and the walk that puts it back are the same walk over the panels.
    """
    view = run.view()
    frame = run.table(view, FIRST, SECOND, THIRD)
    assert len(frame.panels()) == 3
    key = frame.figureKey
    raw = drawn(frame)

    run.core.scale_curve(key, 3.0, curve=1)
    path = QVizSaveSession(run.api, name='panels').execute()

    assert written(QVizSessionFile.read(path), key) \
        == {FIRST: [], SECOND: [(0, 3.0, 0.0)], THIRD: []}

    restored = run.freshApi()
    QVizRestoreSession(restored, path=path).execute()
    again = restored.figureframes[key]
    assert isinstance(again, QVizTablePlot)
    assert affines(again) == {FIRST: (1.0, 0.0), SECOND: (3.0, 0.0),
                              THIRD: (1.0, 0.0)}
    assert drawn(again)[SECOND] == pytest.approx(raw[SECOND] * 3.0, rel=1e-9)
    assert drawn(again)[THIRD] == pytest.approx(raw[THIRD], rel=1e-9)
