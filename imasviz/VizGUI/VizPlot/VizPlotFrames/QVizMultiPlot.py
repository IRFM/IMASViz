#  Name   : QVizMultiPlot
#
#          Provides multiplot template.
#          Note: The wxPython predecessor for MultiPlots is
#          'PlotSelectedSignalsWithWxmplot' class.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#****************************************************

# from imasviz.gui_commands.plot_commands.PlotSignal import PlotSignal
# from imasviz.gui_commands.plot_commands.PlotSelectedSignals import PlotSelectedSignals
# from imasviz.plotframes.IMASVIZMultiPlotFrame import IMASVIZMultiPlotFrame
# from imasviz.gui_commands.select_commands.SelectSignals import SelectSignals
# from imasviz.gui_commands.select_commands.UnselectAllSignals import UnselectAllSignals
# from imasviz.util.QVizGlobalOperations import QVizGlobalOperations
# from imasviz.util.QVizGlobalValues import FigureTypes
# from wxmplot.utils import Closure
# from wxmplot.plotpanel import PlotPanel
# import matplotlib.pyplot as plt
from pyqtgraph import GraphicsWindow, mkPen
import pyqtgraph as pg
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import Qt
import traceback
import sys
import numpy as np
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizUnselectAllSignals \
    import QVizUnselectAllSignals
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignals \
    import QVizSelectSignals
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal \
    import QVizPlotSignal
from imasviz.VizUtils.QVizGlobalValues import getRGBColorList


class QVizMultiPlot(QMainWindow):
    """Main MultiPlot window for plotting the selected signals.
    """
    def __init__(self, dataTreeView, figureKey=0, update=0,
                 configFile = None, all_DTV = True):
        """
        Arguments:
            dataTreeView (QTreeWidget) : DataTreeView object of the QTreeWidget.
            figurekey (str)  : Frame label.
            update (int)     :
            configFile (str) : System path to the configuration file.
            all_DTV (bool)   : Indicator to read selected signals from single
                               DTV (from the given one) or from all DTVs.
                               Note: This has no effect when reading list
                               of signals from the configuration file.
        """
        super(QVizMultiPlot, self).__init__(parent=dataTreeView)

        self.dataTreeView = dataTreeView
        self.configFile = configFile
        self.imas_viz_api = self.dataTreeView.imas_viz_api

        # Set MultiPlot object name and title if not already set
        if figureKey == None:
            figureKey = \
                self.imas_viz_api.GetNextKeyForMultiplePlots()
        self.resize(1000,300)
        self.setObjectName(figureKey)
        self.setWindowTitle(figureKey)
        self.imas_viz_api.figureframes[figureKey] = self

        # Set number of rows and columns of panels in the MultiPlot frame
        self.rows = 2
        self.ncols = 3

        # Get the indicator from which DTVs should the signals be read
        # (single or all)
        self.all_DTV = all_DTV

        self.gw = self.plot1DSelectedSignals(figureKey=figureKey,
                                             all_DTV=self.all_DTV)
        # Set size (depending on the number of plots and number of columns)
        # self.resize(300*self.ncols, (len(self.gw.centralWidget.items)/self.ncols)*300)

        self.setCentralWidget(self.gw)

        self.show()

    def raiseErrorIfNoSelectedArrays(self):
        return False

    def getDimension(self):
        plotDimension = "1D"
        return plotDimension

    def getGraphicsWindow(self, figureKey):
        if figureKey == None:
            figureKey = \
                self.imas_viz_api.GetNextKeyForMultiplePlots()
        gwin = QVizMultiPlotGraphicsWindow(parent=self, ncols=self.ncols)
        gwin.setWindowTitle(figureKey)
        self.imas_viz_api.figureframes[figureKey] = gwin
        # self.setCentralWidget(gwin)
        return gwin

    def plot1DSelectedSignals(self, figureKey=None, update=0, all_DTV=True):
        """Plot the set of 1D signals, selected by the user, as a function of
           time to MultiPlot.
        """

        # Get window
        gw = self.getGraphicsWindow(figureKey)

        # self.applyPlotConfigurationBeforePlotting(frame=frame)

        # Plot number
        n = 0

        # # Set maximum number of plots within frame
        # maxNumberOfPlots = self.rows*self.ncols;

        dtv_selectedSignals = []

        MultiPlotWindow_DTVList = []

        # plotConfig_used = False

        # If plotConfig is available (e.g. save configuration was loaded)
        if self.configFile != None:
            # Select signals, saved in the save configuration. Return the
            # list of signals as 'dtv_selectedSignals'.
            # Get panel plots count
            dtv_selectedSignals, panelPlotsCount = \
                self.selectSignals(gw, dataTreeView=self.dataTreeView)
            # Add a single DTV to the list
            MultiPlotWindow_DTVList.append(self.dataTreeView)
        else:
            # Else if plotConfig is not present (save configuration was
            # not used)
            if self.all_DTV != False:
                # Get the list of all currently opened DTVs
                MultiPlotWindow_DTVList = self.imas_viz_api.DTVlist
            else:
                # Add a single DTV to the list
                MultiPlotWindow_DTVList.append(self.dataTreeView)

        # Go through every opened/created DTV from the list, get its
        # selected plot signals and plot every single to the same
        # MultiPlot window
        for dtv in MultiPlotWindow_DTVList:
            """Get list of selected signals in DTV"""
            dtv_selectedSignals = self.dataTreeView.selectedSignalsDict

            for signalKey in dtv_selectedSignals:

                # if n + 1 > maxNumberOfPlots:
                #     break

                # Get node data
                signalNodeData = dtv_selectedSignals[signalKey]['nodeData']

                key = dtv.dataSource.dataKey(signalNodeData)
                tup = (dtv.dataSource.shotNumber, signalNodeData)
                self.imas_viz_api.addNodeToFigure(figureKey, key, tup)

                # Get signal properties and values
                s = QVizPlotSignal.getSignal(dtv, signalNodeData)
                # Get array of time values
                t = QVizPlotSignal.getTime(s)
                # Get array of y-axis values
                v = QVizPlotSignal.get1DSignalValue(s)

                # Get IDS case shot number
                shotNumber = dtv_selectedSignals[signalKey]['shotNumber']

                # Get number of rows of the y-axis array of values
                # TODO/Note: as it seems the QVizPlotSignal is used for single
                #            signals only, hence nbRows == 1 (always)
                nbRows = v.shape[0]

                # Set plot options
                label, xlabel, ylabel, title = \
                    QVizPlotSignal.plotOptions(self.dataTreeView,
                                               signalNodeData=signalNodeData,
                                               shotNumber=shotNumber,
                                               title=figureKey)

                # Add plot
                for i in range(0, nbRows):
                    # y-axis values
                    u = v[i]
                    # x-axis values
                    # ti = t[i]
                    ti = t[0]
                    gw.plot(n=n, x=ti, y=u, label=label, xlabel=xlabel,
                            ylabel=ylabel)
                    # Get the current (last) plot item, created by gw.plot()
                    currentPlotItem = list(gw.centralWidget.items.keys())[-1]
                    # Modify plot label text size (have to specify text=label
                    # again, as setText() requires it)
                    currentPlotItem.titleLabel.setText(text=label, size='10pt')

                # if update == 1:
                #     # Add plot to existing plot
                #     for i in range(0, nbRows):
                #         # y-axis values
                #         u = v[i]
                #         # x-axis values
                #         # ti = t[i]
                #         ti = t[0]
                #         gw.plot(x=ti, y=u, label=label)
                # else:
                #     # Create new plot
                #     for i in range(0, nbRows):
                #         # y-axis values
                #         u = v[i]
                #         # x-axis values
                #         ti = t[0]

                #         if i == 0:
                #             # New plot
                #             gw.plot(x=ti, y=u, label=label, xlabel=xlabel,
                #                             ylabel=ylabel)
                #         else:
                #             # Add plot
                #             gw.plot(x=ti, y=u, label=label)

                n += 1

        return gw

    def selectSignals(self, graphicsWindow, dataTreeView):
        """Select signals, listed in the configuration file.
        """
        selectedsignalsMap = {} #key = panel key, value = selected arrays count
        pathsList = []
        # Unselect all signals
        QVizUnselectAllSignals(dataTreeView).execute()

        # for n in range(0, len(frame.panels)):

        # Extract all paths from the configuration file
        getNextPath = True
        n = 0
        while getNextPath == True:
            key = GlobalOperations.getNextPanelKey(n, ncols=self.ncols)

            selectedArrays = \
                self.plotConfig.findall(".//*[@key='" + str(key) +
                                        "']/selectedArray")
            if selectedArrays == None:
                getNextPath = False
                break

            selectedsignalsMap[key] = len(selectedArrays)
            for selectedArray in selectedArrays:
                # Get signal paths
                pathsList.append(selectedArray.get("path"))

        # Select the signals
        QVizSelectSignals(dataTreeView, pathsList).execute()

        dtv_selectedSignals = dataTreeView.selectedSignalsDict

        # GlobalOperations. \
        #     getSortedSelectedSignals(WxDataTreeView.selectedSignals)
        return dtv_selectedSignals, selectedsignalsMap

    # TODO
    # def getNumSignals
    # def setRowsColumns
    # def applyPlotConfigurationBeforePlotting
    # def applyPlotConfigurationAfterPlotting
    # def setPlotConfigAttribute
    # def onHide
    # class modifyMultiPlot

