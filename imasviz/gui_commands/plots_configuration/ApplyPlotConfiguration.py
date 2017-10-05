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
                print 'key: ' + str(key)

                panel = frame.panels[key]
                configPanels = self.plotConfig.findall(".//*[@key='" + str(key)+ "']")
                configurationPanel = configPanels[0]
                panel.set_title(configurationPanel.get('title'))

                panel.set_ylabel(configurationPanel.get('ylabel'))
                panel.set_y2label(configurationPanel.get('y2label'))

                configTraces = self.plotConfig.findall(".//*[@key='" + str(key) + "']/trace")

                for i in range(0, len(panel.conf.lines)):
                    configTrace = configTraces[i]
                    panel.conf.set_trace_color(configTrace.get('color'), int(configTrace.get('index')))

                # print 'setting traces'
                # trace_index = 0
                #
                # print "panel.conf.traces.len: " + str(len(panel.conf.traces))
                # print "panel.conf.lines.len: " + str(len(panel.conf.lines))
                # for trace in panel.conf.traces:
                #     #print trace.get('color')
                #     #print trace.get('index')
                #     #panel.conf.set_trace_color(trace.get('color'), int(trace.get('index')))
                #     configTrace = configTraces[trace_index]
                #     panel.conf.set_trace_color(configTrace.get('color'), int(configTrace.get('index')))
                #     trace_index = trace_index + 1