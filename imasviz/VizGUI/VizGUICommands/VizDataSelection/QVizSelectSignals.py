#  Name   : QVizSelectSignals
#
#          Container to handle selection (PyQt5) of signals by
#          given explicit list of paths.
#          Note: The wxPython predecessor of this Python file is
#          SelectSignals.py (greatly redefined for simpler and more direct
#          methon on selecting the signals)
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- F. Ludovic, L. xinyi, D. Penko
#****************************************************

from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignal import QVizSelectSignal
from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadSelectedData import QVizLoadSelectedData


class QVizSelectSignals(QVizAbstractCommand):
    """Select a group of all signals by given list of signal paths.
    """

    def __init__(self, dataTreeView, pathsMap):
        """
        Arguments:
            dataTreeView (QTreeWidget) : QTreeWidget object (DTV tree widget).
            pathsMap     (dict)       : A list if signal paths (e.g.
                                         ['magnetics/flux_loop(0)/flux/data'])
        """
        QVizAbstractCommand.__init__(self, dataTreeView)
        self.pathsMap = pathsMap

    def execute(self):

        if self.pathsMap is None or self.pathsMap == {}:
            return

        # Check if required IDS root tree items are opened
        self.checkIDSOpen()

        # Go through the list of signals and compare their path attribute with
        # the paths from the given list
        # self.updateNodeData()
        for signal in self.dataTreeView.signalsList:
            # Get the path attribute of the signal
            #sigName = signal.getPath()

            # When the signal path matches the path from the given list,
            # select the signal
            pathsList = self.pathsMap.get('paths')
            occurrencesList = self.pathsMap.get('occurrences')
            #if any(sigName == s for s in pathsList):
            for i in range(0, len(pathsList)):
                selectedOccurrence = int(occurrencesList[i])
                s = pathsList[i]
                if selectedOccurrence != signal.getOccurrence():
                    continue
                if s != signal.getPath():
                    continue
                # Tag the signal as current DTV selected item
                self.dataTreeView.selectedItem = signal
                # Select the tree item corresponding to the signal
                QVizSelectSignal(dataTreeView=self.dataTreeView,
                                 nodeData=signal.getInfoDict()).execute()

    def checkIDSOpen(self):
        """Check if the IDS (or IDSs) root tree item is opened/populated. If
        it is not, open it.
        Note: It requires open IDS root tree item in order to have the required
        signalsList populated.
        """

        pathsList = self.pathsMap.get('paths')
        occurrencesList = self.pathsMap.get('occurrences')

        asynch = False  # the command SelectSignals is
        # synchronous so we will wait that
        # this event is set
        for i in range(0, len(pathsList)):

            # Extract the IDS name
            IDSName = pathsList[i].split('/').pop(0)

            if occurrencesList[i] is None:
                occurrencesList[i] = 0
            # Load all IDS data which are referenced in the paths
            if self.dataTreeView.isAlreadyFetched(IDSName, occurrencesList[i]):
                continue

            # Check/Populate the IDS tree node
            QVizLoadSelectedData(self.dataTreeView, IDSName, int(occurrencesList[i]), asynch).execute()