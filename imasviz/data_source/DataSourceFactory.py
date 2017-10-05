from imasviz.data_source.IMASDataSource import IMASDataSource, IMASPublicDataSource
#from imasviz.data_source.ToreSupraDataSource import ToreSupraDataSource
from imasviz.util.GlobalValues import GlobalValues


#A factory for creating a Tore-Supra or MDS+ native data-source for IMAS
class DataSourceFactory:

    def __init__(self):
        pass

    def create(self, shotNumber, runNumber = 0, name=GlobalValues.IMAS_NATIVE, uda=False):
        self.create(shotNumber, runNumber, None, None, name, uda)

    def create(self, shotNumber, runNumber = 0, userName = None, imasDbName = None, name=GlobalValues.IMAS_NATIVE, uda=False):

        if uda == False:
            if name == GlobalValues.IMAS_NATIVE:
                dataSource = IMASDataSource(name, userName, imasDbName, shotNumber, runNumber)
                return dataSource

            elif name==GlobalValues.TORE_SUPRA:
                raise ValueError("Tore-Supra is not currently available")
                #dataSource = ToreSupraDataSource(name, shotNumber, runNumber)
                #return dataSource

            else:
                raise ValueError("Data source '" + name + "' is unknown")

        else:

            if name == GlobalValues.WEST:
                dataSource = IMASPublicDataSource(name, imasDbName, shotNumber, runNumber)
                return dataSource
            else:
                raise ValueError("UDA public data base '" + name + "' is not supported by UDA")



    # def create(self, shotNumber, runNumber=0, imasDbName=None, name=GlobalValues.IMAS_UDA):
    #
    #     if name == GlobalValues.TORE_SUPRA:
    #         raise ValueError("Tore-Supra data is not supported by UDA")
    #
    #     elif name == GlobalValues.IMAS_UDA:
    #         dataSource = IMASPublicDataSource(name, imasDbName, shotNumber, runNumber)
    #         return dataSource