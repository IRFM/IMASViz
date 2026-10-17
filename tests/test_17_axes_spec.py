# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The axes a leaf has to be plotted along.

What a plot can do with a quantity depends on how many dimensions it carries,
and that count is not the data dictionary type: an array of structures adds a
dimension of its own. The shadow tree already records every ingredient
(aos_parents_count, the loop placeholders in parametrizedPath, coordinateN), so
the axes of a leaf are a read of the tree -- no case open, no data read.
"""

import xml.etree.ElementTree as ET

import pytest

from conftest import CASE_DATA_DICTIONARY_VERSION, case_uri_or_skip

from imasviz.VizDataAccess.QVizAxesSpec import (QVizAxesSpec, QVizAxis,
                                                leafRank)

from support.fakes import FakeTreeView


def leaf(dataType, parametrizedPath, aosParents=0, itimeIndex=-1,
         coordinates=(), units=None, coordinateUnits=None, text='x.y'):
    """A shadow tree leaf as QVizIDSViewParser.buildLeaf leaves it."""
    element = ET.Element('name')
    element.text = text
    element.set('data_type', dataType)
    element.set('aos_parents_count', str(aosParents))
    element.set('parametrizedPath', parametrizedPath)
    element.set('itime_index', str(itimeIndex))
    if units is not None:
        element.set('units', units)
    for index, coordinate in enumerate(coordinates):
        element.set('coordinate' + str(index + 1), coordinate)
        if coordinateUnits and coordinateUnits[index]:
            element.set('coordinate' + str(index + 1) + '_units',
                        coordinateUnits[index])
    for level in range(1, aosParents + 1):
        element.set(QVizGlobalIndices[level], str(0))
        element.set(QVizGlobalMaxIndices[level], str(7))
    return element


# Spelled out rather than imported so the test states the convention: the walk
# numbers its loop variables i, j, k, ... and their extents N, M, K, ...
QVizGlobalIndices = {1: 'i', 2: 'j', 3: 'k', 4: 'l', 5: 'q', 6: 'r', 7: 't'}
QVizGlobalMaxIndices = {1: 'N', 2: 'M', 3: 'K', 4: 'L', 5: 'Q', 6: 'R', 7: 'T'}


def spec(**kwargs):
    return QVizAxesSpec.fromShadowElement(leaf(**kwargs), idsName='equilibrium')


def test_a_scalar_outside_any_array_of_structures_has_nothing_to_plot():
    axesSpec = spec(dataType='FLT_0D', parametrizedPath='equilibrium')
    assert axesSpec.rank == 0
    assert not axesSpec.isPlottable()


def test_a_scalar_inside_a_dynamic_array_of_structures_is_a_curve():
    # This is the case the view calls "0D and dynamic": as a tensor it is rank
    # 1, and its single axis is the time of the enclosing array.
    axesSpec = spec(dataType='FLT_0D', parametrizedPath='equilibrium.time_slice[itime]',
                    aosParents=1, itimeIndex=0, text='equilibrium.time_slice[itime].gamma_web')
    assert axesSpec.rank == 1
    assert axesSpec.isPlottable()
    axis, = axesSpec.axes
    assert axis.origin == QVizAxis.AOS
    assert axis.is_time
    assert axis.coordinate == 'equilibrium.time'
    assert axis.units == 's'
    assert axis.length == 7


def test_a_one_dimension_leaf_adds_its_own_axis_to_the_array_axis():
    axesSpec = spec(dataType='FLT_1D', coordinates=['bpol_probe(i1).non_linear_response.b_field_linear'],
                    parametrizedPath='magnetics.bpol_probe[i]', aosParents=1,
                    coordinateUnits=['T'],
                    text='magnetics.bpol_probe[i].non_linear_response.b_field_non_linear')

    assert axesSpec.rank == 2
    aosAxis, leafAxis = axesSpec.axes
    assert (aosAxis.origin, aosAxis.is_time) == (QVizAxis.AOS, False)
    assert (leafAxis.origin, leafAxis.coordinate, leafAxis.units) == \
        (QVizAxis.LEAF, 'bpol_probe(i1).non_linear_response.b_field_linear', 'T')


def test_an_unbounded_coordinate_still_describes_an_axis():
    # 1..N names no node in the dictionary, but it is a dimension to draw: the
    # ranks are the axis, no coordinate values exist for it.
    axesSpec = spec(dataType='FLT_2D',
                    coordinates=['1..N', 'time_slice[0].profiles_1d.grid'],
                    parametrizedPath='equilibrium.time_slice[itime]',
                    aosParents=1, itimeIndex=0,
                    text='equilibrium.time_slice[itime].profiles_1d.psi')

    assert axesSpec.rank == 3
    unbounded = axesSpec.leafAxes()[0]
    assert unbounded.coordinate is None
    assert unbounded.isUnbounded()


def test_a_coordinate_naming_a_time_base_is_flagged_as_time():
    for spelling in ('time', 'time_slice[0].time', 'time_slice/time'):
        axesSpec = spec(dataType='FLT_1D', coordinates=[spelling],
                        parametrizedPath='tf.b_field_tor_vacuum_r',
                        text='tf.b_field_tor_vacuum_r.data')
        assert axesSpec.timeAxes(), spelling


@pytest.mark.parametrize('dataType,aosParents,expected', [
    ('FLT_0D', 0, 0),
    ('STR_0D', 1, 1),
    ('FLT_1D', 2, 3),
    ('CPX_2D', 2, 4),
    ('FLT_6D', 1, 7),
    ('structure', 3, None),
    ('struct_array', 3, None),
])
def test_the_rank_counts_arrays_of_structures_and_the_leaf_type(dataType,
                                                                aosParents,
                                                                expected):
    element = leaf(dataType=dataType, parametrizedPath='a.b', aosParents=aosParents)
    assert leafRank(element) == expected


def walk(dataSource, idsName, ignoreGGD=1):
    from imasviz.VizDataAccess.QVizIDSViewParser import QVizIDSViewParser
    from imasviz.VizUtils import QVizPreferences

    QVizPreferences.Ignore_GGD = ignoreGGD
    view = FakeTreeView(uri=dataSource.uri)
    parser = QVizIDSViewParser(dataSource.uri, view, idsName, 0, None, False)
    parser.dataSource = dataSource
    root, _ = parser.loadIDS(idsName, 0)
    return root


def leafByText(root, text):
    for element in root.iter():
        if element.text == text:
            return element
    raise AssertionError('no leaf %r in the shadow tree' % text)


@pytest.fixture(scope='module')
def shadowTrees(qapp):
    """The trees the rank assertions read, walked once for the whole module."""
    uri = case_uri_or_skip()
    if uri is None:
        pytest.skip('reference case not reachable')
    from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory

    roots = {}
    for idsName in ('tf', 'equilibrium', 'calorimetry', 'core_profiles'):
        source = QVizDataSourceFactory().create(uri)
        source.dd_version = CASE_DATA_DICTIONARY_VERSION
        roots[idsName] = walk(source, idsName)
    return roots


@pytest.mark.case
def test_the_rank_of_real_leaves_matches_the_census(shadowTrees):
    # The four spellings below are the examples TESTING.md section 7 records for
    # ranks 1, 2, 3, 4 and 5. They are what the new path has to plot one day.
    expected = [
        ('tf', 'tf.b_field_tor_vacuum_r.data', 1),
        ('calorimetry', 'calorimetry.group[i].component[j].power.data', 3),
        ('core_profiles', 'core_profiles.profiles_1d[i].ion[j].state[k].z_average_1d', 4),
        ('equilibrium', 'equilibrium.time_slice[i].coordinate_system.tensor_covariant', 5),
    ]
    for idsName, text, rank in expected:
        element = leafByText(shadowTrees[idsName], text)
        axesSpec = QVizAxesSpec.fromShadowElement(element, idsName=idsName)
        assert axesSpec.rank == rank, (text, axesSpec.axes)


@pytest.mark.case
def test_the_dynamic_array_of_structures_gives_its_time_axis(shadowTrees):
    element = leafByText(shadowTrees['equilibrium'],
                         'equilibrium.time_slice[i].coordinate_system.tensor_covariant')
    axesSpec = QVizAxesSpec.fromShadowElement(element, idsName='equilibrium')

    timeAxes = axesSpec.timeAxes()
    assert len(timeAxes) == 1, axesSpec.axes
    assert timeAxes[0].origin == QVizAxis.AOS
    assert timeAxes[0].coordinate == 'equilibrium.time'
    # One array of structures plus a 4D leaf.
    assert axesSpec.rank == 5


@pytest.mark.case
def test_the_rank_distribution_of_a_whole_ids_is_pinned(shadowTrees):
    # Counted before the axes model existed, over the same walk with GGD pruned.
    # If a change to the parser or to this model moves one of those numbers, one
    # of the two is wrong.
    from collections import Counter

    counts = Counter()
    for element in shadowTrees['equilibrium'].iter():
        rank = leafRank(element)
        if rank is not None:
            counts[rank] += 1

    assert dict(sorted(counts.items())) == {0: 18, 1: 424, 2: 3022, 3: 48, 5: 6}
