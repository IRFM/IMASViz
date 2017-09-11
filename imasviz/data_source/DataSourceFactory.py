from imasviz.data_source.IMASDataSource import IMASDataSource, IMASPublicDataSource
#from imasviz.data_source.ToreSupraDataSource import ToreSupraDataSource
from imasviz.util.GlobalValues import GlobalValues


#A factory for creating a Tore-Supra or MDS+ native data-source for IMAS
class DataSourceFactory:

    def __init__(self):
        pass

    def create(self, shotNumber, runNumber = 0, userName = None, imasDbName = None, name=GlobalValues.IMAS_NATIVE):
        
        # if name==GlobalValues.TORE_SUPRA:
        #     dataSource = ToreSupraDataSource(name, shotNumber, runNumber)
        #     return dataSource

        if name == GlobalValues.IMAS_NATIVE:
            dataSource = IMASDataSource(name, userName, imasDbName, shotNumber, runNumber)
            return dataSource

        else:
            raise ValueError("Data source '" +  name + "' is unknown")



    # def create(self, shotNumber, runNumber=0, imasDbName=None, name=GlobalValues.IMAS_UDA):
    #
    #     if name == GlobalValues.TORE_SUPRA:
    #         raise ValueError("Tore-Supra data is not supported by UDA")
    #
    #     elif name == GlobalValues.IMAS_UDA:
    #         dataSource = IMASPublicDataSource(name, imasDbName, shotNumber, runNumber)
    #         return dataSource