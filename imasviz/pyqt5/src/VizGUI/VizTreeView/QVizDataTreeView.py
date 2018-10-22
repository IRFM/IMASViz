#  Name   :IDSTree
#
#          Container to create IDS Tree View structure in PyQt5.
#          Note: The wxPython predecessor of this Python file is
#          WxDataTreeView.py
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#  TODO:
#
#    - Function definitions (from WxDataTreeView to QVizDataTreeView class)
#       def onMouseEvent(...):
#       def OnShowPopup(...):
#
#    - Function definitions (from WxDataTreeViewFrame to QVizDataTreeViewFrame
#      class)
#       def onClose(...):
#       def onShowConfigurations(...):
#       def onSaveSignalSelection(...):
#       def onShowMultiPlot(...):
#       def onUnselectSignals(...):
#       def onCloseAndReopenDatabase(...):
#       def createMenuBar(...):
#       def updateView(...):
#
#    - class TextCtrlLogger definition
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic,L.xinyi, D. Penko
#****************************************************

import xml.etree.ElementTree as ET
import os, sys, time
from functools import partial
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QBrush, \
    QMouseEvent, QFont, QColor
from PyQt5.QtCore import Qt, QSize, pyqtSlot, QMetaObject
from PyQt5.QtWidgets import QMainWindow, QMenu, QTreeWidget, QTreeWidgetItem, \
                            QWidget, QTableWidget, QTableWidgetItem, \
                            QGridLayout, QTextEdit
from imasviz.pyqt5.src.VizGUI.VizGUICommands.QVizHandleRightClick \
    import QVizHandleRightClick
from imasviz.pyqt5.src.VizGUI.VizGUICommands.QVizNodeDocumentationWidget \
    import QVizNodeDocumentationWidget
from imasviz.pyqt5.src.VizGUI.VizPlot.VizPlotFrames.QVizPreviewPlotWidget \
    import QVizPreviewPlotWidget
from imasviz.pyqt5.src.VizGUI.VizGUICommands.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.pyqt5.src.VizGUI.VizTreeView.QVizDataTreeViewBuilder \
    import QVizDataTreeViewBuilder
from imasviz.util.GlobalValues import GlobalValues, GlobalIDs, GlobalColors
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.data_source.DataSourceFactory import DataSourceFactory
from imasviz.pyqt5.src.VizUtils.QWindowUtils import getWindowSize
from imasviz.gui_commands.configurations.SaveSignalSelection \
    import SaveSignalSelection
from imasviz.pyqt5.src.VizGUI.VizConfigurations.QVizConfigurationListsWindow \
    import QVizConfigurationListsWindow

from PyQt5.QtGui import QDockWidget, QMenuBar, QAction # if moved upwards it gives import errors (???)

