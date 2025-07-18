import xml.etree.ElementTree as ET
import os
#from MDSplus import Connection
from threading import Thread, RLock
import traceback

connectionURL = 'altair.partenaires.cea.fr:8000'

# Currently, the data tree is created differently according to the data source.
#For Tore-Supra, the tree is created from XML mapping files parsing
#For IMAS native data, the tree is created from IDS objects state loaded by the GET() operation

class ToreSupraDataSource:

    def __init__(self, name, uri):
            self.name = name
            self.uri = uri
            self.conn = Connection(connectionURL)
            self.mappingFilesDirectory = os.environ["TS_MAPPINGS_DIR"]

    #Load IMAS (meta) data from mapping files
    def load(self, view, IDSName, occurrence=0, asynch=False):
        idsObject = None
        try:
            tree = ET.parse(self.mappingFilesDirectory + '/' + IDSName + '_v1.xml')
            root = tree.getroot()
            idsObject = root.find(IDSName)
        except:
            traceback.print_exc()
            raise ValueError(
                "Error while reading Tore-Supra mapping file (" + self.mappingFilesDirectory + '/' + IDSName + '_v1.xml)')
        try:
            view.parent.updateView(IDSName, occurrence, idsObject)

        except:
            traceback.print_exc()
            raise ValueError("Error while updating the view.")

    #Check if the mapping file for the given IDS exists
    def exists(self, IDSName):
        fileName = self.mappingFilesDirectory + '/' + IDSName + '_v1.xml'
        return os.path.isfile(fileName)

    #Name of the data under the selected node
    def dataNameInPopUpMenu(self, dataDict):
        if 'Path' in dataDict:
            return dataDict['Path']
        elif 'dataName' in dataDict:
            return dataDict['dataName']
        return None

    #The displayed name of the node
    def treeDisplayedNodeName(self, dataElement):
        if dataElement.find('path') != None:
            return str(dataElement.find('path').text)
        return str(dataElement.find('name').text)

    #Add new nodes to the tree
    def addWxNodes(self, itemDataDict, viewerTree, viewerNode, wxTreeItemData):

        doc_display = None

        if 'documentation' in itemDataDict and itemDataDict['documentation'] != None:
            doc_display = "documentation= " + itemDataDict['documentation']
            viewerTree.AppendItem(viewerNode, doc_display, -1, -1, wxTreeItemData)


    #This defines the unique key attached to each data which can be plotted
    def dataKey(self, vizTreeNode):
        return self.name + "::" + self.uri + '::' + vizTreeNode.getPath()

    def getShortLabel(self):
        return self.name + ":" + self.uri
