# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""*Configure Plot* on the window the manual documents it on.

The manual has described this entry under *Plot Configuration and Customization*
for as long as the dialogue has existed, and the dialogue (T32) has been in the
package all along. What was missing is the **entry**: the three questions the
window asks -- `styleCurves()`, `styleText()`, `styleMargins()` -- were answered
in one class, `CustomizedViewBox`, so a figure of curves and a panel of a Table or
Stacked Plot View had nothing to offer and the documented line was simply not on
their menu.

The curve figure is driven on the reference case (WEST 54924 run 0, pinned at
3.35.0), where the traces, the legend and the two labels come from real data. The
panels are driven on stubs, because what is pinned there is the wiring of a panel
and its palette, not an answer of a case.

The record is the part no screenshot shows, and the reason this file is not just
about a menu item. Every trace carries a pen -- the palette hands one out -- so
"is this curve coloured?" cannot tell the colour a user picked from the one the
cycle picked. What is recorded is therefore *which* traces a hand was on, and the
values are read off the item when someone asks for them: writing all of them would
freeze the palette into the session files.

Four measured facts of pyqtgraph 0.13.7 are pinned here, all of them decided a
shape rather than a detail:

* `LegendItem.ItemSample.paint` reads `self.item.opts` at paint time, so a swatch
  follows a hand-set pen with nothing to maintain -- and the identity of the item
  behind the swatch is what a test can assert.
* `AxisItem.setLabel(text, units=...)` clears nothing: it writes `labelStyle` only
  `if len(args) > 0` (`AxisItem.py:341`), and `text`/`units`/`unitPrefix` are named
  parameters. So the relabel a figure does when the next quantity is added leaves a
  styled axis alone -- which is why no label writer had to change for this feature.
* `LabelItem.setText` merges the keywords it is given (`LabelItem.py:49-51`), so a
  title keeps a size and a bold through `setTitle` too.
* `PlotItem.listDataItems()` answers `PlotDataItem`s only, so the error bars and
  the confidence band a figure can draw are not offered as traces to style.
"""

import pytest

import pyqtgraph as pg
from PySide6.QtCore import QObject

from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
    import QVizLoadOccurrence
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode \
    import QVizPlotOneNode
from imasviz.VizGUI.VizPlot.QVizCurveColors import penFor
from imasviz.VizGUI.VizPlot.QVizPlotStyling import (ENTRY, applyCurveStyle,
                                                    curveStyle, replayCurves,
                                                    sourcesOf, styledTraces)
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPanel import QVizPanel
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizStackedPlot import QVizStackedPlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizTablePlot import QVizTablePlot
from imasviz.VizPlugins.viz_Profiles.viz_profiles.CustomizedViewBox \
    import CONFIGURE_PLOT
from imasviz.VizUtils import QVizPreferences

from conftest import CASE_DATA_DICTIONARY_VERSION, case_uri_or_skip
from support import ownership
from support.fakes import FakeAxesNode

IDS_NAME = 'magnetics'
OCCURRENCE = 0
FIRST = 'magnetics/flux_loop(0)/flux/data'
SECOND = 'magnetics/bpol_probe(0)/field/data'

# What the figure's right click answers, in order: pyqtgraph's own four lines, the
# three of `QVizCurveErrors`, then this row's line. Measured on the reference case.
PYQTGRAPH_LINES = ['View All', 'X axis', 'Y axis', 'Mouse Mode']
ERROR_LINES = ['Show/Hide error bars', 'Show error bars (with slicing)',
               'Show/Hide confidence bands']

# What pyqtgraph leaves a curve drawn without a pen at, measured.
LIBRARY_DEFAULT = (200, 200, 200)
HAND = (255, 0, 0)

# The stub case: a scalar per element of a dynamic array, enough for a panel.
TIMES = [0., 1., 2., 3., 4.]
RHO = [0., 1., 2., 3.]
URI = 'imas:hdf5?case=1'
AOS, LEAF = 'AOS', 'LEAF'

pytestmark = [pytest.mark.ui]


def rgbOf(curve):
    """The colour a trace is drawn with, whether its pen is a QPen or a tuple."""
    pen = curve.opts['pen']
    return pen if isinstance(pen, tuple) else pen.color().getRgb()[:3]


def menuLines(frame):
    """The texts of one view box's menu, separators left out."""
    return [action.text() for action
            in frame.pgPlotWidget.getViewBox().menu.actions() if action.text()]


