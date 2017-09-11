import wx
from imasviz.gui_commands.SignalHandling import SignalHandling
from imasviz.gui_commands.LoadDataHandling import LoadDataHandling
from imasviz.gui_commands.PluginsHandler import PluginsHandler

# Handle the mouse right click event on a wx tree
class HandleRightClick:
    def __init__(self, view):
        self.view = view


    def execute(self, node):

        #Get the data source attached to the view
        dataSource = self.view.dataSource
        showPopUp = 0

        #Get the Python dictionary attached to the node
        dico = self.view.GetItemData(node)

        if dico == None:
            showPopUpMenu = PluginsHandler(self.view)
            showPopUp = showPopUpMenu.showPopUpMenu(['overview'])
            return showPopUp

        dataName = dataSource.dataNameInPopUpMenu(dico)

        isSignal = dico['isSignal']
        isIDSRoot = dico['isIDSRoot']

        # If the node is a signal, call showPopUpMenu function for plotting data
        if isSignal == 1 and (self.view.GetItemTextColour(node) == wx.BLUE or self.view.GetItemTextColour(node) == wx.RED):
                showPopUpMenu = SignalHandling(self.view)
                showPopUp = showPopUpMenu.showPopUpMenu(dataName)
        else:
            # If the node is a IDS node, call showPopMenu for loading IDS data
            if isIDSRoot != None and isIDSRoot == 1:
                if dico['availableIDSData'] == 1:
                    showPopUpMenu = LoadDataHandling(self.view)
                    showPopUp = showPopUpMenu.showPopUpMenu(dataName)

        return showPopUp


# Handle the mouse right click and shift down event on a wx tree
class HandleRightClickAndShiftDown:

    def __init__(self, view):
        self.view = view

    def execute(self, node):

        dico = self.view.GetItemData(node)
        idsName = None
        if dico != None and 'IDSName' in dico:
            idsName = dico['IDSName']
        pluginsHandler = PluginsHandler(self.view)

        if idsName != None:
            idsOverview = idsName + "_overview"
            showPopUp = pluginsHandler.showPopUpMenu([idsOverview])
        else:
            showPopUp = pluginsHandler.showPopUpMenu(['overview'])
        return showPopUp
