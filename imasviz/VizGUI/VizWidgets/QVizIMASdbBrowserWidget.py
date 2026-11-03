# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Signal, QObject, QThread
from PySide6.QtWidgets import QProgressBar
import sys
import os
import getpass
import glob
import logging
import threading
from threading import Thread, Condition
from functools import partial


# The two backend labels the Worker writes into the tree, and the id the rest
# of the application asks of the Access Layer for them. The same two numbers the
# command line takes after -b.
BACKENDS = {'HDF5': 13, 'MDS+': 12}


class QVizIMASdbBrowserWidget(QTreeWidget):
    """Set and populate QTreeWidget.
    """

    onItemDoubleClick = Signal()

    def __init__(self, parent):
        """
        Arguments:
            parent     (QWindow) : QVizDataTreeView parent.
        """

        super(QVizIMASdbBrowserWidget, self).__init__(parent)

        # Set QTreeWidget name
        self.setObjectName('IMASdbBrowserWidget')
        # Hide header
        self.setHeaderHidden(False)
        self.setHeaderLabels(['IMAS database browser'])
        tip = """
<html>
Browser through IMAS database displaying available cases for
given user. <br><br>
- <b> Double clicking</b> on the last tree view item (IDS run
parameter) will <b>set the selection</b> in the above
IDS parameters widgets (local data source parameters). <br><br>
- On setting a <b>different 'user name' in user textbox</b> and
confirming the change (either by pressing enter key or by
loosing focus on the textbox e.g. clicking anywhere else)
then the available <b>IDS cases for that user will be shown too</b>.
</html>
"""

        self.setToolTip(tip)
        self.setStatusTip(tip)

        self.activeUsername = None
        self.activeDatabase = None
        self.activeShot = None
        self.activeRun = None
        # The fifth thing a selection spells. It used to be absent from this
        # list and to appear only inside setActiveBackend, under the name
        # 'backend', so a browser that had not seen a run double clicked yet
        # answered AttributeError on getActiveBackend() -- which is what
        # GUIFrame.updateIDSparam asks first thing.
        self.activeBackend = None
        # A list to keep track of which databases had been shown and to
        # use it to avoid duplicates
        self.presentUserNameList = []

        # # Connect 'itemClicked' with the 'onLeftClickItem' function.
        # # On clicking on the QTreeWidgetItem (left click) the function will
        # # be run
        # self.itemClicked.connect(self.onLeftClickItem)

        # # Set action on double click on item
        self.itemDoubleClicked.connect(self.doubleClickHandler)
        
        self.addUserDB(getpass.getuser())
        self.setActiveUsername(getpass.getuser())
        
        self.progressBar = None


    def addUserDB(self, username):
        #logging.info("Populating database browser for user: " + username + "...")
        self.progressBar = QProgressBar()
        self.progressBar.setWindowTitle("Populating database browser for user: " + username + "...")

        self.progressBar.setMaximum(0)
        self.progressBar.setMinimum(0)
        self.progressBar.setGeometry(100, 150, 500, 25)
        self.progressBar.show()
        
        self.thread = QThread()
        self.worker = Worker(username, self.presentUserNameList)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(partial(self.addDB))
        self.thread.start()
        
        
    def addDB(self):
        if self.worker.rootUserItem is not None:
            self.addTopLevelItem(self.worker.rootUserItem)
            self.presentUserNameList.append(self.worker.username)
            #logging.info("End of populating database browser for user: " + self.worker.username + ".")
        #else:
        #    logging.info("No database found for user: " + worker.username + ".")
        if self.progressBar is not None:
           self.progressBar.hide()


    def doubleClickHandler(self, item, column_No):
        """Handler for double click on QTreeWidgetItem in QTreeWidget.

        Only a run number selects a case, and the five values the frame reads
        back are then set together. The signal used to be emitted whatever had
        been clicked: a double click on a shot, a database or a backend row
        left `activeDatabase`, `activeShot` and `activeRun` at None and the
        backend unset, and `GUIFrame.updateIDSparam` blanked its four text
        fields with those None values before dying on the fifth, outside the
        gesture that asked it.
        """
        labels = self._caseLabelsOf(item)
        if labels is None:
            logging.getLogger('logPanel').info(
                "Double clicking '%s' selects no case: only a run number, "
                "the last level of the browser, fills the IDS parameters above."
                % item.text(0))
            return

        username, backendLabel, database, shot, run = labels
        if backendLabel not in BACKENDS:
            logging.getLogger('logPanel').error(
                "Unknown backend '%s' under user '%s' in the database browser: "
                "it must be one of %s."
                % (backendLabel, username, ', '.join(sorted(BACKENDS))))
            return

        self.setActiveUsername(username)
        self.setActiveBackend(BACKENDS[backendLabel])
        self.setActiveDatabase(database)
        self.setActiveShot(shot)
        self.setActiveRun(run)
        self.onItemDoubleClick.emit()

    def _caseLabelsOf(self, item):
        """The five labels of the case a leaf spells; None when it is not one.

        The tree the Worker builds is five levels deep -- user, backend,
        database, shot, run -- and the handler used to walk exactly four
        `parent()` steps without looking at what it walked into, so a shallower
        tree answered AttributeError on `None.text(0)`.
        """
        if item.childCount() != 0:
            return None
        labels = []
        node = item
        while node is not None and len(labels) < 5:
            labels.append(node.text(0))
            node = node.parent()
        if node is not None or len(labels) < 5:
            return None
        return tuple(labels[::-1])

    def setActiveUsername(self, username):
        self.activeUsername = username

    def setActiveBackend(self, backend_id):
        """The backend of the selected case, by id: 13 (HDF5) or 12 (MDS+).

        It used to take the browser *label* and map it with two tests and no
        `else`, so any other label left the local `backend` unbound and the
        answer was UnboundLocalError -- measured with 'hdf5' (the label is
        case sensitive) and with 'ITER'.
        """
        if backend_id not in BACKENDS.values():
            raise ValueError('Unknown backend id %r: HDF5 (13) or MDSplus (12).'
                             % (backend_id,))
        self.activeBackend = backend_id

    def setActiveDatabase(self, db):
        self.activeDatabase = db

    def setActiveShot(self, shot):
        self.activeShot = shot

    def setActiveRun(self, run):
        self.activeRun = run

    def getActiveUsername(self):
        return self.activeUsername

    def getActiveBackend(self):
        return self.activeBackend

    def getActiveDatabase(self):
        return self.activeDatabase

    def getActiveShot(self):
        return self.activeShot

    def getActiveRun(self):
        return self.activeRun


