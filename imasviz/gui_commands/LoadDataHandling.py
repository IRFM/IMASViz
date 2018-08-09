import wx
from imasviz.util.GlobalValues import GlobalIDs
from imasviz.gui_commands.select_commands.LoadSelectedData import LoadSelectedData
from PyQt5.QtCore import pyqtSlot, QObject
from PyQt5.QtWidgets import QAction, QMenu
from PyQt5.QtGui import QMouseEvent

# Default maximum number of IDS occurences
MAX_NUMBER_OF_IDS_OCCURENCES = 10

class LoadDataHandling(QObject):
    """Setting the popup menu: Load the contents of the selected IDS.
    """

    def __init__(self, treeView):
        """
        Arguments:
            treeView (obj) : wxTreeView object of the wxDataTreeViewFrame.
        """
        super(LoadDataHandling, self).__init__()
        self.treeView = treeView

    def showPopUpMenu(self, IDSName):
        """Show the pop up menu for loading IDS.

        Arguments:
            IDSName    (str) : Name of the IDS e.g. 'magnetics'.
        """

        # The name of the current selected IDS is kept and attached to the
        # view
        self.treeView.IDSNameSelected = IDSName

        # Check if the data has been already loaded
        IDSDataLoaded = self.treeView.idsAlreadyFetched[self.treeView.IDSNameSelected]

        # Do not display popup menu if the data are already loaded for the
        # current selected item

        if IDSDataLoaded == 1:
            if self.treeView.dataCurrentlyLoaded == False:
                self.treeView.popupmenu = wx.Menu()
                self.treeView.popupmenu.Append(GlobalIDs.ID_REFRESH_IDS_DATA,   \
                                           'Refresh ' + IDSName             \
                                           + ' data... (default to occurrence 0)')

            self.treeView.Bind(wx.EVT_MENU, self.popUpMenuHandler)
            return 1

        # First, build the popup menu for the selected IDS if there is not a
        # current IDS loading in progress
        if self.treeView.dataCurrentlyLoaded == False:
            self.treeView.popupmenu = wx.Menu()
            self.treeView.popupmenu.Append(GlobalIDs.ID_GET_IDS_DATA,   \
                                       'Get ' + IDSName             \
                                       + ' data... (default to occurrence 0)')

        # We propose to load a given occurence 0
        # Set popup menu for IDS occurences
        if self.treeView.dataCurrentlyLoaded == False:
            showMenu = wx.Menu()
            # Set first-level popup menu
            self.treeView.popupmenu.Append(wx.ID_ANY, \
                                       'Get ' + IDSName \
                                       + ' data for occurrence', showMenu)
            # Set second-level popup menu
            for i in range(0, MAX_NUMBER_OF_IDS_OCCURENCES):
                showMenu.Append(GlobalIDs.ID_GET_IDS_OCC_DATA + i + 1, \
                                item='Occurrence ' + str(i + 1),
                                kind=wx.ITEM_NORMAL)

        self.treeView.Bind(wx.EVT_MENU, self.popUpMenuHandler)

        return 1

    def popUpMenuHandler(self, event):
        if event.GetId() == GlobalIDs.ID_GET_IDS_DATA:
            self.loadSelectedData()
        elif event.GetId() == GlobalIDs.ID_REFRESH_IDS_DATA:
            self.refreshSelectedIDS()
        else:
            for i in range(0, MAX_NUMBER_OF_IDS_OCCURENCES):
                if event.GetId() == i + 1 + GlobalIDs.ID_GET_IDS_OCC_DATA :
                    self.loadSelectedData(i + 1)
                    break
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

    #---------------------------------------------------------------------------
    # PyQt5 routine variations

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
