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
# *****************************************************************************
#     Copyright(c) 2016- F. Ludovic, L. xinyi, D. Penko
# *****************************************************************************

from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand


class QVizSelectSignal(QVizAbstractCommand):
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
    def __init__(self, dataTreeView, treeNode=None):
        QVizAbstractCommand.__init__(self, dataTreeView, treeNode)

    def execute(self):
        key = self.dataTreeView.dataSource.dataKey(self.treeNode)
        # Set the node selection status
        self.nodeData['isSelected'] = 1

        # Set variable representing the currently tagged selected item in DTV
        selectedItem = self.dataTreeView.selectedItem
        # Set the tree item text color
        selectedItem.setStyleWhenSelected()
        # Give the order of user selection
        index = len(self.dataTreeView.selectedSignalsDict) - 1
        # Add a data dictionary of signal parameters to array of
        # data dictionaries of all selected signals
        # (should replace self.dataTreeView.selectedSignals)
        self.dataTreeView.selectedSignalsDict[key] = \
            {'index'            : index,
             'QTreeWidgetItem'  : selectedItem,
             'uri'       : self.dataTreeView.dataSource.uri}
