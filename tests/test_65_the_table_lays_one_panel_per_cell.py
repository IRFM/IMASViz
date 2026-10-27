# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The Table Plot View lays one panel per cell, and never two in one cell.

A user who plotted a selection of fifteen quantities saw a table whose first row
held two panels instead of three, one window of that row missing, that window
lying on top of the second panel of the second row, and a last row holding a
single panel.

The width of the table was asked **per panel, as each one arrived**:
`addPanelToGrid` took `columnsFor(len(self._panels) + 1)`, so the first panel was
laid on a one-column grid, the next three on a two-column one, and the rest on a
three-column one. Measured before the change, on a table filled the way
`QVizPlotAsTable` fills it:

    panels=5   cells (0,0) (0,1) (1,0) (1,1) (1,1)   -> 4 cells, one shared
    panels=15  5x3, row 0 holds 2 panels, cell (0,2) never filled,
               cell (1,1) holds panels 3 and 4
    panels=16  6x3, and the sixth row holds one panel

`QGridLayout` accepts two widgets in one cell without a word of warning, so
nothing said the table was wrong until a user counted the windows.

Two other answers of the same file disagreed with what was on screen:
`getPlotItemsDict` recomputed the places from the final panel count, so a saved
configuration named `(0, 2)` -- where no panel sat -- and named `(1, 1)` once for
the two panels that shared it; loading such a file laid the overlap again. And a
quantity whose read raised kept the panel it had been given: `plot()` built
`QVizPanel(self)` before drawing, so the refused panel stayed a child of the
window with no layout owning it.

The width is now asked once for the whole table, from the panels it holds; the
panels a configuration named a cell for keep it and the others fill what is left.
The places the window reports are read from the layout.
"""

import pytest
from PySide6.QtCore import QObject, QEvent, QCoreApplication
from PySide6.QtWidgets import QMdiArea

from imasviz.VizGUI.VizConfigurations.QVizConfigurationFile import \
    QVizConfigurationFile, QVizQuantity, PLOT
from imasviz.VizGUI.VizConfigurations.QVizSavePlotConfiguration import \
    QVizSavePlotConfiguration
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPanel import QVizPanel
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizTablePlot import QVizTablePlot
from imasviz.Viz_API import Viz_API

from support.fakes import FakeAxesNode
from support.ownership import keep

TIMES = [0., 1., 2., 3., 4.]
RHO = [0., 1., 2., 3.]
URI = 'imas:hdf5?case=1'

AOS, LEAF = 'AOS', 'LEAF'
TIME_SLICE = (AOS, 'foo', 'time_slice')
RADIAL = (LEAF, 'foo', 'rho_tor')
POLLOIDAL = (LEAF, 'foo', 'theta_poloidal')


@pytest.fixture(autouse=True)
def configurationFolder(tmp_path, monkeypatch):
    """Keep every configuration inside the test, and out of the real ~/.imasviz."""
    monkeypatch.setenv('HOME', str(tmp_path))
    return tmp_path


def _ids(leaf, timed):
    """One IDS stub, holding `leaf` in every element of `time_slice`."""
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = list(TIMES)
    ids.rho_tor = list(RHO)
    ids.theta_poloidal = [.1 * i for i in range(len(RHO))]
    ids.time_slice = []
    for timeIndex in range(len(TIMES)):
        timeSlice = type(str('TimeSlice'), (), {})()
        timeSlice.time = TIMES[timeIndex]
        setattr(timeSlice, leaf, timed(timeIndex))
        ids.time_slice.append(timeSlice)
    return ids


class Node(FakeAxesNode):
    """A leaf held by an array of structures, answering for a window and a tree."""

    def is0DAndDynamic(self):
        return self._dataType == 'FLT_0D'

    def is1DAndDynamic(self):
        return self._dataType == 'FLT_1D'

    def hasTimeAxis(self):
        return True

    def isPlotToPerformAlongTimeAxis(self, plotWidget=None):
        if plotWidget is None:
            return self.hasTimeAxis()
        axis = plotWidget.getPlotAxis()
        if axis == 'TIME':
            return self.hasTimeAxis()
        if axis in ('DEFAULT', 'COORDINATE1'):
            if self.is0DAndDynamic():
                return True
            if self.is1DAndDynamic():
                return False
        return None

    def getPath(self):
        return self.getInfoDict().get('Path')

    def getOccurrence(self):
        return self.getInfoDict().get('occurrence')


def _quantity(index):
    """One scalar of the stub IDS, under a path of its own."""
    leaf = 'value%d' % index
    return Node(_ids(leaf, lambda timeIndex: 7. * timeIndex + index),
                'foo', 'foo.time_slice[itime]', 'FLT_0D', name=leaf,
                itimeIndex=0, coordinates=(), indices={'i': '0'},
                lengths={'i': str(len(TIMES))},
                infoDict={'Path': 'foo/time_slice(i)/' + leaf,
                          'occurrence': 0, 'name': leaf})


def _quantities(count):
    return [_quantity(index) for index in range(count)]


def _refused():
    """A quantity with two axes to draw: a panel holds a curve, not a picture."""
    return Node(_ids('matrix', lambda timeIndex:
                     [[10. * row + column for column in range(len(RHO))]
                      for row in range(len(RHO))]),
                'foo', 'foo.time_slice[itime]', 'FLT_2D', name='matrix',
                itimeIndex=0, coordinates=('rho_tor', 'theta_poloidal'),
                coordinateUnits={1: 'm', 2: 'rad'}, indices={'i': '0'},
                lengths={'i': str(len(TIMES))},
                infoDict={'Path': 'foo/time_slice(i)/matrix',
                          'occurrence': 0, 'name': 'matrix'})


@pytest.fixture
def view(qapp):
    """One shot view, and the api its figures are registered to."""

    class FakeSource(QObject):
        def __init__(self, uri):
            super().__init__()
            self.uri = uri
            self.name = 'NATIVE'

        def dataKey(self, treeNode):
            return treeNode.getParametrizedDataPath()

    class FakeView(QObject):
        def __init__(self):
            super().__init__()
            self.uri = 'imas:hdf5?case=1'
            self.dataSource = FakeSource(self.uri)
            self.selectedItem = None
            self.selectedSignalsDict = {}
            self.signalsList = []

    # The entry shows the table it fills, so the shot, its mdi and the frames in
    # its api have to outlive the test -- see support/ownership.py.
    shot = FakeView()
    shot.mdi = QMdiArea()
    shot.imas_viz_api = Viz_API(parent=shot.mdi)
    shot.imas_viz_api.DTVlist = [shot]
    return keep(shot)


def fill(view, nodes, plotAxis='TIME'):
    """Draw the selection into a Table Plot View, as the menu entry does."""
    view.signalsList = list(nodes)
    view.selectedSignalsDict = {n.getParametrizedDataPath():
                                {'index': index,
                                 'QTreeWidgetItem': n,
                                 'uri': URI}
                                for index, n in enumerate(nodes)}
    view.selectedItem = nodes[0]
    QVizSignalHandling(view).onPlotToTablePlotView(all_DTV=False,
                                                   plotAxis=plotAxis)
    return [frame for frame in view.imas_viz_api.figureframes.values()
            if isinstance(frame, QVizTablePlot)][0]


def cells(frame):
    """[(row, column)] where each panel actually sits."""
    return [(row, column) for row, column, _ in frame.panelsInTable()]


def perRow(frame):
    """{row: [columns occupied]}."""
    occupancy = {}
    for row, column in cells(frame):
        occupancy.setdefault(row, []).append(column)
    return {row: sorted(columns)
            for row, columns in sorted(occupancy.items())}


# ---------------------------------------------------------------------------
# One panel per cell, whatever the number of panels.

@pytest.mark.ui
@pytest.mark.parametrize('count', [1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 15, 16, 17])
def test_no_two_panels_share_a_cell(view, count):
    frame = fill(view, _quantities(count))

    placed = cells(frame)
    assert len(placed) == count
    assert len(set(placed)) == count, \
        'two panels share a cell: %r' % (placed,)


@pytest.mark.ui
@pytest.mark.parametrize('count', [1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 15, 16, 17])
def test_the_table_is_regular_from_its_first_row_to_its_last(view, count):
    """No hole before the last panel, no row half filled before the last.

    This is what the user saw turned into an assertion: with 15 panels the first
    row held 2 and cell (0,2) stayed empty, and with 16 a sixth row appeared
    holding one panel while the second row held four.
    """
    frame = fill(view, _quantities(count))
    columns = QVizTablePlot.columnsFor(count)

    rows = perRow(frame)
    full, remainder = divmod(count, columns)
    expected = {row: list(range(columns)) for row in range(full)}
    if remainder:
        expected[full] = list(range(remainder))
    assert rows == expected
    assert list(rows) == list(range(full + (1 if remainder else 0)))


@pytest.mark.ui
def test_the_fifteen_panel_table_the_user_asked_for(view):
    """Fifteen quantities: five rows of three, and every window in its own cell.

    Measured before the change: 14 cells for 15 panels, row 0 holding (0,0) and
    (0,1) only, and cell (1,1) holding two panels -- the window the first row was
    missing lying on the second panel of the second row.
    """
    frame = fill(view, _quantities(15))

    assert perRow(frame) == {row: [0, 1, 2] for row in range(5)}
    assert frame.grid.rowCount() == 5
    assert frame.grid.columnCount() == 3


@pytest.mark.ui
def test_a_sixteenth_panel_goes_to_a_row_of_its_own(view):
    """Sixteen panels: five rows of three and a sixth holding the last one.

    Measured before the change this table cost 15 cells for 16 panels, and the
    sixth row was there for the wrong reason: the panels of the first rows had
    been laid on narrower grids and one cell was shared.
    """
    frame = fill(view, _quantities(16))

    expected = {row: [0, 1, 2] for row in range(5)}
    expected[5] = [0]
    assert perRow(frame) == expected
    assert len(set(cells(frame))) == 16


@pytest.mark.ui
def test_the_width_is_asked_once_for_the_table_and_not_per_panel(view):
    # The width of a five-panel table is three columns, so the fourth and fifth
    # panels share the second row -- and the first panel is no longer alone in a
    # row of its own. Measured before: panels 3 and 4 both landed in (1,1).
    frame = fill(view, _quantities(5))

    assert perRow(frame) == {0: [0, 1, 2], 1: [0, 1]}
    assert not hasattr(QVizTablePlot, 'addPanelToGrid')
    assert not hasattr(QVizTablePlot, 'addPanelAt')


# ---------------------------------------------------------------------------
# What the window reports is what it shows.

@pytest.mark.ui
def test_the_places_the_window_reports_are_the_places_it_shows(view):
    """`getPlotItemsDict` reads the layout, it does not recompute a second table.

    Measured on the 15-panel table before the change: the layout held (1,1)
    twice and never (0,2), while this answer listed (0,2) once and (1,1) once --
    so the file written from it named a cell no panel sat in.
    """
    frame = fill(view, _quantities(15))

    reported = sorted(place[0] for place in
                      frame.getPlotItemsDict().values())
    assert len(frame.getPlotItemsDict()) == 15
    assert reported == sorted(cells(frame))


@pytest.mark.ui
def test_a_saved_table_comes_back_with_the_places_it_showed(view, tmp_path):
    nodes = _quantities(6)
    frame = fill(view, nodes)
    showed = cells(frame)

    path = QVizSavePlotConfiguration(view, frame, name='wide').execute()
    view.imas_viz_api.DeleteFigure(figureKey=frame.figureKey)

    view.signalsList = list(nodes)
    QVizSignalHandling(view).onPlotToTablePlotView(all_DTV=False,
                                                   configFile=path)
    again = [frame for frame in view.imas_viz_api.figureframes.values()
             if isinstance(frame, QVizTablePlot)][0]

    assert cells(again) == showed
    assert len(set(cells(again))) == 6


@pytest.mark.ui
def test_named_cells_are_kept_and_the_rest_fill_what_is_left(view):
    """A file that names two cells and leaves two unnamed: both halves honoured.

    The two named panels go where the file says, including a cell no row-major
    filling would reach ((2, 0) with four panels); the others take the first
    cells left free. Before, an unnamed panel was placed by an index over a
    width read per panel and could land on a named cell.
    """
    nodes = _quantities(4)
    view.signalsList = list(nodes)
    configuration = QVizConfigurationFile(
        kind=PLOT, abscissa='TIME',
        quantities=[QVizQuantity(node.getPath(), 0, row, column, URI)
                    for node, (row, column) in zip(nodes, [(1, 0), (2, 0),
                                                           (None, None),
                                                           (None, None)])])
    path = configuration.write(QVizConfigurationFile.named('mixed', PLOT))

    QVizSignalHandling(view).onPlotToTablePlotView(all_DTV=False,
                                                   configFile=path)

    frame = [frame for frame in view.imas_viz_api.figureframes.values()
             if isinstance(frame, QVizTablePlot)][0]
    assert cells(frame) == [(1, 0), (2, 0), (0, 0), (0, 1)]


@pytest.mark.ui
def test_a_file_naming_one_cell_twice_does_not_fill_it_twice(view):
    """A configuration written before this was fixed names (1,1) twice.

    The first panel to claim a cell keeps it; the other is laid with the ones the
    file left unnamed. Refusing the file would be worse: the quantities it names
    are the ones the user asked for.
    """
    nodes = _quantities(3)
    view.signalsList = list(nodes)
    configuration = QVizConfigurationFile(
        kind=PLOT, abscissa='TIME',
        quantities=[QVizQuantity(node.getPath(), 0, row, column, URI)
                    for node, (row, column) in zip(nodes, [(1, 1), (1, 1),
                                                           (None, None)])])
    path = configuration.write(QVizConfigurationFile.named('twice', PLOT))

    QVizSignalHandling(view).onPlotToTablePlotView(all_DTV=False,
                                                   configFile=path)

    frame = [frame for frame in view.imas_viz_api.figureframes.values()
             if isinstance(frame, QVizTablePlot)][0]
    assert len(set(cells(frame))) == 3


# ---------------------------------------------------------------------------
# A quantity a panel cannot show costs its panel, and nothing else.

@pytest.mark.ui
def test_a_refused_quantity_leaves_no_panel_on_the_window(view, caplog):
    """The panel of a refused read must not stay a child of the window.

    `plot()` used to build `QVizPanel(self)` before drawing it, so a quantity with
    two axes to draw left that panel parented to the window and owned by no
    layout: a curve-sized widget sitting over the table, on top of the panels
    that were accepted.

    The strategy is the default one here, and not by carelessness: along time that
    same quantity has one axis to draw and is drawn, so the refusal -- and the
    panel it costs -- only exists on a window that leaves the read to answer.
    """
    frame = fill(view, _quantities(3) + [_refused()], plotAxis='DEFAULT')

    assert frame.panelCount() == 3
    assert '2 axes to draw' in caplog.text

    # deleteLater() takes the widget back when the events are flushed, which is
    # what the application does as soon as it returns to its event loop.
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    assert len(frame.findChildren(QVizPanel)) == 3
    assert frame.grid.count() == 3
    assert cells(frame) == [(0, 0), (0, 1), (1, 0)]