# --------------------------------------------------------------------- a figure

@pytest.fixture(scope='module')
def session(qapp):
    """One shot view of the reference case, with `magnetics` loaded in it."""
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
    ownership.keep(api)
    ownership.keep(view)
    ownership.keep(frame)
    QVizLoadOccurrence(dataTreeView=view, idsName=IDS_NAME,
                       occurrence=OCCURRENCE, asynch=False).execute()
    return {'view': view, 'api': api,
            'nodes': {node.getPath(): node for node in view.signalsList}}


def figureOf(session, paths=()):
    """A curve figure holding `paths`, drawn the way the shot view draws them."""
    frame = None
    for path in paths:
        frame = QVizPlotOneNode(dataTreeView=session['view'],
                                treeNode=session['nodes'][path],
                                intoFigureKey=None if frame is None
                                else frame.figureKey,
                                alongTime=True).execute()
        assert type(frame) is QVizCurvePlot
    return ownership.keep(frame)


def colourFirstTrace(frame, rgb=HAND):
    """The first row of the window, used the way a user uses a colour button.

    `ColorButton.setColor` does not emit `sigColorChanging` -- that signal is what
    the colour dialogue emits when a user picks -- so a test has to emit it.
    """
    dialog = frame.styling.show()
    row = dialog.curves[0]
    row.colorButton.setColor(rgb)
    row.colorButton.sigColorChanging.emit(row.colorButton)
    return dialog


def test_the_menu_carries_the_line_the_manual_documents(session):
    frame = figureOf(session, [FIRST])

    assert ENTRY not in PYQTGRAPH_LINES + ERROR_LINES
    assert menuLines(frame) == PYQTGRAPH_LINES + ERROR_LINES + [ENTRY]
    # The same words the plugin's menu answers: one window behind both lines.
    assert ENTRY == CONFIGURE_PLOT


def test_the_window_lists_every_trace_under_the_name_the_figure_gives_it(session):
    frame = figureOf(session, [FIRST, SECOND])
    dialog = frame.styling.show()

    legend = [text.text for _, text
              in frame.pgPlotWidget.getPlotItem().legend.items]
    assert [row.curve.opts['name'] for row in dialog.curves] == legend
    assert len(dialog.curves) == frame.curveCount() == 2
    # Two sections: the margins one is for a window that lays panels out, and this
    # figure has one plot over its own controls.
    assert [dialog.tabWidget.tabText(index)
            for index in range(dialog.tabWidget.count())] == \
        ['Curve Properties', 'Text Properties']


def test_a_row_reaches_its_own_trace_and_no_other(session):
    frame = figureOf(session, [FIRST, SECOND])
    before = [rgbOf(curve) for curve in frame.curves()]

    dialog = colourFirstTrace(frame)
    dialog.accept()

    assert rgbOf(frame.curves()[0]) == HAND
    assert rgbOf(frame.curves()[1]) == before[1]
    assert frame.curves()[0].opts['pen'].width() == \
        frame.curves()[1].opts['pen'].width(), 'a row changed a width too'


def test_the_legend_swatch_follows_the_pen(session):
    """No section is needed for the legend, and this is why.

    The swatch reads the curve's own opts when it paints, so what it will show is
    read here off the item it is bound to: a swatch bound to another curve, or to
    nothing, is the bug worth pinning.
    """
    frame = figureOf(session, [FIRST])
    sample = frame.pgPlotWidget.getPlotItem().legend.items[0][0]
    assert sample.item is frame.curves()[0]

    colourFirstTrace(frame).accept()

    assert rgbOf(sample.item) == HAND


def test_a_palette_colour_is_not_a_hand_colour(session):
    """The record, and why it is needed at all.

    Every trace carries a pen, so a session that wrote every one of them would
    freeze the palette into the file and lose the contrast T33 measured the
    colours for. A fresh figure therefore records nothing.
    """
    frame = figureOf(session, [FIRST, SECOND])

    assert styledTraces(frame) == []
    assert frame.styling.styledText() == []
    # And the traces are coloured all the same, by the palette.
    assert rgbOf(frame.curves()[0]) == penFor(0).color().getRgb()[:3]


