# from imasviz.data_source.IMASDataSource import ETNativeDataTree
# from imasviz.data_source.ToreSupraDataSource import ETDataTreeFromXML
# import os
from imasviz.signals_data_access.TSSignalAccess import TSSignalAccess
from imasviz.signals_data_access.IMASNativeSignalAccess import IMASNativeSignalAccess
from imasviz.util.GlobalValues import GlobalValues

class SignalDataAccessFactory:

    def __init__(self, dataSource):
        self.dataSource = dataSource

    def create(self):
        if self.dataSource.name==GlobalValues.TORE_SUPRA:
            return TSSignalAccess(self.dataSource)

        elif self.dataSource.name == GlobalValues.IMAS_NATIVE or self.dataSource.name == GlobalValues.IMAS_UDA:
            return IMASNativeSignalAccess(self.dataSource)



