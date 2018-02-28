import wx

from imasviz.view.TreeNode import TreeNode
from imasviz.util.GlobalValues import GlobalValues

class WxDataTreeViewBuilder:
    def __init__(self):
        self.arrayParentNodes = {}
        self.ids = None

    def addNewNode(self, idsName, dataElement, parentNode, viewerTree):
        self.ids = viewerTree.dataSource.ids
        if dataElement.tag == 'time_dim':
            return

        # if dataElement.tag == 'mapping_info' and viewerTree.dataSource.name != GlobalValues.IMAS_NATIVE:
        #     if viewerTree.dataSource.shotMin == None:
        #         shot_min = dataElement.find('shot_min')
        #         if shot_min == None :
        #             raise ValueError('Unexpected error : shot_min attribute on mapping_info element is empty.')
        #         viewerTree.dataSource.shotMin = shot_min
        #         print 'shot_min' , shot_min
        #     if viewerTree.dataSource.shotMax == None:
        #         shot_max = dataElement.find('shot_max')
        #         if shot_max == None:
        #             raise ValueError('Unexpected error : shot_max attribute on mapping_info element is empty.')
        #         viewerTree.dataSource.shotMax = shot_max

        #patch for TS
        if (dataElement.get('index') != None and viewerTree.dataSource.name == GlobalValues.TORE_SUPRA):
            index = int(dataElement.get('index')) - 1
            dataElement.set('index', str(index))

        isSignal = 0
        isArray=0
        index=-1
        if (dataElement.get('index') != None):
            isArray=1
            index=dataElement.get('index')

        path = self.getPath(parentNode, viewerTree, dataElement.tag, isArray, index)

        itemDataDict = {}
        viewerNode = None

        units = dataElement.get('units')
        if (units != None):
            itemDataDict['units'] = units

        """Retrieve IDS node documentation """
        documentation = dataElement.get('documentation')
        if (documentation != None):
            itemDataDict['documentation'] = documentation


        if (dataElement.get('index') == None):

            if dataElement.find('name') != None:
                # ids = self.ids  # @UnusedVariable
                # itemDataDict['dataName'] = dataElement.find('name').text
                # if len(eval(itemDataDict['dataName'])) != 0:

                wxTreeItemData, isSignal, display_color = self.buildNamedDataElement_FLT1D(
                                                                                                             dataElement,
                                                                                                             itemDataDict,
                                                                                                             idsName,
                                                                                                             viewerTree)
                display=viewerTree.dataSource.treeDisplayedNodeName(dataElement)

                if isSignal==1:
                    display+=' '+ '(' + str(dataElement.get('data_type')) +')'

                if units != None:
                    display += " [" + units + "]"

                viewerNode = viewerTree.AppendItem(parentNode, display , -1, -1, itemDataDict)

                viewerTree.SetItemTextColour(viewerNode, display_color)

                viewerTree.dataSource.addWxNodes(itemDataDict, viewerTree, viewerNode, itemDataDict)

            else:
                # Add node information to each new node of IDS
                itemDataDict['IDSName'] = idsName
                itemDataDict['isSignal'] = 0
                itemDataDict['isIDSRoot'] = 0
                itemDataDict['isSelected'] = 0
                itemDataDict['dataName'] = dataElement.text
                itemDataDict['Tag'] = dataElement.tag

                if (dataElement.get('data_type') == 'FLT_0D') or (dataElement.get('data_type') == 'STR_0D') or (
                            dataElement.get('data_type') == 'INT_0D') or dataElement.get('data_type') == 'xs:integer':

                    if dataElement.text != None:
                        display = dataElement.tag + '=' + str(dataElement.text)
                        if units != None:
                            display += " [" + units + "]"
                        viewerNode = viewerTree.AppendItem(parentNode, display, -1, -1,
                                                       itemDataDict)
                    else:
                        display = dataElement.tag
                        if units != None:
                            display += " [" + units + "]"
                        viewerNode = viewerTree.AppendItem(parentNode, display,
                                                           -1, -1,
                                                           itemDataDict)
                else:

                    if dataElement.text != None and dataElement.text.strip() != '':
                        display = dataElement.tag + '=' + str(dataElement.text)
                        if units != None:
                            display += " [" + units + "]"
                        viewerNode = viewerTree.AppendItem(parentNode, display,
                                                           -1, -1,
                                                           itemDataDict)
                    else:
                        display = dataElement.tag
                        if units != None:
                            display += " [" + units + "]"
                        viewerNode = viewerTree.AppendItem(parentNode, display,
                                                           -1, -1,
                                                           itemDataDict)
        else:
            display = "Array of " + dataElement.tag + ' with ' + dataElement.get('dim') + ' element(s)'
            arrayParentPath = self.getParentPath(parentNode, viewerTree) + "/" + display
            if arrayParentPath not in self.arrayParentNodes:
                parentItemDataDict = {}
                parentItemDataDict['Path'] = arrayParentPath
                parentNode = viewerTree.AppendItem(parentNode, display, -1, -1, parentItemDataDict)
                self.arrayParentNodes[arrayParentPath] = parentNode
            else:
                parentNode = self.arrayParentNodes[arrayParentPath]

            # add the node which has element index
            if dataElement.find('name') != None:
                # itemDataDict['dataName'] = dataElement.find('name').text
                # ids = self.ids  # @UnusedVariable
                # if len(eval(itemDataDict['dataName'])) != 0:
                wxTreeItemData, isSignal, display_color = self.buildNamedDataElement_FLT1D(
                                                                                                           dataElement,
                                                                                                           itemDataDict,
                                                                                                           idsName,
                                                                                                        viewerTree)

                display = viewerTree.dataSource.treeDisplayedNodeName(dataElement)

                index = int(dataElement.get('index')) + 1

                display += ' ' + str(index) + '/' + dataElement.get('dim')

                if units != None:
                    display += " [" + units + "]"

                viewerNode = viewerTree.AppendItem(parentNode, display, -1, -1, wxTreeItemData)

                viewerTree.SetItemTextColour(viewerNode, display_color)

                viewerTree.dataSource.addWxNodes(itemDataDict, viewerTree, viewerNode, wxTreeItemData)

            else:
                itemDataDict['IDSName'] = idsName
                itemDataDict['isSignal'] = 0
                itemDataDict['isIDSRoot'] = 0
                itemDataDict['isSelected'] = 0
                itemDataDict['dataName'] = dataElement.text
                itemDataDict['Tag'] = dataElement.tag
                if (dataElement.get('data_type') == 'FLT_0D') or (dataElement.get('data_type') == 'STR_0D') or (
                            dataElement.get('data_type') == 'INT_0D'  or dataElement.get('data_type') == 'xs:integer'):

                    if dataElement.text != None:
                        display=dataElement.tag + '=' + str(dataElement.text)
                        if units != None:
                            display += " [" + units + "]"
                    else:
                        display = dataElement.tag
                        if units != None:
                            display += " [" + units + "]"



                    viewerNode = viewerTree.AppendItem(parentNode, display, -1, -1, itemDataDict)

                else:
                    #dimStr = str(int(dataElement.get('dim')) - 1)
                    index = int(dataElement.get('index')) + 1
                    display=dataElement.tag + ' ' + str(index) + '/' + dataElement.get('dim')
                    if units != None:
                        display += " [" + units + "]"
                    viewerNode = viewerTree.AppendItem(parentNode,display, -1, -1, itemDataDict)

        if viewerNode != None:
            self.setPath(viewerNode, viewerTree, path)

            if isSignal == 1:
                viewerTree.signalsList.append(viewerNode)

        # print path, isSignalNode

        return viewerNode


    def setPath(self,node,viewerTree,path):
        nodeData = viewerTree.GetItemData(node)
        # tag = nodeData['Tag']
        if path.endswith("/data"): #TODO
            path = path.replace("/data","")
        nodeData['Path'] = path

    def getPath(self,parent,viewerTree,tag, isArray,index):
        parentNodeData = viewerTree.GetItemData(parent)
        parentPath = parentNodeData['Path']
        if isArray ==1:
            tag+= '(' + index + ')'
        return  parentPath + '/'+tag

    def getParentPath(self, parent, viewerTree):
        parentNodeData = viewerTree.GetItemData(parent)
        parentPath = parentNodeData['Path']
        return parentPath

    def buildNamedDataElement_FLT1D(self, dataElement, itemDataDict, idsName, viewerTree):

        # Add node information to each new node of IDS
        display_color = wx.BLUE
        itemDataDict['availableIDSData'] = 0
        itemDataDict['IDSName'] = idsName
        itemDataDict['dataName'] = dataElement.find('name').text

        coordinate1 = dataElement.get('coordinate1')

        if coordinate1 == None and viewerTree.dataSource.name == "TS" and dataElement.find(
                'coordinate1') != None:  # TODO
            coordinate1 = dataElement.find('coordinate1').text

        if coordinate1 != None:
            coordinate1 = coordinate1.replace("/", ".") #PATCH

        if dataElement.get('aos') != None: #only for native data

            t = TreeNode(dataElement.get('aos').replace("self." ,""),
                         coordinate1,
                         dataElement.get('itime_index'),
                         int(dataElement.get('aos_parents_count')))

            viewerTree.node_attributes[itemDataDict['dataName']] = t
            itemDataDict['itime_index'] = dataElement.get('itime_index')

            if coordinate1 != None and t.isCoordinateTimeDependent(coordinate1):
                itemDataDict['coordinate1_itime_dependent'] = 1
            else:
                itemDataDict['coordinate1_itime_dependent'] = 0


            for i in range(0, t.aos_parents_count ):
                aos_index_name = GlobalValues.indices[str(i + 1)]
                aos_index_value = dataElement.get(aos_index_name)
                t.add_aos_value(aos_index_name, aos_index_value)
                aos_max_index_name = GlobalValues.max_indices[str(i + 1)]
                aos_index_max_value = dataElement.get(aos_max_index_name)
                t.add_aos_max_value(aos_index_name, aos_index_max_value)

        isSignal = 0

        data_type = dataElement.get('data_type')


        if data_type == "FLT_1D" or data_type == "flt_1d_type":

            isSignal = 1
            itemDataDict['data_type'] = data_type
            itemDataDict['coordinate1'] = coordinate1
            itemDataDict['path_doc'] = dataElement.get('path_doc')
                # itemDataDict['documentation'] = dataElement.get('documentation')

            display_color = viewerTree.dataSource.colorOf(itemDataDict)

        itemDataDict['isSignal'] = isSignal
        itemDataDict['isIDSRoot'] = 0
        itemDataDict['isSelected'] = 0
        itemDataDict['Tag'] = dataElement.tag
        return (itemDataDict, isSignal, display_color)