def test_a_touched_trace_is_recorded_with_its_quantity_and_its_rank(session):
    frame = figureOf(session, [FIRST, SECOND])

    colourFirstTrace(frame).accept()

    recorded = styledTraces(frame)
    assert len(recorded) == 1
    node, index, style = recorded[0]
    assert node is session['nodes'][FIRST]
    assert index == 0
    assert style['color'] == '#ff0000'
    assert style['width'] and style['style'] and style['symbol'] is not None


def test_cancel_takes_the_record_back_with_the_values(session):
    frame = figureOf(session, [FIRST])
    before = rgbOf(frame.curves()[0])

    dialog = colourFirstTrace(frame)
    assert len(styledTraces(frame)) == 1, 'the edit is live, and recorded'
    dialog.reject()

    assert rgbOf(frame.curves()[0]) == before
    assert styledTraces(frame) == []


def test_a_second_window_adds_to_what_an_earlier_one_left(session):
    frame = figureOf(session, [FIRST, SECOND])

    colourFirstTrace(frame).accept()
    dialog = frame.styling.show()
    row = dialog.curves[1]
    row.colorButton.setColor((0, 0, 255))
    row.colorButton.sigColorChanging.emit(row.colorButton)
    dialog.accept()

    assert sorted(rgbOf(curve) for curve in frame.curves()) == \
        sorted([HAND, (0, 0, 255)])
    assert len(styledTraces(frame)) == 2


def test_a_cancelled_window_leaves_an_earlier_colour_recorded(session):
    """The rollback is to what the window found, not to nothing.

    Measured while writing this: rolling the record back to an empty dict handed
    the first colour back too, so a Cancel on the second window un-coloured a
    trace it had never touched.
    """
    frame = figureOf(session, [FIRST, SECOND])
    colourFirstTrace(frame).accept()

    dialog = frame.styling.show()
    row = dialog.curves[1]
    row.colorButton.setColor((0, 0, 255))
    row.colorButton.sigColorChanging.emit(row.colorButton)
    dialog.reject()

    assert [rgbOf(curve) for curve in frame.curves()] == \
        [HAND, penFor(1).color().getRgb()[:3]]
    recorded = styledTraces(frame)
    assert len(recorded) == 1 and recorded[0][0] is session['nodes'][FIRST]


def test_a_colour_survives_the_slider_that_moves_the_curve(session):
    """`refresh` updates in place, so the pen a hand set is not rebuilt."""
    frame = figureOf(session, [FIRST])
    colourFirstTrace(frame).accept()

    assert frame.refresh() is not None
    assert rgbOf(frame.curves()[0]) == HAND
    assert len(styledTraces(frame)) == 1


def test_a_styled_axis_survives_the_next_quantity_relabelling_it(session):
    """The one reason no label writer had to change, pinned where it was measured.

    `QVizCurvePlot.setQuantityLabel` calls `setLabel('left', ...)` for every
    quantity added; `AxisItem.setLabel` writes `labelStyle` only when style
    keywords arrive with the text, so the label keeps what a hand put on it.
    """
    frame = figureOf(session, [FIRST])
    left = frame.styleText().getAxis('left')
    dialog = frame.styling.show()
    editor = [row for row in dialog.axisEditors if row.key == 'left'][0]
    editor.boldButton.toggle()
    editor.sizeBox.setValue(26)
    dialog.accept()

    assert left.labelStyle['font-weight'] == 'bold'
    assert left.labelStyle['font-size'] == '26px'
    textBefore = left.labelText

    frame.plot(session['nodes'][SECOND], as_function_of_time=True)

    assert left.labelText != textBefore, 'the relabel did not happen'
    assert left.labelStyle['font-weight'] == 'bold'
    assert left.labelStyle['font-size'] == '26px'
    assert frame.styling.styledText() == \
        [('left', {'text': left.labelText, 'bold': '1', 'italic': '0',
                  'size': '26px'})]


def test_a_title_a_hand_sized_is_recorded_and_replayed(session):
    frame = figureOf(session, [FIRST])
    dialog = frame.styling.show()
    dialog.titleEditor.sizeBox.setValue(22)
    dialog.titleEditor.boldButton.toggle()
    dialog.accept()

    recorded = dict(frame.styling.styledText())
    assert recorded['title']['size'] == '22px'
    assert recorded['title']['bold'] == '1'

    frame.styleText().titleLabel.setText('')
    frame.styling.replayText([('title', recorded['title'])])
    assert frame.styleText().titleLabel.opts['size'] == '22px'
    assert frame.styleText().titleLabel.opts['bold'] is True


