import wx
import os
from imasviz.gui_commands.AbstractCommand import AbstractCommand
from imasviz.util.GlobalOperations import GlobalOperations

class SavePlotsConfiguration(AbstractCommand):
    def __init__(self, view, nodeData=None):
        AbstractCommand.__init__(self, view, nodeData)

    def execute(self):
        default_file_name = ""
        configName = None
        cancel = None
        loop = True
        while loop:
            x = GlobalOperations.askWithCancel(message='Name of the configuration ?', default_value=default_file_name)
            cancel = x[0]
            configName = x[1]
            if cancel != wx.CANCEL and (x == None or x == ""):
                x = GlobalOperations.showMessage(message='Please give a name to the configuration')
            else:
                loop = False

        if (cancel == wx.CANCEL):
            return

        configName = GlobalOperations.replaceSpacesByUnderScores(configName)

        fileName = GlobalOperations.getPlotsConfigurationFileName(configName)

        self.f = open(fileName, 'w')
        self.printCode('#This class has been generated automatically by the IMAS_VIZ application', -1)
        self.printCode('from imasviz.Browser_API import Browser_API', -1)
        self.printCode('from imasviz.data_source.DataSourceFactory import DataSourceFactory', -1)
        self.printCode('import wx', -1)
        self.printCode('from imasviz.util.GlobalValues import GlobalValues', -1)
        self.printCode('from imasviz.util.GlobalOperations import GlobalOperations', -1)
        self.printCode('\n', -1)

        className = configName

        self.printCode("class " + className + "():", -1)
        self.printCode(
            "def __init__(self, dataTreeFrame, paths):",0)
        #self.printCode("self.view = view", 1)
        self.printCode("self.dataTreeFrame = dataTreeFrame", 1)
        self.printCode("self.paths = paths", 1)
        self.printCode('', -1)

        self.printCode('def execute(self):', 0)
        self.printCode('api = Browser_API()', 1)
        self.printCode('dataSource = self.dataTreeFrame.wxTreeView.dataSource', 1)
        self.printCode('api.SelectSignals(self.dataTreeFrame, self.paths)', 1)
        self.printCode('api.PlotSelectedSignalsInMultiFrame(self.dataTreeFrame)', 1)

        self.addPanelsConfiguration()

        self.f.close()

    def addPanelsConfiguration(self):
        #framesKey = len(self.view.imas_viz_api.multiPlotsFrames) - 1
        multiplotFrames = self.view.imas_viz_api.multiPlotsFrames
        i = 0
        for frame in multiplotFrames:
            self.printCode('frame = self.dataTreeFrame.wxTreeView.imas_viz_api.multiPlotsFrames[' + str(i) + ']', 1)
            for key in frame.panels:
                panel = frame.panels[key]
                #self.printCode('framesKey = ' + str(framesKey), 1)

                self.printCode('panel = frame.panels[' + str(key) + ']', 1)
                self.printCode('panel.set_title(' + "'" + str(panel.conf.title) + "'" + ')', 1)
                self.printCode('panel.set_ylabel(' + "'" + str(panel.conf.ylabel) + "'" + ')', 1)
                self.printCode('panel.set_y2label(' + "'" + str(panel.conf.y2label) + "'" + ')', 1)

                #j = 0
                #for trace in panel.conf.traces:
                trace = panel.conf.traces[0]
                color = trace.color
                self.printCode('panel.conf.set_trace_color(' + "'" + str(color) + "'" + "," + str(0) + ')',1)
                #self.printCode('panel.conf.traces[' + str(j) + '].set_color(' +  "'" + str(color) +  "'" + ")" , 1)
                #j = j + 1

            i = i + 1


    def printCode(self, text, level):
        return GlobalOperations.printCode(self.f, text, level)
