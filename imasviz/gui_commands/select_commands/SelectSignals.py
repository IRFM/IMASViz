from imasviz.gui_commands.AbstractCommand import AbstractCommand
#from imasviz.view.WxSignalsTreeView import IDSSignalTreeFrame
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.gui_commands.select_commands.LoadSelectedData import LoadSelectedData
import threading
import os

class SelectSignals(AbstractCommand):
    """Utilities for signal selection in DTV.
    """
    def __init__(self, view, pathsList):
        """Args:
                 view      - wxDataTreeView (DTV) object
                 pathsList - A list of signal paths
        """
        AbstractCommand.__init__(self, view, None)
        self.pathsList = pathsList

    def execute(self):
        """Execute the signal selection in the DTV
        """
        # Set empty list of IDS names
        IDSNames = []
        # Go through the list of paths and extract all different IDS names
        # E.g. 'magnetics', 'core_profiles', 'edge_profiles' etc.
        for path in self.pathsList:
            # Extract the IDS name
            IDSName = path.split('/').pop(0)
            # If the extracted IDS name is already in the list don't add it
            # again
            if IDSName not in IDSNames:
                # Add the IDS name to the list of IDS names
                IDSNames.append(IDSName)

        # Load all IDS data which are referenced in the paths
        e = threading.Event()   # the command SelectSignals is synchronous so we
                                # will wait that this event is set
        # Load the required IDSs
        self.LoadMultipleIDSData(IDSNames, threadingEvent=e)

    def LoadMultipleIDSData(self, IDSNamesList, occurrence=0, threadingEvent=None):
        """Load IDSs in the given DTV.

           Args:
                 IDSNamesList   - A list containing IDS names
                                  Note: Same IDS names should not repeat!
                 occurence      -
                 threadingEvent -
        """
        for IDSName in IDSNamesList:
            # Set the IDS to be opened in the DTV
            self.view.setIDSNameSelected(IDSName)
            # Load the DTV and select the signals (marked with red color in DTV)
            LoadSelectedData(self.view, occurrence, self.pathsList,
                threadingEvent).execute()