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
from PyQt5.QtWidgets import QMainWindow, QApplication
from PyQt5.QtCore import Qt
import traceback, math
import sys
import numpy as np
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizUnselectAllSignals \
    import QVizUnselectAllSignals
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignals \
    import QVizSelectSignals
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal \
    import QVizPlotSignal
from imasviz.VizUtils.QVizGlobalValues import getRGBColorList, FigureTypes
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from PyQt5.QtGui import QFont, QTextOption, QWidget, QVBoxLayout, QScrollArea

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
        self.setObjectName(figureKey)
        self.setWindowTitle(figureKey)
        self.imas_viz_api.figureframes[figureKey] = self

        # Set number of rows and columns of panels in the MultiPlot frame
        # self.rows = 2
        self.ncols = 5

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

        # Show MultiPlot window
        self.show()

    def raiseErrorIfNoSelectedArrays(self):
        return False

    def getDimension(self):
        plotDimension = "1D"
        return plotDimension

    def getGraphicsWindow(self, figureKey):
        """get graphics window.
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
        """

        # Set scrollable area
        scrollArea = QScrollArea(self)
        scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scrollArea.setWidgetResizable(True)
        scrollArea.setEnabled(True)
        scrollContent = QWidget(scrollArea)

        # Set layout for scrollable area
        scrollLayout = QVBoxLayout(scrollContent)
        scrollLayout.addWidget(graphicsWindow)
        scrollLayout.setContentsMargins(0,0,0,0)
        scrollContent.setLayout(scrollLayout)
        scrollArea.setWidget(scrollContent)

        return scrollArea

    def windowSizeAdjustement(self):
        """Adjust the size of the main window and its children.
        """

        # TODO: Add rules for different resolutions
        # - Get screen resolution (width and height)
        # self.screenGeometry=QApplication.instance().desktop().screenGeometry()
        # self.screenWidth = self.screenGeometry.width()
        # self.screenHeight = self.screenGeometry.height()
        # self.resize(self.screenWidth*0.8, self.screenHeight*0.8)

        # Set size of the graphics window
        # (depending on the number of plots and number of columns)
        if len(self.gw.centralWidget.items) < 25:
            width_gw = math.ceil(len(self.gw.centralWidget.items)/len(self.gw.centralWidget.rows))*310
            height_gw = len(self.gw.centralWidget.rows)*300
        else:
            width_gw = 1550
            height_gw = 1200
        self.gw.setMinimumSize(width_main, height_main)

        # Set size of the main window
        width_main = math.ceil(len(self.gw.centralWidget.items)/len(self.gw.centralWidget.rows))*300
        height_main = len(self.gw.centralWidget.rows)*300
        self.resize(width_gw, height_gw)
        self.setMaximumSize(self.screenWidth, self.screenHeight)

    def plot1DSelectedSignals(self, figureKey=None, update=0, all_DTV=True):
        """Plot the set of 1D signals, selected by the user, as a function of
           time to MultiPlot.
        """

        # Get window
        gw = self.getGraphicsWindow(figureKey)

        # self.applyPlotConfigurationBeforePlotting(frame=frame)

        # Plot number
        n = 0

        # TODO
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

        # Go through every opened/created DTV found in the list of DTVs, get
        # their selected plot signals and plot every signal to the same
        # MultiPlot window
        for dtv in MultiPlotWindow_DTVList:
            # Get list of selected signals in DTV
            dtv_selectedSignals = dtv.selectedSignalsDict
            # Go through the list of selected signals for every DTV
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
                    gw.plot(n=n, x=ti, y=u, label='', xlabel=xlabel,
                            ylabel=ylabel)
                    # Get the current (last) plot item, created by gw.plot()
                    currentPlotItem = gw.getCurrentPlotItem()
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
                    option = QTextOption()
                    option.setAlignment(Qt.AlignCenter)
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
        if figureKey in api.GetFiguresKeys(figureType=FigureTypes.MULTIPLOTTYPE):
            api.figureframes[figureKey].Hide()

    def getScreenGeometry(self):
        """Get screen geometry.
        Note: QApplication instance required / application must be running.
        """
        QApplication.instance().desktop().screenGeometry()

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

    def getCurrentPlotItem(self):
        # Get the current (last) plot item, created by gw.plot()
        return list(self.centralWidget.items.keys())[-1]



