# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""One 2D quantity from the tree: pictures, and the slices the picture answers.

"Plot X to -> Image -> New" is the second entry that draws a quantity of two
axes, and it went through a frame of its own -- QvizPlotImageWidget, reached
through Viz_API.Plot2DArray. Measured on this checkout with real tree nodes: the
window was registered and embedded in the MDI area before anything was read, so
a read that failed left an Image:1 window holding no plot at all; the frame was
built from dataTreeView.selectedItem, so right clicking a quantity while another
one was selected plotted the other one -- the menu even titled itself after the
selection, "Plot other to", and drew [9, 9, 9] where the node under the menu held
[[1, 2, 3]]; nothing was ever recorded in the figure bookkeeping, so no menu
could say what the window held; and the picture carried the same label on both
its axes, '1..N' bottom and '1..N' left, because the label code spells every
unbounded coordinate '1..N' whichever dimension it is. Inside a dynamic array it
drew one picture of the element the tree carried, with no control to move it and
no time named anywhere: getTimeCoordinateDim() came back None.

What it had that the image figure did not is the ROI: a movable line on each
drawn axis, the slice under that line drawn as a 1D curve, and the choice to
keep a slice for comparison. That is ported here, and ported better: the line is
placed in the coordinates the picture is laid over rather than in element ranks,
the slice runs against the other axis's coordinate values rather than against
range(len(slice)), the slice follows the window of pictures when that window
moves, and the commands sit on the figure instead of in a context menu built by
the legacy viewBox.

