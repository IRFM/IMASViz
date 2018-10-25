import os

from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory

from imasviz.Viz_API import Viz_API
from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues


class QVizOpenShotView:
    def __init__(self):
        self.api = Viz_API()

    def Open(self, evt, dataSourceName, imasDbName, userName, shotNumber, runNumber):
        self.dataSourceName = dataSourceName
        self.imasDbName = imasDbName
        self.userName = userName
        self.shotNumber = shotNumber
        self.runNumber = runNumber
        if self.dataSourceName == QVizGlobalValues.IMAS_NATIVE:
            """Try to open the specified IDS database """
            QVizIMASDataSource.try_to_open(self.imasDbName,
                                           self.userName,
                                           int(self.shotNumber),
                                           int(self.runNumber))

            for i in range(0, 10):
                vname = "MDSPLUS_TREE_BASE_" + str(i)
                mds = os.environ['HOME'] + "/public/imasdb/" \
                      + self.imasDbName + "/3/" + str(i)
                os.environ[vname] = mds


        dataSource = QVizDataSourceFactory().create(shotNumber=self.shotNumber,
                                                    runNumber=self.runNumber,
                                                    userName=self.userName,
                                                    imasDbName=self.imasDbName,
                                                    dataSourceName=self.dataSourceName)

        # api = Viz_API()
        dtv = self.api.CreateDataTree(dataSource)
        self.api.ShowDataTree(dtv)

