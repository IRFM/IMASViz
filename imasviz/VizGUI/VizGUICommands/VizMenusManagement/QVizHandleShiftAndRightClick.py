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

    def execute(self, QVizTreeNode):
        """Execute on the event
        """

        # Get selected item/subject data dict
        dataDict = QVizTreeNode.getDataDict()
        # Set default variables"""
        idsName = None
        isSignal = 0

        if dataDict != None:
            # If the item/subject is available...
            # Set 'isSignal'. IDSs return value 0 while FLT_1D arrays return
            # value 1
            isSignal = dataDict['isSignal']

        if dataDict != None and 'IDSName' in dataDict:
            # If the item/subject is IDS get the IDS name"""
            idsName = dataDict['IDSName']

        # Set plugins handler. Pass the dataTreeView and item/subject to the
        # QVizPluginsHandler
        pluginsHandler = QVizPluginsHandler(self.dataTreeView, dataDict)

        if idsName != None and isSignal == 0:
            # If the item/subject is IDS...
            idsOverview = idsName + "_overview"
            showPopUp = pluginsHandler.showPopUpMenu([idsOverview])
        elif idsName != None and isSignal == 1:
            # Else if the item/subject is a FLT_1D array
            # FLT_1D array -> isSignal == 1)...
            showPopUp = pluginsHandler.showPopUpMenu(['signal'])
            # Note: the pluginHandler.showPopUpMenu argument must match
            # the one returned by the 'getEntriesPerSubject' function, defined in
            # the main plugin .py source file, in this case 'signal'
            # (plugin source file of the ArraySize plugin)
        else:
            showPopUp = pluginsHandler.showPopUpMenu(['overview'])
        return showPopUp