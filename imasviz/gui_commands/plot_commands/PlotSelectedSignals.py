from imasviz.gui_commands.AbstractCommand import AbstractCommand
from imasviz.gui_commands.plot_commands.PlotSignal import PlotSignal
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.plotframes.IMASVIZPlotFrame import IMASVIZPlotFrame
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET
import wxmplot
import wx
import traceback
import sys


class PlotSelectedSignals(AbstractCommand):
    def __init__(self, view, figureKey=None, update=0, configFileName=None):
        AbstractCommand.__init__(self, view, None)
        self.figureKey = figureKey
        self.update = update
        self.plotConfig = None
        if configFileName != None:
            self.plotConfig = ET.parse(configFileName)
        """WxDataTreeView"""
        self.view = view
        """Total number of existing WxDataTreeViews"""
        self.num_view = len(self.view.imas_viz_api.dataTreeFrameList)

    def execute(self):

        if self.raiseErrorIfNoSelectedArrays():
            if len(self.view.selectedSignals) == 0:
                    raise ValueError("No signal selected.")

        plotDimension = self.getDimension()

        if plotDimension == "1D":
            """In case of 1D plots"""
            self.plot1DSelectedSignals(self.figureKey, self.update)
        elif plotDimension == "2D" or plotDimension == "3D":
            """In case of 2D or 3D plots"""
            raise ValueError("2D/3D plots are not currently supported.")

    def raiseErrorIfNoSelectedArrays(self):
        return True

    def getDimension(self):

        # Finding the plot dimension
        signalNodeDataValue = next(iter(self.view.selectedSignals.values()))
        signalNodeData = signalNodeDataValue[1]
        data_type = signalNodeData['data_type']

        plotDimension = None
        if data_type == 'FLT_1D' or data_type == 'INT_1D':
            plotDimension = "1D"
        elif data_type == 'FLT_2D' or data_type == 'INT_2D':
            plotDimension = "2D"
        elif data_type == 'FLT_3D' or data_type == 'INT_3D':
            plotDimension = "3D"
        else:
            raise ValueError("Plots dimension larger than 3D are not supported.")
        return plotDimension

    def getFrame(self, figureKey, rows=1, cols=1):
        from imasviz.gui_commands.SignalHandling import SignalHandling
        api = self.view.imas_viz_api
        if figureKey in api.GetFiguresKeys():
            frame = api.figureframes[figureKey]
        else:
            nextFigureKey = api.GetNextKeyForFigurePlots()
            signalHandling = SignalHandling(self.view)
            frame = IMASVIZPlotFrame(None, size=(600, 500), title=nextFigureKey,
                                     signalHandling=signalHandling)
            frame.panel.toggle_legend(None, True)
            api.figureframes[figureKey] = frame
        return frame

    def plot1DSelectedSignals(self, figureKey=0, update=0, multiple_DTV=False):
        """Plot the set of 1D signals selected by the user as a function of time

           Args:
                figurekey    - List of existing figures.
                update       -
        """
        try:

            if self.num_view == 1:
                """If there is only one WxDataTreeView opened"""
                selectedsignals = GlobalOperations.getSortedSelectedSignals( \
                    self.view.selectedSignals)
            else:
                """Else if there are more WxDataTreeViews (more instances of the
                IDS databases opened at once
                """
                """TODO: (to fix)
                   Path to the signal (node containing the 1D plot
                   array data) is obtained correctly, but the IDS databases
                   are then not set correctly.
                   For example, if we select arrays 1, 2 in DTV1, arrays
                   3, 4 in DTV2 and proceed to run 'Plot all signals' in
                   DTV1, all 1D_FLT arrays (paths) 1, 2, 3, and 4 will be taken
                   from DTV1 and none from DTV2 (vice versa if we run the
                   command from the DTV2).
                """
                selectedsignals = GlobalOperations.getSortedSelectedSignals(
                    self.view.imas_viz_api.GetSelectedSignals_AllDTVs() )

            api = self.view.imas_viz_api

            frame = self.getFrame(figureKey)
            #fig = frame.figure
            #fig.add_subplot(111)

            def lambda_f(evt, i=figureKey, api=api):
                self.onHide(api, i)

            if figureKey != None:
                frame.Bind(wx.EVT_CLOSE, lambda_f)

            i = 0

            for value in selectedsignals:
                signalNodeData = value[1]

                key = self.view.dataSource.dataKey(signalNodeData)
                tup = (self.view.dataSource.shotNumber, signalNodeData)
                api.addNodeToFigure(figureKey, key, tup)

                s = PlotSignal.getSignal(self.view, signalNodeData)
                t = PlotSignal.getTime(s)

                v = PlotSignal.get1DSignalValue(s)

                shotNumber = value[0]

                nbRows = v.shape[0]

                label, xlabel, ylabel, title = \
                 PlotSignal.plotOptions(self.view, signalNodeData, shotNumber)

                if i == 0 and update == 0:
                    for j in range(0, nbRows):
                        u = v[j]
                        ti = t[0]
                        frame.plot(ti, u, title='', xlabel=xlabel,
                                   ylabel=ylabel, label=label)
                    frame.Center()
                    frame.Show()
                else:
                    for j in range(0, nbRows):
                        u = v[j]
                        ti = t[0]
                        frame.oplot(ti, u, label=label)
                i += 1
        except:
            traceback.print_exc(file=sys.stdout)
            raise ValueError("Error while plotting 1D selected signal(s).")


    def onHide(self, api, figureKey):
        if figureKey in api.GetFiguresKeys():
            api.figureframes[figureKey].Hide()

