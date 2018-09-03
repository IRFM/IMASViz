import os
from imasviz.data_source.DataSourceFactory import DataSourceFactory
from imasviz.Browser_API import Browser_API
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.util.GlobalValues import GlobalValues
from imasviz.data_source.IMASDataSource import IMASDataSource

class QtOpenShotView():
    def __init__(self, dataSourceName, imasDbName, userName, shotNumber, runNumber):
        self.dataSourceName = dataSourceName
        self.imasDbName = imasDbName
        self.userName = userName
        self.shotNumber = shotNumber
        self.runNumber = runNumber

    def Open(self, evt):
        if self.dataSourceName == GlobalValues.IMAS_NATIVE:
            """Try to open the specified IDS database """
            IMASDataSource.try_to_open(self.imasDbName,
                                       self.userName,
                                       int(self.shotNumber),
                                       int(self.runNumber))

            for i in range(0, 10):
                vname = "MDSPLUS_TREE_BASE_" + str(i)
                mds = os.environ['HOME'] + "/public/imasdb/" \
                      + self.imasDbName + "/3/" + str(i)
                os.environ[vname] = mds


        dataSource = DataSourceFactory().create(shotNumber=self.shotNumber,
                                              runNumber=self.runNumber,
                                              userName=self.userName,
                                              imasDbName=self.imasDbName,
                                              dataSourceName=self.dataSourceName)

        api = Browser_API()
        dtv = api.CreateDataTree(dataSource)
        api.ShowDataTree(dtv)