class QVizDataTreeView(QTreeWidget):
    """Set and populate QTreeWidget.
    Note: IMASViz wxPython counterpart: WxDataTreeView
          (defined in project directory 'viz/imasviz/view/WxDataTreeView.py')
    """
    def __init__(self, parent, dataSource, mappingFilesDirectory,
                 IDSDefFile, *args, **kwargs):
        """
        Arguments:
            parent     (QWindow)        : QVizDataTreeView parent.
            dataSource (IMASDataSource) : IDS data source from DataSourceFactory
            mappingFilesDirectory (str) : Path to IMASViz mapping files directory
                                          (example: viz/ts_mapping_files)
            IDSDefFile (str)            : Path to IDS dictionary definition .xml
                                          file (example:
                                          viz/imas_data_dictionaries/IDSDef_{IMAS_VERSION}.xml)
        """
        super(QVizDataTreeView, self).__init__(parent)

        # TODO: From original wxPython. Not yet turned into PyQt counterpart
        # self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.OnExpandItem)
        # self.Bind(wx.EVT_TREE_ITEM_COLLAPSING, self.OnCollapseItem)
        # self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouseEvent)
        # self.gauge = gauge

        # Set QTreeWidget name
        self.setObjectName('DTV')

        # Set custom popup menu. Will run the contextMenuEvent() function
        self.setContextMenuPolicy(Qt.DefaultContextMenu)
        # Hide header
        self.setHeaderHidden(True)

        # Connect 'itemClicked' with the 'onLeftClickItem' function.
        # On clicking on the QTreeWidgetItem (left click) the function will
        # be run
        self.itemClicked.connect(self.onLeftClickItem)

        self.dataSource = dataSource
        self.idsNamesList = []
        self.idsAlreadyFetched = {}
        self.selectedItem = None
        self.shotNumber = dataSource.shotNumber
        self.runNumber = dataSource.runNumber
        self.mappingFilesDirectory = mappingFilesDirectory
        self.IDSNameSelected = None

        # Create a IDS root node with each shotnumber
        self.IDSRoot = QTreeWidgetItem(self, ['IDSs'+'('+ str(dataSource.shotNumber)+')'])

        # Array of signal dictionaries (replaced selectedSignals array of
        # tuples)
        self.selectedSignalsDict = {}

        # List of all nodes which contain a signal (all FLT_1D nodes etc.)
        self.signalsList = []

        # Extra informations attached to each leaf of the tree
        #    - key = Node name (IMAS path), value = TreeNode object
        self.node_attributes = {}

        # Parent of this tree, this is the wxDataTreeViewFrame
        self.parent = parent

        # Keep a reference to shared data (frames, figures, ...)
        # - This is a BrowserAPI instance
        self.imas_viz_api = None

        # Create the empty tree
        self.dataTree = self.createEmptyIDSsTree(IDSDefFile)

        self.dataCurrentlyLoaded = False

        self.log = None

        # Set dummy for node documentation widget
        self.ndw = None

    def createEmptyIDSsTree(self, IDSDefFile):
        """The tree is created from CPODef.xml or IDSDef.xml file.
        Note: The original routine source (ues with wxPython) can be found in
        viz/imasviz/view/WxDataTreeView.py
        """
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
                # Add the IDS node as a tree item to the tree view
                idsNode = QTreeWidgetItem(self.IDSRoot, [idsName])
                if self.dataSource.exists(idsName) == 1:
                    # - If there is any data available from the IDS, change set
                    # its dictionary 'availableIDSData' value from 0 to 1 and
                    # color its item text (IDS name) to blue
                    itemDataDict['availableIDSData'] = 1
                    # Set tree item text color
                    idsNode.setForeground(0, GlobalColors.BLUE)

                # Set QTreeWidgetItem custom data
                # idsNode.setData(1, Qt.UserRole+1, itemDataDict)
                idsNode.itemVIZData = itemDataDict
                # Mapping the idsName with idsNode
                returnedDict[idsName] = idsNode
        return returnedDict

    def setSelectedItem(self, item, mouseButton = None):
        """Set selected item.
        Optional: Beside setting the base selected item, set selected item
        explicitly obtained by either left click (marked with blue fill in DTV)
        or right click (on showing the context menu).

        Arguments:
            item        (QTreeWidgetItem) : QTreeWidgetItem object.
            mouseButton (str)             : Define the mouse button clicked on
                                            the QTreeWidgetItem.
                                            Options:
                                            - 'LEFT' for left click
                                            - 'RIGHT' for right click
        """

        # Set base selected item variable
        self.selectedItem = item
        # Set selected item variable obtained by left/right click on the
        # QTreeWidgetItem
        if mouseButton != None:
            if mouseButton == "LEFT":
                self.selectedItem_leftClick = item
            elif mouseButton == "RIGHT":
                self.selectedItem_rightClick = item

    def setIDSNameSelected(self, IDSName):
        self.IDSNameSelected = IDSName

    # Note: pyqtSlot needs QObject to work, in this case, self=QTreeWidget
    # (inherited)
    @pyqtSlot(QTreeWidgetItem, int)
    def onLeftClickItem (self, item, column):
        """ Action to execute upon left clicking on DTV item.

        Arguments:
            item   (QTreeWidgetItem) : QTreeWidgetItem object.
            column (int)             : Item column.
        """

        # Check if item has the 'itemVIZData' attribute. If not -> return
        if hasattr(item, 'itemVIZData'):
            pass
        else:
            return

        # Set selected QTreeWidgetItem on left click
        # (marked with blue fill color in DTV)
        self.setSelectedItem(item = item, mouseButton = "LEFT")

        ### UPDATE NODE DOCUMENTATION WIDGET
        # - Set node label
        node_label = "..."    # Assigning default label
        if (item.itemVIZData.get('dataName') != None):
            node_label = str(item.itemVIZData.get('dataName'))
        elif (item.itemVIZData.get('name') != None):
            node_label = str(item.itemVIZData.get('name'))
        # - Set node documentation#
        node_doc = str(item.itemVIZData.get('documentation'))

        # - Set all node documentation related strings to single
        # string array for better handling
        node_doc_str_array = []
        node_doc_str_array.append("Node: ")
        node_doc_str_array.append(node_label)
        node_doc_str_array.append("Documentation: ")
        node_doc_str_array.append(node_doc)

        # Find and update DTVFrame-docked node documentation widget (NDW)
        ndw = self.parent.findChild(QWidget, "QVizNodeDocumentationWidget")
        if ndw != None:
            ndw.update(documentation = node_doc_str_array)
        else:
            error = 'Node Documentation Widget not found. Update not possible'
            raise ValueError(error)
            self.log.error(str(error))

        ### UPDATE PLOT PREVIEW WIDGET
        if (item.itemVIZData.get('isSignal') == 1 and
            item.itemVIZData.get('data_type') == 'FLT_1D' and
            (item.foreground(0).color().name() == GlobalColors.BLUE_HEX or
            item.foreground(0).color().name() == GlobalColors.RED_HEX)):
            # If the node holds an 1D array of values (1D_FLT) then its
            # isSignal attribute equals 1 (isSignale = 1)

            # Set and show preview panel
            QVizSignalHandlingObj = QVizSignalHandling(dataTreeView = self)
            QVizSignalHandlingObj.plotPreviewSignalCommand()

    def contextMenuEvent(self, event):
        """ Custom menu event on the right click on the tree item.
        """
        # print(event)
        if len(self.selectedItems()) == 1:
            # The selected item
            item = self.selectedItems()[0] # QTreeWidgetItem object

            # Set selected QTreeWidgetItem on right click
            self.setSelectedItem(item = item, mouseButton = "RIGHT")

            # Get position
            self.pos = event.pos()

            # TODO
            handleRightClick = QVizHandleRightClick(self)
            showPopUp = handleRightClick.execute(item)
            # if showPopUp == 1:
            #     self.OnShowPopup(pos)

            # # Below is just a menu example
            # position = event.pos()
            # index = self.indexAt(position)
            # if not index.isValid():
            #     return

            # level = 0
            # while index.parent().isValid():
            #     index = index.parent()
            #     level += 1

            # menu = QMenu()
            # if level == 0:
            #     menu.addAction(self.tr("Menu item 1"))
            # elif level == 1:
            #     menu.addAction(self.tr("Menu item 2"))
            # elif level == 2:
            #     menu.addAction(self.tr("Menu item 3"))
            # menu.exec_(self.viewport().mapToGlobal(position))

    # def mousePressEvent(self, QMouseEvent):
    #     """ Override PyQt5 mousePressEvent for mouse events.
    #     """
    #     if QMouseEvent.button() == Qt.LeftButton:
    #         # Left mouse button click anywhere inside the application
    #         # For actions upon left-clicking on DTV item, the signal connect
    #         # and 'onLefClickItem' routine are to be used.
    #         pass
    #     elif QMouseEvent.button() == Qt.RightButton and \
    #         len(self.selectedItems()) == 1:
    #         # Right mouse button click on a single tree item

    #    return super(QVizDataTreeView, self).mousePressEvent(QMouseEvent)

    def update_view(self,idsName, occurrence, idsData):
        """ Update the tree view with the data.
        """
        self.idsAlreadyFetched[idsName] = 1
        ids_root_node = self.dataTree[idsName]
        if idsData != None:
            self.buildTreeView(ids_root_node, occurrence, idsData)
            # Expand the tree item
            ids_root_node.setExpanded(True)
        self.dataCurrentlyLoaded = False

    def buildTreeView(self, ids_root_node, occurrence, idsData):
        """ Build the data tree view by adding a set of available IDS nodes as
            an items to it.

        Arguments:
            ids_root_node (QTreeWidgetItem) : IDS root tree widget item
                                              (Example: magnetics IDS root node)
            occurrence    (int)             : IDS occurrence number (0-9).
            idsData       (obj)             : Object (element) holding IDS data.
        """
        rootNodeData = ids_root_node.itemVIZData
        rootNodeData['occurrence'] = occurrence
        idsName = rootNodeData['IDSName']
        nodeBuilder = QVizDataTreeViewBuilder()
        #d = ids_root_node.itemVIZData
        ids_root_node = QTreeWidgetItem(ids_root_node, ['occurrence ' + str(int(occurrence))])
        ids_root_node.itemVIZData = {}
        ids_root_node.itemVIZData['Path'] = '/'

        for child in idsData:
            self.addChildren(nodeBuilder, child, ids_root_node, idsName)

    def addChildren(self, nodeBuilder, element, parent, idsName):
        """ To parent item, add all children IDS nodes as a tree view items.

        Arguments:
            nodeBuilder (QVizDataTreeViewBuilder) : Class QVizDataTreeViewBuilder
                                                    object.
            element     (obj)             : idsData child element.
            parent      (QTreeWidgetItem) : Parent tree view item to which the
                                            child is to be added.
            idsName     (str)             : Name of the IDS e.g. 'magnetics'.
        """
        element_node = nodeBuilder.addNewNode(idsName, element, parent, self)
        if element_node != None:
            for child in element:
                self.addChildren(nodeBuilder, child, element_node, idsName)

    def getNodeAttributes(self, dataName):
        if self.node_attributes != None and dataName in self.node_attributes:
            return self.node_attributes[dataName]
        return None

    def OnExpandItem(self, event):
        return

    def OnCollapseItem(self, event):
        return

