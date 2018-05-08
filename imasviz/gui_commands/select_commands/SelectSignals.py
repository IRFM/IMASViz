from imasviz.gui_commands.AbstractCommand import AbstractCommand
#from imasviz.view.WxSignalsTreeView import IDSSignalTreeFrame
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.gui_commands.select_commands.LoadSelectedData import LoadSelectedData
import threading
import os

class SelectSignals(AbstractCommand):
    def __init__(self, view, pathsList):
        AbstractCommand.__init__(self, view, None)
        self.pathsList = pathsList

    def execute(self):
        IDSNames = []
        for path in self.pathsList:
            IDSName = path.split('/').pop(0)
            if IDSName not in IDSNames:
                IDSNames.append(IDSName)

        #Load all IDS data which are referenced in the paths
        e = threading.Event() #the command SelectSignals is synchronous so we will wait that this event is set
        self.LoadMultipleIDSData(IDSNames, threadingEvent=e)

    # Load IDSs data for the given data tree frame
    def LoadMultipleIDSData(self, IDSNamesList, occurrence=0, threadingEvent=None):
        for IDSName in IDSNamesList:
            self.view.setIDSNameSelected(IDSName)
            LoadSelectedData(self.view, occurrence, self.pathsList, threadingEvent).execute()