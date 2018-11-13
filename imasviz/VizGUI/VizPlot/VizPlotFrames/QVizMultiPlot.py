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

from pyqtgraph import GraphicsWindow, mkPen
import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets
import PyQt5.QtCore
import PyQt5.QtGui
import PyQt5.QtWidgets
import traceback, math
import sys
import numpy as np
from functools import partial
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizUnselectAllSignals \
    import QVizUnselectAllSignals
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignals \
    import QVizSelectSignals
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal \
    import QVizPlotSignal
from imasviz.VizUtils.QVizGlobalValues import getRGBColorList, FigureTypes
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizUtils.QVizWindowUtils import getScreenGeometry
from imasviz.VizGUI.VizPlot.QVizCustomPlotContextMenu \
    import QVizCustomPlotContextMenu
from imasviz.VizGUI.VizConfigurations.QVizSavePlotConfig \
    import QVizSavePlotConfig

class QVizMultiPlot(QtWidgets.QMainWindow):
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

        # Get screen resolution (width and height)
        self.screenWidth, self.screenHeight = getScreenGeometry()
        # Set base dimension parameter for setting plot size
        self.plotBaseDim = 300

        # Set MultiPlot object name and title if not already set
        if figureKey == None:
            figureKey = \
                self.imas_viz_api.GetNextKeyForMultiplePlots()
        self.setObjectName(figureKey)
        self.setWindowTitle(figureKey)
        self.imas_viz_api.figureframes[figureKey] = self

        # Set number of rows and columns of panels in the MultiPlot frame
        self.ncols = int(self.screenWidth*0.9/self.plotBaseDim) # round down

        # Get the indicator from which DTVs should the signals be read
        # (single or all)
        self.all_DTV = all_DTV

        # Set GraphicsWindow (holding plots)
        self.gw = self.plot1DSelectedSignals(figureKey=figureKey,
                                             all_DTV=self.all_DTV)
        # Embed GraphicsWindow inside scroll area
        scrollArea = self.setGWAsScrollArea(self.gw)

        # Set GraphicsWindow as central widget
        self.setCentralWidget(scrollArea)

        # Adjust the window and its children size
        self.windowSizeAdjustement()

        # Add menu bar
        self.addMenuBar()

        # Connect custom UI elements
        QtCore.QMetaObject.connectSlotsByName(self)

        # Show MultiPlot window
        self.show()

    def raiseErrorIfNoSelectedArrays(self):
        return False

    def getDimension(self):
        plotDimension = "1D"
        return plotDimension

    def getGraphicsWindow(self, figureKey):
        """get graphics window.

        Arguments:
            figurekey (str)  : Frame label.
        """
        if figureKey == None:
            figureKey = \
                self.imas_viz_api.GetNextKeyForMultiplePlots()
        gwin = QVizMultiPlotGraphicsWindow(parent=self, ncols=self.ncols)
        gwin.setWindowTitle(figureKey)
        self.imas_viz_api.figureframes[figureKey] = gwin
        # Set maximum size
        return gwin

    def setGWAsScrollArea(self, graphicsWindow):
        """Set scrollable graphics window - scroll area contains the graphics
        window.

        Arguments:
            graphicsWindow (GraphicsWindow) : GraphicsWindow containing the
                                              plots (PlotItems).
        """

        # Set scrollable area
        scrollArea = QtGui.QScrollArea(self)
        scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scrollArea.setWidgetResizable(True)
        scrollArea.setEnabled(True)
        scrollContent = QtGui.QWidget(scrollArea)

        # Set layout for scrollable area
        scrollLayout = QtGui.QVBoxLayout(scrollContent)
        scrollLayout.addWidget(graphicsWindow)
        scrollLayout.setContentsMargins(0,0,0,0)
        scrollContent.setLayout(scrollLayout)
        scrollArea.setWidget(scrollContent)

        return scrollArea

    def windowSizeAdjustement(self):
        """Adjust the size of the main window and its children.
        """

        # Set size of the graphics window
        # (depending on the number of plots and number of columns)
        width_gw = self.gw.centralWidget.cols*(self.plotBaseDim+10)
        height_gw = len(self.gw.centralWidget.rows)*self.plotBaseDim
        self.gw.setMinimumSize(width_gw, height_gw)

        # Set size of the main window
        width_main = self.gw.centralWidget.cols*(self.plotBaseDim+20)
        height_main = len(self.gw.centralWidget.rows)*self.plotBaseDim
        self.resize(width_main, height_main)

        # Set main window maximum size
        self.setMaximumSize(self.screenWidth, self.screenHeight)

    def plot1DSelectedSignals(self, figureKey=None, update=0, all_DTV=True):
        """Plot the set of 1D signals, selected by the user, as a function of
           time to MultiPlot.

        Arguments:
            figurekey (str)  : Frame label.
            update (int)     :
            all_DTV (bool)   : Indicator to read selected signals from single
                               DTV (from the given one) or from all DTVs.
                               Note: This has no effect when reading list
                               of signals from the configuration file.
        """

        # Get window
        gw = self.getGraphicsWindow(figureKey)

        # self.applyPlotConfigurationBeforePlotting(frame=frame)

        # Plot number
        n = 0

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

        # Go through every opened/created DTV found in the list of DTVs, get
        # their selected plot signals and plot every signal to the same
        # MultiPlot window
        for dtv in MultiPlotWindow_DTVList:
            # Get list of selected signals in DTV
            dtv_selectedSignals = dtv.selectedSignalsDict
            # Go through the list of selected signals for every DTV
            for signalKey in dtv_selectedSignals:

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
                                               signalNodeData=signalNodeData,
                                               shotNumber=shotNumber,
                                               title=figureKey)
                # Remodify label (to include '\n' for easier alignment handling)
                label = dtv.dataSource.getShortLabel() + ":\n" \
                    + signalNodeData['Path']

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
                    gw.plot(n=n, x=ti, y=u, label=label, xlabel=xlabel,
                            ylabel=ylabel)
                    # Get the current (last) plot item, created by gw.plot()
                    currentPlotItem = gw.getCurrentPlotItem()
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

                # Next plot number
                n += 1

        return gw

    def selectSignals(self, graphicsWindow, dataTreeView):
        """Select signals, listed in the configuration file.

        Arguments:
            graphicsWindow (GraphicsWindow) : GraphicsWindow containing the
                                              plots (PlotItems).
            dataTreeView (QTreeWidget) : DataTreeView object of the QTreeWidget.
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
            key = QVizGlobalOperations.getNextPanelKey(n, ncols=self.ncols)

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

        # Get a dictionary of selected signals
        dtv_selectedSignals = dataTreeView.selectedSignalsDict

        # QVizGlobalOperations. \
        #     getSortedSelectedSignals(WxDataTreeView.selectedSignals)
        return dtv_selectedSignals, selectedsignalsMap

    def addMenuBar(self):
        """Create and configure the menu bar.
        """
        # Main menu bar
        menuBar = QtWidgets.QMenuBar(self)
        options = menuBar.addMenu('Options')
        #-----------------------------------------------------------------------
        # Set new menu item for saving plot configuration
        action_onSavePlotConf = QtWidgets.QAction('Save Plot Configuration', self)
        action_onSavePlotConf.triggered.connect(self.onSavePlotConf)
        options.addAction(action_onSavePlotConf)

        # Set menu bar
        self.setMenuBar(menuBar)

    def getNumSignals(self):
        """Get number of signals intended for the MultiPlot feature
           from either opened DTVs or from configuration file if it is loaded.
        """
        if self.configFile != None and self.plotConfig != False:
            # Get number of signals through number of signal paths
            pathsList = QVizGlobalOperations.\
                getSignalsPathsFromConfigurationFile(self.configFile)
            nSignals = len(pathsList)
        else:
            # If plotConfig is not present (save configuration was
            # not used)
            nSignals = \
                len(self.imas_viz_api.getSelectedSignalsDict_allDTVs())

        return nSignals

    # def setRowsColumns(self, num_signals):
    #     """Modify the MultiPlot rows and columns depending on total number
    #     of signals."""
    #         if num_signals > 6:
    #             if num_signals <= 8:
    #                 self.rows = 2
    #                 self.cols = 4
    #             elif num_signals > 8 and num_signals <= 12:
    #                 self.rows = 3
    #                 self.cols = 4
    #             elif num_signals > 12:
    #                 self.rows = 3
    #                 self.cols = 4
    #                 print('MultiPlot plot limit reached (12)!')

    def onHideFigure(self, api, figureKey):
        """

        Arguments:
            api       (obj)  : IMASViz Application Programming Interface.
            figurekey (str)  : Frame label.
        """
        if figureKey in api.GetFiguresKeys(figureType=FigureTypes.MULTIPLOTTYPE):
            api.figureframes[figureKey].hide()

    def getScreenGeometry(self):
        """Get screen geometry.
        Note: QApplication instance required / application must be running.
        """
        QtWidgets.QApplication.instance().desktop().screenGeometry()

    def getPlotItemsDict(self):
        """Return dictionary of GraphicWindow plot items."""
        return self.gw.centralWidget.items

    @QtCore.pyqtSlot()
    def onSavePlotConf(self):
        """Save configuration for single DTV.
        """
        QVizSavePlotConfig(gWin=self.gw).execute()

    # TODO
    # def applyPlotConfigurationBeforePlotting
    # def applyPlotConfigurationAfterPlotting
    # def setPlotConfigAttribute
    # class modifyMultiPlot

