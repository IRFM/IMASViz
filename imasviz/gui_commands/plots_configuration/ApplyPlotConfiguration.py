#This class has been generated automatically by the IMAS_VIZ application
from imasviz.Browser_API import Browser_API
from imasviz.data_source.DataSourceFactory import DataSourceFactory
import wx
from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalOperations import GlobalOperations


class ApplyPlotConfiguration():

    def __init__(self, dataTreeFrame, paths, plotConfig):
        self.dataTreeFrame = dataTreeFrame
        self.paths = paths
        self.plotConfig = plotConfig

    def execute(self):
        api = Browser_API()
        dataSource = self.dataTreeFrame.wxTreeView.dataSource
        api.SelectSignals(self.dataTreeFrame, self.paths)
        api.PlotSelectedSignalsInMultiFrame(self.dataTreeFrame)

        for frame in self.dataTreeFrame.wxTreeView.imas_viz_api.multiPlotsFrames:

            for key in frame.panels:
                panel = frame.panels[key]
                panel.set_title(self.plotConfig.frame.panel[key].title)
                panel.set_ylabel(panel.ylabel)
                panel.set_y2label(panel.y2label)
                trace_index = 0
                for trace in self.plotConfig.panel.traces:
                    panel.conf.set_trace_color(trace.color, trace_index)
                    trace_index = trace_index + 1


