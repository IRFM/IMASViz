import os
import imas
import traceback, sys
from PyQt5.QtWidgets import QTreeWidgetItem
from imasviz.VizDataAccess.VizCodeGenerator.QVizGeneratedClassFactory import QVizGeneratedClassFactory
from imasviz.VizUtils.QVizGlobalValues import GlobalColors
from imasviz.VizGUI.VizTreeView.QVizTreeNode import QVizTreeNode

class QVizIMASDataSource:

    def __init__(self, name, userName, imasDbName, shotNumber, runNumber, machineName=None):
        self.name = name
        self.userName =  userName
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
        #dataTreeView.idsAlreadyFetched[dataTreeView.IDSNameSelected[occurrence]] = 1
        dataTreeView.log.info('Loading occurrence ' + str(int(occurrence)) + ' of IDS ' + IDSName + '...')

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

    def containsData(self, IDSName):
        imas_entry = imas.ids(self.shotNumber, self.runNumber, 0, 0)
        try:
            imas_major_version = os.environ['IMAS_MAJOR_VERSION']
            imas_entry.open_env(self.userName, self.imasDbName, imas_major_version)
            ids_properties = eval("imas_entry." + IDSName + ".partialGet('ids_properties')")
            imas_entry.close()
            ht = ids_properties.homogeneous_time
            if ht != 0 and ht != 1:
                return False
        except:
            #traceback.print_exc(file=sys.stdout)
            return False

        return True

    # Define the color of a node which contains a signal
    def colorOf(self, signalNode, obsolescent=None):
        ids = self.ids[signalNode['occurrence']] #@UnusedVariable
        if signalNode['data_type'] == 'FLT_1D' or signalNode['data_type'] == 'flt_1d_type':

            # And error occurs for non-homogeneous cases (time array is
            # different or empty). This is 'solved' with the below fix using
            # 'e' variable
            e = eval('ids.' + signalNode['dataName'])
            if e is None or e.all() is None:
                return GlobalColors.BLACK

            # if len(eval(signalNode['dataName'])) == 0: #empty (signals) arrays appear in black
            if len(eval('ids.' + signalNode['dataName'])) == 0: #empty (signals) arrays appear in black
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
    def dataNameInPopUpMenu(self, dataDict):
        #dico = dataDict.GetData()
        if 'dataName' in dataDict:
            return dataDict['dataName']
        return None

    def treeDisplayedNodeName(self, dataElement):
        """The displayed name of the node in DTV.
        """
        # name = str(dataElement.find('name').text) # Full path
        name = dataElement.attrib['name']
        return name

    # This defines the unique key attached to each data which can be plotted
    def dataKey(self, nodeData):
        return self.name + "::" + self.imasDbName + "::" + str(self.shotNumber) + "::" \
               + str(self.runNumber) + '::' + nodeData['Path'] + '::' + str(nodeData['occurrence'])

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
                newTreeItem = QVizTreeNode(viewerNode, [coordinate_display])
            if itemDataDict.get(coordinate_same_as) != None:
                coordinate_display = coordinate_same_as + "=" + itemDataDict[coordinate_same_as]
                newTreeItem = QVizTreeNode(viewerNode, [coordinate_display])

        doc_display = None

        if itemDataDict.get('documentation') != None:
            doc_display = "documentation= " + itemDataDict['documentation']
            newTreeItem = QVizTreeNode(viewerNode, [doc_display])

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
            dataTreeView.log.info("Calling IMAS put() for IDS " + idsName +
                                  " occurrence " + str(occurrence) + ".")
            # Putting to occurrence
            eval("self.ids[" + str(occurrence) + "]."  + idsName + ".put(" + str(
                occurrence) +
                 ")")

        exported_ids.close()


