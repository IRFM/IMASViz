import os

from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource
from imasviz.VizUtils import QVizGlobalValues


# A factory for creating native data-source for IMAS
class QVizDataSourceFactory:

    def __init__(self, legacy_attributes=None):
        if QVizIMASDataSource.getVersion() == 4:
            if legacy_attributes is None or len(legacy_attributes) == 0:
                raise ValueError("Creating a datasource using AL4 required legacy parameters in the datasource factory.")
        self.legacy_attributes = legacy_attributes

    def create(self, uri):
        dataSource = QVizIMASDataSource(QVizGlobalValues.IMAS_NATIVE, uri)
        if QVizIMASDataSource.getVersion() == 4:
            if self.legacy_attributes is not None and len(self.legacy_attributes) > 0:
                dataSource.legacy_attributes = self.legacy_attributes
        return dataSource

