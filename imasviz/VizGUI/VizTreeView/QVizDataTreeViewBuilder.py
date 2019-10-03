#  Name   :QVizDataTreeViewBuilder
#
#          Container to build IDS Tree View structure in PyQt5.
#          Note: The wxPython predecessor of this Python file is
#          WxDataTreeViewBuilder.py
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic,L.xinyi, D. Penko
#****************************************************

from PyQt5.QtWidgets import QTreeWidgetItem, QTextEdit
from PyQt5.QtCore import QSize

from imasviz.VizGUI.VizTreeView.QVizTreeNode import QVizTreeNode
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues, GlobalColors
from imasviz.VizGUI.VizTreeView.QVizTreeNodeExtraAttributes import QVizTreeNodeExtraAttributes


class QVizDataTreeViewBuilder:
    def __init__(self, ids):
        self.arrayParentNodes = {}
        self.ids = ids

    def addNewNode(self, idsName, dataElement, parentNode, occurrence, dataTreeView):
        """ Add a new node (item) to the tree view.

        Arguments:
            idsName      (str)         : Name of the IDS e.g. 'magnetics'.
            dataElement  (obj)         : Data element. To be used to create a
                                         new tree view item.
            parentNode   (QTreeWidgetItem) : Parent of the new-to-be tree view item.
            dataTreeView (QTreeWidget) : QVizDataTreeView object.
        """

        itemDataDict = {}
        itemDataDict['availableIDSData'] = 0
        itemDataDict['IDSName'] = idsName
        itemDataDict['occurrence'] = occurrence
        itemDataDict['isIDSRoot'] = 0
        itemDataDict['isSelected'] = 0
        itemDataDict['Tag'] = dataElement.tag
        itemDataDict['isSignal'] = 0

        name = dataElement.text
        dataElementName = dataElement.find('name')

        if dataElementName is not None:
            itemDataDict['dataName'] = dataElementName.text #this is the name set by QVizDataAccessCodeGenerator (IMAS data full path)

        if name is None:
            if dataElementName is not None:
                name = dataElementName.text

        viewerNode = None
        isSignal = 0
        isArray = 0
        index = -1

        if dataElement.get('index') is not None:
            isArray = 1
            index = dataElement.get('index')

        attribName = dataElement.tag
        if 'name' in dataElement.attrib:
            attribName = dataElement.attrib['name']
            itemDataDict['name'] = attribName #this is the name of the element defined in IDSDef.xml file

        path = self.getPath(parentNode, attribName, isArray,
                            index)

        if dataElement.get('index') is None:

            itemDataDict, extra_attributes, isSignal = \
                self.buildNamedDataElement(name,
                                           dataElement,
                                           itemDataDict,
                                           idsName,
                                           occurrence,
                                           dataTreeView)

            viewerNode = self.build_nodes(dataTreeView, dataElement,
                                          parentNode, itemDataDict, extra_attributes)

            item_color = dataTreeView.dataSource.colorOf(viewerNode)
            itemDataDict['availableData'] = (item_color == GlobalColors.BLUE)
            viewerNode.setForeground(0, item_color) # - Set tree item text color

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
            else:
                parentNode = self.arrayParentNodes[arrayParentPath]


            itemDataDict, extra_attributes, isSignal = \
            self.buildNamedDataElement(name,
                                       dataElement,
                                       itemDataDict,
                                       idsName,
                                       occurrence,
                                       dataTreeView)

            viewerNode = self.build_nodes(dataTreeView, dataElement, parentNode, itemDataDict, extra_attributes)
            item_color = dataTreeView.dataSource.colorOf(viewerNode)
            itemDataDict['availableData'] = (item_color == GlobalColors.BLUE)
            viewerNode.setForeground(0, item_color)  # - Set tree item text color

        self.setPath(viewerNode, path)

        if isSignal == 1:
            dataTreeView.signalsList.append(viewerNode)

        return viewerNode

    def build_nodes(self, dataTreeView, dataElement, parentNode, itemDataDict, extra_attributes):
        viewerNode = None

        if dataElement.get('data_type') == "struct_array":
            index = int(dataElement.get('index')) + 1
            itemNodeName = dataElement.tag + ' ' + str(index) + '/' + dataElement.get('dim')
            if dataElement.get('warning_ggd') is not None:
                dataTreeView. IDSRoots[itemDataDict['IDSName']].getNodeData()['warning_ggd'] = 1
            return QVizTreeNode(parentNode, [itemNodeName], itemDataDict, extra_attributes)

        if dataElement.get('data_type') in ['FLT_0D', 'STR_0D','INT_0D', 'xs:integer']:
            maxLineLengthSizeForString = 40
            if dataElement.text is not None:
                s = dataElement.text
                lines = s.split('\n')
                if len(lines) > 1 or (len(lines) == 1 and len(lines[0]) > maxLineLengthSizeForString):
                    itemNodeName = self.addUnitsAndDataTypeToItemNodeName(dataElement.tag, dataElement)
                    # Add tree item
                    viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict, extra_attributes)

                    item_0 = QTreeWidgetItem(viewerNode)
                    q = QTextEdit()
                    q.setMinimumHeight(150)
                    q.setText(dataElement.text)
                    dataTreeView.setItemWidget(item_0, 0, q)

                else:
                    itemNodeName = self.addUnitsAndDataTypeToItemNodeName(dataElement.tag + '=' + str(dataElement.text), dataElement)
                    # Add tree item
                    viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict, extra_attributes)
            else:
                if '=' in dataElement.tag:
                    if dataElement.tag.startswith('comment='):
                        text = dataElement.tag.split('comment=')
                    elif dataElement.tag.startswith('description='):
                        text = dataElement.tag.split('description=')
                    else:
                        text = dataElement.tag.split('=')
                    s = ''
                    if len(text) > 0:
                        s = text[1]
                    lines = s.split('\n')
                    if len(lines) > 1 or (len(lines) == 1 and len(lines[0]) > maxLineLengthSizeForString):
                        itemNodeName = self.addUnitsAndDataTypeToItemNodeName(
                            dataElement.tag.split('=')[0], dataElement)
                        # Add tree item
                        viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict, extra_attributes)

                        item_0 = QTreeWidgetItem(viewerNode)
                        q = QTextEdit()
                        q.setMinimumHeight(150)
                        q.setText(s)
                        dataTreeView.setItemWidget(item_0, 0, q)
                    else:
                        itemNodeName = self.addUnitsAndDataTypeToItemNodeName(dataElement.tag, dataElement)
                        # Add tree item
                        viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict, extra_attributes)
                else:
                    itemNodeName = self.addUnitsAndDataTypeToItemNodeName(dataElement.tag, dataElement)
                    # Add tree item
                    viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict, extra_attributes)

        else:
            if dataElement.text is not None and dataElement.text.strip() != '':
                itemNodeName = self.addUnitsAndDataTypeToItemNodeName(dataElement.tag + '=' + str(dataElement.text), dataElement)
                # Add tree item
                viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict, extra_attributes)

            else:
                itemNodeName = self.addUnitsAndDataTypeToItemNodeName(dataElement.tag, dataElement)
                # Add tree item
                viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict, extra_attributes)

        # Adding coordinate and documentation nodes
        dataTreeView.dataSource.addQtNodes(itemDataDict, dataTreeView,
                                           viewerNode, itemDataDict)
        return viewerNode

    def addUnitsAndDataTypeToItemNodeName(self, itemNodeName, dataElement):
        if dataElement.get('units') is not None:
            itemNodeName += " [" + dataElement.get('units') + "]"
        if dataElement.get('data_type'):
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

    def buildNamedDataElement(self, name, dataElement, itemDataDict, idsName, occurrence, dataTreeView):
        """ Add node information to each new node of IDS.

        Arguments:
            dataElement  (obj)         : Data element. To be used to create a
                                         new tree view item.
            itemDataDict (obj)         : Data dictionary of the tree item.
            idsName      (str)         : Name of the IDS e.g. 'magnetics'.
            dataTreeView (QTreeWidget) : QVizDataTreeView object.
        """

        extra_attributes = QVizTreeNodeExtraAttributes()
        isSignal = 0

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
                coordinate = "coordinate" + str(i)
                if dataElement.get(coordinate) is not None:
                    itemDataDict[coordinate] = dataElement.get(coordinate)
                coordinateSameAs = "coordinate" + str(i) + "_same_as"
                if dataElement.get(coordinateSameAs) is not None:
                    itemDataDict[coordinateSameAs] = dataElement.get(coordinateSameAs)

            coordinate1 = dataElement.get('coordinate1')

            if coordinate1 is not None:
                coordinate1 = coordinate1.replace("/", ".") #PATCH

            if dataElement.get('aos') is not None: #only for native data

                itemDataDict['itime_index'] = dataElement.get('itime_index')
                extra_attributes.aos = dataElement.get('aos').replace("self.", "")
                extra_attributes.coordinate1 = coordinate1
                extra_attributes.itime_index = dataElement.get('itime_index')
                extra_attributes.aos_parents_count = int(dataElement.get('aos_parents_count'))

                if coordinate1 is not None and extra_attributes.isCoordinateTimeDependent(coordinate1):
                    itemDataDict['coordinate1_time_dependent'] = 1
                else:
                    itemDataDict['coordinate1_time_dependent'] = 0


                for i in range(0, extra_attributes.aos_parents_count ):
                    aos_index_name = QVizGlobalValues.indices[str(i + 1)]
                    aos_index_value = dataElement.get(aos_index_name)
                    extra_attributes.add_aos_value(aos_index_name, aos_index_value)
                    aos_max_index_name = QVizGlobalValues.max_indices[str(i + 1)]
                    aos_index_max_value = dataElement.get(aos_max_index_name)
                    extra_attributes.add_aos_max_value(aos_index_name, aos_index_max_value)

            if data_type is not None:
                if data_type.startswith("FLT_") or data_type.startswith("flt_") or \
                        data_type.startswith("INT_") or data_type.startswith("int_"):

                    if dataElement.get('type') == 'dynamic':
                        isSignal = 1

                    if data_type == 'FLT_1D' or data_type == 'flt_1d_type' or \
                       data_type == 'INT_1D' or data_type == 'int_1d_type':
                       itemDataDict['coordinate1'] = coordinate1

                    itemDataDict['path_doc'] = dataElement.get('path_doc')
                    itemDataDict['aos'] = dataElement.get('aos')
                    itemDataDict['aos_parents_count'] = dataElement.get('aos_parents_count')
                    for i in range(0, len(QVizGlobalValues.indices)):
                        key_name = QVizGlobalValues.indices[str(i + 1)]
                        itemDataDict[key_name] = dataElement.get(key_name)
                        key_max_name = QVizGlobalValues.max_indices[str(i + 1)]
                        itemDataDict[key_max_name] = dataElement.get(key_max_name)

            itemDataDict['isSignal'] = isSignal
        return itemDataDict, extra_attributes, isSignal