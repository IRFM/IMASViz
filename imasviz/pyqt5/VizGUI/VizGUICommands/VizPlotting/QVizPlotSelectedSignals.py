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

import xml.etree.ElementTree as ET

from imasviz.gui_commands.AbstractCommand import AbstractCommand
from imasviz.pyqt5.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal import QVizPlotSignal
from imasviz.pyqt5.VizGUI.VizPlot.VizPlotFrames.QVizPlotWidget import QVizPlotWidget


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
            if len(self.dataTreeView.selectedSignalsDict) == 0:
                    raise ValueError("No signal selected.")

        self.plot1DSelectedSignals(self.figureKey, self.update,
                                   all_DTV = self.all_DTV)

        # # Check the plot dimension
        # for key in self.dataTreeView.selectedSignalsDict:
        #     signalDict = self.dataTreeView.selectedSignalsDict[key]
        #     plotDimension = self.getDimension(signalDict)

        #     if plotDimension == "1D":
        #         # In case of 1D plots
        #         self.plot1DSelectedSignals(self.figureKey, self.update,
        #                                    all_DTV = self.all_DTV)
        #     elif plotDimension == "2D" or plotDimension == "3D":
        #         # In case of 2D or 3D plots
        #         raise ValueError("2D/3D plots are not currently supported.")

    def raiseErrorIfNoSelectedArrays(self):
        return True

    def getDimension(self, signalDict):
        # Finding the plot dimension
        signalNodeData = signalDict['nodeData']
        data_type = signalNodeData['data_type']

        plotDimension = None
        if data_type == 'FLT_1D' or data_type == 'INT_1D':
            plotDimension = "1D"
        elif data_type == 'FLT_2D' or data_type == 'INT_2D':
            raise ValueError("2D plots are not currently supported.")
            plotDimension = "2D"
        elif data_type == 'FLT_3D' or data_type == 'INT_3D':
            raise ValueError("3D plots are not currently supported.")
            plotDimension = "3D"
        else:
            raise ValueError("Plots dimension larger than 3D are not supported.")
        return plotDimension

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

        # TODO
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
        # Go through the list of opened DTVs, get its selected plot signals dict
        # and plot the signals to the same plot widget
        for dtv in plot_DTVlist:
            # Go through DTV selected signal dictionaries
            # (each is specified by key)
            for key in dtv.selectedSignalsDict:

                # Signal dictionary variable
                signalDict = dtv.selectedSignalsDict[key]

                # Check dimension
                plotDimension = self.getDimension(signalDict)

                # Get signal node data
                signalNodeData = signalDict['nodeData']

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
                shotNumber = signalDict['shotNumber']

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
        # Show the plotWidget, holding the plot
        plotWidget.show()

        # except:
        #     traceback.print_exc(file=sys.stdout)
        #     raise ValueError("Error while plotting 1D selected signal(s).")


    def onHide(self, api, figureKey):
        if figureKey in api.GetFiguresKeys():
            api.figureframes[figureKey].Hide()

