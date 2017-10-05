#  Name   :IDSTree
#
#          container to create IDS Tree structure in piscope
#
#  Author :
#         Ludovic Fleury, Xinyi Li
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr
#
#
#*******************************************
#     Copyright(c) 2016- F.Ludovic,L.xinyi
#*******************************************
import os
import wx

from imasviz.gui_commands.HandleRightClick import HandleRightClick, HandleRightClickAndShiftDown
from imasviz.view.WxDataTreeViewBuilder import WxDataTreeViewBuilder
import xml.etree.ElementTree as ET
from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.view.ResultEvent import ResultEvent
from imasviz.view.WxSignalsTreeView import IDSSignalTreeFrame

# Define IDS Tree structure and the function to handle the click to display the IDS data
class WxDataTreeView(wx.TreeCtrl):
    def __init__(self, parent, dataSource, mappingFilesDirectory, IDSDefFile, gauge, *args, **kwargs):
        super(WxDataTreeView, self).__init__(parent, style=wx.TR_DEFAULT_STYLE | wx.TR_LINES_AT_ROOT)

        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.OnExpandItem)
        self.Bind(wx.EVT_TREE_ITEM_COLLAPSING, self.OnCollapseItem)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouseEvent)

        self.gauge = gauge

        self.dataSource = dataSource
        self.idsNamesList = []
        self.idsAlreadyParsed = {}
        self.selectedItem = None
        self.shotNumber = dataSource.shotNumber
        self.mappingFilesDirectory = mappingFilesDirectory
        self.IDSNameSelected = None

        self.__collapsing = False

        # Create a IDS root node with each shotnumber
        self.root = self.AddRoot('IDSs'+'('+ str(dataSource.shotNumber)+')')
        self.SetItemHasChildren(self.root)

        # Create the empty tree
        self.dataTree = self.createEmptyIDSsTree(IDSDefFile)

        #User selected signals
        self.selectedSignals = {}

        #List of nodes which contain a signal
        self.signalsList = []

        #Extra informations attached to each leaf of the tree - key = Node name (IMAS path), value = TreeNode object
        self.node_attributes = {}

        #Parent of this frame
        self.parent = parent

        #Keep a reference to shared data (frames, figures, ...) - This is a BrowserAPI instance
        self.imas_viz_api = None

        self.dataCurrentlyLoaded = False

        self.log = Logger()


    def createEmptyIDSsTree(self, IDSDefFile):
        #The tree is created from CPODef.xml or IDSDef.xml file
        tree = ET.parse(IDSDefFile)
        idssroot = tree.getroot()
        # Add the node information to each IDS node
        returnedDict = {}
        for child in idssroot:
            if (child.tag == 'IDS'):
                idsName = child.get('name')
                self.idsNamesList.append(idsName)
                self.idsAlreadyParsed[idsName] = 0
                itemDataDict = {}
                itemDataDict['IDSName'] = idsName
                itemDataDict['isIDSRoot'] = 1
                itemDataDict['dataName'] = idsName
                itemDataDict['isSignal'] = 0
                itemDataDict['isSelected'] = 0
                itemDataDict['Tag'] = idsName
                itemDataDict['Path']= itemDataDict['Tag']
                itemDataDict['availableIDSData'] = 0
                # Add the ids nodes
                #item = wx.TreeItemData(itemDataDict)
                idsNode = self.AppendItem(self.root, idsName, -1, -1, itemDataDict)
                if self.dataSource.exists(idsName) == 1:
                    itemDataDict['availableIDSData'] = 1
                    self.SetItemTextColour(idsNode, wx.BLUE)
                # Mapping the idsName with idsNode
                returnedDict[idsName] = idsNode
        return returnedDict

    def setSelectedItem(self, item):
        self.selectedItem = item

    def setIDSNameSelected(self, IDSName):
        self.IDSNameSelected = IDSName

    # Select the node, call the HandleClick function
    def OnMouseEvent(self, event):

        pos = event.GetPosition()

        if (event.LeftDown()):
            self.popupmenu = None

        if event.LeftDown() and not self.HasFlag(wx.TR_MULTIPLE):
            ht_item, ht_flags = self.HitTest(event.GetPosition())
            if (ht_flags & wx.TREE_HITTEST_ONITEM) != 0:
                self.SetFocus()
                self.SelectItem(ht_item)
            else:
                event.Skip()

        elif event.RightDown() and not event.ShiftDown():
            ht_item, ht_flags = self.HitTest(event.GetPosition())
            if (ht_flags & wx.TREE_HITTEST_ONITEM) != 0:
                self.setSelectedItem(ht_item)
                handleRightClick = HandleRightClick(self)
                showPopUp = handleRightClick.execute(ht_item)
                if showPopUp == 1:
                    self.OnShowPopup(pos)

        elif event.RightDown() and event.ShiftDown():
            ht_item, ht_flags = self.HitTest(event.GetPosition())
            if (ht_flags & wx.TREE_HITTEST_ONITEM) != 0:
                self.setSelectedItem(ht_item)
                handleRightClick = HandleRightClickAndShiftDown(self)
                showPopUp = handleRightClick.execute(ht_item)
                if showPopUp == 1:
                    self.OnShowPopup(pos)
        else:
            event.Skip()

    #  Popup menu
    def OnShowPopup(self, pos):
        if (self.popupmenu == None): return
        self.PopupMenu(self.popupmenu, pos)


    def buildTreeView(self, ids_root_node, idsData):
        # Update the magnetics node with data
        rootNodeData = self.GetItemData(ids_root_node)
        idsName = rootNodeData['IDSName']
        nodeBuilder = WxDataTreeViewBuilder()
        for child in idsData:
            self.addChildren(nodeBuilder, child, ids_root_node, idsName)

    def addChildren(self, nodeBuilder, element, parent, idsName):
        # Add the children node to the IDS node
        element_node = nodeBuilder.addNewNode(idsName, element, parent, self)
        if element_node != None:
            for child in element:
                self.addChildren(nodeBuilder, child, element_node, idsName)

    def update_view(self,idsName, idsData): # Update the tree view with the data

        self.idsAlreadyParsed[idsName] = 1
        ids_root_node = self.dataTree[idsName]
        #self.log.info("Building view for " + idsName + " IDS...")
        if idsData != None:
            self.buildTreeView(ids_root_node, idsData)
            self.EnsureVisible(self.GetLastChild(ids_root_node))
            self.EnsureVisible(ids_root_node)
        #print strftime("%Y-%m-%d %H:%M:%S", gmtime())
        self.dataCurrentlyLoaded = False

    def getNodeAttributes(self, dataName):
        if self.node_attributes != None and dataName in self.node_attributes:
            return self.node_attributes[dataName]
        return None

    def OnExpandItem(self, event):
        return

    def OnCollapseItem(self, event):
        return
        
