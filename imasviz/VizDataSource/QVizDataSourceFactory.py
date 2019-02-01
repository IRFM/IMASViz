from imasviz.VizDataSource.QVizToreSupraDataSource import ToreSupraDataSource
from imasviz.VizDataSource.QvizIMASPublicDataSource import QVizIMASPublicDataSource

from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues


#A factory for creating a Tore-Supra or MDS+ native data-source for IMAS
class QVizDataSourceFactory:

    def __init__(self):
        pass

    def createUDADatasource(self, UDAMachineName, shotNumber, runNumber = 0):
        return self.create(shotNumber, runNumber, None, None,
                           QVizGlobalValues.IMAS_UDA, UDAMachineName)

    def create(self, shotNumber, runNumber = 0, userName = None,
               imasDbName = None, dataSourceName = QVizGlobalValues.IMAS_NATIVE,
               machineName = None):

        if dataSourceName == None or dataSourceName == '':
            raise ValueError(
                "A datasource name is required for creating a datasource")

        if dataSourceName == QVizGlobalValues.IMAS_NATIVE:
            dataSource = QVizIMASDataSource(dataSourceName, userName, imasDbName,
                                            shotNumber, runNumber)
            return dataSource

        elif dataSourceName == QVizGlobalValues.TORE_SUPRA:
            #raise ValueError("Tore-Supra datasource is not currently available")
            dataSource = ToreSupraDataSource(QVizGlobalValues.TORE_SUPRA,
                                             shotNumber, runNumber)
            return dataSource

        else: # UDA datasource

            if machineName == None or machineName == '':
                raise ValueError("A machine name is required for UDA datasource")

            elif machineName in QVizGlobalValues.ExternalSources:
                #print "Creating QVizIMASPublicDataSource..."
                dataSource = QVizIMASPublicDataSource(dataSourceName, machineName,
                                                      shotNumber, runNumber)
                return dataSource
            else:
                raise ValueError("UDA public datasource '" + machineName
                    + "' is not supported by UDA")
