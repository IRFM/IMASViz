import os, logging
import imas
import traceback, sys
from PyQt5.QtWidgets import QTreeWidgetItem
from imasviz.VizDataAccess.VizCodeGenerator.QVizGeneratedClassFactory import QVizGeneratedClassFactory
from imasviz.VizUtils.QVizGlobalValues import GlobalColors
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues
from imasviz.VizGUI.VizTreeView.QVizTreeNode import QVizTreeNode

class QVizIMASDataSource:

    def __init__(self, name, userName, imasDbName, shotNumber, runNumber, machineName=None):
        self.name = name
        self.userName = userName
        self.imasDbName = imasDbName
        self.shotNumber = int(shotNumber)
        self.runNumber = int(runNumber)
        self.machineName = machineName
        self.ids = {} #key = occurrence, value = ids object

    # Load IMAS data using IMAS api
    def load(self, dataTreeView, IDSName, occurrence=0, asynch=True):
        self.generatedDataTree = QVizGeneratedClassFactory(self, dataTreeView, IDSName, occurrence, asynch).create()
        if self.generatedDataTree == None:
            raise ValueError("Code generation issue detected !!")

        if self.ids.get(occurrence) is None:
            self.ids[occurrence] = imas.ids(self.shotNumber, self.runNumber, 0, 0)
            v = os.environ["IMAS_MAJOR_VERSION"]
            self.ids[occurrence].open_env(self.userName, self.imasDbName, os.environ["IMAS_MAJOR_VERSION"])
            if (self.ids[occurrence].expIdx == -1):
                raise ValueError("Can not open shot " + str(self.shotNumber) + "  from data base " + self.imasDbName + " of user " + self.userName)

        self.generatedDataTree.ids = self.ids[occurrence]

        if asynch:
            self.generatedDataTree.start() #This will call asynchroneously the get() operation for fetching IMAS data
        else:
            self.generatedDataTree.run()  #This will call the get() operation for fetching IMAS data

    @staticmethod
    def try_to_open(imasDbName, userName, shotNumber, runNumber, imas_major_version='3'):
        ids = imas.ids(shotNumber, runNumber, 0, 0)
        try:
            ids.open_env(userName, imasDbName, imas_major_version)
        except Exception:
            raise ValueError("Can not open shot " + str(shotNumber) +
                             "  from data base " + imasDbName + " of user " + userName + ".")

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

    def getImasEntry(self):
        return  imas.ids(self.shotNumber, self.runNumber, 0, 0)

    def open(self, imas_entry):
        imas_major_version = os.environ['IMAS_MAJOR_VERSION']
        imas_entry.open_env(self.userName, self.imasDbName, imas_major_version)

    def close(self, imas_entry):
        imas_entry.close()

    def containsData(self, IDSRootNode, imas_entry):
        containsData = False
        try:
            IDSRootNode.setForeground(0, GlobalColors.BLACK)  # Set tree item text color
            logging.info("Searching available data in all occurrences of " + IDSRootNode.getIDSName() + "IDS...")
            for occurrence in range(0, QVizGlobalValues.MAX_NUMBER_OF_IDS_OCCURRENCES):
                IDSRootNode.setAvailableIDSData(occurrence, False)
                #logging.info("Searching if available data in occurrence " + str(
                #    occurrence) + " of " + IDSRootNode.getIDSName() + "IDS...")
                logging.info("Searching for occurrence: " + str(occurrence) + "...")
                try:
                    ids_properties = eval("imas_entry." + IDSRootNode.getIDSName() + ".partialGet('ids_properties', occurrence)")
                    ht = ids_properties.homogeneous_time
                    if ht == 0 or ht == 1 or ht == 2:
                        containsData = True
                        logging.info("Found data for occurrence " + str(occurrence) + " of "+ IDSRootNode.getIDSName() + " IDS...")
                        IDSRootNode.setAvailableIDSData(occurrence, True)
                        # Set tree item text color
                        IDSRootNode.setForeground(0, GlobalColors.BLUE)
                except:
                    pass
            logging.info("Data search ended.")
        except:
            pass
        #IDSRootNode.setAvailableData(containsData)
        return containsData

    # Define the color of a node which contains a signal
    def colorOf(self, signalNode, obsolescent=None):
        ids = self.ids[signalNode.getOccurrence()] #@UnusedVariable
        if signalNode.is1DAndDynamic():

            # And error occurs for non-homogeneous cases (time array is
            # different or empty). This is 'solved' with the below fix using
            # 'e' variable
            e = eval('ids.' + signalNode.getDataName())
            if e is None or e.all() is None:
                return GlobalColors.BLACK

            # if len(eval(signalNode['dataName'])) == 0: #empty (signals) arrays appear in black
            if len(eval('ids.' + signalNode.getDataName())) == 0: #empty (signals) arrays appear in black
                if obsolescent is None or obsolescent is False:
                    return GlobalColors.BLACK
                elif obsolescent is True:
                    return GlobalColors.LIGHT_GREY
            else:
                if obsolescent is None or obsolescent is False:
                    return GlobalColors.BLUE  # non empty (signals) arrays appear in blue
                elif obsolescent is True:
                    return GlobalColors.CYAN

        elif signalNode.is0DAndDynamic():
            # And error occurs for non-homogeneous cases (time array is
            # different or empty). This is 'solved' with the below fix using
            # 'e' variable
            e = eval('ids.' + signalNode.getDataName())

            emptyField = False
            if signalNode.getDataType() == 'FLT_0D' or signalNode.getDataType() == 'flt_0d_type':
                if e == -9.0E40:
                    emptyField = True

            elif signalNode.getDataType() == 'INT_0D' or signalNode.getDataType() == 'int_0d_type':
                if e == -999999999:
                    emptyField = True

            if emptyField:  # empty (signals) arrays appear in black
                if obsolescent is None or obsolescent is False:
                    return GlobalColors.BLACK
                elif obsolescent is True:
                    return GlobalColors.LIGHT_GREY
            else:
                if obsolescent is None or obsolescent is False:
                    return GlobalColors.BLUE  # non empty (signals) arrays appear in blue
                elif obsolescent is True:
                    return GlobalColors.CYAN

        elif signalNode.is2DOrLarger():
            e = eval('ids.' + signalNode.getDataName())
            if e.shape[0] == 0:
                if obsolescent is None or obsolescent is False:
                    return GlobalColors.BLACK
                elif obsolescent is True:
                    return GlobalColors.LIGHT_GREY
            else:
                if obsolescent is None or obsolescent is False:
                    return GlobalColors.BLUE  # non empty (signals) arrays appear in blue
                elif obsolescent is True:
                    return GlobalColors.CYAN

        if obsolescent is None or obsolescent is False:
            return GlobalColors.BLACK
        elif obsolescent is True:
            return GlobalColors.LIGHT_GREY

    # Name of the data under the selected node
    # def dataNameInPopUpMenu(self, dataDict):
    #     if 'dataName' in dataDict:
    #         return dataDict['dataName']
    #     return None

    def treeDisplayedNodeName(self, dataElement):
        """The displayed name of the node in DTV.
        """
        # name = str(dataElement.find('name').text) # Full path
        return dataElement.attrib['name']

    # This defines the unique key attached to each data which can be plotted
    def dataKey(self, nodeData):
        return self.name + "::" + self.imasDbName + "::" + str(self.shotNumber) + "::" \
               + str(self.runNumber) + '::' + nodeData['Path'] + '::' + str(nodeData['occurrence'])

    def getShortLabel(self):
        return self.userName + ":" + self.imasDbName + ":" + str(self.shotNumber) + ":" + str(self.runNumber)


    def exportToLocal(self, dataTreeView, exported_ids):
        """Export specified IDS to a new separate IDS.

        Arguments:

            dataTreeView (QTreeWidget) :
            exported_ids (object)      : IDS object (A new IDS to which the
                                         export is to be done)
        """

        # List of loaded IDS roots with occurrences included (in form
        # 'magnetics/0')
        # list = dataTreeView.ids_roots_occurrence

        for db in dataTreeView.ids_roots_occurrence:
            # Extract IDS name and occurrence
            idsName, occurrence = db.split("/")

            if os.getenv('IMAS_PREFIX') != None and 'IMAS' in os.getenv('IMAS_PREFIX'):
                # Set the export command
                command2 = "self.ids[" + str(occurrence) + "]." + idsName + \
                          ".setExpIdx(exported_ids." + idsName + "._idx)"
            else:
                command2 = "self.ids[" + str(occurrence) + "]." + idsName + \
                           ".setExpIdx(exported_ids." + idsName + ".idx)"

            # Run the export command
            eval(command2)
            logging.info("Calling IMAS put() for IDS " + idsName +
                                  " occurrence " + str(occurrence) + ".")
            # Putting to occurrence
            eval("self.ids[" + str(occurrence) + "]."  + idsName + ".put(" + str(
                occurrence) +
                 ")")

        exported_ids.close()


