#  Name   :IDSTree
#
#          Container to create IDS Tree View structure in PyQt5
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic,L.xinyi, D. Penko
#****************************************************
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QBrush
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow, QTreeView
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

    Arguments:
        parent (QWindow) : QVizDataTreeView parent.

    """
    def __init__(self, parent, dataSource, mappingFilesDirectory,
                 IDSDefFile, *args, **kwargs):
        super(QVizDataTreeView, self).__init__(parent)

        # TODO: From original wxPython. Not yet turned into PyQt counterpart
        # self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.OnExpandItem)
        # self.Bind(wx.EVT_TREE_ITEM_COLLAPSING, self.OnCollapseItem)
        # self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouseEvent)
        # self.gauge = gauge

        # # Basic qMainWindow settings
        # self.resize(520, 800)
        # self.setWindowTitle("IMASViz PyQt5 Treeview")
        # # Set Qt treeview
        # self.treeview = QTreeView(self)
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

        # # TreeView settings
        # self.treeview.setModel(model)
        # self.treeview.setColumnWidth(0, 150)
        # self.setCentralWidget(self.treeview)
        # self.treeview.setAlternatingRowColors(True)

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

class QVizDataTreeViewFrame(QMainWindow):
    def __init__(self, parent, dataSource, IDSDefFile, *args, **kwargs):
        super(QVizDataTreeViewFrame, self).__init__(parent, *args, **kwargs)

        # Basic qMainWindow settings
        self.resize(520, 800)
        self.setWindowTitle("IMASViz PyQt5 Treeview")

        # Set Qt TreeView
        self.treeview = QVizDataTreeView(parent=None,
                       dataSource=dataSource,
                       mappingFilesDirectory=os.environ['TS_MAPPINGS_DIR'],
                       IDSDefFile=IDSDefFile)

        # TreeView settings
        self.treeview.setModel(self.treeview.model)
        self.treeview.setColumnWidth(0, 150)
        self.setCentralWidget(self.treeview)
        self.treeview.setAlternatingRowColors(True)

class Logger:
    def __init__(self):
        pass

    def info(self, message):
        message += '\n'
        print (message)

    def error(self, message):
        message += '\n'