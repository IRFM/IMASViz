# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The image figure, end to end: a quantity becomes pictures, and every axis
outside the pictures stays under the user's hand.

An image draws two axes and pins the rest, so a figure that does not say where
it pinned them shows a picture of one unnamed slice of a quantity. One of those
pinned axes is now read across the images instead of being pinned by a control:
a quantity held by a dynamic array is drawn as three time slices side by side,
which is the only way to compare them. The axes left over keep a control each,
named after the arrays and coordinates the dictionary uses.

Three choices are checked here. The axis spread across the images is the time
one when the quantity has it, the window of images starts at the slice the tree
carries and slides over that axis, and one colour scale answers for all the
images -- comparing two pictures means comparing colours, so a scale that
re-fits itself to each one makes every picture look the same.

Nothing here opens a case. A 2D leaf with values in it needs several enclosing
arrays of structures, and no reference case on this checkout holds one filled
(with GGD ignored, the rank 3 leaves of core_profiles and equilibrium are
empty), so the quantity is held in memory and its axes are what the test says.
"""

import numpy as np
import pytest

from imasviz.VizDataAccess.QVizAxesSpec import QVizAxesSpec
from imasviz.VizDataAccess.QVizSlices import frameLabel
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizImagePlot import QVizImagePlot

from support.fakes import FakeAxesNode

AOS, LEAF = 'AOS', 'LEAF'
TIME_SLICE = (AOS, 'foo', 'time_slice')
PROFILES_2D = (AOS, 'foo', 'profiles_2d')

# rho_tor and theta_poloidal are the leaf's own coordinates; the enclosing
# arrays are the dynamic time_slice and the static profiles_2d. The image draws
# the two leaf axes, time_slice is read across the images, and profiles_2d keeps
# a control.
RHO = [0., 1., 2., 3.]
THETA = [0., .25, .5, .75, 1.]
TIMES = [0., 1., 2., 3., 4.]
SLICES = 3
TREE_TIME = 1
TREE_SLICE = 2
# The window opens on the slice the tree carries, and holds three images.
WINDOW = [TREE_TIME, TREE_TIME + 1, TREE_TIME + 2]


def psi(timeIndex, sliceIndex):
    """One 2D slice, every element carrying where in the quantity it sits."""
    return [[1000. * timeIndex + 100. * sliceIndex + 10. * radial + vertical
             for vertical in range(len(THETA))]
            for radial in range(len(RHO))]


def _ids(times=TIMES):
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = list(times)
    # The leaf coordinates are spelled from the IDS, so they sit at IDS level
    # here -- which is also what makes the axes real arrays rather than ranks.
    ids.rho_tor = list(RHO)
    ids.theta_poloidal = list(THETA)
    ids.time_slice = []
    for timeIndex in range(len(times)):
        timeSlice = type(str('TimeSlice'), (), {})()
        timeSlice.time = None
        timeSlice.profiles_2d = []
        for sliceIndex in range(SLICES):
            element = type(str('Profiles2d'), (), {})()
            element.time = None
            element.psi = psi(timeIndex, sliceIndex)
            timeSlice.profiles_2d.append(element)
        ids.time_slice.append(timeSlice)
    return ids


def _psi(times=TIMES):
    """equilibrium-like: the tree carries time slice 1 and profiles_2d element 2."""
    return FakeAxesNode(_ids(times), 'foo', 'foo.time_slice[itime].profiles_2d[j]',
                        'FLT_2D', name='psi', units='Pa', itimeIndex=0,
                        coordinates=('rho_tor', 'theta_poloidal'),
                        coordinateUnits={1: 'm', 2: 'rad'},
                        indices={'i': str(TREE_TIME), 'j': str(TREE_SLICE)},
                        lengths={'i': str(len(times)), 'j': str(SLICES)})


def _matrix(values=None):
    """A 2D leaf at IDS level: two axes to draw and nothing outside them."""
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0.]
    ids.matrix = [[1., 2., 3.], [4., 5., 6.]] if values is None else values
    return FakeAxesNode(ids, 'foo', 'foo', 'FLT_2D', name='matrix',
                        coordinates=('1..N', '1..M'))


def _vector():
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0.]
    ids.rho_tor = list(RHO)
    ids.vector = [1., 2., 3., 4.]
    return FakeAxesNode(ids, 'foo', 'foo', 'FLT_1D', name='vector',
                        coordinates=('rho_tor',))


def _cube():
    """A leaf with three axes of its own: two are drawn, one is read across images."""
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0.]
    ids.cube = [[[1., 2., 3., 4.], [5., 6., 7., 8.], [9., 10., 11., 12.]],
                [[13., 14., 15., 16.], [17., 18., 19., 20.], [21., 22., 23., 24.]]]
    return FakeAxesNode(ids, 'foo', 'foo', 'FLT_3D', name='cube',
                        coordinates=('1..N', '1..M', '1..7'))


@pytest.fixture
def figure(qtbot):
    widget = QVizImagePlot(title='Image:1')
    qtbot.addWidget(widget)
    return widget


def drawn(figure, index=0):
    """The numbers actually on screen, one picture at a time."""
    return figure.images()[index].image


def drawnRect(figure, index=0):
    """Where the picture sits once the plot transformed it (0.13.7 keeps no
    rect() on an ImageItem: the transform is what the renderer holds)."""
    image = figure.images()[index]
    return image.mapRectToParent(image.boundingRect())


@pytest.mark.ui
def test_the_dynamic_array_is_read_across_the_images(figure):
    assert figure.plot(_psi()) == 3
    assert figure.imageCount() == 3
    # The window opens on the slice the tree carries, not on the first one: the
    # picture the user was looking at stays the first of the three.
    for position, timeIndex in enumerate(WINDOW):
        np.testing.assert_array_equal(drawn(figure, position), psi(timeIndex,
                                                                   TREE_SLICE))


@pytest.mark.ui
def test_the_axis_read_across_the_images_loses_its_control(figure):
    figure.plot(_psi())

    # time_slice is on screen: three pictures are its three elements, so a slider
    # for it would ask for something already displayed.
    assert figure.sliceControls.keys() == [PROFILES_2D]
    assert [row.nameLabel.text() for row in figure.sliceControls.rows()] == \
           ['profiles_2d:']


@pytest.mark.ui
def test_the_window_control_says_which_elements_the_images_are(qtbot):
    figure = QVizImagePlot(title='Image:1')
    qtbot.addWidget(figure)
    figure.plot(_psi())

    assert figure.framesControls.start() == TREE_TIME
    assert figure.framesControls.labelText() == 'time_slice: %d-%d / %d' % (
        WINDOW[0], WINDOW[-1], len(TIMES) - 1)


@pytest.mark.ui
def test_moving_the_window_reads_the_next_elements(figure):
    figure.plot(_psi())

    figure.framesControls.setStart(0)

    for position, timeIndex in enumerate(range(0, 3)):
        np.testing.assert_array_equal(drawn(figure, position), psi(timeIndex,
                                                                   TREE_SLICE))


@pytest.mark.ui
def test_the_window_stops_where_the_axis_does(figure):
    figure.plot(_psi())

    figure.framesControls.setStart(len(TIMES))

    # The last window, not a request past the end of the axis: three images of
    # elements that do not exist would be blank pictures the user cannot read.
    assert figure.framesControls.start() == len(TIMES) - 3
    np.testing.assert_array_equal(drawn(figure, 2), psi(len(TIMES) - 1, TREE_SLICE))


@pytest.mark.ui
def test_fewer_elements_than_images_draws_only_what_exists(figure):
    # The axis length is what the shot holds, not what the tree declares: an IDS
    # with two time slices cannot fill a window of three.
    assert figure.plot(_psi(times=TIMES[:2])) == 2
    assert figure.imageCount() == 2
    np.testing.assert_array_equal(drawn(figure, 1), psi(1, TREE_SLICE))


@pytest.mark.ui
def test_a_two_dimension_quantity_becomes_one_image_when_nothing_is_pinned(figure):
    assert figure.plot(_matrix()) == 1
    assert figure.imageCount() == 1
    assert not figure.framesControls.isVisible()
    np.testing.assert_array_equal(drawn(figure), np.array([[1., 2., 3.],
                                                           [4., 5., 6.]]))


@pytest.mark.ui
def test_the_controls_are_bounded_by_the_arrays_they_move(figure):
    figure.plot(_psi())
    rows = {row.key: row for row in figure.sliceControls.rows()}

    assert rows[PROFILES_2D].slider.maximum() == SLICES - 1
    assert rows[PROFILES_2D].indexLabel.text() == '%d / %d' % (TREE_SLICE,
                                                               SLICES - 1)


@pytest.mark.ui
def test_moving_the_static_array_control_moves_every_image(figure):
    figure.plot(_psi())

    figure.sliceControls.setIndex(PROFILES_2D, 0)

    for position, timeIndex in enumerate(WINDOW):
        np.testing.assert_array_equal(drawn(figure, position), psi(timeIndex, 0))


@pytest.mark.ui
def test_a_slice_change_updates_the_pictures_and_not_the_controls(figure):
    # Rebuilding the controls under a user still holding one would move the
    # handle they are dragging back to the array's default.
    figure.plot(_psi())
    before = figure.sliceControls.rows()

    figure.framesControls.setStart(0)

    assert figure.sliceControls.rows() == before
    assert figure.imageCount() == 3
    np.testing.assert_array_equal(drawn(figure, 0), psi(0, TREE_SLICE))


@pytest.mark.ui
def test_one_colour_scale_answers_for_every_image(figure):
    # Comparing two slices means comparing colours. A scale that re-fits itself
    # to each picture makes every picture look the same whatever it holds.
    figure.plot(_psi())
    levels = figure.colourLevels()
    assert levels is not None

    assert [tuple(image.getLevels()) for image in figure.images()] == \
           [levels] * 3


@pytest.mark.ui
def test_the_scale_does_not_move_when_the_window_does(figure):
    figure.plot(_psi())
    levels = figure.colourLevels()

    figure.framesControls.setStart(0)

    assert figure.colourLevels() == levels
    assert [tuple(image.getLevels()) for image in figure.images()] == \
           [levels] * 3


@pytest.mark.ui
def test_the_scale_spans_the_images_it_answers(figure):
    figure.plot(_psi())

    low, high = figure.colourLevels()

    # The window is three slices of the same quantity: a scale that covered only
    # the first picture would saturate the two others.
    assert low <= min(np.min(drawn(figure, p)) for p in range(3))
    assert high >= max(np.max(drawn(figure, p)) for p in range(3))


@pytest.mark.ui
def test_each_image_says_which_element_of_the_axis_it_is(figure):
    node = _psi()
    figure.plot(node)
    titles = [plotItem.titleLabel.text for plotItem in figure.plotItems()]
    # The same helper the read uses to name a picture: retyping the spelling in
    # the test would only prove the test agrees with itself.
    timeAxis = QVizAxesSpec.fromTreeNode(node).axes[0]
    labels = [frameLabel(timeAxis, index, TIMES) for index in WINDOW]

    assert all('psi' in title for title in titles)
    for label, title in zip(labels, titles):
        assert title.endswith(label)


@pytest.mark.ui
def test_the_image_axes_are_labelled_with_the_coordinates_they_draw(figure):
    figure.plot(_psi())

    for plotItem in figure.plotItems():
        axis = plotItem.getAxis
        assert axis('bottom').labelText == 'rho_tor'
        assert axis('bottom').labelUnits == 'm'
        assert axis('left').labelText == 'theta_poloidal'
        assert axis('left').labelUnits == 'rad'


@pytest.mark.ui
def test_every_image_is_placed_over_the_coordinates_it_was_taken_on(figure):
    # Cells stay element ranks -- a dictionary grid need not be regular -- but
    # the image has to span the coordinate extents, or an axis labelled metres
    # carries rank numbers under it.
    figure.plot(_psi())

    for rect in (drawnRect(figure, position) for position in range(3)):
        assert rect.left() == pytest.approx(RHO[0])
        assert rect.width() == pytest.approx(RHO[-1] - RHO[0])
        assert rect.top() == pytest.approx(THETA[0])
        assert rect.bottom() == pytest.approx(THETA[-1])


@pytest.mark.ui
def test_a_leaf_of_three_axes_draws_two_and_reads_one_across_images(figure):
    # A rank 3 leaf had no frame at all: three axes to draw and a frame that
    # shows two. One axis moves from inside the picture to between pictures, so
    # each picture keeps the two others -- here the (3, 4) face of a (2, 3, 4)
    # quantity, taken at each element of the first.
    assert figure.plot(_cube()) == 2
    assert figure.imageCount() == 2
    np.testing.assert_array_equal(
        drawn(figure, 0), [[1., 2., 3., 4.], [5., 6., 7., 8.], [9., 10., 11., 12.]])
    np.testing.assert_array_equal(
        drawn(figure, 1), [[13., 14., 15., 16.], [17., 18., 19., 20.],
                           [21., 22., 23., 24.]])


@pytest.mark.ui
def test_a_quantity_with_one_axis_to_draw_is_refused_with_a_reason(figure):
    with pytest.raises(ValueError) as raised:
        figure.plot(_vector())

    assert 'foo.vector' in str(raised.value)
    assert figure.imageCount() == 0


@pytest.mark.ui
def test_a_quantity_holding_nothing_says_so(figure):
    with pytest.raises(ValueError) as raised:
        figure.plot(_matrix(values=[]))

    assert 'foo.matrix' in str(raised.value)
    assert figure.imageCount() == 0


@pytest.mark.ui
def test_one_quantity_per_figure_says_so_rather_than_drawing_over_it(figure):
    # The images on a figure are the elements of one axis of one quantity: each
    # has its own title, extent and slice, and all three answer to one colour
    # scale and one window. A second quantity would need a scale of its own.
    figure.plot(_psi())

    with pytest.raises(ValueError) as raised:
        figure.plot(_psi())

    assert 'image' in str(raised.value)
    assert figure.imageCount() == 3
