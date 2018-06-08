
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
    """Plotting the selected signals with wxmplot to MultiPlot frame.
    """
    def __init__(self, WxDataTreeView, figurekey=0, update=0,
                 configFile = None, all_DTV = True):
        """
        Parameters
        ----------

        WxDataTreeView : WxDataTreeView object
            WxDataTreeView (DTV) object.
        figurekey : string
            Frame label.
        update :
        configFile : string
            System path to the configuration file.
        all_DTV : bool
            Indicator to read selected signals from single DTV (from the given
            one) or from all DTVs. Note: This has no effect when reading list
            of signals from the configuration file.
        """
        PlotSelectedSignals.__init__(self, WxDataTreeView, figureKey=figurekey,
                                     update=update, configFile=configFile,
                                     all_DTV=True)
        # self.labels = {}
        # Set number of rows and columns of panels in the MultiPlot frame
        self.rows = 2
        self.cols = 3
        # Get the indicator from which DTVs should the signals be read
        # (single or all)
        self.all_DTV = all_DTV

        self.configFile = configFile

        # Browser_API
        self.api = self.WxDataTreeView.imas_viz_api
        # DTV
        self.WxDataTreeView = WxDataTreeView

    def raiseErrorIfNoSelectedArrays(self):
        return False

    def getDimension(self):
        plotDimension = "1D"
        return plotDimension

    def getFrame(self, figureKey, rows=1, cols=1):
        if figureKey == None:
            figureKey = self.api.GetNextKeyForMultiplePlots()
        frame = IMASVIZMultiPlotFrame(WxDataTreeView = self.WxDataTreeView,
                                      rows = rows,
                                      cols = cols,
                                      panelsize = (400, 300))
        frame.SetTitle(title=figureKey)
        frame.panel.toggle_legend(None, True)
        self.api.figureframes[figureKey] = frame
        return frame

    def plot1DSelectedSignals(self, figureKey=None, update=0, all_DTV=True):
        """Plot the set of 1D signals, selected by the user, as a function of
           time to MultiPlot.
        """

        try:
            # Set rows and columns
            self.setRowsColumns()
            # Get frame
            frame = self.getFrame(figureKey, self.rows, self.cols)

            self.applyPlotConfigurationBeforePlotting(frame=frame)

            def lambda_f(evt, i=figureKey, api=self.api):
                self.onHide(self.api, i)

            frame.Bind(wx.EVT_CLOSE, lambda_f)

            n = 0 # Plot number

            # Set maximum number of plots within frame
            maxNumberOfPlots = self.rows*self.cols;

            dtv_selectedSignals = []

            MultiPlotFrame_WxDTVList = []

            plotConfig_used = False

            # If plotConfig is available (e.g. save configuration was loaded)
            if self.plotConfig != None:
                plotConfig_used = True

                # Select signals, saved in the save configuration. Return the
                # list of signals as 'dtv_selectedSignals'.
                # Get panel plots count
                dtv_selectedSignals, panelPlotsCount = \
                    self.selectSignals(frame, WxDataTreeView=self.WxDataTreeView)
                # Add a single DTV to the list
                MultiPlotFrame_WxDTVList.append(self.WxDataTreeView)

            else:
                # Else if plotConfig is not present (save configuration was
                # not used)
                if self.all_DTV != False:
                    # Get the list of current opened DTVs, created by manually
                    # opening IDS databases thus creating the DTVs.
                    MultiPlotFrame_WxDTVList = self.api.wxDTVlist
                else:
                    # Add a single DTV to the list
                    MultiPlotFrame_WxDTVList.append(self.WxDataTreeView)

            # Go through every opened/created DTV from the list, get its
            # selected plot signals and plot every single to the same
            # MultiPlot frame
            for dtv in MultiPlotFrame_WxDTVList:
                """Get list of selected signals in DTV"""
                dtv_selectedSignals = GlobalOperations. \
                    getSortedSelectedSignals(dtv.selectedSignals)

                for element in dtv_selectedSignals:

                    if n + 1 > maxNumberOfPlots:
                        break

                    #Get node data
                    signalNodeData = element[1] # element[0] = shot number,
                                                # element[1] = node data
                                                # element[2] = index,
                                                # element[3] = shot number,
                                                # element[3] = IDS database name,
                                                # element[4] = user name

                    key = dtv.dataSource.dataKey(signalNodeData)
                    tup = (dtv.dataSource.shotNumber, signalNodeData)
                    self.api.addNodeToFigure(figureKey, key, tup)

                    # Get signal properties and values
                    s = PlotSignal.getSignal(dtv, signalNodeData)
                    # Get array of time values
                    t = PlotSignal.getTime(s)
                    # Get array of y-axis values
                    v = PlotSignal.get1DSignalValue(s)

                    # Get IDS case shot number
                    shotNumber = element[0]

                    # Get number of rows of the y-axis array of values
                    nbRows = v.shape[0]

                    # Set plot labels and title
                    label, xlabel, ylabel, title = \
                        PlotSignal.plotOptions(dtv, signalNodeData, shotNumber)

                    for j in range(0, nbRows):
                        # y-axis values
                        u = v[j]
                        # x-axis values
                        ti = t[0]

                        a = n//self.cols
                        b = n - (n//self.cols)*self.cols
                        p = (a,b)

                        if self.plotConfig is None:
                            numberOfPlots = 1
                        else:
                            # numberOfPlots = panelPlotsCount[p]
                            numberOfPlots = 1

                        for k in range(0, numberOfPlots):
                            if k == 0:
                                # Create plot
                                frame.plot(ti, u, panel=p, xlabel=xlabel,
                                           ylabel=ylabel, label=label,
                                           labelfontsize=5, show_legend=True,
                                           legend_loc='uc', legendfontsize=5,
                                           legend_on=False)
                            else:
                                # Add to pre-existing plot
                                frame.oplot(ti, u, panel=p, xlabel=xlabel,
                                            ylabel=ylabel, label=label,
                                            labelfontsize=5, show_legend=True,
                                            legend_loc='uc', legendfontsize=5,
                                            legend_on=False)
                        n = n + 1

                    # if plotConfig_used == True:
                    #     UnselectAllSignals(dtv).execute()

            self.applyPlotConfigurationAfterPlotting(frame=frame)
            frame.Center()
            # Show the frame, holding the plots
            frame.Show()

        except:
            traceback.print_exc(file=sys.stdout)
            raise ValueError("Error while plotting 1D selected signal(s).")

    def selectSignals(self, frame, WxDataTreeView):
        selectedsignalsMap = {} #key = panel key, value = selected arrays count
        pathsList = []
        UnselectAllSignals(WxDataTreeView).execute()

        for n in range(0, len(frame.panels)):
            key = GlobalOperations.getNextPanelKey(n, cols=self.cols)

            selectedArrays = \
                self.plotConfig.findall(".//*[@key='" + str(key) +
                                        "']/selectedArray")
            selectedsignalsMap[key] = len(selectedArrays)
            for selectedArray in selectedArrays:
                # Get signal paths
                pathsList.append(selectedArray.get("path"))

        SelectSignals(WxDataTreeView, pathsList).execute()

        dtv_selectedSignals = GlobalOperations. \
            getSortedSelectedSignals(WxDataTreeView.selectedSignals)
        return dtv_selectedSignals, selectedsignalsMap

    def getNumSignals(self):
        """Get number of signals intended for the MultiPlot feature
           from either opened DTVs or from configuration file if it is loaded.
           TODO: Find more lightweight way to get the number of signals.
        """
        if self.configFile != None and self.plotConfig != False:
            # Get number of signals through number of signal paths
            pathsList = GlobalOperations.\
                getSignalsPathsFromConfigurationFile(self.configFile)
            num_signals = len(pathsList)
        else:
            # If plotConfig is not present (save configuration was
            # not used)
            MultiPlotFrame_WxDTVList = []
            if self.all_DTV != False:
                # Get the list of current opened DTVs, created by manually
                # opening IDS databases thus creating the DTVs.
                MultiPlotFrame_WxDTVList = self.api.wxDTVlist
            else:
                # Add a single DTV to the list
                MultiPlotFrame_WxDTVList.append(self.WxDataTreeView)

            # Get the number of signals through the currently opened DTVs
            num_signals = 0
            for dtv in MultiPlotFrame_WxDTVList:
                # Get list of selected signals in DTV
                dtv_selectedSignals = GlobalOperations. \
                    getSortedSelectedSignals(dtv.selectedSignals)
                num_signals += len(dtv_selectedSignals)

        return num_signals

    def setRowsColumns(self):
            # Get total number of signals
            num_signals = \
                self.getNumSignals()
            # Modify the MultiPlot rows and columns depending on total number
            # of signals
            if num_signals > 6:
                if num_signals <= 8:
                    self.rows = 2
                    self.cols = 4
                elif num_signals > 8 and num_signals <= 12:
                    self.rows = 3
                    self.cols = 4
                elif num_signals > 12:
                    self.rows = 3
                    self.cols = 4
                    print('MultiPlot plot limit reached (12)!')

    def applyPlotConfigurationBeforePlotting(self, frame):
        if self.plotConfig == None:
            return
        print ("Applying plot configuration before plotting...")
        for key in frame.panels:
            panel = frame.panels[key]
            configPanels = self.plotConfig.findall(".//*[@key='" + str(key) + "']")
            if len(configPanels) == 0:
                break
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
        print ("Applying plot configuration after plotting...")
        for key in frame.panels:
            #print 'key: ' + str(key)
            panel = frame.panels[key]
            configPanels = self.plotConfig.findall(".//*[@key='" + str(key)+ "']")
            if len(configPanels) == 0:
                break
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
                print (e)

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

                    #panel.conf.set_trace_zorder(configTrace.get('zorder'), int(configTrace.get('index')))
                    #panel.conf.set_trace_label(configTrace.get('label'), int(configTrace.get('index')))
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
                    print (e)


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

class modifyMultiPlot():
    """Routines handling the existing MultiPlots (adding selected signals,
       reshaping etc).
    """

    def __init__(self, multiPlotFrame, WxDataTreeView):
        self.multiPlotFrame = multiPlotFrame
        # DTV
        self.WxDataTreeView = WxDataTreeView
        # Browser_API
        self.api = self.WxDataTreeView.imas_viz_api

    def addSignalSelection(self):
        """Add a selection from other DTV to existing MultiPlot frame.

        Parameters
        ----------

        multiPlotFrame : wx.Frame object
            MultiPlot frame to update
        figurekey : string
            Label of the MultiPlot frame that is to be updated (new signal
            selection added).
        WxDataTreeView : WxDataTreeView object
            WxDataTreeView (DTV) object.
        """
        self.rows = self.multiPlotFrame.rows
        self.cols = self.multiPlotFrame.cols

        self.filledPlotPanelList = []
        self.emptyPlotPanelList = []

        # Extract the data-filled PlotPanels
        # Note: the empty PlotPanels do not contain the 'legend_map' attribute
        #       (it holds the string describing the source of data - IDS path to
        #       the array)
        for p in self.multiPlotFrame.panels:
            panel = self.multiPlotFrame.panels[p]
            if hasattr(panel.conf, 'legend_map'):
                self.filledPlotPanelList.append(panel)
            else:
                self.emptyPlotPanelList.append(panel)

        # Get list of selected signals in DTV
        dtv_selectedSignals = GlobalOperations. \
            getSortedSelectedSignals(self.WxDataTreeView.selectedSignals)

        # Set maximum number of plots within frame
        maxNumberOfPlots = self.rows*self.cols;

        # First empty plot number
        n = len(self.filledPlotPanelList)

        for element in dtv_selectedSignals:

            if n + 1 > maxNumberOfPlots:
                break

            #Get node data
            signalNodeData = element[1] # element[0] = shot number,
                                        # element[1] = node data
                                        # element[2] = index,
                                        # element[3] = shot number,
                                        # element[3] = IDS database name,
                                        # element[4] = user name

            key = self.WxDataTreeView.dataSource.dataKey(signalNodeData)
            tup = (self.WxDataTreeView.dataSource.shotNumber, signalNodeData)

            # if figureKey == None:
            figureKey = self.api.GetNextKeyForMultiplePlots()

            self.api.addNodeToFigure(figureKey, key, tup)

            # Get signal properties and values
            s = PlotSignal.getSignal(self.WxDataTreeView, signalNodeData)
            # Get array of time values
            t = PlotSignal.getTime(s)
            # Get array of y-axis values
            v = PlotSignal.get1DSignalValue(s)

            # Get IDS case shot number
            shotNumber = element[0]

            # Get number of rows of the y-axis array of values
            nbRows = v.shape[0]

            # Set plot labels and title
            label, xlabel, ylabel, title = \
                PlotSignal.plotOptions(self.WxDataTreeView, signalNodeData, shotNumber)

            for j in range(0, nbRows):
                # y-axis values
                u = v[j]
                # x-axis values
                ti = t[0]

                a = n//self.cols
                b = n - (n//self.cols)*self.cols
                p = (a,b)

                numberOfPlots = 1

                for k in range(0, numberOfPlots):
                    if k == 0:
                        # Create plot
                        self.multiPlotFrame.plot(ti, u, panel=p, xlabel=xlabel,
                                   ylabel=ylabel, label=label,
                                   labelfontsize=5, show_legend=True,
                                   legend_loc='uc', legendfontsize=5,
                                   legend_on=False, update=True)
                    else:
                        # Add to pre-existing plot
                        self.multiPlotFrame.oplot(ti, u, panel=p, xlabel=xlabel,
                                    ylabel=ylabel, label=label,
                                    labelfontsize=5, show_legend=True,
                                    legend_loc='uc', legendfontsize=5,
                                    legend_on=False, update=True)
                n = n + 1

        self.multiPlotFrame.Refresh()
        # Show the frame, holding the plots
        self.multiPlotFrame.Show()
        self.multiPlotFrame.Raise()
