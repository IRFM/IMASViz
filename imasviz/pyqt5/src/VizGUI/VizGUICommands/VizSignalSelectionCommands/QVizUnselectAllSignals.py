#  Name   : QVizUnselectAllSignals
#
#          Container to handle the unselection of all selected signals (PyQt5).
#          Note: The wxPython predecessor of this Python file is
#          UnselectAllSignals.py
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

class QVizUnselectAllSignals(AbstractCommand):
    def __init__(self, dataTreeView):
        AbstractCommand.__init__(self, dataTreeView)

    def execute(self):
        # Set empty list of signal keys to remove
        keysToRemove = []
        for key in self.dataTreeView.selectedSignalsDict:
            signalDict = self.dataTreeView.selectedSignalsDict[key]

            # Signal/Node itemVIZData attribute
            signalItemVIZData = signalDict['nodeData']
            # Signal/Node associated QTreeWidget object
            signalTreeItem = signalDict['QTreeWidgetItem']
            # Search through the whole list of signals (all FLT_1D nodes etc.)
            for s in self.dataTreeView.signalsList:
                # If the itemVIZData matches, add the signal key to the list
                # of keys for removal
                if signalItemVIZData == s.itemVIZData:
                    # Set the signal isSelected attribute/status
                    signalItemVIZData['isSelected'] = 0
                    # Set the QTreeWidgetItem foreground color to blue
                    signalTreeItem.setForeground(0, GlobalColors.BLUE)
                    key = self.dataTreeView.dataSource.dataKey(signalItemVIZData)
                    keysToRemove.append(key)
                    break
        # Go through the list of selected signals and delete all of them from
        # the same list
        for i in range(0, len(self.dataTreeView.selectedSignalsDict)):
            key = keysToRemove[i]
            # Delete the signal from selectedSignalsDict list
            del self.dataTreeView.selectedSignalsDict[key]