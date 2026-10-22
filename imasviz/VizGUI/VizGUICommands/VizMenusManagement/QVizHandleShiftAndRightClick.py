# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import logging

from PySide6.QtWidgets import QMenu
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizPluginMenu import QVizPluginMenu


class QVizHandleShiftAndRightClick:
    """Handle the mouse right click + shift down event on a tree widget item
    within the data tree view.

    This gesture offers the plugins and nothing else, so it is the one that
    showed an empty menu: measured on the reference case, 42 of its 55 IDS names
    are claimed by no plugin, and Shift+right click on one of them opened a menu
    with no line in it.
    """

    def __init__(self, dataTreeView):
        self.dataTreeView = dataTreeView
        self.pluginsMenu = QVizPluginMenu()

    def execute(self, treeNode):
        """Execute on the event
        """
        self.dataTreeView.popupmenu = QMenu()
        lines = self.pluginsMenu.buildPluginsMenu(treeNode, self.dataTreeView,
                                                 self.dataTreeView.popupmenu)
        if lines == 0:
            logging.getLogger(self.dataTreeView.uri).info(
                'No plugin offers anything for the %s IDS.'
                % (treeNode.getIDSName(),))
            return
        self.dataTreeView.popupmenu.exec_(
            self.dataTreeView.viewport().mapToGlobal(self.dataTreeView.pos))
