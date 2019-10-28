
#  Name   : QVizHandleRightClick
#
#          Container to handle right click events in PyQt5.
#          Note: The wxPython predecessor of this Python file is
#          HandleRightClick.py. 'HandleRightClickAndShiftDown' routine was
#          moved to separate file - QVizHandleShiftDownAndRightClick.
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
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
#****************************************************

from PyQt5.QtWidgets import QMenu
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizLoadDataHandling import QVizLoadDataHandling
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling import QVizSignalHandling
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizPluginsPopUpMenu import QVizPluginsPopUpMenu
from imasviz.VizUtils.QVizGlobalValues import GlobalColors


class QVizHandleRightClick:
    """ Handle the mouse right click event on a PyQt5 QTreeWidget.
    TODO: currently the right click menu creation is done in QVizSignalHandling
          (as right click are currently performed only on signal nodes).
    """

    def execute(self, node, dataTreeView):
        """
        Arguments:
            node (QVizTreeNode) : Item (node) from in the QTreeWidget.
            dataTreeView (QVizDataTreeView) : DataTreeView object to which the node belongs.
        """
        if dataTreeView.popupmenu is None:
            dataTreeView.popupmenu = QMenu()
        else:
            dataTreeView.popupmenu.clear()

        showMenu = False

        # If the node is a signal and occurrence contains data, call showPopUpMenu function for plotting data
        if node.isDynamicData() and node.hasAvailableData():
            handling = QVizSignalHandling(dataTreeView=dataTreeView)
            dataTreeView.popupmenu = handling.buildContextMenu(node)
            showMenu = True
        else:
            # If the node is a IDS node, call showPopMenu for loading IDS data
            if node.isIDSRoot()and node.hasAvailableData():
                subMenu = QMenu('Get ' + node.getIDSName() + ' data for occurrence')
                dataTreeView.popupmenu.addMenu(subMenu)
                QVizLoadDataHandling().updateMenu(node, dataTreeView, subMenu)
                sub_menu = QMenu('Plugins')
                dataTreeView.popupmenu.addMenu(sub_menu)
                QVizPluginsPopUpMenu().upateMenu(node, dataTreeView, sub_menu)
                showMenu = True

        if showMenu:
            dataTreeView.popupmenu.exec_(dataTreeView.viewport().mapToGlobal(dataTreeView.pos))
