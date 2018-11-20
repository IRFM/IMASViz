import os

from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory

from imasviz.Viz_API import Viz_API
from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues


class QVizOpenShotView:
    def __init__(self):
        self.api = Viz_API()

    def Open(self, evt, dataSourceName, imasDbName, userName, shotNumber, runNumber, UDAMachineName=None):

        if dataSourceName == QVizGlobalValues.IMAS_NATIVE:
            """Try to open the specified IDS database """
            QVizIMASDataSource.try_to_open(imasDbName,
                                           userName,
                                           int(shotNumber),
                                           int(runNumber))

            for i in range(0, 10):
                vname = "MDSPLUS_TREE_BASE_" + str(i)
                mds = os.environ['HOME'] + "/public/imasdb/" \
                      + imasDbName + "/3/" + str(i)
                os.environ[vname] = mds

        if UDAMachineName is not None: # UDA
            dataSource = QVizDataSourceFactory().createUDADatasource(UDAMachineName=UDAMachineName,
                                                        shotNumber=shotNumber,
                                                        runNumber=runNumber)
        else: # local IMAS pulse file
            dataSource = QVizDataSourceFactory().create(shotNumber=shotNumber,
                                                    runNumber=runNumber,
                                                    userName=userName,
                                                    imasDbName=imasDbName,
                                                    dataSourceName=dataSourceName)

        # api = Viz_API()
        dtv = self.api.CreateDataTree(dataSource)
        self.api.ShowDataTree(dtv)

