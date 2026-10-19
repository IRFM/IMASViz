# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""One reader for the IMAS sources, and the shape it answers with.

The widgets call one factory to get a data access, and that access answers
GetSignal with a pair of arrays (a curve) or a QVizDataArrayHandle (an image).
Which of the two a node gets follows from its axes, so what is pinned here is the
contract the frames index -- [0] and [1], or the handle a frame can lay out -- and
not the numbers: those are frozen for these same leaves in
test_18_case_readings.py, where they stand on their own rather than beside
another reader.

The axes model is checked from both sides too, since the frames hand the read a
tree node while the parser walks a shadow element: if the two disagree about the
rank or the coordinates, the shape asserted here would be the shape of a
different quantity than the one on screen.

Two things are deliberately not asserted. The 2D handle is checked for shape and
labels, not number by number. And the rank 3 case asserts the two rows a frame
indexes even when the case leaves them empty -- what matters is that the read
reaches the leaf instead of discarding it.
"""

import numpy as np
import pytest

from imasviz.VizDataAccess.QVizAxesSpec import QVizAxesSpec
from imasviz.VizDataAccess.QVizDataAccessFactory import QVizDataAccessFactory
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


def test_the_factory_hands_back_the_tensor_access_for_an_imas_source():
    # One reader for both IMAS sources: the switch that used to choose between
    # two is gone, so nothing here can ask for the old one.
    access = QVizDataAccessFactory(StubSource()).create()
    assert type(access) is QVizTensorDataAccess


def test_a_remote_imas_source_reads_the_same_way_as_a_local_one():
    access = QVizDataAccessFactory(
        StubSource(QVizGlobalValues.IMAS_UDA)).create()
    assert type(access) is QVizTensorDataAccess


def test_the_tore_supra_source_still_gets_its_own_access():
    from imasviz.VizDataAccess.QVizTSDataAccess import QVizTSDataAccess
    access = QVizDataAccessFactory(
        StubSource(QVizGlobalValues.TORE_SUPRA)).create()
    assert type(access) is QVizTSDataAccess


def test_a_preferences_file_naming_the_retired_reading_key_is_still_read(tmp_path,
                                                                        monkeypatch):
    # Files already on disk carry the key the switch used to read. Its reader is
    # gone, so the line has to be passed over without a word -- and the options
    # that remain have to keep being read.
    (tmp_path / '.imasviz').mkdir()
    (tmp_path / '.imasviz' / 'preferences').write_text(
        'Tensor_based_reading=1\nIgnore_GGD=0\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setattr(QVizPreferences, 'userPreferencesInitialized', False)
    monkeypatch.setattr(QVizPreferences, 'Ignore_GGD', 1)
    QVizPreferences().build()
    assert QVizPreferences.Ignore_GGD == 0


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
def test_a_curve_comes_back_as_two_rows_of_one_length(case, treeView,
                                                      idsName, leafText):
    # What a frame needs, rather than what a second reader used to answer: [0] is
    # the abscissa and [1] the values, each one row per quantity drawn. The
    # numbers themselves are frozen in test_18_case_readings.py, where they stand
    # on their own instead of being checked against another reader.
    node = nodeForLeaf(case, treeView, idsName, leafText)
    signal = QVizTensorDataAccess(treeView.dataSource).GetSignal(
        treeNode=node, plotWidget=None)

    assert isinstance(signal, tuple) and len(signal) == 2, \
        'a curve comes back as (abscissa, values)'
    assert signal[0].ndim == 2 and signal[1].ndim == 2
    assert signal[0].shape == signal[1].shape


@pytest.mark.case
def test_a_two_dimension_leaf_comes_back_as_a_data_array_handle(case, treeView):
    # The image widgets consume a QVizDataArrayHandle, not a pair of arrays: the
    # two kinds of answer are told apart by type, so a curve shape on a 2D leaf
    # would reach a frame that cannot read it.
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
    # Two arrays of structures plus a 1D leaf: the read finds the index the tree
    # carries for the static array and reaches the leaf, but this leaf's own axis
    # is empty in this case. The answer therefore stays two rows of one length
    # instead of growing a third axis -- which is the shape a frame indexing [0]
    # and [1] can still draw, empty as it is.
    node = nodeForLeaf(case, treeView, 'core_profiles',
                       'core_profiles.profiles_1d[i].ion[j].z_ion_1d')

    signal = QVizTensorDataAccess(treeView.dataSource).GetSignal(
        treeNode=node, plotWidget=None)
    assert len(signal) == 2
    assert signal[0].ndim == 2 and signal[1].ndim == 2
    assert signal[0].shape == signal[1].shape


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
