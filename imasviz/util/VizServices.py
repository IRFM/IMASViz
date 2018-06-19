from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalOperations import GlobalOperations

from imasviz.gui_commands.select_commands.LoadSelectedData import LoadSelectedData
import os

class VizServices:

    def __init__(self):
        pass

    def getNode(self, wxTreeView, occurrence, searchedPath):

        splitItems = searchedPath.split('/')
        if len(splitItems) == 0:
            raise ValueError('Bad IMAS path (IMAS paths start with IDSName/)')

        idsName = splitItems[0]
        pathsList = [searchedPath]

        wxTreeView.setIDSNameSelected(idsName)
        LoadSelectedData(wxTreeView, occurrence, pathsList, False).execute()
        from imasviz.view.WxSignalsTreeView import IDSSignalTreeFrame
        signalsFrame = \
            IDSSignalTreeFrame(None, wxTreeView,
                               str(wxTreeView.shotNumber),
                               GlobalOperations.getIDSDefFile(os.environ['IMAS_VERSION']))
        return signalsFrame.tree.selectNodeWithPath(searchedPath)

    def getNodeData(self, wxTreeView, occurrence, searchedPath):
        node = self.getNode(wxTreeView, occurrence, searchedPath)
        return wxTreeView.GetItemData(node)

    def getRootNode(self, wxTreeView, idsName):
        return wxTreeView.dataTree[idsName]

    def getRootNodeData(self, wxTreeView, idsName):
        return wxTreeView.GetItemData(self.getRootNode(wxTreeView, idsName))

