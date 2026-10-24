# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
import logging
from functools import partial
import imas
from PySide6.QtWidgets import QProgressBar
from imasviz.VizDataAccess.QVizIDSViewParser import QVizIDSViewParser
from imasviz.VizDataSource.QVizDBEntryRegistry import QVizDBEntryRegistry
from imasviz.VizUtils import QVizGlobalValues, QVizPreferences


def caseLabel(uri):
    """Short human readable name for the case a source points to.

    Used in curve legends, where the whole IMAS URI used to be embedded and made
    the legend unreadable. Both URI spellings are understood: the parameter form
    (database=…;shot=…;run=…) and the path form (…/<db>/<dd>/<shot>/<run>).
    Falls back to the URI itself when neither can be read, so nothing is lost.

    The Access Layer 4 'legacy parameters' used to be read first, because that
    is what an AL4 entry was built from; nothing builds an entry from them any
    more, so the URI is the one place the case is spelled.
    """
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


def caseUri(backendId, user, database, shot, run, dataVersion, options=''):
    """Spell the URI of a case from the parameters the user gives.

    This is the inverse of `_readCaseFromUri`, and it is the only place that
    spells it. The Access Layer used to be asked for it through
    ``_al_lowlevel.al_build_uri_from_legacy_parameters``; that module is not in
    the Access Layer bindings this application runs on (IMAS-Python 2.3.0), so
    every call answered ``ImportError`` -- including the first statement of the
    *Export to IDS* handler and the command line's ``-u -d -s -r -b`` path. The
    spelling here is the one the Access Layer documents, and it is the one the
    cases on disk are opened with.

    `dataVersion` is the version of the **data**, not of the Access Layer: it
    becomes the directory the pulse is stored under,
    ``<database>/<version>/<shot>/<run>``, so a case written with the Access
    Layer's own major version lands where no reader looks for it.
    """
    backend = {13: 'hdf5', 12: 'mdsplus'}.get(backendId)
    if backend is None:
        raise ValueError('Unknown backend %r: HDF5 (13) or MDSplus (12).'
                         % (backendId,))
    if not dataVersion:
        raise ValueError('No data version given to build a case URI.')
    uri = 'imas:%s?user=%s;shot=%s;run=%s;database=%s;version=%s' % (
        backend, user, shot, run, database, dataVersion)
    if options:
        uri += ';' + options.lstrip(';')
    return uri