class QVizMultiPlotGraphicsWindow(GraphicsWindow):
    """GraphicsWindow containing the MultiPlot plots.
    """
    def __init__(self, parent, ncols=3):
        """
        Arguments:
            parent (QMainWindow) : Parent of MultiPlot GraphicsWindow.
            ncols  (int)         : Number of columns.
        """

        super(QVizMultiPlotGraphicsWindow, self).__init__(parent=parent)
        # super(QVizMultiPlotGraphicsWindow, self).__init__()

        self.ncols = ncols

        self.setAntialiasing(True)
        self.setBackground((255, 255, 255))
        self.resize(1500,500)
        # self.adjustSize()
        # self.setWindowTitle('pyqtgraph example: Plotting')

        # Enable antialiasing for prettier plots
        pg.setConfigOptions(antialias=True)

    def plot(self, n, x, y, label, xlabel, ylabel):

        # Set pen
        pen = self.setPen()
        # Set new plot
        p = self.addPlot(name = 'Plot'+str(n),
                         title=label,
                         pen=pen)
        # p = self.addPlot(name='plotName',
        #                   title="Basic array plotting " + str(n),
        #                   row=rowNum,
        #                   col=colNum)

        p.showGrid(x=True, y=True)
        p.plot(x, y, pen=pen)

        if (n+1)%self.ncols == 0:
            self.nextRow()

    @staticmethod
    def setPen():
        """Set pen (line design) for plot.
        """
        # Set line color
        # - Get list of available global colors (RGB)
        RGBlist = getRGBColorList()
        # - Note: self.RGBlist[0] -> blue color
        color = RGBlist[0]
        # Set style
        style = Qt.SolidLine
        # Set pen
        pen = mkPen(color=color, width=3, style=style)

        return pen