class WxDataTreeViewFrame(wx.Frame):
    def __init__(self, parent, views, dataSource, IDSDefFile, *args, **kwargs):
        super(WxDataTreeViewFrame, self).__init__(parent, *args, **kwargs)
        publicStr = ''
        if dataSource.name == GlobalValues.IMAS_UDA:
            publicStr = "public "
        self.SetTitle("'" + dataSource.imasDbName + "' " + publicStr + "data source, shot=" + str(dataSource.shotNumber) + ", run=" +  str(dataSource.runNumber))
        # self.gauge = wx.Gauge(panel, 0, 50, size=(250, 10))
        views[dataSource.shotNumber] = WxDataTreeView(self, dataSource, os.environ['TS_MAPPINGS_DIR'], IDSDefFile, None)
        self.wxTreeView = views[dataSource.shotNumber]
        self.parent = parent
        self.Bind(wx.EVT_CLOSE, self.onClose)

        self.logWindow = wx.TextCtrl(self, wx.ID_ANY, "Log window\n", size=(100, 100),
                                     style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox2 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1 = wx.BoxSizer(wx.VERTICAL)

        hbox1.Add(self.wxTreeView, 1, wx.EXPAND)
        vbox2.Add(hbox1, 1, wx.EXPAND)
        vbox.Add(vbox2, 1, wx.EXPAND)

        vbox.Add(self.logWindow, 0, wx.ALL | wx.EXPAND, 3)

        self.SetSizer(vbox)

        self.wxTreeView.log = TextCtrlLogger(self.logWindow)

        # Set up event handler for any worker thread results
        #EVT_RESULT(self, self.OnResult)

        self.eventResultId =  wx.NewId()
        self.Connect(-1, -1,  self.eventResultId , self.OnResult)

        
    def onClose(self, event):
        self.Hide()

    def OnResult(self, event):
        idsName = event.data[0]
        idsData = event.data[1]
        pathsList = event.data[2]
        threadingEvent = event.data[3]
        self.updateView(idsName, idsData, pathsList, threadingEvent)

    def updateView(self, idsName, idsData, pathsList, threadingEvent=None):
        print 'updateView called...'
        self.wxTreeView.log.info("Loading of " + idsName + " IDS ended successfully, building view...")
        self.wxTreeView.update_view(idsName, idsData)
        self.wxTreeView.log.info("View update ended.")
        print 'updateView ended.'

        # Creating the signals tree
        signalsFrame = IDSSignalTreeFrame(None, self.wxTreeView,
                                          str(self.wxTreeView.shotNumber),
                                          GlobalOperations.getIDSDefFile(os.environ['IMAS_DATA_DICTIONARY_VERSION']))
        if pathsList != None:
            for s in pathsList:
                n = signalsFrame.tree.selectNodeWithPath(s)
                if n == None:
                    print 'Path: ' + s + " not found"

        if threadingEvent != None:
            threadingEvent.set()

class Logger:
    def __init__(self):
        pass

    def info(self, message):
        message += '\n'
        print message

    def error(self, message):
        message += '\n'

class TextCtrlLogger:
    def __init__(self, logWindow):
        self.logWindow = logWindow

    def error(self, message):
        message +='\n'
        self.logWindow.AppendText(str(message))

    def info(self, message):
        message +='\n'
        self.logWindow.AppendText(str(message))


if __name__ == "__main__":
    app = wx.App(False)

    GlobalOperations.checkEnvSettings()
    from imasviz.data_source.DataSourceFactory import DataSourceFactory
    dataSourceFactory = DataSourceFactory()
    dataSource = dataSourceFactory.create(name=GlobalValues.TORE_SUPRA, shotNumber=47979)
    from imasviz.Browser_API import Browser_API
    api = Browser_API()
    frame = api.CreateDataTree(dataSource)
    frame.Show()
    app.MainLoop()
