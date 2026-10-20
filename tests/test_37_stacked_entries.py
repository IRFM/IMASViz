# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Stacked Plot View: a column of panels reading along one shared abscissa.

The four entries under "Plot selected nodes to → StackedPlotView" opened a
`QVizMultiPlotWindow` filled by `QVizStackedPlotView`, whose whole point is that
its plots are compared against the same span: the manual says "All plots displays
always share the same X and Y range, even when using plot interaction features".
Measured on real tree nodes, the window did not do that, and neither of its two
checkboxes did what its label says:

* the second panel was linked to nothing. `plotItemFirst`, the plot the others
  were linked to, was reset to `None` at the top of every `plot()` call, so the
  first panel got a link to itself and every later panel got none: measured
  `(False, False)` for the second of two plots, each keeping its own range.
* "Group pan mode" raised `AttributeError: 'QVizStackedPlotView' object has no
  attribute 'viewBoxes'` -- the class sets `viewBoxList`, never `viewBoxes`.
* "Display X axis of all plots" changed nothing: it rewrote the tick-label style
  the axis linking had already set, and measured on two panels the result was
  `[False, True]` either way -- one panel labelled, the other not, in both states.
* the two panels of one selection were not even titled alike: measured, the first
  carried the figure key and the second carried nothing.
* a quantity with two axes to draw, under the default strategy, died out of the
  entry with `TypeError: 'QVizDataArrayHandle' object is not subscriptable`, after
  registering `StackedPlotView:7` with no `multiPlotView` behind it and recording
  both nodes in `figToNodes`.
* closing the window left its key registered (measured: `['StackedPlotView:1']`
  before and after `close()`, and the next window was handed `StackedPlotView:2`).

And the four entries could not be reached at all from the shot view's menu bar:
the `StackedPlotView` submenu was built with `menu.addMenu('StackedPlotView')`,
which returns a `QMenu` held only by a Python local, so its C++ object was
deleted when the method returned. Measured, asking that menu what it holds raises
`RuntimeError: Internal C++ object (PySide6.QtWidgets.QMenu) already deleted`
while the `Figure` and `TablePlotView` submenus next to it answer.

Since the abscissa is shared by definition, the gate the entries hid behind
(`shareSameCoordinates`, measured `False` for a selection the window drew anyway)
is replaced by a refusal the user can read: the first quantity read fixes the
abscissa, and a quantity the read would take along another one is refused by
name, with both axes named and TablePlotView pointed at -- the window for
quantities that do not agree.

