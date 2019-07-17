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
        # if dataElement.tag == 'time_dim':
        #     return

        itemDataDict = {}
        viewerNode = None

        isSignal = 0
        isArray=0
        index=-1

        if (dataElement.get('index') != None):
            #patch for TS
            if(dataTreeView.dataSource.name == QVizGlobalValues.TORE_SUPRA):
                index = dataElement.get('index') - 1
                dataElement.set('index', str(index))
            else:
                isArray=1
                index=dataElement.get('index')

        path = self.getPath(parentNode, dataElement.tag, isArray,
                            index)

        units = dataElement.get('units')
        if (units != None):
            itemDataDict['units'] = units

        # Retrieve IDS node documentation
        documentation = dataElement.get('documentation')
        if (documentation != None):
            itemDataDict['documentation'] = documentation
        # Retrieve node label (name)
        if (dataElement.get('name') != None):
            itemDataDict['name'] = dataElement.get('name')
        if (dataElement.find('name') != None):
            if (dataElement.find('name').text != None):
                itemDataDict['name'] = dataElement.find('name').text

        if (dataElement.get('index') == None):

            if dataElement.find('name') != None:

                QVizTreeItemData, extra_attributes, isSignal, item_color = \
                    self.buildNamedDataElement_FLT1D(dataElement,
                                                     itemDataDict,
                                                     idsName,
                                                     occurrence,
                                                     dataTreeView)
                # Get item text to be displayed in the tree view
                itemNodeName = \
                    dataTreeView.dataSource.treeDisplayedNodeName(dataElement)

                if isSignal==1 or isSignal==2:
                    itemNodeName+=' '+ '(' + str(dataElement.get('data_type')) +')'

                if units != None:
                    itemNodeName += " [" + units + "]"

                # Add tree item
                viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict, extra_attributes)

                # - Set tree item text color
                viewerNode.setForeground(0, item_color)

                dataTreeView.dataSource.addQtNodes(itemDataDict, dataTreeView,
                                                   viewerNode, itemDataDict)

            else:
                # Add node information to each new node of IDS
                itemDataDict['IDSName'] = idsName
                itemDataDict['isSignal'] = 0
                itemDataDict['isIDSRoot'] = 0
                itemDataDict['isSelected'] = 0
                itemDataDict['dataName'] = dataElement.text
                itemDataDict['Tag'] = dataElement.tag

                if dataElement.get('data_type') in ['FLT_0D', 'STR_0D',
                                                    'INT_0D', 'xs:integer']:
                    maxLineLengthSizeForString = 70
                    if dataElement.text != None:
                        s = dataElement.text
                        lines = s.split('\n')
                        if len(lines) > 1 or (len(lines) == 1 and len(lines[0]) > maxLineLengthSizeForString):
                            itemNodeName = dataElement.tag
                            if units != None:
                                itemNodeName += " [" + units + "]"
                            # Add tree item
                            viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict)

                            item_0 = QTreeWidgetItem(viewerNode)
                            q = QTextEdit()
                            q.setMinimumHeight(150)
                            q.setText(dataElement.text)
                            dataTreeView.setItemWidget(item_0, 0, q)
                            #for i in range(0, len(lines)):
                                # Add tree item
                            #    newItem = QVizTreeNode(viewerNode, [lines[i]], itemDataDict)

                        else:
                            itemNodeName = dataElement.tag + '=' + str(dataElement.text)
                            if units != None:
                                itemNodeName += " [" + units + "]"
                            # Add tree item
                            viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict)
                    else:
                        if '=' in dataElement.tag:
                            text = dataElement.tag.split('=')
                            s = text[1]
                            lines = s.split('\n')
                            if len(lines) > 2 or (len(lines) == 1 and len(lines[0]) > maxLineLengthSizeForString):
                                itemNodeName = text[0]
                                if units != None:
                                    itemNodeName += " [" + units + "]"
                                # Add tree item
                                viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict)

                                item_0 = QTreeWidgetItem(viewerNode)
                                q = QTextEdit()
                                q.setMinimumHeight(150)
                                q.setText(s)
                                dataTreeView.setItemWidget(item_0, 0, q)


                                #for i in range(0, len(lines)):
                                    # Add tree item
                                #    newItem = QVizTreeNode(viewerNode, [lines[i]], itemDataDict)

                            else:
                                itemNodeName = dataElement.tag
                                if units != None:
                                    itemNodeName += " [" + units + "]"
                                # Add tree item
                                viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict)
                        else:
                            itemNodeName = dataElement.tag
                            if units != None:
                                itemNodeName += " [" + units + "]"
                            # Add tree item
                            viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict)
                else:

                    if dataElement.text != None and \
                            dataElement.text.strip() != '':
                        itemNodeName = dataElement.tag + '=' + str(dataElement.text)
                        if units != None:
                            itemNodeName += " [" + units + "]"
                        # Add tree item
                        viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict)

                    else:
                        itemNodeName = dataElement.tag
                        if units != None:
                            itemNodeName += " [" + units + "]"
                        # Add tree item
                        viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict)
        else:
            itemNodeName = "Array of " + dataElement.tag + ' with ' + \
                           dataElement.get('dim') + ' element(s)'
            arrayParentPath = \
                self.getParentPath(parentNode) + "/" + itemNodeName
            if arrayParentPath not in self.arrayParentNodes:
                parentItemDataDict = {}
                parentItemDataDict['Path'] = arrayParentPath
                # Add tree item
                parentNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict)

                self.arrayParentNodes[arrayParentPath] = parentNode
            else:
                parentNode = self.arrayParentNodes[arrayParentPath]

            # add the node which has element index
            if dataElement.find('name') != None:
                # itemDataDict['dataName'] = dataElement.find('name').text
                # ids = self.ids  # @UnusedVariable
                # if len(eval(itemDataDict['dataName'])) != 0:
                QVizTreeItemData, extra_attributes, isSignal, item_color = \
                    self.buildNamedDataElement_FLT1D(dataElement,
                                                     itemDataDict,
                                                     idsName,
                                                     occurrence,
                                                     dataTreeView)

                itemNodeName = \
                    dataTreeView.dataSource.treeDisplayedNodeName(dataElement)

                index = int(dataElement.get('index')) + 1

                itemNodeName += ' ' + str(index) + '/' + dataElement.get('dim')

                if units != None:
                    itemNodeName += " [" + units + "]"

                # Add tree item
                viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict, extra_attributes)

                # Set tree item text color
                viewerNode.setForeground(0, item_color)

                dataTreeView.dataSource.addQtNodes(itemDataDict, dataTreeView,
                                                   viewerNode, QVizTreeItemData)

            else:
                itemDataDict['IDSName'] = idsName
                itemDataDict['isSignal'] = 0
                itemDataDict['isIDSRoot'] = 0
                itemDataDict['isSelected'] = 0
                itemDataDict['dataName'] = dataElement.text
                itemDataDict['Tag'] = dataElement.tag
                if dataElement.get('data_type') in ['FLT_0D', 'STR_0D',
                                                    'INT_0D', 'xs:integer']:
                    if dataElement.text != None:
                        itemNodeName=dataElement.tag + '=' + str(dataElement.text)
                        if units != None:
                            itemNodeName += " [" + units + "]"
                    else:
                        itemNodeName = dataElement.tag
                        if units != None:
                            itemNodeName += " [" + units + "]"

                    # Add tree item
                    viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict)

                else:
                    #dimStr = str(int(dataElement.get('dim')) - 1)
                    index = int(dataElement.get('index')) + 1
                    # if dataElement.get('limited_nodes') != None and dataElement.get('limited_nodes') == "1":
                    #     itemNodeName= dataElement.tag + ' ' + "i" + '/' + \
                    #                   dataElement.get('dim')
                    # else:
                    #     itemNodeName = dataElement.tag + ' ' + str(index) + '/' + \
                    #                    dataElement.get('dim')

                    itemNodeName = dataElement.tag + ' ' + str(index) + '/' + \
                                   dataElement.get('dim')
                    if units != None:
                        itemNodeName += " [" + units + "]"
                    # Add tree item
                    viewerNode = QVizTreeNode(parentNode, [itemNodeName], itemDataDict)

        if viewerNode != None:
            self.setPath(viewerNode, path)

            if isSignal == 1:
                dataTreeView.signalsList.append(viewerNode)

        return viewerNode

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
        #parentNodeData = parent.itemVIZData
        #parentPath = parentNodeData['Path']
        return parent.getPath()

    def buildNamedDataElement_FLT1D(self, dataElement, itemDataDict, idsName, occurrence, dataTreeView):
        """ Add node information to each new node of IDS.

        Arguments:
            dataElement  (obj)         : Data element. To be used to create a
                                         new tree view item.
            itemDataDict (obj)         : Data dictionary of the tree item.
            idsName      (str)         : Name of the IDS e.g. 'magnetics'.
            dataTreeView (QTreeWidget) : QVizDataTreeView object.
        """
        item_color = GlobalColors.BLUE
        itemDataDict['availableIDSData'] = 0
        itemDataDict['IDSName'] = idsName
        itemDataDict['dataName'] = dataElement.find('name').text
        itemDataDict['occurrence'] = occurrence

        for i in range(1,7):
            coordinate = "coordinate" + str(i)
            if dataElement.get(coordinate) is not None:
                itemDataDict[coordinate] = dataElement.get(coordinate)
            coordinateSameAs = "coordinate" + str(i) + "_same_as"
            if dataElement.get(coordinateSameAs) is not None:
                itemDataDict[coordinateSameAs] = dataElement.get(coordinateSameAs)

        coordinate1 = dataElement.get('coordinate1')

        if coordinate1 == None and dataTreeView.dataSource.name == "TS" and  \
           dataElement.find('coordinate1') is not None:  # TODO
            coordinate1 = dataElement.find('coordinate1').text

        if coordinate1 != None:
            coordinate1 = coordinate1.replace("/", ".") #PATCH

        extra_attributes = QVizTreeNodeExtraAttributes()

        #TODO !!!!
        if dataElement.get('aos') is not None: #only for native data

            itemDataDict['itime_index'] = dataElement.get('itime_index')
            extra_attributes.aos = dataElement.get('aos').replace("self.", "")
            extra_attributes.coordinate1 = coordinate1
            extra_attributes.itime_index = dataElement.get('itime_index')
            extra_attributes.aos_parents_count = int(dataElement.get('aos_parents_count'))

            if coordinate1 is not None and extra_attributes.isCoordinateTimeDependent(coordinate1):
                itemDataDict['coordinate1_itime_dependent'] = 1
            else:
                itemDataDict['coordinate1_itime_dependent'] = 0


            for i in range(0, extra_attributes.aos_parents_count ):
                aos_index_name = QVizGlobalValues.indices[str(i + 1)]
                aos_index_value = dataElement.get(aos_index_name)
                extra_attributes.add_aos_value(aos_index_name, aos_index_value)
                aos_max_index_name = QVizGlobalValues.max_indices[str(i + 1)]
                aos_index_max_value = dataElement.get(aos_max_index_name)
                extra_attributes.add_aos_max_value(aos_index_name, aos_index_max_value)

        isSignal = 0

        data_type = dataElement.get('data_type')
        if data_type is not None:
            if data_type.startswith("FLT_") or data_type.startswith("flt_") and data_type != "FLT_0D" \
                    and data_type != 'flt_0d_type':
                isSignal = 1
                itemDataDict['data_type'] = data_type
                if data_type == 'FLT_1D' or data_type == 'flt_1d_type':
                   itemDataDict['coordinate1'] = coordinate1
                else:
                    isSignal = 2
                itemDataDict['path_doc'] = dataElement.get('path_doc')
                item_color = dataTreeView.dataSource.colorOf(itemDataDict)
                itemDataDict['aos'] = dataElement.get('aos')
                itemDataDict['aos_parents_count'] = dataElement.get('aos_parents_count')
                for i in range(0, len(QVizGlobalValues.indices)):
                    key_name = QVizGlobalValues.indices[str(i + 1)]
                    itemDataDict[key_name] = dataElement.get(key_name)
                    key_max_name = QVizGlobalValues.max_indices[str(i + 1)]
                    itemDataDict[key_max_name] = dataElement.get(key_max_name)

        itemDataDict['isSignal'] = isSignal
        itemDataDict['isIDSRoot'] = 0
        itemDataDict['isSelected'] = 0
        itemDataDict['Tag'] = dataElement.tag
        return itemDataDict, extra_attributes, isSignal, item_color
