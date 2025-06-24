# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand


class QVizDisplayCurrentSelection(QVizAbstractCommand):
    """Displays current nodes selection.

    Arguments:
        dataTreeView (QTreeWidget) : Corresponding DataTreeView.
    """

    def __init__(self, dataTreeView, treeNode=None):
        """Set self.nodeData = nodeData etc. with the use of the
           QVizAbstractCommand
        """
        QVizAbstractCommand.__init__(self, dataTreeView, treeNode)

    def execute(self):
        # Get list of signals, selected in the DataTreeView (dataTreeView)
        self.dataTreeView.imas_viz_api.ShowNodesSelection(self.dataTreeView)
