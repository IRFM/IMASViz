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
import time
from imasviz.gui_commands.HandleRightClick import HandleRightClick, HandleRightClickAndShiftDown
from imasviz.view.WxDataTreeViewBuilder import WxDataTreeViewBuilder
import xml.etree.ElementTree as ET
from imasviz.util.GlobalValues import GlobalIDs
from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.view.ResultEvent import ResultEvent
from imasviz.view.WxSignalsTreeView import IDSSignalTreeFrame
from imasviz.gui_commands.configurations.ConfigurationListsFrame import ConfigurationListsFrame
from imasviz.gui_commands.show_node_documentation.ShowNodeDocumentation import ShowNodeDocumentation
from imasviz.gui_commands.SignalHandling import SignalHandling
from imasviz.gui_commands.configurations.SaveSignalSelection import SaveSignalSelection
from imasviz.gui_commands.select_commands.UnselectAllSignals import UnselectAllSignals

class WxDataTreeView(wx.TreeCtrl):
    """Define IDS Tree structure and the function to handle the click to
       display the IDS data
    """
    def __init__(self, parent, dataSource, mappingFilesDirectory, IDSDefFile,
                 gauge, *args, **kwargs):
        super(WxDataTreeView, self).__init__(parent,
                                             style=wx.TR_DEFAULT_STYLE | wx.TR_LINES_AT_ROOT)

        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.OnExpandItem)
        self.Bind(wx.EVT_TREE_ITEM_COLLAPSING, self.OnCollapseItem)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouseEvent)

        self.gauge = gauge

        self.dataSource = dataSource
        self.idsNamesList = []
        self.idsAlreadyFetched = {}
        self.selectedItem = None
        self.shotNumber = dataSource.shotNumber
        self.runNumber = dataSource.runNumber
        self.mappingFilesDirectory = mappingFilesDirectory
        self.IDSNameSelected = None

        self.__collapsing = False

        """Create a IDS root node with each shotnumber"""
        self.root = self.AddRoot('IDSs'+'('+ str(dataSource.shotNumber)+')')
        self.SetItemHasChildren(self.root)

        """Create the empty tree"""
        self.dataTree = self.createEmptyIDSsTree(IDSDefFile)

        """User selected signals"""
        self.selectedSignals = {} # tuple: view.dataSource.shotNumber,
                                  # nodeData, index

        """List of nodes which contain a signal"""
        self.signalsList = []

        """Extra informations attached to each leaf of the tree
           - key = Node name (IMAS path), value = TreeNode object
        """
        self.node_attributes = {}

        """Parent of this tree, this is the wxDataTreeViewFrame"""
        self.parent = parent

        """Keep a reference to shared data (frames, figures, ...)
        - This is a BrowserAPI instance
        """
        self.imas_viz_api = None

        self.dataCurrentlyLoaded = False

        self.log = Logger()

    def createEmptyIDSsTree(self, IDSDefFile):
        """The tree is created from CPODef.xml or IDSDef.xml file"""
        tree = ET.parse(IDSDefFile)
        # Add the node information to each IDS node
        returnedDict = {}
        for child in tree.getroot():
            if (child.tag == 'IDS'):
                """Extract IDS properties from IDSDef.xml file"""
                """Get IDS name"""
                idsName = child.get('name')
                """Get IDS documentation"""
                idsDocumentation = child.get('documentation')
                self.idsNamesList.append(idsName)
                self.idsAlreadyFetched[idsName] = 0

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
                    display_color = wx.BLUE
                    obsolescent = child.get('lifecycle_status')
                    if obsolescent is None or obsolescent == 'active':
                        display_color = wx.BLUE
                    else:
                        display_color = wx.CYAN
                    self.SetItemTextColour(idsNode, display_color)
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
            """Within database tree structure window"""
            ht_item, ht_flags = self.HitTest(event.GetPosition())
            if (ht_flags & wx.TREE_HITTEST_ONITEM) != 0:
                """On left click directly on IDS database node.
                (TREE_HITTEST_ONITEM -> Anywhere on item)
                """
                self.SetFocus()
                """ - Select/Highlight the item/node"""
                self.SelectItem(ht_item)

                """NODE DOCUMENTATION PANEL"""
                self.setSelectedItem(ht_item)
                """ - Set node label"""
                node_label = "..."    # Assigning default label
                if (self.GetItemData(ht_item).get('dataName') != None):
                    node_label = \
                        str(self.GetItemData(ht_item).get('dataName'))
                elif (self.GetItemData(ht_item).get('name') != None):
                    node_label = \
                        str(self.GetItemData(ht_item).get('name'))
                """ - Set node documentation"""
                node_doc = \
                    str(self.GetItemData(ht_item).get('documentation'))

                """ - Set all node documentation related strings to single
                string array for better handling
                """
                node_doc_str_array = []
                node_doc_str_array.append("Node: ")
                node_doc_str_array.append(node_label)
                node_doc_str_array.append("Documentation: ")
                node_doc_str_array.append(node_doc)

                """Set and show node documentation panel"""
                ShowNodeDocumentation.SetAndShow(
                    parent_WxDataTreeView = self.parent,
                    documentation = node_doc_str_array)

                """PLOT PREVIEW PANEL"""
                """Check the enable/disable preview plot checkbox value"""
                checkout_menu_preview_panel_value = self.parent.GetMenuBar(). \
                    FindItemById(GlobalIDs.ID_MENU_ITEM_PREVIEW_PLOT_ENABLE_DISABLE). \
                    IsChecked()

                if (checkout_menu_preview_panel_value == True and
                    self.GetItemData(ht_item).get('isSignal') == 1 and
                    self.GetItemData(ht_item).get('data_type') == 'FLT_1D' and
                    (self.GetItemTextColour(ht_item) == wx.BLUE or
                    self.GetItemTextColour(ht_item) == wx.RED)):
                    """If the node holds an 1D array of values (1D_FLT) then its
                       isSignal attribute equals 1 (isSignale = 1)
                    """

                    """Set and show preview panel"""
                    SignalHandlingObj = SignalHandling(view=self)
                    SignalHandlingObj.plotPreviewSignalCommand(event=event)

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


    def buildTreeView(self, ids_root_node, occurrence, idsData):
        # Update the magnetics node with data
        rootNodeData = self.GetItemData(ids_root_node)
        rootNodeData['occurrence'] = occurrence
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

    def update_view(self,idsName, occurrence, idsData): # Update the tree view with the data
        self.idsAlreadyFetched[idsName] = 1
        ids_root_node = self.dataTree[idsName]
        if idsData != None:
            self.buildTreeView(ids_root_node, occurrence, idsData)
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
            self.SetTitle("'" + dataSource.machineName + "' " + publicStr
                + "data source, shot=" + str(dataSource.shotNumber) + ", run="
                +  str(dataSource.runNumber))
        else:
            self.SetTitle("'" + dataSource.imasDbName + "' "
                + "data source, shot=" + str(dataSource.shotNumber) + ", run="
                + str(dataSource.runNumber))
        self.wxTreeView = WxDataTreeView(self, dataSource,
                                         os.environ['TS_MAPPINGS_DIR'],
                                         IDSDefFile, None)
        #self.wxTreeView = views[dataSource.shotNumber]
        self.parent = parent
        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.createMenu()
        """ Set WxDataTreeViewFrame ID"""
        # self.SetId(10)

        self.logWindow = \
            wx.TextCtrl(self, wx.ID_ANY, "Log window\n", size=(100, 100),
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
        """Unset WxDataTreeViewFrame ID (set it to unused ID)"""
        self.SetId(-1)

    def onShowConfigurations(self, event):
        """Show configuration window
        """
        self.configurationListsFrame = ConfigurationListsFrame(self)
        self.configurationListsFrame.showListBox()

    def onSaveSignalSelection(self, event=None, **kws):
        """Save signal selection as a list of signal paths for single DTV
           (WxDataTreeView)
        """
        print ("Saving signal selection.")
        # Save signal selection as a list of signal paths to .lsp file
        SaveSignalSelection(DTV=self.wxTreeView).execute()

    def onShowMultiPlot(self, event, all_DTV=False):
        """Apply selected signals (single or all DTVs) to MultiPlot
        """
        ss = SignalHandling(self.wxTreeView)
        ss.plotSelectedSignalsToMultiPlotsFrame(all_DTV=all_DTV)

    def onUnselectSignals(self, event, all_DTV=False):
        """Unselect signals in single (current) or all DTVs

           Parameters:
                all_DTV : bool
                Indicator to read selected signals from the current or all DTVs.
        """
        if all_DTV != True:
            UnselectAllSignals(self.wxTreeView).execute()
        else:
            for dtv in self.wxTreeView.imas_viz_api.wxDTVlist:
                UnselectAllSignals(dtv).execute()

    def onCloseAndReopenDatabase(self, event):
        dataSource = self.wxTreeView.dataSource
        api = self.wxTreeView.imas_viz_api
        self.Destroy()
        f = api.CreateDataTree(dataSource)
        api.ShowDataTree(f)

    def createMenu(self):
        """Configure the menu bar.
        """
        menubar = wx.MenuBar()
        # Set new menu list item to be added to 'Options' menu
        menu = wx.Menu()

        ## APPLY CONFIGURATION
        # Add item for showing the Configuration window
        item_conf = menu.Append(
            id=GlobalIDs.ID_MENU_ITEM_APPLY_CONFIGURATION,
            item='Apply Configuration',
            kind=wx.ITEM_NORMAL)

        ## SIGNAL HANDLING
        # Set main submenu for handling signal selection
        menu_signals = wx.Menu()

        # Add item for saving signal selection to configuration file
        item_signals_save_conf = menu_signals.Append(
            id=GlobalIDs.ID_MENU_ITEM_SIGNALS_SAVE,
            item='Save signal selection',
            kind=wx.ITEM_NORMAL)

        # Set submenu for handling signal unselection feature
        menu_signals_unselect = wx.Menu()

        # Add item for unselecting signals in single (this) DTV
        item_signals_unselect_single = menu_signals_unselect.Append(
            id=GlobalIDs.ID_MENU_ITEM_SIGNALS_UNSELECT_SINGLE_DTV,
            item='This IMAS database',
            kind=wx.ITEM_NORMAL)

        # Add item for unselecting signals in single (this) DTV
        item_signals_unselect_all = menu_signals_unselect.Append(
            id=GlobalIDs.ID_MENU_ITEM_SIGNALS_UNSELECT_ALL_DTV,
            item='All IMAS databases',
            kind=wx.ITEM_NORMAL)

        # Append to menu
        menu_signals.Append(GlobalIDs.ID_MENU_SIGNALS_UNSELECT,
                        "Unselect signals", menu_signals_unselect)

        # Append to menu
        menu.Append(GlobalIDs.ID_MENU_SIGNALS,
                        "Signal Selection Options", menu_signals)

        # Add menu separator line
        menu.AppendSeparator()

        ## PREVIEW PLOT MENU
        # Set main preview plot submenu
        menu_pp = wx.Menu()

        # Set enable/disable preview plot checkout item:
        #  - Set checkout item
        item_pp_1 = menu_pp.AppendCheckItem(
                    id=GlobalIDs.ID_MENU_ITEM_PREVIEW_PLOT_ENABLE_DISABLE,
                    item='Enable',
                    help="Enable/Disable preview plot display")
        #  - Set checkout value 'True' as default
        menu_pp.Check(id=GlobalIDs.ID_MENU_ITEM_PREVIEW_PLOT_ENABLE_DISABLE,
                      check=True)

        # """Add option to fix the position of the preview plot"""
        # """ - Set checkout item"""
        # item_pp_2 = menu_pp.AppendCheckItem(
        #             id=GlobalIDs.ID_MENU_ITEM_PREVIEW_PLOT_FIX_POSITION,
        #             item='Fix position', help="Fix position of the preview plot")

        #  - Append to menu
        menu.Append(GlobalIDs.ID_MENU_PREVIEW_PLOT,
                        "Preview Plot Options", menu_pp)

        # Add menu separator line
        menu.AppendSeparator()

        # Set main MultiPlot submenu
        menu_multiPlot = wx.Menu()

        #  - Set item to apply signals, selected in all opened IMAS data source
        #    windows, to MultiPlot submenu
        item_multiPlot_all = menu_multiPlot.Append(
            GlobalIDs.ID_MENU_ITEM_SIGNALS_ALL_DTV_TO_MULTIPLOT,
            item='Create new MultiPlot from selected signals'
                 '(all opened IMAS databases)',
            kind=wx.ITEM_NORMAL)

        #  - Set item to apply signals, selected in a single opened
        #    IMAS data source windows, to MultiPlot submenu
        item_multiPlot_single = menu_multiPlot.Append(
            GlobalIDs.ID_MENU_ITEM_SIGNALS_SINGLE_DTV_TO_MULTIPLOT,
            item='Create new MultiPlot from selected signals '
                 '(this IMAS database)',
            kind=wx.ITEM_NORMAL)

        # - Append to MultiPlot submenu
        menu.Append(GlobalIDs.ID_MENU_MULTIPLOT,
                        "MultiPlot Options", menu_multiPlot)

        # Add and set 'Options' menu
        menubar.Append(menu, 'Options')

        # Add menu separator line
        menu.AppendSeparator()

        # Set and add menu item for the 'Close and Reopen This Database' feature
        item_reopen = menu.Append(
            id=GlobalIDs.ID_MENU_ITEM_CLOSE_AND_REOPEN_DATABASE,
            item='Close and Reopen This Database',
            kind=wx.ITEM_NORMAL)

        # Add the menu to the DTV frame
        self.SetMenuBar(menubar)

        # Bind the features to the menu items
        self.Bind(wx.EVT_MENU, self.onShowConfigurations, item_conf)
        self.Bind(wx.EVT_MENU, self.onSaveSignalSelection, item_signals_save_conf)
        self.Bind(wx.EVT_MENU,
            lambda event: self.onShowMultiPlot(event=event, all_DTV=True),
            item_multiPlot_all)
        self.Bind(wx.EVT_MENU,
            lambda event: self.onShowMultiPlot(event=event, all_DTV=False),
            item_multiPlot_single)
        self.Bind(wx.EVT_MENU,
                  lambda event: self.onUnselectSignals(event=event, all_DTV=False),
                  item_signals_unselect_single)
        self.Bind(wx.EVT_MENU,
                  lambda event: self.onUnselectSignals(event=event, all_DTV=True),
                  item_signals_unselect_all)
        self.Bind(wx.EVT_MENU,
            lambda event: self.onCloseAndReopenDatabase(event=event),
            item_reopen)

    def OnResult(self, event):
        idsName = event.data[0]
        occurrence = event.data[1]
        idsData = event.data[2]
        pathsList = event.data[3]
        threadingEvent = event.data[4]
        self.updateView(idsName, occurrence,idsData, pathsList, threadingEvent)

    def updateView(self, idsName, occurrence, idsData=None, pathsList=None,
                   threadingEvent=None):
        #print ('updating view...')
        t4 = time.time()
        if idsData != None:
            self.wxTreeView.log.info("Loading occurrence " + str(occurrence)
                + " of "+ idsName + " IDS ended successfully, building view...")
            self.wxTreeView.update_view(idsName, occurrence, idsData)
            self.wxTreeView.log.info("View update ended.")
            if (idsName == 'equilibrium'):
                self.wxTreeView.log.info("WARNING: GGD structure array from "
                    + "parent equilibrium.time_slice[itime] has been ignored.")
        t5 = time.time()
        #print('view update took ' + str(t5 - t4) + ' seconds')
        #print ('updateView ended.')

        # Creating the signals tree
        signalsFrame = \
            IDSSignalTreeFrame(None, self.wxTreeView,
                               str(self.wxTreeView.shotNumber),
                               GlobalOperations.getIDSDefFile(os.environ['IMAS_VERSION']))
        if pathsList != None:
            for s in pathsList:
                n = signalsFrame.tree.selectNodeWithPath(s)
                if n == None:
                    print ('Path: ' + s + " not found")

        if threadingEvent != None:
            threadingEvent.set()

class Logger:
    def __init__(self):
        pass

    def info(self, message):
        message += '\n'
        print (message)

    def error(self, message):
        message += '\n'

class TextCtrlLogger:
    def __init__(self, logWindow):
        self.logWindow = logWindow

    def error(self, message):
        message +='\n'
        self.logWindow.append(message)

    def info(self, message):
        message +='\n'
        self.logWindow.append(message)


if __name__ == "__main__":
    app = wx.App(False)

    GlobalOperations.checkEnvSettings()
    from imasviz.data_source.QVizDataSourceFactory import DataSourceFactory
    dataSourceFactory = DataSourceFactory()
    #dataSource = dataSourceFactory.create(dataSourceName=GlobalValues.TORE_SUPRA, shotNumber=47979)
    dataSource = \
        dataSourceFactory.create(dataSourceName=GlobalValues.IMAS_NATIVE,
                                 shotNumber=52205, runNumber=0,
                                 userName="imas_public",imasDbName='west')
    from imasviz.Browser_API import Browser_API
    api = Browser_API()
    frame = api.CreateDataTree(dataSource)
    #frame.Show()
    frame.wxTreeView.setIDSNameSelected("magnetics")
    dataSource.load(frame.wxTreeView, 0, [], True)
    frame.Show()
    app.MainLoop()
