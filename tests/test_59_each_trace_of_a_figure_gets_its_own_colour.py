# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Every trace of a curve figure gets a colour of its own.

Six entries lay a second trace on a figure the user is already looking at --
*Plot X to -> Figure -> New*, the same with an open figure named, *Plot selected
nodes to -> Figure -> New -> This/All IMAS Databases*, the same into an open
figure, a plugin's *plot to figure*, and the two scripting wrappers -- and all six
end in `QVizCurvePlot.plot()`. Until now that call drew without a pen, and
pyqtgraph **0.13.7** answers a curve drawn without one with `opts['pen'] ==
(200, 200, 200)`, an instance default: the library holds no colour cycle at all
(`colorCycle`, `colorLists`, `currentColor`: **0** occurrence in the package). So
the comparison a curve figure exists for was drawn twice in the same grey.
Measured on the reference case before the change: the figure holding
`magnetics/flux_loop(0)/flux/data` and `magnetics/bpol_probe(0)/field/data` answered
`tuple(200, 200, 200)` for **both** curves, and so did the selection figure built
from **3** selected nodes (**2** traces drawn, the third refused for want of
values along the plotted axis).

What is pinned here, measured after it:

* those two traces answer **(255, 140, 0)** then **(0, 255, 255)**, in the order
  they were laid down, and the legend keeps one entry per quantity;
* the palette is legible on the background those figures paint -- **(0, 0, 0,
  255)**, the configuration default `background 'k'`, which nothing in `imasviz`
  changes for a curve figure -- so it holds no near-black and no near-white, and
  it holds **no pure red**: the confidence band of `QVizCurveErrors` is filled
  with `(255, 0, 0)` in `DiagCrossPattern`, and a trace in the colour of the band
  over it is the confusion this row removes, not one it should bring back;
* a band is not a trace: its two borders keep the library's `(200, 200, 200)`,
  because they are read off a curve rather than being one, and they take no place
  in the cycle;
* several rows of one quantity are several traces, so they take several colours
  **and** several legend labels -- `path[0]`, `path[1]` -- where the path alone
  would have named two different lines identically. The reference case answers
  **one** row for every quantity read along time (`y.shape == (1, 17344)`), so
  that loop is exercised through a read asked to answer several.
"""

import numpy as np
import pytest

import pyqtgraph as pg

from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
    import QVizLoadOccurrence
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectNodes \
    import QVizSelectNodes
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsSlices \
    import QVizPlotAsSlices
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode \
    import QVizPlotOneNode
from imasviz.VizGUI.VizPlot.QVizCurveColors import (CURVE_COLOURS, CYCLE,
                                                    colourFor, nameFor)
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizImagePlot import QVizImagePlot
from imasviz.VizUtils import QVizPreferences

from conftest import (CASE_DATA_DICTIONARY_VERSION, case_uri_or_skip)
from support import ownership

IDS_NAME = 'magnetics'
OCCURRENCE = 0
FIRST = 'magnetics/flux_loop(0)/flux/data'
SECOND = 'magnetics/bpol_probe(0)/field/data'
# What the legend has to say for those two nodes: the path of the element, with
# the array index the tree carries spelled out. A legend spelling `flux_loop[i]`
# says a trace came from some element and not which, which is how two traces of
# one array came to be the same curve twice without anyone being able to see it.
FIRST_ELEMENT = 'magnetics.flux_loop[0].flux.data'
SECOND_ELEMENT = 'magnetics.bpol_probe[0].field.data'
# A leaf the case holds no value for along the plotted axis: selected with the
# other two, it is refused by name and draws no trace.
NO_VALUE = 'magnetics/bpol_probe(0)/voltage/data'

# What the two traces of the reference figure answer, measured.
FIRST_RGB = (255, 140, 0)
SECOND_RGB = (0, 255, 255)
POINTS = 17344

# What pyqtgraph gives a curve drawn without a pen, and what the confidence band
# is filled with: neither may be a colour of the palette.
LIBRARY_DEFAULT = (200, 200, 200)
BAND_RGB = (255, 0, 0)

pytestmark = [pytest.mark.case, pytest.mark.dd, pytest.mark.ui]


@pytest.fixture(scope='module')
def session(qapp):
    """One shot view of the reference case, with `magnetics` loaded in it.

    `qapp` is not decoration: this fixture builds a `QMainWindow`, and a Qt
    widget built before the `QApplication` exists aborts the process where it
    stands.
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
    # The view and its api are what holds the loaded occurrence alive.
    ownership.keep(api)
    ownership.keep(view)
    ownership.keep(frame)
    QVizLoadOccurrence(dataTreeView=view, idsName=IDS_NAME,
                       occurrence=OCCURRENCE, asynch=False).execute()
    return {'view': view, 'api': api,
            'nodes': {node.getPath(): node for node in view.signalsList}}


