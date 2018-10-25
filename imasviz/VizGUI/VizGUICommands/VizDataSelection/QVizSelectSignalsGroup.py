#  Name   : QVizSelectSignalsGroup
#
#          Container to handle the selection of a group of signals.
#          Note: The wxPython predecessor of this Python file is
#          SelectSignalsGroup.py
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- F. Ludovic, L. xinyi, D. Penko
#****************************************************

import re

from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignal import QVizSelectSignal
from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand


class QVizSelectSignalsGroup(QVizAbstractCommand):
    """Select a group of all signals - siblings of the node.
    """
    def __init__(self, dataTreeView, nodeData = None):
        """
        Arguments:
            dataTreeView (QTreeWidget) : QTreeWidget object (DTV tree widget).
            nodeData     (array)       : Array of node data.
        """
        QVizAbstractCommand.__init__(self, dataTreeView, nodeData)

    def execute(self):
        #self.updateNodeData()

        # Get the name of the clicked-on signal
        startSigName = self.nodeData['Path']

        # Go through the list of signals and compare the formatted names with
        # the name of the clicked-on signal.
        for signal in self.dataTreeView.signalsList:
            # When comparing the signal names, the brackets and the integers
            # between the brackets are ignored (e.g. from
            # 'parent.array_of_structures[0].leaf' ->
            # 'parent.array_of_structures.leaf' ).
            # This way all structures of the array have the same formatted name.
            sigName = signal.itemVIZData['Path']
            # If the formatted names matches (-> the signals are of the same
            # array of structures), select tree item corresponding to the signal
            if re.sub("[\(\[].*?[\)\]]", "", startSigName) == \
                re.sub("[\(\[].*?[\)\]]", "", sigName):
                # Tag the signal as current DTV selected item
                self.dataTreeView.selectedItem = signal
                # Select the tree item corresponding to the signal
                QVizSelectSignal(dataTreeView=self.dataTreeView,
                                 nodeData=signal.itemVIZData).execute()
