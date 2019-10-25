#  Name   : QVizSelectOrUnselectSignal
#
#          Container to handle signal selection/unselection (PyQt5).
#          Note: The wxPython predecessor of this Python file is
#          SelectOrUnselectSignal.py
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- F. Ludovic, L. xinyi, D. Penko
#****************************************************

from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand
from imasviz.VizUtils.QVizGlobalValues import GlobalColors, QVizGlobalValues, QVizPreferences


class QVizSelectOrUnselectSignal(QVizAbstractCommand):
    def __init__(self, dataTreeView, nodeData = None):
        QVizAbstractCommand.__init__(self, dataTreeView, nodeData)

    def execute(self):
        self.updateNodeData()
        isSelected = self.nodeData['isSelected']
        key = self.dataTreeView.dataSource.dataKey(self.nodeData)
        # If the signal is selected (isSelected == 1), unselect it (red -> blue)
        # Else if the signal is unselected (isSelected == 0), select it (blue -> red)
        if isSelected == 1:
            # If the node is unselected, the text color is blue
            # Set the item color
            self.dataTreeView.selectedItem.setStyleWhenContainingData()
            # Delete the signal from the list of selected signals
            del self.dataTreeView.selectedSignalsDict[key]
            # Set the node selection status
            self.nodeData['isSelected'] = 0
        else:
            # Set the node selection status
            self.nodeData['isSelected'] = 1
            # If the node is selected, the text color is red
            # Set the item color
            self.dataTreeView.selectedItem.setStyleWhenSelected()
            # Give the order of user selection
            index = len(self.dataTreeView.selectedSignalsDict) - 1
            # Add a data dictionary of signal parameters to array of
            # data dictionaries of all selected signals
            # (should replace self.dataTreeView.selectedSignals)
            self.dataTreeView.selectedSignalsDict[key] = \
                 {'index'           : index,
                 'QTreeWidgetItem'  : self.dataTreeView.selectedItem,
                 'shotNumber'       : self.dataTreeView.dataSource.shotNumber,
                 'runNumber'        : self.dataTreeView.dataSource.runNumber,
                 'imasDbName'       : self.dataTreeView.dataSource.imasDbName,
                 'userName'         : self.dataTreeView.dataSource.userName}

