from imasviz.data_source.IMASDataSource import IMASDataSource, IMASPublicDataSource
from imasviz.data_source.ToreSupraDataSource import ToreSupraDataSource
from imasviz.util.GlobalValues import GlobalValues


#A factory for creating a Tore-Supra or MDS+ native data-source for IMAS
class DataSourceFactory:

    def __init__(self):
        pass

    def createUDADatasource(self, shotNumber, runNumber = 0, machineName=None):
        return self.create(shotNumber, runNumber, None, None,
                           GlobalValues.IMAS_UDA, machineName)

    def create(self, shotNumber, runNumber = 0, userName = None,
               imasDbName = None, dataSourceName = GlobalValues.IMAS_NATIVE,
               machineName = None):

        if dataSourceName == None or dataSourceName == '':
            raise ValueError(
                "A datasource name is required for creating a datasource")

        if dataSourceName == GlobalValues.IMAS_NATIVE:
            dataSource = IMASDataSource(dataSourceName, userName, imasDbName,
                                        shotNumber, runNumber)
            return dataSource

        elif dataSourceName == GlobalValues.TORE_SUPRA:
            #raise ValueError("Tore-Supra datasource is not currently available")
            dataSource = ToreSupraDataSource(GlobalValues.TORE_SUPRA,
                                            shotNumber, runNumber)
            return dataSource

        else: # UDA datasource

            if machineName == None or machineName == '':
                raise ValueError("A machine name is required for UDA datasource")

            elif machineName == GlobalValues.WEST:
                #print "Creating IMASPublicDataSource..."
                dataSource = IMASPublicDataSource(dataSourceName, machineName,
                                                  shotNumber, runNumber)
                return dataSource
            else:
                raise ValueError("UDA public datasource '" + machineName
                    + "' is not supported by UDA")