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
# ****************************************************
#  TODO:
#
#    - Function definitions (from PlotSignal class)
#    def onHide
#    def getSignal
#
# ****************************************************
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
# ****************************************************

import xml.etree.ElementTree as ET
import logging
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal import QVizPlotSignal
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizAbstractPlot import QVizAbstractPlot
from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand


class QVizPlotSelectedSignals(QVizAbstractCommand, QVizAbstractPlot):
    def __init__(self, dataTreeView, figureKey=None, update=0,
                 configFile=None, all_DTV=True, strategy="TIME"):
        self.api = dataTreeView.imas_viz_api
        figureKey, plotWidget = self.api.GetPlotWidget(dataTreeView, figureKey, strategy=strategy)
        self.figureKey = figureKey
        self.update = update
        QVizAbstractCommand.__init__(self, dataTreeView, None)
        QVizAbstractPlot.__init__(self, plotWidget)
        self.plotConfig = None
        self.configFile = configFile
        self.all_DTV = all_DTV
        if self.configFile is not None:
            self.plotConfig = ET.parse(self.configFile)
        # DTV
        self.dataTreeView = dataTreeView
        # Viz_API

    def execute(self):
        if self.raiseErrorIfNoSelectedArrays():
            if len(self.dataTreeView.selectedSignalsDict) == 0:
                # Removes the current figure
                self.api.DeleteFigure(figureKey=self.figureKey)
                raise ValueError("No signal selected.")
        self.plot1DSelectedSignals(self.update,
                                   all_DTV=self.all_DTV)

    def raiseErrorIfNoSelectedArrays(self):
        return True

    def getDimension(self, treeNode):
        plotDimension = None
        if treeNode.is1D() or treeNode.is0DAndDynamic():
            plotDimension = "1D"
        else:
            logging.warning('Plots dimension larger than 1D are currently not supported.')
            logging.warning('Unsupported data type. Aborting!')
            return False
        return plotDimension

    def plot1DSelectedSignals(self, update=0, all_DTV=True):
        """Plot the set of 1D signals selected by the user as a function of time.

        Arguments
            figurekey (str) : Figure key/label.
            update    (int) :
        """
        try:

            # Total number of existing DTVs
            self.num_view = len(self.api.DTVlist)

            i = 0
            # Create a list of DTVs to specify either single DTV or a list of
            # DTVs fro, which the signals should be plotted to a single plot
            plot_DTVlist = []
            if all_DTV == False:
                plot_DTVlist = [self.dataTreeView]
            else:
                plot_DTVlist = self.api.DTVlist

            disableSlider = True
            # Go through the list of opened DTVs, get its selected plot signals dict
            # and plot the signals to the same plot widget
            for dtv in plot_DTVlist:
                # Go through DTV selected signal dictionaries
                # (each is specified by key)
                for key in dtv.selectedSignalsDict:

                    v = dtv.selectedSignalsDict[key]
                    vizTreeNode = v['QTreeWidgetItem']

                    # Check dimension
                    plotDimension = self.getDimension(vizTreeNode)

                    # Cancel plotting procedure if there is something wrong with
                    # the dimension
                    if not plotDimension:
                        return

                    key = dtv.dataSource.dataKey(vizTreeNode)
                    tup = (dtv.dataSource.shotNumber, vizTreeNode)
                    self.api.AddNodeToFigure(self.figureKey, key, tup)
                    # Get signal properties and values
                    s = self.api.GetSignal(dtv, vizTreeNode, plotWidget=self.plotWidget)
                    # Get array of time values
                    t = QVizPlotSignal.getXAxisValues(s)
                    # Get array of y-axis values
                    v = QVizPlotSignal.get1DSignalValue(s)
                    # Get number of rows of the y-axis array of values
                    nbRows = v.shape[0]

                    # Set plot labels and title
                    label, xlabel, ylabel, title = \
                        vizTreeNode.plotOptions(dtv, vizTreeNode.getShotNumber(),
                                                plotWidget=self.plotWidget)

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
                            # Creating plot
                            # Setting range manually (see IMAS-3658)
                            self.plotWidget.getPlotItem().setRange(xRange=(min(ti), max(ti)), yRange=(min(u), max(u)))
                            self.plotWidget.plot(vizTreeNode=vizTreeNode, x=ti, y=u, title='', xlabel=xlabel,
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
                            self.plotWidget.getPlotItem().setRange(xRange=(min(ti), max(ti)), yRange=(min(u), max(u)))
                            self.plotWidget.plot(vizTreeNode=vizTreeNode, x=ti, y=u, label=label)

                    if vizTreeNode.embedded_in_time_dependent_aos() and vizTreeNode.is1DAndDynamic():
                        disableSlider = False

                    i += 1

            if not disableSlider:
                self.plotWidget.setSliderComponentsDisabled(disableSlider)

            # Show the plotWidget, holding the plot
            self.plotWidget.show()

        except ValueError as e:
            logging.error(str(e))

        except Exception as e:
            logging.error(str(e))

    def onHide(self, api, figureKey):
        if figureKey in api.GetFiguresKeys():
            api.figureframes[figureKey].Hide()
