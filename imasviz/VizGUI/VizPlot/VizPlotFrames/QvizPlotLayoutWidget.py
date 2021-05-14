#  Name   : QVizPlotLayoutWidget
#
#          Provides plot widget template.
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
import numpy as np
import logging
from PyQt5.QtCore import Qt, QMetaObject, QRect
from PyQt5.QtGui import QWidget, QGridLayout
import PyQt5.QtWidgets as QtWidgets
from imasviz.VizUtils import (QVizGlobalOperations, getRGBColorList,
                              GlobalFonts, PlotTypes)
from imasviz.VizGUI.VizPlot.QVizCustomPlotContextMenu \
    import QVizCustomPlotContextMenu


class QvizPlotLayoutWidget(QWidget):
    """QvizPlotLayoutWidget containing pyqtgraph GraphicsLayoutWidget.
    """

    def __init__(self, dataTreeView, rows, columns, parent=None, size=(500, 400), title='QvizPlotLayoutWidget'):
        super(QvizPlotLayoutWidget, self).__init__(parent)

        self.dataTreeView = dataTreeView

        # Set default background color: white
        pg.setConfigOption('background', 'w')
        # Set default foreground (text etc.) color: black
        pg.setConfigOption('foreground', 'k')

        # Enable antialiasing for prettier plots
        pg.setConfigOptions(antialias=True)

        # QVizPlotWidget settings
        self.setObjectName("QVizPlotLayoutWidget")
        self.setWindowTitle(title)
        self.resize(size[0], size[1])
        self.rows = rows
        self.columns = columns
        self.row = 0
        self.column = 0
        self.num_plots = 0
        # Set up the QWidget contents (pyqtgraph PlotWidget etc.)
        self.setContents()

    def setContents(self):
        """Setup QVizPlotWidget contents.
        """
        self.gridLayout = QGridLayout(self)
        self.gridLayout.setObjectName("gridLayout")

        # Set layout margin (left, top, right, bottom)
        #self.gridLayout.setContentsMargins(10, 10, 10, 10)

    def addPlot(self, data_features):
        if self.column == self.columns:
            self.column = 0
            self.row += 1
            if self.row == self.rows:
                self.row = 0
        self.addPlotAt(self.row, self.column, data_features)
        self.column += 1

    def addPlotAt(self, row, column, data_features):
        title =  data_features[7]
        x = data_features[2]
        y = data_features[3]
        label = data_features[4]
        xlabel = data_features[5]
        ylabel = data_features[6]
        pen, style = self.getPenAndStyle()
        pgPlotWidget = self.getPlotItem(row, column)
        if pgPlotWidget is None:
            pgPlotWidget = pg.PlotWidget(self, viewBox=QVizCustomPlotContextMenu(qWidgetParent=self))
            # Setting range manually (see IMAS-3658)
            pgPlotWidget.setRange(xRange=(min(x), max(x)), yRange=(min(y), max(y)))
            p = pgPlotWidget.plot(x, y, title=title, pen=pen, name=label)
            legend = pgPlotWidget.getPlotItem().addLegend(size=(5,1), offset=10)
            #legendLabelStyle = {'color': '#FFF', 'size': '8pt', 'bold': False, 'italic': False}
            legend.addItem(p, label)
        else:
            # Setting range manually (see IMAS-3658)
            pgPlotWidget.setRange(xRange=(min(x), max(x)), yRange=(min(y), max(y)))
            p = pgPlotWidget.plot(x, y, title=title, pen=pen, name=label)

        pgPlotWidget.setLabel('left', ylabel, units='')
        # - Set y-axis label
        pgPlotWidget.setLabel('bottom', xlabel, units='')
        # - Enable grid
        pgPlotWidget.showGrid(x=True, y=True)
        self.gridLayout.addWidget(pgPlotWidget, row, column)
        # Number of already present plots
        self.num_plots += 1


    def getPenAndStyle(self):
        RGBlist = getRGBColorList()

        # Number of available colors
        num_avail_colors = len(RGBlist)

        # Set color loop counter (for cases where there are more plots
        # than available plot color+style variations)
        color_loop_counter = int(self.num_plots / num_avail_colors)
        # Set next RGB ID
        next_RGB_ID = self.num_plots - color_loop_counter * num_avail_colors
        # Set pen style
        if color_loop_counter % 2 == 0:
            style = Qt.SolidLine
        else:
            style = Qt.DotLine

        # Set pen
        # Note: width higher than '1' considerably decreases performance
        pen = pg.mkPen(color=RGBlist[next_RGB_ID], width=1, style=style)
        return pen, style

    def getPlotItem(self, row, col):
        item = self.gridLayout.itemAtPosition(row, col)
        if item is not None:
            return item.widget()
        return None
