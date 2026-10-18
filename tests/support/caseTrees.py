# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Shadow trees and runtime objects of the reference case, walked once.

test_18 and test_20 read the same leaves through two different access paths, so
both need the trees and the runtime objects. Walking them costs seconds per IDS
(equilibrium alone is over four), and both paths must see the very same runtime
object: parity between two copies of a case proves less than parity between two
reads of one object.
"""

import pytest

from conftest import CASE_DATA_DICTIONARY_VERSION, case_uri_or_skip

from imasviz.VizDataAccess.QVizIDSViewParser import QVizIDSViewParser
from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource
from imasviz.VizUtils import QVizPreferences

from support.fakes import FakeTreeView


def loadCaseTrees(qapp, idsNames):
    """{idsName: (shadow tree, runtime object)} for the reference case."""
    uri = case_uri_or_skip()
    if uri is None:
        pytest.skip('reference case not reachable')

    QVizPreferences.Ignore_GGD = 1
    trees = {}
    runtime = {}
    for idsName in idsNames:
        source = QVizIMASDataSource('west 54924', uri)
        source.dd_version = CASE_DATA_DICTIONARY_VERSION
        view = FakeTreeView(uri=uri)
        parser = QVizIDSViewParser(uri, view, idsName, 0, None, False)
        parser.dataSource = source
        trees[idsName], runtime[idsName] = parser.loadIDS(idsName, 0)
    return {'uri': uri, 'trees': trees, 'runtime': runtime}


def leafByText(root, text):
    for element in root.iter():
        if element.text == text:
            return element
    raise AssertionError('no leaf %r in the shadow tree' % text)


def nodeAsTheBuilderBuildsIt(element, idsName, idsInstance, treeView):
    """The QVizTreeNode QVizDataTreeViewBuilder would put on the screen."""
    from imasviz.VizGUI.VizTreeView.QVizDataTreeViewBuilder import QVizDataTreeViewBuilder
    from imasviz.VizGUI.VizTreeView.QVizTreeNode import QVizTreeNode

    itemDataDict = {'IDSName': idsName, 'occurrence': 0, 'Tag': element.tag,
                    'isSignal': 1, 'isIDSRoot': 0, 'isSelected': 0}
    nameChild = element.find('name')
    if nameChild is not None:
        itemDataDict['dataName'] = nameChild.text
    if 'name' in element.attrib:
        itemDataDict['name'] = element.attrib['name']
    itemDataDict, extraAttributes = QVizDataTreeViewBuilder().buildNamedDataElement(
        element.text, element, itemDataDict, idsName, 0)
    node = QVizTreeNode(None, [element.tag], itemDataDict, extraAttributes)
    node.idsRef = idsInstance
    node.dataTreeView = treeView
    return node
