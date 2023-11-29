import os
import logging
import imas
from PySide6.QtWidgets import QProgressBar
from imasviz.VizDataAccess.VizCodeGenerator.QVizGeneratedClassFactory import QVizGeneratedClassFactory
from imasviz.VizUtils import QVizGlobalValues, QVizPreferences
from imas import _al_lowlevel as ll


class QVizIMASDataSource:

    def __init__(self, name, uri):
        self.generatedDataTree = None
        self.progressBar = None
        self.name = name
        self.uri = uri
        self.data_entries = {}  # key = IDSName/occurrence, value = IDS data instance
        # data_dictionary_version will be initialized only when loading
        # the first IDS (currently, it is not possible to get the DD version
        # from the AL at the data entry level, see IMAS-2835 for details

        self.db_entry = None
        self.data_dictionary_version = None

    @staticmethod
    def defaultBackend():
        backend = os.getenv('IMAS_AL_DEFAULT_BACKEND')
        if backend is None:
            return imas.imasdef.MDSPLUS_BACKEND
        return int(backend)

    @staticmethod
    def fallbackBackend():
        backend = os.getenv('IMAS_AL_FALLBACK_BACKEND')
        if backend is None:
            return NO_BACKEND
        return int(backend)

    @staticmethod
    def build_legacy_uri(backend_id, shot, run, user_name, 
    db_name, data_version, options):
        status, uri = ll.al_build_uri_from_legacy_parameters(
            backend_id,
            shot,
            run,
            user_name,
            db_name,
            data_version,
            options,
        )
        if status != 0:
            raise ValueError("Error calling al_build_uri_from_legacy_parameters(...)")
        return uri

    # Load IMAS data using IMAS api
    def load(self, dataTreeView, IDSName, occurrence=0, viewLoadingStrategy=None, asynch=True):

        self.progressBar = QProgressBar()
        self.progressBar.setWindowTitle("Loading '" + IDSName + "'...")

        self.progressBar.setMaximum(0)
        self.progressBar.setMinimum(0)
        self.progressBar.setGeometry(100, 150, 500, 25)
        self.progressBar.show()

        self.generatedDataTree = \
            QVizGeneratedClassFactory(self, dataTreeView, IDSName,
                                      occurrence, viewLoadingStrategy,
                                      asynch).create(self.progressBar)
        if self.generatedDataTree is None:
            raise ValueError("Code generation issue detected !!")

        # load_data = True
        # if self.data_entries.get(occurrence) is None:
        #     major_version = os.environ["IMAS_MAJOR_VERSION"]
        #     self.data_entries[occurrence] = imas.DBEntry(self.uri, 'r')
        #     status, idx = self.data_entries[occurrence].open()
        #     if status != 0:
        #         raise valueError("Unable to open pulse file with URI: " + uri)

        # if IDSName in self.loaded_ids:
        #     load_data = False
        # else:
        #     load_data = True

        #self.generatedDataTree.loadData = load_data # Do not call IMAS GET(), data are already loaded in memory
        self.generatedDataTree.dataSource = self

        if asynch:
            # This will call asynchroneously the get() operation for fetching IMAS data
            self.generatedDataTree.start()
        else:
            # This will call the get() operation for fetching IMAS data
            self.generatedDataTree.run()

        #self.loaded_ids.append(IDSName)

    @staticmethod
    def try_to_open(uri):
        db_entry = imas.DBEntry(uri, 'r')
        status, idx = db_entry.open()
        db_entry.close()
        return status

    def open(self):
        if self.db_entry is None:
            self.db_entry = imas.DBEntry(self.uri, 'r')
        status, idx = self.db_entry.open()
        return status

    def get(self, IDSName, occurrence):
        key = IDSName + "/" + str(occurrence)
        if not key in self.data_entries:
            logging.info("Loading '" + IDSName + "'" + " with occurrence " + str(occurrence))
            ids_instance = self.db_entry.get(IDSName, occurrence)
            self.data_entries[key] = ids_instance
        return self.data_entries[key]
        
    def remove_entry(self, IDSName, occurrence):
        key = IDSName + "/" + str(occurrence)
        if self.data_entries.get(key) is not None:
            del self.data_entries[key]

    def close(self):
        if self.db_entry is not None:
            self.db_entry.close()

    # Check if the data for the given IDS exists
    def exists(self, IDSName=None):
        return True

    def containsData(self, node, data_entry):
        ret = False
        #logging.info("Searching available data in all occurrences of " +
        #             node.getIDSName() + " IDS...")

        maxOccurrences = eval("imas." + node.getIDSName() + "().getMaxOccurrences()")

        for occurrence in range(0, maxOccurrences):
            #logging.info("Searching for occurrence: " + str(occurrence) + "...")
            node.setAvailableIDSData(occurrence, 0)
            try:
                ids_properties = eval("data_entry.partial_get('" + node.getIDSName() + "', 'ids_properties', occurrence)")
                ht = ids_properties.homogeneous_time
                if ht == 0 or ht == 1 or ht == 2:
                    logging.info("Found data for occurrence " +
                                 str(occurrence) + " of " + node.getIDSName() +
                                 " IDS...")
                    node.setHomogeneousTime(ht)
                    node.setAvailableIDSData(occurrence, 1)
                    self.data_dictionary_version = ids_properties.version_put.data_dictionary
                    ret = True
                # elif occurrence == 0:
                # break the loop as soon as occurrence 0 is empty
                #    break
            except Exception as e:
                print(e)
        #logging.info("Data search ended.")
        return ret

    def dataKey(self, vizTreeNode):
        """Defines the unique key attached to each data which can be plotted.
        """
        return self.name + "::" + self.uri + '::' + vizTreeNode.getPath() + '::' + str(vizTreeNode.getOccurrence())

    def dataKey2(self, figureKey):
        """Defines the unique key attached to a figure
        """
        return self.name + "::" + self.uri + '::' + str(figureKey)

    def getShortLabel(self):
        return self.uri

    def getLongLabel(self):
        return "URI:" + self.uri

    def getKey(self):
        return self.getLongLabel()

    def getName(self):
        return self.getShortLabel()

    def exportToLocal(self, dataTreeView, exported_db_entry):
        """Export specified IDS to a new separate IDS.

        Arguments:

            dataTreeView (QTreeWidget) :
            exported_db_entry (object) : imas.DBEntry object
        """

        for db in dataTreeView.ids_roots_occurrence:
            # Extract IDS name and occurrence
            idsName, occurrence = db.split("/")
            ids_instance = dataTreeView.ids_roots_occurrence[db]

            # Run the export command
            logging.info("Calling IMAS put() for IDS " + idsName +
                         " occurrence " + str(occurrence) + ".")
            # Putting to occurrence
            exported_db_entry.put(ids_instance, occurrence)

        exported_db_entry.close()
