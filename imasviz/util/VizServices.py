from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalOperations import GlobalOperations

from imasviz.gui_commands.select_commands.LoadSelectedData import LoadSelectedData
import os

class VizServices:

    def __init__(self):
        pass

    def getNode(self, dataTreeView, occurrence, searchedPath):
        """Get/Find node using its path.

        Arguments:
            dataTreeView (QTreeWidget) : DataTreeView object.
            occurrence    (int) : IDS occurrence number.
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

        dataTreeView.setIDSNameSelected(idsName)
        LoadSelectedData(dataTreeView, occurrence, pathsList, False).execute()
        from imasviz.view.WxSignalsTreeView import IDSSignalTreeFrame
        signalsFrame = \
            IDSSignalTreeFrame(None, dataTreeView,
                               str(dataTreeView.shotNumber),
                               GlobalOperations.getIDSDefFile(os.environ['IMAS_VERSION']))
        # Return the node
        return signalsFrame.tree.selectNodeWithPath(searchedPath)


    def getNodeData(self, dataTreeView, occurrence, searchedPath):
        """Get full data on the node using its path ('path' is one of them).

        Arguments:
            dataTreeView (QTreeWidget) : DataTreeView object.
            occurrence    (int) : IDS occurrence number.
            searchedPath (str) : An IDS path to one of the node (signals),
                                 containing a data array (e.g. FLT_1D), of
                                 which all siblings are to be selected.
                                 Example: 'magnetics/flux_loop(0)/flux/data'
        """
        # Find the node by its path
        node = self.getNode(dataTreeView, occurrence, searchedPath)
        # Return the node data
        return dataTreeView.GetItemData(node)

    def getRootNode(self, dataTreeView, idsName):
        """Get root node of the IDS.
        Arguments:
            dataTreeView (QTreeWidget) : DataTreeView object.
            idsName    (str) : Name of the IDS.
        """

        return dataTreeView.dataTree[idsName]

    def getRootNodeData(self, dataTreeView, idsName):
        """Get data of the IDS root node.
        Arguments:
            dataTreeView (QTreeWidget) : DataTreeView object.
            idsName    (str) : Name of the IDS.
        """
        #return dataTreeView.GetItemData(self.getRootNode(dataTreeView, idsName))
        return self.getRootNode(dataTreeView, idsName).itemVIZData

