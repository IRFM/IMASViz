# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The curve figure, end to end: a rank 3 quantity becomes a curve whose slices
the user can move.

The model, the read and the widget each have their own tests. What is checked
here is the loop between them, which is the part a user experiences: plot the
quantity, see a control for every axis the read pinned, move one, see that curve
change and no other.

Nothing here opens a case. A rank 3 quantity with values in it exists in no
reference case on this checkout (with GGD ignored, the rank 3 leaves of
core_profiles and equilibrium are empty), so the quantity is held in memory and
its axes are exactly what the test says they are.
"""

import pytest

from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot

from support.fakes import FakeAxesNode

AOS, LEAF = 'AOS', 'LEAF'
ION = (AOS, 'foo', 'ion')
RADIAL = (LEAF, 'foo', 'dimension 1')

# Two time slices, two ions each, three radial points each. profiles_1d is the
# dynamic array, ion a static one, and each ion carries two rank 1 leaves.
VALUES = {'z_ion': [[[1., 2., 3.], [10., 20., 30.]],
                    [[4., 5., 6.], [40., 50., 60.]]],
          'density': [[[7., 8., 9.], [70., 80., 90.]],
                      [[14., 15., 16.], [140., 150., 160.]]]}


def _idsWith(leafValues):
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0., 1.]
    # Every leaf of the stub has the same shape: time slices, then ions, then
    # radial points.
    shape = next(iter(leafValues.values()))
    ids.profiles_1d = []
    for index in range(len(shape)):
        slice_ = type(str('Slice'), (), {})()
        slice_.time = None
        slice_.ion = []
        for ionIndex in range(len(shape[0])):
            ion = type(str('Ion'), (), {})()
            for leaf, values in leafValues.items():
                setattr(ion, leaf, values[index][ionIndex])
            slice_.ion.append(ion)
        ids.profiles_1d.append(slice_)
    return ids


def _leaf(name, ionIndex='1'):
    """One of the rank 3 leaves, the ion array read at `ionIndex` by the tree."""
    return FakeAxesNode(_idsWith(VALUES), 'foo', 'foo.profiles_1d[itime].ion[j]',
                        'FLT_1D', name=name, itimeIndex=0, coordinates=('1..N',),
                        indices={'i': '0', 'j': str(ionIndex)},
                        lengths={'i': '2', 'j': '2'})


def _scalarInTime():
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0., 1.]
    ids.profiles_1d = []
    for gap in (100., 200.):
        element = type(str('Element'), (), {})()
        element.time = None
        element.gap = gap
        ids.profiles_1d.append(element)
    return FakeAxesNode(ids, 'foo', 'foo.profiles_1d[itime]', 'FLT_0D', name='gap',
                        itimeIndex=0, coordinates=(), lengths={'i': '2'})


def _scalarInAoS():
    """A scalar held by a static array: no axis of its own to run along.

    The figure it is plotted on decides its abscissa, so the read has nothing to
    spread the value over until something else is drawn.
    """
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0., 1.]
    ids.ion = []
    for gap in (7., 9.):
        ion = type(str('Ion'), (), {})()
        ion.gap = gap
        ids.ion.append(ion)
    # The array is the only one around the leaf, so it is level 1 and the tree
    # keys its index by that level's letter -- which is what the axes model reads
    # back. Spelling it with the next letter used to cost nothing, because the
    # node's own index was never asked: the read took the index another curve's
    # control happened to hold.
    return FakeAxesNode(ids, 'foo', 'foo.ion[i]', 'FLT_0D', name='gap',
                        coordinates=(), indices={'i': '1'}, lengths={'i': '2'},
                        alongTime=False)


@pytest.fixture
def figure(qtbot):
    widget = QVizCurvePlot(title='Figure:1')
    qtbot.addWidget(widget)
    return widget


def plotted(figure, index=0):
    """The numbers actually on screen for one curve."""
    x, y = figure.curves()[index].getData()
    return list(x), list(y)


def legendOf(figure):
    """The legend's labels, in the order the traces were drawn.

    A legend entry is a `(sample, LabelItem)` pair, and a `LabelItem` keeps its
    string in `.text`.
    """
    return [text.text for _, text in figure.pgPlotWidget.getPlotItem().legend.items]


@pytest.mark.ui
def test_a_rank_three_quantity_becomes_one_curve(figure):
    assert figure.plot(_leaf('z_ion')) == 1
    assert figure.curveCount() == 1
    _, y = plotted(figure)
    # The curve runs along time at the ion index the tree carries (1) and the
    # radial point asked for (0).
    assert y == [10., 40.]


@pytest.mark.ui
def test_the_figure_offers_a_control_for_the_leaf_coordinate_only(figure):
    """The array the tree stands on is fixed; the leaf's coordinate is not.

    The node asked for is an *element* of `ion`. Another element is another node,
    so a slider here would move a curve the user never asked about -- and a second
    curve of the same array would be read at the first one's element. What the tree
    does not fix is the leaf's own coordinate, and that keeps its control.
    """
    figure.plot(_leaf('z_ion'))

    assert figure.sliceControls.keys() == [RADIAL]
    assert [row.nameLabel.text() for row in figure.sliceControls.rows()] == \
           ['dimension 1:']
    assert legendOf(figure) == ['foo.profiles_1d[itime].ion[1].z_ion']


@pytest.mark.ui
def test_moving_the_coordinate_slice_moves_that_curve(figure):
    figure.plot(_leaf('z_ion'))
    before = plotted(figure)

    figure.sliceControls.setIndex(RADIAL, 2)

    assert plotted(figure) != before
    assert plotted(figure)[1] == [30., 60.]


@pytest.mark.ui
def test_two_elements_of_one_array_in_one_figure_are_two_curves(figure):
    """The loop the per-trace index set exists for.

    The figure used to carry one index per *axis*, shared by every curve, and the
    read took it from there: asking for ion 0 then ion 1 drew the same element
    twice, and the legend spelled both traces `ion[j]`, so nothing on screen said
    they were the same curve.
    """
    figure.plot(_leaf('z_ion', ionIndex=0))
    figure.plot(_leaf('z_ion', ionIndex=1))

    assert plotted(figure, 0)[1] == [1., 4.]
    assert plotted(figure, 1)[1] == [10., 40.]
    assert legendOf(figure) == ['foo.profiles_1d[itime].ion[0].z_ion',
                                'foo.profiles_1d[itime].ion[1].z_ion']


@pytest.mark.ui
def test_a_scalar_in_the_dynamic_array_needs_no_control(figure):
    # Time is the only axis and the curve draws it, so there is nothing left
    # fixed and nothing to show.
    figure.plot(_scalarInTime())

    assert figure.sliceControls.keys() == []
    assert plotted(figure) == ([0., 1.], [100., 200.])


@pytest.mark.ui
def test_the_time_axis_is_labelled_as_time(figure):
    figure.plot(_scalarInTime())
    axis = figure.pgPlotWidget.getPlotItem().getAxis('bottom')

    assert axis.labelText == 'time'
    assert axis.labelUnits == 's'


@pytest.mark.ui
def test_two_quantities_of_one_array_share_one_control(figure):
    # The leaf is sampled on one radial grid whether its z or its density is
    # drawn, so one control moves both. The ion array is not a control at all:
    # each curve keeps the element the tree was standing on, which is why the two
    # here can disagree about which ion they came from and be right both times.
    figure.plot(_leaf('z_ion'))
    figure.plot(_leaf('density'))

    assert figure.sliceControls.keys() == [RADIAL]
    assert figure.curveCount() == 2
    assert legendOf(figure) == ['foo.profiles_1d[itime].ion[1].z_ion',
                                'foo.profiles_1d[itime].ion[1].density']


@pytest.mark.ui
def test_two_elements_of_one_array_keep_their_own_curve(figure):
    """What the shared control used to make impossible, and what replaced it.

    Two quantities of one array share their coordinate; two elements of that array
    share nothing. The tensor representation, where one slider does drive several
    traces at once, is test_60's subject.
    """
    figure.plot(_leaf('z_ion', ionIndex=0))
    figure.plot(_leaf('density', ionIndex=1))

    assert plotted(figure, 0)[1] == [1., 4.]
    assert plotted(figure, 1)[1] == [70., 140.]


@pytest.mark.ui
def test_moving_the_radial_slice_moves_both_curves(figure):
    figure.plot(_leaf('z_ion'))
    figure.plot(_leaf('density'))

    figure.sliceControls.setIndex(RADIAL, 2)

    assert plotted(figure, 0)[1] == [30., 60.]
    assert plotted(figure, 1)[1] == [90., 160.]


@pytest.mark.ui
def test_a_scalar_is_spread_over_the_axis_already_drawn(figure):
    # A scalar held by a static array has no axis of its own. On a figure where
    # something else already runs along an axis, the honest reading is the same
    # value at every point of that axis -- which is what the table and the
    # stacked figure have always shown, and what this read used to refuse.
    figure.plot(_leaf('z_ion'))

    assert figure.plot(_scalarInAoS()) == 1
    x, y = plotted(figure, 1)

    assert x == [0., 1.]
    assert y == [9., 9.]


@pytest.mark.ui
def test_the_spread_scalar_says_so_in_the_shot_log(figure, caplog):
    # A flat line is one value, not a measurement along the axis: the shot's log
    # panel has to carry that, or a flat line reads as a flat quantity.
    figure.plot(_leaf('z_ion'))
    caplog.clear()

    figure.plot(_scalarInAoS())

    warnings = [record.getMessage() for record in caplog.records
                if record.levelname == 'WARNING']
    assert any('gap' in message for message in warnings)


@pytest.mark.ui
def test_a_scalar_with_nothing_to_run_along_says_so(figure):
    with pytest.raises(ValueError) as raised:
        figure.plot(_scalarInAoS())

    assert 'gap' in str(raised.value)
    assert figure.curveCount() == 0


@pytest.mark.ui
def test_a_quantity_holding_nothing_says_so(figure):
    # An empty curve drawn without a word is how a rank 3 quantity used to end
    # up on screen: the old path had no branch for that shape and discarded every
    # slice that failed to evaluate.
    empty = _leaf('z_ion')
    empty.getIDSRef().profiles_1d[0].ion[0].z_ion = []
    empty.getIDSRef().profiles_1d[0].ion[1].z_ion = []
    empty.getIDSRef().profiles_1d[1].ion[0].z_ion = []
    empty.getIDSRef().profiles_1d[1].ion[1].z_ion = []

    with pytest.raises(ValueError) as raised:
        figure.plot(empty)

    assert 'z_ion' in str(raised.value)


@pytest.mark.ui
def test_nothing_is_drawn_when_the_read_refused(figure):
    ids = _idsWith(VALUES)
    for slice_ in ids.profiles_1d:
        for ion in slice_.ion:
            for leaf in VALUES:
                setattr(ion, leaf, [])
    empty = FakeAxesNode(ids, 'foo', 'foo.profiles_1d[itime].ion[j]', 'FLT_1D',
                         name='z_ion', itimeIndex=0, coordinates=('1..N',),
                         indices={'i': '0', 'j': '1'}, lengths={'i': '2', 'j': '2'})

    with pytest.raises(ValueError):
        figure.plot(empty)

    assert figure.curveCount() == 0
    assert figure.sliceControls.keys() == []
