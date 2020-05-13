#  Name   : QVizPAvailableIDSBrowserWidget
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
import sys
import os
import getpass
import glob


class QVizPAvailableIDSBrowserWidget(QTreeWidget):
    """Set and populate QTreeWidget.
    """

    def __init__(self, parent):
        """
        Arguments:
            parent     (QWindow) : QVizDataTreeView parent.
        """

        super(QVizPAvailableIDSBrowserWidget, self).__init__(parent)

        # Set QTreeWidget name
        self.setObjectName('AvailableIDSBrowserWidget')
        # Hide header
        self.setHeaderHidden(True)

        # # Connect 'itemClicked' with the 'onLeftClickItem' function.
        # # On clicking on the QTreeWidgetItem (left click) the function will
        # # be run
        # self.itemClicked.connect(self.onLeftClickItem)

        # # Set action on double click on item
        # self.itemDoubleClicked.connect(self.loadDefaultOccurrence)

        self.setContents()

    def setContents(self):
        """Set treeWidget items.
        """

        rootUserItem = QTreeWidgetItem(self)
        # Get current username
        userName = getpass.getuser()
        rootUserItem.setText(0, userName)

        # Get (standard) imasdb path
        imasdbPath = os.environ['HOME'] + "/public/imasdb"

        databaseList = [dI for dI in os.listdir(imasdbPath)
                        if os.path.isdir(os.path.join(imasdbPath, dI))]

        # Go through databases
        for db in databaseList:
            databaseItem = QTreeWidgetItem(rootUserItem)
            databaseItem.setText(0, db)

            shotRunPath = imasdbPath + "/" + db + "/3/0"

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


if __name__ == '__main__':
    """Test.
    """
    from PyQt5.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)
    mainWin = QMainWindow()
    treeWidget = QVizPAvailableIDSBrowserWidget(mainWin)
    mainWin.setCentralWidget(treeWidget)
    mainWin.show()
    sys.exit(app.exec_())
