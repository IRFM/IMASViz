# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

import pyqtgraph as pg
import numpy as np
import logging
import itertools
from PySide6.QtCore import Qt, QMetaObject, QRectF
from PySide6.QtWidgets import QWidget, QGridLayout, QHBoxLayout
from PySide6.QtGui import QColor
import PySide6.QtWidgets as QtWidgets
from imasviz.VizUtils import (QVizGlobalOperations, getRGBColorList,
                              GlobalFonts, PlotTypes)
from imasviz.VizGUI.VizPlot.QVizCustomPlotContextMenu \
    import QVizCustomPlotContextMenu
from imasviz.VizGUI.VizPlot.QVizImageCustomPlotContextMenu \
    import QVizImageCustomPlotContextMenu
from functools import partial


class QvizPlotImageWidget(QWidget):
    """QvizPlotImageWidget containing pyqtgraph ImageView.
    """

    def __init__(self, vizTreeNode, plotSliceFromROI=False,
                 parent=None, size=(400, 200), title='QvizPlotImageWidget', showImageTitle=True):
        super(QvizPlotImageWidget, self).__init__(parent)

        self.vizTreeNode = vizTreeNode

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

        self.plotSliceFromROI = plotSliceFromROI
        self.showImageTitle = showImageTitle

        self.plotImageItem = None
        self.slicesXPlotItem = None
        self.slicesYPlotItem = None

        # Set up the QWidget contents (pyqtgraph PlotWidget etc.)
        self.setContents()
        self.dataArrayHandle = None

    """
    Return axis orientation according to the column_major value.
    """

    def getAxisOrientations(self):
        return 1, 2

    """
    Setup QvizPlotImageWidget contents.
    """

    def setContents(self):

        self.gridLayout = QGridLayout(self)
        self.gridLayout.setObjectName("gridLayout")

    def plot(self, dataArrayHandle):
        self.dataArrayHandle = dataArrayHandle
        data = self.dataArrayHandle.arrayValues  # 2D data array
        self.coordinate_of_time = self.dataArrayHandle.getTimeCoordinateDim()  # 1 or 2

        if self.coordinate_of_time == 1:
            data = np.transpose(data)

        time_array = self.dataArrayHandle.getTimeCoordinateArray()  # can be None
        imageItem = pg.ImageItem(data)

        # The pgw component is a layout wich contains:
        #  a plotImageItem (PlotItem type) at 0,0 associated to an ImageItem (the image)
        #  an histogram ( HistogramLUTItem object ) at 0, 2
        #  a optional second PlotItem at 1, 0 containing all slices kept by the user with the current selected slice
        self.pgw = pg.GraphicsLayoutWidget(parent=self)
        firstLayout = self.pgw.addLayout(row=0, col=0)

        # Creation of the plotImageItem
        viewBox = QVizCustomPlotContextMenu(qWidgetParent=self)
        viewBox.displayMenu1D = False
        viewBox.setRange(xRange=(0, len(data[:, 0])))
        viewBox.setLimits(xMin=0, xMax=len(data[:, 0]), yMin=0, yMax=len(data[0, :]))
        if self.vizTreeNode is not None:
            viewBox.addVizTreeNode(self.vizTreeNode)

        self.plotImageItem = firstLayout.addPlot(row=0, col=0, rowSpan=1, colSpan=2, viewBox=viewBox)
        self.plotImageItem.addItem(imageItem)

        if self.showImageTitle:
            self.plotImageItem.setTitle(self.dataArrayHandle.getLabel(), size='8')

        # Creation of the histogram
        histogram = pg.HistogramLUTItem(image=imageItem)
        # Adding the histogram to the pgw layout
        firstLayout.addItem(histogram, row=0, col=2)

        self.setupImageAxes()

        if self.plotSliceFromROI:  # slice plot item is displayed (option)
            self.slicesXPlotItem = SlicesPlotItem(self, axis=1,
                                                  imageItem=imageItem, plotImageItem=self.plotImageItem)
            self.slicesYPlotItem = SlicesPlotItem(self, axis=2,
                                                  imageItem=imageItem, plotImageItem=self.plotImageItem, transpose=True)

        # Add the pgw component to the main layout
        self.gridLayout.addWidget(self.pgw, 0, 0)

    """
    Setup the axis of the image plot item
    """

    def setupImageAxes(self):

        i, j = self.getAxisOrientations()
        firstLayout = self.pgw.getItem(row=0, col=0)
        plotItem = firstLayout.getItem(row=0, col=0)

        if self.coordinate_of_time is None:
            plotItem.setLabel('bottom', self.dataArrayHandle.getCoordinateLabel(i))
            plotItem.setLabel('left', self.dataArrayHandle.getCoordinateLabel(j))
            return

        plotItem.setLabel('left', 'Time[s]')
        if self.coordinate_of_time == j:
            plotItem.setLabel('bottom', self.dataArrayHandle.getCoordinateLabel(i))

        elif self.coordinate_of_time == i:
            plotItem.setLabel('bottom', self.dataArrayHandle.getCoordinateLabel(j))

    """
    Utility function to set a plot color and a plot style
    """

    def getPenAndStyle(self, num_plots):
        RGBlist = getRGBColorList()

        # Number of available colors
        num_avail_colors = len(RGBlist)

        # Set color loop counter (for cases where there are more plots
        # than available plot color+style variations)
        color_loop_counter = int(num_plots / num_avail_colors)
        # Set next RGB ID
        next_RGB_ID = num_plots - color_loop_counter * num_avail_colors
        # Set pen style
        if color_loop_counter % 2 == 0:
            style = Qt.SolidLine
        else:
            style = Qt.DotLine

        # Set pen
        pen = pg.mkPen(color=RGBlist[next_RGB_ID], width=1, style=style)
        return pen, style

    def getTime(self, value):
        if self.coordinate_of_time is None:
            raise ValueError('Can not compute time value; no axis depend on time.')
        data = self.dataArrayHandle.arrayValues
        if self.coordinate_of_time == 2:
            maxVal = len(data[0, :])  # deltaY, length of array in the vertical slice direction
        else:
            maxVal = len(data[:, 0])  # deltaX, length of array in the horizontal slice direction
        time_array = self.dataArrayHandle.getTimeCoordinateArray()
        t0 = time_array[0]
        tend = time_array[-1]
        if value == 0:
            return round(t0, 2)
        else:
            return round(t0 + value / maxVal * (tend - t0), 2)


