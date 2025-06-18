# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

from PySide6.QtWidgets import QMenu
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizPluginsPopUpMenu import QVizPluginsPopUpMenu


class QVizHandleShiftAndRightClick:
    """Handle the mouse right click + shift down event on a tree widget item
    within the data tree view.
    """

    def __init__(self, dataTreeView):
        self.dataTreeView = dataTreeView
        self.pluginsPopUpMenu = QVizPluginsPopUpMenu()

    def execute(self, treeNode):
        """Execute on the event
        """
        self.dataTreeView.popupmenu = QMenu()
        self.pluginsPopUpMenu.upateMenu(treeNode, self.dataTreeView,
                                        self.dataTreeView.popupmenu)
        self.dataTreeView.popupmenu.exec_(
            self.dataTreeView.viewport().mapToGlobal(self.dataTreeView.pos))
