import imas
from PySide6.QtWidgets import QProgressBar
from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource, QVizGeneratedClassFactory


class QVizIMASPublicDataSource(QVizIMASDataSource):

    def __init__(self, name, uri):

        super(QVizIMASPublicDataSource, self).__init__(name, uri)

    # Load IMAS data using IMAS api
    def load(self, dataTreeView, IDSName, occurrence=0, viewLoadingStrategy=None, asynch=True):
        print("Loading data using UDA")
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

        self.generatedDataTree.dataSource = self

        if asynch:
            self.generatedDataTree.start()  # This will call asynchroneously the get() operation for fetching IMAS data
        else:
            self.generatedDataTree.run()  # This will call the get() operation for fetching IMAS data

    # This defines the unique key attached to each data which can be plotted
    def dataKey(self, vizTreeNode):
        return self.name + "::" + self.uri +  '::' + vizTreeNode.getPath()

    def getShortLabel(self):
        return self.uri

    def getLongLabel(self):
        return "UDA URI:" + self.uri

    def open(self, data_entry):
        data_entry.open()

    def containsData(self, node):
        node.setAvailableIDSData(0, True)
        return True
