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
            showPopUpMenu = PluginsHandler(self.view, dico)
            showPopUp = showPopUpMenu.showPopUpMenu(['overview'])
            return showPopUp

        dataName = dataSource.dataNameInPopUpMenu(dico)

        if not 'isSignal' in dico:
            return showPopUp

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

class HandleRightClickAndShiftDown:
    """Handle the mouse right click + shift down event on a item/subject
    within the WxDataTreeViewer panel.
    """

    def __init__(self, view):
        self.view = view

    def execute(self, node):
        """Execute on the event
        """

        """Get selected item/subject"""
        dico = self.view.GetItemData(node)
        """Set default variables"""
        idsName = None
        isSignal = 0

        if dico != None:
            """If the item/subject is available..."""
            """Set 'isSignal'. IDSs return value 0 while FLT_1D arrays return
            value 1
            """
            isSignal = dico.get('isSignal')

        if dico != None and 'IDSName' in dico:
            """If the item/subject is IDS get the IDS name"""
            idsName = dico['IDSName']

        """Set plugins handler. Pass the view and item/subject to the
        PluginsHandler
        """
        pluginsHandler = PluginsHandler(self.view, dico)

        if idsName != None and isSignal == 0:
            """If the item/subject is IDS..."""
            idsOverview = idsName + "_overview"
            showPopUp = pluginsHandler.showPopUpMenu([idsOverview])
        elif idsName != None and isSignal == 1:
            """Else if the item/subject is a FLT_1D array
            FLT_1D array -> isSignal == 1)...
            """
            showPopUp = pluginsHandler.showPopUpMenu(['signal'])
            """Note: the pluginHandler.showPopUpMenu argument must match
            the one returned by the 'getEntriesPerSubject' function, defined in
            the main plugin .py source file, in this case 'signal'
            (plugin source file of the ArraySize plugin)
            """
        else:
            showPopUp = pluginsHandler.showPopUpMenu(['overview'])
        return showPopUp

#---------------------------------------------------------------------------
# PyQt5 routine variations

class QHandleRightClick:
    """ Handle the mouse right click event on a PyQt5 QTreeWidget.
    """
    def __init__(self, dataTreeView):
        """
        Arguments:
            dataTreeView (QTreeWidget) : QVizDataTreeView object.
        """
        self.dataTreeView = dataTreeView

    def execute(self, node):
        """
        Arguments:
            node (QTreeWidgetItem) : Item (node) from in the QTreeWidget.
        """

        #Get the data source attached to the dataTreeView
        dataSource = self.dataTreeView.dataSource
        showPopUp = 0

        #Get the Python dictionary attached to the node
        dico = node.itemVIZData

        if dico == None:
            # TODO
            # showPopUpMenu = PluginsHandler(self.dataTreeView, dico)
            # showPopUp = showPopUpMenu.showPopUpMenu(['overview'])
            return showPopUp

        dataName = dataSource.dataNameInPopUpMenu(dico)

        if not 'isSignal' in dico:
            return showPopUp

        isSignal = dico['isSignal']
        isIDSRoot = dico['isIDSRoot']

        # If the node is a signal, call showPopUpMenu function for plotting data
        if isSignal == 1 and \
            (node.foreground(0).color().name() == '#0000ff' or \
            node.foreground(0).color().name() == '#ff0000'):
            # '#0000ff' - blue
            # '#ff0000' - red
            pass
            # TODO
            # showPopUpMenu = SignalHandling(self.dataTreeView)
            # showPopUp = showPopUpMenu.showPopUpMenu(dataName)
        else:
            # If the node is a IDS node, call showPopMenu for loading IDS data
            if isIDSRoot != None and isIDSRoot == 1:
                if dico['availableIDSData'] == 1:
                    showPopUpMenu = LoadDataHandling(self.dataTreeView)
                    showPopUp = showPopUpMenu.QshowPopUpMenu(dataName)

        return showPopUp

# TODO
# class QHandleRightClickAndShiftDown:
