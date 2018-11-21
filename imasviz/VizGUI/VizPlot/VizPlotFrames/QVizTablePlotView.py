#  Name   : QVizTablePlotView
#
#          Provides multiplot template.
#          Note: The wxPython predecessor for MultiPlotView is
#          'PlotSelectedSignalsWithWxmplot' class.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#*******************************************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#*******************************************************************************

from pyqtgraph import GraphicsWindow, mkPen
import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets
import PyQt5.QtCore
import PyQt5.QtGui
import PyQt5.QtWidgets
import xml.etree.ElementTree as ET
import traceback
import math
import sys
import numpy as np
from functools import partial
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizUnselectAllSignals \
    import QVizUnselectAllSignals
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignals \
    import QVizSelectSignals
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignalsFromConfig \
    import QVizSelectSignalsFromConfig
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal \
    import QVizPlotSignal
from imasviz.VizUtils.QVizGlobalValues import getRGBColorList, FigureTypes
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizUtils.QVizWindowUtils import getScreenGeometry
from imasviz.VizGUI.VizPlot.QVizCustomPlotContextMenu \
    import QVizCustomPlotContextMenu
from imasviz.VizGUI.VizConfigurations.QVizSavePlotConfig \
    import QVizSavePlotConfig


class QVizTablePlotView(GraphicsWindow):
    """TablePlotView GraphicsWindow containing the plots in a table layout.
    """

    def __init__(self, parent, ncols=5):
        """
        Arguments:
            parent (QtWidgets.QMainWindow) : Parent of TablePlotView GraphicsWindow.
            ncols  (int)         : Number of columns.
        """
        super(QVizTablePlotView, self).__init__(parent=parent)

        self.parent = parent
        self.ncols = ncols

        self.dataTreeView = parent.getDTV()
        self.plotConfig = parent.getPlotConfig()  # dictionary
        self.imas_viz_api = parent.getIMASVizAPI()
        self.log = parent.getLog()  # QTextEdit widget
        self.figureKey = parent.getFigureKey()

        # Get screen resolution (width and height)
        self.screenWidth, self.screenHeight = getScreenGeometry()
        # Set base dimension parameter for setting plot size
        self.plotBaseDim = 300

        # Set TablePlotView object name and title if not already set
        self.setObjectName(self.figureKey)
        self.setWindowTitle(self.figureKey)
        # self.imas_viz_api.figureframes[self.figureKey] = self

        # Set number of rows and columns of panels in the TablePlotView frame
        self.ncols = int(self.screenWidth * 0.9 / self.plotBaseDim)  # round down

        # Get the indicator from which DTVs should the signals be read
        # (single or all)
        self.all_DTV = parent.getAllDTV()

        # Add attribute describing the number of columns
        # (same as self.centralWidget.rows is for number of rows. Initially
        # the centralWidget does not contain the 'cols' attribute)
        self.centralWidget.cols = self.ncols

        # Set GraphicsWindow (holding plots)
        self.plot1DSelectedSignals(all_DTV=self.all_DTV)

        self.setAntialiasing(True)
        self.setBackground((255, 255, 255))

        self.modifySize()

        # Enable antialiasing for prettier plots
        pg.setConfigOptions(antialias=True)

    def plot1DSelectedSignals(self, update=0, all_DTV=True):
        """Plot the set of 1D signals, selected by the user, as a function of
           time to TablePlotView.

        Arguments:
            figurekey (str)  : Frame label.
            update (int)     :
            all_DTV (bool)   : Indicator to read selected signals from single
                               DTV (from the given one) or from all DTVs.
                               Note: This has no effect when reading list
                               of signals from the configuration file.
        """

        # self.applyPlotConfigurationBeforePlotting(frame=frame)

        # Plot number
        n = 0

        dtv_selectedSignals = []

        TablePlotView_DTVList = []

        # If configuration file is available (e.g. save configuration was
        # loaded)
        if self.plotConfig != None:
            # Select signals, saved in the save configuration. Return the
            # list of signals as 'dtv_selectedSignals'.
            # Get panel plots count
            dtv_selectedSignals, panelPlotsCount = \
                QVizSelectSignalsFromConfig.execute(self,
                                                    dataTreeView=self.dataTreeView,
                                                    config=self.plotConfig)
            # Add a single DTV to the list
            TablePlotView_DTVList.append(self.dataTreeView)
        else:
            # Else if configuration file is not present (save configuration was
            # not used)
            if self.all_DTV != False:
                # Get the list of all currently opened DTVs
                TablePlotView_DTVList = self.imas_viz_api.DTVlist
            else:
                # Add a single DTV to the list
                TablePlotView_DTVList.append(self.dataTreeView)

        # Go through every opened/created DTV found in the list of DTVs, get
        # their selected plot signals and plot every signal to the same
        # TablePlotView window
        for dtv in TablePlotView_DTVList:
            # Get list of selected signals in DTV
            dtv_selectedSignals = dtv.selectedSignalsDict
            # Go through the list of selected signals for every DTV
            for signalKey in dtv_selectedSignals:

                # Get node data
                signalNode = dtv_selectedSignals[signalKey]['QTreeWidgetItem']
                signalNodeData = signalNode.dataDict

                key = dtv.dataSource.dataKey(signalNodeData)
                tup = (dtv.dataSource.shotNumber, signalNodeData)
                self.imas_viz_api.addNodeToFigure(self.figureKey, key, tup)

                # Get signal properties and values
                s = QVizPlotSignal.getSignal(dtv, signalNodeData)
                # Get array of time values
                t = QVizPlotSignal.getTime(s)
                # Get array of y-axis values
                v = QVizPlotSignal.get1DSignalValue(s)
                # TODO (idea): create global getSignal(), getTime(),
                # get1DSignalValue to be used by all plot frame routines

                # Get IDS case shot number
                shotNumber = dtv_selectedSignals[signalKey]['shotNumber']

                # Get number of rows of the y-axis array of values
                # TODO/Note: as it seems the QVizPlotSignal is used for single
                #            signals only, hence nbRows == 1 (always)
                nbRows = v.shape[0]

                # Set plot options
                label, xlabel, ylabel, title = \
                    QVizPlotSignal.plotOptions(dataTreeView=dtv,
                                               signalNode=signalNode,
                                               shotNumber=shotNumber,
                                               title=self.figureKey)
                # Remodify label (to include '\n' for easier alignment handling)
                label = dtv.dataSource.getShortLabel() + ":\n" \
                    + signalNode.getPath()

                # Add plot
                for i in range(0, nbRows):
                    # y-axis values
                    u = v[i]
                    # x-axis values
                    # ti = t[i]
                    ti = t[0]
                    # Add plot
                    # Note: label='' is used because it is redefined with
                    # setText(text='', size='8pt')
                    self.plot(n=n, x=ti, y=u, label=label, xlabel=xlabel,
                              ylabel=ylabel)
                    # Get the current (last) plot item, created by self.plot()
                    currentPlotItem = self.getCurrentPlotItem()  # pg.PlotItem
                    # Add new attribute to current item, holding all signal data
                    currentPlotItem.signalData = dtv_selectedSignals[signalKey]
                    # Get titleLabel
                    tLabel = currentPlotItem.titleLabel
                    # Set title label size
                    # Note: empty text provided as requires text argument
                    tLabel.setText(text='', size='8pt')
                    # Set title width
                    tLabel.item.setPlainText(label)
                    # Set title label width
                    # Note: required for alignment to take effect
                    tLabel.item.setTextWidth(250)
                    # Set alignment as text option
                    option = QtGui.QTextOption()
                    option.setAlignment(QtCore.Qt.AlignCenter)
                    tLabel.item.document().setDefaultTextOption(option)

                    # Set plotItem key (row, column)
                    plotItemKey = (currentPlotItem.row, currentPlotItem.column)

                    # If configuration is present
                    if self.plotConfig is not None:
                        self.parent.applyPlotConfigurationAfterPlotting(currentPlotItem,
                                                                        self.plotConfig)

                # Next plot number
                n += 1

    def plot(self, n, x, y, label, xlabel, ylabel):
        """Add new plot to TablePlotView GraphicsWindow.

        Arguments:
            n      (int)      : Plot number.
            x      (1D array) : 1D array of X-axis values.
            y      (1D array) : 1D array of Y-axis values.
            label  (str)      : Plot label.
            xlabel (str)      : Plot X-axis label.
            ylabel (str)      : Plot Y-axis label.
        """

        # Set pen
        pen = self.setPen()
        # Set new plot (use IMASViz custom plot context menu)
        p = self.addPlot(x=x,
                         y=y,
                         name='Plot' + str(n),
                         title=label.replace("\n", ""),
                         xlabel=xlabel,
                         ylabel=ylabel,
                         pen=pen,
                         viewBox=QVizCustomPlotContextMenu(qWidgetParent=self))
        # pg.PlotItem

        # p = self.addPlot(name='plotName',
        #                   title="Basic array plotting " + str(n),
        #                   row=rowNum,
        #                   col=colNum)
        # p.plot(x, y, pen=pen)
        # Set axis labels
        p.setLabel('left', ylabel, units='')
        p.setLabel('bottom', xlabel, units='')
        # Enable grid
        p.showGrid(x=True, y=True)
        # Add a name attribute directly to pg.PlotDataItem - a child of
        # pg.PlotData
        p.dataItems[0].opts['name'] = label.replace("\n", "")

        p.column = int(n / self.centralWidget.cols)
        p.row = int(n % self.centralWidget.cols)

        if (n + 1) % self.centralWidget.cols == 0:
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
        style = QtCore.Qt.SolidLine
        # Set pen
        pen = mkPen(color=color, width=3, style=style)

        return pen

    def getCurrentPlotItem(self):
        """Get the current (last) plot item, created by gw.plot().
        """
        return list(self.centralWidget.items.keys())[-1]

    def getPlotItemsDict(self):
        """Return dictionary of GraphicWindow plot items
        (list of pg.DataItem-s).
        """
        return self.centralWidget.items

    def modifySize(self):
        """Modify multiplot view size.
        (depending on the number of plots and number of columns)
        """

        # Set suitable width and height
        self.okWidth = self.centralWidget.cols * (self.plotBaseDim + 10)
        self.okHeight = len(self.centralWidget.rows) * self.plotBaseDim
        self.setMinimumSize(self.okWidth, self.okHeight)
