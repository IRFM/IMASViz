#  Name   : QVizAvailableIDSBrowserWidget
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


from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import pyqtSignal
import sys
import os
import getpass
import glob


class QVizAvailableIDSBrowserWidget(QTreeWidget):
    """Set and populate QTreeWidget.
    """

    onItemDoubleClick = pyqtSignal()

    def __init__(self, parent):
        """
        Arguments:
            parent     (QWindow) : QVizDataTreeView parent.
        """

        super(QVizAvailableIDSBrowserWidget, self).__init__(parent)

        # Set QTreeWidget name
        self.setObjectName('AvailableIDSBrowserWidget')
        # Hide header
        self.setHeaderHidden(False)
        self.setHeaderLabels(['IDS cases browser'])

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
        # Get current username
        username = getpass.getuser()
        self.addContentsForUsername(username)

    def addContentsForUsername(self, username):
        """Set treeWidget items based on imasdb for given user.
        """

        try:

            self.activeUsername = username
            # Get (standard) imasdb path
            # userPath = os.path.abspath(os.path.join(
            #     os.path.dirname(__file__), '..', os.environ['HOME']))

            userPath = os.path.abspath(os.path.join(
                os.path.dirname(__file__), os.environ['HOME'], '..'))
            userPath = userPath + "/" + username

            # If user path does not exist, return
            if os.path.exists(userPath) is False or \
                    username in self.presentUserNameList:
                return False

            self.presentUserNameList.append(username)

            rootUserItem = QTreeWidgetItem(self)
            rootUserItem.setText(0, username)

            imasdbPath = userPath + "/public/imasdb"

            databaseList = [dI for dI in os.listdir(imasdbPath)
                            if os.path.isdir(os.path.join(imasdbPath, dI))]

            # Sort by alphabetical order
            databaseList.sort()

            # Go through databases
            for db in databaseList:
                databaseItem = QTreeWidgetItem(rootUserItem)
                databaseItem.setText(0, db)

                shotRunPath = imasdbPath + "/" + db + "/3/0"

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
                    # Note: Last 4 digits are always run number. The rest are shot
                    rs = dataFileList[i].split(".")[0]
                    rs = rs.split("_")[1]
                    run = int(rs[-4:])
                    run = str(run)
                    shot = rs[:-4]

                    if shot not in shotList:
                        shotItem = QTreeWidgetItem(databaseItem)
                        shotItem.setText(0, shot)

                        shotList.append(shot)
                        shotItemList.append(shotItem)

                    runItem = QTreeWidgetItem(shotItem)
                    runItem.setText(0, run)

            return True
        except Exception as e:
            print(str(e))
            return False

    def doubleClickHandler(self, item, column_No):
        """Handler for double click on QTreeWidgetItem in QTreeWidget
        """

        # When clicking on item representing run number
        # (last in tree hierarchy -> 0 children)
        if item.childCount() == 0:
            # self.activeUsername = item.parent().parent().parent().text(0)
            self.setActiveDatabase(item.parent().parent().text(0))
            self.setActiveShot(item.parent().text(0))
            self.setActiveRun(item.text(0))

        self.onItemDoubleClick.emit()

    def setActiveDatabase(self, db):
        self.activeDatabase = db

    def setActiveShot(self, shot):
        self.activeShot = shot

    def setActiveRun(self, run):
        self.activeRun = run

    def getActiveDatabase(self):
        return self.activeDatabase

    def getActiveShot(self):
        return self.activeShot

    def getActiveRun(self):
        return self.activeRun


if __name__ == '__main__':
    """Test.
    """
    from PyQt5.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)
    mainWin = QMainWindow()
    treeWidget = QVizAvailableIDSBrowserWidget(mainWin)
    mainWin.setCentralWidget(treeWidget)
    mainWin.show()
    sys.exit(app.exec_())
