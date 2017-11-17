
from imasviz.gui_commands.plot_commands.PlotSignal import PlotSignal
from imasviz.gui_commands.plot_commands.PlotSelectedSignals import PlotSelectedSignals
from imasviz.plotframes.IMASVIZMultiPlotFrame import IMASVIZMultiPlotFrame
from imasviz.gui_commands.select_commands.SelectSignals import SelectSignals
from imasviz.gui_commands.select_commands.UnselectAllSignals import UnselectAllSignals
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.util.GlobalValues import FigureTypes
import matplotlib.pyplot as plt
import wxmplot
import wx
import traceback
import sys


class PlotSelectedSignalsWithWxmplot(PlotSelectedSignals):
    def __init__(self, view, figurekey=0, update=0, configFileName = None):
        PlotSelectedSignals.__init__(self, view, figureKey=figurekey, update=update, configFileName=configFileName)
        self.labels = {}
        self.rows = 2
        self.cols = 3

    def raiseErrorIfNoSelectedArrays(self):
        return False

    def getDimension(self):
        plotDimension = "1D"
        return plotDimension

    def getFrame(self, figureKey, rows=1, cols=1):
        api = self.view.imas_viz_api
        if figureKey == None:
            figureKey = api.GetNextKeyForMultiplePlots()
        frame = IMASVIZMultiPlotFrame(view=self.view,rows=rows, cols=cols, panelsize=(400, 300))
        frame .SetTitle(title=figureKey)
        frame.panel.toggle_legend(None, True)
        api.figureframes[figureKey] = frame
        return frame

    # Plot the set of 1D signals selected by the user as a function of time
    def plot1DSelectedSignals(self, figureKey=None, update=0):

        try:

            api = self.view.imas_viz_api
            frame = self.getFrame(figureKey, self.rows, self.cols)

            if self.plotConfig != None:
                selectedsignalsList, panelPlotsCount = self.selectSignals(frame)
            else:
                selectedsignalsList = GlobalOperations.getSortedSelectedSignals(self.view.selectedSignals)

            self.applyPlotConfigurationBeforePlotting(frame=frame)

            def lambda_f(evt, i=figureKey, api=api):
                self.onHide(api, i)

            frame.Bind(wx.EVT_CLOSE, lambda_f)

            n = 0 #number of plots

            maxNumberOfPlots = self.rows*self.cols;

            print "selectedsignalsList count --> " + str(len(selectedsignalsList))

            for tupleElement in selectedsignalsList:

                #print tupleElement

                if n + 1 > maxNumberOfPlots:
                    break

                signalNodeData = tupleElement[1]

                key = self.view.dataSource.dataKey(signalNodeData)
                tup = (self.view.dataSource.shotNumber, signalNodeData)
                api.addNodeToFigure(figureKey, key, tup)

                s = PlotSignal.getSignal(self.view, signalNodeData)
                t = PlotSignal.getTime(s)

                v = PlotSignal.get1DSignalValue(s)

                shotNumber = tupleElement[0]

                nbRows = v.shape[0]

                label, xlabel, ylabel, title = PlotSignal.plotOptions(self.view, signalNodeData, shotNumber)

                for j in range(0, nbRows):
                    u = v[j]
                    ti = t[0]
                    #print signalNodeData['Path']
                    a = n//self.cols
                    b = n - (n//self.cols)*self.cols
                    p = (a,b)

                    if self.plotConfig is None:
                        numberOfPlots = 1
                    else:
                        numberOfPlots = panelPlotsCount[p]

                    print str(numberOfPlots) + " plot(s) for panel " + str(p)

                    for k in range(0, numberOfPlots):
                        if k == 0:
                            frame.plot(ti, u, panel=p, xlabel=xlabel, ylabel=ylabel, label=label, labelfontsize=5,
                                       show_legend=True, legend_loc='uc', legendfontsize=5, legend_on=False)
                        else:
                            frame.oplot(ti, u, panel=p, xlabel=xlabel, ylabel=ylabel, label=label, labelfontsize=5,
                                       show_legend=True, legend_loc='uc', legendfontsize=5, legend_on=False)
                    n = n + 1

            self.applyPlotConfigurationAfterPlotting(frame=frame)
            frame.Center()
            frame.Show()

        except:
            traceback.print_exc(file=sys.stdout)
            raise ValueError("Error while plotting 1D selected signal(s).")


    def selectSignals(self, frame):
        selectedsignalsMap = {} #key = panel key, value = selected arrays count
        pathsList = []
        UnselectAllSignals(self.view).execute()
        for n in range(0, len(frame.panels)):
            key = GlobalOperations.getNextPanelKey(n, cols=self.cols)
            selectedArrays = self.plotConfig.findall(".//*[@key='" + str(key) + "']/selectedArray")
            selectedsignalsMap[key] = len(selectedArrays)
            for selectedArray in selectedArrays:
                pathsList.append(selectedArray.get("path"))
        print "pathsList count --> " + str(len(pathsList))
        print pathsList
        SelectSignals(self.view, pathsList).execute()
        selectedsignalsList = GlobalOperations.getSortedSelectedSignals(self.view.selectedSignals)
        return selectedsignalsList, selectedsignalsMap


    def applyPlotConfigurationBeforePlotting(self, frame):
        if self.plotConfig == None:
            return
        print "Applying plot configuration before plotting..."
        for key in frame.panels:
            panel = frame.panels[key]
            configPanels = self.plotConfig.findall(".//*[@key='" + str(key) + "']")
            configurationPanel = configPanels[0]

            #panel.conf.plot_type = configurationPanel.get("plot_type")

            panel.conf.set_defaults()

            self.setPlotConfigAttribute(panel, configurationPanel, "scatter_size")
            self.setPlotConfigAttribute(panel, configurationPanel, "scatter_normalcolor")
            self.setPlotConfigAttribute(panel, configurationPanel, "scatter_normaledge")
            self.setPlotConfigAttribute(panel, configurationPanel, "scatter_selectcolor")
            self.setPlotConfigAttribute(panel, configurationPanel, "scatter_selectedge")
            self.setPlotConfigAttribute(panel, configurationPanel, "scatter_data")
            self.setPlotConfigAttribute(panel, configurationPanel, "scatter_coll")
            self.setPlotConfigAttribute(panel, configurationPanel, "scatter_mask")
            self.setPlotConfigAttribute(panel, configurationPanel, "show_legend")
            self.setPlotConfigAttribute(panel, configurationPanel, "show_grid")
            self.setPlotConfigAttribute(panel, configurationPanel, "legend_loc")
            self.setPlotConfigAttribute(panel, configurationPanel, "legend_onaxis")
            #self.setPlotConfigAttribute(panel, configurationPanel, "mpl_legend")
            self.setPlotConfigAttribute(panel, configurationPanel, "draggable_legend")
            self.setPlotConfigAttribute(panel, configurationPanel, "hidewith_legend")
            self.setPlotConfigAttribute(panel, configurationPanel, "show_legend_frame")
            self.setPlotConfigAttribute(panel, configurationPanel, "axes_style")

    def applyPlotConfigurationAfterPlotting(self, frame):
        if self.plotConfig == None:
            return
        print "Applying plot configuration after plotting..."
        for key in frame.panels:
            #print 'key: ' + str(key)
            panel = frame.panels[key]
            configPanels = self.plotConfig.findall(".//*[@key='" + str(key)+ "']")
            configurationPanel = configPanels[0]
            panel.set_title(configurationPanel.get('title'))
            panel.set_xlabel(configurationPanel.get('xlabel'))
            panel.set_ylabel(configurationPanel.get('ylabel'))
            panel.set_y2label(configurationPanel.get('y2label'))

            if configurationPanel.get('color_theme') != None:
                panel.conf.set_color_theme(configurationPanel.get('color_theme'))

            panel.conf.set_gridcolor(configurationPanel.get('gridcolor'))
            panel.conf.set_bgcolor(configurationPanel.get('bgcolor'))
            panel.conf.set_framecolor(configurationPanel.get('framecolor'))
            panel.conf.set_textcolor(configurationPanel.get('textcolor'))

            try:
                panel.conf.set_logscale(configurationPanel.get("xscale"), configurationPanel.get("yscale"))
                panel.conf.draw_legend()
                if panel.conf.show_grid != None:
                    if panel.conf.show_grid == "True":
                        panel.conf.show_grid = "on"
                    elif panel.conf.show_grid == "False":
                        panel.conf.show_grid = "off"
                    panel.conf.enable_grid(panel.conf.show_grid)
            except ValueError as e:
                print e

            configTraces = self.plotConfig.findall(".//*[@key='" + str(key) + "']/trace")
            refresh_done = []

            linesCount = len(panel.conf.lines)
            linesCount = 1
            for i in range(0,linesCount):
                refresh_done.append(False)

            for i in range(0, linesCount):
                configTrace = configTraces[i]
                try:
                    #print "handling trace: " + str(i)
                    panel.conf.set_trace_color(configTrace.get('color'), int(configTrace.get('index')))

                    panel.conf.set_trace_zorder(configTrace.get('zorder'), int(configTrace.get('index')))
                    panel.conf.set_trace_label(configTrace.get('label'), int(configTrace.get('index')))
                    panel.conf.set_trace_style(configTrace.get('style'), int(configTrace.get('index')))
                    panel.conf.set_trace_drawstyle(configTrace.get('drawstyle'), int(configTrace.get('index')))
                    panel.conf.set_trace_marker(configTrace.get('marker'), int(configTrace.get('index')))
                    panel.conf.set_trace_markersize(float(configTrace.get('markersize')), int(configTrace.get('index')))
                    panel.conf.set_trace_linewidth(configTrace.get('linewidth'), int(configTrace.get('index')))

                    #print "handling data range for trace: " + str(i)
                    configDataRanges = self.plotConfig.findall(".//*[@key='" + str(key) + "']/trace/data_range")
                    configDataRange = configDataRanges[0]
                    dataRange = []
                    dataRange.append(float(configDataRange.get("dr1")))
                    dataRange.append(float(configDataRange.get("dr2")))
                    dataRange.append(float(configDataRange.get("dr3")))
                    dataRange.append(float(configDataRange.get("dr4")))
                    panel.conf.set_trace_datarange(dataRange, int(configTrace.get('index')))

                    if not refresh_done[i]:
                        panel.conf.refresh_trace(int(configTrace.get('index')))
                        refresh_done[i] = True

                except ValueError as e:
                    print e


    def setPlotConfigAttribute(self, panel, configurationPanel, attributeName):
        v = configurationPanel.get(attributeName)
        if v != None:
            if v == "True" or v == "False":
                c = (v == "True")
                exec ("panel.conf." + attributeName + " = c")
            else:
                exec("panel.conf." + attributeName + " = v")

    def onHide(self, api, figureKey):
        if figureKey in api.GetFiguresKeys(figureType=FigureTypes.MULTIPLOTTYPE):
            api.figureframes[figureKey].Hide()
