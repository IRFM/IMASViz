#  Name   : QVizStackedPlotView
#
#          Provides pg.GraphicWindow that contains multiple plot panels in a
#          stacked layout.
#          Note: The wxPython predecessor for StackedPlotView are
#          'IMASVIZSubPlotViewsFrame' and 'IMASVIZ_SubPlotViewManagerBaseFrame.py'
#          classes.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#*******************************************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#*******************************************************************************

import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal \
    import QVizPlotSignal
from imasviz.VizUtils.QVizGlobalValues import getRGBColorList
from imasviz.VizGUI.VizPlot.QVizCustomPlotContextMenu \
    import QVizCustomPlotContextMenu

class QVizStackedPlotView(pg.GraphicsWindow):
    """StackedPlotView pg.GraphicsWindow containing the plots in a stacked layout.
    """

    def __init__(self, parent, ncols=1):
        """
        Arguments:
            parent (QtWidgets.QMainWindow) : Parent of TablePlotView
                                             pg.GraphicsWindow.
            ncols  (int)                   : Number of columns.
        """
        super(QVizStackedPlotView, self).__init__(parent=parent)

        self.parent = parent
        self.ncols = ncols

        self.dataTreeView = parent.getDTV()
        self.plotConfig = parent.getPlotConfig()  # dictionary
        self.imas_viz_api = parent.getIMASVizAPI()
        self.log = parent.getLog()  # QTextEdit widget
        self.figureKey = parent.getFigureKey()

        # Set base dimension parameter for setting plot size
        self.plotBaseDim = 100
        # Set bottom plot margin to remove unwanted whitespace between plot
        # widgets
        self.bPlotMargin = -15

        # Set object name and title if not already set
        self.setObjectName(self.figureKey)
        self.setWindowTitle(self.figureKey)
        # self.imas_viz_api.figureframes[self.figureKey] = self

        # Set number of rows and columns of panels in the StackedPlotView frame
        self.ncols = 1

        # Get the indicator from which DTVs should the signals be read
        # (single or all)
        self.all_DTV = parent.getAllDTV()

        # Add attribute describing the number of columns
        # (same as self.centralWidget.rows is for number of rows. Initially
        # the centralWidget does not contain the 'cols' attribute)
        self.centralWidget.cols = self.ncols

        # Set pg.GraphicsWindow (holding plots)
        self.plot1DSelectedSignals(all_DTV=self.all_DTV)

        # Enable antialiasing for prettier plots
        # pg.setConfigOptions(antialias=True)
        self.setAntialiasing(True)
        self.setBackground((255, 255, 255))
        self.centralWidget.setSpacing(0)

        self.modifySize()

    def plot1DSelectedSignals(self, update=0, all_DTV=True):
        """Plot the set of 1D signals, selected by the user, as a function of
           time to StackedPlotView.

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
        # StackedPlotView window
        for dtv in self.parent.MultiPlotView_DTVList:
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
                # label=dtv.dataSource.getShortLabel() + ":\n" \
                #     + signalNodeData['Path']

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
                              ylabel=ylabel, title=title)
                    # Get the current (last) plot item, created by self.plot()
                    currentPlotItem = self.getCurrentPlotItem()  # pg.PlotItem
                    # Add new attribute to current item, holding all signal data
                    currentPlotItem.signalData = dtv_selectedSignals[signalKey]

                    # Modify title label
                    # # Get titleLabel
                    # tLabel = currentPlotItem.titleLabel
                    # # Set title label size
                    # # Note: empty text provided as requires text argument
                    # tLabel.setText(text='', size='8pt')
                    # # Set title width
                    # tLabel.item.setPlainText(title)
                    # # Set title label width
                    # # Note: required for alignment to take effect
                    # tLabel.item.setTextWidth(500)
                    # # Set alignment as text option
                    # option = QtGui.QTextOption()
                    # option.setAlignment(QtCore.Qt.AlignCenter)
                    # tLabel.item.document().setDefaultTextOption(option)

                    # Set plotItem key (row, column)
                    plotItemKey = (currentPlotItem.row, currentPlotItem.column)

                    # If configuration is present
                    if self.plotConfig != None:
                        self.applyPlotConfigurationAfterPlotting(currentPlotItem,
                                                                 self.plotConfig)

                # Next plot number
                n += 1

    def plot(self, n, x, y, label, xlabel, ylabel, title):
        """Add new plot to StackedPlotView pg.GraphicsWindow.

        Arguments:
            n      (int)      : Plot number.
            x      (1D array) : 1D array of X-axis values.
            y      (1D array) : 1D array of Y-axis values.
            label  (str)      : Plot label.
            xlabel (str)      : Plot X-axis label.
            ylabel (str)      : Plot Y-axis label.
            title  (str)      : StackedPlotView title.
        """

        # Set pen
        pen = self.setPen()

        # Set first plot
        if n == 0:
            # Rules for first plot
            # - Set  X-Axis label to None
            xlabel = None
        elif n == (self.parent.getNumSignals(all_DTV=False) - 1):
            # Rules for last plot
            # - Set title to None
            title = None
        else:
            # Rules for mid-plots
            # - Set title to None
            title = None
            # - Set  X-Axis label to None
            xlabel = None

        # Set new plot (use IMASViz custom plot context menu)
        p = self.addPlot(title=title,
                         viewBox=QVizCustomPlotContextMenu(qWidgetParent=self))
        # Enable legend (Note: must be done before plotting!)
        p.addLegend()
        p.plot(x=x,
               y=y,
               name=label,
               xlabel=xlabel,
               ylabel=ylabel,
               pen=pen)
        # pg.PlotItem

        # p = self.addPlot(name='plotName',
        #                   title="Basic array plotting " + str(n),
        #                   row=rowNum,
        #                   col=colNum)
        # Set axis labels
        p.setLabel('left', ylabel, units='')
        p.setLabel('bottom', xlabel, units='')
        # Enable grid
        p.showGrid(x=True, y=True)
        # Add a name attribute directly to pg.PlotDataItem - a child of
        # pg.PlotData
        # p.dataItems[0].opts['name'] = label.replace("\n", "")
        p.dataItems[0].opts['name'] = label

        p.column = int(n / self.centralWidget.cols)
        p.row = int(n % self.centralWidget.cols)

        # Set plot rules
        if n == 0:
            # Rules for first plot
            # - Set reference global variable to first plot
            p.getAxis('bottom').setStyle(showValues=False)
            # - Set bottom margin
            p.setContentsMargins(0, 0, 0, self.bPlotMargin)

            p.setMinimumHeight(100)
            self.p0 = p
        elif n == (self.parent.getNumSignals(all_DTV=False) - 1):
            # Rules for last plot
            # - Remove axis values
            p.getAxis('bottom').setStyle(showValues=True)
            # - Set X and Y-axis link to first plot
            p.setXLink(self.p0)
            p.setYLink(self.p0)
            p.setMinimumHeight(100)

        else:
            # Rules for mid-plots
            # - Remove axis values
            p.getAxis('bottom').setStyle(showValues=False)
            # - Set X and Y-axis link to first plot
            p.setXLink(self.p0)
            p.setYLink(self.p0)
            # - Set bottom margin
            p.setContentsMargins(0, 0, 0, self.bPlotMargin)

            p.setMinimumHeight(60)
        # Go to next row
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
        pen = pg.mkPen(color=color, width=1, style=style)

        return pen

    def getCurrentPlotItem(self):
        """Get the current (last) plot item, created by self.plot().
        """
        return list(self.centralWidget.items.keys())[-1]

    def getPlotItemsDict(self):
        """Return dictionary of GraphicWindow plot items
        (list of pg.DataItem-s).
        """
        return self.centralWidget.items

    def modifySize(self):
        """Modify StackedPlotView view size.
        (depending on the number of plots and number of columns)
        """

        # Set suitable width and height
        self.okWidth = self.centralWidget.cols * (self.plotBaseDim + 10) * 12
        self.okHeight = len(self.centralWidget.rows) * self.plotBaseDim
        # self.setMinimumSize(self.okWidth, self.okHeight)
        self.setMinimumSize(300, self.okHeight)

    # TODO
    # class modifyStackedPlotView