def test_replaying_a_style_lands_on_the_trace_named_and_nowhere_else(session):
    frame = figureOf(session, [FIRST, SECOND])
    node = session['nodes'][SECOND]
    style = {'color': '#0000ff', 'style': 'Dotted Line', 'width': '3',
             'symbol': 'o', 'size': '14', 'fill': '#ff0000',
             'outline': '#00ff00'}
    palette = [penFor(rank).color().getRgb()[:3] for rank in range(2)]

    # The rank counts a trace among the traces of *its own* quantity -- see
    # `tracesForStyling`. A session naming rank 1 for a quantity the case draws
    # as one trace has nothing to style, and must not reach over to the trace of
    # the quantity that happens to sit next to it in the figure.
    assert replayCurves(frame, [(node, 1, style)]) == 0
    assert [rgbOf(curve) for curve in frame.curves()] == palette

    assert replayCurves(frame, [(node, 0, style)]) == 1
    assert rgbOf(frame.curves()[1]) == (0, 0, 255)
    assert frame.curves()[1].opts['symbolSize'] == 14
    assert rgbOf(frame.curves()[0]) == palette[0]
    # A replay is a hand: saving the session again has to keep what came back.
    assert [(n, i) for n, i, _ in styledTraces(frame)] == [(node, 0)]

    assert replayCurves(frame, [(object(), 0, {'color': '#123456'})]) == 0
    assert rgbOf(frame.curves()[0]) == palette[0]


def test_a_style_naming_nothing_the_window_draws_costs_its_entry_only(session):
    frame = figureOf(session, [FIRST])
    node = session['nodes'][FIRST]

    assert replayCurves(frame, [(node, 5, {'color': '#0000ff'})]) == 0
    assert styledTraces(frame) == []


# ---------------------------------------------------------------------- a panel

class _StubIds:
    """One IDS stub: `value<i>` per element of a dynamic array."""

    def __init__(self, leaf, count):
        self.ids_properties = type(str('Props'), (), {})()
        self.ids_properties.homogeneous_time = 1
        self.time = list(TIMES)
        self.rho_tor = list(RHO)
        self.theta_poloidal = [.1 * i for i in range(len(RHO))]
        self.time_slice = []
        for timeIndex in range(len(TIMES)):
            timeSlice = type(str('TimeSlice'), (), {})()
            timeSlice.time = TIMES[timeIndex]
            setattr(timeSlice, leaf, 7. * timeIndex + count)
            self.time_slice.append(timeSlice)


class Node(FakeAxesNode):
    """A leaf held by an array of structures, answering for a window and a tree."""

    def is0DAndDynamic(self):
        return self._dataType == 'FLT_0D'

    def is1DAndDynamic(self):
        return self._dataType == 'FLT_1D'

    def hasTimeAxis(self):
        return True

    def isPlotToPerformAlongTimeAxis(self, plotWidget=None):
        return self.hasTimeAxis()

    def getPath(self):
        return self.getInfoDict().get('Path')

    def getOccurrence(self):
        return self.getInfoDict().get('occurrence')


def _quantity(index):
    leaf = 'value%d' % index
    return Node(_StubIds(leaf, index), 'foo', 'foo.time_slice[itime]', 'FLT_0D',
                name=leaf, itimeIndex=0, coordinates=(), indices={'i': '0'},
                lengths={'i': str(len(TIMES))},
                infoDict={'Path': 'foo/time_slice(i)/' + leaf,
                          'occurrence': 0, 'name': leaf})


@pytest.fixture
def view(qapp, tmp_path, monkeypatch):
    """One shot view of stub data, and the api its figures are registered to."""

    class FakeSource(QObject):
        def __init__(self, uri):
            super().__init__(None)
            self.uri = uri
            self.name = 'NATIVE'

        def dataKey(self, treeNode):
            return treeNode.getParametrizedDataPath()

    class FakeView(QObject):
        def __init__(self):
            super().__init__(None)
            self.uri = URI
            self.dataSource = FakeSource(URI)
            self.selectedItem = None
            self.selectedSignalsDict = {}
            self.signalsList = []

    from PySide6.QtWidgets import QMdiArea
    from imasviz.Viz_API import Viz_API

    monkeypatch.setenv('HOME', str(tmp_path))
    shot = FakeView()
    shot.mdi = QMdiArea()
    shot.imas_viz_api = Viz_API(parent=shot.mdi)
    shot.imas_viz_api.DTVlist = [shot]
    return ownership.keep(shot)


