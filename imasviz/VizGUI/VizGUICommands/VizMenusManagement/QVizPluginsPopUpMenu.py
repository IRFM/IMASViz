from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizPluginsHandler import QVizPluginsHandler

class QVizPluginsPopUpMenu:

    def __init__(self):
        self.pluginsHandler = None

    def upateMenu(self, treeNode, dataTreeView, menu):

        idsName = None

        if treeNode.getIDSName() is not None:
            # If the item/subject is IDS get the IDS name"""
            idsName = treeNode.getIDSName()

        # Set plugins handler. Pass the dataTreeView and item/subject to the
        # QVizPluginsHandler
        self.pluginsHandler = QVizPluginsHandler(dataTreeView, treeNode)

        if idsName is not None and treeNode.isDynamicData() == 0:
            # If the item/subject is IDS...
            idsOverview = idsName + "_overview"
            self.pluginsHandler.updateMenu(menu, [idsOverview])
        elif idsName is not None and treeNode.isDynamicData() == 1:
            # Else if the item/subject is a FLT_1D array
            # FLT_1D array -> isSignal == 1)...
            subjectsList = ['FLT_2D', 'FLT_1D', 'signal']
            self.pluginsHandler.updateMenu(menu, subjectsList)
            # Note: the pluginHandler.showPopUpMenu argument must match
            # the one returned by the 'getEntriesPerSubject' function, defined in
            # the main plugin .py source file, in this case 'signal'
            # (plugin source file of the ArraySize plugin)
        else:
            self.pluginsHandler.updateMenu(menu, ['overview'])