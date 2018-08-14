import os
import imas
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import QTreeWidgetItem

#from imasviz.signals_data_access.generator.ETNativeDataTree_Generated_3_6_0 import ETNativeDataTree_Generated_3_6_0
from imasviz.signals_data_access.generator.ETNativeDataTree_Generated_3_7_0 import ETNativeDataTree_Generated_3_7_0
from imasviz.signals_data_access.generator.ETNativeDataTree_Generated_3_9_0 import ETNativeDataTree_Generated_3_9_0
from imasviz.signals_data_access.generator.ETNativeDataTree_Generated_3_9_1 import ETNativeDataTree_Generated_3_9_1
from imasviz.signals_data_access.generator.ETNativeDataTree_Generated_3_11_0 import ETNativeDataTree_Generated_3_11_0
from imasviz.signals_data_access.generator.ETNativeDataTree_Generated_3_12_0 import ETNativeDataTree_Generated_3_12_0
from imasviz.signals_data_access.generator.ETNativeDataTree_Generated_3_12_1 import ETNativeDataTree_Generated_3_12_1
from imasviz.signals_data_access.generator.ETNativeDataTree_Generated_3_15_0 import ETNativeDataTree_Generated_3_15_0
from imasviz.signals_data_access.generator.ETNativeDataTree_Generated_3_15_1 import ETNativeDataTree_Generated_3_15_1
from imasviz.signals_data_access.generator.ETNativeDataTree_Generated_3_16_0 import ETNativeDataTree_Generated_3_16_0
from imasviz.signals_data_access.generator.ETNativeDataTree_Generated_3_17_0 import ETNativeDataTree_Generated_3_17_0
from imasviz.signals_data_access.generator.ETNativeDataTree_Generated_3_17_1 import ETNativeDataTree_Generated_3_17_1
from imasviz.signals_data_access.generator.ETNativeDataTree_Generated_3_17_2 import ETNativeDataTree_Generated_3_17_2
from imasviz.signals_data_access.generator.ETNativeDataTree_Generated_3_18_0 import ETNativeDataTree_Generated_3_18_0
from imasviz.signals_data_access.generator.ETNativeDataTree_Generated_3_19_1 import ETNativeDataTree_Generated_3_19_1
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.util.GlobalValues import GlobalValues, GlobalColors


class GeneratedClassFactory:
    def __init__(self, IMASDataSource, view, occurrence=0, pathsList = None, async = True):
        self.IMASDataSource = IMASDataSource
        self.view = view
        self.occurrence = occurrence
        self.pathsList = pathsList
        self.async = async

    def create(self):
        generatedDataTree = None

        imas__dd_version = os.environ['IMAS_VERSION']
        if GlobalValues.TESTING:
            imas__dd_version = GlobalValues.TESTING_IMAS_VERSION

        if imas__dd_version == "3.7.0":
            generatedDataTree = ETNativeDataTree_Generated_3_7_0(userName=self.IMASDataSource.userName,
                                                           imasDbName=self.IMASDataSource.imasDbName,
                                                           shotNumber=self.IMASDataSource.shotNumber,
                                                           runNumber=self.IMASDataSource.runNumber,
                                                           view=self.view,
                                                           occurrence=self.occurrence,
                                                           pathsList = self.pathsList,
                                                           async=self.async)
        # elif imas__dd_version == "3.6.0":
        #     generatedDataTree = ETNativeDataTree_Generated_3_6_0(userName=self.IMASDataSource.userName,
        #                                                          imasDbName=self.IMASDataSource.imasDbName,
        #                                                          shotNumber=self.IMASDataSource.shotNumber,
        #                                                          runNumber=self.IMASDataSource.runNumber,
        #                                                          view=self.view,
        #                                                          occurrence=self.occurrence,
        #                                                          pathsList=self.pathsList,
        #                                                          async=self.async)
        elif imas__dd_version == "3.9.0":
            generatedDataTree = ETNativeDataTree_Generated_3_9_0(userName=self.IMASDataSource.userName,
                                                                 imasDbName=self.IMASDataSource.imasDbName,
                                                                 shotNumber=self.IMASDataSource.shotNumber,
                                                                 runNumber=self.IMASDataSource.runNumber,
                                                                 view=self.view,
                                                                 occurrence=self.occurrence,
                                                                 pathsList=self.pathsList,
                                                                 async=self.async)
        elif imas__dd_version == "3.9.1":
            generatedDataTree = ETNativeDataTree_Generated_3_9_1(userName=self.IMASDataSource.userName,
                                                                 imasDbName=self.IMASDataSource.imasDbName,
                                                                 shotNumber=self.IMASDataSource.shotNumber,
                                                                 runNumber=self.IMASDataSource.runNumber,
                                                                 view=self.view,
                                                                 occurrence=self.occurrence,
                                                                 pathsList=self.pathsList,
                                                                 async=self.async)
        elif imas__dd_version == "3.11.0":
            generatedDataTree = ETNativeDataTree_Generated_3_11_0(userName=self.IMASDataSource.userName,
                                                                 imasDbName=self.IMASDataSource.imasDbName,
                                                                 shotNumber=self.IMASDataSource.shotNumber,
                                                                 runNumber=self.IMASDataSource.runNumber,
                                                                 view=self.view,
                                                                 occurrence=self.occurrence,
                                                                 pathsList=self.pathsList,
                                                                 async=self.async)
        elif imas__dd_version == "3.12.0":
            generatedDataTree = ETNativeDataTree_Generated_3_12_0(userName=self.IMASDataSource.userName,
                                                                 imasDbName=self.IMASDataSource.imasDbName,
                                                                 shotNumber=self.IMASDataSource.shotNumber,
                                                                 runNumber=self.IMASDataSource.runNumber,
                                                                 view=self.view,
                                                                 occurrence=self.occurrence,
                                                                 pathsList=self.pathsList,
                                                                 async=self.async)
        elif imas__dd_version == "3.15.0":
            generatedDataTree = ETNativeDataTree_Generated_3_15_0(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        elif imas__dd_version == "3.15.1":
            generatedDataTree = ETNativeDataTree_Generated_3_15_1(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        elif imas__dd_version == "3.16.0":
            generatedDataTree = ETNativeDataTree_Generated_3_16_0(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)

        elif imas__dd_version == "3.17.0":
            generatedDataTree = ETNativeDataTree_Generated_3_17_0(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        elif imas__dd_version == "3.17.1":
            generatedDataTree = ETNativeDataTree_Generated_3_17_1(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        elif imas__dd_version == "3.17.2":
            generatedDataTree = ETNativeDataTree_Generated_3_17_2(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        elif imas__dd_version == "3.18.0":
            generatedDataTree = ETNativeDataTree_Generated_3_18_0(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        elif imas__dd_version == "3.19.1":
            generatedDataTree = ETNativeDataTree_Generated_3_19_1(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        else:
            raise ValueError("IMAS dictionary version not supported")

        return generatedDataTree


class IMASDataSource:

    IDAM_MAPPED_IDS = ["bolometer", "core_profiles", "equilibrium", "summary","magnetics","pf_active","tf","interfero_polarimeter","pf_passive","soft_x_rays","ece"]

    def __init__(self, name, userName, imasDbName, shotNumber, runNumber, machineName=None):
        self.name = name
        self.userName =  userName
        self.imasDbName = imasDbName
        self.shotNumber = shotNumber
        self.runNumber = runNumber
        self.machineName = machineName
        self.ids = None

    # Load IMAS data using IMAS api
    def load(self, view, occurrence=0, pathsList = None, async=True):
        self.generatedDataTree = GeneratedClassFactory(self, view, occurrence, pathsList, async).create()
        if self.generatedDataTree == None:
            raise ValueError("Code generation issue detected !!")

        if self.ids == None:
            self.ids = imas.ids(self.shotNumber, self.runNumber, 0, 0)

            self.ids.open_env(self.userName, self.imasDbName, os.environ["IMAS_MAJOR_VERSION"])
            if (self.ids.expIdx == -1):
                raise ValueError("Can not open shot " + str(self.shotNumber) + "  from data base " + self.imasDbName + " of user " + self.userName)

        self.generatedDataTree.ids = self.ids

        view.dataCurrentlyLoaded = True
        view.idsAlreadyFetched[view.IDSNameSelected] = 1
        #view.log.info('Loading ' + view.IDSNameSelected + ' IDS...')

        if async==True:
            self.generatedDataTree.start() #This will call asynchroneously the get() operation for fetching IMAS data
        else:
            self.generatedDataTree.run()  #This will call the get() operation for fetching IMAS data

    def refreshIDS(self, IDSName, occurrence=0):
        """Refresh the source IDS and its data.

        Arguments:
            IDSName    (str) : Name of the IDS e.g. 'magnetics'.
            occurrence (int) : IDS occurrence number (0-9).
        """
        exec('self.ids.' + IDSName + '.get()')

    @staticmethod
    def try_to_open(imasDbName, userName, shotNumber, runNumber):
        ids = imas.ids(shotNumber, runNumber, 0, 0)
        ids.open_env(userName, imasDbName, os.environ["IMAS_MAJOR_VERSION"])
        if (ids.expIdx == -1):
            raise ValueError("Can not open shot " + str(shotNumber) + "  from data base " + imasDbName + " of user " + userName)

    @staticmethod
    def try_to_open_uda_datasource(machineName, shotNumber, runNumber):
        ids = imas.ids(shotNumber, runNumber, 0, 0)
        if machineName in ('WEST',):
            ids.open_public(machineName)
        else:
            ids.create_public(machineName)
        if (ids.expIdx == -1):
            raise ValueError("Can not open shot " + str(shotNumber) + "  from " + machineName)

    # Check if the data for the given IDS exists
    def exists(self, IDSName):
        return True
        # if IDSName in IMASDataSource.IDAM_MAPPED_IDS:
        #     return True
        # else:
        #     return False

    # Define the color of a node which contains a signal
    def colorOf(self, signalNode):
        ids = self.ids #@UnusedVariable
        if signalNode['data_type'] == 'FLT_1D' or signalNode['data_type'] == 'flt_1d_type' :
            if len(eval(signalNode['dataName'])) == 0: #empty (signals) arrays appear in black
                return GlobalColors.BLACK
            else:
                return GlobalColors.BLUE #non empty (signals) arrays appear in blue
        return GlobalColors.BLACK

    # Name of the data under the selected node
    def dataNameInPopUpMenu(self, dataDict):
        #dico = dataDict.GetData()
        if 'dataName' in dataDict:
            return dataDict['dataName']
        return None

    # The displayed name of the node
    def treeDisplayedNodeName(self, dataElement):
        return str(dataElement.find('name').text)

    # This defines the unique key attached to each data which can be plotted
    def dataKey(self, nodeData):
        return self.name + "::" + self.imasDbName + "::" + str(self.shotNumber) + "::" + str(self.runNumber) + '::' + nodeData['Path']

    def getShortLabel(self):
        return self.imasDbName + ":" + str(self.shotNumber) + ":" + str(self.runNumber)

    def addQtNodes(self, itemDataDict, dataTreeView, viewerNode, treeItemData):
        """ Add new nodes to the tree view.

        Arguments:
            itemDataDict (obj)             : Data dictionary of the tree item.
            dataTreeView (QTreeWidget)     : QVizDataTreeView object.
            viewerNode   (QTreeWidgetItem) : Tree item to be added to the
                                             dataTreeView
        """

        coordinate_display = None

        # if itemDataDict.get('coordinate1') != None:
        #     coordinate_display = "coordinate1= " + itemDataDict['coordinate1']
        #     dataTreeView.AppendItem(viewerNode, coordinate_display, -1, -1, treeItemData)

        for i in range(1,7):
            coordinate = "coordinate" + str(i)
            coordinate_same_as = "coordinate" + str(i) + "_same_as"
            if itemDataDict.get(coordinate) != None:
                coordinate_display = coordinate + "=" + itemDataDict[coordinate]
                newTreeItem = QTreeWidgetItem(viewerNode, [coordinate_display])
                newTreeItem.itemVIZData = treeItemData
            if itemDataDict.get(coordinate_same_as) != None:
                coordinate_display = coordinate_same_as + "=" + itemDataDict[coordinate_same_as]
                newTreeItem = QTreeWidgetItem(viewerNode, [coordinate_display])
                newTreeItem.itemVIZData = treeItemData

        doc_display = None

        if itemDataDict.get('documentation') != None:
            doc_display = "documentation= " + itemDataDict['documentation']
            newTreeItem = QTreeWidgetItem(viewerNode, [doc_display])
            newTreeItem.itemVIZData = treeItemData

class IMASPublicDataSource(IMASDataSource):

    def __init__(self, name, machineName, shotNumber, runNumber):
        IMASDataSource.__init__(self, name, None, None, shotNumber, runNumber, machineName)

    # Load IMAS data using IMAS api
    def load(self, view, occurrence=0, pathsList = None, async=True):
        print ("Loading data using UDA")
        #view.log.info('Loading ' + view.IDSNameSelected + ' IDS...')
        self.generatedDataTree = GeneratedClassFactory(self, view, occurrence, pathsList, async).create()
        if self.ids == None:
            self.ids = imas.ids(self.shotNumber, self.runNumber, 0, 0)
            self.ids.open_public(self.machineName)

        self.generatedDataTree.ids = self.ids
        view.dataCurrentlyLoaded = True
        view.idsAlreadyFetched[view.IDSNameSelected] = 1

        if async == True:
            self.generatedDataTree.start()  # This will call asynchroneously the get() operation for fetching IMAS data
        else:
            self.generatedDataTree.run()  # This will call the get() operation for fetching IMAS data

    # This defines the unique key attached to each data which can be plotted
    def dataKey(self, nodeData):
        return self.name + "::" + self.machineName + "::" + str(self.shotNumber) + "::" + str(self.runNumber) + '::' + nodeData['Path']

    def getShortLabel(self):
        return self.machineName + ":" + str(self.shotNumber) + ":" + str(self.runNumber)
