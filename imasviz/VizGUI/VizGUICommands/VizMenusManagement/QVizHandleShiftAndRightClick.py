#  Name   : QVizHandleShiftAndRightClick
#
#          Container to handle shift down + right click events in PyQt5.
#          Note: The wxPython predecessor of this Python file is
#          HandleRightClick.py
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
# *****************************************************************************
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
# *****************************************************************************

from PySide2.QtWidgets import QMenu
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
