import wx
from imasviz.util.GlobalValues import GlobalValues
from imasviz.gui_commands.select_commands.LoadSelectedData import LoadSelectedData

MAX_NUMBER_OF_IDS_OCCURENCES = 10

class MenuIDS:
    def __init__(self):
        self.GET_IDS_DATA = 5000
        self.GET_IDS_OCC_DATA = 10000

class LoadDataHandling:
    
    def __init__(self, view):
        self.view = view
        self.menuIDS = MenuIDS()

    #Show the pop up menu for loading IDS
    def showPopUpMenu(self, IDSName):

        #The name of the current selected IDS is kept and attached to the view
        self.view.IDSNameSelected = IDSName

        #Check if the data has been already loaded
        IDSDataLoaded = self.view.idsAlreadyParsed[self.view.IDSNameSelected]

        #Do not diplay popup if the data are already loaded for the current selected item
        if IDSDataLoaded == 1:
            return

        #First, build the popup menu for the selected IDS if there is not a current IDS loading in progress
        if self.view.dataCurrentlyLoaded == False:
            self.view.popupmenu = wx.Menu()
            self.view.popupmenu.Append(self.menuIDS.GET_IDS_DATA, 'Get ' + IDSName + ' data... (default to occurrence 0)')

        #we propose to load a given occurence
        if self.view.dataCurrentlyLoaded == False:
            showMenu = wx.Menu()
            self.view.popupmenu.Append(wx.ID_ANY, 'Get ' + IDSName + ' data for occurrence', showMenu)
            for i in range(0, MAX_NUMBER_OF_IDS_OCCURENCES):
                showMenu.Append(self.menuIDS.GET_IDS_OCC_DATA + i + 1, item='Occurrence ' + str(i + 1), kind=wx.ITEM_NORMAL)

        self.view.Bind(wx.EVT_MENU, self.popUpMenuHandler)

        return 1

    def popUpMenuHandler(self, event):
        if event.GetId() == self.menuIDS.GET_IDS_DATA:
            self.loadSelectedData()
        else:
            for i in range(0, MAX_NUMBER_OF_IDS_OCCURENCES):
                if event.GetId() == i + 1 + self.menuIDS.GET_IDS_OCC_DATA :
                    self.loadSelectedData(i + 1)
                    break

    def loadSelectedData(self, occurrence=0, threadingEvent=None):
        LoadSelectedData(self.view, occurrence, threadingEvent).execute()
