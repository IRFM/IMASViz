#  Name   : QVizPlotSelectedSignals
#
#          Container to handle plotting of selected signals/nodes.
#          Note: The wxPython predecessor of this Python file is
#          PlotSelectedSignals.py
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#  TODO:
#
#    - Function definitions (from PlotSignal class)
#    def onHide
#    def getSignal
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#****************************************************

from imasviz.gui_commands.AbstractCommand import AbstractCommand
from imasviz.pyqt5.src.VizGUI.VizPlot.QVizPlotSignal import QVizPlotSignal
from imasviz.pyqt5.src.VizGUI.VizPlot.VizPlotFrames.QVizPlotWidget import QVizPlotWidget
from imasviz.util.GlobalOperations import GlobalOperations
import xml.etree.ElementTree as ET
import traceback
import sys

class QVizPlotSelectedSignals(AbstractCommand):
    def __init__(self, dataTreeView, figureKey=None, update=0,
            configFile=None, all_DTV=True):
        AbstractCommand.__init__(self, dataTreeView, None)
        self.figureKey = figureKey
        self.update = update
        self.plotConfig = None
        self.configFile = configFile
        self.all_DTV = all_DTV
        if self.configFile != None:
            self.plotConfig = ET.parse(self.configFile)
        # DTV
        self.dataTreeView = dataTreeView
        # Browser_API
        self.api = self.dataTreeView.imas_viz_api

    def execute(self):

        if self.raiseErrorIfNoSelectedArrays():
            if len(self.dataTreeView.selectedSignals) == 0:
                    raise ValueError("No signal selected.")

        plotDimension = self.getDimension()

        if plotDimension == "1D":
            # In case of 1D plots
            self.plot1DSelectedSignals(self.figureKey, self.update,
                                       all_DTV = self.all_DTV)
        elif plotDimension == "2D" or plotDimension == "3D":
            # In case of 2D or 3D plots
            raise ValueError("2D/3D plots are not currently supported.")

    def raiseErrorIfNoSelectedArrays(self):
        return True

    def getDimension(self):
        # Finding the plot dimension
        signalNodeDataValue = \
            next(iter(self.dataTreeView.selectedSignals.values()))
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

    """
    def getFrame(self, figureKey, rows=1, cols=1):
        from imasviz.gui_commands.SignalHandling import SignalHandling
        api = self.dataTreeView.imas_viz_api
        if figureKey in api.GetFiguresKeys():
            frame = api.figureframes[figureKey]
        else:
            nextFigureKey = api.GetNextKeyForFigurePlots()
            signalHandling = SignalHandling(self.dataTreeView)
            frame = IMASVIZPlotFrame(None, size=(600, 500), title=nextFigureKey,
                                     signalHandling=signalHandling)
            frame.panel.toggle_legend(None, True)
            api.figureframes[figureKey] = frame
        return frame
    """

    def getPlotWidget(self, figureKey=0):
        api = self.dataTreeView.imas_viz_api
        if figureKey in api.figureframes:
            plotWidget = api.figureframes[figureKey]
        else:
            figureKey = api.GetNextKeyForFigurePlots()
            plotWidget = QVizPlotWidget(size=(600,500), title=figureKey)
            api.figureframes[figureKey] = plotWidget
        return plotWidget

    def plot1DSelectedSignals(self, figureKey=0, update=0, all_DTV=True):
        """Plot the set of 1D signals selected by the user as a function of time.

        Arguments
            figurekey (str) : Figure key/label.
            update    (int) :
        """
        # try:
        # Total number of existing DTVs
        self.num_view = len(self.api.DTVlist)

        plotWidget = self.getPlotWidget(figureKey)

        #def lambda_f(evt, i=figureKey, api=self.api):
        #    self.onHide(self.api, i)

        #if figureKey != None:
        #    plotWidget.Bind(wx.EVT_CLOSE, lambda_f)

        i = 0
        # Create a list of DTVs to specify either single DTV or a list of
        # DTVs fro, which the signals should be plotted to a single plot
        plot_DTVlist = []
        if all_DTV == False:
            plot_DTVlist = [self.dataTreeView]
        else:
            plot_DTVlist = self.api.DTVlist
        """Go through the list of opened DTVs, get its selected plot signals
        and plot every single on to the same plot panel
        """
        for dtv in plot_DTVlist:
            # Get list of selected signals in DTV
            dtv_selectedSignals = GlobalOperations.getSortedSelectedSignals( \
                dtv.selectedSignals)
            # Go through array of selected signals
            for element in dtv_selectedSignals:
                # Get node data
                signalNodeData = element[1] # element[0] = shot number,
                                            # element[1] = node data (itemVIZData)
                                            # element[2] = index,
                                            # element[3] = shot number,
                                            # element[3] = IDS database name,
                                            # element[4] = user name
                                            # element[5] = QTreeWidget item
                                            #              corresponding to the
                                            #              signal

                key = dtv.dataSource.dataKey(signalNodeData)
                tup = (dtv.dataSource.shotNumber, signalNodeData)
                self.api.addNodeToFigure(figureKey, key, tup)

                # Get signal properties and values
                s = QVizPlotSignal.getSignal(dtv, signalNodeData)
                # Get array of time values
                t = QVizPlotSignal.getTime(s)
                # Get array of y-axis values
                v = QVizPlotSignal.get1DSignalValue(s)

                # Get IDS case shot number
                shotNumber = element[0]

                # Get number of rows of the y-axis array of values
                nbRows = v.shape[0]

                # Set plot labels and title
                label, xlabel, ylabel, title = \
                    QVizPlotSignal.plotOptions(dtv, signalNodeData, shotNumber)

                if i == 0 and update == 0:
                    # If the selected node array (selected signal) is the
                    # first in line for the plot (and with update
                    # disabled), create new plot
                    for j in range(0, nbRows):
                        # y-axis values
                        u = v[j]
                        # x-axis values
                        ti = t[0]
                        # Create plot
                        plotWidget.plot(x=ti, y=u, title='', xlabel=xlabel,
                                   ylabel=ylabel, label=label)
                    # Show the plotWidget, holding the plot
                    plotWidget.show()
                else:
                    # Else add the remaining selected node arrays
                    # (selected signals) to the existing plot
                    for j in range(0, nbRows):
                        # y-axis values
                        u = v[j]
                        # x-axis values
                        ti = t[0]
                        # Add to plot
                        plotWidget.plot(x=ti, y=u, label=label)
                i += 1

        # except:
        #     traceback.print_exc(file=sys.stdout)
        #     raise ValueError("Error while plotting 1D selected signal(s).")


    def onHide(self, api, figureKey):
        if figureKey in api.GetFiguresKeys():
            api.figureframes[figureKey].Hide()

