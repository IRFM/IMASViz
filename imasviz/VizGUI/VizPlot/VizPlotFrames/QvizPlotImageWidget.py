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

    def __init__(self, dataTreeView, rows=1, columns=1, plotSliceFromROI=False,
                 parent=None, size=(400, 200), title='QvizPlotImageWidget', showImageTitle=True):
        super(QvizPlotImageWidget, self).__init__(parent)

        self.dataTreeView = dataTreeView
        self.column_major = True

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
        self.plotSliceFromROI = plotSliceFromROI
        self.showImageTitle = showImageTitle
        self.slice_plot = None
        # Set up the QWidget contents (pyqtgraph PlotWidget etc.)
        self.setContents()

    def setContents(self):
        """Setup QVizPlotWidget contents.
        """
        self.gridLayout = QGridLayout(self)
        self.gridLayout.setObjectName("gridLayout")

    def getAxisOrientations(self):
        i = None
        j = None
        if self.column_major:
            i = 2
            j = 1
        else:
            i = 1
            j = 2
        return i, j

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
            plotItem = pgw.addPlot(0,0,1,2)
        else:
            i, j = self.getAxisOrientations()
            if coordinate_of_time == i:
                orientation = 'left' #if coordinate_of_time == 2
            elif coordinate_of_time == j:
                orientation = 'bottom'
            time_axis = TimeAxisItem(time_array, orientation=orientation)
            plotItem = pgw.addPlot(row=0,col=0, rowSpan=1, colSpan=2, axisItems={orientation:time_axis})

        plotItem.addItem(imageItem)
        if self.showImageTitle:
            plotItem.setTitle(dataArrayHandle.getLabel(), size='8')
        self.manageImageAxes(dataArrayHandle, coordinate_of_time=coordinate_of_time, plotItem=plotItem)

        histo = pg.HistogramLUTItem(image=imageItem)
        pgw.addItem(histo, 0, 2)

        if self.plotSliceFromROI:
            slice_plotItem = pgw.addPlot(1, 0, 1, 3)
            self.manageSliceImageAxes(dataArrayHandle, slice_plotItem, coordinate_of_time)
            roi = self.addSegmentROI(pgw, plotItem, data)
            roi.sigRegionChanged.connect(partial(self.roiChanged, roi, data, imageItem, slice_plotItem))
            self.roiChanged(roi, data, imageItem, slice_plotItem)

        self.gridLayout.addWidget(pgw, row, column)

        # Number of current plots
        self.num_plots += 1

    def addSegmentROI(self, pgw, plotItem, data):
        positions = []
        positions.append((0, len(data[0, :]) / 2))
        positions.append((len(data[:, 0]), len(data[0, :]) / 2))
        maxBounds = QRectF(0, -len(data[0, :])/2, 0, len(data[0, :]))
        roi = pg.LineSegmentROI(positions=positions, maxBounds=maxBounds,
                                pos=(0, 0), scaleSnap=True, snapSize=5)
        plotItem.getViewBox().addItem(roi)
        roi.setPen(pg.mkPen(width=5, color='r'))
        return roi

    def roiChanged(self, roi, data, imageItem, slice_plotItem):
        for handle in roi.getHandles():
            handle.hide()
        slice = None
        try:
            slice = roi.getArrayRegion(data, imageItem)
        except:
            pass
        #print(np.shape(roi.getArrayRegion(data, imageItem)))
        if slice is not None and slice.ndim == 1:
            if self.slice_plot is None:
                slice_plotItem.clear()
                self.slice_plot = slice_plotItem.plot(x=np.asarray(range(0, len(slice))), y=slice)
            else:
                self.slice_plot.setData(x=np.asarray(range(0, len(slice))), y=slice)

    def updateSlicePlot(self, roi, data, imageItem):
        slice = None
        try:
            slice = roi.getArrayRegion(data, imageItem)
        except:
            pass
        # print(np.shape(roi.getArrayRegion(data, imageItem)))
        if slice is not None and slice.ndim == 1:
            if self.slice_plot is None:
                slice_plotItem.clear()
                self.slice_plot = slice_plotItem.plot(x=np.asarray(range(0, len(slice))), y=slice)
            else:
                self.slice_plot.setData(x=np.asarray(range(0, len(slice))), y=slice)

    def manageImageAxes(self, dataArrayHandle, coordinate_of_time, plotItem):
        i, j = self.getAxisOrientations()
        if coordinate_of_time is None:
            plotItem.setLabel('bottom', dataArrayHandle.getCoordinateLabel(j))
            plotItem.setLabel('left', dataArrayHandle.getCoordinateLabel(i))
            return

        if coordinate_of_time == i:
            plotItem.setLabel('left', 'Time[s]')
            plotItem.setLabel('bottom', dataArrayHandle.getCoordinateLabel(j))

        elif coordinate_of_time == j:
            plotItem.setLabel('bottom', 'Time[s]')
            plotItem.setLabel('left', dataArrayHandle.getCoordinateLabel(i))

    def manageSliceImageAxes(self, dataArrayHandle, plotItem, coordinate_of_time):
        i, j = self.getAxisOrientations()
        plotItem.setLabel('left', dataArrayHandle.getName())
        if coordinate_of_time == i:
            plotItem.setLabel('bottom', dataArrayHandle.getCoordinateLabel(j))
        elif coordinate_of_time == j:
            plotItem.setLabel('bottom', 'Time[s]')
        else:
            plotItem.setLabel('bottom', dataArrayHandle.getCoordinateLabel(j))

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

