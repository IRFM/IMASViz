from imasviz.VizDataAccess.QVizTSDataAccess import TSSignalAccess

from imasviz.VizDataAccess.QVizIMASNativeDataAccess import IMASNativeSignalAccess
from imasviz.VizUtils.GlobalValues import GlobalValues


class SignalDataAccessFactory:

    def __init__(self, dataSource):
        self.dataSource = dataSource

    def create(self):
        if self.dataSource.name==GlobalValues.TORE_SUPRA:
            return TSSignalAccess(self.dataSource)

        elif self.dataSource.name == GlobalValues.IMAS_NATIVE or self.dataSource.name == GlobalValues.IMAS_UDA:
            return IMASNativeSignalAccess(self.dataSource)



