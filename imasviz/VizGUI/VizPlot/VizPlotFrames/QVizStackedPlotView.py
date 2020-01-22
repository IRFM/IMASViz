#  Name   : QVizStackedPlotView
#
#          Provides a QWidget that contains pg.GraphicWindow with multiple plot
#          views in a stacked layout.
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
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
#*******************************************************************************

import pyqtgraph as pg
from pyqtgraph.graphicsItems.ViewBox.ViewBox import ViewBox
from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtWidgets import QWidget, QGridLayout, QCheckBox, QMainWindow
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal \
    import QVizPlotSignal
from imasviz.VizUtils.QVizGlobalValues import getRGBColorList, PlotTypes
from imasviz.VizGUI.VizPlot.QVizCustomPlotContextMenu \
    import QVizCustomPlotContextMenu
from imasviz.VizDataAccess.QVizDataAccessFactory import QVizDataAccessFactory


class QVizStackedPlotView(QWidget):

    def __init__(self, parent: QMainWindow, strategy=None):

        super(QVizStackedPlotView, self).__init__(parent=parent)

        # Set parent
        self.parent = parent
        # Get parent DTV
        # self.dataTreeView = parent.getDTV()
        # Get dictionary associated to plot configuration
        self.plotConfig = parent.getPlotConfig()  # dictionary
        # Get API
        self.imas_viz_api = parent.getIMASVizAPI()
        # Get figurekey (label for the SPV window)
        self.figureKey = parent.getFigureKey()

        # Get the indicator from which DTVs should the signals be read
        # (single or all)
        self.all_DTV = parent.getAllDTV()

        # Set graphicsWindow
        self.graphicsWindow = StackedPlotWindow(self, strategy=strategy)
        # Get a list of viewBoxes each plot has its own associated viewbox)
        self.viewBoxes = self.graphicsWindow.viewBoxList
        # Get a list of plots
        self.plotList = self.graphicsWindow.plotList
        # Set layout
        gridLayout = QGridLayout()
        # Add graphicsWindow to layout
        # Note: position 0, 0, width=1 column, -1 -> stretch through whole row
        gridLayout.addWidget(self.graphicsWindow, 0, 0, 1, -1)

        # Set layout
        self.setLayout(gridLayout)

        # Add checkbox for enabling/disabling dragging all plots together e.g.
        # moving view in one plot will move also view in all plots
        self.addCheckBoxGroupPanMode()

        self.addCheckBoxDisplayAllXAxis()
        """Add checkbox for enabling/disabling showing X axis of all plots
        (intended to be used with group pan mode).
        """

        # Set base dimension parameter for setting plot size
        self.plotBaseDim = 100
        # Set window size
        self.setWindowSize()

    def setWindowSize(self):
        """Set StackedPlotView window size
        (depending on the number of plots and number of columns).
        """

        # Set suitable width and height
        self.okWidth = self.graphicsWindow.centralWidget.cols * (self.plotBaseDim + 10) * 12
        self.okHeight = len(self.graphicsWindow.centralWidget.rows) * self.plotBaseDim
        # self.setMinimumSize(self.okWidth, self.okHeight)
        self.setMinimumSize(300, self.okHeight)

    def addCheckBoxGroupPanMode(self):
        """Add checkbox for enabling/disabling dragging all plots together e.g.
        moving view in one plot will move also view in all plots.
        """
        self.groupPanMode = QCheckBox()
        self.groupPanMode.setChecked(True)
        self.groupPanMode.setText('Group pan mode')
        # On checkbox stateChanged signal enable/disable dragging plots together
        self.groupPanMode.stateChanged.connect(self.checkGroupPanMode)
        # Add checkbox to layout
        self.layout().addWidget(self.groupPanMode, 1, 0, 1, 1)

    def addCheckBoxDisplayAllXAxis(self):
        """Add checkbox for enabling/disabling showing X axis of all plots
        (intended to be used with group pan mode).
        """
        self.displayAllXAxis = QCheckBox()
        self.displayAllXAxis.setChecked(False)
        self.displayAllXAxis.setText('Display X axis of all plots')
        # On checkbox stateChanged signal enable/disable dragging plots together
        self.displayAllXAxis.stateChanged.connect(self.checkDisplayAllXAxis)
        # Add checkbox to layout
        self.layout().addWidget(self.displayAllXAxis, 2, 0, 1, 1)


    @pyqtSlot()
    def checkGroupPanMode(self):
        """Check value of groupPanMode checkbox and change blockLink
        (e.g. axis links between plots -> dragging views together) accordingly.
        """

        # If checkbox is checked enable the links, otherwise disable them
        if self.groupPanMode.isChecked():
            [el.blockLink(False) for el in self.viewBoxes]
        else:
            [el.blockLink(True) for el in self.viewBoxes]

    @pyqtSlot()
    def checkDisplayAllXAxis(self):
        """Check value of groupPanMode checkbox and change display of X axis
        of all plots accordingly.
        """

        # If checkbox is checked enable the links, otherwise disable them
        if self.displayAllXAxis.isChecked():
            [el.getAxis('bottom').setStyle(showValues=True) for el in self.plotList]
        else:
            # Set false for all plots except for the last/bottom one
            [el.getAxis('bottom').setStyle(showValues=False) for el in self.plotList[:-1]]