As in the routing and image figure tests, nothing opens a case: a filled 2D leaf
needs several enclosing arrays of structures and no reference case on this
checkout holds one.
"""

import numpy as np
import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import QMdiArea, QPushButton

from imasviz.VizUtils import FigureTypes
from imasviz.Viz_API import Viz_API
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizImagePlot import QVizImagePlot

from support.fakes import FakeAxesNode

RHO = [0., 1., 2., 3.]
THETA = [0., .25, .5, .75]
TIMES = [0., 1., 2., 3., 4.]
TREE_TIME = 1
AOS, LEAF = 'AOS', 'LEAF'
PROFILES_2D = (AOS, 'foo', 'profiles_2d')
TREE_SLICE = 0


def sliceValues(timeIndex):
    """One picture: every element says where in the quantity it sits."""
    return [[100. * timeIndex + 10. * row + column for column in range(len(THETA))]
            for row in range(len(RHO))]


def heldValues(timeIndex, sliceIndex):
    """The same, held by a static array as well: 1000 per time, 100 per slice."""
    return [[1000. * timeIndex + 100. * sliceIndex + 10. * row + column
             for column in range(len(THETA))] for row in range(len(RHO))]


def _ids(dynamic=True, values=None):
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = list(TIMES) if dynamic else [0.]
    ids.rho_tor = list(RHO)
    ids.theta_poloidal = list(THETA)
    if dynamic:
        ids.time_slice = []
        for timeIndex in range(len(TIMES)):
            timeSlice = type(str('TimeSlice'), (), {})()
            timeSlice.time = None
            timeSlice.matrix = sliceValues(timeIndex)
            ids.time_slice.append(timeSlice)
    else:
        ids.matrix = sliceValues(0) if values is None else values
    return ids


def _idsHeld():
    ids = _ids()
    ids.time_slice = []
    for timeIndex in range(len(TIMES)):
        timeSlice = type(str('TimeSlice'), (), {})()
        timeSlice.time = None
        timeSlice.profiles_2d = []
        for sliceIndex in range(2):
            element = type(str('Profiles2d'), (), {})()
            element.time = None
            element.matrix = heldValues(timeIndex, sliceIndex)
            timeSlice.profiles_2d.append(element)
        ids.time_slice.append(timeSlice)
    return ids


def _inTime():
    """Two axes to draw, one array to read between the pictures."""
    return FakeAxesNode(_ids(), 'foo', 'foo.time_slice[itime]', 'FLT_2D',
                        name='matrix', units='Pa', itimeIndex=0,
                        coordinates=('rho_tor', 'theta_poloidal'),
                        coordinateUnits={1: 'm', 2: 'rad'},
                        indices={'i': str(TREE_TIME)},
                        lengths={'i': str(len(TIMES))})


def _held():
    """The same, plus a static array the figure pins with a slider."""
    return FakeAxesNode(_idsHeld(), 'foo', 'foo.time_slice[itime].profiles_2d[j]',
                        'FLT_2D', name='matrix', units='Pa', itimeIndex=0,
                        coordinates=('rho_tor', 'theta_poloidal'),
                        coordinateUnits={1: 'm', 2: 'rad'},
                        indices={'i': str(TREE_TIME), 'j': str(TREE_SLICE)},
                        lengths={'i': str(len(TIMES)), 'j': '2'})


def _static():
    """Two axes to draw and nothing around them."""
    return FakeAxesNode(_ids(dynamic=False), 'foo', 'foo', 'FLT_2D',
                        name='matrix', units='Pa',
                        coordinates=('rho_tor', 'theta_poloidal'),
                        coordinateUnits={1: 'm', 2: 'rad'})


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


@pytest.fixture
def figure(qtbot):
    widget = QVizImagePlot(title='SlicesImage1')
    # Held from the frame: a Qt child does not keep the Python wrapper of its
    # parent alive, and a collected parent destroys the widget under the test.
    widget.frame = widget
    qtbot.addWidget(widget)
    return widget


def plotOne(view, node):
    """The "Plot X to" entry, triggered as the click does."""
    QVizSignalHandling(dataTreeView=view, treeNode=node).plotSignalCommand()


def pictures(view):
    frames = [frame for frame in view.imas_viz_api.figureframes.values()
              if isinstance(frame, QVizImagePlot)]
    assert len(frames) == 1, view.imas_viz_api.figureframes
    return frames[0]


def subMenu(menu, title):
    for action in menu.actions():
        if action.text() == title:
            return action.menu()
    raise AssertionError('no %r submenu in %r' %
                         (title, [action.text() for action in menu.actions()]))


def sliceNumbers(figure, side):
    """The curve the line on one axis answers: (abscissa, values)."""
    return figure.sliceCurve(side).getData()


# ---------------------------------------------------------------------------
# The entry, on the frame the quantity needs.

@pytest.mark.ui
def test_the_image_entry_draws_pictures_of_the_node_under_the_menu(view):
    node = _inTime()
    # The legacy frame was built from the selection: this other node is what
    # would have been drawn.
    view.selectedItem = FakeAxesNode(_ids(dynamic=False), 'foo', 'foo', 'FLT_2D',
                                     name='other', coordinates=('1..N', '1..M'))

    plotOne(view, node)

    frame = pictures(view)
    np.testing.assert_array_equal(frame.images()[0].image, sliceValues(TREE_TIME))
    assert frame.imageCount() == 3


@pytest.mark.ui
def test_the_figure_is_recorded_under_the_key_its_title_carries(view):
    plotOne(view, _inTime())
    keys = view.imas_viz_api.GetFiguresKeys(figureType=FigureTypes.IMAGEPLOTTYPE)

    # figToNodes is how the menus say what a window holds: the legacy image
    # registered the window and nothing else, so the window was unaddressable.
    assert len(keys) == 1
    assert list(view.imas_viz_api.figToNodes[keys[0]]) == ['foo.time_slice[itime].matrix']


@pytest.mark.ui
def test_no_legacy_image_key_is_produced(view):
    plotOne(view, _inTime())

    # Two namespaces for one kind of window is two Show/Hide menus and one
    # figure the "add to" entries cannot fill. Spelled as a prefix, because the
    # 'Image:' namespace is gone: an entry in FigureTypes for it would outlive
    # the only frame that ever produced one.
    assert view.imas_viz_api.GetFiguresKeys(figureType=FigureTypes.FIGURETYPE) == []
    assert not [key for key in view.imas_viz_api.figureframes
                if key.startswith('Image:')]


@pytest.mark.ui
def test_the_submenu_names_the_frame_the_quantity_needs(view):
    plotOne(view, _static())

    menu = QVizSignalHandling(dataTreeView=view,
                              treeNode=_inTime()).menuPlotCurrentSignalNode()
    imageMenu = subMenu(menu, 'Image')

    assert [action.text() for action in imageMenu.actions()] == ['New']
    assert 'Figure' not in [action.text() for action in menu.actions()]


@pytest.mark.ui
def test_a_picture_quantity_that_holds_nothing_costs_no_window(view, caplog):
    node = _static()
    node.getIDSRef().matrix = []

    plotOne(view, node)

    assert view.imas_viz_api.figureframes == {}
    assert 'foo.matrix' in caplog.text


# ---------------------------------------------------------------------------
# The ROI: a line per drawn axis, in the coordinates the picture is laid over.

@pytest.mark.ui
def test_a_movable_line_per_axis_of_the_picture(figure):
    figure.plot(_static())

    for side in ('bottom', 'left'):
        line = figure.sliceLine(side)
        assert line.movable
        # The picture spans the coordinate extents, so a line in ranks would
        # sit somewhere else than where the user sees it.
        low, high = line.bounds()
        expected = (RHO if side == 'bottom' else THETA)
        assert (low, high) == (pytest.approx(expected[0]),
                               pytest.approx(expected[-1]))


@pytest.mark.ui
def test_the_line_answers_the_slice_under_it_against_the_other_axis(figure):
    figure.plot(_static())
    line = figure.sliceLine('bottom')

    line.setPos(2.0)

    x, y = sliceNumbers(figure, 'bottom')
    np.testing.assert_allclose(x, THETA)
    np.testing.assert_allclose(y, [sliceValues(0)[2][column]
                                   for column in range(len(THETA))])


@pytest.mark.ui
def test_the_line_reads_the_nearest_element_not_the_one_below_it(figure):
    figure.plot(_static())

    # The grid is 1 metre wide here, but a shot's is not: a slice is an element
    # of the array, and the one the line is closest to is the one it stands on.
    figure.sliceLine('bottom').setPos(2.4)
    lower = figure.sliceNumbers('bottom')[1]
    figure.sliceLine('bottom').setPos(2.6)

    assert not np.array_equal(lower, figure.sliceNumbers('bottom')[1])


@pytest.mark.ui
def test_the_line_says_which_axis_it_stands_on(figure):
    figure.plot(_static())
    figure.sliceLine('bottom').setPos(2.0)

    assert figure.sliceLabelText('bottom') == 'rho_tor[m]=2'


@pytest.mark.ui
def test_the_slice_plots_are_labelled_like_the_picture(figure):
    figure.plot(_static())

    assert figure.sliceAxisLabel('bottom') == ('theta_poloidal', 'rad')
    assert figure.sliceAxisLabel('left') == ('rho_tor', 'm')


# ---------------------------------------------------------------------------
# Reading a position off a slice.

@pytest.mark.ui
def test_each_slice_carries_a_movable_cursor(figure):
    # The legacy window put a marker on each slice plot by default, and the
    # manual documents it; here it is bounded by the same coordinate extents as
    # the picture, because the slice runs along those values too.
    figure.plot(_static())

    for side, expected in (('bottom', THETA), ('left', RHO)):
        marker = figure.sliceMarkers(side)[0]
        assert marker.movable
        low, high = marker.bounds()
        assert (low, high) == (pytest.approx(expected[0]),
                               pytest.approx(expected[-1]))


@pytest.mark.ui
def test_a_cursor_says_which_axis_it_reads(figure):
    # The units are in the label, so a slice running along time reads seconds.
    figure.plot(_static())
    figure.sliceMarkers('bottom')[0].setPos(0.5)

    assert figure.sliceMarkerText('bottom') == 'theta_poloidal[rad]=0.5'


@pytest.mark.ui
def test_a_cursor_can_be_added_and_taken_away(figure):
    figure.plot(_static())
    assert len(figure.sliceMarkers('left')) == 1

    figure.addSliceMarker('left')
    assert len(figure.sliceMarkers('left')) == 2

    figure.clearSliceMarkers()
    assert figure.sliceMarkers('left') == []
    # Taking the cursors away leaves the slice itself: they read it, they are
    # not it.
    assert figure.sliceCurve('left').getData()[1].size == len(RHO)


# ---------------------------------------------------------------------------
# The slice follows the pictures.

@pytest.mark.ui
def test_moving_the_window_of_pictures_moves_the_slice_with_it(figure):
    figure.plot(_inTime())
    assert figure.framesControls.start() == TREE_TIME

    figure.framesControls.setStart(0)

    x, y = sliceNumbers(figure, 'bottom')
    np.testing.assert_allclose(y, [sliceValues(0)[2][column]
                                   for column in range(len(THETA))])


@pytest.mark.ui
def test_moving_a_pinned_axis_moves_the_slice_with_it(figure):
    # The slice is a row of the picture that is on screen, so a control that
    # changes what is on screen changes the slice: a curve left behind would be
    # a record of a picture the user no longer sees.
    figure.plot(_held())
    figure.sliceLine('bottom').setPos(2.0)

    figure.sliceControls.setIndex(PROFILES_2D, 1)

    x, y = sliceNumbers(figure, 'bottom')
    np.testing.assert_allclose(x, THETA)
    np.testing.assert_allclose(y, [heldValues(TREE_TIME, 1)[2][column]
                                   for column in range(len(THETA))])


@pytest.mark.ui
def test_the_two_lines_answer_their_own_slice(figure):
    # One line stands on each drawn axis: the bottom one picks a column and runs
    # along the left axis, the left one picks a row and runs along the bottom.
    figure.plot(_static())

    figure.sliceLine('left').setPos(0.25)

    assert not np.array_equal(sliceNumbers(figure, 'bottom')[1],
                              sliceNumbers(figure, 'left')[1])


# ---------------------------------------------------------------------------
# Keeping a slice is the point of the line.

@pytest.mark.ui
def test_keeping_a_slice_leaves_it_on_the_plot(figure):
    figure.plot(_static())
    figure.sliceLine('bottom').setPos(1.0)

    figure.keepSlice('bottom')
    kept = figure.sliceNumbers('bottom')[1]
    figure.sliceLine('bottom').setPos(3.0)

    # The kept curve is a record of where the line was, not a second view of
    # where it is now: comparing slices is the whole feature.
    np.testing.assert_allclose(figure.keptSlices('bottom')[0][1], kept)
    assert figure.sliceCurve('bottom').getData()[1][-1] == \
        sliceValues(0)[3][-1]


@pytest.mark.ui
def test_a_kept_slice_says_where_it_was_taken(figure):
    figure.plot(_static())
    figure.sliceLine('bottom').setPos(1.0)

    figure.keepSlice('bottom')

    assert figure.keptSlices('bottom')[0][0] == 'rho_tor[m]=1'


@pytest.mark.ui
def test_the_kept_slices_are_dropped_on_request(figure):
    figure.plot(_static())
    for position in (1.0, 3.0):
        figure.sliceLine('bottom').setPos(position)
        figure.keepSlice('bottom')

    assert len(figure.keptSlices('bottom')) == 2
    figure.clearKeptSlices()
    assert figure.keptSlices('bottom') == []
    # The line and its slice stay: clearing what was kept is not clearing the
    # picture.
    assert figure.sliceCurve('bottom').getData()[1].size == len(THETA)


@pytest.mark.ui
def test_the_commands_are_on_the_figure_not_only_in_a_menu(figure, qtbot):
    figure.plot(_static())
    figure.sliceLine('bottom').setPos(1.0)

    buttons = figure.findChildren(QPushButton)
    labels = [button.text() for button in buttons]
    assert 'Keep this slice' in labels
    assert 'Delete the kept slices' in labels

    for button in buttons:
        if button.text() == 'Keep this slice':
            qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    assert len(figure.keptSlices('bottom')) == 1


# ---------------------------------------------------------------------------
# A quantity with one picture is still a quantity of two axes.

@pytest.mark.ui
def test_a_single_picture_still_answers_its_slices(figure):
    figure.plot(_static())
    assert figure.imageCount() == 1

    figure.sliceLine('left').setPos(0.25)

    x, y = sliceNumbers(figure, 'left')
    np.testing.assert_allclose(x, RHO)
    np.testing.assert_allclose(y, [sliceValues(0)[row][1]
                                   for row in range(len(RHO))])
