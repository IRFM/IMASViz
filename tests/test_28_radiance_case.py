# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""A rank 3 quantity that a real shot actually holds values for.

hard_x_rays.channel[i1].radiance.data on WEST 55799: 38 static channels, each
carrying eight energy bands by 808 time samples. Everything the model has to get
right is here at once -- an array of structures that is not the dynamic one, a
leaf with two axes of its own, one of those axes spelled as a time under the
array that carries the quantity, and an IDS whose homogeneous_time is 0, which
means the shot has no clock to borrow: its IDS.time holds one value while the
channel holds 808.

The rest of the suite reads rank 3 quantities out of stubs built in the test,
because the reference case has rank 3 leaves and none of them filled. This is the
one that says the model meets a dictionary written by someone else.

Skipped when the shot's pulse files are not mounted.
"""

import logging

import numpy as np
import pytest

from conftest import (RANK3_CASE_DATA_DICTIONARY_VERSION, RANK3_CASE_URI,
                      rank3_case_uri_or_skip)

from imasviz.VizDataAccess.QVizAxesSpec import (QVizAxis, QVizAxesSpec,
                                                isUnboundedCoordinate)
from imasviz.VizDataAccess.QVizTensorDataAccess import QVizTensorDataAccess
from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource
from imasviz.VizEntities.QVizDataArrayHandle import QVizDataArrayHandle
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsSlices import QVizPlotAsSlices
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizImagePlot import QVizImagePlot

from support.caseTrees import loadCaseTrees, leafByText, nodeAsTheBuilderBuildsIt
from support.fakes import FakeTreeView
from support.plotting import FakeView, FakeApi

IDS_NAME = 'hard_x_rays'
LEAF = 'hard_x_rays.channel[i].radiance.data'
CHANNEL = (QVizAxis.AOS, IDS_NAME, 'channel')
BANDS, SAMPLES = 8, 808


@pytest.fixture(scope='module')
def case(qapp, request):
    """The shadow tree and the runtime IDS, walked once for all tests."""
    uri = rank3_case_uri_or_skip()
    if uri is None:
        pytest.skip('rank 3 case not reachable: %s' % RANK3_CASE_URI)
    return loadCaseTrees(qapp, (IDS_NAME,), uri=uri,
                         dd_version=RANK3_CASE_DATA_DICTIONARY_VERSION,
                         label='west 55799', request=request)


@pytest.fixture
def treeView(qapp, case):
    view = FakeTreeView(uri=case['uri'])
    view.dataSource = QVizIMASDataSource('west 55799', case['uri'])
    return view


@pytest.fixture
def radiance(treeView, case):
    """The radiance.data node as the tree builder would put it on the screen."""
    element = leafByText(case['trees'][IDS_NAME], LEAF)
    return nodeAsTheBuilderBuildsIt(element, IDS_NAME, case['runtime'][IDS_NAME],
                                    treeView)


def channels(ids):
    return len(ids.channel)


def radianceOf(ids, index):
    return np.asarray(ids.channel[index].radiance.data, dtype=float)


def timeOf(ids, index):
    return np.asarray(ids.channel[index].radiance.time, dtype=float)


@pytest.mark.case
def test_the_shot_holds_the_quantity_the_suite_thinks_it_holds(case):
    ids = case['runtime'][IDS_NAME]

    assert ids.ids_properties.homogeneous_time == 0
    assert channels(ids) == 38
    assert radianceOf(ids, 0).shape == (BANDS, SAMPLES)
    # The reason this case is not redundant with the reference one: the IDS clock
    # holds one value, the channel holds 808.
    assert len(ids.time or []) == 1


@pytest.mark.case
def test_the_shadow_tree_carries_the_coordinate_the_structure_declares(case):
    leaf = leafByText(case['trees'][IDS_NAME], LEAF)

    assert isUnboundedCoordinate(leaf.get('coordinate1').replace('/', '.')) is False
    assert leaf.get('coordinate1').replace('/', '.').endswith('channel(i1).energy_band')


@pytest.mark.case
def test_the_one_dimension_sibling_of_the_array_is_left_anonymous(case):
    # radiance declares two coordinates and holds a 2D 'data' and a 1D 'time'.
    # Naming time's axis with the first of the two would call it an energy band.
    timeLeaf = leafByText(case['trees'][IDS_NAME],
                          'hard_x_rays.channel[i].radiance.time')

    assert isUnboundedCoordinate(timeLeaf.get('coordinate1'))


@pytest.mark.case
def test_an_axis_named_by_an_array_of_structures_keeps_element_ranks(radiance, case):
    # energy_band is an array of structures, not a set of values: the rows of
    # data are its elements, so the axis is their index. Reading values out of
    # the array would put one number where there are eight rows.
    handle = QVizTensorDataAccess(radiance.getDataSource()).GetSignal(
        treeNode=radiance, as_function_of_time=False)

    np.testing.assert_array_equal(np.asarray(handle.getCoordinateValues(1)),
                                  np.arange(BANDS))
    assert len(case['runtime'][IDS_NAME].channel[0].energy_band) == 1


@pytest.mark.case
def test_the_disagreement_between_the_array_and_the_axis_is_said(radiance, caplog):
    # The shot declares one energy band and holds eight rows: the picture is
    # right and the base is inconsistent, and only the log can say so.
    with caplog.at_level(logging.WARNING):
        QVizTensorDataAccess(radiance.getDataSource()).GetSignal(
            treeNode=radiance, as_function_of_time=False)

    assert 'energy_band' in caplog.text
    assert '1' in caplog.text and str(BANDS) in caplog.text


@pytest.mark.case
def test_the_axes_are_one_static_array_and_two_axes_of_the_leaf(radiance):
    axesSpec = QVizAxesSpec.fromTreeNode(radiance)

    assert axesSpec.rank == 3
    channel = axesSpec.axes[0]
    assert channel.origin == QVizAxis.AOS and channel.name == 'channel'
    assert channel.length == 38 and channel.index == 0
    assert not channel.is_time
    bands, time = axesSpec.leafAxes()[0], axesSpec.leafAxes()[1]
    # The dictionary spells this dimension 1..N on the leaf and names it
    # channel(i1)/energy_band on the structure that holds the array -- see
    # tests/test_29_inherited_coordinates.py for the rule that carries it over.
    assert not bands.isUnbounded()
    assert bands.coordinate.endswith('energy_band')
    assert time.is_time and time.coordinate.endswith('radiance.time')
    assert time.units == 's'


@pytest.mark.case
def test_the_read_keeps_every_axis_of_the_leaf_and_pins_the_channel(radiance, case):
    handle = QVizTensorDataAccess(radiance.getDataSource()).GetSignal(
        treeNode=radiance, as_function_of_time=False)

    assert isinstance(handle, QVizDataArrayHandle)
    assert handle.arrayValues.shape == (BANDS, SAMPLES)
    np.testing.assert_allclose(handle.arrayValues, radianceOf(case['runtime'][IDS_NAME], 0))


@pytest.mark.case
def test_the_time_axis_is_the_channel_owns_and_not_the_ids_clock(radiance, case):
    ids = case['runtime'][IDS_NAME]
    handle = QVizTensorDataAccess(radiance.getDataSource()).GetSignal(
        treeNode=radiance, as_function_of_time=False)

    time = np.asarray(handle.getCoordinateValues(2), dtype=float)

    assert time.size == SAMPLES
    np.testing.assert_allclose(time, timeOf(ids, 0))
    # Reading IDS.time here would answer 808 samples with one value.
    assert time[0] != pytest.approx(float(np.asarray(ids.time)[0]), rel=1e-6)


@pytest.mark.case
def test_an_axis_the_dictionary_leaves_unbounded_keeps_element_ranks(radiance):
    handle = QVizTensorDataAccess(radiance.getDataSource()).GetSignal(
        treeNode=radiance, as_function_of_time=False)

    np.testing.assert_array_equal(np.asarray(handle.getCoordinateValues(1)),
                                  np.arange(BANDS))


@pytest.mark.case
def test_the_quantity_is_routed_to_an_image_with_one_control(qapp, radiance, case):
    view = FakeView('imas:hdf5?case=55799', [radiance])
    view.dataSource = QVizIMASDataSource('west 55799', view.uri)
    FakeApi([view])

    command = QVizPlotAsSlices(dataTreeView=view)
    figure = case['runtime'][IDS_NAME]
    try:
        figures = command.execute()

        assert [type(frame) for frame in figures] == [QVizImagePlot]
        assert command.curveFigure is None
        # The radiance has no dynamic array to take the place between pictures,
        # so its one enclosing array -- the 38 channels -- is what the pictures
        # are taken along. It therefore keeps no slider.
        frame = command.imageFigures[0]
        assert frame.sliceControls.keys() == []
        assert frame.framesKey() == CHANNEL
        assert (frame.imageCount(), frame.framesControls.count()) == (3, 3)
        assert frame.framesControls.start() == 0
        assert frame.framesControls.labelText() == 'channel: 0-2 / %d' % (
                channels(figure) - 1)
    finally:
        for frame in command.figures:
            frame.close()


@pytest.mark.case
def test_the_window_reads_three_channels_at_a_time(qapp, radiance, case):
    frame = QVizImagePlot(title='Image:55799')
    try:
        frame.plot(radiance)

        ids = case['runtime'][IDS_NAME]
        for position, channel in enumerate(range(0, 3)):
            # The picture is the channel's values laid out the way the frame
            # draws them, which is transposed here: time horizontal.
            np.testing.assert_allclose(frame.images()[position].image,
                                       radianceOf(ids, channel).T)

        frame.framesControls.setStart(5)

        for position, channel in enumerate(range(5, 8)):
            np.testing.assert_allclose(frame.images()[position].image,
                                       radianceOf(ids, channel).T)
    finally:
        frame.close()


@pytest.mark.case
def test_the_time_axis_lies_horizontal_under_the_picture(qapp, radiance, case):
    # A radiance picture is read as a signal against time; with the dictionary
    # order kept, the 808 samples would stand up the wrong way.
    frame = QVizImagePlot(title='Image:55799')
    try:
        frame.plot(radiance)
        axis = frame.plotItem.getAxis

        assert axis('bottom').labelText == 'time'
        assert axis('bottom').labelUnits == 's'
        # Named by the structure that holds the array, not left anonymous: the
        # rows of data are the elements of channel[i1].energy_band.
        assert axis('left').labelText == 'energy_band'

        rect = frame.images()[0].mapRectToParent(frame.images()[0].boundingRect())
        time = timeOf(case['runtime'][IDS_NAME], 0)
        assert rect.left() == pytest.approx(time[0])
        assert rect.right() == pytest.approx(time[-1])
        assert rect.height() == pytest.approx(BANDS - 1)
    finally:
        frame.close()


@pytest.mark.case
def test_the_picture_carries_the_quantity_and_its_units(qapp, radiance):
    frame = QVizImagePlot(title='Image:55799')
    try:
        frame.plot(radiance)

        assert 'data' in frame.plotItem.titleLabel.text
    finally:
        frame.close()