class QVizDataTreeViewFrame(QMainWindow):
    """ Set QMainWindow to contain the QTreeWidget.
    """

    def __init__(self, parent, views, dataSource, IDSDefFile, *args, **kwargs):
        """
        Arguments:
            parent     (PyQT obj)       : QVizDataTreeView parent.
            views      (array)          :
            dataSource (IMASDataSource) : IDS data source from DataSourceFactory
            IDSDefFile (str)            : Path to IDS dictionary definition .xml
                                          file (example:
                                          viz/imas_data_dictionaries/IDSDef_{IMAS_VERSION}.xml)
        """
        super(QVizDataTreeViewFrame, self).__init__(parent, *args, **kwargs)

        # Set empty list of configuration windows
        self.configurationListsFrame = None

        # Basic settings (QMainWindow)
        self.resize(800, 800)

        # Set Data Tree View Window name
        self.setObjectName('DTV Window')

        # Set title (QMainWindow)
        publicStr = ''
        if dataSource.name == GlobalValues.IMAS_UDA:
            publicStr = "public "
            self.setWindowTitle("'" + dataSource.machineName + "' " + publicStr
                + "data source, shot=" + str(dataSource.shotNumber) + ", run="
                +  str(dataSource.runNumber))
        else:
            self.setWindowTitle("'" + dataSource.imasDbName + "' "
                + "data source, shot=" + str(dataSource.shotNumber) + ", run="
                + str(dataSource.runNumber))

        # Set Qt TreeView
        self.dataTreeView = QVizDataTreeView(parent=self,
                                             dataSource=dataSource,
                                             mappingFilesDirectory= \
                                                os.environ['TS_MAPPINGS_DIR'],
                                             IDSDefFile=IDSDefFile)

        # Set custom event type (ID)
        self.eventResultId =  GlobalIDs.RESULT_EVENT

        # TreeView settings
        self.dataTreeView.setColumnWidth(0, 150)
        self.dataTreeView.setAlternatingRowColors(True)
        self.dataTreeView.setUniformRowHeights(True)
        self.dataTreeView.expandsOnDoubleClick()
        # self.dataTreeView.resize(400,500)
        self.setCentralWidget(self.dataTreeView)

        # Set and add dock widgets to QMainWindow
        self.addDockWidgets()

        # Set and add menu bar
        self.createMenuBar()

        # Connect custom UI elements
        QMetaObject.connectSlotsByName(self)

        # Old wx variable label. Remove when obsolete
        self.view = self.dataTreeView

    def event(self, event):
        """ Listen to events.
        """
        # print(event)
        # print(event.type())
        if event.type() == GlobalIDs.RESULT_EVENT:
            self.onResult(event)
        return super(QVizDataTreeViewFrame, self).event(event)

    def onResult(self, event):
        """ Set data obtained on event (event.type() == GlobalIDs.RESULT_EVENT).
        """
        idsName = event.data[0]
        occurrence = event.data[1]
        idsData = event.data[2]
        pathsList = event.data[3]
        threadingEvent = event.data[4]
        self.updateView(idsName, occurrence, idsData, pathsList, threadingEvent)

    def updateView(self, idsName, occurrence, idsData=None, pathsList=None,
                   threadingEvent=None):
        """ Update QVizDataTreeViewFrame.

        Arguments:
            idsName        (str) : Name of the IDS e.g. 'magnetics'.
            occurrence     (int) : IDS occurrence number (0-9).
            idsData        (obj) : Object (element) holding IDS data.
            pathsList      () :
            threadingEvent () :
        """
        t4 = time.time()
        if idsData != None:
            self.dataTreeView.log.info("Loading occurrence " + str(int(occurrence))
                + " of "+ idsName + " IDS ended successfully, building view...")
            self.dataTreeView.update_view(idsName, occurrence, idsData)
            self.dataTreeView.log.info("View update ended.")
            if (idsName == 'equilibrium'):
                self.dataTreeView.log.info("WARNING: GGD structure array from "
                    + "parent equilibrium.time_slice[itime] has been ignored.")
       # t5 = time.time()

    def createMenuBar(self):
        """Create and configure the menu bar.
        """
        # Main menu bar
        menuBar = QMenuBar(self)
        options = menuBar.addMenu('Options')
        #-----------------------------------------------------------------------
        # Set new menu item for showing the Configuration window
        action_onShowConfigurations = QAction('Apply Configuration', self)
        action_onShowConfigurations.triggered.connect(
            partial(self.onShowConfigurations, self))
        options.addAction(action_onShowConfigurations)

        #-----------------------------------------------------------------------
        # Set new submenu for handling signal selection to be added to 'Options'
        # menu
        subMenu = options.addMenu('Signal Selection Options')

        action_onSaveSignalSelection = QAction('Save Signal Selection', self)
        action_onSaveSignalSelection.triggered.connect(self.onSaveSignalSelection)
        subMenu.addAction(action_onSaveSignalSelection)

        self.setMenuBar(menuBar)

    def addDockWidgets(self):
        """Add dockable widgets to DTV frame main window.
        """

        # Get reference parameters
        # - DTV frame width and height
        ref_width, ref_height = getWindowSize(self)

        # PREVIEW PLOT WIDGET (PPW)
        # - Set the widget
        self.previewPlotWidget=QVizPreviewPlotWidget(parent=self,
                                                     title='Preview Plot')
        # - Plot empty
        self.previewPlotWidget.plot()
        # - Dock the widget
        self.dockWidget_ppw = QDockWidget("Preview Plot", self)
        self.dockWidget_ppw.setFeatures(QDockWidget.DockWidgetFloatable)
        self.dockWidget_ppw.setObjectName("DockWidget_PPW")
        self.dockWidgetContents_ppw = QWidget()
        self.dockWidgetContents_ppw.setObjectName("DockWidgetContents_PPW")
        self.gridLayout_ppw = QGridLayout(self.dockWidgetContents_ppw)
        self.gridLayout_ppw.setObjectName("GridLayout_PPW")
        self.gridLayout_ppw.addWidget(self.previewPlotWidget, 0, 0, 1, 1)
        self.dockWidget_ppw.setWidget(self.dockWidgetContents_ppw)
        # - Set dockwidget size
        self.dockWidget_ppw.setMinimumSize(QSize(ref_width/2, ref_height/2))
        self.addDockWidget(Qt.DockWidgetArea(2), self.dockWidget_ppw)

        # NODE DOCUMENTATION WIDGET (NDW)
        # - Set the widget with default text
        self.nodeDocumentationWidget=QVizNodeDocumentationWidget(parent=self)
        # - Add the widget to dockwidget
        self.dockWidget_ndw = QDockWidget("Node documentation", self)
        self.dockWidget_ndw.setFeatures(QDockWidget.DockWidgetFloatable)
        self.dockWidget_ndw.setObjectName("DockWidget_NDW")
        self.dockWidgetContents_ndw = QWidget()
        self.dockWidgetContents_ndw.setObjectName("DockWidgetContents_NDW")
        self.gridLayout_ndw = QGridLayout(self.dockWidgetContents_ndw)
        self.gridLayout_ndw.setObjectName("GridLayout_NDW")
        self.gridLayout_ndw.addWidget(self.nodeDocumentationWidget, 0, 0, 1, 1)
        self.dockWidget_ndw.setWidget(self.dockWidgetContents_ndw)
        # - Set dockwidget size
        self.dockWidget_ndw.setMinimumSize(QSize(ref_width/2, ref_height/4))
        self.addDockWidget(Qt.DockWidgetArea(2), self.dockWidget_ndw)

        # LOG WIDGET
        self.logWidget = QTextEdit(parent=self)
        self.dockWidget_log = QDockWidget("Log", self)
        self.dockWidget_log.setFeatures(QDockWidget.DockWidgetFloatable)
        self.dockWidget_log.setObjectName("DockWidget_LOG")
        self.dockWidgetContents_log = QWidget()
        self.dockWidgetContents_log.setObjectName("DockWidgetContents_LOG")
        self.gridLayout_log = QGridLayout(self.dockWidgetContents_log)
        self.gridLayout_log.setObjectName("GridLayout_LOG")
        self.gridLayout_log.addWidget(self.logWidget, 0, 0, 1, 1)
        self.dockWidget_log.setWidget(self.dockWidgetContents_log)
        # - Set dockwidget size
        self.dockWidget_ndw.setMinimumSize(QSize(ref_width / 2, ref_height / 4))
        self.addDockWidget(Qt.DockWidgetArea(2), self.dockWidget_log)
        self.dataTreeView.log = Logger(self.logWidget)

    @pyqtSlot(QMainWindow)
    def onShowConfigurations(self, parent):
        """Show configuration window.
        """
        pass
        self.configurationListsWindow = \
            QVizConfigurationListsWindow(parent = self)
        self.configurationListsWindow.show()
        # self.configurationListsFrame.showListBox()

    @pyqtSlot()
    def onSaveSignalSelection(self):
        """Save signal selection as a list of signal paths for single DTV
        (QVizDataTreeView)
        """
        # Save signal selection as a list of signal paths to .lsp file
        SaveSignalSelection(DTV=self.dataTreeView).execute()

class Logger:
    def __init__(self, logWidget):
        self.logWidget = logWidget

    def info(self, message):
        print(message)
        self.logWidget.append(message)


    def error(self, message):
        self.logWidget.append(message)