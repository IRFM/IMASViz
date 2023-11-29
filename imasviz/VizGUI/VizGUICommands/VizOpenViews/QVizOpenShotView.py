import os

from imasviz.Viz_API import Viz_API
from imasviz.VizUtils import QVizGlobalValues


class QVizOpenShotView:
    def __init__(self, parent=None):
        self.api = Viz_API(parent)

    def Open(self, evt, uri):
                 
        from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
        from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource
        
        dataSource = QVizDataSourceFactory().create(uri)

        dtv = None
        if self.api.isDataSourceAlreadyOpened(dataSource):
            dtv = self.api.GetDTVFor(dataSource.getKey())
        else:
            dtv = self.api.CreateDataTree(dataSource)

        self.api.ShowDataTree(dtv)