class SlicesPlotItem:
    def __init__(self, parent, axis, imageItem, plotImageItem, transpose=False):
        self.parent = parent
        self.axis = axis
        self.transpose = transpose
        self.roi = None  # the ROI selecting the slice
        self.slice = None  # the current selected slice
        self.slice_plot = None  # the slice plot
        roi = self.addSegmentROI(plotImageItem)  # add a ROI to the image
        # Creation of the slice plot item at 1, 0 of the pgw layout
        viewBox = self.createViewBox()
        if parent.vizTreeNode is not None:
            viewBox.addVizTreeNode(parent.vizTreeNode)
        self.slice_plotItem = parent.pgw.addPlot(row=self.axis, col=0, rowSpan=1, colSpan=2, viewBox=viewBox)
        self.slice_plotItem.addLegend()
        self.setupSliceImageAxes()  # setup plot axis
        self.eventsData = {}
        self.eventsData['roi'] = roi
        self.eventsData['imageItem'] = imageItem
        roi.sigPositionChangeFinished.connect(self.roiChanged)
        self.roiChanged()
        self.roi = roi  # the ROI selecting the slice
        self.vline = self.createInfLine()
        self.slice_plotItem.addItem(self.vline)

    def createViewBox(self):
        viewBox = QVizImageCustomPlotContextMenu(qWidgetParent=self.parent, axis=self.axis)
        return viewBox

    def createInfLine(self):
        bounds = None
        data = self.parent.dataArrayHandle.arrayValues
        if self.axis == 1:
            bounds = (0, len(data[:, 0]))
        else:
            bounds = (0, len(data[0, :]))
        vline = pg.InfiniteLine(bounds=bounds, angle=90, movable=True)
        label = QVizInfLineLabel(roi_label=False, line=vline, spi=self, text='{value}')
        vline.setZValue(1)  # ensure vline is above plot elements
        return vline

    def addNewMarker(self):
        marker = self.createInfLine()
        self.slice_plotItem.addItem(marker)

    """
    Setup the axis of the slice plot item
    """

    def setupSliceImageAxes(self):
        ct = self.parent.coordinate_of_time
        self.slice_plotItem.setLabel('left', self.parent.dataArrayHandle.getName())
        if ct == self.axis:
            self.slice_plotItem.setLabel('bottom', 'Time[s]')
        else:
            self.slice_plotItem.setLabel('bottom', self.parent.dataArrayHandle.getCoordinateLabel(self.axis))

    """
    Add a ROI to the image
    """

    def addSegmentROI(self, plotImageItem):
        data = self.parent.dataArrayHandle.arrayValues
        angle = None
        if self.transpose:
            angle = 90
            dy = len(data[:, 0])
            bounds = (0, dy)
            pos = 20. / 100. * dy  # default position at 20% of the max value
        else:
            angle = 0
            dx = len(data[0, :])
            bounds = (0, dx)
            pos = 20. / 100. * dx  # default position at 20% of the max value
        roi = pg.InfiniteLine(pos=pos, bounds=bounds, angle=angle, movable=True)
        label = QVizInfLineLabel(roi_label=True, line=roi, spi=self, text='{value}')
        roi.setZValue(1)  # ensure vline is above plot elements
        plotImageItem.getViewBox().addItem(roi)
        return roi

    """
    Create/update the plot of the current selected slice when the roi change
    """

    def roiChanged(self):

        roi = self.eventsData['roi']
        imageItem = self.eventsData['imageItem']
        data = self.parent.dataArrayHandle.arrayValues

        if self.transpose:
            self.slice = data[int(roi.value()), :]
        else:
            self.slice = data[:, int(roi.value())]

        # We create/update the plot of the current selected slice
        if self.slice is not None and self.slice.ndim == 1:
            if self.slice_plot is None:
                self.slice_plotItem.clear()
                self.slice_plot = self.slice_plotItem.plot(x=np.asarray(range(0,
                                                                              len(self.slice))), y=self.slice,
                                                           name='selected slice')
            else:
                self.slice_plot.setData(x=np.asarray(range(0, len(self.slice))), y=self.slice)
        self.slice_plot.setPen(pg.mkPen(width=1, color='k'))
        self.displaySliceInfo()

    def displaySliceInfo(self):
        sliceInfo = self.getSliceInfo(displayCoordinatesOnly=True)
        if sliceInfo is not None:
            current_selection = self.slice_plotItem.listDataItems()[0]
            newLabelName = current_selection.name() + ' (' + sliceInfo + ')'
            t = self.slice_plotItem.legend.items[0]
            labelItem = t[1]
            labelItem.setText(newLabelName)

    def getSliceInfo(self, displayCoordinatesOnly=False):

        if self.roi is None:
            return None

        sliceInfo = None

        if self.slice is None or (self.slice is not None and self.slice.ndim == 1):

            label = {1: 'y=', 2: 'x='}

            time_label = ''
            if self.parent.coordinate_of_time is not None:
                if self.parent.coordinate_of_time != self.axis:
                    time = self.parent.getTime(self.roi.value())
                    time_label = ", time=" + str(time)

            sliceInfo = label[self.axis] + str(round(self.roi.value(), 2)) + time_label
            if not displayCoordinatesOnly:
                sliceInfo = 'slice at: ' + sliceInfo

        return sliceInfo

    """
    Keep the current selected slice
    """

    def keepSlice(self):
        if self.slice is not None and self.slice.ndim == 1:
            pen, style = self.parent.getPenAndStyle(len(self.slice_plotItem.listDataItems()))
            plotName = self.getSliceInfo()
            pdItem = self.slice_plotItem.plot(x=np.asarray(range(0, len(self.slice))),
                                              y=self.slice, pen=pen, style=style, name=plotName)  # create plotDataItem

    """
    Delete all slices from the slice_plotItem
    """

    def removeAllSlices(self):
        for item in self.slice_plotItem.listDataItems()[1:]:
            self.slice_plotItem.removeItem(item)
        self.slice_plotItem.getViewBox().scene().removeItem(self.slice_plotItem.legend)
        current_selection = self.slice_plotItem.listDataItems()[0]
        self.slice_plotItem.addLegend()
        self.slice_plotItem.legend.addItem(current_selection, current_selection.name())

    def plotToNewFigure(self):
        # c.getData() returns a tuple of 2 arrays (x,y)
        data = [c.getData() for c in self.slice_plotItem.listDataItems()]
        labels = [c.name() for c in self.slice_plotItem.listDataItems()]
        signals = []
        for d in data:
            signals.append((np.array([d[0]]), np.array([d[1]])))
        treeNode = self.parent.vizTreeNode
        labelText = self.slice_plotItem.getAxis('bottom').labelText
        treeNode.dataTreeView.imas_viz_api.plot1DInNewFigure(x_label=labelText,
                                                             signals_labels=labels,
                                                             signals=signals,
                                                             treeNode=treeNode)


