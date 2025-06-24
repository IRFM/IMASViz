# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand


class QVizSelectOrUnselectSignal(QVizAbstractCommand):
    def __init__(self, dataTreeView, treeNode=None):
        QVizAbstractCommand.__init__(self, dataTreeView, treeNode)

    def execute(self):
        isSelected = self.nodeData['isSelected']
        key = self.dataTreeView.dataSource.dataKey(self.treeNode)
        # If the signal is selected (isSelected == 1), unselect it
        # (red -> blue)
        # Else if the signal is unselected (isSelected == 0), select it
        # (blue -> red)
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
                {'index'            : index,
                 'QTreeWidgetItem'  : self.dataTreeView.selectedItem,
                 'uri'              : self.dataTreeView.dataSource.uri}
