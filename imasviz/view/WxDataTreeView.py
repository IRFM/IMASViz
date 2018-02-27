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
from imasviz.gui_commands.plots_configuration.ConfigurationListsFrame import ConfigurationListsFrame
from imasviz.gui_commands.show_node_documentation.ShowNodeDocumentation import ShowNodeDocumentation

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
        self.selectedSignals = {} # tuple: view.dataSource.shotNumber, nodeData, index

        #List of nodes which contain a signal
        self.signalsList = []

        #Extra informations attached to each leaf of the tree - key = Node name (IMAS path), value = TreeNode object
        self.node_attributes = {}

        #Parent of this tree, this is the wxDataTreeViewFrame
        self.parent = parent

        #Keep a reference to shared data (frames, figures, ...) - This is a BrowserAPI instance
        self.imas_viz_api = None

        self.dataCurrentlyLoaded = False

        self.log = Logger()

    def createEmptyIDSsTree(self, IDSDefFile):
        """The tree is created from CPODef.xml or IDSDef.xml file"""
        tree = ET.parse(IDSDefFile)
        idssroot = tree.getroot()
        # Add the node information to each IDS node
        returnedDict = {}
        for child in idssroot:
            if (child.tag == 'IDS'):
                """Extract IDS properties from IDSDef.xml file"""
                """Get IDS name"""
                idsName = child.get('name')
                """Get IDS documentation"""
                idsDocumentation = child.get('documentation')
                self.idsNamesList.append(idsName)
                self.idsAlreadyParsed[idsName] = 0

                """Set array holding IDS properties"""
                itemDataDict = {}
                itemDataDict['IDSName'] = idsName
                itemDataDict['isIDSRoot'] = 1
                itemDataDict['dataName'] = idsName
                itemDataDict['isSignal'] = 0
                itemDataDict['isSelected'] = 0
                itemDataDict['Tag'] = idsName
                itemDataDict['Path']= itemDataDict['Tag']
                itemDataDict['availableIDSData'] = 0
                itemDataDict['documentation'] = idsDocumentation
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
        """Mouse event handlers."""

        pos = event.GetPosition()

        if (event.LeftDown()):
            """Left mouse button click anywhere inside the application"""
            self.popupmenu = None

        if event.LeftDown() and not self.HasFlag(wx.TR_MULTIPLE):
            """Left mouse button click (down):"""
            """1. Inside database tree structure window"""
            ht_item, ht_flags = self.HitTest(event.GetPosition())
            if (ht_flags & wx.TREE_HITTEST_ONITEM) != 0:
                """1.1 directly on IDS database node.
                (TREE_HITTEST_ONITEM -> Anywhere on item)
                """
                self.SetFocus()
                """Select/Highlight the item/node"""
                self.SelectItem(ht_item)

                """NODE DOCUMENTATION PANEL"""
                self.setSelectedItem(ht_item)
                """Set node label"""
                node_label = \
                    str(self.GetItemData(ht_item).get('dataName'))
                """Set node documentation"""
                node_doc = \
                    str(self.GetItemData(ht_item).get('documentation'))
                """ Set all node documentation related strings to single string 
                array for better handling 
                """
                node_doc_str_array = []
                node_doc_str_array.append("Node: ")
                node_doc_str_array.append(node_label)
                node_doc_str_array.append("Documentation: ")
                node_doc_str_array.append(node_doc)

                """Set default variables for position and size of the node 
                documentation frame"""
                px, py = (0,0)      # Position
                sx,sy = (200,50)    # Size
                """Get size and position of Browser_API window/frame"""
                browser_API_frame_id = 10
                if (wx.FindWindowById(browser_API_frame_id) != None):
                    """Find Browser_API frame by ID"""
                    browser_API_frame = wx.FindWindowById(browser_API_frame_id)
                    """Get position"""
                    px, py = browser_API_frame.GetPosition()
                    """Get size"""
                    sx, sy = browser_API_frame.GetSize()

                """Modify the position and size for more appealing look of the 
                node documentation panel
                """
                px_ndoc = px
                py_ndoc = py+sy
                sx_ndoc = sx
                sy_ndoc = 200

                """New frame for displaying node documentation with the use of 
                ShowNodeDocumentation.py. 
                """
                frame_node_doc_id = 10012
                stext_node_label_id = 10002
                stext_node_doc_id = 10004

                if (wx.FindWindowById(stext_node_doc_id) != None):
                    """If the frame window (documentation static text ID) 
                    already exists, then update only the required static text 
                    (SetLabel), displaying the node label and documentation
                    """
                    stext_node_label = wx.FindWindowById(stext_node_label_id)
                    stext_node_label.SetLabel(node_doc_str_array[1])
                    stext_node_doc = wx.FindWindowById(stext_node_doc_id)
                    stext_node_doc.SetLabel(node_doc_str_array[3])
                    stext_node_doc.Wrap(sx_ndoc*0.95)
                    """Update the node documentation frame position in 
                    correlation to Browser_API position and size changes
                    """
                    """Find node documentation frame by ID"""
                    frame_node_doc = wx.FindWindowById(frame_node_doc_id)
                    """Update position"""
                    frame_node_doc.SetPosition((px_ndoc, py_ndoc))
                    """Update size"""
                    frame_node_doc.SetSize((sx_ndoc, sy_ndoc))
                else:
                    """ Else, if the frame window (static text ID) doesn't exist,
                    create new one"""
                    frame_node_doc = \
                        ShowNodeDocumentation(
                            documentation = node_doc_str_array,
                            pos_x=px_ndoc, pos_y=py_ndoc,
                            size_x=sx_ndoc, size_y=sy_ndoc)
                    frame_node_doc.SetId(frame_node_doc_id)
                    frame_node_doc.Show()
            else:
                event.Skip()
        elif event.RightDown() and not event.ShiftDown():
            """Right mouse button click (down) on IDS node"""
            ht_item, ht_flags = self.HitTest(event.GetPosition())
            if (ht_flags & wx.TREE_HITTEST_ONITEM) != 0:
                self.setSelectedItem(ht_item)
                handleRightClick = HandleRightClick(self)
                showPopUp = handleRightClick.execute(ht_item)
                if showPopUp == 1:
                    self.OnShowPopup(pos)

        elif event.RightDown() and event.ShiftDown():
            """Right mouse button click (down) + holding shift key on IDS node"""
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
        if idsData != None:
            self.buildTreeView(ids_root_node, idsData)
            self.EnsureVisible(self.GetLastChild(ids_root_node))
            self.EnsureVisible(ids_root_node)
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
            self.SetTitle("'" + dataSource.machineName + "' " + publicStr + "data source, shot=" + str(
                dataSource.shotNumber) + ", run=" +  str(dataSource.runNumber))
        else:
            self.SetTitle("'" + dataSource.imasDbName + "' " + "data source, shot=" + str(
                dataSource.shotNumber) + ", run=" + str(dataSource.runNumber))
        self.wxTreeView = WxDataTreeView(self, dataSource, os.environ['TS_MAPPINGS_DIR'], IDSDefFile, None)
        #self.wxTreeView = views[dataSource.shotNumber]
        self.parent = parent
        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.createMenu()

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
        self.configurationListsFrame = None

        self.eventResultId =  wx.NewId()
        self.Connect(-1, -1,  self.eventResultId , self.OnResult)

        
    def onClose(self, event):
        self.Hide()

    def onShowConfigurations(self, event):
        self.configurationListsFrame = ConfigurationListsFrame(self)
        self.configurationListsFrame.showListBox()

    def createMenu(self):
        """
        Configure the menu bar.
        """
        menubar = wx.MenuBar()
        menu = wx.Menu()
        """Set new menubar item to be added to 'Options' menu"""
        item = menu.Append(wx.NewId(), \
            item='Apply multiple plots configuration', kind=wx.ITEM_NORMAL)
        """Add and set 'Options' menu """
        menubar.Append(menu, 'Options')
        self.SetMenuBar(menubar)
        self.Bind(wx.EVT_MENU, self.onShowConfigurations, item)

    def OnResult(self, event):
        idsName = event.data[0]
        occurrence = event.data[1]
        idsData = event.data[2]
        pathsList = event.data[3]
        threadingEvent = event.data[4]
        self.updateView(idsName, occurrence,idsData, pathsList, threadingEvent)

    def updateView(self, idsName, occurrence, idsData=None, pathsList=None, threadingEvent=None):
        print 'updateView called...'
        if idsData != None:
            self.wxTreeView.log.info("Loading occurrence " + str(occurrence) + " of "+ idsName + " IDS ended successfully, building view...")
            self.wxTreeView.update_view(idsName, idsData)
            self.wxTreeView.log.info("View update ended.")
        print 'updateView ended.'

        # Creating the signals tree
        signalsFrame = IDSSignalTreeFrame(None, self.wxTreeView,
                                          str(self.wxTreeView.shotNumber),
                                          GlobalOperations.getIDSDefFile(os.environ['IMAS_VERSION']))
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
    #dataSource = dataSourceFactory.create(dataSourceName=GlobalValues.TORE_SUPRA, shotNumber=47979)
    dataSource = dataSourceFactory.create(dataSourceName=GlobalValues.IMAS_NATIVE, shotNumber=51460, runNumber=0, userName="imas_public",imasDbName='west')
    from imasviz.Browser_API import Browser_API
    api = Browser_API()
    frame = api.CreateDataTree(dataSource)
    frame.Show()
    app.MainLoop()
