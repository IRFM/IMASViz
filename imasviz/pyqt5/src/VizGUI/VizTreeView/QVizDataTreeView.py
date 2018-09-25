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
#       def createMenu(...):
#       def updateView(...):
#
#    - class TextCtrlLogger definition
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic,L.xinyi, D. Penko
#****************************************************

from PyQt5.QtGui import QStandardItem, QStandardItemModel, QBrush, QMouseEvent, QFont, QColor
from PyQt5.QtCore import Qt, QSize, pyqtSlot
from PyQt5.QtWidgets import QMainWindow, QTreeView, QMenu, QTreeWidget, QTreeWidgetItem
import xml.etree.ElementTree as ET
from imasviz.util.GlobalValues import GlobalValues, GlobalIDs, GlobalColors
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.data_source.DataSourceFactory import DataSourceFactory
from imasviz.pyqt5.src.VizGUI.VizGUICommands.QVizHandleRightClick import QVizHandleRightClick
from imasviz.pyqt5.src.VizGUI.VizGUICommands.QVizNodeDocumentationWidget import QVizNodeDocumentationWidget
from imasviz.pyqt5.src.VizGUI.VizTreeView.QVizDataTreeViewBuilder import QVizDataTreeViewBuilder
import os, sys, time
from functools import partial

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

        # User selected signals
        self.selectedSignals = {} # tuple: view.dataSource.shotNumber,
                                  # nodeData, index

        # List of nodes which contain a signal
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

        self.log = Logger()

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

    def setSelectedItem(self, item):
        self.selectedItem = item

    def setIDSNameSelected(self, IDSName):
        self.IDSNameSelected = IDSName

    # Note: pyqtSlot needs QObject to work, in this case, self=QTreeWidget
    # (inherited)
    @pyqtSlot(QTreeWidgetItem, int)
    def onLeftClickItem (self, item, column):
        """ Action to execute upon left clicking on DTV item.

        Arguments:
            item   (obj) : QTreeWidgetItem object.
            column (int) : Item column.
        """

        # Check if item has the 'itemVIZData' attribute. If not -> return
        if hasattr(item, 'itemVIZData'):
            pass
        else:
            return

        ### NODE DOCUMENTATION PANEL
        self.setSelectedItem(item)
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

        # Set and show node documentation panel
        # (TODO)
        # ShowNodeDocumentation.SetAndShow(
        #     parent_WxDataTreeView = self.parent,
        #     documentation = node_doc_str_array)
        self.ndw = \
            QVizNodeDocumentationWidget(documentation = node_doc_str_array)
        self.ndw.show()

        print("Node Label: ", node_label)
        print("Node Documentation: ", node_doc)

        ### PLOT PREVIEW PANEL
        # TODO

    def contextMenuEvent(self, event):
        """ Custom menu event on the right click on the tree item.
        """
        # print(event)
        if len(self.selectedItems()) == 1:
            # # The selected item
            item = self.selectedItems()[0] # QTreeWidgetItem object
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
    """ Set QMainWindow to contain the QTreeView.
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

        # Basic settings (QMainWindow)
        self.resize(520, 800)

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
        self.setCentralWidget(self.dataTreeView)

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
        #print ('updating view...')
        t4 = time.time()
        if idsData != None:
            self.dataTreeView.log.info("Loading occurrence " + str(occurrence)
                + " of "+ idsName + " IDS ended successfully, building view...")
            self.dataTreeView.update_view(idsName, occurrence, idsData)
            self.dataTreeView.log.info("View update ended.")
            if (idsName == 'equilibrium'):
                self.dataTreeView.log.info("WARNING: GGD structure array from "
                    + "parent equilibrium.time_slice[itime] has been ignored.")
        t5 = time.time()
        #print('view update took ' + str(t5 - t4) + ' seconds')
        #print ('updateView ended.')

        # # Creating a separate signals tree
        # signalsFrame = \
        #     IDSSignalTreeFrame(None, self.dataTreeView,
        #                        str(self.dataTreeView.shotNumber),
        #                        GlobalOperations.getIDSDefFile(os.environ['IMAS_VERSION']))
        # if pathsList != None:
        #     for s in pathsList:
        #         n = signalsFrame.tree.selectNodeWithPath(s)
        #         if n == None:
        #             print ('Path: ' + s + " not found")

        # if threadingEvent != None:
        #     threadingEvent.set()

class Logger:
    def __init__(self):
        pass

    def info(self, message):
        message += '\n'
        print (message)

    def error(self, message):
        message += '\n'