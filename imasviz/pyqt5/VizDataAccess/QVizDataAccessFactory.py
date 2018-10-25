# from imasviz.data_source.IMASDataSource import ETNativeDataTree
# from imasviz.VizDataSource.ToreSupraDataSource import ETDataTreeFromXML
# import os
from imasviz.pyqt5.VizDataAccess.QVizTSDataAccess import TSSignalAccess

from imasviz.pyqt5.VizDataAccess.QVizIMASNativeDataAccess import IMASNativeSignalAccess
from imasviz.util.GlobalValues import GlobalValues


class SignalDataAccessFactory:

    def __init__(self, dataSource):
        self.dataSource = dataSource

    def create(self):
        if self.dataSource.name==GlobalValues.TORE_SUPRA:
            return TSSignalAccess(self.dataSource)

        elif self.dataSource.name == GlobalValues.IMAS_NATIVE or self.dataSource.name == GlobalValues.IMAS_UDA:
            return IMASNativeSignalAccess(self.dataSource)



