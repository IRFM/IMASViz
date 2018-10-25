import imas

from imasviz.pyqt5.VizDataSource.QVizIMASDataSource import IMASDataSource, GeneratedClassFactory


class IMASPublicDataSource(IMASDataSource):

    def __init__(self, name, machineName, shotNumber, runNumber):
        IMASDataSource.__init__(self, name, None, None, shotNumber, runNumber, machineName)

    # Load IMAS data using IMAS api
    def load(self, view, occurrence=0, pathsList = None, async=True):
        print ("Loading data using UDA")
        self.generatedDataTree = GeneratedClassFactory(self, view, occurrence, pathsList, async).create()
        if self.ids.get(occurrence) is None:
            self.ids = imas.ids(self.shotNumber, self.runNumber, 0, 0)
            self.ids.open_public(self.machineName)

        self.generatedDataTree.ids = self.ids.get(occurrence)
        view.dataCurrentlyLoaded[occurrence] = True
        view.idsAlreadyFetched[view.IDSNameSelected] = 1

        if async == True:
            self.generatedDataTree.start()  # This will call asynchroneously the get() operation for fetching IMAS data
        else:
            self.generatedDataTree.run()  # This will call the get() operation for fetching IMAS data

    # This defines the unique key attached to each data which can be plotted
    def dataKey(self, nodeData):
        return self.name + "::" + self.machineName + "::" + str(self.shotNumber) + "::" + str(self.runNumber) + '::' + nodeData['Path']

    def getShortLabel(self):
        return self.machineName + ":" + str(self.shotNumber) + ":" + str(self.runNumber)