import os

from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource
from imasviz.VizUtils import QVizGlobalValues


# A factory for creating native data-source for IMAS
class QVizDataSourceFactory:

    def __init__(self):
        pass

    def create(self, uri):
        return QVizIMASDataSource(QVizGlobalValues.IMAS_NATIVE, uri)
