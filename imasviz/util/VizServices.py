from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalOperations import GlobalOperations

from imasviz.gui_commands.select_commands.LoadSelectedData import LoadSelectedData
import os

class VizServices:

    def __init__(self):
        pass

    def getNode(self, wxTreeView, occurrence, searchedPath):
        """Get/Find node using its path.

        Arguments:
            wxTreeView   (obj) : wxTreeView object of the wxDataTreeViewFrame.
            occurence    (int) : IDS occurence number.
            searchedPath (str) : An IDS path to one of the node (signals),
                                 containing a data array (e.g. FLT_1D), of
                                 which all siblings are to be selected.
                                 Example: 'magnetics/flux_loop(0)/flux/data'
        """

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
        # Return the node
        return signalsFrame.tree.selectNodeWithPath(searchedPath)

    def getNodeData(self, wxTreeView, occurrence, searchedPath):
        """Get full data on the node using its path ('path' is one of them).

        Arguments:
            wxTreeView   (obj) : wxTreeView object of the wxDataTreeViewFrame.
            occurence    (int) : IDS occurence number.
            searchedPath (str) : An IDS path to one of the node (signals),
                                 containing a data array (e.g. FLT_1D), of
                                 which all siblings are to be selected.
                                 Example: 'magnetics/flux_loop(0)/flux/data'
        """
        # Find the node by its path
        node = self.getNode(wxTreeView, occurrence, searchedPath)
        # Return the node data
        return wxTreeView.GetItemData(node)

    def getRootNode(self, wxTreeView, idsName):
        """Get root node of the IDS.
        Arguments:
            wxTreeView (obj) : wxTreeView object of the wxDataTreeViewFrame.
            idsName    (str) : Name of the IDS.
        """

        return wxTreeView.dataTree[idsName]

    def getRootNodeData(self, wxTreeView, idsName):
        """Get data of the IDS root node.
        Arguments:
            wxTreeView (obj) : wxTreeView object of the wxDataTreeViewFrame.
            idsName    (str) : Name of the IDS.
        """
        return wxTreeView.GetItemData(self.getRootNode(wxTreeView, idsName))

