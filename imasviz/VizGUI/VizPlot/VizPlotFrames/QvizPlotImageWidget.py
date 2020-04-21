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
from PyQt5.QtCore import Qt, QMetaObject, QRectF
from PyQt5.QtGui import QWidget, QGridLayout, QHBoxLayout, QColor
import PyQt5.QtWidgets as QtWidgets
from imasviz.VizUtils import (QVizGlobalOperations, getRGBColorList,
                              GlobalFonts, PlotTypes)
from functools import partial


class QvizPlotImageWidget(QWidget):
    """QvizPlotImageWidget containing pyqtgraph ImageView.
    """

    def __init__(self, dataTreeView, rows=1, columns=1, plotSlideFromROI=False,
                 parent=None, size=(400, 200), title='QvizPlotImageWidget'):
        super(QvizPlotImageWidget, self).__init__(parent)

        self.dataTreeView = dataTreeView

        # Set default background color: white
        pg.setConfigOption('background', 'w')
        # Set default foreground (text etc.) color: black
        pg.setConfigOption('foreground', 'k')

        # Enable antialiasing for prettier plots
        pg.setConfigOptions(antialias=True)

        # QVizPlotWidget settings
        self.setObjectName("QvizPlotImageWidget")
        self.setWindowTitle(title)
        self.resize(size[0], size[1])
        self.rows = rows
        self.columns = columns
        self.row = 0
        self.column = 0
        self.num_plots = 0
        self.plotSlideFromROI = plotSlideFromROI
        # Set up the QWidget contents (pyqtgraph PlotWidget etc.)
        self.setContents()

    def setContents(self):
        """Setup QVizPlotWidget contents.
        """
        self.gridLayout = QGridLayout(self)
        self.gridLayout.setObjectName("gridLayout")

    def addPlot(self, data_features):
        if self.column == self.columns:
            self.column = 0
            self.row += 1
            if self.row == self.rows:
                self.row = 0

        self.addPlotAt(self.row, self.column, data_features)
        self.column += 1

    def addPlotAt(self, row, column, dataArrayHandle):
        data = dataArrayHandle.arrayValues
        coordinate_of_time = dataArrayHandle.getTimeCoordinateDim()
        time_array = dataArrayHandle.getTimeCoordinateArray() #can be None
        #print(len(time_array))
        #print(np.shape(y))
        imageItem = pg.ImageItem(data)
        pgw = pg.GraphicsLayoutWidget(parent=self)
        plotItem = None

        if coordinate_of_time is None:
            plotItem = pgw.addPlot(0,0)
        else:
            orientation = 'left' #if coordinate_of_time == 2
            if coordinate_of_time == 1:
                orientation = 'bottom'
            time_axis = TimeAxisItem(time_array, orientation=orientation)
            plotItem = pgw.addPlot(row=0,col=0, axisItems={orientation:time_axis})

        plotItem.addItem(imageItem)
        self.manageTimeAxis(dataArrayHandle, coordinate_of_time=coordinate_of_time, plotItem=plotItem)

        histo = pg.HistogramLUTItem(image=imageItem)
        pgw.addItem(histo, 0, 1)
        if self.plotSlideFromROI:
            roi = self.addROI(pgw, plotItem, data, imageItem=imageItem)
        self.gridLayout.addWidget(pgw, row, column)

        # Number of current plots
        self.num_plots += 1

    def addROI(self, pgw, plotItem, data, imageItem):
        self.slice_plotItem = pgw.addPlot(1, 0, 1, 2)
        roi = pg.RectROI(maxBounds=QRectF(0, 0, len(data[:,0]), len(data[0,:])), pos=(0,0), size=(len(data[:,0]), 70),
                         pen=pg.mkPen(pg.mkColor(255,0,0)), scaleSnap=True, snapSize=5)
        plotItem.getViewBox().addItem(roi)
        roi.sigRegionChanged.connect(partial(self.roiChanged, roi, data, imageItem))
        return roi


    def roiChanged(self, roi, data, imageItem):
        self.slice_plotItem.clear()
        slice = roi.getArrayRegion(data, imageItem)
        self.slice_plotItem.plot(x=np.asarray(range(0, len(data[:,0]))), y=slice[:,0])
        #print(np.shape(roi.getArrayRegion(data, img)))

    def manageTimeAxis(self, dataArrayHandle, coordinate_of_time, plotItem):

        if coordinate_of_time is None:
            labels = dataArrayHandle.getCoordinateLabels(1)
            plotItem.setLabel('bottom', labels[1])
            labels = dataArrayHandle.getCoordinateLabels(2)
            plotItem.setLabel('left', labels[1])
            return

        if coordinate_of_time == 2:
            plotItem.setLabel('left', 'Time[s]')
            labels = dataArrayHandle.getCoordinateLabels(1)
            plotItem.setLabel('bottom', labels[1])

        elif coordinate_of_time == 1:
            plotItem.setLabel('bottom', 'Time[s]')
            #axisItem = plotItem.getAxis('bottom')
            labels = dataArrayHandle.getCoordinateLabels(2)
            plotItem.setLabel('left', labels[1])


    def getPlotItem(self, row, col):
        item = self.gridLayout.itemAtPosition(row, col)
        if item is not None:
            return item.widget()
        return None


class TimeAxisItem(pg.AxisItem):
    def __init__(self, time_array, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.time_array = time_array

    def tickStrings(self, values, scale, spacing):
        t0 = self.time_array[0]
        tend = self.time_array[-1]
        maxVal = 0
        if values is not None and len(values) > 0:
            maxVal = int(values[-1])
        if maxVal == 0:
            return [str(round(t0, 2)) for value in values]
        return [str(round(t0 + (int(value)/maxVal)*(tend-t0), 2)) for value in values]

