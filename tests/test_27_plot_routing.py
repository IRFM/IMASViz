# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""One selection, two kinds of figure: a curve draws one axis, an image two.

The user selects signals, not figure types, and the tree does not tell them which
frame a quantity needs. So the command asks the read how many axes of the quantity
it would draw -- not the dimension the dictionary spells on the leaf, which says
nothing about whether the plot runs along time -- and sends the selection to the
frame that can show it. A quantity with two axes to draw sent to the curve frame
dies on unpacking a data-array handle; a quantity with one axis sent to the image
frame has nothing to colour.

A two-dimension quantity inside a dynamic array is the case worth testing: it has
a time axis, so a decision taken from the presence of time alone calls it a curve.

Nothing opens a case: a two-dimension leaf with values in it needs several
enclosing arrays of structures, and no reference case on this checkout holds one
filled.
"""

import numpy as np
import pytest

from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizImagePlot import QVizImagePlot

from support.fakes import FakeAxesNode
from support.plotting import FakeView, plotCommand, plotted

AOS, LEAF = 'AOS', 'LEAF'
TIME_SLICE = (AOS, 'foo', 'time_slice')
PROFILES_2D = (AOS, 'foo', 'profiles_2d')

TIMES = [0., 1.]
RHO = [0., 1., 2.]
THETA = [0., .5, 1.]

# A 2D slice whose every element says where in the quantity it sits: 100 per time
# slice, 10 per radial point, 1 per vertical point.
def psi(timeIndex):
    return [[100. * timeIndex + 10. * radial + vertical
             for vertical in range(len(THETA))] for radial in range(len(RHO))]


def _idsWithTimeSlices(leaves):
    """foo.time_slice[itime].<leaf>, one element of profiles_2d per time slice."""
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = list(TIMES)
    ids.time_slice = []
    for timeIndex in range(len(TIMES)):
        timeSlice = type(str('TimeSlice'), (), {})()
        timeSlice.time = None
        timeSlice.profiles_2d = []
        for sliceIndex in range(2):
            element = type(str('Profiles2d'), (), {})()
            element.time = None
            for leaf, values in leaves.items():
                setattr(element, leaf, values(timeIndex))
            timeSlice.profiles_2d.append(element)
        ids.time_slice.append(timeSlice)
    return ids


def _twoDimensionInTime(name='psi'):
    """Two axes to draw, and a time axis the image will pin with a control."""
    ids = _idsWithTimeSlices({name: psi})
    return FakeAxesNode(ids, 'foo', 'foo.time_slice[itime].profiles_2d[j]',
                        'FLT_2D', name=name, units='Pa', itimeIndex=0,
                        coordinates=('1..N', '1..M'),
                        indices={'i': '1', 'j': '0'},
                        lengths={'i': str(len(TIMES)), 'j': '2'})


def _twoDimensionStatic():
    """Two axes to draw and nothing around them: an image with no control."""
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0.]
    ids.matrix = [[1., 2., 3.], [4., 5., 6.]]
    return FakeAxesNode(ids, 'foo', 'foo', 'FLT_2D', name='matrix',
                        coordinates=('1..N', '1..M'))


def _oneDimensionInTime(name='z_ion'):
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = list(TIMES)
    ids.profiles_1d = []
    for z in ([1., 2., 3.], [4., 5., 6.]):
        element = type(str('Profiles1d'), (), {})()
        element.time = None
        setattr(element, name, z)
        ids.profiles_1d.append(element)
    return FakeAxesNode(ids, 'foo', 'foo.profiles_1d[itime]', 'FLT_1D',
                        name=name, units='m', itimeIndex=0,
                        coordinates=('1..N',), lengths={'i': str(len(TIMES))})


def _threeAxesLeaf():
    """A leaf with three axes of its own: two drawn, one read between pictures."""
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0.]
    ids.cube = [[[1., 2.], [3., 4.]], [[5., 6.], [7., 8.]]]
    return FakeAxesNode(ids, 'foo', 'foo', 'FLT_3D', name='cube',
                        coordinates=('1..N', '1..M', '1..7'))


def _fourAxesLeaf():
    """The same leaf inside the dynamic array: rank 4, and no frame holds it.

    The time axis takes the place between the pictures, which leaves the leaf's
    three axes inside one picture -- more than two is more than a picture shows,
    and pinning one of them silently is what this path refuses to do.
    """
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
                        indices={'i': '1'}, lengths={'i': str(len(TIMES))})


@pytest.fixture
def run(qtbot):
    """Run a command over the given nodes and hand back (command, figures)."""
    def go(*nodes, **kwargs):
        command = plotCommand(*nodes, **kwargs)
        return command, command.execute()
    return go


@pytest.fixture
def plotCommandOf(qtbot):
    """Build a command over the given nodes without running it.

    For what execute() refuses: the command and what it left behind are the
    findings, and the exception is the least of them.
    """
    return lambda *nodes, **kwargs: plotCommand(*nodes, **kwargs)


@pytest.mark.ui
def test_a_two_dimension_quantity_goes_to_an_image_and_not_a_curve(run):
    command, figures = run(_twoDimensionInTime())

    assert command.curveFigure is None
    assert [type(frame) for frame in figures] == [QVizImagePlot]
    # The dynamic array is the axis read between the pictures, so this figure
    # holds one picture per time slice -- two here, the shot has two.
    assert [frame.imageCount() for frame in figures] == [2]
    np.testing.assert_array_equal(figures[0].images()[0].image, psi(0))
    np.testing.assert_array_equal(figures[0].images()[1].image, psi(1))


@pytest.mark.ui
def test_a_one_dimension_quantity_still_goes_to_the_curve_figure(run):
    command, figures = run(_oneDimensionInTime())

    assert [type(frame) for frame in figures] == [QVizCurvePlot]
    assert command.imageFigures == []
    # A curve does run along time, so it takes one point per time slice -- here
    # the first point of each slice, which is what a curve figure starts on.
    assert plotted(figures[0]) == ([0., 1.], [1., 4.])


@pytest.mark.ui
def test_a_selection_of_both_gets_one_curve_and_one_image(run):
    command, figures = run(_oneDimensionInTime(), _twoDimensionStatic())

    assert [type(frame) for frame in figures] == [QVizCurvePlot, QVizImagePlot]
    assert command.curveFigure.curveCount() == 1
    assert command.imageFigures[0].imageCount() == 1


@pytest.mark.ui
def test_the_quantities_that_share_an_axis_share_the_curve_figure(run):
    command, figures = run(_oneDimensionInTime('z_ion'), _oneDimensionInTime('z_tot'))

    assert len(figures) == 1
    assert figures[0].curveCount() == 2


@pytest.mark.ui
def test_each_two_dimension_quantity_gets_its_own_image(run):
    # Two quantities on one frame would need one colour scale for both and one
    # window answering two axes. The pictures inside one figure are the elements
    # of one axis of one quantity, never two quantities.
    command, figures = run(_twoDimensionStatic(), _twoDimensionInTime())
    images = [frame.images()[0].image for frame in command.imageFigures]

    assert len(command.imageFigures) == 2
    assert [frame.imageCount() for frame in command.imageFigures] == [1, 2]
    np.testing.assert_array_equal(images[0], np.array([[1., 2., 3.], [4., 5., 6.]]))
    np.testing.assert_array_equal(images[1], psi(0))
    assert command.imageFigures[0].figureKey != command.imageFigures[1].figureKey


@pytest.mark.ui
def test_the_image_figure_keeps_its_controls_after_the_command_is_done(run):
    command, figures = run(_twoDimensionInTime())
    frame = figures[0]

    # Only the static array needs a control: the dynamic one is the axis the
    # pictures are taken along, so it is on screen and needs a window instead.
    assert frame.sliceControls.keys() == [PROFILES_2D]
    assert frame.framesKey() == TIME_SLICE
    assert frame.sliceControls.rows()[0].slider.maximum() == 1
    assert (frame.framesControls.count(), frame.framesControls.start()) == (2, 0)

    frame.sliceControls.setIndex(PROFILES_2D, 1)

    np.testing.assert_array_equal(frame.images()[0].image, psi(0))
    np.testing.assert_array_equal(frame.images()[1].image, psi(1))


@pytest.mark.ui
def test_both_kinds_are_registered_under_their_own_figure(run):
    command, figures = run(_oneDimensionInTime(), _twoDimensionStatic())

    assert sorted(command.api.figToNodes[command.curveFigure.figureKey]) == \
           ['foo.profiles_1d[itime].z_ion']
    assert sorted(command.api.figToNodes[command.imageFigures[0].figureKey]) == \
           ['foo.matrix']


@pytest.mark.ui
def test_a_leaf_of_three_axes_is_routed_to_an_image_now(run):
    # This quantity used to be refused outright: three axes to draw, a frame that
    # shows two. One of the three moved between the pictures, so it has a frame.
    command, figures = run(_threeAxesLeaf())

    assert [type(frame) for frame in figures] == [QVizImagePlot]
    assert figures[0].imageCount() == 2
    np.testing.assert_array_equal(figures[0].images()[0].image,
                                  [[1., 2.], [3., 4.]])
    np.testing.assert_array_equal(figures[0].images()[1].image,
                                  [[5., 6.], [7., 8.]])


@pytest.mark.ui
def test_a_quantity_no_frame_can_draw_is_refused_by_name(plotCommandOf, caplog):
    command = plotCommandOf(_fourAxesLeaf())

    with pytest.raises(ValueError):
        command.execute()

    assert command.figures == []
    assert command.api.figureframes == {}
    assert command.api.figToNodes == {}
    # Refusing quietly would leave the user with no figure and no reason; the
    # message goes to the log panel of the shot view it came from.
    assert 'foo.time_slice[itime].cube' in caplog.text
    assert '3 axes to draw' in caplog.text


@pytest.mark.ui
def test_a_two_dimension_quantity_holding_nothing_leaves_no_image_behind(plotCommandOf):
    node = _twoDimensionInTime()
    for timeSlice in node.getIDSRef().time_slice:
        for element in timeSlice.profiles_2d:
            element.psi = []

    command = plotCommandOf(node)
    with pytest.raises(ValueError):
        command.execute()

    assert command.figures == []
    assert command.api.figureframes == {}


@pytest.mark.ui
def test_the_figure_keys_leave_the_legacy_namespaces_alone(run):
    command, figures = run(_oneDimensionInTime(), _twoDimensionStatic())
    keys = [frame.figureKey for frame in figures]

    assert keys == ['SlicesPlot1', 'SlicesImage1']
    assert command.api.GetFiguresKeys('Figure:') == []
    assert command.api.GetFiguresKeys('Image:') == []
