import imas
from PySide2.QtWidgets import QProgressBar
from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource, QVizGeneratedClassFactory


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
        self.progressBar = QProgressBar()
        self.progressBar.setWindowTitle("Loading '" + IDSName + "'...")

        self.progressBar.setMaximum(0)
        self.progressBar.setMinimum(0)
        self.progressBar.setGeometry(100, 150, 500, 25)
        self.progressBar.show()
        self.generatedDataTree = QVizGeneratedClassFactory(self, dataTreeView,
                                                           IDSName,
                                                           occurrence,
                                                           asynch).create(self.progressBar)
        print("*: self.ids: ", self.ids)
        if self.data_entries.get(occurrence) is None:
            self.data_entries[occurrence] = imas.ids(self.shotNumber, self.runNumber,
                                            0, 0)
            self.data_entries[occurrence].open_public(self.machineName)

        self.generatedDataTree.ids = self.data_entries.get(occurrence)

        if asynch == True:
            self.generatedDataTree.start()  # This will call asynchroneously the get() operation for fetching IMAS data
        else:
            self.generatedDataTree.run()  # This will call the get() operation for fetching IMAS data

    # This defines the unique key attached to each data which can be plotted
    def dataKey(self, vizTreeNode):
        return self.name + "::" + self.machineName + "::" + str(self.shotNumber) + "::" + str(self.runNumber) + '::' + vizTreeNode.getPath()

    def getShortLabel(self):
        return "UDA: " + self.machineName + ":" + str(self.shotNumber) + ":" + str(self.runNumber)

    def getLongLabel(self):
        return "(UDA) Database:" + self.machineName + " Shot:" + str(self.shotNumber) + " Run:" + str(self.runNumber)

    def open(self, imas_entry):
        imas_entry.open_public(self.machineName)


    def containsData(self, node, imas_entry):
        node.setAvailableIDSData(0, True)
        return True
