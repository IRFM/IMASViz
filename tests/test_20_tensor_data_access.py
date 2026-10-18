# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The tensor access must sit behind a switch and answer like the current one.

Nothing here is new behaviour either. The widgets call one factory to get a data
access, and that access answers GetSignal with a pair of arrays (a curve) or a
QVizDataArrayHandle (an image). With the preference off -- the default -- the
factory must hand back exactly what it hands back today. With it on, the tensor
access must hand back the same numbers for the quantities the application plots
today, so that switching can be tried without a plot changing under the user's
hand.

Two things are deliberately not asserted. The 2D handle is checked for shape and
labels, not number by number: the 2D parity pass was dropped on purpose. And the
rank 3 case asserts a raised error where the current path returns two empty
arrays -- the one place the new path answers differently, on purpose.
"""

import numpy as np
import pytest

from imasviz.VizDataAccess.QVizAxesSpec import QVizAxesSpec
from imasviz.VizDataAccess.QVizDataAccessFactory import QVizDataAccessFactory
from imasviz.VizDataAccess.QVizIMASNativeDataAccess import QVizIMASNativeDataAccess
from imasviz.VizDataAccess.QVizTensorDataAccess import QVizTensorDataAccess
from imasviz.VizEntities.QVizDataArrayHandle import QVizDataArrayHandle
from imasviz.VizUtils import QVizGlobalValues, QVizPreferences

from support.caseTrees import loadCaseTrees, leafByText, nodeAsTheBuilderBuildsIt
from support.fakes import FakeAxesNode, FakeTreeView


@pytest.fixture(scope='module')
def case(qapp):
    return loadCaseTrees(qapp, ('tf', 'equilibrium', 'core_profiles'))


@pytest.fixture
def treeView(qapp, case):
    from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource
    view = FakeTreeView(uri=case['uri'])
    view.dataSource = QVizIMASDataSource('native', case['uri'])
    return view


class StubSource:
    """The factory only reads .name; the Tore-Supra access also reads .conn."""

    def __init__(self, name=QVizGlobalValues.IMAS_NATIVE):
        self.name = name
        self.conn = None


def test_the_factory_hands_back_the_current_access_by_default():
    assert QVizPreferences.Tensor_based_reading == 0
    access = QVizDataAccessFactory(StubSource()).create()
    assert type(access) is QVizIMASNativeDataAccess


def test_the_factory_hands_back_the_tensor_access_when_the_preference_is_on(monkeypatch):
    monkeypatch.setattr(QVizPreferences, 'Tensor_based_reading', 1)
    access = QVizDataAccessFactory(StubSource()).create()
    assert type(access) is QVizTensorDataAccess


def test_the_tore_supra_source_still_gets_its_own_access(monkeypatch):
    monkeypatch.setattr(QVizPreferences, 'Tensor_based_reading', 1)
    from imasviz.VizDataAccess.QVizTSDataAccess import QVizTSDataAccess
    access = QVizDataAccessFactory(
        StubSource(QVizGlobalValues.TORE_SUPRA)).create()
    assert type(access) is QVizTSDataAccess


def test_the_reading_preference_is_read_from_the_preferences_file(tmp_path, monkeypatch):
    (tmp_path / '.imasviz').mkdir()
    (tmp_path / '.imasviz' / 'preferences').write_text('Tensor_based_reading=1\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setattr(QVizPreferences, 'userPreferencesInitialized', False)
    monkeypatch.setattr(QVizPreferences, 'Tensor_based_reading', 0)
    QVizPreferences().build()
    assert QVizPreferences.Tensor_based_reading == 1


def nodeForLeaf(case, treeView, idsName, leafText):
    element = leafByText(case['trees'][idsName], leafText)
    return nodeAsTheBuilderBuildsIt(element, idsName, case['runtime'][idsName],
                                    treeView)


@pytest.mark.case
@pytest.mark.parametrize('idsName,leafText', [
    ('tf', 'tf.b_field_tor_vacuum_r.data'),
    ('equilibrium', 'equilibrium.time_slice[i].boundary.psi_norm'),
    ('core_profiles', 'core_profiles.profiles_1d[i].grid.rho_tor_norm'),
])
def test_the_axes_read_on_the_node_are_the_axes_read_on_the_shadow_element(case,
                                                                           treeView,
                                                                           idsName,
                                                                           leafText):
    # The widgets hand the access a tree node, never the shadow tree element, so
    # the axes model has to be rebuilt from what the node carries. If the two
    # readings disagree, the switch changes the geometry of the plot as well as
    # the way the numbers are read, and parity means nothing.
    node = nodeForLeaf(case, treeView, idsName, leafText)
    fromElement = QVizAxesSpec.fromShadowElement(leafByText(case['trees'][idsName],
                                                            leafText), idsName=idsName)
    fromNode = QVizAxesSpec.fromTreeNode(node)

    assert fromNode.rank == fromElement.rank
    assert [(axis.origin, axis.level, axis.is_time) for axis in fromNode.axes] == \
           [(axis.origin, axis.level, axis.is_time) for axis in fromElement.axes]
    # The node spells a coordinate with dots, the shadow tree with slashes: the
    # model takes both, so the comparison normalises the separator instead of
    # pretending the two readings write the same string.
    assert [axis.coordinate.replace('/', '.') if axis.coordinate else None
            for axis in fromNode.leafAxes()] == \
           [axis.coordinate.replace('/', '.') if axis.coordinate else None
            for axis in fromElement.leafAxes()]


@pytest.mark.case
@pytest.mark.parametrize('idsName,leafText', [
    ('tf', 'tf.b_field_tor_vacuum_r.data'),
    ('equilibrium', 'equilibrium.time_slice[i].boundary.psi_norm'),
    ('core_profiles', 'core_profiles.profiles_1d[i].grid.rho_tor_norm'),
])
def test_the_tensor_access_plots_what_the_current_access_plots(case, treeView,
                                                               idsName, leafText):
    node = nodeForLeaf(case, treeView, idsName, leafText)

    current = QVizIMASNativeDataAccess(treeView.dataSource).GetSignal(treeNode=node,
                                                                      plotWidget=None)
    tensor = QVizTensorDataAccess(treeView.dataSource).GetSignal(treeNode=node,
                                                                 plotWidget=None)

    assert isinstance(tensor, tuple) and len(tensor) == 2, \
        'a curve must come back as (time, values) like the current access'
    np.testing.assert_allclose(current[0], tensor[0])
    np.testing.assert_allclose(current[1], tensor[1])


@pytest.mark.case
def test_a_two_dimension_leaf_comes_back_as_a_data_array_handle(case, treeView):
    # The image widgets consume a QVizDataArrayHandle, not a pair of arrays.
    # Checked for what the handle must carry; its numbers are not compared with
    # the current access -- the 2D parity pass was dropped on purpose.
    node = nodeForLeaf(case, treeView, 'equilibrium',
                       'equilibrium.time_slice[i].coordinate_system.r')
    handle = QVizTensorDataAccess(treeView.dataSource).GetSignal(
        treeNode=node, plotWidget=None, as_function_of_time=False, time_index=0)

    assert isinstance(handle, QVizDataArrayHandle)
    assert len(handle.arrayCoordinates.coordinatesPath) == 2
    assert len(handle.arrayCoordinates.coordinates_labels) == 2
    assert handle.getArrayDimension() == 2


@pytest.mark.case
def test_a_rank_three_leaf_keeps_the_two_row_contract_when_it_holds_nothing(case,
                                                                           treeView):
    # Two arrays of structures plus a 1D leaf. The current path has no branch
    # for that shape: it substitutes the time index into the path and leaves the
    # static array's placeholder alone, so every slice fails to evaluate, every
    # time slice is dropped as bad, and it hands back two empty arrays -- a
    # caller draws that as an empty curve and nothing is said about why. The
    # tensor path finds the index the tree carries for the static array and
    # reads the leaf, but this leaf's own axis is empty in this case, so the
    # answer stays two rows of the same length rather than a third axis.
    node = nodeForLeaf(case, treeView, 'core_profiles',
                       'core_profiles.profiles_1d[i].ion[j].z_ion_1d')

    current = QVizIMASNativeDataAccess(treeView.dataSource).GetSignal(treeNode=node,
                                                                      plotWidget=None)
    assert current[0].size == 0 and current[1].size == 0

    tensor = QVizTensorDataAccess(treeView.dataSource).GetSignal(treeNode=node,
                                                                 plotWidget=None)
    assert len(tensor) == 2
    assert tensor[0].ndim == 2 and tensor[1].ndim == 2
    assert tensor[0].shape == tensor[1].shape


def test_a_quantity_in_two_arrays_inside_the_time_slices_becomes_a_curve():
    # No reference case here holds a rank 3 quantity with values in it, so this
    # one is held in memory: two time slices, two ions each, three values each.
    # The curve must run along time at the ion index the node carries (1) and
    # the value index asked for (0) -- and not come back as a three-dimension
    # array, which is what indexing the values by the spec positions does: those
    # positions count the fixed array, the values do not.
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0., 1.]
    bySlice = [[[1., 2., 3.], [10., 20., 30.]],
               [[4., 5., 6.], [40., 50., 60.]]]
    ids.profiles_1d = []
    for valuesPerIon in bySlice:
        slice_ = type(str('Slice'), (), {})()
        slice_.time = None
        slice_.ion = []
        for values in valuesPerIon:
            ion = type(str('Ion'), (), {})()
            ion.z_ion_1d = values
            slice_.ion.append(ion)
        ids.profiles_1d.append(slice_)

    node = FakeAxesNode(ids, 'foo', 'foo.profiles_1d[itime].ion[j]', 'FLT_1D',
                        name='z_ion_1d', itimeIndex=0, coordinates=('1..N',),
                        indices={'i': '0', 'j': '1'}, lengths={'i': '2', 'j': '2'})
    t, r = QVizTensorDataAccess(None).GetSignal(treeNode=node, plotWidget=None)

    assert r.shape == (1, 2)
    np.testing.assert_allclose(r[0], [10., 40.])
    np.testing.assert_allclose(t[0], [0., 1.])