def fill(view, kind, count):
    """The selection drawn into a Table or a Stacked window, as the menu does."""
    nodes = [_quantity(index) for index in range(count)]
    view.signalsList = list(nodes)
    view.selectedSignalsDict = {node.getParametrizedDataPath():
                                {'index': index,
                                 'QTreeWidgetItem': node,
                                 'uri': URI}
                                for index, node in enumerate(nodes)}
    view.selectedItem = nodes[0]
    handling = QVizSignalHandling(view)
    if kind == 'table':
        handling.onPlotToTablePlotView(all_DTV=False, plotAxis='TIME')
    else:
        handling.onPlotToStackedPlotView(all_DTV=False, plotAxis='TIME')
    wanted = QVizTablePlot if kind == 'table' else QVizStackedPlot
    return [frame for frame in view.imas_viz_api.figureframes.values()
            if isinstance(frame, wanted)][0]


@pytest.mark.parametrize('kind', ['table', 'stacked'])
def test_every_panel_offers_the_line_on_its_own_right_click(view, kind):
    frame = fill(view, kind, 3)

    assert all(isinstance(panel, QVizPanel) for panel in frame.panels())
    for panel in frame.panels():
        assert ENTRY in menuLines(panel), \
            'a %s window offers no way to style its panels' % kind
        # The menu is the view box's own: styling one panel cannot reach its
        # neighbour, and one panel's window lists one curve.
        dialog = panel.styling.show()
        assert len(dialog.curves) == panel.curveCount() == 1
        assert [dialog.tabWidget.tabText(index)
                for index in range(dialog.tabWidget.count())] == \
            ['Curve Properties', 'Text Properties']


@pytest.mark.parametrize('kind', ['table', 'stacked'])
def test_a_panel_draws_the_palette_and_not_pyqtgraphs_grey(view, kind):
    """The defect the colour row left behind in these two windows.

    `penFor` was asked by the curve figure alone, so every trace of a panel came
    out the library's (200, 200, 200) -- the same grey twice over on a window
    whose purpose is to compare quantities.
    """
    frame = fill(view, kind, 2)

    colours = [rgbOf(curve) for panel in frame.panels()
               for curve in panel.curves()]
    assert colours == [penFor(0).color().getRgb()[:3],
                       penFor(0).color().getRgb()[:3]]
    assert LIBRARY_DEFAULT not in colours


@pytest.mark.parametrize('kind', ['table', 'stacked'])
def test_a_window_of_panels_records_each_panel_apart(view, kind):
    frame = fill(view, kind, 2)

    assert sourcesOf(frame) == frame.panels()
    first, second = frame.panels()

    dialog = first.styling.show()
    dialog.curves[0].colorButton.setColor(HAND)
    dialog.curves[0].colorButton.sigColorChanging.emit(
        dialog.curves[0].colorButton)
    dialog.accept()

    recorded = styledTraces(frame)
    assert len(recorded) == 1, 'styling one panel coloured the record of another'
    node, index, style = recorded[0]
    assert node is first.treeNode
    assert index == 0 and style['color'] == '#ff0000'
    assert rgbOf(second.curves()[0]) == penFor(0).color().getRgb()[:3]


def test_a_panel_window_replays_onto_the_panel_that_draws_the_quantity(view):
    frame = fill(view, 'table', 2)
    first, second = frame.panels()

    applied = replayCurves(frame, [(second.treeNode, 0,
                                    {'color': '#00ff00', 'width': '4'})])

    assert applied == 1
    assert rgbOf(second.curves()[0]) == (0, 255, 0)
    assert rgbOf(first.curves()[0]) == penFor(0).color().getRgb()[:3]
    assert [(node, index) for node, index, _ in styledTraces(frame)] == \
        [(second.treeNode, 0)]


def test_the_module_functions_answer_a_curve_figure_as_one_source(session):
    frame = figureOf(session, [FIRST])

    assert sourcesOf(frame) == [frame]
    assert [node is session['nodes'][FIRST]
            for node, _, _ in frame.tracesForStyling()] == [True]
    assert applyCurveStyle(frame.curves()[0], {'color': '#010203'}) is None
    assert rgbOf(frame.curves()[0]) == (1, 2, 3)
    assert curveStyle(frame.curves()[0])['color'] == '#010203'