class QVizInfLineLabel(pg.InfLineLabel):

    def __init__(self, roi_label, line, spi, text, *args, **kwargs):
        self.spi = spi
        self.roi_label = roi_label
        super().__init__(line, text=text, *args, **kwargs)

    def valueChanged(self):
        piw = self.spi.parent
        value = self.line.value()
        label = None
        displayTime = False

        if piw.coordinate_of_time is not None:
            if self.roi_label and self.line.angle < 80:
                displayTime = True
            elif not self.roi_label and self.spi.axis == 2:
                displayTime = True

        if self.roi_label:
            if self.line.angle > 80:
                label = 'x='
            else:
                label = 'y='
        else:
            if self.line.angle > 80 and self.spi.axis == 1:
                label = 'x='
            elif self.line.angle > 80 and self.spi.axis == 2:
                label = 'y='
            elif self.line.angle < 80 and self.spi.axis == 1:
                label = 'data='
            elif self.line.angle < 80 and self.spi.axis == 2:
                label = 'data='

        axisInfo = label + str(round(value, 2))
        time_label = ''

        if displayTime:
            time = piw.getTime(value)
            time_label = ", time=" + str(time)
            axisInfo = axisInfo + time_label

        self.setText(self.format.format(value=axisInfo))
        self.updatePosition()
