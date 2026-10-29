# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Error bars and confidence bands, on the figure that drew the curve.

The manual promises three lines in the right-click menu of a plot -- *Show/Hide
error bars*, *Show error bars (with slicing)*, *Show/Hide confidence bands* --
"if data for fields error_upper and/or error_lower are available"
(`plotting_1d_arrays.rst`, *Basic plot display features* and *Displaying error
bars and/or confidence bands*). Until this row, only the Profiles plugin answered
them, from a copy of the whole behaviour written inside its view box, and a curve
drawn by *Plot selected nodes to -> Figure* answered pyqtgraph's own four lines
and nothing else. So the behaviour was written once, in `QVizCurveErrors`, the
plugin's copy was deleted (202 lines out of that file, 445 down to 272), and what
is pinned here is what the reference case answers through it.

Measured on WEST 54924 run 0, dictionary **3.35.0**, `magnetics` occurrence 0 --
**6058** signal nodes, of which **1681** carry both an `_error_upper` and an
`_error_lower` sibling and **4377** carry neither:

* `magnetics/flux_loop(0)/flux/data` along time: **17344** points, an upper
  holding **17344** values and **no** lower. One `ErrorBarItem` is drawn over all
  of them, and because only one side of the error is held, the bar is symmetric:
  `top` and `bottom` are the same array.
* The beam is **0,072851** s. The raw value -- the span 72,850972 s over 17344
  samples -- is **0,0042** s, and a bar one sample wide on that record is
  invisible, which is why the bound at `span/1000` is there.
* Slicing at **3** draws **5782** bars, the last one at x = **74,686744...**,
  which is the last sample of the curve. The plugin's copy asked
  `x[0:len(x)-1:3]` and drew **5781**: it dropped the last sample, and with it the
  end of the curve.
* A band is three items -- the two borders and the `FillBetweenItem` between them
  -- so a figure holding one curve goes from **1** view-box item to **4**. The
  upper border of `flux/data` starts at **0,01619676...** where the curve starts
  at **0,00619676...**: the band is the error, added and subtracted.
* A quantity with no error sibling at all (`magnetics/time`) draws nothing and is
  named in the log of its own case. It is not an error the user is left to guess.

The step question is a modal `QInputDialog`, so it is recorded here rather than
answered by hand -- the same reason the Profiles occurrence question is recorded
in `test_51`. Asked: `(None, 'Enter a step value for slicing', 'Step:', 10, 1)`.
Refusing it changes nothing: no bar, no new item.

