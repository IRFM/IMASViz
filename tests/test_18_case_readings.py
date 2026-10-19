# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""What the reference case holds, read through the axes model.

These numbers used to be a comparison: each leaf was read twice, once through the
reader that built a Python expression out of its path and evaluated it, once
through the axes model, and the two had to agree. The expression reader is gone,
so the numbers are frozen here instead -- they were measured while both readers
were still side by side, and they are what the application draws on this case
today.

The counts and endpoints are worth freezing on their own terms, not only as
measurements: 49 time slices is what WEST kept for this shot, a normalised
poloidal flux of exactly 1 is the definition of the magnetic boundary, and a
normalised toroidal flux of 0 on axis is where the profile grid starts. A number
that is also a physical invariant is a expectation a future reader can judge.
"""

import numpy as np
import pytest

from imasviz.VizDataAccess.QVizAxesSpec import QVizAxesSpec
from imasviz.VizDataAccess.QVizTensorDataAccess import QVizTensorDataAccess
from imasviz.VizDataAccess.QVizTensorExtractor import QVizTensorExtractor

from support.caseTrees import loadCaseTrees, leafByText, nodeAsTheBuilderBuildsIt
from support.fakes import FakeTreeView

# tf.b_field_tor_vacuum_r.data: one value per shot sample, no array around it.
TF_SAMPLES = 17344
TF_TIME_FIRST = 1.83577299118042
TF_TIME_LAST = 74.6867446899414
TF_FIELD_FIRST = -9.109991073608398
TF_FIELD_LAST = -9.109155654907227
TF_FIELD_LOW = -9.111328125
TF_FIELD_HIGH = -9.105144500732422

# equilibrium.time_slice[i].boundary.psi_norm: one value per time slice.
EQ_SLICES = 49
EQ_TIME_FIRST = 32.1336784362793
EQ_TIME_LAST = 48.54828643798828

# core_profiles.profiles_1d[i].grid.rho_tor_norm: slices by grid points.
CP_SLICES = 1642
CP_GRID_POINTS = 101
CP_TIME_FIRST = 32.1336784362793
CP_TIME_LAST = 48.54367843627929


@pytest.fixture(scope='module')
def case(qapp):
    """The shadow trees and the runtime objects, walked once for all tests."""
    return loadCaseTrees(qapp, ('tf', 'equilibrium', 'core_profiles'))


@pytest.fixture
def treeView(qapp, case):
    from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource
    view = FakeTreeView(uri=case['uri'])
    view.dataSource = QVizIMASDataSource('native', case['uri'])
    return view


def readBoth(case, treeView, idsName, leafText):
    """The leaf as the builder presents it, and as the axes model sees it."""
    element = leafByText(case['trees'][idsName], leafText)
    node = nodeAsTheBuilderBuildsIt(element, idsName, case['runtime'][idsName],
                                    treeView)
    axesSpec = QVizAxesSpec.fromShadowElement(element, idsName=idsName)
    tensor = QVizTensorExtractor(case['runtime'][idsName]).extract(axesSpec)
    return node, axesSpec, tensor


def curve(treeView, node, **options):
    """The pair of arrays a plot frame would be handed."""
    signal = QVizTensorDataAccess(treeView.dataSource).GetSignal(
        treeNode=node, plotWidget=None, **options)
    assert isinstance(signal, tuple) and len(signal) == 2, \
        'a curve comes back as (abscissa, values): every frame indexes [0] and [1]'
    return signal


@pytest.mark.case
def test_a_one_dimension_leaf_outside_any_array(case, treeView):
    # The magnetic field of the vessel: 17 344 samples over the shot, sitting at
    # IDS level with nothing enclosing them. Its coordinate spells time, so the
    # read takes IDS.time and no axis is left fixed -- which is why
    # timeAxisPosition is None rather than 0.
    node, axesSpec, tensor = readBoth(case, treeView, 'tf',
                                      'tf.b_field_tor_vacuum_r.data')

    assert axesSpec.rank == 1
    assert tensor.values.shape == (TF_SAMPLES,)
    assert tensor.timeAxisPosition is None
    np.testing.assert_allclose(tensor.axesValues[0][0], TF_TIME_FIRST)
    np.testing.assert_allclose(tensor.axesValues[0][-1], TF_TIME_LAST)
    np.testing.assert_allclose(tensor.values[0], TF_FIELD_FIRST)
    np.testing.assert_allclose(tensor.values[-1], TF_FIELD_LAST)
    # The field is held steady through the shot at about -9.11 T: a read that
    # mixed two quantities or shifted by a slice would leave this band.
    assert TF_FIELD_LOW <= tensor.values.min()
    assert tensor.values.max() <= TF_FIELD_HIGH

    x, y = curve(treeView, node)
    assert x.shape == y.shape == (1, TF_SAMPLES)
    np.testing.assert_allclose(x[0][0], TF_TIME_FIRST)
    np.testing.assert_allclose(y[0][-1], TF_FIELD_LAST)


@pytest.mark.case
def test_a_scalar_in_a_dynamic_array(case, treeView):
    # equilibrium carries homogeneous_time 0, so the times of a slice live under
    # time_slice[i].time -- and are the same 49 values as IDS.time here, which is
    # why reading the wrong one never showed up. psi_norm is normalised by the
    # boundary itself: it is 1 on the magnetic boundary, by definition.
    node, axesSpec, tensor = readBoth(case, treeView, 'equilibrium',
                                      'equilibrium.time_slice[i].boundary.psi_norm')

    assert axesSpec.rank == 1
    x, y = curve(treeView, node)

    assert x.shape == y.shape == (1, EQ_SLICES)
    np.testing.assert_allclose(x[0][0], EQ_TIME_FIRST)
    np.testing.assert_allclose(x[0][-1], EQ_TIME_LAST)
    np.testing.assert_allclose(y[0], np.ones(EQ_SLICES))


@pytest.mark.case
def test_a_dynamic_array_along_time(case, treeView):
    # The profile grid: 1 642 time slices by 101 grid points. A curve along time
    # keeps one grid point -- the read takes the index the tree carries -- so the
    # column comes back at the slice count, and the first point of a normalised
    # toroidal flux grid is 0 on axis.
    node, axesSpec, tensor = readBoth(case, treeView, 'core_profiles',
                                      'core_profiles.profiles_1d[i].grid.rho_tor_norm')

    assert axesSpec.rank == 2
    assert tensor.values.shape == (CP_SLICES, CP_GRID_POINTS)
    np.testing.assert_allclose(tensor.timeAxisValues()[0], CP_TIME_FIRST)
    np.testing.assert_allclose(tensor.timeAxisValues()[-1], CP_TIME_LAST)
    np.testing.assert_allclose(tensor.values[:, 0], np.zeros(CP_SLICES))

    x, y = curve(treeView, node)
    assert x.shape == y.shape == (1, CP_SLICES)
    np.testing.assert_allclose(y[0], np.zeros(CP_SLICES))


@pytest.mark.case
def test_a_rank_three_leaf_is_read_at_all(case, treeView):
    # Two arrays of structures and a 1D leaf. The expression reader had no branch
    # for that shape: it substituted the time index, left the static array's
    # placeholder alone, watched every slice fail to evaluate, and handed back two
    # empty arrays -- an empty curve with nothing said about why. This read finds
    # the index the tree carries for the static array and reaches the leaf.
    #
    # The leaf's own axis is empty in this case, which is what the shape says: 1
    # ion in the first slice, 0 values on its axis. The point is that the axis is
    # now seen as an axis, with a length the read can answer for, instead of
    # being discarded on the way to an empty array.
    node, axesSpec, tensor = readBoth(case, treeView, 'core_profiles',
                                      'core_profiles.profiles_1d[i].ion[j].z_ion_1d')

    assert axesSpec.rank == 3
    assert tensor.values.shape == (CP_SLICES, 1, 0)
    assert tensor.timeAxisPosition == 0

    x, y = curve(treeView, node)
    assert x.shape == y.shape == (1, 0)