# The local-case scanner. Pure on the filesystem (no Qt), so the legacy tree
# and the URI list of the start window are both built from one reading of
# "which local cases exist" and cannot drift apart on what they show.
def caseRootForUser(username):
    """The imasdb root holding this user's local cases, or None when it is unset.

    The same path the legacy browser walked, factored out so the URI list and
    the tree look at the same place: ``public`` under ``$IMAS_HOME/shared`` and
    a named user under their home. ``None`` is the refusal -- an unset
    ``IMAS_HOME`` (for ``public``) or ``HOME`` (for a user) answers an empty
    list later, not a NameError in the middle of the walk.
    """
    separator = os.path.sep
    if username == 'public':
        imas_home = os.environ.get('IMAS_HOME')
        if not imas_home:
            return None
        return imas_home + separator + 'shared' + separator + 'imasdb'
    home = os.environ.get('HOME')
    if not home:
        return None
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), home, '..'))
    return base + separator + username + separator + 'public' + separator + 'imasdb'


def _dirsUnder(folder):
    """The subdirectories of `folder`, sorted; [] when it is not a directory.

    Swallows the permissions and race errors a local walk can meet instead of
    propagating them out of a list the user is about to click on.
    """
    if not os.path.isdir(folder):
        return []
    try:
        names = [n for n in os.listdir(folder)
                 if os.path.isdir(os.path.join(folder, n))]
    except OSError:
        return []
    names.sort()
    return names


def hdf5Cases(imasdbPath, database):
    """The local HDF5 cases of `database`: one dict per run folder holding ``*.h5``.

    `database/<dataVersion>/<shot>/<run>` with the version left generic. The
    legacy browser hard-coded ``/3/``, so a case stored under another data
    version lived on disk and was invisible in the browser; the URI list keeps
    the same rule but does not lose it.
    """
    cases = []
    dbRoot = os.path.join(imasdbPath, database)
    for version in _dirsUnder(dbRoot):
        versionRoot = os.path.join(dbRoot, version)
        for shot in _dirsUnder(versionRoot):
            shotRoot = os.path.join(versionRoot, shot)
            for run in _dirsUnder(shotRoot):
                runFolder = os.path.join(shotRoot, run)
                try:
                    if glob.glob1(runFolder, '*.h5'):
                        cases.append({'shot': shot, 'run': run, 'path': runFolder})
                except glob.GlobError:
                    pass
    return cases


def mdsplusCases(imasdbPath, database):
    """The local MDS+ cases of `database`, read from the ``.datafile`` names.

    `database/3/<digit>/` holds the pulses whose run number is the digit's
    leading character followed by the last four characters of the name's last
    word; the rest of that word is the shot. A name that does not spell a case
    -- the bookkeeping files a database always carries -- is left out, not an
    exception raised into the list.
    """
    cases = []
    for digit in range(10):
        digitRoot = os.path.join(imasdbPath, database, '3', str(digit))
        if not os.path.isdir(digitRoot):
            continue
        try:
            names = sorted(f for f in os.listdir(digitRoot)
                           if f.endswith('.datafile'))
        except OSError:
            continue
        for name in names:
            head = name.split('.')[0]
            if '_' not in head:
                continue
            rest = head.split('_')[1]
            if len(rest) < 4:
                continue
            run = rest[-4:] if digit == 0 else str(digit) + rest[-4:]
            try:
                int(run)
            except ValueError:
                continue
            cases.append({'shot': rest[:-4], 'run': run})
    return cases


