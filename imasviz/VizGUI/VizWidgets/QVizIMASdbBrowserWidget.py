#  Name   : QVizIMASdbBrowserWidget
#
#          A widget for browsing through available IDSs.
#
#  Author :
#         Ludovic Fleury, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
# *****************************************************************************
#     Copyright(c) 2016- L. Fleury, D. Penko
# *****************************************************************************


from PySide2.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide2.QtCore import Signal, QObject, QThread
from PySide2.QtWidgets import QProgressBar
import sys
import os
import getpass
import glob
import logging
import threading
from threading import Thread, Condition
from functools import partial


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
        """Handler for double click on QTreeWidgetItem in QTreeWidget
        """

        # When clicking on item representing run number
        # (last in tree hierarchy -> 0 children)
        if item.childCount() == 0:
            self.setActiveUsername(item.parent().parent().parent().parent().text(0))
            self.setActiveDatabase(item.parent().parent().text(0))
            self.setActiveShot(item.parent().text(0))
            self.setActiveRun(item.text(0))

        self.onItemDoubleClick.emit()

    def setActiveUsername(self, username):
        self.activeUsername = username

    def setActiveDatabase(self, db):
        self.activeDatabase = db

    def setActiveShot(self, shot):
        self.activeShot = shot

    def setActiveRun(self, run):
        self.activeRun = run

    def getActiveUsername(self):
        return self.activeUsername

    def getActiveDatabase(self):
        return self.activeDatabase

    def getActiveShot(self):
        return self.activeShot

    def getActiveRun(self):
        return self.activeRun

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
       for d in range(10):  # will look in /0 and /1 dirs
            shotRunPath = imasdbPath + "/" + db + "/3/" + str(d)

            if os.path.exists(shotRunPath) is False:
                continue

            for f in os.listdir(shotRunPath):
                if f.endswith(".datafile"):
                    return True
       return False
       
    def found_hdf5_pulse_files(self, db, imasdbPath):
        shotPath = imasdbPath + "/" + db + "/3/"
    
        if os.path.exists(shotPath) is False:
            return False
    
        shotList = []
    
        # Get shots directories
        shotList = glob.glob1(shotPath, "*")
        shotList.sort()
    
        for shot in shotList:
    
            if len(shot) < 5:
                continue
            
            runList = []
            runList = glob.glob1(shotPath + "/" + shot, "*")
            
            for run in runList:
                
                filesList = glob.glob1(shotPath + "/" + shot + "/" + run, "*.h5")
                
                if len(filesList) > 0:
                    return True;
                    
        return False
        
    
    def populate_from_mdsplus(self, db, imasdbPath, databaseItem):
        # /0 contains runs=0...9999
        # /1 contains runs=10000...19999, first run number is folder number
        # /2 contains runs=20000...29999
        # /3 contains runs=30000...39999
        # /4 contains runs=40000...49999
        # /5 contains runs=50000...59999
        # /6 contains runs=60000...69999
        # /7 contains runs=70000...79999
        # /8 contains runs=80000...89999
        # /9 contains runs=90000...99999

        for d in range(10):  # will look in /0 and /1 dirs
            shotRunPath = imasdbPath + "/" + db + "/3/" + str(d)

            if os.path.exists(shotRunPath) is False:
                continue

            # Shot list to take care the shot entries do no repeat
            shotList = []
            shotItemList = []

            # Get number of *.datafile files (to avoid using list.append())
            dataFileCounter = len(glob.glob1(shotRunPath, "*.datafile"))
            dataFileList = [""]*dataFileCounter

            # Set dataFileList
            i = 0
            for f in os.listdir(shotRunPath):
                if f.endswith(".datafile"):
                    dataFileList[i] = f
                    i += 1

            # Sort by alphabetical order
            # Note: This is mandatory, otherwise the further strategy of
            #       avoiding duplication of shotItems will be broken
            dataFileList.sort()

            for i in range(len(dataFileList)):
                # Extract shot and run numbers
                # Strategy: Last 4 digits are always run number. The rest
                #           are shot (for /0 folder!)
                rs = dataFileList[i].split(".")[0]
                rs = rs.split("_")[1]
                try:
                    if d == 0:
                        run = int(rs[-4:])
                    else:
                        run = int(str(d)+rs[-4:])
                except:
                    # In case non-valid .datafile name is found
                    # e.g. 'ids_model.datafile', skip this file
                    continue
                run = str(run)
                shot = rs[:-4]

                if shot not in shotList:
                    shotItem = QTreeWidgetItem(databaseItem)
                    shotItem.setText(0, shot)

                    shotList.append(shot)
                    shotItemList.append(shotItem)

                runItem = QTreeWidgetItem(shotItem)
                runItem.setText(0, run)
                
    def populate_from_hdf5(self, db, imasdbPath, databaseItem):
        
        shotPath = imasdbPath + "/" + db + "/3/"

        if os.path.exists(shotPath) is False:
            return

        # Shot list to take care the shot entries do no repeat
        shotList = []
        shotItemList = []

        # Get shots directories
        shotList = glob.glob1(shotPath, "*")
        shotList.sort()

        for shot in shotList:

            if len(shot) < 5:
                continue
            
            shotItem = QTreeWidgetItem(databaseItem)
            shotItem.setText(0, shot)
            
            runList = []
            runList = glob.glob1(shotPath + "/" + shot, "*")
            
            for run in runList:
                runItem = QTreeWidgetItem(shotItem)
                runItem.setText(0, run) 
        
    def addContentsForUsername(self):
        """Set treeWidget items based on imasdb for given user.
        """
        
        try:
            #self.activeUsername = self.username

            imasdbPath = None
            if self.username != "public":
               userPath = os.path.abspath(os.path.join(
               os.path.dirname(__file__), os.environ['HOME'], '..'))
               userPath = userPath + "/" + self.username
               # If user path does not exist, return
               if os.path.exists(userPath) is False or \
                    self.username in self.presentUserNameList:
                 return
               if os.path.exists(userPath) is False:
                 return
               imasdbPath = userPath + "/public/imasdb"
            else:
               imasdbPath = os.environ['IMAS_HOME'] + "/shared/imasdb"
               if not os.path.exists(imasdbPath) or \
                    self.username in self.presentUserNameList:
                 return
              
            self.rootUserItem = QTreeWidgetItem()
            self.rootUserItem.setText(0, self.username)

            databaseList = [dI for dI in os.listdir(imasdbPath)
                            if os.path.isdir(os.path.join(imasdbPath, dI))]

            # Sort by alphabetical order
            databaseList.sort()
            
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
    from PySide2.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)
    mainWin = QMainWindow()
    treeWidget = QVizIMASdbBrowserWidget(mainWin)
    mainWin.setCentralWidget(treeWidget)
    mainWin.show()
    sys.exit(app.exec_())