The package re-exports `QVizCurveErrors` under the module's own name, so patching
that name reaches the class and leaves the module's `QInputDialog` alone -- which
is how a first probe spent 300 s inside a modal dialog instead of failing. The
patch below goes through `sys.modules`, which is what the module's globals are.
"""

import logging
import sys
import weakref

import pytest

import pyqtgraph as pg

from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
    import QVizLoadOccurrence
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode \
    import QVizPlotOneNode
from imasviz.VizGUI.VizPlot.QVizCurveErrors import (CONFIDENCE_BANDS,
                                                    ERROR_BARS,
                                                    ERROR_BARS_SLICED,
                                                    QVizCurveErrors)
from imasviz.VizGUI.VizPlot.QVizPlotStyling import ENTRY
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizImagePlot import QVizImagePlot
from imasviz.VizPlugins.viz_Profiles.viz_profiles.CustomizedViewBox \
    import CustomizedViewBox
from imasviz.VizUtils import QVizPreferences

from conftest import (CASE_DATA_DICTIONARY_VERSION, case_uri_or_skip)
from support import ownership

IDS_NAME = 'magnetics'
OCCURRENCE = 0
WITH_ERRORS = 'magnetics/flux_loop(0)/flux/data'
WITHOUT_ERRORS = 'magnetics/time'
SECOND = 'magnetics/bpol_probe(0)/field/data'

# pyqtgraph's own four lines, then the three this row carries onto the figure,
# then the styling line the Configure Plot row carries. Measured on a curve figure
# of the reference case, in menu order.
PYQTGRAPH_LINES = ['View All', 'X axis', 'Y axis', 'Mouse Mode']
DOCUMENTED_LINES = [ERROR_BARS, ERROR_BARS_SLICED, CONFIDENCE_BANDS]
STYLING_LINE = ENTRY

# What the case answers for `magnetics/flux_loop(0)/flux/data` along time.
POINTS = 17344
BEAM = 0.072851
RAW_BEAM = 0.0042
SPAN = 72.850972
STEP = 3
SLICED_POINTS = 5782
# What the plugin's copy would have drawn at the same step, for the record.
DROPPED_LAST = 5781
BAND_ITEMS = 3
BORDER_TOP = 0.016196762677282095
BORDER_BASE = 0.006196762900799513

# Named so a frame built by the cycle guard below can be told from the rest in a
# report -- the harness's ownership watch names frames by their object name.
CYCLE_GUARD = 'errorsCycleGuard'

pytestmark = [pytest.mark.case, pytest.mark.dd, pytest.mark.ui]


@pytest.fixture(scope='module')
def session(qapp):
    """One shot view of the reference case, with `magnetics` loaded in it.

    `qapp` is not decoration: this fixture builds a `QMainWindow`, and a Qt
    widget built before the `QApplication` exists aborts the process where it
    stands -- measured here as `Fatal Python error: Aborted` inside
    `QVizDataTreeViewFrame.__init__`, with nothing in the output naming either
    the widget or the reason.
    """
    uri = case_uri_or_skip()
    if uri is None:
        pytest.skip('the reference case is not on disk')

    QVizPreferences().build()
    from imasviz.Viz_API import Viz_API

    api = Viz_API()
    source = QVizDataSourceFactory().create(uri)
    source.dd_version = CASE_DATA_DICTIONARY_VERSION
    frame = api.CreateDataTree(source)
    view = frame.dataTreeView
    # The view and its api are what holds the loaded occurrence alive: a test
    # that only kept the view could drop the api underneath it.
    ownership.keep(api)
    ownership.keep(view)
    ownership.keep(frame)
    QVizLoadOccurrence(dataTreeView=view, idsName=IDS_NAME,
                       occurrence=OCCURRENCE, asynch=False).execute()
    return {'view': view, 'api': api,
            'nodes': {node.getPath(): node for node in view.signalsList}}


def plotOf(session, path, alongTime=True):
    """One quantity, drawn by the entry the shot view uses, held for the run."""
    frame = QVizPlotOneNode(dataTreeView=session['view'],
                            treeNode=session['nodes'][path],
                            alongTime=alongTime).execute()
    assert type(frame) is QVizCurvePlot
    return ownership.keep(frame)


def barsOf(frame):
    return [item for item in frame.pgPlotWidget.getViewBox().addedItems
            if isinstance(item, pg.ErrorBarItem)]


def fillsOf(frame):
    return [item for item in frame.pgPlotWidget.getViewBox().addedItems
            if isinstance(item, pg.FillBetweenItem)]


@pytest.fixture
def stepQuestion(monkeypatch):
    """The step question, recorded and answered with `STEP`.

    Reached through `sys.modules`: the package binds the name
    `imasviz.VizGUI.VizPlot.QVizCurveErrors` to the class, so setting an
    attribute there patches the class and leaves the module's global alone.
    """
    module = sys.modules[QVizCurveErrors.__module__]

    class Asked:
        questions = []

        @staticmethod
        def getInt(parent, title, label, value, minValue):
            Asked.questions.append((parent, title, label, value, minValue))
            return (STEP, True)

    monkeypatch.setattr(module, 'QInputDialog', Asked)
    return Asked


@pytest.mark.ui
def test_the_figure_answers_the_three_lines_the_manual_names(session):
    frame = plotOf(session, WITH_ERRORS)

    texts = [action.text() for action
             in frame.pgPlotWidget.getViewBox().menu.actions()
             if action.text()]
    assert texts == PYQTGRAPH_LINES + DOCUMENTED_LINES + [STYLING_LINE], texts
    assert [line for line in DOCUMENTED_LINES if line not in texts] == []


@pytest.mark.ui
def test_the_bars_are_drawn_over_the_curve_that_was_drawn(session):
    frame = plotOf(session, WITH_ERRORS)
    x, y = frame.curves()[0].getData()
    assert len(x) == POINTS

    frame.errors.toggleErrorBars()
    bars = barsOf(frame)
    assert len(bars) == 1
    assert frame.errors.errorBarCount() == 1
    # `ErrorBarItem` has no getData(): what was set is read back through opts.
    assert len(bars[0].opts['x']) == POINTS
    assert (bars[0].opts['x'] == x).all()
    assert (bars[0].opts['y'] == y).all()


@pytest.mark.ui
def test_a_beam_one_sample_wide_is_widened_to_something_visible(session):
    frame = plotOf(session, WITH_ERRORS)
    x, _ = frame.curves()[0].getData()
    assert (x.max() - x.min()) == pytest.approx(SPAN, abs=1e-6)
    assert (x.max() - x.min()) / len(x) == pytest.approx(RAW_BEAM, abs=1e-6)

    frame.errors.showErrorBars()
    assert barsOf(frame)[0].opts['beam'] == pytest.approx(BEAM, abs=1e-6)


@pytest.mark.ui
def test_one_side_of_the_error_draws_a_symmetric_bar(session):
    """The case fills `flux/data_error_upper` and leaves `_error_lower` empty.

    "One sibling and not the other" is not a dictionary shape -- measured, no
    node of this occurrence holds only one -- it is this case leaving one side
    unfilled. The known side is what bounds the value, so the bar is symmetric.
    """
    node = session['nodes'][WITH_ERRORS]
    frame = plotOf(session, WITH_ERRORS)
    assert node.get_data_error_lower(frame.curves()[0]) is None
    assert node.get_data_error_upper(frame.curves()[0]) is not None

    frame.errors.showErrorBars()
    bar = barsOf(frame)[0]
    assert (bar.opts['top'] == bar.opts['bottom']).all()


@pytest.mark.ui
def test_a_second_click_on_the_entry_takes_the_bars_away(session):
    frame = plotOf(session, WITH_ERRORS)
    assert frame.errors.toggleErrorBars() is True
    assert len(frame.pgPlotWidget.getViewBox().addedItems) == 2

    assert frame.errors.toggleErrorBars() is False
    assert frame.errors.errorBarCount() == 0
    assert barsOf(frame) == []
    assert len(frame.pgPlotWidget.getViewBox().addedItems) == 1


@pytest.mark.ui
def test_slicing_asks_its_step_and_keeps_the_end_of_the_curve(session,
                                                               stepQuestion):
    frame = plotOf(session, WITH_ERRORS)
    x, _ = frame.curves()[0].getData()

    assert frame.errors.toggleSlicedErrorBars() is True
    assert stepQuestion.questions == [(None, 'Enter a step value for slicing',
                                       'Step:', 10, 1)]
    assert frame.errors.stepUsed() == STEP
    bars = barsOf(frame)
    assert len(bars[0].opts['x']) == SLICED_POINTS
    assert len(x[::STEP]) == SLICED_POINTS
    # The plugin's slice, `x[0:len(x)-1:STEP]`, answered DROPPED_LAST here: it
    # left the last sample -- and the end of the curve -- without a bar.
    assert len(x[0:len(x) - 1:STEP]) == DROPPED_LAST
    assert bars[0].opts['x'][-1] == x[-1]


@pytest.mark.ui
def test_a_refused_step_question_changes_nothing(session, monkeypatch):
    module = sys.modules[QVizCurveErrors.__module__]

    class Refused:
        @staticmethod
        def getInt(parent, title, label, value, minValue):
            return (10, False)

    monkeypatch.setattr(module, 'QInputDialog', Refused)
    frame = plotOf(session, WITH_ERRORS)

    assert frame.errors.toggleSlicedErrorBars() is False
    assert frame.errors.errorBarCount() == 0
    assert len(frame.pgPlotWidget.getViewBox().addedItems) == 1


@pytest.mark.ui
def test_a_band_is_two_borders_and_the_fill_between_them(session):
    frame = plotOf(session, WITH_ERRORS)
    x, y = frame.curves()[0].getData()
    assert len(frame.pgPlotWidget.getViewBox().addedItems) == 1

    assert frame.errors.toggleConfidenceBands() is True
    assert frame.errors.bandCount() == 1
    assert len(fillsOf(frame)) == 1
    assert len(frame.pgPlotWidget.getViewBox().addedItems) == 1 + BAND_ITEMS

    # The curve of the figure is a PlotDataItem too: the band's own two borders
    # are the ones that are not a curve this figure drew.
    borders = [item for item in frame.pgPlotWidget.getViewBox().addedItems
               if isinstance(item, pg.PlotDataItem)
               and item not in frame.curves()]
    assert len(borders) == 2
    tops = sorted(border.getData()[1][0] for border in borders)
    assert y[0] == pytest.approx(BORDER_BASE, rel=1e-9)
    assert tops[1] == pytest.approx(BORDER_TOP, rel=1e-9)
    assert tops[0] == pytest.approx(2 * y[0] - tops[1], rel=1e-9)

    assert frame.errors.toggleConfidenceBands() is False
    assert frame.errors.bandCount() == 0
    assert fillsOf(frame) == []
    assert len(frame.pgPlotWidget.getViewBox().addedItems) == 1


@pytest.mark.ui
def test_a_quantity_added_afterwards_joins_the_bars_already_drawn(session):
    frame = plotOf(session, WITH_ERRORS)
    frame.errors.toggleErrorBars()
    assert frame.errors.errorBarCount() == 1

    assert frame.plot(session['nodes'][SECOND]) == 1
    assert frame.curveCount() == 2
    assert frame.errors.errorBarCount() == 2


@pytest.mark.ui
def test_a_quantity_holding_no_error_is_refused_by_name(session):
    """The refusal is told, not swallowed -- in the log of its own case.

    Heard on the logger the shot view names itself with, which is the name the
    log panel of that window shows: a handler on the root would miss it if the
    case logger stopped propagating, and the whole point is that the user of
    *this* case is the one told.
    """
    frame = plotOf(session, WITHOUT_ERRORS)
    node = session['nodes'][WITHOUT_ERRORS]
    named = node.getParametrizedDataPath() or node.getName()
    records = []

    class Grabber(logging.Handler):
        def emit(self, record):
            records.append((record.name, record.levelname, record.getMessage()))

    logger = logging.getLogger(session['view'].uri)
    handler = Grabber()
    logger.addHandler(handler)
    try:
        frame.errors.toggleErrorBars()
    finally:
        logger.removeHandler(handler)

    assert frame.errors.errorBarCount() == 0
    assert barsOf(frame) == []
    assert records == [(session['view'].uri, 'ERROR',
                        'No error data available for: %s' % named)], records


@pytest.mark.ui
def test_bars_and_bands_are_read_again_when_the_curve_is_read_again(session):
    """A frame re-reads its curves on every slice move; the bars must move too."""
    frame = plotOf(session, WITH_ERRORS)
    frame.errors.showErrorBars()
    frame.errors.showConfidenceBands()
    before = barsOf(frame)[0].opts['x'].copy()
    items = len(frame.pgPlotWidget.getViewBox().addedItems)

    frame.refresh()
    assert len(frame.pgPlotWidget.getViewBox().addedItems) == items
    assert (barsOf(frame)[0].opts['x'] == before).all()
    assert (barsOf(frame)[0].opts['x'] == frame.curves()[0].getData()[0]).all()
    assert frame.errors.bandCount() == 1
    assert len(fillsOf(frame)) == 1


@pytest.mark.ui
def test_the_plugin_window_draws_its_bars_through_the_same_object(session):
    """The move, from the other side: what the plugin kept is the menu only.

    Its copy of the drawing code is gone; the view box still offers the three
    lines, and what they call is the shared object, fed by the pairing this
    window holds between a node and the curves it drew for it.
    """
    holder = pg.PlotWidget()
    ownership.keep(holder)
    box = CustomizedViewBox(qWidgetParent=holder, imas_viz_api=session['api'])
    ownership.keep(box)

    node = session['nodes'][WITH_ERRORS]
    frame = plotOf(session, WITH_ERRORS)
    curve = frame.curves()[0]
    box.addVizTreeNode(node)
    box.addVizTreeNodeDataItems(node, [curve])

    assert box.errors.viewBox is box
    assert [pair[1] for pair in box.errorQuantities()] == [curve]

    assert box.errors.toggleErrorBars() is True
    assert box.errors.errorBarCount() == 1
    assert len([item for item in box.addedItems
                if isinstance(item, pg.ErrorBarItem)]) == 1
    assert box.errors.toggleErrorBars() is False
    assert box.errors.errorBarCount() == 0


@pytest.mark.ui
def test_the_bars_belong_to_the_curve_figure_and_the_image_figure_has_none(qapp):
    """Why the manual can say an :guilabel:`Image` figure answers no error line.

    Not a menu quirk but what each frame draws: a bar and a band are read off a
    curve and the node that curve came from, so the object holding them is built
    by the frame that draws curves -- and by the plugin's view box, which draws
    them too. An image frame draws pictures and builds neither, which is what the
    note under *Basic plot display features* states. Pinned because that sentence
    is negative, and because handing the object to a frame with no curve to read
    it from is exactly how the sentence becomes a lie.
    """
    curveFrame = QVizCurvePlot(title='errorsCurveGuard')
    imageFrame = QVizImagePlot(title='errorsImageGuard')
    ownership.keep(curveFrame)
    ownership.keep(imageFrame)

    assert isinstance(curveFrame.errors, QVizCurveErrors)
    assert not hasattr(imageFrame, 'errors'), (
        'the image frame was handed an errors object it has no curve to feed')


@pytest.mark.ui
def test_the_errors_object_never_holds_its_figure_alive(qapp):
    """The one argument that decides whether a dropped figure dies or crashes.

    `QVizCurveErrors` has to ask the figure which curve came from which node, and
    it has to still be able to ask once the figure is gone. Handing it
    `self.errorQuantities` -- a bound method, so a reference back -- makes the
    figure and the object one cycle: the figure then survives its last reference
    and is freed inside the cyclic collector instead of at its refcount, and a Qt
    widget freed there is freed while Qt still owes it a paint event.

    Measured, on the file the harness dedicates to exactly that hazard
    (`tests/test_44_plot_frame_ownership.py`, which drops a shown frame and calls
    `gc.collect()`): with the bound method held, `Fatal Python error: Segmentation
    fault` inside `gc.collect()`, 2 runs out of 2, while the same file on the
    commit before this row passes 3 out of 3. Bisected in a throw-away worktree:
    dropping the menu entries leaves the crash in place (2/2), replacing the bound
    method with a function takes it away (0/2) -- the entries are innocent, the
    cycle is not.
    """
    frame = QVizCurvePlot(title=CYCLE_GUARD)
    frame.setObjectName(CYCLE_GUARD)
    errors = frame.errors
    figure = weakref.ref(frame)

    del frame
    assert figure() is None, (
        'the errors object still reaches the figure that owns it: a reference '
        'cycle, so the figure is freed by the collector rather than at its '
        'refcount -- which is what takes a run down when it drops a shown frame')
    # And the answer it gives afterwards is the harmless one, not an exception:
    # a figure that is gone has no curve left to put a bar on.
    assert errors.quantities() == []
