from imasviz.gui_commands.AbstractCommand import AbstractCommand
from imasviz.view.WxSignalsTreeView import IDSSignalTreeFrame
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.gui_commands.select_commands.LoadSelectedData import LoadSelectedData
import threading
import os

class SelectSignals(AbstractCommand):
    def __init__(self, view, dataTreeFrame, pathsList):
        AbstractCommand.__init__(self, view, None)
        self.pathsList = pathsList
        self.dataTreeFrame = dataTreeFrame

    def execute(self):
        IDSNames = []
        for path in self.pathsList:
            IDSName = path.split('/').pop(0)
            if IDSName not in IDSNames:
                IDSNames.append(IDSName)
                
        #Load all IDS data which are referenced in the paths
        e = threading.Event() #the command SelectSignals is synchronous so we will wait that this event is set
        self.LoadMultipleIDSData(self.dataTreeFrame, IDSNames, threadingEvent=e)

        #Creating the signals tree
        # signalsFrame = IDSSignalTreeFrame(None, self.view,
        #                                   str(self.view.shotNumber), GlobalOperations.getIDSDefFile(os.environ['IMAS_DATA_DICTIONARY_VERSION']))
        # for s in self.pathsList:
        #     #print 'path = ' + s
        #     n = signalsFrame.tree.selectNodeWithPath(s)
        #     if n == None:
        #         print 'Path: ' + s + " not found"
                
    # Load IDSs data for the given data tree frame
    def LoadMultipleIDSData(self, dataTreeFrame, IDSNamesList, occurrence=0, threadingEvent=None):
        for IDSName in IDSNamesList:
            dataTreeFrame.wxTreeView.setIDSNameSelected(IDSName)
            LoadSelectedData(self.view, occurrence, self.pathsList, threadingEvent).execute()
            #self.LoadIDSData(dataTreeFrame, IDSName, occurrence, threadingEvent)

    # def LoadIDSData(self, dataTreeFrame, IDSName, occurrence=0, threadingEvent=None):
    #     dataTreeFrame.wxTreeView.setIDSNameSelected(IDSName)
    #     LoadSelectedData(self.view, occurrence, threadingEvent).execute()