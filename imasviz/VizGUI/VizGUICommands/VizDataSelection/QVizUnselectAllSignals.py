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
# *****************************************************************************
#     Copyright(c) 2016- F. Ludovic, L. xinyi, D. Penko
# *****************************************************************************

from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand


class QVizUnselectAllSignals(QVizAbstractCommand):
    def __init__(self, dataTreeView, all_DTV=False):
        QVizAbstractCommand.__init__(self, dataTreeView)
        self.all_DTV = all_DTV
        self.imas_viz_api = self.dataTreeView.imas_viz_api

    def execute(self):

        # If signals from all DTV are to be unselected, use the list of all
        # existing DTVs. Otherwise use current DTV.
        DTVList = []
        if self.all_DTV is not True:
            DTVList.append(self.dataTreeView)
        else:
            DTVList = self.imas_viz_api.DTVlist

        # Go through the set list of DTVs
        for dtv in DTVList:
            # Set empty list of signal keys to remove
            keysToRemove = []
            for key in dtv.selectedSignalsDict:
                v = dtv.selectedSignalsDict[key]
                # Signal/Node associated QTreeWidget object
                vizTreeNode = v['QTreeWidgetItem']

                # Signal/Node itemVIZData attribute
                signalItemVIZData = vizTreeNode.getInfoDict()

                # Search through the whole list of signals (all FLT_1D nodes etc.)
                for s in dtv.signalsList:
                    # If the itemVIZData matches, add the signal key to the
                    # list of keys for removal
                    if signalItemVIZData == s.getData():
                        # Set the signal isSelected attribute/status
                        signalItemVIZData['isSelected'] = 0
                        # Set the QTreeWidgetItem foreground color to blue
                        vizTreeNode.setStyleWhenContainingData()
                        key = dtv.dataSource.dataKey(vizTreeNode)
                        keysToRemove.append(key)
                        break
            # Go through the list of selected signals and delete all of them
            # from the same list
            for i in range(0, len(dtv.selectedSignalsDict)):
                key = keysToRemove[i]
                # Delete the signal from selectedSignalsDict list
                del dtv.selectedSignalsDict[key]