def localCases(root):
    """The local cases held under one imasdb root, flat and ordered.

    One dict per case, keyed ``backend, database, shot, run`` plus ``path``
    (HDF5 only), sorted by database with HDF5 ahead of MDS+ for a given
    database, then shot and run. That is the order the start window's list is
    drawn in, and it is the same reading the legacy tree applies -- so the two
    cannot name different cases for the same folder.
    """
    cases = []
    for database in _dirsUnder(root):
        for c in hdf5Cases(root, database):
            cases.append({'backend': 'HDF5', 'database': database,
                          'shot': c['shot'], 'run': c['run'], 'path': c['path']})
        for c in mdsplusCases(root, database):
            cases.append({'backend': 'MDS+', 'database': database,
                          'shot': c['shot'], 'run': c['run'], 'path': None})
    key = lambda c: (c['database'], 0 if c['backend'] == 'HDF5' else 1,
                     c['shot'], c['run'])
    return sorted(cases, key=key)


class Worker(QObject):

    finished = Signal()
    progress = Signal(int)
    
    def __init__(self, username, presentUserNameList):
       super(Worker, self).__init__()
       
       self.username = username
       self.presentUserNameList = presentUserNameList
       self.rootUserItem = None

    def run(self):
        """Long-running task."""
        self.addContentsForUsername()
        self.finished.emit()
        
    def found_mdsplus_pulse_files(self, db, imasdbPath):
       return bool(mdsplusCases(imasdbPath, db))

    def found_hdf5_pulse_files(self, db, imasdbPath):
        return bool(hdf5Cases(imasdbPath, db))


    def populate_from_mdsplus(self, db, imasdbPath, databaseItem):
        """The MDS+ shot/run items under a database row, from the shared scanner.

        The parsing of the ``.datafile`` names lives in `mdsplusCases`; this
        only lays the rows the tree has always shown -- one shot item, then its
        runs -- so the tree and the URI list of the start window read the same
        pulse off the same file.
        """
        shots = {}
        for case in mdsplusCases(imasdbPath, db):
            shotItem = shots.get(case['shot'])
            if shotItem is None:
                shotItem = QTreeWidgetItem(databaseItem)
                shotItem.setText(0, case['shot'])
                shots[case['shot']] = shotItem
            runItem = QTreeWidgetItem(shotItem)
            runItem.setText(0, case['run'])

    def populate_from_hdf5(self, db, imasdbPath, databaseItem):
        """The HDF5 shot/run items under a database row, from the shared scanner.

        The `*.h5` test lives in `hdf5Cases`; this lays the same shot/run rows
        the tree has always shown, so a case that is a case in the URI list is a
        case in the tree and the reverse.
        """
        shots = {}
        for case in hdf5Cases(imasdbPath, db):
            shotItem = shots.get(case['shot'])
            if shotItem is None:
                shotItem = QTreeWidgetItem(databaseItem)
                shotItem.setText(0, case['shot'])
                shots[case['shot']] = shotItem
            runItem = QTreeWidgetItem(shotItem)
            runItem.setText(0, case['run'])

    def addContentsForUsername(self):
        """Set treeWidget items based on imasdb for given user.
        """
        
        try:
            if self.username in self.presentUserNameList:
                return
            imasdbPath = caseRootForUser(self.username)
            if imasdbPath is None or not os.path.exists(imasdbPath):
                return

            self.rootUserItem = QTreeWidgetItem()
            self.rootUserItem.setText(0, self.username)

            databaseList = _dirsUnder(imasdbPath)

            mdsplus_backendItem = QTreeWidgetItem(self.rootUserItem)
            mdsplus_backendItem.setText(0, "MDS+")
            
            hdf5_backendItem = QTreeWidgetItem(self.rootUserItem)
            hdf5_backendItem.setText(0, "HDF5")

            # Go through databases
            for db in databaseList:
                if self.found_mdsplus_pulse_files(db, imasdbPath):
                    databaseItem = QTreeWidgetItem(mdsplus_backendItem)
                    databaseItem.setText(0, db)
                    self.populate_from_mdsplus(db, imasdbPath, databaseItem)
                
                if self.found_hdf5_pulse_files(db, imasdbPath):
                    databaseItem = QTreeWidgetItem(hdf5_backendItem)
                    databaseItem.setText(0, db)
                    self.populate_from_hdf5(db, imasdbPath, databaseItem)
                
        except Exception as e:
            print(str(e))
            

if __name__ == '__main__':
    """Test.
    """
    from PySide6.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)
    mainWin = QMainWindow()
    treeWidget = QVizIMASdbBrowserWidget(mainWin)
    mainWin.setCentralWidget(treeWidget)
    mainWin.show()
    sys.exit(app.exec_())
