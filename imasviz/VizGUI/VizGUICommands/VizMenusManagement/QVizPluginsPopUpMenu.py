# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizPluginsHandler import QVizPluginsHandler


class QVizPluginsPopUpMenu:

    def __init__(self):
        self.pluginsHandler = None

    def upateMenu(self, treeNode, dataTreeView, menu):

        idsName = None

        if treeNode.getIDSName() is not None:
            # If the item/subject is IDS get the IDS name"""
            idsName = treeNode.getIDSName()

        # Set plugins handler. Pass the dataTreeView and item/subject to the
        # QVizPluginsHandler
        self.pluginsHandler = QVizPluginsHandler(dataTreeView, treeNode)
        self.pluginsHandler.updateMenu(menu, dataTreeView, treeNode)
