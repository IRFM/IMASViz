#  Name   : QVizHandleShiftAndRightClick
#
#          Container to handle shift down + right click events in PyQt5.
#          Note: The wxPython predecessor of this Python file is
#          HandleRightClick.py
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#****************************************************

from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizLoadDataHandling import QVizLoadDataHandling
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling import QVizSignalHandling
from imasviz.VizUtils.QVizGlobalValues import GlobalColors
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizPluginsHandler \
    import QVizPluginsHandler

class QVizHandleShiftAndRightClick:
    """Handle the mouse right click + shift down event on a tree widget item
    within the data tree view.
    """

    def __init__(self, dataTreeView):
        self.dataTreeView = dataTreeView

    def execute(self, treeNode):
        """Execute on the event
        """

        idsName = None
        isSignal = 0

        if treeNode.isDynamicData() is not None:
            isSignal = treeNode.isDynamicData()
        else:
            return

        if treeNode.getIDSName() is not None:
            # If the item/subject is IDS get the IDS name"""
            idsName = treeNode.getIDSName()

        # Set plugins handler. Pass the dataTreeView and item/subject to the
        # QVizPluginsHandler
        pluginsHandler = QVizPluginsHandler(self.dataTreeView, treeNode)

        if idsName is not None and isSignal == 0:
            # If the item/subject is IDS...
            idsOverview = idsName + "_overview"
            showPopUp = pluginsHandler.showPopUpMenu([idsOverview])
        elif idsName is not None and isSignal == 1:
            # Else if the item/subject is a FLT_1D array
            # FLT_1D array -> isSignal == 1)...
            subjectsList = ['FLT_2D', 'FLT_1D', 'signal']
            showPopUp = pluginsHandler.showPopUpMenu(subjectsList)
            # Note: the pluginHandler.showPopUpMenu argument must match
            # the one returned by the 'getEntriesPerSubject' function, defined in
            # the main plugin .py source file, in this case 'signal'
            # (plugin source file of the ArraySize plugin)
        else:
            showPopUp = pluginsHandler.showPopUpMenu(['overview'])
        return showPopUp