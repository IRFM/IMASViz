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

        dtv = self.api.CreateDataTree(dataSource)

        self.api.ShowDataTree(dtv)
        #self.test(dtv)

    def test(self, dtv):
        # Check if necessary system variables are set
        from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
        QVizGlobalOperations.checkEnvSettings()

        # Set Application Program Interface
        from imasviz.Viz_API import Viz_API
        from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
        api = Viz_API()

        # Set data source retriever/factory
        dataSourceFactory = QVizDataSourceFactory()

        from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues
        # Load IMAS database
        dataSource = dataSourceFactory.create(
            dataSourceName=QVizGlobalValues.IMAS_NATIVE,
            shotNumber=54178,
            runNumber=0,
            userName='imas_public',
            imasDbName='west')

        #dtv.show()
        # Build the data tree view frame
        #f = api.CreateDataTree(dataSource)

        #api.LoadIDSData(self, 'magnetics', 0, 0)
        from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadSelectedData import QVizLoadSelectedData
        QVizLoadSelectedData(dtv.dataTreeView, 'magnetics', 0, 0).execute()
        #self.show()