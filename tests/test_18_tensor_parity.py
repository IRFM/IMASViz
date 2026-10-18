# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The tensor path must read what the current path reads.

Nothing here is new behaviour: these are leaves the application plots today,
read twice -- once through QVizIMASNativeDataAccess, which builds a Python
expression out of the path and evaluates it, once through the axes model and
the structured walk. Same numbers, same coordinate values. The last test is the
exception that proves the point: a rank 3 leaf, which today silently reads as
nothing.
"""

import numpy as np
import pytest

from imasviz.VizDataAccess.QVizAxesSpec import QVizAxesSpec
from imasviz.VizDataAccess.QVizIMASNativeDataAccess import QVizIMASNativeDataAccess
from imasviz.VizDataAccess.QVizTensorExtractor import QVizTensorExtractor

from support.caseTrees import loadCaseTrees, leafByText, nodeAsTheBuilderBuildsIt
from support.fakes import FakeTreeView


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
    """The leaf through the current path and through the axes model."""
    element = leafByText(case['trees'][idsName], leafText)
    node = nodeAsTheBuilderBuildsIt(element, idsName, case['runtime'][idsName],
                                    treeView)
    axesSpec = QVizAxesSpec.fromShadowElement(element, idsName=idsName)
    tensor = QVizTensorExtractor(case['runtime'][idsName]).extract(axesSpec)
    return node, axesSpec, tensor


@pytest.mark.case
def test_a_one_dimension_leaf_outside_any_array_reads_the_same(case, treeView):
    # GetSignal1DAt evaluates 'tf.b_field_tor_vacuum_r.data' and takes the time
    # base from IDS.time because coordinate1 spells it.
    node, axesSpec, tensor = readBoth(case, treeView, 'tf',
                                      'tf.b_field_tor_vacuum_r.data')
    t, r = QVizIMASNativeDataAccess(node.getDataSource()).GetSignal1DAt(node, 0)

    assert axesSpec.rank == 1
    np.testing.assert_array_equal(r[0], tensor.values)
    np.testing.assert_allclose(t[0], tensor.axesValues[0])
    assert tensor.timeAxisPosition is None


@pytest.mark.case
def test_a_scalar_in_a_dynamic_array_reads_the_same(case, treeView):
    # equilibrium carries homogeneous_time 0: the times live under
    # time_slice[i].time, and the view still reads IDS.time. Both are the same
    # 49 values in this case, which is why the current code never noticed.
    node, axesSpec, tensor = readBoth(case, treeView, 'equilibrium',
                                      'equilibrium.time_slice[i].boundary.psi_norm')
    t, r = QVizIMASNativeDataAccess(node.getDataSource()).GetSignalVsTime(node, 0)

    assert axesSpec.rank == 1
    timeValues, values = tensor.alongTime()
    np.testing.assert_array_equal(r[0], values)
    np.testing.assert_allclose(t[0], timeValues)


@pytest.mark.case
def test_a_dynamic_array_along_time_reads_the_same(case, treeView):
    # The current path keeps one index of the leaf's own axis (coordinate_index)
    # and walks the time slices one Python expression at a time; the tensor
    # holds the whole grid, so the same curve is one column of it.
    leafText = 'core_profiles.profiles_1d[i].grid.rho_tor_norm'
    node, axesSpec, tensor = readBoth(case, treeView, 'core_profiles', leafText)
    t, r = QVizIMASNativeDataAccess(node.getDataSource()).GetSignalVsTime(node,
                                                                          0)

    assert axesSpec.rank == 2
    np.testing.assert_array_equal(r[0], tensor.values[:, 0])
    np.testing.assert_allclose(t[0], tensor.timeAxisValues())


@pytest.mark.case
def test_a_rank_three_leaf_reads_something_at_all(case, treeView):
    # Two arrays of structures plus a 1D leaf. GetSignal has no branch for it,
    # and what it does in that case was measured rather than assumed: it neither
    # raises nor returns None, it hands back two empty arrays, which the caller
    # plots as an empty curve with nothing said about why.
    node, axesSpec, tensor = readBoth(case, treeView, 'core_profiles',
                                      'core_profiles.profiles_1d[i].ion[j].z_ion_1d')

    legacy = QVizIMASNativeDataAccess(node.getDataSource()).GetSignal(node)
    assert legacy is not None
    assert legacy[0].size == 0 and legacy[1].size == 0

    assert axesSpec.rank == 3
    assert tensor.rank == 3
    assert tensor.values.shape[0] == len(case['runtime']['core_profiles'].profiles_1d)
    assert tensor.values.shape[1] > 0
    assert tensor.timeAxisPosition == 0
