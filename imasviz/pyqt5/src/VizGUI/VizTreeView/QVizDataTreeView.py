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
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QBrush, QMouseEvent
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow, QTreeView, QMenu
import xml.etree.ElementTree as ET
from imasviz.util.GlobalValues import GlobalIDs
from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.data_source.DataSourceFactory import DataSourceFactory
import os, sys

class QVizDataTreeView(QTreeView):
    """Set and populate QTreeView.
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

        # Set custom popup menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setHeaderHidden(True)
        self.customContextMenuRequested.connect(self.onMouseEventTEST)

        # Set treeview model
        self.model = QStandardItemModel()
        # Set treeview base root
        self.treeRoot = self.model.invisibleRootItem()

        self.dataSource = dataSource
        self.idsNamesList = []
        self.idsAlreadyFetched = {}
        self.selectedItem = None
        self.shotNumber = dataSource.shotNumber
        self.runNumber = dataSource.runNumber
        self.mappingFilesDirectory = mappingFilesDirectory
        self.IDSNameSelected = None

        # Create a IDS root node with each shotnumber
        self.IDSRoot = QStandardItem('IDSs'+'('+ str(dataSource.shotNumber)+')')
        # Set the IDS root node as non-editable
        self.IDSRoot.setEditable(False)
        # Add IDSRoot to treeRoot
        self.treeRoot.appendRow([self.IDSRoot])

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
                # print("*itemDataDict", itemDataDict)
                # Add the ids nodes
                # Note: appendRow([QStandardItem_first_column, QStandartItem_second_column...])
                idsNode = QStandardItem(idsName)
                # - Set the node as non-editable
                idsNode.setEditable(False)
                # - Add the node to treeview root model
                self.IDSRoot.appendRow([idsNode])
                if self.dataSource.exists(idsName) == 1:
                    # - If there is any data available from the IDS, change set
                    # its dictionary 'availableIDSData' value from 0 to 1 and
                    # color its item text (IDS name) to blue
                    itemDataDict['availableIDSData'] = 1
                    idsNode.setForeground(QBrush(Qt.blue))

                idsNode.setData(itemDataDict)
                # Mapping the idsName with idsNode
                returnedDict[idsName] = idsNode
        return returnedDict

    def setSelectedItem(self, item):
        self.selectedItem = item

    def setIDSNameSelected(self, IDSName):
        self.IDSNameSelected = IDSName

    def onMouseEventTEST(self, position):
        """ Mouse event handlers. TODO
        """
        print("* position: ", position)
        # Right mouse button click on the treeview item
        try:
            indexes = self.selectedIndexes()

            if len(indexes) > 0:

                level = 0
                index = indexes[0]
                while index.parent().isValid():
                    index = index.parent()
                    level += 1

            menu = QMenu()
            if level == 0:
                menu.addAction(self.tr("Edit person"))
            elif level == 1:
                menu.addAction(self.tr("Edit object/container"))
            elif level == 2:
                menu.addAction(self.tr("Edit object"))

            menu.exec_(self.viewport().mapToGlobal(position))
        except:
            pass

    def mousePressEvent(self, QMouseEvent):
        """ Override PyQt5 mousePressEvent for mouse events:
        """
        if QMouseEvent.button() == Qt.LeftButton:
            # Left mouse button click anywhere inside the application
            # print("Left Button Clicked")
            pass
        elif QMouseEvent.button() == Qt.RightButton:
            # Right mouse button click anywhere inside the application
            # print("Right Button Clicked")
            position=QMouseEvent.pos()
            index = self.indexAt(position)

            if not index.isValid():
                return

            level = 0
            while index.parent().isValid():
                index = index.parent()
                level += 1

            menu = QMenu()
            if level == 0:
                menu.addAction(self.tr("Edit person"))
            elif level == 1:
                menu.addAction(self.tr("Edit object/container"))
            elif level == 2:
                menu.addAction(self.tr("Edit object"))

            menu.exec_(self.viewport().mapToGlobal(position))

        return super(QVizDataTreeView, self).mousePressEvent(QMouseEvent)

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
        self.dataTreeView.setModel(self.dataTreeView.model)
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