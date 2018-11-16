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
#    - Function definitions (from LoadDataHandling class)
#       def popUpMenuHandler
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic,L.xinyi, D. Penko
#****************************************************

from functools import partial

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QMenu

from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadSelectedData import QVizLoadSelectedData

# Default maximum number of IDS occurences
MAX_NUMBER_OF_IDS_OCCURENCES = 10

class QVizLoadDataHandling(QObject):
    """Setting the popup menu: Load the contents of the selected IDS.
    """

    def __init__(self, dataTreeView):
        """
        Arguments:
            dataTreeView (QTreeWidget) : DataTreeView object of the QTreeWidget.
        """
        super(QVizLoadDataHandling, self).__init__()
        self.dataTreeView = dataTreeView

    def showPopUpMenu(self, IDSName):
        """Show the pop up menu for loading IDS.

        Arguments:
            IDSName    (str) : Name of the IDS e.g. 'magnetics'.
        """

        # The name of the current selected IDS is kept and attached to the
        # view
        self.dataTreeView.IDSNameSelected = IDSName

        # Do not display popup menu if the data are already loaded for the
        # current selected item
        # if not self.dataTreeView.dataCurrentlyLoaded.get(0):
        #     action_GET_IDS_DATA = QAction('Get ' + IDSName + \
        #         ' data... (default to occurrence 0)', self)
        #     action_GET_IDS_DATA.triggered.connect(self.loadSelectedData)
        #     self.dataTreeView.popupmenu = QMenu()
        #     self.dataTreeView.popupmenu.addAction(action_GET_IDS_DATA)
        #
        #     # We propose to load a given occurence 0
        #     # Set popup menu for IDS occurences
        #     # Set first-level popup menu
        #     subMenu = QMenu('Get ' + IDSName + ' data for occurrence')
        #     self.dataTreeView.popupmenu.addMenu(subMenu)
        #     # Set second-level popup menu
        #     # action_GET_IDS_OCC_DATA_list = []

        subMenu = None
        self.dataTreeView.popupmenu = None

        for i in range(0, MAX_NUMBER_OF_IDS_OCCURENCES):

            if self.dataTreeView.popupmenu is None:
                self.dataTreeView.popupmenu = QMenu()
                subMenu = QMenu('Get ' + IDSName + ' data for occurrence')
                self.dataTreeView.popupmenu.addMenu(subMenu)
            # - Set new submenu action and its label
            if not self.occurrenceAlreadyLoaded(IDSName, i):
                action_GET_IDS_OCC_DATA = \
                    subMenu.addAction('Occurrence ' + str(i))
                # - Connect action to function using partial
                #   Note: PyQt5 lambda method is not a good way to pass the
                #         function arguments. The use of partial is better
                #         and more bulletproof
                action_GET_IDS_OCC_DATA.triggered.connect(partial(self.loadSelectedData, i))
        # Map the menu (in order to show it)

        if subMenu is not None:
            self.dataTreeView.popupmenu.exec_( \
                self.dataTreeView.viewport().mapToGlobal(self.dataTreeView.pos))
        return 1

    def occurrenceAlreadyLoaded(self, IDSName, occurrence):
        key = IDSName + "/" + str(occurrence)
        if self.dataTreeView.ids_roots_occurrence.get(key) is not None:
            return True
        return False

    def loadSelectedData(self, occurrence=0, threadingEvent=None):
        """Load data of selected IDS and its occurrence.

        Arguments:
            occurrence     (int) : IDS occurrence number (0-9).
            threadingEvent ()    : Event.
        """
        QVizLoadSelectedData(self.dataTreeView, occurrence, threadingEvent).execute()

    def refreshSelectedIDS(self, occurrence=0, threadingEvent=None):
        """Refresh the source IDS and its data for the set occurrence.

        Arguments:
            occurrence     (int) : IDS occurrence number (0-9).
            threadingEvent ()    : Event.
        """
        QVizLoadSelectedData(self.dataTreeView, occurrence, threadingEvent).refreshIDS()