class QVizIMASDataSource:

    # A source only ever reads a case; writing one happens through a separate
    # entry of its own (QVizExportToIDS.openForWriting), built at the data
    # dictionary the exported IDSs were read at and never shared with this one.
    MODE = 'r'

    def __init__(self, name, uri):
        self.generatedDataTree = None
        # The walks this source started and has not finished. A parser is a
        # QThread, and a QThread whose Python wrapper dies while it runs takes
        # the process with it: `generatedDataTree` alone is one slot, so a
        # second load would drop the reference on a walk still reading the case.
        self.runningParsers = set()
        self.progressBar = None
        self.name = name
        self.uri = uri
        self.data_dictionary_version = None
        # Pins the data dictionary used to open the entry, for cases written
        # with another version than the one the Access Layer loads by default.
        self.dd_version = None

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
    def build_uri(backend_id, shot, run, user_name, db_name, data_version,
                  options):
        """The URI of a case, spelled from the five parameters the user gives.

        It used to answer a pair, `(uri, legacy_attributes)`: under Access Layer
        4 an entry could not be built from an URI at all, only from those five
        numbers. The major version the Access Layer reports here has been 5 on
        every stack this application has run on (AL_VERSION is 5.7.1 on the
        stack of the README), so that second answer was always an empty dict,
        and nothing built an entry from it.
        """
        return caseUri(backend_id, user_name, db_name, shot, run, data_version,
                       options)
        

    def load(self, dataTreeView, IDSName, occurrence=0, sliceSelection=None,
             asynch=True):
        """Walk one occurrence of one IDS and let the view build its tree.

        The walk runs in the parser's own thread when `asynch` is asked for, and
        hands the shadow tree to the frame with a Qt event; it runs here when it
        is not. Measured, this method overrode its own argument with
        `asynch = False` and then handed the walk to a fresh `QThreadPool` per
        load -- a pool the caller never sees and cannot wait on -- so the walk
        was off-thread while its result was applied to the tree directly, from
        that thread, instead of through the event the parser posts for it.
        """
        self.progressBar = QProgressBar()
        self.progressBar.setWindowTitle("Loading '" + IDSName + "'...")

        self.progressBar.setMaximum(0)
        self.progressBar.setMinimum(0)
        self.progressBar.setGeometry(100, 150, 500, 25)
        self.progressBar.show()

        self.generatedDataTree = QVizIDSViewParser(self.uri, dataTreeView, IDSName,
                                                   occurrence, sliceSelection,
                                                   asynch)
        self.generatedDataTree.setProgressBar(self.progressBar)
        self.generatedDataTree.dataSource = self

        # The load belongs to the view that asked for it: the view says whether
        # it is already building this occurrence, and the walk tells it when it
        # is done, on the thread the finished signal is delivered on.
        dataTreeView.beginLoad(IDSName, occurrence)
        parser = self.generatedDataTree
        if asynch:
            self.runningParsers.add(parser)
            parser.finished.connect(partial(self._loadFinished, dataTreeView,
                                            IDSName, occurrence, parser))
            parser.start()
        else:
            try:
                parser.run()
            finally:
                dataTreeView.endLoad(IDSName, occurrence)

    def _loadFinished(self, dataTreeView, IDSName, occurrence, parser):
        """Take a finished walk off the list of the ones held alive.

        Delivered on the thread that owns the view, which is where the tree it
        built belongs. The walk is dropped here rather than when `load` returns:
        the call returns as soon as the thread is started, and a parser garbage
        collected mid-walk is a crash, not a bug report.

        The bar goes down here too, whatever the walk met. It used to be taken
        down by the walk itself on the failure paths, which lost the thread -- a
        window closed from the thread that does not own it never comes back from
        `close()`, and with it go `finished`, the parser and the record that this
        occurrence is still being loaded. An accepted walk has its bar closed by
        the frame once the tree is drawn; closing it again here is harmless.
        """
        parser.closeProgressBar()
        self.runningParsers.discard(parser)
        dataTreeView.endLoad(IDSName, occurrence)

    def createDBEntry(self, mode):
        """Builds an entry on this case and returns it; it is not kept here.

        An URI is the whole description of a case. The five numbers Access Layer
        4 needed instead -- `imas.DBEntry(backend_id, db_name, shot, run, user,
        version)` -- went with the branch that asked `getVersion()` for them; on
        every stack this application has run on that answer was 5, so that
        branch had been unreachable here for as long as the Access Layer
        bindings have been IMAS-Python's.
        """
        # A case may have been written with a data dictionary other than the
        # one the Access Layer loads by default; IMAS-Python refuses to read
        # an IDS across a DD major version, so the pin has to be given here.
        if self.dd_version:
            return imas.DBEntry(self.uri, mode, dd_version=self.dd_version)
        return imas.DBEntry(self.uri, mode)

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

        An entry built from an URI opens at construction and refuses a second
        open(); under Access Layer 4 it had to be opened explicitly, which is
        what this method's version test was for. It runs once per case, not
        once per IDS, which is what used to make the second IDS of a shot view
        fail.
        """
        return self.createDBEntry(self.MODE)

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

    def dataKey(self, vizTreeNode):
        """Defines the unique key attached to each data which can be plotted.
        """
        return self.name + "::" + self.uri + '::' + vizTreeNode.getPath() + '::' + str(vizTreeNode.getOccurrence())

    def dataKey2(self, figureKey):
        """Defines the unique key attached to a figure
        """
        return self.name + "::" + self.uri + '::' + str(figureKey)

    def getShortLabel(self):
        return caseLabel(self.uri)

    def getLongLabel(self):
        return "URI:" + self.uri

    def getKey(self):
        return self.getLongLabel()

    def getName(self):
        return self.getShortLabel()
