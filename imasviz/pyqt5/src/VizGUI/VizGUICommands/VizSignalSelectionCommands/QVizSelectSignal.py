#  Name   : QVizSelectSignal
#
#          Container to handle signal selection (PyQt5).
#          Note: The wxPython predecessor of this Python file is
#          SelectSignal.py
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- F. Ludovic, L. xinyi, D. Penko
#****************************************************

from imasviz.gui_commands.AbstractCommand import AbstractCommand
from imasviz.util.GlobalValues import GlobalColors

class QVizSelectSignal(AbstractCommand):
    """Select the signal (selectable node - BLUE). If no treeItem is
    given for selection, the self.dataTreeView.selectedItem (set by left/right
    click on item in DTV) will be used.

    Arguments:
        dataTreeView (QTreeWidget)     : DataTreeView object of the QTreeWidget.
        nodeData     (itemVIZData)     : QTreeWidgetItem dictionary with data.
        treeItem     (QTreeWidgetItem) : QTreeWidgetItem to be selected. If not
                                         specified, the selected item, obtained
                                         by either left or right click on the
                                         item in the DTV, will be used
                                         (self.dataTreeView.selectedItem).
    """
    def __init__(self, dataTreeView, nodeData = None, treeItem = None):
        AbstractCommand.__init__(self, dataTreeView, nodeData)

        self.treeItem = treeItem

    def execute(self):
        self.updateNodeData();
        key = self.dataTreeView.dataSource.dataKey(self.nodeData)
        # Set the node selection status
        self.nodeData['isSelected'] = 1

        # Use DTV selected item if tree item is not present
        if self.treeItem != None:
            selectedItem = self.treeItem
        else:
            selectedItem = self.dataTreeView.selectedItem

        # Set the tree item color
        selectedItem.setForeground(0, GlobalColors.RED)
        # Give the order of user selection
        index = len(self.dataTreeView.selectedSignals) - 1
            # Add selected signal to 'selectedSignals list'. Order of parameters:
            # - shot number
            # - node data
            # - index
            # - shot number
            # - IDS database name
            # - user name
            # - selected signals QTreeWidgetItem
        self.dataTreeView.selectedSignals[key] = \
            (self.dataTreeView.dataSource.shotNumber,
             self.nodeData,
             index,
             self.dataTreeView.dataSource.runNumber,
             self.dataTreeView.dataSource.imasDbName,
             self.dataTreeView.dataSource.userName,
             selectedItem)# tuple
