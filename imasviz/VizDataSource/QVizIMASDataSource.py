# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

import os
import logging
import imas
from PySide6.QtWidgets import QProgressBar
from imasviz.VizDataAccess.VizCodeGenerator.QVizGeneratedClassFactory import QVizGeneratedClassFactory
from imasviz.VizUtils import QVizGlobalValues, QVizPreferences
from PySide6.QtCore import QRunnable, Slot, QThreadPool
from PySide6.QtCore import QObject, Slot, Signal, QThread

class QVizIMASDataSource:

    def __init__(self, name, uri):
        self.generatedDataTree = None
        self.progressBar = None
        self.name = name
        self.uri = uri
        self.data_entries = {}  # key = IDSName/occurrence, value = IDS data instance
        self.db_entry = None
        self.data_dictionary_version = None
        self.al_version = self.getVersion()
        self.legacy_attributes = {} #used only for AL4

    @staticmethod
    def getVersion():
        imas_prefix = os.environ.get('UAL_VERSION')
        if imas_prefix is None:
           raise ValueError('Unable to set the version used by the IMAS Access Layer')
        splits = imas_prefix.split("-")
        full_al_version = splits[0]
        splits2 = full_al_version.split(".")
        major_version = splits2[0]
        #print('major_version=', major_version)
        return int(major_version)

    @staticmethod
    def build_legacy_uri(backend_id, shot, run, user_name, 
    db_name, data_version, options):
        from imas import _al_lowlevel as ll
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

    
    @staticmethod
    def build_uri(backend_id, shot, run, user_name, 
    db_name, data_version, options):
        legacy_attributes = {}
        if QVizIMASDataSource.getVersion()==4:
            backend = ''
            if backend_id == 13:
                backend = 'hdf5'
            elif backend_id == 12:
                backend = 'mdsplus'
            else:
                raise ValueError("Unknown backend")

            legacy_attributes['user'] = user_name
            legacy_attributes['shot'] = int(shot)
            legacy_attributes['run'] = int(run)
            legacy_attributes['database'] = db_name
            legacy_attributes['version'] = str(data_version)
            legacy_attributes['backend_id'] = backend_id
            legacy_uri = "imas:" + backend + "?" + "user=" + user_name + ";shot=" + str(shot) + ";run=" + str(run) + ";database=" + db_name + ";version=" + data_version
            return (legacy_uri, legacy_attributes)
        elif QVizIMASDataSource.getVersion()==5:
            uri = QVizIMASDataSource.build_legacy_uri(backend_id, shot, run, user_name, db_name, data_version, options)
            return (uri, {})
        else:
            raise ValueError("Unknown Access Layer version")
        

    # Load IMAS data using IMAS api
    def load(self, dataTreeView, IDSName, occurrence=0, viewLoadingStrategy=None, asynch=True):

        self.progressBar = QProgressBar()
        self.progressBar.setWindowTitle("Loading '" + IDSName + "'...")

        self.progressBar.setMaximum(0)
        self.progressBar.setMinimum(0)
        self.progressBar.setGeometry(100, 150, 500, 25)
        self.progressBar.show()
        asynch = False
        self.generatedDataTree = \
            QVizGeneratedClassFactory(self, dataTreeView, IDSName,
                                      occurrence, viewLoadingStrategy,
                                      asynch).create(self.progressBar)
        if self.generatedDataTree is None:
            raise ValueError("Code generation issue detected !!")

        self.generatedDataTree.dataSource = self

        worker = Worker('Loading', self.generatedDataTree)

        self.threadpool = QThreadPool()
        self.threadpool.start(worker)

    def createDBEntry(self, mode=None):
        if QVizIMASDataSource.getVersion()==4:
            if self.legacy_attributes is None or len(self.legacy_attributes) == 0:
                raise ValueError('No legacy parameters available.')

            user_name = self.legacy_attributes['user']
            shot = self.legacy_attributes['shot']
            run = self.legacy_attributes['run']
            db_name = self.legacy_attributes['database']
            data_version = self.legacy_attributes['version']
            backend_id = self.legacy_attributes['backend_id']

            self.db_entry = imas.DBEntry(backend_id, db_name, shot, run, user_name, data_version)
        elif QVizIMASDataSource.getVersion()==5:
            if mode is None:
                raise ValueError("Unspecified mode argument for createDBEntry()")
            self.db_entry = imas.DBEntry(self.uri, mode)
        else:
            raise ValueError("Unknown Access Layer version")

    def open(self):
        try:
            if QVizIMASDataSource.getVersion()==4:
                if self.db_entry is None:
                    self.createDBEntry()

            elif QVizIMASDataSource.getVersion()==5:
                if self.db_entry is None:
                    self.createDBEntry('r')

            status, idx = self.db_entry.open()
            
            if status != 0:
                raise ValueError("An error has occured while opening URI: " + self.uri + ".")
            return status
        except BaseException as e:
            print(e)
            #logging.getLogger("logPanel").error(str(e))
            raise ValueError(e)

    def get(self, IDSName, occurrence):
        try:
            key = IDSName + "/" + str(occurrence)
            if not key in self.data_entries:
                logging.getLogger(self.uri).info("Loading '" + IDSName + "'" + " with occurrence " + str(occurrence))
                ids_instance = self.db_entry.get(IDSName, occurrence)
                self.data_entries[key] = ids_instance

            return self.data_entries[key]
        except BaseException as e:
            logging.getLogger("logPanel").error(str(e))
        
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

    def containsData(self, node):
        ret = False

        maxOccurrences = eval("imas." + node.getIDSName() + "().getMaxOccurrences()")

        for occurrence in range(0, maxOccurrences):
            node.setAvailableIDSData(occurrence, 0)
            try:
                ids_properties = eval("self.db_entry.partial_get('" + node.getIDSName() + "', 'ids_properties', occurrence)")
                ht = ids_properties.homogeneous_time
                if ht == 0 or ht == 1 or ht == 2:
                    logging.getLogger(self.uri).info("Found data for occurrence " + str(occurrence) + " of " + node.getIDSName() + " IDS...")
                    node.setHomogeneousTime(ht)
                    node.setAvailableIDSData(occurrence, 1)
                    self.data_dictionary_version = ids_properties.version_put.data_dictionary
                    ret = True
            except Exception as e:
                print(e)
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

    def exportToLocal(self, exported_db_entry):
        """Export specified IDS to a new separate IDS.

        Arguments:
            exported_db_entry (object) : imas.DBEntry object
        """
        i = 0
        for key in self.data_entries:
            splits = key.split("/")
            #IDSName = splits[0]
            occurrence = int(splits[1])
            ids_instance = self.data_entries[key]
            exported_db_entry.put(ids_instance, occurrence)
            i+=1

class Worker(QRunnable):
    
    finished = Signal()
    progress = Signal(int)
    
    def __init__(self, name, generatedDataTree):
       super(Worker, self).__init__()

       self.name = name
       self.generatedDataTree = generatedDataTree

    def run(self):
        """Long-running task."""
        self.generatedDataTree.run()
        #self.finished.emit()