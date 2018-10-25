import xml.etree.ElementTree as ET
import os
#from MDSplus import Connection
from threading import Thread, RLock
import traceback

lock = RLock()

connectionURL = 'altair.partenaires.cea.fr:8000'

# Currently, the data tree is created differently according to the data source. 
#For Tore-Supra, the tree is created from XML mapping files parsing
#For IMAS native data, the tree is created from IDS objects state loaded by the GET() operation

class ToreSupraDataSource:

    def __init__(self, name, shotNumber, runNumber):
            self.name = name
            self.shotNumber = shotNumber
            self.runNumber = runNumber
            self.imasDbName = name
            self.conn = Connection(connectionURL)
            self.mappingFilesDirectory = os.environ["TS_MAPPINGS_DIR"]

    #Load IMAS (meta) data from mapping files
    def load(self, view, occurrence=0, pathsList=None, async=False):
        # self.threadingEvent = threadingEvent
        # tparser = ThreadedParser(view, threadingEvent)
        # tparser.start()
        idsObject = None
        idsName = view.IDSNameSelected
        try:
            tree = ET.parse(self.mappingFilesDirectory + '/' + idsName + '_v1.xml')
            root = tree.getroot()
            idsObject = root.find(idsName)
        except:
            traceback.print_exc()
            raise ValueError(
                "Error while reading Tore-Supra mapping file (" + self.mappingFilesDirectory + '/' + idsName + '_v1.xml)')
        try:
            view.parent.updateView(idsName, occurrence, idsObject, pathsList)

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

    #Define the color of a node which contains a signal
    def colorOf(self, signalNode, obsolescent=None):
        return wx.BLUE

    #This defines the unique key attached to each data which can be plotted
    def dataKey(self, nodeData):
        return self.name + "::" + str(self.shotNumber) + "::" + str(self.runNumber) + '::' + nodeData['Path']

    def getShortLabel(self):
        return self.name + ":" + str(self.shotNumber) + ":" + str(self.runNumber)


#This class, which inherits from Thread, allows to load IDS data in a separated thread
# class ThreadedParser(Thread):
#     def __init__(self, view, threadingEvent):
#         Thread.__init__(self)
#         self.view = view
#         self.idsName = view.IDSNameSelected
#         self.mappingFilesDirectory = os.environ["TS_MAPPINGS_DIR"]
#         self.threadingEvent = threadingEvent
#
#     #The thread loads all Tore-Supra metadata from the mapping file for the given IDS name
#     def run(self):
#         try:
#             tree = ET.parse(self.mappingFilesDirectory + '/' + self.idsName + '_v1.xml')
#             root = tree.getroot()
#             idsObject = root.find(self.idsName)
#         except:
#             traceback.print_exc()
#             raise ValueError(
#                 "Error while reading Tore-Supra mapping file (" + self.mappingFilesDirectory + '/' + self.idsName + '_v1.xml)')
#
#         try:
#             lock.acquire()
#             self.view.update_view(self.idsName, idsObject)
#         except:
#             traceback.print_exc()
#             raise ValueError(
#                 "Error while updating the view.")
#         finally:
#             lock.release()
#             if self.threadingEvent != None:
#                 self.threadingEvent.set()