# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The unit of the coordinate an array is indexed by, up to the X axis label.

The view builds an X axis label out of the coordinate path, but the unit of that
coordinate never left the shadow tree: every axis that is not time was left bare,
while the seconds of a time axis were hardcoded in the label text.
"""

import pytest

from conftest import CASE_DATA_DICTIONARY_VERSION, case_uri_or_skip

from imasviz.VizGUI.VizTreeView.QVizDataTreeViewBuilder import QVizDataTreeViewBuilder
from imasviz.VizGUI.VizTreeView.QVizTreeNode import QVizTreeNode

from support.fakes import FakeTreeView

PATH_URI = 'imas:hdf5?path=/afs/eufus.eu/g2itmdev/user/g2lfleur/public/imasdb/west/3/54924/0'

# A 1D signal indexed by another 1D signal: IDSDef 3.35.0 gives that X
# coordinate ('b_field_linear') the unit 'T', and the array is not time based,
# so the view does plot it along coordinate 1.
IDS = 'magnetics'
LEAF = 'magnetics.bpol_probe[i].non_linear_response.b_field_non_linear'
X_COORDINATE = 'bpol_probe(i1).non_linear_response.b_field_linear'
X_UNITS = 'T'


@pytest.fixture
def dataSource(qapp):
    uri = case_uri_or_skip()
    if uri is None:
        pytest.skip('reference case not reachable')
    from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource
    source = QVizIMASDataSource('west 54924', uri)
    # The case was written with this dictionary; the harness runs against
    # another one, so the entry has to be pinned or the AL refuses to read it.
    source.dd_version = CASE_DATA_DICTIONARY_VERSION
    return source


@pytest.fixture
def treeView(qapp):
    """A tree view only standing in for the one attribute plotOptions reads."""
    from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource
    view = FakeTreeView(uri=PATH_URI)
    view.dataSource = QVizIMASDataSource('native', PATH_URI)
    return view


def parsedElement(dataSource, idsName, elementText):
    from imasviz.VizDataAccess.QVizIDSViewParser import QVizIDSViewParser
    from imasviz.VizUtils import QVizPreferences

    QVizPreferences.Ignore_GGD = 1
    view = FakeTreeView(uri=dataSource.uri)
    parser = QVizIDSViewParser(dataSource.uri, view, idsName, 0, None, False)
    parser.dataSource = dataSource
    root, _ = parser.loadIDS(idsName, 0)
    for element in root.iter():
        if element.text == elementText:
            return element
    raise AssertionError('no element %r in the %s shadow tree' % (elementText, idsName))


def nodeAsTheBuilderBuildsIt(element, idsName):
    """The pair QVizDataTreeViewBuilder.addNewNode hands to QVizTreeNode."""
    itemDataDict = {'IDSName': idsName, 'occurrence': 0, 'Tag': element.tag,
                    'isSignal': 0, 'isIDSRoot': 0, 'isSelected': 0}
    # What addNewNode (:48-63) puts in before calling buildNamedDataElement.
    nameChild = element.find('name')
    if nameChild is not None:
        itemDataDict['dataName'] = nameChild.text
    if 'name' in element.attrib:
        itemDataDict['name'] = element.attrib['name']
    itemDataDict, extraAttributes = QVizDataTreeViewBuilder().buildNamedDataElement(
        element.text, element, itemDataDict, idsName, 0)
    return QVizTreeNode(None, [element.tag], itemDataDict, extraAttributes)


def makeLeaf(coordinates, coordinateUnits, timeDependent=False, **overrides):
    """A 1D leaf shaped as the builder leaves it, without the tree around it."""
    infoDict = {'IDSName': IDS, 'occurrence': 0, 'name': 'b_field_non_linear',
                'dataName': LEAF, 'data_type': 'FLT_1D', 'units': 'T',
                'isSignal': 1, 'isStatic': 0, 'homogeneous_time': 1,
                'coordinate1': coordinates[0]}
    if coordinateUnits is not None:
        infoDict['coordinate1_units'] = coordinateUnits
    infoDict.update(overrides)
    node = QVizTreeNode(None, ['b_field_non_linear'], infoDict)
    node.parametrizedPath = 'magnetics.bpol_probe[i1].non_linear_response'
    node.coordinates = list(coordinates)
    node.aos_parents_count = 0
    node.coordinates_explicitly_time_dependent = {1: 1 if timeDependent else 0}
    return node


@pytest.mark.case
def test_the_coordinate_unit_reaches_the_tree_node(dataSource):
    # The parser puts it on the shadow tree element; the view has to carry it
    # over, otherwise nothing downstream can show it.
    element = parsedElement(dataSource, IDS, LEAF)
    assert element.get('coordinate1_units') == X_UNITS

    node = nodeAsTheBuilderBuildsIt(element, IDS)
    assert node.getCoordinateUnits(1) == X_UNITS


@pytest.mark.case
def test_a_coordinate_axis_label_carries_the_unit_of_the_coordinate(dataSource,
                                                                   treeView):
    node = nodeAsTheBuilderBuildsIt(parsedElement(dataSource, IDS, LEAF), IDS)
    label, xlabel, ylabel, title = node.plotOptions(treeView, title='')

    assert xlabel.endswith('[' + X_UNITS + ']'), xlabel
    # The Y unit was already shown, glued into the label text: it must stay put
    # instead of being printed twice.
    assert ylabel == 'b_field_non_linear[T]', ylabel
    assert xlabel.count('[' + X_UNITS + ']') == 1


def test_a_time_axis_still_shows_seconds(treeView):
    node = makeLeaf(['bpol_probe(i1).non_linear_response.b_field_linear.time'],
                    's', timeDependent=True)
    label, xlabel, ylabel, title = node.plotOptions(treeView, title='')

    assert xlabel == 'time[s]', xlabel


def test_a_time_based_coordinate_keeps_its_seconds(treeView):
    # Here the coordinate itself names the time base, so its own unit and the
    # hardcoded seconds agree; the label is the full path to it.
    node = makeLeaf(['b_field_tor_vacuum_r.time'], 's', timeDependent=True,
                    homogeneous_time=0)
    label, xlabel, ylabel, title = node.plotOptions(treeView, title='')

    assert xlabel.endswith('.time[s]'), xlabel


def test_an_unbounded_coordinate_gets_no_unit(treeView):
    node = makeLeaf(['1..N'], None)
    label, xlabel, ylabel, title = node.plotOptions(treeView, title='')

    assert xlabel == '1..N', xlabel


def test_a_coordinate_without_a_unit_gets_no_brackets(treeView):
    node = makeLeaf([X_COORDINATE], None)
    label, xlabel, ylabel, title = node.plotOptions(treeView, title='')

    assert not xlabel.endswith('[]'), xlabel
    assert '[' not in xlabel.split('.')[-1], xlabel


def test_a_caller_supplied_label_is_left_alone(treeView):
    # The unit belongs to the label the view generated itself. A label given by
    # the caller (a plot configuration, a plugin) is not ours to annotate.
    node = makeLeaf([X_COORDINATE], X_UNITS)
    label, xlabel, ylabel, title = node.plotOptions(treeView, title='',
                                                    xlabel='my own abscissa')

    assert xlabel == 'my own abscissa', xlabel


def test_the_labels_helper_agrees_with_plotOptions(treeView):
    # QVizIMASNativeDataAccess.py:147 builds the axis text of table and stacked
    # plots through labels(), which duplicated the same hardcoded seconds.
    node = makeLeaf([X_COORDINATE], X_UNITS)
    # labels() takes no dataTreeView argument: it walks up to getDataTreeView().
    node.dataTreeView = treeView
    quantityName, label, xlabel = node.labels(None, 1, 0, 0)

    assert xlabel.endswith('[' + X_UNITS + ']'), xlabel
