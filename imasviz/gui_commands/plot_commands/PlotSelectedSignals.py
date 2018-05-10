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
    def __init__(self, WxDataTreeView, figureKey=None, update=0,
        configFileName=None, all_DTV = True):
        AbstractCommand.__init__(self, WxDataTreeView, None)
        self.figureKey = figureKey
        self.update = update
        self.plotConfig = None
        if configFileName != None:
            self.plotConfig = ET.parse(configFileName)
        """WxDataTreeView"""
        self.WxDataTreeView = WxDataTreeView
        """Browser_API"""
        self.api = self.WxDataTreeView.imas_viz_api
        self.all_DTV = all_DTV

    def execute(self):

        if self.raiseErrorIfNoSelectedArrays():
            if len(self.WxDataTreeView.selectedSignals) == 0:
                    raise ValueError("No signal selected.")

        plotDimension = self.getDimension()

        if plotDimension == "1D":
            """In case of 1D plots"""
            self.plot1DSelectedSignals(self.figureKey, self.update,
                                       all_DTV=True)
        elif plotDimension == "2D" or plotDimension == "3D":
            """In case of 2D or 3D plots"""
            raise ValueError("2D/3D plots are not currently supported.")

    def raiseErrorIfNoSelectedArrays(self):
        return True

    def getDimension(self):

        # Finding the plot dimension
        signalNodeDataValue = \
            next(iter(self.WxDataTreeView.selectedSignals.values()))
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
        api = self.WxDataTreeView.imas_viz_api
        if figureKey in api.GetFiguresKeys():
            frame = api.figureframes[figureKey]
        else:
            nextFigureKey = api.GetNextKeyForFigurePlots()
            signalHandling = SignalHandling(self.WxDataTreeView)
            frame = IMASVIZPlotFrame(None, size=(600, 500), title=nextFigureKey,
                                     signalHandling=signalHandling)
            frame.panel.toggle_legend(None, True)
            api.figureframes[figureKey] = frame
        return frame

    def plot1DSelectedSignals(self, figureKey=0, update=0, all_DTV=True):
        """Plot the set of 1D signals selected by the user as a function of time.

        Parameters
        ----------
            figurekey : string
                Figure key/label.
            update :
        """
        try:
            """Total number of existing WxDataTreeViews"""
            self.num_view = len(self.api.wxDTVlist)

            frame = self.getFrame(figureKey)

            def lambda_f(evt, i=figureKey, api=self.api):
                self.onHide(self.api, i)

            if figureKey != None:
                frame.Bind(wx.EVT_CLOSE, lambda_f)

            i = 0
            """Go through each opened DTV, get its selected plot signals and
               plot every single on to the same plot panel
            """
            for dtv in self.api.wxDTVlist:
                """Get list of selected signals in DTV"""
                dtv_selectedSignals = GlobalOperations.getSortedSelectedSignals( \
                    dtv.selectedSignals)

                for element in dtv_selectedSignals:
                    """Get node data"""
                    signalNodeData = element[1] # element[0] = shot number,
                                                # element[1] = node data
                                                # element[2] = index,
                                                # element[3] = shot number,
                                                # element[3] = IDS database name,
                                                # element[4] = user name

                    key = dtv.dataSource.dataKey(signalNodeData)
                    tup = (dtv.dataSource.shotNumber, signalNodeData)
                    self.api.addNodeToFigure(figureKey, key, tup)

                    """Get signal properties and values"""
                    s = PlotSignal.getSignal(dtv, signalNodeData)
                    """Get array of time values"""
                    t = PlotSignal.getTime(s)
                    """Get array of y-axis values"""
                    v = PlotSignal.get1DSignalValue(s)

                    """Get IDS case shot number"""
                    shotNumber = element[0]

                    """Get number of rows of the y-axis array of values"""
                    nbRows = v.shape[0]

                    """Set plot labels and title"""
                    label, xlabel, ylabel, title = \
                        PlotSignal.plotOptions(dtv, signalNodeData, shotNumber)

                    if i == 0 and update == 0:
                        """If the selected node array (selected signal) is the
                           first in line for the plot (and with update
                           disabled), create new plot
                        """
                        for j in range(0, nbRows):
                            """y-axis values"""
                            u = v[j]
                            """x-axis values"""
                            ti = t[0]
                            """Create plot"""
                            frame.plot(ti, u, title='', xlabel=xlabel,
                                       ylabel=ylabel, label=label)
                        frame.Center()
                        """Show the frame, holding the plot"""
                        frame.Show()
                    else:
                        """Else add the remaining selected node arrays
                           (selected signals) to the existing plot
                        """
                        for j in range(0, nbRows):
                            """y-axis values"""
                            u = v[j]
                            """x-axis values"""
                            ti = t[0]
                            """Add to plot"""
                            frame.oplot(ti, u, label=label)
                    i += 1
        except:
            traceback.print_exc(file=sys.stdout)
            raise ValueError("Error while plotting 1D selected signal(s).")


    def onHide(self, api, figureKey):
        if figureKey in api.GetFiguresKeys():
            api.figureframes[figureKey].Hide()

