
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
# *****************************************************************************
#  TODO:
#
#    - class HandleRightClickAndShiftDown definition
#
# *****************************************************************************
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
# *****************************************************************************

from PyQt5.QtWidgets import QMenu
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizLoadDataHandling import QVizLoadDataHandling
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling import QVizSignalHandling
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizPluginsPopUpMenu import QVizPluginsPopUpMenu


class QVizHandleRightClick:
    """ Handle the mouse right click event on a PyQt5 QTreeWidget.
    TODO: currently the right click menu creation is done in QVizSignalHandling
          (as right click are currently performed only on signal nodes).
    """

    def execute(self, node, dataTreeView):
        """
        Arguments:
            node (QVizTreeNode) : Item (node) from in the QTreeWidget.
            dataTreeView (QVizDataTreeView) : DataTreeView object to which the
            node belongs.
        """

        self.popupmenu = dataTreeView.popupmenu
        if self.popupmenu is None:
            self.popupmenu = QMenu()
        else:
            self.popupmenu.clear()

        # Show tool tips that are set to menu actions etc.
        self.popupmenu.setToolTipsVisible(True)

        showMenu = False

        # If the node is a signal and occurrence contains data, call
        # showPopUpMenu function for plotting data
        if not node.isIDSRoot() and node.hasAvailableData():
            handling = QVizSignalHandling(dataTreeView=dataTreeView)
            self.popupmenu = handling.buildContextMenu(node)
            showMenu = True
        else:
            # If the node is a IDS node, call showPopMenu for loading IDS data
            if node.isIDSRoot() and node.hasAvailableData():
                subMenu = QMenu('Get (display one time slice only if any) ' + node.getIDSName() +
                                ' data for occurrence')
                self.popupmenu.addMenu(subMenu)
                QVizLoadDataHandling().updateMenu(node, dataTreeView, subMenu)
                
                subMenu1 = QMenu('Get (display all time slices if any) ' + node.getIDSName() +
                                ' data for occurrence')
                self.popupmenu.addMenu(subMenu1)
                QVizLoadDataHandling().updateMenu(node, dataTreeView, subMenu1, loadingStrategy="All time slices")
                
                subMenu2 = QMenu('Get (display 1 over 10 time slices if any) ' + node.getIDSName() +
                                ' data for occurrence')
                self.popupmenu.addMenu(subMenu2)
                QVizLoadDataHandling().updateMenu(node, dataTreeView, subMenu2, loadingStrategy="One over 10 time slices")
                
                self.sub_menu = QMenu('Plugins')
                self.popupmenu.addMenu(self.sub_menu)
                QVizPluginsPopUpMenu().upateMenu(node, dataTreeView,
                                                 self.sub_menu)
                showMenu = True

        if showMenu:
            self.popupmenu.exec_(
                dataTreeView.viewport().mapToGlobal(dataTreeView.pos))
