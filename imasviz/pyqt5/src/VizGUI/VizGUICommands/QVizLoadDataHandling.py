#  Name   :IDSTree
#
#          Container to handle data loading.
#          Note: The wxPython predecessor of this Python file is
#          LoadDataHandling.py
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#  TODO:
#
#    - Function definitions (from LoadDataHandling to LoadDataHandling class)
#       def popUpMenuHandler
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic,L.xinyi, D. Penko
#****************************************************

from imasviz.util.GlobalValues import GlobalIDs
from imasviz.gui_commands.select_commands.LoadSelectedData import LoadSelectedData
from PyQt5.QtCore import pyqtSlot, QObject
from PyQt5.QtWidgets import QAction, QMenu
from PyQt5.QtGui import QMouseEvent

# Default maximum number of IDS occurences
MAX_NUMBER_OF_IDS_OCCURENCES = 10

class QVizLoadDataHandling(QObject):
    """Setting the popup menu: Load the contents of the selected IDS.
    """

    def __init__(self, treeView):
        """
        Arguments:
            treeView (obj) : wxTreeView object of the wxDataTreeViewFrame.
        """
        super(QVizLoadDataHandling, self).__init__()
        self.treeView = treeView

    def QshowPopUpMenu(self, IDSName):
        """Show the pop up menu for loading IDS.

        Arguments:
            IDSName    (str) : Name of the IDS e.g. 'magnetics'.
        """

        # The name of the current selected IDS is kept and attached to the
        # view
        self.treeView.IDSNameSelected = IDSName

        # Check if the data has been already loaded
        IDSDataLoaded = \
            self.treeView.idsAlreadyFetched[self.treeView.IDSNameSelected]

        # Do not display popup menu if the data are already loaded for the
        # current selected item

        # if IDSDataLoaded == 1:
        #     if self.treeView.dataCurrentlyLoaded == False:
        #         TODO

        # First, build the popup menu for the selected IDS if there is not a
        # current IDS loading in progress
        if self.treeView.dataCurrentlyLoaded == False:
            action_GET_IDS_DATA = QAction('Get ' + IDSName + \
                ' data... (default to occurrence 0)')
            # action_GET_IDS_DATA.triggered.connect(self.runExample)
            action_GET_IDS_DATA.triggered.connect(self.loadSelectedData)
            self.treeView.popupmenu = QMenu()
            self.treeView.popupmenu.addAction(action_GET_IDS_DATA)
            self.treeView.popupmenu.exec_( \
                self.treeView.viewport().mapToGlobal(self.treeView.pos))

        # # We propose to load a given occurence 0
        # # Set popup menu for IDS occurences
        # if self.treeView.dataCurrentlyLoaded == False:
        #   TODO

        return 1

    @pyqtSlot()
    def loadSelectedData(self, occurrence=0, threadingEvent=None):
        """Load selected IDS data.

        Arguments:
            occurrence     (int) : IDS occurrence number (0-9).
            threadingEvent ()    : Event.
        """
        LoadSelectedData(self.treeView, occurrence, threadingEvent).execute()

    def refreshSelectedIDS(self, occurrence=0, threadingEvent=None):
        """Refresh the source IDS and its data.

        Arguments:
            occurrence     (int) : IDS occurrence number (0-9).
            threadingEvent ()    : Event.
        """
        LoadSelectedData(self.treeView, occurrence, threadingEvent).refreshIDS()
