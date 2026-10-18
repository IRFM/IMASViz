# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The image figure, end to end: a quantity with two axes to draw becomes an
image, and every axis outside the image becomes a control the user can move.

An image pins more than a curve does -- two axes drawn instead of one -- so a
figure that does not say where it pinned the rest shows a picture of one
unnamed slice of a quantity. That is what is checked here: the controls are
there, they are named after the arrays and coordinates the dictionary uses, and
each one moves this image and nothing else. The time axis is one of those
controls: an image does not run along time, so a picture taken at time slice 1
has to say so and let the user pick another one.

Nothing here opens a case. A 2D leaf with values in it needs several enclosing
arrays of structures, and no reference case on this checkout holds one filled
(with GGD ignored, the rank 3 leaves of core_profiles and equilibrium are
empty), so the quantity is held in memory and its axes are what the test says.
"""

import numpy as np
import pytest

from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizImagePlot import QVizImagePlot

from support.fakes import FakeAxesNode

AOS, LEAF = 'AOS', 'LEAF'
TIME_SLICE = (AOS, 'foo', 'time_slice')
PROFILES_2D = (AOS, 'foo', 'profiles_2d')

# rho_tor and theta_poloidal are the leaf's own coordinates; the enclosing
# arrays are the dynamic time_slice and the static profiles_2d. So the image
# draws two axes and pins two more.
RHO = [0., 1., 2., 3.]
THETA = [0., .25, .5, .75, 1.]
TIMES = [0., 1., 2.]
SLICES = 3


def psi(timeIndex, sliceIndex):
    """One 2D slice, every element carrying where in the quantity it sits."""
    return [[1000. * timeIndex + 100. * sliceIndex + 10. * radial + vertical
             for vertical in range(len(THETA))]
            for radial in range(len(RHO))]


def _ids():
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = list(TIMES)
    # The leaf coordinates are spelled from the IDS, so they sit at IDS level
    # here -- which is also what makes the axes real arrays rather than ranks.
    ids.rho_tor = list(RHO)
    ids.theta_poloidal = list(THETA)
    ids.time_slice = []
    for timeIndex in range(len(TIMES)):
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


def _psi():
    """equilibrium-like: the tree carries time slice 1 and profiles_2d element 2."""
    return FakeAxesNode(_ids(), 'foo', 'foo.time_slice[itime].profiles_2d[j]',
                        'FLT_2D', name='psi', units='Pa', itimeIndex=0,
                        coordinates=('rho_tor', 'theta_poloidal'),
                        coordinateUnits={1: 'm', 2: 'rad'},
                        indices={'i': '1', 'j': '2'},
                        lengths={'i': str(len(TIMES)), 'j': str(SLICES)})


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


@pytest.fixture
def figure(qtbot):
    widget = QVizImagePlot(title='Image:1')
    qtbot.addWidget(widget)
    return widget


def drawn(figure):
    """The numbers actually on screen."""
    return figure.images()[0].image


def drawnRect(figure):
    """Where the picture sits once the plot transformed it (0.13.7 keeps no
    rect() on an ImageItem: the transform is what the renderer holds)."""
    image = figure.images()[0]
    return image.mapRectToParent(image.boundingRect())


@pytest.mark.ui
def test_a_two_dimension_quantity_becomes_an_image(figure):
    assert figure.plot(_psi()) == 1
    assert figure.imageCount() == 1
    # The image is the slice the tree carries: time 1, profiles_2d element 2.
    np.testing.assert_array_equal(drawn(figure), psi(1, 2))


@pytest.mark.ui
def test_the_figure_offers_a_control_for_every_axis_outside_the_image(figure):
    figure.plot(_psi())

    assert figure.sliceControls.keys() == [TIME_SLICE, PROFILES_2D]
    assert [row.nameLabel.text() for row in figure.sliceControls.rows()] == \
           ['time_slice:', 'profiles_2d:']


@pytest.mark.ui
def test_the_controls_are_bounded_by_the_arrays_they_move(figure):
    figure.plot(_psi())
    rows = {row.key: row for row in figure.sliceControls.rows()}

    assert rows[TIME_SLICE].slider.maximum() == len(TIMES) - 1
    assert rows[PROFILES_2D].slider.maximum() == SLICES - 1
    assert rows[PROFILES_2D].indexLabel.text() == '2 / %d' % (SLICES - 1)


@pytest.mark.ui
def test_moving_the_static_array_control_moves_the_image(figure):
    figure.plot(_psi())

    figure.sliceControls.setIndex(PROFILES_2D, 0)

    np.testing.assert_array_equal(drawn(figure), psi(1, 0))


@pytest.mark.ui
def test_moving_the_time_control_moves_the_image(figure):
    # An image does not draw time, so the time axis is a control like any other
    # -- and a control that leaves the picture alone is the defect this checks.
    figure.plot(_psi())

    figure.sliceControls.setIndex(TIME_SLICE, 0)

    np.testing.assert_array_equal(drawn(figure), psi(0, 2))


@pytest.mark.ui
def test_a_slice_change_updates_the_image_and_not_the_controls(figure):
    # Rebuilding the controls under a user still holding one would move the
    # handle they are dragging back to the array's default.
    figure.plot(_psi())
    before = figure.sliceControls.rows()

    figure.sliceControls.setIndex(TIME_SLICE, 2)

    assert figure.sliceControls.rows() == before
    assert figure.imageCount() == 1
    np.testing.assert_array_equal(drawn(figure), psi(2, 2))


@pytest.mark.ui
def test_the_colour_scale_does_not_move_when_the_slice_does(figure):
    # Comparing two slices means comparing colours. A scale that re-fits itself
    # to each slice makes every picture look the same whatever it holds.
    figure.plot(_psi())
    levels = figure.colourLevels()
    assert levels is not None

    figure.sliceControls.setIndex(TIME_SLICE, 0)

    assert figure.colourLevels() == levels


@pytest.mark.ui
def test_the_image_axes_are_labelled_with_the_coordinates_they_draw(figure):
    figure.plot(_psi())
    axis = figure.plotItem.getAxis

    assert axis('bottom').labelText == 'rho_tor'
    assert axis('bottom').labelUnits == 'm'
    assert axis('left').labelText == 'theta_poloidal'
    assert axis('left').labelUnits == 'rad'


@pytest.mark.ui
def test_the_image_is_placed_over_the_coordinates_it_was_taken_on(figure):
    # Cells stay element ranks -- a dictionary grid need not be regular -- but
    # the image has to span the coordinate extents, or an axis labelled metres
    # carries rank numbers under it.
    figure.plot(_psi())
    rect = drawnRect(figure)

    assert rect.left() == pytest.approx(RHO[0])
    assert rect.width() == pytest.approx(RHO[-1] - RHO[0])
    assert rect.top() == pytest.approx(THETA[0])
    assert rect.bottom() == pytest.approx(THETA[-1])


@pytest.mark.ui
def test_the_figure_is_titled_after_the_quantity(figure):
    figure.plot(_psi())

    assert 'psi' in figure.plotItem.titleLabel.text


@pytest.mark.ui
def test_a_two_dimension_leaf_with_nothing_around_it_needs_no_control(figure):
    figure.plot(_matrix())

    assert figure.sliceControls.keys() == []
    assert not figure.sliceControls.isVisible()
    np.testing.assert_array_equal(drawn(figure), np.array(
        [[1., 2., 3.], [4., 5., 6.]]))


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
def test_one_image_per_figure_says_so_rather_than_drawing_over_it(figure):
    # Two pictures of the same quantity at different slices would need their own
    # colour scale and their own controls; overlapping them in one frame is what
    # makes a figure unreadable.
    figure.plot(_psi())

    with pytest.raises(ValueError) as raised:
        figure.plot(_psi())

    assert 'image' in str(raised.value)
    assert figure.imageCount() == 1