Nothing here opens a case: a filled leaf inside arrays of structures needs a case
whose arrays are filled, and no reference case on this checkout has them.
"""

import numpy as np
import pytest
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMdiArea, QMenu

import pyqtgraph as pg

from imasviz.VizUtils import FigureTypes
from imasviz.Viz_API import Viz_API, QVizMdiSubWindow
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizStackedPlot import QVizStackedPlot

from support.fakes import FakeAxesNode

RHO = [0., 1., 2., 3.]
THETA = [0., .25, .5, .75]
TIMES = [0., 1., 2., 3., 4.]
TREE_TIME = 1


def _ids(extra=None):
    """The stub IDS: one array of structures, four kinds of leaf inside it.

    `extra` adds a filled leaf on the same coordinate as `vector`, which is what
    a shared abscissa needs to be measurable at all: the stock leaves sit on
    different coordinates, so a window of them refuses every one but the first.
    """
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
        for name in extra or ():
            setattr(timeSlice, name, [1000. * timeIndex + i
                                      for i in range(len(RHO))])
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

    def getDataTreeView(self):
        """As QVizTreeNode answers it: the menu built on a node asks its view."""
        return VIEWS_OF_NODES[0]

    def getPath(self):
        """As QVizTreeNode spells it: the tree builds it with slashes."""
        return self.getInfoDict().get('Path')

    def getOccurrence(self):
        return self.getInfoDict().get('occurrence')


VIEWS_OF_NODES = []


def node(dataType, name, coordinates, extra=None, units='K'):
    return Node(_ids(extra), 'foo', 'foo.time_slice[itime]', dataType,
                name=name, units=units, itimeIndex=0, coordinates=coordinates,
                coordinateUnits={number: 'm'
                                 for number in range(1, len(coordinates) + 1)},
                indices={'i': str(TREE_TIME)},
                lengths={'i': str(len(TIMES))},
                infoDict={'Path': 'foo/time_slice(i)/' + name,
                          'occurrence': 0,
                          'name': name})


def _vector():
    return node('FLT_1D', 'vector', ('rho_tor',))


def _sameAxis(name='rho_other'):
    """A second quantity on the same coordinate: what a shared abscissa is for."""
    return node('FLT_1D', name, ('rho_tor',), extra=(name,), units='T')


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
    VIEWS_OF_NODES.append(shot)
    return shot


def select(view, *nodes):
    # The shape a selection entry has (QVizSelectNodes.entryFor): the
    # commands read 'uri' off it, so a stub without it tests a shape no caller
    # produces.
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


def stacks(view):
    return [frame for frame in view.imas_viz_api.figureframes.values()
            if isinstance(frame, QVizStackedPlot)]


def panelData(frame, index=0):
    x, y = frame.panels()[index].curves()[0].getData()
    return np.asarray(x), np.asarray(y)


def axisLabel(plotItem, which):
    axis = plotItem.getAxis(which)
    units = axis.labelUnits or ''
    return '%s[%s]' % (axis.labelText, units) if units else axis.labelText


def linkedToFirst(frame):
    """[(shares x, shares y)] for every panel of the window.

    Asked of the view boxes, which is where the ranges live: `setXLink` links a
    whole view, while a linked axis item would only mirror a range for its own
    label. The first panel is the reference, so it answers for itself.
    """
    first = frame.panels()[0].plotItem().getViewBox()
    return [(panel.plotItem().getViewBox().linkedView(pg.ViewBox.XAxis) is first,
             panel.plotItem().getViewBox().linkedView(pg.ViewBox.YAxis) is first)
            for panel in frame.panels()]


def xLabelsShown(frame):
    return [panel.plotItem().getAxis('bottom').style.get('showValues', True)
            for panel in frame.panels()]


def subMenu(menu, title):
    for action in menu.actions():
        if action.text() == title:
            return action.menu()
    raise AssertionError('no %r submenu in %r' %
                         (title, [a.text() for a in menu.actions()]))


# ---------------------------------------------------------------------------
# The four entries, and the abscissa they are named after.

@pytest.mark.ui
def test_the_four_entries_are_still_there_to_be_clicked(view, bar):
    # The legacy submenu was built with menu.addMenu('StackedPlotView'), whose
    # QMenu is held only by a Python local: read after the call, asking it for its
    # actions raised 'Internal C++ object (QMenu) already deleted'.
    select(view, _vector())
    menu = entry(view).menuPlotSelectedSignalNodes(parentMenu=bar)
    stackedPlotView = subMenu(menu, 'StackedPlotView')
    assert [action.text() for action in stackedPlotView.actions()] == \
        ['New (default axis)', "New ('TIME' axis)"]
    for title in ('New (default axis)', "New ('TIME' axis)"):
        assert [action.text()
                for action in subMenu(stackedPlotView, title).actions()] == \
            ['This IMAS Database', 'All IMAS Databases']


@pytest.mark.ui
def test_the_default_entry_reads_a_1d_quantity_along_its_own_coordinate(view):
    select(view, _vector())

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='DEFAULT')

    frame = stacks(view)[0]
    x, y = panelData(frame)
    np.testing.assert_allclose(x, RHO)
    np.testing.assert_allclose(y, [100. * TREE_TIME + 10. * i
                                   for i in range(len(RHO))])
    assert axisLabel(frame.panels()[0].plotItem(), 'bottom') == 'rho_tor[m]'
    assert frame.abscissaName() == 'rho_tor'


@pytest.mark.ui
def test_the_time_entry_reads_the_same_quantity_along_time(view):
    select(view, _vector())

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='TIME')

    frame = stacks(view)[0]
    x, y = panelData(frame)
    np.testing.assert_allclose(x, TIMES)
    np.testing.assert_allclose(y, [100. * t for t in TIMES])
    assert axisLabel(frame.panels()[0].plotItem(), 'bottom') == 'time[s]'
    assert frame.abscissaName() == 'time'


@pytest.mark.ui
def test_the_two_entries_are_not_wired_to_the_same_answer(view):
    # Three of the four legacy entries were wired with plotAxis='TIME', so the
    # two submenus answered the same question for one selection out of one.
    select(view, _vector())

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='DEFAULT')
    alongCoordinate = panelData(stacks(view)[0])[0]

    for key in list(view.imas_viz_api.figureframes):
        view.imas_viz_api.ForgetFigure(key)
    select(view, _vector())
    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='TIME')
    alongTime = panelData(stacks(view)[0])[0]

    assert not np.array_equal(alongCoordinate, alongTime)


@pytest.mark.ui
def test_clicking_the_time_entry_reaches_the_command_that_reads_along_time(view,
                                                                          bar):
    # The wiring, not just the titles: an action that is built and never connected
    # reads the same in a test of the menu alone.
    select(view, _vector())
    menu = entry(view).menuPlotSelectedSignalNodes(parentMenu=bar)
    subMenu(subMenu(menu, 'StackedPlotView'),
            "New ('TIME' axis)").actions()[0].trigger()

    frame = stacks(view)[0]
    np.testing.assert_allclose(panelData(frame)[0], TIMES)


# ---------------------------------------------------------------------------
# A column of panels against one abscissa.

@pytest.mark.ui
def test_two_quantities_on_one_coordinate_are_drawn_against_it(view):
    select(view, _vector(), _sameAxis())

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='DEFAULT')

    frame = stacks(view)[0]
    assert frame.panelCount() == 2
    for index in (0, 1):
        np.testing.assert_allclose(panelData(frame, index)[0], RHO)
    np.testing.assert_allclose(panelData(frame, 1)[1],
                               [1000. * TREE_TIME + i for i in range(len(RHO))])
    assert frame.abscissaName() == 'rho_tor'


@pytest.mark.ui
def test_every_panel_shares_the_ranges_of_the_first_one(view):
    # Measured on the old window: the second of two plots was linked to neither
    # axis, because plotItemFirst was reset at the top of every plot() call.
    select(view, _vector(), _sameAxis(), _scalar())

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='TIME')

    frame = stacks(view)[0]
    assert frame.panelCount() == 3
    assert linkedToFirst(frame) == [(False, False)] + [(True, True)] * 2


@pytest.mark.ui
def test_group_pan_mode_off_gives_every_panel_its_own_range(view):
    # The old slot read self.viewBoxes, which that class never set: toggling the
    # box raised AttributeError.
    select(view, _vector(), _sameAxis())

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='TIME')

    frame = stacks(view)[0]
    frame.groupPanCheck.setChecked(False)
    assert linkedToFirst(frame) == [(False, False)] * 2
    frame.groupPanCheck.setChecked(True)
    assert linkedToFirst(frame) == [(False, False), (True, True)]


@pytest.mark.ui
def test_the_abscissa_is_labelled_under_the_bottom_panel_only(view):
    # Both states of the old checkbox left the same two panels labelled [False,
    # True]: it rewrote a style the linking had already decided, and never read
    # its own state.
    select(view, _vector(), _sameAxis(), _scalar())

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='TIME')

    frame = stacks(view)[0]
    assert xLabelsShown(frame) == [False, False, True]
    assert [axisLabel(panel.plotItem(), 'bottom')
            for panel in frame.panels()] == ['time[s]'] * 3


@pytest.mark.ui
def test_the_display_x_axis_checkbox_labels_every_panel(view):
    select(view, _vector(), _sameAxis())

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='TIME')

    frame = stacks(view)[0]
    frame.xAxisCheck.setChecked(True)
    assert xLabelsShown(frame) == [True, True]
    frame.xAxisCheck.setChecked(False)
    assert xLabelsShown(frame) == [False, True]


@pytest.mark.ui
def test_each_panel_keeps_its_own_title_and_quantity_label(view):
    # Measured on the old window: the first plot was titled with the figure key
    # and the second with nothing.
    select(view, _vector(), _sameAxis())

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='DEFAULT')

    frame = stacks(view)[0]
    titles = [panel.plotItem().titleLabel.text for panel in frame.panels()]
    assert titles == ['foo.time_slice[itime].vector',
                      'foo.time_slice[itime].rho_other']
    assert [axisLabel(panel.plotItem(), 'left')
            for panel in frame.panels()] == ['vector[K]', 'rho_other[T]']


@pytest.mark.ui
def test_the_panels_are_keyed_by_their_row_in_one_column(view):
    # The old window forced cols=1 and still wrote column = n // cols and
    # row = n % cols: every panel landed in row 0, spread over columns it never
    # drew.
    select(view, _vector(), _sameAxis(), _scalar())

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='TIME')

    frame = stacks(view)[0]
    assert [frame.getPlotItemsDict()[panel.plotItem()][0]
            for panel in frame.panels()] == [(0, 0), (1, 0), (2, 0)]


@pytest.mark.ui
def test_every_panel_carries_the_selection_entry_the_saver_asks_for(view):
    select(view, _vector(), _sameAxis())

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='TIME')

    frame = stacks(view)[0]
    for panel in frame.panels():
        assert hasattr(panel.plotItem(), 'signalData')
        assert panel.plotItem().signalData['uri'] == view.dataSource.uri


# ---------------------------------------------------------------------------
# A quantity that does not run along the window's abscissa is refused, by name.

@pytest.mark.ui
def test_a_quantity_on_another_abscissa_is_refused_and_named(view, caplog):
    select(view, _vector(), _theta())

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='DEFAULT')

    frame = stacks(view)[0]
    assert frame.panelCount() == 1
    assert frame.abscissaName() == 'rho_tor'
    assert 'theta_vector' in caplog.text
    assert 'theta_poloidal' in caplog.text
    assert 'rho_tor' in caplog.text
    assert 'TablePlotView' in caplog.text
    assert len(view.imas_viz_api.figToNodes[FigureTypes.STACKEDPLOTTYPE + '1']) \
        == 1


@pytest.mark.ui
def test_the_refused_quantity_leaves_no_panel_behind(view):
    # The read has already happened when the window notices the abscissa differs,
    # so the panel has to be dropped rather than shown: a parentless widget left
    # in the frame is a blank plot the user did not ask for.
    select(view, _vector(), _theta())

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='DEFAULT')

    frame = stacks(view)[0]
    assert len(frame.findChildren(frame.panels()[0].__class__)) == 1
    assert len(frame.getPlotItemsDict()) == 1


@pytest.mark.ui
def test_the_first_quantity_read_is_the_one_that_fixes_the_abscissa(view, caplog):
    select(view, _theta(), _vector())

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='DEFAULT')

    frame = stacks(view)[0]
    assert frame.abscissaName() == 'theta_poloidal'
    np.testing.assert_allclose(panelData(frame)[0], THETA)
    assert 'not theta_poloidal' in caplog.text


@pytest.mark.ui
def test_the_time_entry_makes_a_scalar_and_a_1d_quantity_agree(view):
    # Under the default strategy the scalar answers "along time" and the 1D
    # quantity "along its own coordinate", so the second is refused; the 'TIME'
    # entry is what puts them on one abscissa.
    select(view, _scalar(), _vector())

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='DEFAULT')
    assert stacks(view)[0].panelCount() == 1

    for key in list(view.imas_viz_api.figureframes):
        view.imas_viz_api.ForgetFigure(key)
    select(view, _scalar(), _vector())
    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='TIME')

    frame = stacks(view)[0]
    assert frame.panelCount() == 2
    np.testing.assert_allclose(panelData(frame, 1)[0], TIMES)
    np.testing.assert_allclose(panelData(frame, 1)[1],
                               [100. * t for t in TIMES])


@pytest.mark.ui
def test_a_quantity_of_two_axes_is_refused_by_name(view, caplog):
    # The old entry died with "TypeError: 'QVizDataArrayHandle' object is not
    # subscriptable" after registering a window with no view in it.
    select(view, _vector(), _matrix())

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='DEFAULT')

    frame = stacks(view)[0]
    assert frame.panelCount() == 1
    assert 'matrix' in caplog.text
    assert 'a picture needs a window of its own' in caplog.text
    assert len(view.imas_viz_api.figToNodes[FigureTypes.STACKEDPLOTTYPE + '1']) \
        == 1


@pytest.mark.ui
def test_a_selection_that_gives_nothing_draws_no_window(view, caplog):
    select(view, _matrix())

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='DEFAULT')

    # The legacy left `StackedPlotView:7` registered with no multiPlotView behind
    # it, and both nodes already recorded as drawn.
    assert view.imas_viz_api.figureframes == {}
    assert view.imas_viz_api.figToNodes == {}
    assert 'nothing to plot' in caplog.text.lower()


@pytest.mark.ui
def test_no_selection_at_all_draws_no_window(view, caplog):
    select(view)

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='TIME')

    assert view.imas_viz_api.figureframes == {}
    assert 'no selected node to draw' in caplog.text


# ---------------------------------------------------------------------------
# The window in the api: its key, and what closing it frees.

@pytest.mark.ui
def test_the_window_is_registered_under_the_stacked_namespace(view):
    select(view, _vector())

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='TIME')

    assert list(view.imas_viz_api.figureframes) == \
        [FigureTypes.STACKEDPLOTTYPE + '1']
    assert view.imas_viz_api.GetStackedPlotViewsCount() == 1


@pytest.mark.ui
def test_closing_the_window_frees_its_key(view):
    # The old window registered its key twice and embedded itself in a plain
    # QMdiSubWindow, so closing it left the key: measured, 'StackedPlotView:1'
    # was registered before and after close(), and the next window was handed :2.
    select(view, _vector())

    entry(view).onPlotToStackedPlotView(all_DTV=False, plotAxis='TIME')

    subWindow = view.imas_viz_api.parent.findChild(QVizMdiSubWindow)
    subWindow.close()

    assert view.imas_viz_api.figureframes == {}
    assert view.imas_viz_api.figToNodes == {}
