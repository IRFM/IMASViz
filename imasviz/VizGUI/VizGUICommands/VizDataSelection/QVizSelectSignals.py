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
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations


class QVizSelectSignals(QVizAbstractCommand):
    """Select a group of all signals by given list of signal paths.
    """

    def __init__(self, dataTreeView, pathsMap):
        """
        Arguments:
            dataTreeView (QTreeWidget) : QTreeWidget object (DTV tree widget).
            pathsMap     (dict)       : A map of signal paths (e.g.
                                         ['magnetics/flux_loop(0)/flux/data', occurrence])
        """
        QVizAbstractCommand.__init__(self, dataTreeView)
        pathsMap['paths'] = QVizGlobalOperations.makeIMASPaths(pathsMap['paths'])
        self.pathsMap = pathsMap

    def execute(self):

        if self.pathsMap is None or self.pathsMap == {}:
            return

        # Check if required IDS root tree items are opened
        self.checkIDSOpen()

        pathsList = self.pathsMap.get('paths')
        # Check pathsList
        if type(pathsList) is not list:
            # Convert pathsList to a list of strings
            pathsList = self.convertPathsLists(pathsList)
        # Get list of occurrences
        occurrencesList = self.pathsMap.get('occurrences')
        # In case occurrences were not given, set and use default occurrence 0
        occurrence = None
        if occurrencesList is None:
            occurrence = 0
        elif len(occurrencesList) == 1:
            occurrence = int(occurrencesList[0])

        for i in range(0, len(pathsList)):

            # If no  occurrences list is provided, use occurrence 0
            if occurrencesList is None:
                occurrence = 0
            # Use the first occurrence if only one was given (assuming all
            # signals correspond to the same occurrence)
            elif len(occurrencesList) == 1:
                occurrence = int(occurrencesList[0])
            else:
                occurrence = int(occurrencesList[i])

            if len(occurrencesList) > 1 and (len(occurrencesList) != len(pathsList)):
                raise ValueError('The number of specified occurrences differ from the number of specified paths.')

            s = pathsList[i]
            # When the signal path matches the path from the given list,
            # select the signal
            # Go through the list of signals and compare their path attribute with
            # the paths from the given list
            for signal in self.dataTreeView.signalsList:

                if occurrence != signal.getOccurrence() or s != signal.getPath():
                    continue

                # Tag the signal as current DTV selected item
                self.dataTreeView.selectedItem = signal
                # Select the tree item corresponding to the signal
                QVizSelectSignal(dataTreeView=self.dataTreeView,
                                 treeNode=signal).execute()

    def checkIDSOpen(self):
        """Check if the IDS (or IDSs) root tree item is opened/populated. If
        it is not, load it.
        Note: It requires open IDS root tree item in order to have the required
        signalsList populated.
        """

        # Get paths list from dictionary
        pathsList = self.pathsMap.get('paths')

        # Check pathsList
        if type(pathsList) is not list:
            # Convert pathsList to a list of strings
            pathsList = self.convertPathsLists(pathsList)

        # Get list of occurrences
        occurrencesList = self.pathsMap.get('occurrences')
        # In case occurrences were not given, set and use default occurrence 0
        occurrence = None
        if occurrencesList is None:
            occurrence = 0
        elif len(occurrencesList) == 1:
            occurrence = int(occurrencesList[0])

        asynch = False  # the command SelectSignals is
        # synchronous so we will wait that
        # this event is set
        for i in range(0, len(pathsList)):

            # Extract the IDS name
            IDSName = pathsList[i].split('/').pop(0)

            # If no  occurrences list is provided, use occurrence 0
            if occurrencesList is None:
                occurrence = 0
            # Use the first occurrence if only one was given (assuming all
            # signals correspond to the same occurrence)
            elif len(occurrencesList) == 1:
                occurrence = int(occurrencesList[0])
            else:
                occurrence = int(occurrencesList[i])

            # Load all IDS data which are referenced in the paths
            api = self.dataTreeView.imas_viz_api
            if api.IDSDataAlreadyFetched(self.dataTreeView, IDSName, occurrence):
                continue

            # Check/Populate the IDS tree node
            QVizLoadSelectedData(self.dataTreeView, IDSName, int(occurrence), asynch).execute()

    @staticmethod
    def convertPathsLists(pathsList):
        """Converts the pathsList (which is actually a string) to a list
        containing a single string.

        Argument:
            pathsList (str) : Path string.
        """

        # In case a regular single string was given as path instead of an
        # array of paths, change it into an array holding a single path value
        if type(pathsList) is str:
            pathsList = [pathsList]

        return pathsList

