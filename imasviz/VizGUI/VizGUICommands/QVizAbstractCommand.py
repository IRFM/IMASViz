
# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

class QVizAbstractCommand:

    def __init__(self, dataTreeView, treeNode=None):
        self.dataTreeView = dataTreeView
        if treeNode is not None:
            self.treeNode = treeNode
        else:
            self.treeNode = self.dataTreeView.selectedItem
        if self.treeNode is not None:
            self.nodeData = self.treeNode.getData()
