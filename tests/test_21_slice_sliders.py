# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Every axis the plot does not draw has to be fixed in front of the user.

A curve draws one axis and an image two, so a quantity with more axes than that
has axes the read has to pin somewhere. If that place is only the index the tree
happens to carry, the plot is of one unnamed slice: nothing on screen says which
ion, which channel, which radius the numbers belong to. So the read and the
controls must come out of the same decision, and this tests that decision:

  - the controls are exactly the axes the read fixes -- no control for an axis
    the plot already draws, no fixed axis left without one;
  - each control names its axis the way the tree names it, and knows how many
    values there are to choose from;
  - moving a control moves the numbers.

The rank 3 quantity is held in memory. No reference case on this checkout holds
one with values in it (with GGD ignored, the rank 3 leaves in core_profiles and
equilibrium are empty), so the alternative is not to test it at all.
"""

import numpy as np
import pytest

from imasviz.VizDataAccess.QVizAxesSpec import QVizAxesSpec
from imasviz.VizDataAccess.QVizSlices import slicesFor
from imasviz.VizDataAccess.QVizTensorDataAccess import QVizTensorDataAccess

from support.fakes import FakeAxesNode

AOS, LEAF = 'AOS', 'LEAF'

# Two time slices, two ions each, three radial points each: profiles_1d is the
# dynamic array, ion a static one, z_ion_1d the leaf. Rank 3.
BY_SLICE_AND_ION = [[[1., 2., 3.], [10., 20., 30.]],
                    [[4., 5., 6.], [40., 50., 60.]]]


def _idsWithTwoArrays(valuesBySliceAndIon, time=(0., 1.)):
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = list(time)
    ids.profiles_1d = []
    for valuesPerIon in valuesBySliceAndIon:
        slice_ = type(str('Slice'), (), {})()
        slice_.time = None
        slice_.ion = []
        for values in valuesPerIon:
            ion = type(str('Ion'), (), {})()
            ion.z_ion_1d = values
            slice_.ion.append(ion)
        ids.profiles_1d.append(slice_)
    return ids


def _rank3Node(alongTime=True):
    """The rank 3 leaf as the tree builder leaves it: ion read at index 1."""
    return FakeAxesNode(_idsWithTwoArrays(BY_SLICE_AND_ION), 'foo',
                        'foo.profiles_1d[itime].ion[j]', 'FLT_1D',
                        name='z_ion_1d', itimeIndex=0, coordinates=('1..N',),
                        indices={'i': '0', 'j': '1'}, lengths={'i': '2', 'j': '2'},
                        alongTime=alongTime)


def test_the_axes_that_need_a_control_are_the_axes_the_plot_leaves_out():
    # The plot draws the time axis, so it needs a control for the ion array and
    # for the leaf's own axis -- and none for time, which it draws.
    axesSpec = QVizAxesSpec.fromTreeNode(_rank3Node())
    assert [axis.origin for axis in axesSpec.axes] == [AOS, AOS, LEAF]

    produced = slicesFor(axesSpec, plottedPositions=(0,))

    assert [sl.key for sl in produced] == [(AOS, 2), (LEAF, 1)]


def test_a_control_names_its_axis_the_way_the_tree_names_it():
    # 'ion' is the name the path is written with and the name the tree shows;
    # 'level 2' or 'j' would send the user to the dictionary to find out what
    # they are moving. An axis the dictionary gives no node for (the 1..N
    # spelling) is named by its rank, which is all the dictionary says.
    produced = slicesFor(QVizAxesSpec.fromTreeNode(_rank3Node()),
                         plottedPositions=(0,))

    assert [sl.label for sl in produced] == ['ion', 'dimension 1']


def test_a_control_knows_the_length_of_what_it_moves():
    # The ion array's length comes from the tree; the leaf axis has no node in
    # the dictionary, so the only length that means anything is the length of
    # the values that were read.
    produced = slicesFor(QVizAxesSpec.fromTreeNode(_rank3Node()),
                         plottedPositions=(0,),
                         lengths={(AOS, 2): 2, (LEAF, 1): 3})

    assert [sl.length for sl in produced] == [2, 3]
    # The ion index the tree carries becomes the control's starting point, so
    # the control shows where the plot actually is rather than claiming index 0.
    assert [sl.index for sl in produced] == [1, 0]


def test_the_access_asks_for_one_control_per_axis_it_fixes():
    # The same decision, taken by the object that will do the reading: if the
    # read fixes an axis the controls do not offer, the number on screen is
    # fixed by nothing the user can see.
    node = _rank3Node()

    produced = QVizTensorDataAccess(None).slicesFor(node)

    assert [(sl.key, sl.label, sl.length, sl.index) for sl in produced] == \
           [((AOS, 2), 'ion', 2, 1), ((LEAF, 1), 'dimension 1', 3, 0)]


def test_a_curve_needs_no_control_for_the_axis_it_draws():
    # A scalar inside the dynamic array: time is the only axis, the curve draws
    # it, so there is nothing left to fix and no control to show.
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
    node = FakeAxesNode(ids, 'foo', 'foo.profiles_1d[itime]', 'FLT_0D',
                        name='gap', itimeIndex=0, coordinates=(),
                        lengths={'i': '2'})

    assert QVizAxesSpec.fromTreeNode(node).rank == 1
    assert QVizTensorDataAccess(None).slicesFor(node) == []


def test_a_curve_plot_offers_a_control_for_the_leaf_axis_it_pins():
    # A 1D leaf drawn along time: one radial point per time slice, so a radial
    # index is being pinned and the user has to be able to move it. This is the
    # coordinate slider of the current widgets, arriving from the axes model
    # instead of from a flag set when the figure was created.
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0., 1.]
    ids.rho_tor = [0.1, 0.2, 0.3]
    ids.profiles_1d = []
    for values in ([1., 2., 3.], [4., 5., 6.]):
        element = type(str('Element'), (), {})()
        element.time = None
        element.density_1d = values
        ids.profiles_1d.append(element)
    node = FakeAxesNode(ids, 'foo', 'foo.profiles_1d[itime]', 'FLT_1D',
                        name='density_1d', itimeIndex=0,
                        coordinates=('foo.rho_tor',), lengths={'i': '2'})

    produced = QVizTensorDataAccess(None).slicesFor(node)

    assert [(sl.key, sl.label, sl.length) for sl in produced] == \
           [((LEAF, 1), 'rho_tor', 3)]


def test_moving_an_array_slice_moves_the_curve():
    # Ion 0, not the tree's ion 1: the points come from the other element of
    # that array. Asserted against the values, not against a call count -- the
    # control is only worth having if the read follows it.
    access = QVizTensorDataAccess(None)
    node = _rank3Node()

    atIon1 = access.GetSignal(treeNode=node, plotWidget=None)
    atIon0 = access.GetSignal(treeNode=node, plotWidget=None,
                              slices={(AOS, 2): 0})

    np.testing.assert_allclose(atIon1[1][0], [10., 40.])
    np.testing.assert_allclose(atIon0[1][0], [1., 4.])


def test_moving_a_leaf_slice_moves_the_curve_too():
    access = QVizTensorDataAccess(None)
    node = _rank3Node()

    atPoint0 = access.GetSignal(treeNode=node, plotWidget=None,
                                slices={(LEAF, 1): 0})
    atPoint2 = access.GetSignal(treeNode=node, plotWidget=None,
                                slices={(LEAF, 1): 2})

    np.testing.assert_allclose(atPoint0[1][0], [10., 40.])
    np.testing.assert_allclose(atPoint2[1][0], [30., 60.])


def test_a_slice_index_out_of_range_names_the_axis_it_is_about():
    # The index comes from a control the user moves. An IndexError about a numpy
    # axis would leave the user guessing which of the controls is wrong.
    with pytest.raises(ValueError) as raised:
        QVizTensorDataAccess(None).GetSignal(treeNode=_rank3Node(),
                                             plotWidget=None,
                                             slices={(AOS, 2): 5})

    assert 'ion' in str(raised.value)


def test_a_slice_also_applies_when_the_plot_is_one_slice_at_a_time():
    # Not along time: the plot draws the leaf's axis, so the array of structures
    # is what has to be pinned, and moving it changes which element is drawn.
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0.]
    ids.profiles_1d = []
    for values in ([1., 2., 3.], [7., 8., 9.]):
        element = type(str('Element'), (), {})()
        element.grid = type(str('Grid'), (), {})()
        element.grid.rho_tor_1d = values
        ids.profiles_1d.append(element)
    node = FakeAxesNode(ids, 'foo', 'foo.profiles_1d[i].grid', 'FLT_1D',
                        name='rho_tor_1d', itimeIndex=-1, coordinates=('1..N',),
                        indices={'i': '0'}, lengths={'i': '2'})

    access = QVizTensorDataAccess(None)
    atElement0 = access.GetSignal(treeNode=node, plotWidget=None,
                                  as_function_of_time=False, time_index=0)
    atElement1 = access.GetSignal(treeNode=node, plotWidget=None,
                                  as_function_of_time=False, time_index=0,
                                  slices={(AOS, 1): 1})

    # One row per curve, the same contract the along-time branch keeps.
    np.testing.assert_allclose(atElement0[1][0], [1., 2., 3.])
    np.testing.assert_allclose(atElement1[1][0], [7., 8., 9.])
    # The plot draws the leaf axis, so only the array of structures is a slice.
    assert [(sl.key, sl.label) for sl in
            access.slicesFor(node, as_function_of_time=False)] == [((AOS, 1), 'profiles_1d')]
