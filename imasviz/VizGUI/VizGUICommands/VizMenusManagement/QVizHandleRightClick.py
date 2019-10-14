
#  Name   : QVizHandleRightClick
#
#          Container to handle right click events in PyQt5.
#          Note: The wxPython predecessor of this Python file is
#          HandleRightClick.py. 'HandleRightClickAndShiftDown' routine was
#          moved to separate file - QVizHandleShiftDownAndRightClick.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#  TODO:
#
#    - class HandleRightClickAndShiftDown definition
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#****************************************************

from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizLoadDataHandling import QVizLoadDataHandling
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling import QVizSignalHandling
from imasviz.VizUtils.QVizGlobalValues import GlobalColors


class QVizHandleRightClick:
    """ Handle the mouse right click event on a PyQt5 QTreeWidget.
    TODO: currently the right click menu creation is done in QVizSignalHandling
          (as right click are currently performed only on signal nodes).
    """

    def execute(self, node, dataTreeView):
        """
        Arguments:
            node (QVizTreeNode) : Item (node) from in the QTreeWidget.
            dataTreeView : DataTreeView object to which the node belongs.
        """
        showPopUp = 0

        # If the node is a signal and occurrence contains data, call showPopUpMenu function for plotting data
        #IDSRootNode = dataTreeView.IDSRoots[node.getIDSName()]
        if node.isDynamicData() and node.hasAvailableData():
            showPopUpMenu = QVizSignalHandling(dataTreeView=dataTreeView)
            showPopUp = showPopUpMenu.showPopUpMenu(node)
        else:
            # If the node is a IDS node, call showPopMenu for loading IDS data
            if node.isIDSRoot()and node.hasAvailableData():
                showPopUpMenu = QVizLoadDataHandling()
                showPopUp = showPopUpMenu.showPopUpMenu(node, dataTreeView)

        return showPopUp
