# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Table Plot View: one panel per quantity, and the two abscissa strategies.

The four entries under "Plot selected nodes to → TablePlotView" opened a
`QVizMultiPlotWindow` filled by `QVizTablePlotView`, which read the whole
selection against one abscissa through `Viz_API.GetSignal` and drew whatever came
back. Measured on real tree nodes, four things went wrong at once:

* a quantity with two axes to draw, under the default strategy, died out of the
  entry with `TypeError: 'QVizDataArrayHandle' object is not subscriptable`, and
  it died after the window had been registered and both nodes recorded in
  `figToNodes`: a husk under `TablePlotView:1` with no view in it, and a selection
  half-drawn.
* the same quantity asked for the 'TIME' axis came back as a curve of 5 points --
  one element of it, `[0, 100, 200, 300, 400]` -- titled as the whole quantity,
  with nothing on the window saying which element had been picked.
* three of the four entries asked for the same abscissa: both "All" entries and
  the "This" entry of the 'TIME' submenu were wired with `plotAxis='TIME'`, so
  the two submenus differed for one entry out of four.
* the number of columns came from the screen width (measured: `cols=1` with
  2 panels on this display), while the `column` and `row` set on each plot item
  were the other way round -- `column = n // cols`, `row = n % cols`. The
  configuration file keys a panel by `(row, column)` and the code applying it
  compares `(column, row)`, so a saved configuration re-applied to one panel out
  of two, and only on the diagonal.

And the window itself: `QVizMultiPlotWindow` registers its key twice and embeds
itself in the MDI area in a plain `QMdiSubWindow`, so closing it left the key
registered -- the same defect T0 removed from the Show/Hide/Delete menus.

The gate the entries hid behind, `shareSameCoordinates`, measured `False` for a
selection of two quantities on different coordinates that the window drew
correctly anyway. A panel holds one quantity and shares nothing with its
neighbours, so the question is not asked here: each panel is read on the axes it
sits on, and carries the controls for the axes that read pins.

