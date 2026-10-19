# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Plotting one node from the tree, into the frame its axes call for.

Three entries do this today: "Plot as function of time", "Plot X to -> Figure ->
New", and the same with an existing figure picked from the submenu. All three end
in one command that reads through a plot widget and draws two rows or nothing: a
quantity of two axes is refused with "only 1D plots are currently supported"
*after* a window has been opened for it, and a quantity of three is refused too
although the read walks its axes. The time entry reads the node from
`dataTreeView.selectedItem` rather than the one the menu was built on, and takes
its index from `infoDict['i']` -- the loop letter of the *first* enclosing array
of structures, so a quantity held by two of them is plotted at the outer element.
The submenu is built with `menu.addMenu('Figure')`, which is the dangling-submenu
defect T0 removed from the Show/Hide menus: the entry is there to look at and
gone to click.

What is pinned is the shape of the replacement: the same entries ask the read how
many axes it would draw and pick the frame that shows them, the node under the
menu is the node drawn, the index pinned is the one the tree carries, the window
is reachable under the key it was drawn with, and a refusal costs no window. As
in the routing and image tests, nothing opens a case: the quantities live in
memory, because no reference case on this checkout holds a filled leaf of three
axes.
"""

import numpy as np
import pytest
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMdiArea

from imasviz.VizUtils import FigureTypes
from imasviz.Viz_API import Viz_API
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizImagePlot import QVizImagePlot

from support.fakes import FakeAxesNode

TIMES = [0., 1., 2.]
RHO = [0.1, 0.2, 0.3, 0.4]
VALUES = [10., 20., 30., 40.]
OTHER = [-1., -2., -3., -4.]
# The tree points at the second element of the static array; only that element
# carries the values the plot has to show.
SET_INDEX = 1
MAJOR_RADIUS = [6.0, 6.1, 6.2]


def _idsWith(name, values):
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0.]
    ids.rho_tor = list(RHO)
    setattr(ids, name, list(values))
    return ids


def _vector(name='vector', values=VALUES):
    """One axis of its own, at IDS level: a curve, and nothing pinned."""
    return FakeAxesNode(_idsWith(name, values), 'foo', 'foo', 'FLT_1D',
                        name=name, units='m', coordinates=('rho_tor',),
                        coordinateUnits={1: 'm'})


def _scalarInTwoArrays():
    """One number per time slice, held by a static array of structures as well.

    Two enclosing arrays: the outer one is pinned by the index the tree carries,
    the inner one is the time base. The outer array's letter is 'i' and the time
    one's is 'j', which is exactly the difference infoDict['i'] flattens.
    """
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = list(TIMES)
    ids.sets = []
    for setIndex in range(SET_INDEX + 1):
        oneSet = type(str('Set'), (), {})()
        oneSet.time_slice = []
        for timeIndex in range(len(TIMES)):
            timeSlice = type(str('TimeSlice'), (), {})()
            timeSlice.time = None
            timeSlice.major_radius = (MAJOR_RADIUS[timeIndex]
                                      if setIndex == SET_INDEX
                                      else -float(timeIndex))
            oneSet.time_slice.append(timeSlice)
        ids.sets.append(oneSet)
    return FakeAxesNode(ids, 'foo', 'foo.sets[i].time_slice[itime]', 'FLT_0D',
                        name='major_radius', units='m', itimeIndex=1,
                        indices={'i': str(SET_INDEX), 'j': str(len(TIMES) - 1)},
                        lengths={'i': str(SET_INDEX + 1), 'j': str(len(TIMES))})


def _matrix():
    """Two axes to draw and nothing around them: a picture, not two curves."""
    ids = _idsWith('vector', [1., 2.])
    ids.matrix = [[1., 2., 3.], [4., 5., 6.]]
    return FakeAxesNode(ids, 'foo', 'foo', 'FLT_2D', name='matrix',
                        coordinates=('1..N', '1..M'))


def _fourAxes():
    """Three axes to draw and a time base: no frame shows that in one picture."""
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = list(TIMES)
    ids.time_slice = []
    for timeIndex in range(len(TIMES)):
        timeSlice = type(str('TimeSlice'), (), {})()
        timeSlice.time = None
        timeSlice.cube = [[[1., 2.], [3., 4.]], [[5., 6.], [7., 8.]]]
        ids.time_slice.append(timeSlice)
    return FakeAxesNode(ids, 'foo', 'foo.time_slice[itime]', 'FLT_3D',
                        name='cube', itimeIndex=0,
                        coordinates=('1..N', '1..M', '1..7'),
                        indices={'i': str(len(TIMES) - 1)},
                        lengths={'i': str(len(TIMES))})


@pytest.fixture
def view(qapp):
    """One shot view and the api it reports its figures to, with an MDI area."""

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

    shot = FakeView()
    # The MDI area owns the windows the commands open, so it has to outlive the
    # call that builds it: the api holds it as its Qt parent.
    shot.mdi = QMdiArea()
    shot.imas_viz_api = Viz_API(parent=shot.mdi)
    shot.imas_viz_api.DTVlist = [shot]
    return shot


def plotOne(view, node):
    """The "Plot X to -> Figure -> New" entry, triggered as the click does."""
    QVizSignalHandling(dataTreeView=view, treeNode=node).plotSignalCommand()


def plotAlongTime(view, node):
    """The "Plot as function of time" entry, triggered as the click does."""
    action = QVizSignalHandling(dataTreeView=view,
                                treeNode=node).actionPlotAsFunctionOfTime()
    assert action is not None, 'no "as function of time" entry for this node'
    action.trigger()


def curveFigures(view):
    return [frame for frame in view.imas_viz_api.figureframes.values()
            if isinstance(frame, QVizCurvePlot)]


def oneCurveFigure(view):
    frames = curveFigures(view)
    assert len(frames) == 1, view.imas_viz_api.figureframes
    return frames[0]


def rows(frame):
    """The curves on a figure, as the plot holds them."""
    return [frame.curves()[row].getData() for row in range(frame.curveCount())]


def figureSubMenu(menu):
    """The 'Figure' submenu of a 'Plot X to' menu, as the click opens it."""
    for action in menu.actions():
        if action.text() == 'Figure':
            return action.menu()
    raise AssertionError('no Figure submenu in %r' %
                         [action.text() for action in menu.actions()])


# ---------------------------------------------------------------------------
# The frame the quantity needs, not the one the menu happened to offer.

@pytest.mark.ui
def test_a_quantity_with_one_axis_to_draw_becomes_a_curve(view):
    plotOne(view, _vector())

    [[x, y]] = rows(oneCurveFigure(view))
    np.testing.assert_array_almost_equal(x, RHO)
    np.testing.assert_array_almost_equal(y, VALUES)


@pytest.mark.ui
def test_a_quantity_with_two_axes_to_draw_becomes_a_picture(view, caplog):
    # The legacy answer was a window opened first and a logged "only 1D plots
    # are currently supported" after it. A quantity of two axes is a picture,
    # and the read already knows how to hand one over.
    plotOne(view, _matrix())

    pictures = [frame for frame in view.imas_viz_api.figureframes.values()
                if isinstance(frame, QVizImagePlot)]
    assert len(pictures) == 1, view.imas_viz_api.figureframes
    np.testing.assert_array_equal(pictures[0].images()[0].image,
                                  [[1., 2., 3.], [4., 5., 6.]])


@pytest.mark.ui
def test_a_quantity_no_frame_can_draw_costs_no_window(view, caplog):
    plotOne(view, _fourAxes())

    # An empty window the user has to close by hand is not an answer. The reason
    # belongs in the log panel of the shot view it came from.
    assert view.imas_viz_api.figureframes == {}
    assert 'foo.time_slice[itime].cube' in caplog.text


# ---------------------------------------------------------------------------
# The window the curve is in is reachable, and addable to.

@pytest.mark.ui
def test_the_window_is_registered_under_the_key_its_title_carries(view):
    plotOne(view, _vector())

    # The key is how Show/Hide and Delete address a window: a frame registered
    # nowhere is a window the user cannot close from any menu.
    keys = view.imas_viz_api.GetFiguresKeys(figureType=FigureTypes.CURVEPLOTTYPE)
    assert len(keys) == 1
    assert view.imas_viz_api.figureframes[keys[0]] is oneCurveFigure(view)
    assert list(view.imas_viz_api.figToNodes[keys[0]]) == ['foo.vector']


@pytest.mark.ui
def test_the_figure_submenu_offers_the_frames_this_command_fills(view):
    plotOne(view, _vector())
    key = view.imas_viz_api.GetFiguresKeys(figureType=FigureTypes.CURVEPLOTTYPE)[0]
    # A legacy frame is filled by the old path, which cannot read a quantity of
    # two axes: listing it here is an entry that cannot work.
    view.imas_viz_api.figureframes['Figure:1'] = QVizCurvePlot(title='Figure:1')

    menu = QVizSignalHandling(dataTreeView=view,
                              treeNode=_vector()).menuPlotCurrentSignalNode()

    assert 'New' in [action.text() for action in figureSubMenu(menu).actions()]
    assert key in [action.text() for action in figureSubMenu(menu).actions()]
    assert 'Figure:1' not in [action.text()
                              for action in figureSubMenu(menu).actions()]


@pytest.mark.ui
def test_adding_a_node_to_an_existing_figure_adds_a_curve(view):
    plotOne(view, _vector())
    key = view.imas_viz_api.GetFiguresKeys(figureType=FigureTypes.CURVEPLOTTYPE)[0]
    number = view.imas_viz_api.getFigureKeyNum(key, FigureTypes.CURVEPLOTTYPE)

    QVizSignalHandling(dataTreeView=view,
                       treeNode=_vector('other', OTHER)).addSignalPlotToFig(number)

    frame = view.imas_viz_api.figureframes[key]
    assert frame.curveCount() == 2
    np.testing.assert_array_almost_equal(rows(frame)[1][1], OTHER)
    assert len(curveFigures(view)) == 1


# ---------------------------------------------------------------------------
# "As function of time": the node under the menu, at the index the tree carries.

@pytest.mark.ui
def test_the_history_is_read_for_the_element_the_tree_carries(view):
    plotAlongTime(view, _scalarInTwoArrays())

    [[x, y]] = rows(oneCurveFigure(view))
    np.testing.assert_array_almost_equal(x, TIMES)
    np.testing.assert_array_almost_equal(y, MAJOR_RADIUS)


@pytest.mark.ui
def test_the_node_under_the_menu_is_the_node_drawn(view):
    # The entry reads dataTreeView.selectedItem, so right clicking a quantity
    # while another one is selected plots the other one.
    node = _scalarInTwoArrays()
    view.selectedItem = _vector()

    plotAlongTime(view, node)

    [[_, y]] = rows(oneCurveFigure(view))
    np.testing.assert_array_almost_equal(y, MAJOR_RADIUS)


@pytest.mark.ui
def test_the_time_entry_follows_the_axes_not_the_leaf_spelling(view):
    # The gate asked the dictionary whether the leaf was 1D and dynamic, and
    # whether its path was time dependent. A scalar held by the dynamic array is
    # a history, plainly, and got no entry; a static curve got none either, which
    # is right, but for a reason that has nothing to do with the quantity.
    assert (QVizSignalHandling(dataTreeView=view,
                               treeNode=_scalarInTwoArrays())
            .actionPlotAsFunctionOfTime() is not None)

    for node in (_vector(), _matrix()):
        assert (QVizSignalHandling(dataTreeView=view, treeNode=node)
                .actionPlotAsFunctionOfTime() is None), node