class QVizMultiPlotGraphicsWindow(GraphicsWindow):
    """GraphicsWindow containing the MultiPlot plots.
    """
    def __init__(self, parent, ncols=3):
        """
        Arguments:
            parent (QtWidgets.QMainWindow) : Parent of MultiPlot GraphicsWindow.
            ncols  (int)         : Number of columns.
        """

        super(QVizMultiPlotGraphicsWindow, self).__init__(parent=parent)
        # super(QVizMultiPlotGraphicsWindow, self).__init__()

        self.parent = parent

        # Add attribute describing the number of columns
        # (same as self.centralWidget.rows is for number of rows. Initially
        # the centralWidget does not contain the 'cols' attribute)
        self.centralWidget.cols = ncols

        self.setAntialiasing(True)
        self.setBackground((255, 255, 255))
        self.resize(1500,500)
        # self.adjustSize()
        # self.setWindowTitle('pyqtgraph example: Plotting')

        # Enable antialiasing for prettier plots
        pg.setConfigOptions(antialias=True)

    def plot(self, n, x, y, label, xlabel, ylabel):
        """Add new plot to MultiPlot GraphicsWindow.

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
                         name='Plot'+str(n),
                         title=label,
                         pen=pen,
                         viewBox=QVizCustomPlotContextMenu(qWidgetParent=self))
        # p = self.addPlot(name='plotName',
        #                   title="Basic array plotting " + str(n),
        #                   row=rowNum,
        #                   col=colNum)
        # Set plotDataItem (p.dataItems[0]) name
        # TODO: find out how to properly pass 'name' to plot (addPlot() and
        #       plot() does not accept it...)
        p.dataItems[0].opts['name'] = label.replace("\n", "")
        p.showGrid(x=True, y=True)
        # p.plot(x, y, pen=pen)

        if (n+1)%self.centralWidget.cols == 0:
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
        """Return dictionary of GraphicWindow plot items."""
        return self.centralWidget.items
