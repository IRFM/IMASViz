from imasviz.Browser_API import Browser_API


class ApplyPlotConfiguration:

    def __init__(self, dataTreeFrame, paths, plotConfig):
        self.dataTreeFrame = dataTreeFrame
        self.paths = paths
        self.plotConfig = plotConfig

    def execute(self):
        api = Browser_API()
        api.SelectSignals(self.dataTreeFrame, self.paths)
        api.PlotSelectedSignalsInMultiPlotFrame(self.dataTreeFrame, 0, 0, plotConfig=self.plotConfig)