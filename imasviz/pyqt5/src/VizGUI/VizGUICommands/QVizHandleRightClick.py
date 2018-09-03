
#  Name   : QVizHandleRightClick
#
#          Container to handle right click events in PyQt5.
#          Note: The wxPython predecessor of this Python file is
#          HandleRightClick.py
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

from imasviz.pyqt5.src.VizGUI.VizGUICommands.QVizLoadDataHandling import QVizLoadDataHandling
from imasviz.pyqt5.src.VizGUI.VizGUICommands.QVizSignalHandling import QVizSignalHandling

from imasviz.util.GlobalValues import GlobalColors

class QVizHandleRightClick:
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
            (node.foreground(0).color().name() == GlobalColors.BLUE_HEX or \
            node.foreground(0).color().name() == GlobalColors.RED_HEX ):
            showPopUpMenu = QVizSignalHandling(dataTreeView=self.dataTreeView)
            showPopUp = showPopUpMenu.showPopUpMenu(signalName=dataName)
        else:
            # If the node is a IDS node, call showPopMenu for loading IDS data
            if isIDSRoot != None and isIDSRoot == 1:
                if dico['availableIDSData'] == 1:
                    showPopUpMenu = QVizLoadDataHandling(self.dataTreeView)
                    showPopUp = showPopUpMenu.showPopUpMenu(dataName)

        return showPopUp
