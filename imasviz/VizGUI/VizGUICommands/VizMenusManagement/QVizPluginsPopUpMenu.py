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
        self.pluginsHandler.updateMenu(menu,dataTreeView, treeNode)