Nothing here opens a case: a filled leaf inside arrays of structures needs a case
whose arrays are filled, and no reference case on this checkout has them.
"""

import numpy as np
import pytest
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMdiArea, QMenu

from imasviz.VizUtils import FigureTypes
from imasviz.Viz_API import Viz_API, QVizMdiSubWindow
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizTablePlot import QVizTablePlot

from support.fakes import FakeAxesNode

RHO = [0., 1., 2., 3.]
THETA = [0., .25, .5, .75]
TIMES = [0., 1., 2., 3., 4.]
TREE_TIME = 1

AOS, LEAF = 'AOS', 'LEAF'
TIME_SLICE = (AOS, 'foo', 'time_slice')
RADIAL = (LEAF, 'foo', 'rho_tor')
POLLOIDAL = (LEAF, 'foo', 'theta_poloidal')


def _ids():
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = list(TIMES)
    ids.rho_tor = list(RHO)
    ids.theta_poloidal = list(THETA)
    ids.time_slice = []
    for timeIndex in range(len(TIMES)):
        timeSlice = type(str('TimeSlice'), (), {})()
        timeSlice.time = TIMES[timeIndex]
        timeSlice.vector = [100. * timeIndex + 10. * i for i in range(len(RHO))]
        timeSlice.theta_vector = [1. * timeIndex + .1 * i
                                  for i in range(len(THETA))]
        timeSlice.matrix = [[100. * timeIndex + 10. * row + column
                             for column in range(len(THETA))]
                            for row in range(len(RHO))]
        timeSlice.scalar = 7. * timeIndex
        ids.time_slice.append(timeSlice)
    return ids


class Node(FakeAxesNode):
    """Answers the abscissa question the way a tree node does.

    The read asks the node, not the menu, whether a quantity is drawn along time,
    and `QVizTreeNode.isPlotToPerformAlongTimeAxis` (QVizTreeNode.py:154-167)
    answers from the window the plot is drawn in: 'TIME' means along time for
    anything with a time base, while 'DEFAULT' means along time only for a scalar
    and NOT for a 1D quantity held by a dynamic array. `FakeAxesNode` answers from
    a constructor flag and ignores the window, so a test built on it measures the
    stub: the two menu strategies come out identical whether the code tells them
    apart or not.
    """

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
        """As QVizTreeNode spells it: the tree builds it with slashes."""
        return self.getInfoDict().get('Path')

    def getOccurrence(self):
        return self.getInfoDict().get('occurrence')


def node(dataType, name, coordinates, path=None, units='K'):
    return Node(_ids(), 'foo', 'foo.time_slice[itime]', dataType, name=name,
                units=units, itimeIndex=0, coordinates=coordinates,
                coordinateUnits={number: 'm'
                                 for number in range(1, len(coordinates) + 1)},
                indices={'i': str(TREE_TIME)},
                lengths={'i': str(len(TIMES))},
                infoDict={'Path': path if path is not None
                          else 'foo/time_slice(i)/' + name,
                          'occurrence': 0,
                          'name': name})


def _vector(path=None):
    return node('FLT_1D', 'vector', ('rho_tor',), path=path)


def _theta():
    return node('FLT_1D', 'theta_vector', ('theta_poloidal',), units='rad')


def _matrix():
    return node('FLT_2D', 'matrix', ('rho_tor', 'theta_poloidal'), units='Pa')


def _scalar():
    return node('FLT_0D', 'scalar', ())


@pytest.fixture
def view(qapp):
    """One shot view with a selection, and the api its figures are registered to."""

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

    # The MDI area owns the windows the entries open, so it has to outlive the
    # call that builds it: the api holds it as its Qt parent.
    shot = FakeView()
    shot.mdi = QMdiArea()
    shot.imas_viz_api = Viz_API(parent=shot.mdi)
    shot.imas_viz_api.DTVlist = [shot]
    return shot


def select(view, *nodes):
    # The shape a real tree gives a selection entry (QVizSelectSignal.py:43): the
    # save command reads 'uri' off it, so a stub without it tests a shape no
    # caller produces.
    view.selectedSignalsDict = {n.getParametrizedDataPath():
                                {'index': index,
                                 'QTreeWidgetItem': n,
                                 'uri': view.dataSource.uri}
                                for index, n in enumerate(nodes)}
    view.selectedItem = nodes[0] if nodes else None
    view.signalsList = list(nodes)
    return view


def entry(view, treeNode=None):
    return QVizSignalHandling(dataTreeView=view,
                              treeNode=treeNode or view.selectedItem)


@pytest.fixture
def bar(qapp):
    """A menu to hang the selection menu on.

    The entry builds its menu as a child of the one it is handed, and Qt deletes
    children along with their parent: a parent left as an unnamed temporary takes
    the whole selection menu down before the test can read one title.
    """
    return QMenu()


def tables(view):
    return [frame for frame in view.imas_viz_api.figureframes.values()
            if isinstance(frame, QVizTablePlot)]


def panelData(frame, index=0):
    x, y = frame.panels()[index].curves()[0].getData()
    return np.asarray(x), np.asarray(y)


def axisLabel(plotItem, which):
    axis = plotItem.getAxis(which)
    units = axis.labelUnits or ''
    return '%s[%s]' % (axis.labelText, units) if units else axis.labelText


def subMenu(menu, title):
    for action in menu.actions():
        if action.text() == title:
            return action.menu()
    raise AssertionError('no %r submenu in %r' %
                         (title, [a.text() for a in menu.actions()]))


# ---------------------------------------------------------------------------
# The four entries, and the two questions they are named after.

@pytest.mark.ui
def test_the_two_submenus_ask_the_two_questions_they_are_named_for(view, bar):
    # The whole branch is built only when something is selected: the entry holds
    # the menu disabled otherwise, so a test without a selection reads an empty
    # menu and proves nothing about these four entries.
    select(view, _vector())
    menu = entry(view).menuPlotSelectedSignalNodes(parentMenu=bar)
    tablePlotView = subMenu(menu, 'TablePlotView')
    assert [action.text() for action in tablePlotView.actions()] == \
        ['New (default axis)', "New ('TIME' axis)"]
    for title in ('New (default axis)', "New ('TIME' axis)"):
        assert [action.text() for action in subMenu(tablePlotView, title).actions()] \
            == ['This IMAS Database', 'All IMAS Databases']


@pytest.mark.ui
def test_the_default_entry_reads_a_1d_quantity_along_its_own_coordinate(view):
    select(view, _vector())

    entry(view).onPlotToTablePlotView(all_DTV=False, plotAxis='DEFAULT')

    frame = tables(view)[0]
    x, y = panelData(frame)
    np.testing.assert_allclose(x, RHO)
    np.testing.assert_allclose(y, [100. * TREE_TIME + 10. * i
                                   for i in range(len(RHO))])
    assert axisLabel(frame.panels()[0].plotItem(), 'bottom') == 'rho_tor[m]'


@pytest.mark.ui
def test_the_time_entry_reads_the_same_quantity_along_time(view):
    select(view, _vector())

    entry(view).onPlotToTablePlotView(all_DTV=False, plotAxis='TIME')

    frame = tables(view)[0]
    x, y = panelData(frame)
    np.testing.assert_allclose(x, TIMES)
    np.testing.assert_allclose(y, [100. * t for t in TIMES])
    assert axisLabel(frame.panels()[0].plotItem(), 'bottom') == 'time[s]'


@pytest.mark.ui
def test_the_two_entries_are_not_wired_to_the_same_answer(view):
    # Three of the four legacy entries were wired with plotAxis='TIME', so the
    # two submenus answered the same question for one selection out of one.
    select(view, _vector())

    entry(view).onPlotToTablePlotView(all_DTV=False, plotAxis='DEFAULT')
    alongCoordinate = panelData(tables(view)[0])[0]

    for key in list(view.imas_viz_api.figureframes):
        view.imas_viz_api.ForgetFigure(key)
    select(view, _vector())
    entry(view).onPlotToTablePlotView(all_DTV=False, plotAxis='TIME')
    alongTime = panelData(tables(view)[0])[0]

    assert not np.array_equal(alongCoordinate, alongTime)


# ---------------------------------------------------------------------------
# One panel each: what a panel shares with its neighbours is nothing.

@pytest.mark.ui
def test_two_quantities_on_two_coordinates_each_get_their_own_abscissa(view):
    select(view, _vector(), _theta())

    entry(view).onPlotToTablePlotView(all_DTV=False, plotAxis='DEFAULT')

    frame = tables(view)[0]
    assert frame.panelCount() == 2
    assert axisLabel(frame.panels()[0].plotItem(), 'bottom') == 'rho_tor[m]'
    assert axisLabel(frame.panels()[1].plotItem(), 'bottom') == \
        'theta_poloidal[m]'
    np.testing.assert_allclose(panelData(frame, 1)[0], THETA)
    np.testing.assert_allclose(panelData(frame, 1)[1],
                               [1. * TREE_TIME + .1 * i
                                for i in range(len(THETA))])


@pytest.mark.ui
def test_a_quantity_of_two_axes_is_refused_by_name_and_costs_nothing_else(view,
                                                                          caplog):
    # The legacy entry died out of the menu handler with
    # `TypeError: 'QVizDataArrayHandle' object is not subscriptable`, after
    # registering a window with no view in it and recording both nodes.
    select(view, _vector(), _matrix())

    entry(view).onPlotToTablePlotView(all_DTV=False, plotAxis='DEFAULT')

    frame = tables(view)[0]
    assert frame.panelCount() == 1
    assert 'matrix' in caplog.text
    assert 'a picture needs a window of its own' in caplog.text
    assert len(view.imas_viz_api.figToNodes[FigureTypes.TABLEPLOTTYPE + '1']) == 1


@pytest.mark.ui
def test_the_time_entry_names_both_axes_it_pins_on_a_quantity_of_two_axes(view):
    select(view, _matrix())

    entry(view).onPlotToTablePlotView(all_DTV=False, plotAxis='TIME')

    # Measured on the legacy window: one curve of one element, titled as the
    # whole quantity, with no control and no word naming the element. Here the
    # element is pinned too, but it is pinned where the user can see and move it.
    frame = tables(view)[0]
    panel = frame.panels()[0]
    assert list(panel.sliceControls.keys()) == [RADIAL, POLLOIDAL]
    assert [row.nameLabel.text() for row in panel.sliceControls.rows()] == \
        ['rho_tor:', 'theta_poloidal:']
    assert panel.curveCount() == 1
    assert panel.sliceControls.indices()[RADIAL] == 0


@pytest.mark.ui
def test_a_scalar_held_by_the_dynamic_array_is_read_along_time(view):
    select(view, _scalar())

    entry(view).onPlotToTablePlotView(all_DTV=False, plotAxis='DEFAULT')

    frame = tables(view)[0]
    x, y = panelData(frame)
    np.testing.assert_allclose(x, TIMES)
    np.testing.assert_allclose(y, [7. * t for t in TIMES])
    assert frame.panels()[0].sliceControls.keys() == []


@pytest.mark.ui
def test_a_selection_that_gives_nothing_draws_no_window(view, caplog):
    select(view, _matrix())

    entry(view).onPlotToTablePlotView(all_DTV=False, plotAxis='DEFAULT')

    # The legacy left `TablePlotView:1` registered with no view behind it, with
    # both nodes already recorded as drawn.
    assert view.imas_viz_api.figureframes == {}
    assert view.imas_viz_api.figToNodes == {}
    assert 'nothing to plot' in caplog.text.lower()


# ---------------------------------------------------------------------------
# The table itself, and the panel keys a configuration file is written from.

@pytest.mark.ui
def test_the_width_of_the_table_follows_the_number_of_panels():
    # The legacy took the column count from the screen width: measured cols=1
    # with two panels on this display, and 2 rows for 3 quantities.
    assert QVizTablePlot.columnsFor(1) == 1
    assert QVizTablePlot.columnsFor(4) == 2
    assert QVizTablePlot.columnsFor(6) == 3


@pytest.mark.ui
def test_a_panel_is_keyed_by_where_it_sits_in_the_table(view):
    # The legacy set column = n // cols and row = n % cols -- the other way round
    # from where the panel was laid -- and the configuration file keys a panel by
    # (row, column) while the code applying it compares (column, row): only a
    # panel on the diagonal of the table was ever found again.
    select(view, _vector(), _theta(), _scalar())

    entry(view).onPlotToTablePlotView(all_DTV=False, plotAxis='TIME')

    frame = tables(view)[0]
    keys = [frame.getPlotItemsDict()[panel.plotItem()][0]
            for panel in frame.panels()]
    columns = frame.columnsFor(3)
    assert keys == [(index // columns, index % columns) for index in range(3)]


@pytest.mark.ui
def test_every_panel_carries_the_selection_entry_the_saver_asks_for(view):
    # The save command stops at the first plot item without a signalData of its
    # own, so a panel missing one is a panel that never reaches the file.
    select(view, _vector(), _theta())

    entry(view).onPlotToTablePlotView(all_DTV=False, plotAxis='TIME')

    frame = tables(view)[0]
    for panel in frame.panels():
        assert hasattr(panel.plotItem(), 'signalData')
        assert panel.plotItem().signalData['uri'] == view.dataSource.uri


@pytest.mark.ui
def test_closing_the_window_frees_its_key(view):
    # The legacy window registered its key twice and embedded itself in the MDI
    # area in a plain QMdiSubWindow, so closing it left the key behind.
    select(view, _vector())

    entry(view).onPlotToTablePlotView(all_DTV=False, plotAxis='TIME')

    frame = tables(view)[0]
    subWindow = view.imas_viz_api.parent.findChild(QVizMdiSubWindow)
    subWindow.close()

    assert view.imas_viz_api.figureframes == {}
    assert view.imas_viz_api.figToNodes == {}


# ---------------------------------------------------------------------------
# A saved configuration: which quantities, and not how they looked.

def configuration(tmp_path, entries, styling=True):
    """A '.pcfg' spelled the way QVizSavePlotConfig writes one."""
    panels = []
    for index, (path, occurrence) in enumerate(entries):
        opts = '<opts connect="True" antialias="True"/>' if styling else ''
        panels.append(
            '<PlotItem key="(%d, %d)" row="%d" column="%d" title="a panel">'
            '<PlotDataItem>'
            '<sourceInfo path="%s" occurrence="%d" uri="imas:hdf5?case=1"/>'
            '%s'
            '</PlotDataItem></PlotItem>'
            % (index // 2, index % 2, index // 2, index % 2,
               path, occurrence, opts))
    configFile = tmp_path / 'saved.pcfg'
    configFile.write_text('<?xml version="1.0" ?><PlotConfiguration>'
                          '<GraphicsWindow>%s</GraphicsWindow>'
                          '</PlotConfiguration>' % ''.join(panels))
    return str(configFile)


@pytest.mark.ui
def test_a_configuration_file_draws_one_panel_per_quantity_it_names(view, tmp_path,
                                                                   caplog):
    select(view, _vector(), _theta())

    entry(view).onPlotToTablePlotView(
        all_DTV=False, plotAxis='TIME',
        configFile=configuration(tmp_path, [('foo/time_slice(i)/vector', 0),
                                            ('foo/time_slice(i)/theta_vector', 0)]))

    frame = tables(view)[0]
    assert frame.panelCount() == 2
    np.testing.assert_allclose(panelData(frame, 0)[1], [100. * t for t in TIMES])
    np.testing.assert_allclose(panelData(frame, 1)[1], [1. * t for t in TIMES])


@pytest.mark.ui
def test_a_configuration_file_holding_styling_says_what_it_leaves_out(view,
                                                                     tmp_path,
                                                                     caplog):
    select(view, _vector(), _theta())

    entry(view).onPlotToTablePlotView(
        all_DTV=False, plotAxis='TIME',
        configFile=configuration(tmp_path, [('foo/time_slice(i)/vector', 0),
                                            ('foo/time_slice(i)/theta_vector', 0)]))

    assert 'not applied' in caplog.text
    assert '2 panel' in caplog.text


@pytest.mark.ui
def test_a_path_the_tree_does_not_hold_is_named_and_skipped(view, tmp_path,
                                                            caplog):
    select(view, _vector())

    entry(view).onPlotToTablePlotView(
        all_DTV=False, plotAxis='TIME',
        configFile=configuration(tmp_path, [('foo/time_slice(i)/vector', 0),
                                            ('wall/time_slice(i)/vector', 0)]))

    assert tables(view)[0].panelCount() == 1
    assert 'wall/time_slice(i)/vector' in caplog.text
    assert 'not in this tree' in caplog.text


@pytest.mark.ui
def test_a_configuration_file_naming_an_occurrence_the_tree_does_not_hold_is_named(
        view, tmp_path, caplog):
    select(view, _vector())

    entry(view).onPlotToTablePlotView(
        all_DTV=False, plotAxis='TIME',
        configFile=configuration(tmp_path, [('foo/time_slice(i)/vector', 3)]))

    assert view.imas_viz_api.figureframes == {}
    assert 'foo/time_slice(i)/vector' in caplog.text


@pytest.mark.ui
def test_a_configuration_file_that_cannot_be_read_answers_with_a_reason(view,
                                                                       caplog):
    select(view, _vector())

    entry(view).onPlotToTablePlotView(all_DTV=False, plotAxis='TIME',
                                      configFile='/no/such/file.pcfg')

    assert view.imas_viz_api.figureframes == {}
    assert 'Cannot read' in caplog.text
