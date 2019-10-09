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
import logging
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal import QVizPlotSignal
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPlotWidget import QVizPlotWidget
from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand


class QVizPlotSelectedSignals(QVizAbstractCommand):
    def __init__(self, dataTreeView, figureKey=None, update=0,
                 configFile=None, all_DTV=True):
        QVizAbstractCommand.__init__(self, dataTreeView, None)
        self.figureKey = figureKey
        self.update = update
        self.plotConfig = None
        self.configFile = configFile
        self.all_DTV = all_DTV
        if self.configFile is not None:
            self.plotConfig = ET.parse(self.configFile)
        # DTV
        self.dataTreeView = dataTreeView
        # Viz_API
        self.api = self.dataTreeView.imas_viz_api

    def execute(self):
        if self.raiseErrorIfNoSelectedArrays():
            if len(self.dataTreeView.selectedSignalsDict) == 0:
                raise ValueError("No signal selected.")

        self.plot1DSelectedSignals(self.figureKey, self.update,
                                   all_DTV=self.all_DTV)

    def raiseErrorIfNoSelectedArrays(self):
        return True

    def getDimension(self, treeNode):
        plotDimension = None
        if treeNode.is1DAndDynamic() or treeNode.is0DAndDynamic():
            plotDimension = "1D"
        else:
            logging.warning('Plots dimension larger than 1D are currently not supported.')
            logging.warning('Data of unsupported data type passed. Aborting!')
            return False
        return plotDimension

    def getPlotWidget(self, figureKey=0):
        api = self.dataTreeView.imas_viz_api
        if figureKey in api.figureframes:
            plotWidget = api.figureframes[figureKey]
        else:
            figureKey = api.GetNextKeyForFigurePlots()
            plotWidget = QVizPlotWidget(size=(600, 550), title=figureKey)
            api.figureframes[figureKey] = plotWidget
        return plotWidget

    def plot1DSelectedSignals(self, figureKey=0, update=0, all_DTV=True):
        """Plot the set of 1D signals selected by the user as a function of time.

        Arguments
            figurekey (str) : Figure key/label.
            update    (int) :
        """
        try:
            # Total number of existing DTVs
            self.num_view = len(self.api.DTVlist)

            # Get plot widget
            plotWidget = self.getPlotWidget(figureKey)

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

                    v = dtv.selectedSignalsDict[key]
                    vizTreeNode = v['QTreeWidgetItem']

                    # Get node dataDict
                    signalNodeData = vizTreeNode.getInfoDict()

                    # Check dimension
                    plotDimension = self.getDimension(vizTreeNode)

                    # Cancel plotting procedure if there is something wrong with
                    # the dimension
                    if plotDimension == False:
                        return

                    key = dtv.dataSource.dataKey(vizTreeNode.getInfoDict())
                    tup = (dtv.dataSource.shotNumber, signalNodeData)
                    self.api.addNodeToFigure(figureKey, key, tup)

                    # Get signal properties and values
                    s = QVizPlotSignal.getSignal(dtv, vizTreeNode)
                    # Get array of time values
                    t = QVizPlotSignal.getTime(s)
                    # Get array of y-axis values
                    v = QVizPlotSignal.get1DSignalValue(s)

                    # Get number of rows of the y-axis array of values
                    nbRows = v.shape[0]

                    # Set plot labels and title
                    label, xlabel, ylabel, title = \
                        QVizPlotSignal.plotOptions(dtv, vizTreeNode, vizTreeNode.getShotNumber())

                    if i == 0 and update == 0:
                        # Adding the first plot (first selected signal)
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
                        # Appending plot (the remaining selected signals)
                        # Else add the remaining selected node arrays
                        # (selected signals) to the existing plot
                        for j in range(0, nbRows):
                            # y-axis values
                            u = v[j]
                            # x-axis values
                            ti = t[0]
                            # Add to plot
                            # Note: do not pass again title, xlabel and ylabel
                            #       arguments if those attributes from the first
                            #       plot are to be kept.
                            plotWidget.plot(x=ti, y=u, label=label)
                    i += 1
            # Show the plotWidget, holding the plot
            plotWidget.show()

        except ValueError as e:
            logging.error(str(e))

        except Exception as e:
            logging.error(str(e))

    def onHide(self, api, figureKey):
        if figureKey in api.GetFiguresKeys():
            api.figureframes[figureKey].Hide()
