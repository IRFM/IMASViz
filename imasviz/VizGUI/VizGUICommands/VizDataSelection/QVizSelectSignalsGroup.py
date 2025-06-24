# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import re

from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignal import QVizSelectSignal
from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand


class QVizSelectSignalsGroup(QVizAbstractCommand):
    """Select a group of all signals - siblings of the node.
    """
    def __init__(self, dataTreeView, treeNode=None):
        """
        Arguments:
            dataTreeView (QTreeWidget) : QTreeWidget object (DTV tree widget).
            nodeData     (array)       : Array of node data.
        """
        QVizAbstractCommand.__init__(self, dataTreeView, treeNode)

    def execute(self):
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
            sigName = signal.getPath()
            # If the formatted names matches (-> the signals are of the same
            # array of structures), select tree item corresponding to the signal
            if re.sub("[\(\[].*?[\)\]]", "", startSigName) == \
                re.sub("[\(\[].*?[\)\]]", "", sigName):
                # Tag the signal as current DTV selected item
                self.dataTreeView.selectedItem = signal
                # Select the tree item corresponding to the signal
                QVizSelectSignal(dataTreeView=self.dataTreeView,
                                 treeNode=signal).execute()
