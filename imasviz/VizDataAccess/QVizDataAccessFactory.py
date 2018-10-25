from imasviz.VizDataAccess.QVizTSDataAccess import QVizTSDataAccess

from imasviz.VizDataAccess.QVizIMASNativeDataAccess import QVizIMASNativeDataAccess
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues


class QVizDataAccessFactory:

    def __init__(self, dataSource):
        self.dataSource = dataSource

    def create(self):
        if self.dataSource.name==QVizGlobalValues.TORE_SUPRA:
            return QVizTSDataAccess(self.dataSource)

        elif self.dataSource.name == QVizGlobalValues.IMAS_NATIVE or self.dataSource.name == QVizGlobalValues.IMAS_UDA:
            return QVizIMASNativeDataAccess(self.dataSource)



