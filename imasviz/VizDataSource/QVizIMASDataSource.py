import os
import logging
import imas
from PyQt5.QtWidgets import QProgressBar
from imasviz.VizDataAccess.VizCodeGenerator.QVizGeneratedClassFactory import QVizGeneratedClassFactory
from imasviz.VizUtils import QVizGlobalValues

class QVizIMASDataSource:

    def __init__(self, name, userName, imasDbName, shotNumber, runNumber, machineName=None):
        self.name = name
        self.userName = userName
        self.imasDbName = imasDbName
        self.shotNumber = int(shotNumber)
        self.runNumber = int(runNumber)
        self.machineName = machineName
        self.ids = {}  # key = occurrence, value = ids object
        # data_dictionary_version will be initialized only when loading
        # the first IDS (currently, it is not possible to get the DD version
        # from the AL at the data entry level, see IMAS-2835 for details
        self.data_dictionary_version = None

    # Load IMAS data using IMAS api
    def load(self, dataTreeView, IDSName, occurrence=0, loadingStrategy=None, asynch=True):

        self.progressBar = QProgressBar()
        self.progressBar.setWindowTitle("Loading '" + IDSName + "'...")

        self.progressBar.setMaximum(0)
        self.progressBar.setMinimum(0)
        self.progressBar.setGeometry(100, 150, 500, 25)
        self.progressBar.show()

        self.generatedDataTree = \
            QVizGeneratedClassFactory(self, dataTreeView, IDSName,
                                      occurrence, loadingStrategy,
                                      asynch).create(self.progressBar)
        if self.generatedDataTree is None:
            raise ValueError("Code generation issue detected !!")

        if self.ids.get(occurrence) is None:
            self.ids[occurrence] = imas.ids(self.shotNumber, self.runNumber,
                                            0, 0)
            v = os.environ["IMAS_MAJOR_VERSION"]
            self.ids[occurrence].open_env(self.userName,
                                          self.imasDbName,
                                          os.environ["IMAS_MAJOR_VERSION"])
            if self.ids[occurrence].expIdx == -1:
                raise ValueError("Can not open shot " + str(self.shotNumber) +
                                 " from data base " + self.imasDbName +
                                 " of user " + self.userName)

        self.generatedDataTree.ids = self.ids[occurrence]

        if asynch:
            # This will call asynchroneously the get() operation for fetching
            # IMAS data
            self.generatedDataTree.start()
        else:
            # This will call the get() operation for fetching IMAS data
            self.generatedDataTree.run()

    @staticmethod
    def try_to_open(imasDbName, userName, shotNumber, runNumber,
                    imas_major_version='3'):
        ids = imas.ids(shotNumber, runNumber, 0, 0)
        try:
            ids.open_env(userName, imasDbName, imas_major_version)
            ids.close()
        except Exception:
            raise ValueError("Can not open shot " + str(shotNumber) +
                             "  from data base " + imasDbName + " of user " +
                             userName + ".")

    @staticmethod
    def try_to_open_uda_datasource(machineName, shotNumber, runNumber):
        ids = imas.ids(shotNumber, runNumber, 0, 0)
        ids.open_public(machineName)
        if (ids.expIdx == -1):
            raise ValueError("Can not open shot " + str(shotNumber) +
                             "  from " + machineName)
        else:
            ids.close()

    # Check if the data for the given IDS exists
    def exists(self, IDSName):
        return True

    def createImasDataEntry(self):
        return imas.ids(self.shotNumber, self.runNumber, 0, 0)

    def open(self, imas_entry):
        imas_major_version = os.environ['IMAS_MAJOR_VERSION']
        imas_entry.open_env(self.userName, self.imasDbName, imas_major_version)

    def close(self, imas_entry):
        imas_entry.close()

    def getImasEntry(self, occurrence):
        return self.ids.get(occurrence)

    def containsData(self, node, imas_entry):
        ret = False
        logging.info("Searching available data in all occurrences of " +
                     node.getIDSName() + " IDS...")
        for occurrence in range(0, QVizGlobalValues.MAX_NUMBER_OF_IDS_OCCURRENCES):
            logging.info("Searching for occurrence: " + str(occurrence) +
                         "...")
            node.setAvailableIDSData(occurrence, 0)
            try:
                ids_properties = eval("imas_entry." + node.getIDSName() +
                                      ".partialGet('ids_properties', occurrence)")
                ht = ids_properties.homogeneous_time
                if ht == 0 or ht == 1 or ht == 2:
                    logging.info("Found data for occurrence " +
                                 str(occurrence) + " of " + node.getIDSName() +
                                 " IDS...")
                    node.setHomogeneousTime(ht)
                    node.setAvailableIDSData(occurrence, 1)
                    self.data_dictionary_version = ids_properties.version_put.data_dictionary
                    ret = True
                #elif occurrence == 0:
                    # break the loop as soon as occurrence 0 is empty
                #    break
            except:
                pass
        logging.info("Data search ended.")
        return ret

    def dataKey(self, vizTreeNode):
        """Defines the unique key attached to each data which can be plotted.
        """
        return self.name + "::" + self.imasDbName + "::" + \
            str(self.shotNumber) + "::" + str(self.runNumber) + '::' + \
            vizTreeNode.getPath() + '::' + str(vizTreeNode.getOccurrence())

    def getShortLabel(self):
        return self.userName + ":" + self.imasDbName + ":" + \
            str(self.shotNumber) + ":" + str(self.runNumber)

    def getLongLabel(self):
        return "User:" + self.userName + " Database:" + self.imasDbName + \
            " Shot:" + str(self.shotNumber) + " Run:" + str(self.runNumber)

    def getKey(self):
        return self.getLongLabel()

    def getName(self):
        return self.getShortLabel()

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

            if os.getenv('IMAS_PREFIX') != None and \
                    'IMAS' in os.getenv('IMAS_PREFIX'):
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
            eval("self.ids[" + str(occurrence) + "]." + idsName +
                 ".put(" + str(occurrence) + ")")

        exported_ids.close()
