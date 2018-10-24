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

from imasviz.gui_commands.AbstractCommand import AbstractCommand
from imasviz.pyqt5.src.VizGUI.VizGUICommands.VizSignalSelectionCommands.QVizSelectSignal \
    import QVizSelectSignal
from imasviz.gui_commands.select_commands.LoadSelectedData import LoadSelectedData
import threading


class QVizSelectSignals(AbstractCommand):
    """Select a group of all signals by given list of signal paths.
    """
    def __init__(self, dataTreeView, pathsList, occurrence=0):
        """
        Arguments:
            dataTreeView (QTreeWidget) : QTreeWidget object (DTV tree widget).
            nodeData     (array)       : A list if signal paths (e.g.
                                         ['magnetics/flux_loop(0)/flux/data'])
            occurrence   (int)         : IDS occurrence number (default = 0).
        """
        AbstractCommand.__init__(self, dataTreeView)
        self.pathsList = pathsList
        self.occurrence = occurrence

        # Check if required IDS root tree items are opened
        self.checkIDSOpen()

    def execute(self):
        # Go through the list of signals and compare their path attribute with
        # the paths from the given list
        for signal in self.dataTreeView.signalsList:
            # Get the path attribute of the signal
            sigName = signal.itemVIZData['Path']
            # When the signal path matches the path from the given list,
            # select the signal
            if any(sigName in s for s in self.pathsList):
                # Tag the signal as current DTV selected item
                self.dataTreeView.selectedItem = signal
                # Select the tree item corresponding to the signal
                QVizSelectSignal(dataTreeView=self.dataTreeView,
                                 nodeData=signal.itemVIZData).execute()

    def checkIDSOpen(self):
        """Check if the IDS (or IDSs) root tree item is opened/populated. If
        it is not, open it.
        Note: It requires open IDS root tree item in order to have the required
        signalsList populated.
        """

        # Set empty list of IDS names
        IDSNamesList = []
        # Go through the list of paths and extract all different IDS names
        # E.g. 'magnetics', 'core_profiles', 'edge_profiles' etc.
        for path in self.pathsList:
            # Extract the IDS name
            IDSName = path.split('/').pop(0)
            # If the extracted IDS name is already in the list don't add it
            # again
            if IDSName not in IDSNamesList:
                # Add the IDS name to the list of IDS names
                IDSNamesList.append(IDSName)

        # Load all IDS data which are referenced in the paths
        #threadingEvent = threading.Event()  # the command SelectSignals is
                                            # synchronous so we will wait that
                                            # this event is set

        threadingEvent = True

        for IDSName in IDSNamesList:
            # Set the IDS to be checked if it is opened. If it is not,open it
            # in the DTV
            self.dataTreeView.setIDSNameSelected(IDSName)
            # Check/Populate the IDS tree node
            LoadSelectedData(self.dataTreeView, self.occurrence, self.pathsList,
                threadingEvent).execute()

