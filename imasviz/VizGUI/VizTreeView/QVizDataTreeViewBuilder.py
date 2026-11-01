# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import logging
import re
from threading import Thread, Condition
from imasviz.VizGUI.VizTreeView.QVizTreeNode import QVizTreeNode
from imasviz.VizUtils import QVizGlobalValues, QVizPreferences
from imasviz.VizDataAccess.QVizNodePlotting import QVizNodePlotting

class QVizDataTreeViewBuilder:
    # The index an array of structures leaves in a path: the letter the walk
    # parametrizes with, or the concrete element number.
    INDEXED = re.compile(r'\[[^\]]*\]|\(\d+\)')

    def __init__(self, showOnlyTensorsRankGe1=None):
        self.arrayParentNodes = {}
        self.signalsList = []
        self.ids_root_node = None
        self.showOnlyTensorsRankGe1 = showOnlyTensorsRankGe1

    def getSignalsList(self):
        return self.signalsList

    def setIDSRootNode(self, ids_root_node):
        self.ids_root_node = ids_root_node

    def getIDSRootNode(self):
        return self.ids_root_node

    def addNewNode(self, idsName, dataElement, parentNode, occurrence,
                   dataTreeView, ids_root_occ):
        """ Add a new node (item) to the tree view.

        Arguments:
            idsName      (str)         : Name of the IDS e.g. 'magnetics'.
            dataElement  (obj)         : Data element. To be used to create a
                                         new tree view item.
            parentNode   (QTreeWidgetItem) : Parent of the new-to-be tree view item.
            dataTreeView (QTreeWidget) : QVizDataTreeView object.
        """

        itemDataDict = {}
        itemDataDict['IDSName'] = idsName
        itemDataDict['occurrence'] = occurrence
        itemDataDict['isIDSRoot'] = 0
        itemDataDict['Tag'] = dataElement.tag
        itemDataDict['isSignal'] = 0
        itemDataDict['homogeneous_time'] = ids_root_occ.getHomogeneousTime()

        name = dataElement.text
        dataElementName = dataElement.find('name')

        if dataElementName is not None:
            itemDataDict['dataName'] = dataElementName.text  # set by QVizIDSViewParser (IMAS data full path)

        if name is None:
            if dataElementName is not None:
                name = dataElementName.text

        viewerNode = None
        isArray = 0
        index = -1

        if dataElement.get('index') is not None:
            isArray = 1
            index = dataElement.get('index')

        attribName = dataElement.tag
        if 'name' in dataElement.attrib:
            attribName = dataElement.attrib['name']
            itemDataDict['name'] = attribName  # this is the name of the element defined in IDSDef.xml file

        path = self.getPath(parentNode, attribName, isArray,index)

        if dataElement.get('index') is None:

            itemDataDict, extra_attributes = \
                self.buildNamedDataElement(name,
                                           dataElement,
                                           itemDataDict,
                                           idsName,
                                           occurrence)

            viewerNode = self.build_nodes(dataTreeView, dataElement,
                                          parentNode, itemDataDict,
                                          extra_attributes,
                                          path, ids_root_occ)


        else:
            itemNodeName = "Array of " + dataElement.tag + ' with ' + \
                           dataElement.get('dim') + ' element(s)'
            arrayParentPath = self.getParentPath(parentNode) + "/" + itemNodeName
            if arrayParentPath not in self.arrayParentNodes:
                parentItemDataDict = {}
                parentItemDataDict['Path'] = arrayParentPath
                # Add tree item
                parentNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict)
                parentNode.dataTreeView = dataTreeView
                self.arrayParentNodes[arrayParentPath] = parentNode
                parentNode.setStyleForAOSContainingData()
            else:
                parentNode = self.arrayParentNodes[arrayParentPath]
                parentNode.dataTreeView = dataTreeView


            itemDataDict, extra_attributes = \
            self.buildNamedDataElement(name,
                                       dataElement,
                                       itemDataDict,
                                       idsName,
                                       occurrence)

            viewerNode = self.build_nodes(dataTreeView, dataElement, parentNode, itemDataDict,
                                          extra_attributes, path, ids_root_occ)


        self.setPath(viewerNode, path)

        if viewerNode.isDynamicData() or viewerNode.isStaticData():
            self.signalsList.append(viewerNode)

        return viewerNode

    def build_nodes(self, dataTreeView, dataElement, parentNode, itemDataDict,
                    extra_attributes, path, ids_root_occ):
        global cv
        viewerNode = None

        if dataElement.get('data_type') == "struct_array":
            index = int(dataElement.get('index')) + 1

            if index % 5 == 0:
                logging.getLogger(dataTreeView.uri).info("Building node for " + path + "...")

            itemNodeName = dataElement.tag + ' ' + str(index) + '/' + dataElement.get('dim')

            viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict, extra_attributes)

        elif dataElement.get('data_type') in ['FLT_0D', 'STR_0D', 'INT_0D', 'CPX_0D',
                                              'flt_type', 'str_type', 'int_type', 'cpx_type']:
            itemDataDict['0D_content'] = dataElement.get('content')
            if dataElement.text is not None:
                tag = ''
                if dataElement.tag is not None:
                    tag = dataElement.tag
                itemNodeName = self.addUnitsAndDataTypeToItemNodeName(tag + '=' + dataElement.text, dataElement)
                viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict, extra_attributes) # Add tree item

            elif dataElement.tag is not None:
                itemNodeName = self.addUnitsAndDataTypeToItemNodeName(dataElement.tag, dataElement)
                viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict, extra_attributes) # Add tree item

        else:
            if dataElement.text is not None and dataElement.text.strip() != '':
                itemNodeName = self.addUnitsAndDataTypeToItemNodeName(dataElement.tag + '=' + str(dataElement.text), dataElement)
                viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict, extra_attributes) # Add tree item

            else:
                itemNodeName = self.addUnitsAndDataTypeToItemNodeName(dataElement.tag, dataElement)
                # Add tree item
                viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict, extra_attributes)

        viewerNode.idsRef = ids_root_occ.idsRef
        viewerNode.updateStyle()
        # Adding coordinate and documentation nodes
        self.addQtNodes(itemDataDict, viewerNode)
        viewerNode.dataTreeView = dataTreeView
        return viewerNode

    def addQtNodes(self, itemDataDict, viewerNode):
        """ Add new nodes to the tree view.

        Arguments:
            itemDataDict (obj)             : Data dictionary of the tree item.
            viewerNode   (QTreeWidgetItem) : tree parent item to which new items will be added to the
                                             dataTreeView
        """

        coordinate_display = None

        for i in range(1,7):
            coordinate = "coordinate" + str(i)
            coordinate_same_as = "coordinate" + str(i) + "_same_as"
            if viewerNode.getCoordinate(coordinateNumber=i) is not None:
                coordinate_display = coordinate + "=" + viewerNode.getCoordinate(coordinateNumber=i)
                QVizTreeNode(viewerNode, [coordinate_display])
            if itemDataDict.get(coordinate_same_as) is not None:
                coordinate_display = coordinate_same_as + "=" + itemDataDict[coordinate_same_as]
                QVizTreeNode(viewerNode, [coordinate_display])

        doc_display = None

        if itemDataDict.get('documentation') is not None:
            doc_display = "documentation= " + itemDataDict['documentation']
            QVizTreeNode(viewerNode, [doc_display])

    def addUnitsAndDataTypeToItemNodeName(self, itemNodeName, dataElement):
        if dataElement.get('units') is not None:
            itemNodeName += " [" + dataElement.get('units') + "]"
        if dataElement.get('data_type') is not None:
            itemNodeName += ' ' + '(' + str(dataElement.get('data_type')) + ')'
        return itemNodeName

    def setPath(self, node, path):
        """Set IDS node path.

        Arguments:
            node (QTreeWidgetItem) : Tree view item.
            path (str)             : IDS path to node.
        """
        node.setPath(path)

    def getPath(self, parent, tag, isArray, index):
        """ Get IDS structure node path.

        Arguments:
            parent  (QTreeWidgetItem) : Tree view item. Parent-to-be to a new
                                        item created from the data of the child
                                        data element.
            tag     (str)             : Child data element tag.
            isArray (int)             : Indicator that the child data element is
                                        an array of values (0 for False, 1 for
                                        True)
            index   (int)             : Child data element index.
        """
        parentPath = parent.getPath()
        if isArray == 1:
            tag += '(' + index + ')'
        return parentPath + '/'+tag

    def getParentPath(self, parent):
        """ Get tree view parent item path.

        Arguments:
            parent (QTreeWidgetItem) : Tree view item.
        """
        return parent.getPath()

    def buildNamedDataElement(self, name, dataElement, itemDataDict, idsName, occurrence):
        """ Add node information to each new node of IDS.

        Arguments:
            dataElement  (obj)         : Data element. To be used to create a
                                         new tree view item.
            itemDataDict (obj)         : Data dictionary of the tree item.
            idsName      (str)         : Name of the IDS e.g. 'magnetics'.
        """

        extra_attributes = QVizTreeNode()
        isSignal = 0
        isStatic = 0

        data_type = dataElement.get('data_type')
        if data_type is not None:
            itemDataDict['data_type'] = data_type

        units = dataElement.get('units')
        if units is not None:
            itemDataDict['units'] = units

        # Retrieve IDS node documentation
        documentation = dataElement.get('documentation')
        if documentation is not None:
            itemDataDict['documentation'] = documentation

        # The walk already carries the data dictionary's own verdict on the node
        # -- required, optional, experimental, alpha, obsolescent. Without it the
        # shot view shows a quantity the dictionary is retiring exactly like one
        # it mandates, and the panel that exists to inform the choice says nothing.
        lifecycleStatus = dataElement.get('lifecycle_status')
        if lifecycleStatus is not None:
            itemDataDict['lifecycle_status'] = lifecycleStatus

        if name is not None:

            for i in range(1, 7):
                coordinateName = "coordinate" + str(i)
                coordinateSameAs = coordinateName + "_same_as"
                if dataElement.get(coordinateSameAs) is not None:
                    itemDataDict[coordinateSameAs] = dataElement.get(coordinateSameAs)

                coordinateUnits = coordinateName + "_units"
                if dataElement.get(coordinateUnits) is not None:
                    itemDataDict[coordinateUnits] = dataElement.get(coordinateUnits)

                if dataElement.get('parametrizedPath') is not None:

                    itemDataDict['itime_index'] = dataElement.get('itime_index')
                    extra_attributes.parametrizedPath = dataElement.get('parametrizedPath').replace("self.", "")
                    extra_attributes.itime_index = dataElement.get('itime_index')
                    extra_attributes.aos_parents_count = int(dataElement.get('aos_parents_count'))

                    coordinate = dataElement.get(coordinateName)

                    if coordinate is not None:
                        coordinate = coordinate.replace("/", ".")  # PATCH
                        extra_attributes.coordinates.append(coordinate)
                        if coordinate.endswith('/time') or coordinate.endswith('.time') or coordinate == 'time':
                            extra_attributes.coordinates_explicitly_time_dependent[i] = 1
                        else:
                            extra_attributes.coordinates_explicitly_time_dependent[i] = 0

                        extra_attributes.default_coordinates[i - 1] = coordinate #store coordinates

                    for i in range(0, extra_attributes.aos_parents_count):
                        parameterName = QVizGlobalValues.indices[str(i + 1)]
                        parameterValue = dataElement.get(parameterName)
                        extra_attributes.setParameterValue(parameterName, parameterValue)
                        maxParameterName = QVizGlobalValues.max_indices[str(i + 1)]
                        maxParameterValue = dataElement.get(maxParameterName)
                        extra_attributes.setMaxParameterValue(parameterName, maxParameterValue)

            if data_type is not None:
                if data_type.startswith("FLT_") or data_type.startswith("flt_") or \
                        data_type.startswith("INT_") or data_type.startswith("int_") or data_type == "STR_1D":
                    if dataElement.get('type') == 'dynamic' or dataElement.get('type') == 'static':
                        isSignal = 1
                    if dataElement.get('type') == 'static':
                        isStatic = 1

                    itemDataDict['path_doc'] = dataElement.get('path_doc')
                    itemDataDict['parametrizedPath'] = dataElement.get('parametrizedPath')
                    itemDataDict['aos_parents_count'] = dataElement.get('aos_parents_count')
                    for i in range(0, len(QVizGlobalValues.indices)):
                        key_name = QVizGlobalValues.indices[str(i + 1)]
                        itemDataDict[key_name] = dataElement.get(key_name)
                        key_max_name = QVizGlobalValues.max_indices[str(i + 1)]
                        itemDataDict[key_max_name] = dataElement.get(key_max_name)

            itemDataDict['isSignal'] = isSignal
            itemDataDict['isStatic'] = isStatic

        return itemDataDict, extra_attributes

    def endBuildView(self, idsName, occurrence, dataTreeView):
        ids_root_node = self.getIDSRootNode()
        ids_root_occurrence = ids_root_node.child(0)

        if self._tensorFilterActive():
            self._flattenToNonEmptyTensors(
                ids_root_occurrence,
                self._filledPaths(dataTreeView, idsName, occurrence))

        dataTreeView.signalsList.extend(self.getSignalsList())
        ids_root_node.removeChild(ids_root_occurrence)

        dataTreeView.IDSRoots[idsName].addChild(ids_root_occurrence)
        key = idsName + "/" + str(occurrence)
        dataTreeView.ids_roots_occurrence[key] = ids_root_occurrence

        # Expand the tree item
        dataTreeView.DTVRoot.setExpanded(True)

    def _tensorFilterActive(self):
        if self.showOnlyTensorsRankGe1 is not None:
            return self.showOnlyTensorsRankGe1
        return QVizPreferences.Show_only_tensors_rank_ge_1 == 1

    def _collectDataLeaves(self, node, leaves):
        for i in range(node.childCount()):
            child = node.child(i)
            if child.isDynamicData() or child.isStaticData():
                leaves.append(child)
            else:
                self._collectDataLeaves(child, leaves)

    def _tensorKeyOf(self, leaf):
        """The path naming this tensor, free of any array index.

        The filled paths of an IDS are spelled without an index for its arrays
        of structures, so a tree path only becomes comparable to them once the
        indices it carries -- the letters of the parametrized path, or the
        concrete index of the walk -- are taken out.
        """
        path = leaf.getParametrizedDataPath()
        if path:
            if '.' in path:
                path = path.split('.', 1)[1]
        else:
            path = leaf.getPath() or ''
        return self.INDEXED.sub('', path.replace('.', '/'))

    def _filledPaths(self, dataTreeView, idsName, occurrence):
        """The paths this occurrence holds data at, or None when unknowable.

        Reading one array per tensor to ask whether it is empty costs the whole
        read; the entry answers the same question for every path at once without
        touching a value. An occurrence the case does not hold at all answers a
        refusal, and so does a source that is not the IMAS one: both mean "no
        opinion", and the tree then keeps what the dictionary alone can tell.
        """
        try:
            entry = dataTreeView.dataSource.db_entry
            return set(entry.list_filled_paths(idsName, occurrence))
        except Exception as error:
            logging.getLogger(dataTreeView.uri).info(
                "The filled paths of '%s' occurrence %s cannot be asked (%s): "
                "the tensors shown are those the dictionary declares."
                % (idsName, occurrence, type(error).__name__))
            return None

    def _flattenToNonEmptyTensors(self, root, filled):
        """One node per non-empty tensor, hanging off the occurrence itself.

        The walk goes through the dictionary, so a tensor held by an array of
        structures is met once per element of that array, nested in the folders
        that hold it, and a tensor the case never filled looks exactly like one
        it did. Here the folders are taken out, the tensors of rank 0 with them,
        and each remaining tensor keeps its first element in tree order.
        """
        leaves = []
        self._collectDataLeaves(root, leaves)

        kept, keys = [], set()
        for leaf in leaves:
            if len(QVizNodePlotting(leaf).axes.leafAxes()) < 1:
                continue
            key = self._tensorKeyOf(leaf)
            if key in keys or (filled is not None and key not in filled):
                continue
            keys.add(key)
            kept.append(leaf)

        # Settled before anything is taken out of the tree: a node that loses
        # both its parent and its last reference has its C++ side deleted, and
        # asking a question of the wrapper left behind answers RuntimeError.
        self.signalsList = list(kept)
        keptSet = set(kept)

        for leaf in kept:
            parent = leaf.parent()
            if parent is not root:
                parent.removeChild(leaf)
                root.addChild(leaf)

        for i in range(root.childCount() - 1, -1, -1):
            child = root.child(i)
            if child not in keptSet:
                root.removeChild(child)
