# This example demonstrates the use of PyQt5 to construct the imasviz treeview
# GateWay: The next modules are required (written 25. July 2018):
# module load itm-python/3.6
# module load itm-qt/5.8.0

# Simple PyQt5 treeview example:
# https://joekuan.wordpress.com/2016/02/11/pyqt-how-to-hide-top-level-nodes-in-tree-view/

from PyQt5.QtGui import QStandardItem, QStandardItemModel
# from PyQt5.QtCore import *
from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeView
import xml.etree.ElementTree as ET
from imasviz.util.GlobalValues import GlobalIDs
from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.data_source.DataSourceFactory import DataSourceFactory
import os, sys
import imas

# ---------------------------------------------------------------------
class QtDataTreeView(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Basic qMainWindow settings
        self.resize(520, 800)
        self.setWindowTitle("Treeview Example")
        # Set Qt treeview
        self.treeview = QTreeView(self)
        model = QStandardItemModel()
        self.rootNode = model.invisibleRootItem()

        # Set global environment variables and settings
        GlobalOperations.checkEnvSettings()

        # Get IDS data source
        dataSource = DataSourceFactory().create(dataSourceName=GlobalValues.IMAS_NATIVE,
                                                shotNumber=52344,
                                                runNumber=1,
                                                userName='g2penkod',
                                                imasDbName='test')
        self.dataSource = dataSource
        self.idsNamesList = []
        self.idsAlreadyFetched = {}
        self.selectedItem = None
        self.shotNumber = dataSource.shotNumber
        self.runNumber = dataSource.runNumber
        # self.mappingFilesDirectory = mappingFilesDirectory
        self.IDSNameSelected = None

        """Create a IDS root node with each shotnumber"""
        # self.root = self.AddRoot('IDSs'+'('+ str(dataSource.shotNumber)+')')

        # Get IDSDefFile
        IDSDefFile = GlobalOperations.getIDSDefFile(os.environ['IMAS_VERSION'])
        # Create the empty tree
        self.dataTree = self.createEmptyIDSsTree(IDSDefFile)

        # Show QTreeView
        self.treeview.setModel(model)
        self.treeview.setColumnWidth(0, 150)
        self.setCentralWidget(self.treeview)
        self.treeview.setAlternatingRowColors(True)

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
                # print("*itemDataDict", itemDataDict)
                # Add the ids nodes
                idsNode = self.rootNode.appendRow([QStandardItem(idsName), None])
                #TODO figure out how to include itemDataDict ...
                #item = wx.TreeItemData(itemDataDict)
                # idsNode = self.AppendItem(self.root, idsName, -1, -1, itemDataDict)
                # if self.dataSource.exists(idsName) == 1:
                #     itemDataDict['availableIDSData'] = 1
                #     self.SetItemTextColour(idsNode, wx.BLUE)
                # Mapping the idsName with idsNode
                returnedDict[idsName] = idsNode
        return returnedDict

# ---------------------------------------------------------------------

if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    w = QtDataTreeView()
    w.show()
    sys.exit(app.exec_())