#  Name   :QVizDataTreeViewBuilder
#
#          Container to build IDS Tree View structure in PyQt5.
#  Author :
#         Ludovic Fleury, Li Xinyi, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- L. Fleury,X. Li, D. Penko
#****************************************************
import logging
from threading import Thread, Condition
from imasviz.VizGUI.VizTreeView.QVizTreeNode import QVizTreeNode
from imasviz.VizUtils import QVizGlobalValues

class QVizDataTreeViewBuilder:
    def __init__(self, ids):
        self.arrayParentNodes = {}
        self.ids = ids
        self.ggd_warning = 0
        self.signalsList = []
        self.ids_root_node = None

    def getSignalsList(self):
        return self.signalsList

    def setIDSRootNode(self, ids_root_node):
        self.ids_root_node = ids_root_node

    def getIDSRootNode(self):
        return self.ids_root_node

    def getGGDWarning(self):
        return self.ggd_warning

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

        imas_entry = dataTreeView.dataSource.data_entries[occurrence]

        itemDataDict = {}
        itemDataDict['IDSName'] = idsName
        itemDataDict['occurrence'] = occurrence
        itemDataDict['isIDSRoot'] = 0
        itemDataDict['isSelected'] = 0
        itemDataDict['Tag'] = dataElement.tag
        itemDataDict['isSignal'] = 0
        itemDataDict['homogeneous_time'] = ids_root_occ.getHomogeneousTime()

        name = dataElement.text
        dataElementName = dataElement.find('name')

        if dataElementName is not None:
            itemDataDict['dataName'] = dataElementName.text  # this is the name set by QVizDataAccessCodeGenerator (IMAS data full path)

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
                                          path, imas_entry)


        else:
            itemNodeName = "Array of " + dataElement.tag + ' with ' + \
                           dataElement.get('dim') + ' element(s)'
            arrayParentPath = self.getParentPath(parentNode) + "/" + itemNodeName
            if arrayParentPath not in self.arrayParentNodes:
                parentItemDataDict = {}
                parentItemDataDict['Path'] = arrayParentPath
                # Add tree item
                parentNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict)
                self.arrayParentNodes[arrayParentPath] = parentNode
                parentNode.setStyleForAOSContainingData()
            else:
                parentNode = self.arrayParentNodes[arrayParentPath]


            itemDataDict, extra_attributes = \
            self.buildNamedDataElement(name,
                                       dataElement,
                                       itemDataDict,
                                       idsName,
                                       occurrence)

            viewerNode = self.build_nodes(dataTreeView, dataElement, parentNode, itemDataDict,
                                          extra_attributes, path, imas_entry)


        self.setPath(viewerNode, path)

        if viewerNode.isDynamicData() or viewerNode.isStaticData():
            self.signalsList.append(viewerNode)

        return viewerNode

    def build_nodes(self, dataTreeView, dataElement, parentNode, itemDataDict,
                    extra_attributes, path, imas_entry):
        global cv
        viewerNode = None

        if dataElement.get('data_type') == "struct_array":
            index = int(dataElement.get('index')) + 1

            if index % 5 == 0:
                logging.info("Building node for " + path + "...")

            itemNodeName = dataElement.tag + ' ' + str(index) + '/' + dataElement.get('dim')
            if dataElement.get('ggd_warning') is not None:
                self.ggd_warning = 1

            viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict, extra_attributes)

        elif dataElement.get('data_type') in ['FLT_0D', 'STR_0D', 'INT_0D', 'xs:integer']:
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

        viewerNode.updateStyle(imas_entry)
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

        if name is not None:

            for i in range(1, 7):
                coordinateName = "coordinate" + str(i)
                coordinateSameAs = coordinateName + "_same_as"
                if dataElement.get(coordinateSameAs) is not None:
                    itemDataDict[coordinateSameAs] = dataElement.get(coordinateSameAs)

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
        dataTreeView.signalsList.extend(self.getSignalsList())
        ids_root_node.removeChild(ids_root_occurrence)

        dataTreeView.IDSRoots[idsName].addChild(ids_root_occurrence)
        key = idsName + "/" + str(occurrence)
        dataTreeView.ids_roots_occurrence[key] = ids_root_occurrence

        # Expand the tree item
        dataTreeView.DTVRoot.setExpanded(True)
