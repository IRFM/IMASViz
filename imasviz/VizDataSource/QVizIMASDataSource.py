# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
import os
import logging
import imas
from PySide6.QtWidgets import QProgressBar
from imasviz.VizDataAccess.QVizIDSViewParser import QVizIDSViewParser
from imasviz.VizDataSource.QVizDBEntryRegistry import QVizDBEntryRegistry
from imasviz.VizUtils import QVizGlobalValues, QVizPreferences
from PySide6.QtCore import QRunnable, Slot, QThreadPool
from PySide6.QtCore import QObject, Slot, Signal, QThread


def caseLabel(uri, legacy_attributes=None):
    """Short human readable name for the case a source points to.

    Used in curve legends, where the whole IMAS URI used to be embedded and made
    the legend unreadable. Both URI spellings are understood: the parameter form
    (database=…;shot=…;run=…) and the path form (…/<db>/<dd>/<shot>/<run>).
    Falls back to the URI itself when neither can be read, so nothing is lost.
    """
    attributes = legacy_attributes or {}
    database = attributes.get('database_name') or attributes.get('database')
    shot = attributes.get('shot')
    run = attributes.get('run')

    if database is None or shot is None:
        database, shot, run = _readCaseFromUri(uri)

    if database is None or shot is None:
        return uri
    return '{} {}.{}'.format(database, shot, 0 if run is None else run)


def _readCaseFromUri(uri):
    parameters = {}
    question = uri.find('?')
    if question != -1:
        for term in uri[question + 1:].split(';'):
            if '=' in term:
                key, value = term.split('=', 1)
                parameters[key] = value

    if 'path' in parameters:
        parts = [part for part in parameters['path'].rstrip('/').split('/') if part]
        if len(parts) >= 4:
            return parts[-4], parts[-2], parts[-1]
        return None, None, None

    return (parameters.get('database'), parameters.get('shot'),
            parameters.get('run'))


class QVizIMASDataSource:

    # A source only ever reads a case; writing one happens through a separate
    # entry of its own (QVizDataTreeView.exportToLocal).
    MODE = 'r'

    def __init__(self, name, uri):
        self.generatedDataTree = None
        self.progressBar = None
        self.name = name
        self.uri = uri
        self.data_dictionary_version = None
        # Pins the data dictionary used to open the entry, for cases written
        # with another version than the one the Access Layer loads by default.
        self.dd_version = None
        self.al_version = self.getVersion()
        self.legacy_attributes = {} #used only for AL4

    @property
    def db_entry(self):
        """The entry open for this case, None while nobody holds one.

        Read through the registry instead of owned here: an entry built from an
        URI cannot be re-opened once closed, so a source keeping its own
        reference around ends up handing out a handle nobody can use.
        """
        return QVizDBEntryRegistry.entry(self.uri, self.MODE, self.dd_version)

    @property
    def data_entries(self):
        """IDS instances loaded from this case, shared with its other users.

        Keyed IDSName/occurrence. The dictionary belongs to the registry record,
        so it outlives both this source and the entry it was read through: an
        entry loads whole IDSs in memory. forget_case() drops it.
        """
        return QVizDBEntryRegistry.ids_cache(self.uri, self.MODE, self.dd_version)

    @staticmethod
    def getVersion():
        imas_prefix = os.environ.get('AL_VERSION')
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
        self.generatedDataTree = QVizIDSViewParser(self.uri, dataTreeView, IDSName,
                                                   occurrence, viewLoadingStrategy,
                                                   asynch)
        self.generatedDataTree.setProgressBar(self.progressBar)
        self.generatedDataTree.dataSource = self

        worker = Worker('Loading', self.generatedDataTree)

        self.threadpool = QThreadPool()
        self.threadpool.start(worker)

    def createDBEntry(self, mode=None):
        """Builds an entry on this case and returns it; it is not kept here."""
        if QVizIMASDataSource.getVersion()==4:
            if self.legacy_attributes is None or len(self.legacy_attributes) == 0:
                raise ValueError('No legacy parameters available.')

            user_name = self.legacy_attributes['user']
            shot = self.legacy_attributes['shot']
            run = self.legacy_attributes['run']
            db_name = self.legacy_attributes['database']
            data_version = self.legacy_attributes['version']
            backend_id = self.legacy_attributes['backend_id']

            entry = imas.DBEntry(backend_id, db_name, shot, run, user_name, data_version)
        elif QVizIMASDataSource.getVersion()==5:
            if mode is None:
                raise ValueError("Unspecified mode argument for createDBEntry()")
            # A case may have been written with a data dictionary other than the
            # one the Access Layer loads by default; IMAS-Python refuses to read
            # an IDS across a DD major version, so the pin has to be given here.
            if self.dd_version:
                entry = imas.DBEntry(self.uri, mode,
                                     dd_version=self.dd_version)
            else:
                entry = imas.DBEntry(self.uri, mode)
        else:
            raise ValueError("Unknown Access Layer version")
        return entry

    def open(self):
        """Takes a reference on the entry for this case, opening the case when
        nobody holds it yet. Must be paired with close().
        """
        try:
            QVizDBEntryRegistry.acquire(
                self.uri, self.MODE, self.dd_version, build=self.buildEntry)
            return 0
        except BaseException as e:
            print(e)
            #logging.getLogger("logPanel").error(str(e))
            raise ValueError(e)

    def buildEntry(self):
        """Builds the entry the registry will share, already usable.

        An AL5 entry opens at construction and refuses a second open(); an AL4
        entry has to be opened explicitly. This runs once per case, not once
        per IDS, which is what used to make the second IDS of a shot view fail.
        """
        version = QVizIMASDataSource.getVersion()
        if version == 4:
            entry = self.createDBEntry()
            status, idx = entry.open()
            if status != 0:
                raise ValueError("An error has occured while opening URI: " + self.uri + ".")
        elif version == 5:
            entry = self.createDBEntry(self.MODE)
        else:
            raise ValueError("Unknown Access Layer version")
        return entry

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
        """Hands our reference back; whoever drops the last one closes the case.

        Nothing is remembered here: db_entry reads the registry, so the entry
        disappears from this source as soon as the last reference is gone.
        Keeping a closed entry around made the next open() try to re-open it,
        which IMAS-Python refuses for an entry built from an URI.
        """
        QVizDBEntryRegistry.release(self.uri, self.MODE, self.dd_version)

    def forget_case(self):
        """Forgets this case and the IDS instances loaded from it.

        A shot view calls it when it goes away, releasing the reference it held
        on the case. Until then the loaded IDSs stay in memory, as they did when
        each data source owned its own cache.
        """
        return QVizDBEntryRegistry.drop(self.uri, self.MODE, self.dd_version)

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
        return caseLabel(self.uri, getattr(self, 'legacy_attributes', None))

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