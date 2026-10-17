# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The reflection based view parser, which replaced the generated IDS parsers.

The pure helpers need no data. The tree walk runs against the reference case and
pins the node counts measured on the generated parser of the same data
dictionary (IDSDef 3.35.0), so a regression in the walk shows up as a count or
an attribute change.
"""

import pytest

from conftest import CASE_DATA_DICTIONARY_VERSION, case_uri_or_skip

from imasviz.VizDataAccess.QVizIDSViewParser import (cleanDocumentation,
                                                     dataTypeName,
                                                     itimeIndexFromPathDoc)

from support.fakes import FakeTreeView

# (IDS, Ignore_GGD, shadow tree node count) measured on the generated parser.
LEGACY_NODE_COUNTS = [('tf', 0, 77),
                      ('pulse_schedule', 0, 7196),
                      ('equilibrium', 1, 7203)]


def countNodes(element):
    return 1 + sum(countNodes(child) for child in list(element))


class _MetaDataStub:
    """Stands in for IDSMetadata where only the type spelling matters."""

    def __init__(self, value, ndim):
        self.data_type = type('EnumValue', (), {'value': value})()
        self.ndim = ndim


def test_itime_index_is_minus_one_without_a_time_placeholder():
    assert itimeIndexFromPathDoc('equilibrium.time') == -1
    assert itimeIndexFromPathDoc('') == -1


def test_itime_index_counts_the_enclosing_struct_arrays():
    # Real path_doc spellings from the data dictionary: the marker is always the
    # literal (itime), and the enclosing levels are written (i1), (i2), ...
    assert itimeIndexFromPathDoc('frame(itime)/time') == 0
    assert itimeIndexFromPathDoc('change(i1)/profiles_1d(itime)') == 1
    assert itimeIndexFromPathDoc('channel(i1)/detector(i2)/frame(itime)') == 2


def test_itime_index_stops_at_the_first_missing_level():
    # Synthetic on purpose: real dictionaries keep the levels contiguous, but
    # the generated parsers stopped counting at the first missing (iN) and the
    # walk downstream relies on that, so the behaviour is pinned here.
    assert itimeIndexFromPathDoc('a(i1)(i3)/frame(itime)') == 1


def test_data_type_restores_the_dictionary_spelling():
    assert dataTypeName(_MetaDataStub('structure', 0)) == 'structure'
    assert dataTypeName(_MetaDataStub('struct_array', 1)) == 'struct_array'
    assert dataTypeName(_MetaDataStub('FLT', 1)) == 'FLT_1D'
    assert dataTypeName(_MetaDataStub('INT', 0)) == 'INT_0D'


def test_documentation_becomes_one_line_with_real_quotes():
    cleaned = cleanDocumentation('a\nb  &#34;x&#34;')
    assert '\n' not in cleaned
    assert '"x"' in cleaned


@pytest.fixture
def dataSource():
    uri = case_uri_or_skip()
    if uri is None:
        pytest.skip('reference case not reachable')
    from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource
    source = QVizIMASDataSource('west 54924', uri)
    # The case was written with this dictionary; the harness runs against
    # another one, so the entry has to be pinned or the AL refuses to read it.
    source.dd_version = CASE_DATA_DICTIONARY_VERSION
    return source


@pytest.mark.case
@pytest.mark.parametrize('idsName,ignoreGGD,expectedNodes', LEGACY_NODE_COUNTS)
def test_the_shadow_tree_keeps_the_generated_shape(dataSource, qapp,
                                                   idsName, ignoreGGD,
                                                   expectedNodes):
    from imasviz.VizDataAccess.QVizIDSViewParser import QVizIDSViewParser
    from imasviz.VizUtils import QVizPreferences

    QVizPreferences.Ignore_GGD = ignoreGGD

    view = FakeTreeView(uri=dataSource.uri)
    parser = QVizIDSViewParser(dataSource.uri, view, idsName, 0, None, False)
    parser.dataSource = dataSource
    root, _ = parser.loadIDS(idsName, 0)

    assert countNodes(root) == expectedNodes


@pytest.mark.case
def test_every_element_carries_its_data_path_as_text(dataSource, qapp):
    # QVizDataTreeViewBuilder names every tree item as tag + '=' + text
    # (:142-148 for 0D, :155-160 for the others). Without the accumulated path
    # the whole shot view loses that suffix.
    from imasviz.VizDataAccess.QVizIDSViewParser import QVizIDSViewParser
    from imasviz.VizUtils import QVizPreferences

    QVizPreferences.Ignore_GGD = 1
    view = FakeTreeView(uri=dataSource.uri)
    parser = QVizIDSViewParser(dataSource.uri, view, 'tf', 0, None, False)
    parser.dataSource = dataSource
    root, _ = parser.loadIDS('tf', 0)

    elements = list(root.iter())

    # Only the IDS root carries no path: the generated parsers seeded the
    # accumulation with the IDS name and wrote it onto the children.
    assert [element for element in elements if not element.text] == [root]

    for element in elements:
        if element is root or element.tag == 'name':
            continue
        assert element.text.startswith('tf.'), (element.tag, element.text)


@pytest.mark.case
def test_the_dictionary_is_descended_once_per_coordinate(dataSource, qapp):
    # Every element of an array of structures repeats the same coordinate
    # spelling, so resolving it through the dictionary has to be paid once per
    # spelling and not once per node. Measured before any caching, on this very
    # tree: 305 descents for 10 distinct coordinates, and 84 708 for 16 when the
    # GGD structures are kept. The bound stays far below the node count, so it
    # fails if the walk ever goes back to descending per node.
    from imasviz.VizDataAccess.QVizIDSViewParser import QVizIDSViewParser
    from imasviz.VizUtils import QVizPreferences

    QVizPreferences.Ignore_GGD = 1
    view = FakeTreeView(uri=dataSource.uri)
    parser = QVizIDSViewParser(dataSource.uri, view, 'equilibrium', 0, None, False)
    parser.dataSource = dataSource
    root, _ = parser.loadIDS('equilibrium', 0)

    assert countNodes(root) == 7203
    assert parser.metadataDescents <= 64, parser.metadataDescents


@pytest.mark.case
def test_an_array_of_structures_keeps_the_loop_placeholder(dataSource, qapp):
    # The generated parsers wrote the unsubstituted loop variable into the path
    # ('tf.coil[i]', not 'tf.coil[0]'), leaving the view to substitute it per
    # element. tf holds no populated array of structures in this case, so
    # equilibrium is used here.
    from imasviz.VizDataAccess.QVizIDSViewParser import QVizIDSViewParser
    from imasviz.VizUtils import QVizPreferences

    QVizPreferences.Ignore_GGD = 1
    view = FakeTreeView(uri=dataSource.uri)
    parser = QVizIDSViewParser(dataSource.uri, view, 'equilibrium', 0, None, False)
    parser.dataSource = dataSource
    root, _ = parser.loadIDS('equilibrium', 0)

    arrayElements = [element for element in root.iter()
                     if element.attrib.get('index') is not None]
    assert arrayElements, 'equilibrium is expected to hold arrays of structures'
    for element in arrayElements:
        assert element.text.endswith(']'), (element.tag, element.text)
        assert element.tag + '[' in element.text