def rgbOf(curve):
    """The colour the curve is drawn with, as the library will paint it.

    A pen left unset is a bare tuple; a pen the figure set is a `QPen`. Read
    through one helper so a test cannot mistake one for the other.
    """
    pen = curve.opts['pen']
    if isinstance(pen, tuple):
        return pen
    return pen.color().getRgb()[:3]


def legendOf(figure):
    """The legend's labels, in the order the traces were drawn.

    A legend entry is a `(sample, LabelItem)` pair, and a `LabelItem` keeps its
    string in `.text`: it has no `toPlainText()`.
    """
    return [text.text for _, text in figure.pgPlotWidget.getPlotItem().legend.items]


def plotOne(session, path, intoFigureKey=None, alongTime=True):
    """One quantity, drawn by the entry the shot view uses, held for the run."""
    frame = QVizPlotOneNode(dataTreeView=session['view'],
                            treeNode=session['nodes'][path],
                            intoFigureKey=intoFigureKey,
                            alongTime=alongTime).execute()
    assert type(frame) is QVizCurvePlot
    return ownership.keep(frame)


class SeveralRows:
    """A read asked to answer several rows for one quantity.

    The row loop of `QVizCurvePlot.plot` is the frame's own contract, and it is
    unreachable through the real read: every quantity of the reference case read
    along time comes back as `y.shape == (1, 17344)`. So the loop is exercised by
    wrapping the real read and repeating its answer, which keeps the axes, the
    values and the slice controls real and changes only how many rows they cover.
    """

    def __init__(self, real, rows):
        self._real = real
        self._rows = rows

    def plan(self, treeNode, plotWidget=None, as_function_of_time=None,
             abscissa=None):
        return self._real.plan(treeNode, plotWidget, as_function_of_time,
                               abscissa)

    def slicesFor(self, treeNode, **kargs):
        return self._real.slicesFor(treeNode, **kargs)

    def GetSignal(self, treeNode, plotWidget=None, as_function_of_time=None,
                  slices=None, abscissa=None):
        x, y = self._real.GetSignal(treeNode=treeNode, plotWidget=plotWidget,
                                    as_function_of_time=as_function_of_time,
                                    slices=slices, abscissa=abscissa)
        return x[:1], np.repeat(y[:1], self._rows, axis=0)


def figureDrawingRows(session, path, rows):
    """A figure holding one quantity read at `rows` rows, held for the run."""
    from imasviz.VizDataAccess.QVizTensorDataAccess import QVizTensorDataAccess

    frame = ownership.keep(QVizCurvePlot(title='rowsFigure'))
    node = session['nodes'][path]
    read = SeveralRows(QVizTensorDataAccess(node.getDataSource()), rows)
    frame.accessFor = lambda treeNode: read
    assert frame.plot(node, as_function_of_time=True) == rows
    return frame, node


@pytest.mark.ui
def test_two_quantities_of_one_figure_are_not_the_same_colour(session):
    """"Plot X to -> Figure -> <open figure>": the second trace joins the first."""
    first = plotOne(session, FIRST)
    same = plotOne(session, SECOND, intoFigureKey=first.figureKey)
    assert same is first
    assert first.curveCount() == 2

    assert rgbOf(first.curves()[0]) == FIRST_RGB
    assert rgbOf(first.curves()[1]) == SECOND_RGB
    assert len({rgbOf(curve) for curve in first.curves()}) == 2
    # The legend still says which trace is which quantity -- and says it with the
    # element each trace came from, not with the array's loop letter.
    assert legendOf(first) == [FIRST_ELEMENT, SECOND_ELEMENT]


@pytest.mark.ui
def test_the_selection_figure_colours_every_trace_it_drew(session):
    """"Plot selected nodes to -> Figure -> New": one shared figure, n colours.

    Three nodes are selected, and only two draw: the third holds no value along
    the plotted axis and is refused by name in the log of its case, so it takes no
    colour and no place in the cycle.
    """
    select = QVizSelectNodes(dataTreeView=session['view'])
    for path in (FIRST, SECOND, NO_VALUE):
        select.selectNode(session['nodes'][path], session['view'])
    assert len(session['view'].selectedSignalsDict) == 3

    figures = QVizPlotAsSlices(dataTreeView=session['view'],
                               all_DTV=False).execute()
    assert len(figures) == 1
    figure = ownership.keep(figures[0])
    assert figure.curveCount() == 2
    assert [rgbOf(curve) for curve in figure.curves()] == [FIRST_RGB, SECOND_RGB]
    assert len(figure.curves()[0].getData()[0]) == POINTS


