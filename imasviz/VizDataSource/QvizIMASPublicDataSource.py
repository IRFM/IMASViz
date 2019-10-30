import imas

from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource, QVizGeneratedClassFactory
from imasviz.VizUtils.QVizGlobalValues import GlobalColors
import logging


class QVizIMASPublicDataSource(QVizIMASDataSource):

    def __init__(self, name, machineName, shotNumber, runNumber):

        super(QVizIMASPublicDataSource, self).__init__(name, userName=None,
                                                       imasDbName=None,
                                                       shotNumber=shotNumber,
                                                       runNumber=runNumber,
                                                       machineName=machineName)

    # Load IMAS data using IMAS api
    def load(self, dataTreeView, IDSName, occurrence=0, asynch=True):
        print ("Loading data using UDA")
        self.generatedDataTree = QVizGeneratedClassFactory(self, dataTreeView,
                                                           IDSName,
                                                           occurrence,
                                                           asynch).create()
        print("*: self.ids: ", self.ids)
        if self.ids.get(occurrence) is None:
            self.ids[occurrence] = imas.ids(self.shotNumber, self.runNumber,
                                            0, 0)
            self.ids[occurrence].open_public(self.machineName)

        self.generatedDataTree.ids = self.ids.get(occurrence)

        if asynch == True:
            self.generatedDataTree.start()  # This will call asynchroneously the get() operation for fetching IMAS data
        else:
            self.generatedDataTree.run()  # This will call the get() operation for fetching IMAS data

    # This defines the unique key attached to each data which can be plotted
    def dataKey(self, nodeData):
        return self.name + "::" + self.machineName + "::" + str(self.shotNumber) + "::" + str(self.runNumber) + '::' + nodeData['Path']

    def getShortLabel(self):
        return "UDA: " + self.machineName + ":" + str(self.shotNumber) + ":" + str(self.runNumber)

    def getLongLabel(self):
        return "(UDA) Tokamak:" + self.machineName + " Shot:" + str(self.shotNumber) + " Run:" + str(self.runNumber)

    def open(self, imas_entry):
        imas_entry.open_public(self.machineName)


    def containsData(self, node, imas_entry):
        node.setAvailableIDSData(0, True)
        return True