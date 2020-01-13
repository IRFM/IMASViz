#  Name   : QVizTablePlotView
#
#          Provides pg.GraphicWindow that contains multiple plot panels in a
#          table layout.
#          Note: The wxPython predecessor for MultiPlotView is
#          'PlotSelectedSignalsWithWxmplot' class.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#*******************************************************************************
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
#*******************************************************************************

import pyqtgraph as pg
import logging
from PyQt5 import QtCore, QtGui, QtWidgets
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal \
    import QVizPlotSignal
from imasviz.VizUtils.QVizGlobalValues import getRGBColorList, PlotTypes
from imasviz.VizUtils.QVizWindowUtils import getScreenGeometry
from imasviz.VizGUI.VizPlot.QVizCustomPlotContextMenu \
    import QVizCustomPlotContextMenu


class QVizTablePlotView(pg.GraphicsWindow):
    """TablePlotView pg.GraphicsWindow containing the plots in a table layout.
    """

    def __init__(self, parent, ncols=5, strategy=None):
        """
        Arguments:
            parent (QtWidgets.QMainWindow) : Parent of TablePlotView
                                             pg.GraphicsWindow.
            ncols  (int)                   : Number of columns.
        """
        super(QVizTablePlotView, self).__init__(parent=parent)

        self.parent = parent
        self.ncols = ncols

        self.dataTreeView = parent.getDTV()
        self.plotConfig = parent.getPlotConfig()  # dictionary
        self.imas_viz_api = parent.getIMASVizAPI()
        self.figureKey = parent.getFigureKey()

        # List of tree nodes contained in this plot
        self.vizTreeNodesList = []

        # Define if time or coordinate slider is required (required by
        # QVizTreeNode (!))
        self.addTimeSlider = False
        self.addCoordinateSlider = False

        # Get screen resolution (width and height)
        self.screenWidth, self.screenHeight = getScreenGeometry()
        # Set base dimension parameter for setting plot size
        self.plotBaseDim = 300

        # Set object name and title if not already set
        self.setObjectName(self.figureKey)
        self.setWindowTitle(self.figureKey)
        # self.imas_viz_api.figureframes[self.figureKey] = self

        # Set number of rows and columns of panels in the TablePlotView frame
        self.ncols = int(self.screenWidth * 0.7 / self.plotBaseDim)  # round down

        # Get the indicator from which DTVs should the signals be read
        # (single or all)
        self.all_DTV = parent.getAllDTV()

        # Add attribute describing the number of columns
        # (same as self.centralWidget.rows is for number of rows. Initially
        # the centralWidget does not contain the 'cols' attribute)
        self.centralWidget.cols = self.ncols

        # Set pg.GraphicsWindow (holding plots)
        self.plot1DSelectedSignals(all_DTV=self.all_DTV, strategy=strategy)

        self.setAntialiasing(True)
        self.setBackground((255, 255, 255))

        self.modifySize()

        # Enable antialiasing for prettier plots
        pg.setConfigOptions(antialias=True)

    def getType(self):
        return PlotTypes.TABLE_PLOT


    def plot1DSelectedSignals(self, update=0, all_DTV=True, strategy='DEFAULT'):
        """Plot the set of 1D signals, selected by the user, as a function of
           time to TablePlotView.

        Arguments:
            update (int)     :
            all_DTV (bool)   : Indicator to read selected signals from single
                               DTV (from the given one) or from all DTVs.
                               Note: This has no effect when reading list
                               of signals from the configuration file.
        """

        # self.applyPlotConfigurationBeforePlotting(frame=frame)

        # Plot number
        n = 0

        # Go through every opened/created DTV found in the list of DTVs, get
        # their selected plot signals and plot every signal to the same
        # TablePlotView window
        for dtv in self.parent.MultiPlotView_DTVList:
            # Get list of selected signals in DTV
            dtv_selectedSignals = dtv.selectedSignalsDict
            # Go through the list of selected signals for every DTV
            for signalKey in dtv_selectedSignals:

                # Get node data
                signalNode = dtv_selectedSignals[signalKey]['QTreeWidgetItem']

                # Append the node to the list of tree nodes
                self.vizTreeNodesList.append(signalNode)

                key = dtv.dataSource.dataKey(signalNode)
                tup = (dtv.dataSource.shotNumber, signalNode)
                self.imas_viz_api.AddNodeToFigure(self.figureKey, key, tup)

                s= self.imas_viz_api.GetSignal(dataTreeView=self.dataTreeView,
                                            vizTreeNode=signalNode,
                                            plotWidget=self,
                                            strategy=strategy)

                t = QVizPlotSignal.getTime(s)
                
                # Get array of y-axis values
                v = QVizPlotSignal.get1DSignalValue(s)

                # Get number of rows of the y-axis array of values
                # TODO/Note: as it seems the QVizPlotSignal is used for single
                #            signals only, hence nbRows == 1 (always)
                nbRows = v.shape[0]

                # Set plot options
                label, xlabel, ylabel, title = \
                    signalNode.plotOptions(dataTreeView=dtv,
                                           title=self.figureKey,
                                           plotWidget=self,
                                           strategy=strategy)

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
                    if len(u) != len(ti):
                        mess = 'x,y shapes are different, ignoring plot with label:' + label
                        print(mess)
                        logging.error(mess)
                        continue
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
                    tLabel.item.setTextWidth(self.plotBaseDim)
                    # Set alignment as text option
                    option = QtGui.QTextOption()
                    option.setAlignment(QtCore.Qt.AlignCenter)
                    tLabel.item.document().setDefaultTextOption(option)

                    # Set plotItem key (row, column)
                    plotItemKey = (currentPlotItem.row, currentPlotItem.column)

                    # If configuration is present
                    if self.plotConfig is not None:
                        self.parent.applyPlotConfigurationAfterPlotting(currentPlotItem)

                # Next plot number
                n += 1

    def plot(self, n, x, y, label, xlabel, ylabel):
        """Add new plot to TablePlotView pg.GraphicsWindow.

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
        pen = pg.mkPen(color=color, width=3, style=style)

        return pen

    def getCurrentPlotItem(self):
        """Get the current (last) plot item, created by gw.plot().
        """
        if len(self.centralWidget.items.keys()) > 0:
            return list(self.centralWidget.items.keys())[-1]
        return None

    def getPlotItemsDict(self):
        """Return dictionary of GraphicWindow plot items
        (list of pg.DataItem-s).
        """
        return self.centralWidget.items

    def modifySize(self):
        """Modify TablePlotView size.
        (depending on the number of plots and number of columns)
        """

        # Set suitable width and height
        self.okWidth = self.centralWidget.cols * (self.plotBaseDim + 50)
        self.okHeight = len(self.centralWidget.rows) * self.plotBaseDim
        self.setMinimumSize(self.okWidth, self.okHeight)

    # TODO
    # class modifyTablePlotView