@pytest.mark.ui
def test_several_rows_of_one_quantity_have_their_colour_and_their_label(session):
    """Two traces of one quantity: two colours and two legend entries.

    The path alone names both rows identically, which is how a legend comes to
    hold the same words twice and say nothing.
    """
    figure, node = figureDrawingRows(session, FIRST, 3)

    assert figure.curveCount() == 3
    assert rgbOf(figure.curves()[0]) == colourFor(0)
    assert rgbOf(figure.curves()[1]) == colourFor(1)
    assert rgbOf(figure.curves()[2]) == colourFor(2)
    assert len({rgbOf(curve) for curve in figure.curves()}) == 3
    assert legendOf(figure) == ['%s[%d]' % (FIRST_ELEMENT, row)
                                for row in range(3)]


@pytest.mark.ui
def test_the_palette_cycles_under_a_figure_longer_than_it_is(session):
    """A selection longer than the palette repeats a colour rather than failing.

    Repeating is what the cycle means; what must not happen is running off the
    end of the list, which would leave a trace with no colour at all.
    """
    figure, _ = figureDrawingRows(session, FIRST, CYCLE + 1)

    assert figure.curveCount() == CYCLE + 1
    assert rgbOf(figure.curves()[CYCLE]) == rgbOf(figure.curves()[0])
    assert nameFor(CYCLE) == nameFor(0)
    for index in range(CYCLE):
        assert rgbOf(figure.curves()[index]) == colourFor(index)


@pytest.mark.ui
def test_moving_a_slice_takes_the_colours_back_with_the_curves(session):
    """`refresh` re-reads the samples through `setData`, so the pen survives.

    The colour moving under the user's hand while they drag a slice control is
    the one thing this change could have cost them.
    """
    first = plotOne(session, FIRST)
    plotOne(session, SECOND, intoFigureKey=first.figureKey)
    before = [rgbOf(curve) for curve in first.curves()]
    samples = [len(curve.getData()[0]) for curve in first.curves()]

    first.refresh()

    assert [rgbOf(curve) for curve in first.curves()] == before
    assert [len(curve.getData()[0]) for curve in first.curves()] == samples


@pytest.mark.ui
def test_a_band_is_not_a_trace_and_takes_no_colour_of_its_own(session):
    """The band keeps the library's grey borders over a red fill.

    Its borders are read off a curve, they are not one: they take no place in the
    cycle, and a user comparing two traces is never comparing two of these.
    """
    first = plotOne(session, FIRST)
    first.errors.showConfidenceBands()
    added = first.pgPlotWidget.getViewBox().addedItems
    fills = [item for item in added if isinstance(item, pg.FillBetweenItem)]
    borders = [item for item in added if isinstance(item, pg.PlotDataItem)
               and item not in first.curves()]

    assert len(fills) == 1
    assert fills[0].brush().color().getRgb()[:3] == BAND_RGB
    assert len(borders) == 2
    assert [rgbOf(border) for border in borders] == [LIBRARY_DEFAULT,
                                                     LIBRARY_DEFAULT]
    # And the traces under it keep the colours they were given.
    assert rgbOf(first.curves()[0]) == FIRST_RGB


@pytest.mark.ui
def test_no_colour_of_the_palette_is_the_grey_it_replaces_or_the_red_of_a_band():
    """The palette answers on the background those figures paint.

    Measured: a curve figure paints `(0, 0, 0, 255)`, so a near-black colour
    would read as background and the `(200, 200, 200)` this row replaces would
    read as an uncoloured trace. Two consecutive colours being equal would put
    the same grey back, one entry apart.
    """
    assert CYCLE == len(CURVE_COLOURS)
    assert LIBRARY_DEFAULT not in [rgb for _, rgb in CURVE_COLOURS]
    assert BAND_RGB not in [rgb for _, rgb in CURVE_COLOURS]

    for index in range(CYCLE):
        assert colourFor(index) == CURVE_COLOURS[index][1]
        # Legible on black: one channel at full strength.
        assert max(colourFor(index)) == 255
        assert min(colourFor(index)) <= 140, (
            '%s reads as background noise on the black these figures paint'
            % nameFor(index))
        following = colourFor(index + 1)
        assert sum((a - b) ** 2 for a, b in zip(colourFor(index), following)) \
            > 20000, ('%s then %s: two traces the user cannot tell apart'
                      % (nameFor(index), nameFor(index + 1)))


@pytest.mark.ui
def test_a_picture_figure_has_no_trace_to_colour(qapp):
    """Why the palette is asked by the curve frame and not by every frame.

    A picture figure answers its pictures through `images()` and `plotItems()`
    and holds no curve at all, so handing it a colour per trace would be
    inventing traces it does not have -- the mistake that would make the manual's
    sentence about an :guilabel:`Image` figure a lie. Its slice-preview lines are
    drawn by `QVizSliceLines`, which sets their pens itself and is out of this
    row's scope.
    """
    figure = ownership.keep(QVizImagePlot(title='imageNoColourGuard'))

    assert figure.images() == []
    assert not hasattr(figure, 'curves'), (
        'the picture figure was given curves to colour; it draws pictures, and '
        'one colour scale already answers for all of them')