class StackedPlotWindow(pg.GraphicsWindow):
    """View containing the plots in a stacked layout.
    """

    def __init__(self, parent: QWidget, ncols: int=1, strategy="TIME"):
        """
        Arguments:
            parent : Parent of StackedPlotWindow (QVizStackedPlotView).
            ncols  : Number of columns.
        """
        super(StackedPlotWindow, self).__init__(parent=parent)

        self.parent = parent
        # Set number of columns (the default is 1)
        self.ncols = ncols

        # Get parent DTV
        # self.dataTreeView = parent.getDTV()
        self.plotConfig = parent.plotConfig  # dictionary
        # Get API
        self.imas_viz_api = parent.imas_viz_api
        # Get figure key / label for the SPV window
        self.figureKey = parent.figureKey

        # List of tree nodes contained in this plot
        self.vizTreeNodesList = []

        # Define if time or coordinate slider is required (required by
        # QVizTreeNode (!))
        self.addTimeSlider = False
        self.addCoordinateSlider = False

        self.plotStrategy = strategy

        # Set bottom plot margin to remove unwanted whitespace between plot
        # widgets
        self.bPlotMargin = -15

        # Set object name and title if not already set
        self.setObjectName(self.figureKey)
        self.setWindowTitle(self.figureKey)

        # Set number of rows and columns of panels in the StackedPlotView frame
        self.ncols = 1

        # Get the indicator from which DTVs should the signals be read
        # (single or all)
        self.all_DTV = parent.all_DTV

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


    def getType(self):
        return PlotTypes.STACKED_PLOT

    def setStrategy(self, strategy):
        self.plotStrategy = strategy

    def getStrategy(self):
        return self.plotStrategy

    def plot1DSelectedSignals(self, update: int=0, all_DTV: bool=True):
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

        # Clear viewBoxList
        self.viewBoxList = []

        # Clear plot list
        self.plotList = []

        # for dtv in self.getDTVList():
        #     # Get list of selected signals in DTV
        #     dtv_selectedSignals = dtv.selectedSignalsDict
        #     # Go through the list of selected signals for every DTV
        #     for signalKey in dtv_selectedSignals:
        #         # Get node data
        #         signalNode = dtv_selectedSignals[signalKey]['QTreeWidgetItem']
        #         if strategy == 'TIME' and not signalNode.hasTimeAxis():
        #             raise ValueError('Unable to plot node ' + signalNode.getName() + ' which does not depend on time.')

        for dtv in self.getDTVList():
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

                # Get signal properties and values
                s = self.imas_viz_api.GetSignal(dtv, signalNode, plotWidget=self)

                # Get array of time values
                t = QVizPlotSignal.getXAxisValues(s)
                # Get array of y-axis values
                v = QVizPlotSignal.get1DSignalValue(s)

                # TODO (idea): create global getSignal(), getTime(),
                # get1DSignalValue to be used by all plot frame routines

                # Get number of rows of the y-axis array of values
                # TODO/Note: as it seems the QVizPlotSignal is used for single
                #            signals only, hence nbRows == 1 (always)
                nbRows = v.shape[0]

                # Set plot options
                label, xlabel, ylabel, title = \
                    signalNode.plotOptions(dataTreeView=dtv,
                                               title=self.figureKey,
                                               plotWidget=self)

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
                    if self.plotConfig is not None:
                        self.applyPlotConfigurationAfterPlotting(currentPlotItem)

                # Next plot number
                n += 1

    def plot(self, n: int, x: list, y: list, label: str,
             xlabel: str, ylabel: str, title: str):
        """Add new plot to StackedPlotView pg.GraphicsWindow.

        Arguments:
            n      (int)      : Plot number.
            x      (1D array) : 1D array of X-axis values (list or numpy array).
            y      (1D array) : 1D array of Y-axis values (list or numpy array).
            label  (str)      : Plot label.
            xlabel (str)      : Plot X-axis label.
            ylabel (str)      : Plot Y-axis label.
            title  (str)      : StackedPlotView title.
        """

        # Set pen
        pen = self.createPen()

        # Set first plot
        if n == 0:
            # Rules for first plot
            # - Set  X-Axis label to None
            xlabel = None
        elif n == (self.getNumSignals(all_DTV=False) - 1):
            # Rules for last plot
            # - Set title to None
            title = None
        else:
            # Rules for mid-plots
            # - Set title to None
            title = None
            # - Set  X-Axis label to None
            xlabel = None

        # Set viewBox
        viewBox = QVizCustomPlotContextMenu(qWidgetParent=self)

        # Set new plot (use IMASViz custom plot context menu)
        p = self.addPlot(title=title,
                         viewBox=viewBox)
        # Add viewBox to list of viewBoxes
        self.viewBoxList.append(viewBox)

        # Enable legend (Note: must be done before plotting!)
        p.addLegend()
        #p.getViewBox().enableAutoRange(axis=ViewBox.YAxis, enable=False)
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
            self.pg = p
        elif n == (self.getNumSignals(all_DTV=False) - 1):
            # Rules for last plot
            # - Remove axis values
            p.getAxis('bottom').setStyle(showValues=True)
            # - Set X and Y-axis link to first plot
            p.setXLink(self.pg)
            p.setYLink(self.pg)
            p.setMinimumHeight(100)

        else:
            # Rules for mid-plots
            # - Remove axis values
            p.getAxis('bottom').setStyle(showValues=False)
            # - Set X and Y-axis link to first plot
            p.setXLink(self.pg)
            p.setYLink(self.pg)
            # - Set bottom margin
            p.setContentsMargins(0, 0, 0, self.bPlotMargin)

            p.setMinimumHeight(60)

        # Add plot to a list of plots
        self.plotList.append(p)

        # Go to next row
        self.nextRow()

    @staticmethod
    def createPen():
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

    def getDTVList(self):
        """Return list of opened DTVs.
        """
        return self.parent.parent.MultiPlotView_DTVList

    def getNumSignals(self, all_DTV=False):
        """Return total number of all selected signals.
        """
        return self.parent.parent.getNumSignals(all_DTV)
