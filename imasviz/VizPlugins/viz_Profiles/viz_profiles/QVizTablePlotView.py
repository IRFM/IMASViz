#  Name   : QVizTablePlotViewForPlugin
#
#          Provides pg.GraphicWindow that contains multiple plot panels in a
#          table layout.
#
#  Author :
#         Ludovic Fleury
#  E-mail :
#         ludovic.fleury@cea.fr
#
# *****************************************************************************
#     Copyright(c) 2022- L. Fleury
# *****************************************************************************

import pyqtgraph as pg
import logging
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QWidget, QScrollArea
from PyQt5.QtCore import Qt
from imasviz.Viz_API import Viz_API
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal import QVizPlotSignal
from imasviz.VizUtils import getRGBColorList, PlotTypes, getScreenGeometry
from .CustomizedViewBox import CustomizedViewBox
from pyqtgraph.graphicsItems.ViewBox import ViewBox
import numpy as np


class QVizTablePlotView(pg.GraphicsLayoutWidget):
    """TablePlotView pg.GraphicsWindow containing the plots in a table layout.
    """

    def __init__(self, viz_api, dataTreeView, n_curves, slices_aos_name):
        super(QVizTablePlotView, self).__init__()

        self.full_line = None
        self.nb_lines = 0
        self.nb_plots_per_line = 0
        self.last_node = ''
        self.okHeight = None
        self.okWidth = None
        self.dataTreeView = dataTreeView
        self.ncols = 4
        self.headers_count = 0
        self.imas_viz_api = viz_api
        self.figureKey = 0  # TODO

        self.slices_aos_name = slices_aos_name

        # # Get screen resolution (width and height)
        # self.screenWidth, self.screenHeight = getScreenGeometry()
        # # Set base dimension parameter for setting plot size
        self.plotVerticalDim = 290
        self.plotHorizontalDim = 270

        # # Set object name and title if not already set
        self.setObjectName("QVizPlugin")
        self.setWindowTitle(str(self.figureKey))

        # # Set number of rows and columns of panels in the TablePlotView frame
        # self.ncols = int(self.screenWidth * 0.7 / self.plotBaseDim)  # round down

        # # Add attribute describing the number of columns
        # # (same as self.centralWidget.rows is for number of rows. Initially
        # # the centralWidget does not contain the 'cols' attribute)
        self.centralWidget.cols = self.ncols

        self.setAntialiasing(True)
        self.setBackground((255, 255, 255))

        # Enable antialiasing for prettier plots
        pg.setConfigOptions(antialias=True)

        self.plotItems = []
        self.plotWidget = None

    def plot1D(self, plottable_signals, plotWidget, strategy):

        n = 0
        self.plotWidget = plotWidget
        dtv = self.dataTreeView
        self.nb_plots_per_line = 0

        for plottable_signal in plottable_signals:

            signalNode = plottable_signal[0]
            signal = plottable_signal[1]
            coordinate1_value = plottable_signal[2]

            if n == 0:
                self.last_node = signalNode.getParametrizedDataPath()

            # print("-->plotting node:" + signalNode.getPath())

            t = QVizPlotSignal.getXAxisValues(signal)

            # Get array of y-axis values
            v = QVizPlotSignal.get1DSignalValue(signal)

            # Set plot options
            label, xlabel, ylabel, title = \
                signalNode.plotOptions(dataTreeView=dtv,
                                       title=self.figureKey,
                                       plotWidget=self.plotWidget)
            # Add plot
            # y-axis values
            u = v[0]
            # x-axis values
            ti = t[0]
            if len(u) != len(ti):
                mess = 'x,y shapes are different, ignoring plot with label:' + label
                print(mess)
                logging.error(mess)
                continue

            currentPlotItem = self.plot(n=n, x=ti, y=u, label=label, xlabel=xlabel,
                                        ylabel=ylabel, node=signalNode, strategy=strategy)

            # Setting range manually (see IMAS-3658)
            try:
               currentPlotItem.setRange(xRange=(min(ti), max(ti)), yRange=(min(u), max(u)))
            except:
               pass
            if signalNode.is1D() and request.strategy == 'TIME':
                c1 = signalNode.evaluateCoordinateVsTime(coordinateNumber=1)
                label = pg.LabelItem('coordinate1(' + c1 + ")=" + str(round(coordinate1_value, 2)),
                                     size="6pt",
                                     color="FF0000")
                label.setParentItem(currentPlotItem)
                label.anchor(itemPos=(1, 0), parentPos=(1, 0), offset=(-30, 20))

            # Next plot number
            n += 1

        self.addEndLine()

    def addHeader(self, node):
        label = self.addLabel(colspan=self.ncols)
        import re
        phoneNumRegex = re.compile(r'\d\d\d-\d\d\d-\d\d\d\d')
        mo = phoneNumRegex.search('My number is 415-555-4242.')

        label.setText(node.getParametrizedDataPath(), bold=True, size='10pt')
        self.headers_count += 1
        self.nextRow()

    def addEndLine(self):
        self.nextRow()

        label = self.addLabel(colspan=4)
        label.setText('-------------------------------------------------------'
                      '-------------------------------------------------------'
                      '-------------------------------------------------------'
                      '-------------------------------------------------------', bold=True, size='10pt')

    def addViewBoxesForNextPlot(self, count):
        for i in range(count):
            self.addViewBox(colspan=1)

    def addViewBoxes(self):
        if self.nb_plots_per_line != 0:
            for i in range(self.ncols - self.nb_plots_per_line):
                self.addViewBox(colspan=1)

    def endOfPlotsProcessing(self):
        self.addViewBoxes()
        if not self.full_line:
            self.nb_lines += 1
        if self.nb_lines == 1:
            self.nextRow()
            self.nb_lines += 1
            for i in range(self.ncols):
                self.addViewBox(colspan=1)

    def plot(self, n, x, y, label, xlabel, ylabel, node=None, strategy=None):
        """Add new plot to TablePlotView pg.GraphicsWindow.

        Arguments:
            :param n      (int)      : Plot number.
            :param x      (1D array) : 1D array of X-axis values.
            :param y      (1D array) : 1D array of Y-axis values.
            :param label  (str)      : Plot label.
            :param xlabel (str)      : Plot X-axis label.
            :param ylabel (str)      : Plot Y-axis label.
            :param node:
            :param strategy:
        """
        # Set pen
        pen = self.setPen()
        viewBox = CustomizedViewBox(qWidgetParent=self, imas_viz_api=self.imas_viz_api)
        viewBox.id = n
        viewBox.addVizTreeNode(node)
        viewBox.strategy = strategy
        title = label.replace("\n", "")
        title = self.imas_viz_api.modifyTitle(title, None, self.slices_aos_name)

        if self.last_node != node.getParametrizedDataPath():
            self.addViewBoxes()
            self.addEndLine()
            if not self.full_line:
                self.nb_lines += 1
            self.nextRow()
            self.addHeader(node)
            self.nb_plots_per_line = 0
            self.last_node = node.getParametrizedDataPath()
        elif n == 0:
            self.addHeader(node)

        plotItem = self.addPlot(x=x,
                                y=y,
                                pen=pen,
                                title=title,
                                viewBox=viewBox)

        self.nb_plots_per_line += 1

        viewBox.addVizTreeNodeDataItems(node, plotItem.listDataItems())

        # Get titleLabel
        tLabel = plotItem.titleLabel

        # Set title label size
        # Note: empty text provided as requires text argument
        tLabel.setText(text=title, size='6pt')

        # Set title width
        # Note: required for alignment to take effect
        tLabel.item.setPlainText(title)

        # Set axis labels
        plotItem.setLabel('left', ylabel, units='')
        plotItem.setLabel('bottom', xlabel, units='')

        # Enable grid
        plotItem.showGrid(x=True, y=True)
        plotItem.dataItems[0].opts['name'] = title.replace("\n", "")
        viewBox.plotItem = plotItem

        if self.nb_plots_per_line % self.ncols == 0:
            self.nb_plots_per_line = 0
            self.full_line = True
            self.nb_lines += 1
            self.nextRow()
        else:
            self.full_line = False

        self.plotItems.append(plotItem)
        return plotItem

    def updatePlot(self, signals):

        # print("len(signals)=", len(signals))
        # print("len(self.plotItems)=", len(self.plotItems))

        for i in range(len(self.plotItems)):
            plottable_signal = signals[i]

            signalNode = plottable_signal[0]
            signal = plottable_signal[1]

            # print("-->updating node plot:" + signalNode.getPath())

            t = QVizPlotSignal.getXAxisValues(signal)
            ti = t[0]

            # Get array of y-axis values
            v = QVizPlotSignal.get1DSignalValue(signal)
            u = v[0]

            # dataItem = self.dataItems[i]
            plotItem = self.plotItems[i]
            dataItem = plotItem.listDataItems()[0]
            # print("u=", u)
            dataItem.setData(x=ti, y=u)

            # Setting range manually (see IMAS-3658)
            try:
               plotItem.setRange(xRange=(min(ti), max(ti)), yRange=(min(u), max(u)))
            except:
               pass
            i += 1

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

    def modifySize(self, n_plots):
        """Modify TablePlotView size.
        (depending on the number of plots and number of columns)
        """
        # Set suitable width and height
        self.okWidth = self.ncols * self.plotHorizontalDim + 220
        n_plots_lines = self.nb_lines
        # print("n_plots_lines=", n_plots_lines)
        # print("headers_count=", self.headers_count)
        self.okHeight = n_plots_lines * self.plotVerticalDim + 100 * self.headers_count
        self.setMinimumSize(self.okWidth, self.okHeight)
