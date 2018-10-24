from imasviz.Browser_API import Browser_API
from imasviz.data_source.QVizDataSourceFactory import DataSourceFactory
import wx
from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalOperations import GlobalOperations


class ApplyPlotConfiguration:

    def __init__(self, dataTreeFrame, paths, plotConfig):
        self.dataTreeFrame = dataTreeFrame
        self.paths = paths
        self.plotConfig = plotConfig

    def execute(self):
        api = Browser_API()
        api.SelectSignals(self.dataTreeFrame, self.paths)
        api.PlotSelectedSignalsInMultiPlotFrame(self.dataTreeFrame, 0, 0, plotConfig=self.plotConfig)