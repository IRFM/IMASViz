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
#       def buildTreeView(...):
#       def addChildren(...):
#       def update_view(...):
#       def getNodeAttributes():
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
#       def OnResult(...):
#       def updateView(...):
#
#    - class TextCtrlLogger definition
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic,L.xinyi, D. Penko
#****************************************************

from PyQt5.QtGui import QStandardItem, QStandardItemModel, QBrush, QMouseEvent, QFont
from PyQt5.QtCore import Qt, QSize, pyqtSlot
from PyQt5.QtWidgets import QMainWindow, QTreeView, QMenu, QTreeWidget, QTreeWidgetItem
import xml.etree.ElementTree as ET
from imasviz.util.GlobalValues import GlobalIDs
from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.data_source.DataSourceFactory import DataSourceFactory
import os, sys
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
                # Add the ids nodes
                idsNode = QTreeWidgetItem(self.IDSRoot, [idsName])
                if self.dataSource.exists(idsName) == 1:
                    # - If there is any data available from the IDS, change set
                    # its dictionary 'availableIDSData' value from 0 to 1 and
                    # color its item text (IDS name) to blue
                    itemDataDict['availableIDSData'] = 1
                    idsNode.setForeground(0, QBrush(Qt.blue))

                # Set QTreeWidgetItem custom data
                # idsNode.setData(1, Qt.UserRole+1, itemDataDict)
                idsNode.itemVIZData = itemDataDict
                # Mapping the idsName with idsNode
                returnedDict[idsName] = idsNode
        return returnedDict

    # def setSelectedItem(self, item):
    #     self.selectedItem = item

    def setIDSNameSelected(self, IDSName):
        self.IDSNameSelected = IDSName

    @pyqtSlot(QTreeWidgetItem, int)
    def onLeftClickItem (self, item, column):
        """ Action to execute upon left clicking on DTV item.

        Arguments:
            item   (obj) : QTreeWidgetItem object.
            column (int) : Item column.
        """
        ### NODE DOCUMENTATION PANEL
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

        # Set and show node documentation panel (TODO)
        # ShowNodeDocumentation.SetAndShow(
        #     parent_WxDataTreeView = self.parent,
        #     documentation = node_doc_str_array)

        print("Node Label: ", node_label)
        print("Node Documentation: ", node_doc)

    def contextMenuEvent(self, event=QMouseEvent):
        if len(self.selectedItems()) == 1:
            # # The selected item
            # item = self.selectedItems()[0] # QTreeWidgetItem object

            # Below is just a menu example
            position=event.pos()
            index = self.indexAt(position)
            if not index.isValid():
                return

            level = 0
            while index.parent().isValid():
                index = index.parent()
                level += 1

            menu = QMenu()
            if level == 0:
                menu.addAction(self.tr("Menu item 1"))
            elif level == 1:
                menu.addAction(self.tr("Menu item 2"))
            elif level == 2:
                menu.addAction(self.tr("Menu item 3"))
            menu.exec_(self.viewport().mapToGlobal(position))

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
        self.dataTreeView = QVizDataTreeView(parent=None,
                                             dataSource=dataSource,
                                             mappingFilesDirectory= \
                                                os.environ['TS_MAPPINGS_DIR'],
                                             IDSDefFile=IDSDefFile)
        print("*", os.environ['TS_MAPPINGS_DIR'])

        # TreeView settings
        self.dataTreeView.setColumnWidth(0, 150)
        self.dataTreeView.setAlternatingRowColors(True)
        self.dataTreeView.setUniformRowHeights(True)
        self.dataTreeView.expandsOnDoubleClick()
        self.setCentralWidget(self.dataTreeView)

class Logger:
    def __init__(self):
        pass

    def info(self, message):
        message += '\n'
        print (message)

    def error(self, message):
        message += '\n'