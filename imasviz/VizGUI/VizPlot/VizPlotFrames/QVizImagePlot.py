# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""An image figure that says which slice of a quantity it drew.

A curve draws one axis, an image two -- so an image pins more, and a picture that
does not say where it pinned them shows one unnamed slice of a quantity. The loop
is the curve figure's, unchanged: the read answers what it draws and what it
fixes, the controls come out of that same answer, and moving one reads again
through it.

One of the axes the image leaves out is read across the pictures instead of under
a slider. Three elements of the dynamic array side by side is the only way to
compare them, and a leaf with more axes than a picture draws had no frame at all
until one of those axes moved from inside the picture to between pictures. That
axis is on screen, so it gets no slider: it gets a window, saying which of its
elements are up and letting the user move on.

The pictures all answer to one colour scale, fixed when the quantity is plotted.
Comparing two of them means comparing colours, and a scale that re-fit itself to
each picture would make every picture look the same whatever it held.

The cells of the image are element ranks, laid over the coordinate extents: a
dictionary grid need not be regular, and pyqtgraph draws an image as a regular
grid. What is exact is the extent, the labels and the slice the colours stand for.
"""

import numpy as np
import pyqtgraph as pg

from PySide6.QtWidgets import QVBoxLayout, QWidget

from imasviz.VizDataAccess.QVizTensorDataAccess import FRAMES, QVizTensorDataAccess
from imasviz.VizEntities.QVizDataArrayHandle import QVizDataArrayHandle
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizSliceControls import (
    QVizFramesWindow, QVizSliceControls)


class QVizImagePlot(QWidget):
    """The pictures of one quantity, with a control per axis outside them."""

    # The data access and the node's label code ask a plot frame these three.
    # This path drives nothing from them -- the slice controls carry the indices
    # -- but they are asked, so they are answered without the slider machinery
    # the names imply.
    addTimeSlider = False
    addCoordinateSlider = False
    sliderGroup = None

    def __init__(self, parent=None, title=''):
        super().__init__(parent)

        self.plotAxis = 'DEFAULT'
        self._treeNode = None
        # The axis read between the pictures, and where the window sits on it.
        self._frames = None
        self._count = 0
        self._levels = None
        # Which axis of the read lies horizontal, decided when the pictures are
        # drawn and reused by every slice after them.
        self._xAxis, self._yAxis = 1, 2
        # One entry per picture, in screen order: the plot it lives in and the
        # image drawn in it.
        self._pictures = []

        self.pgPlotWidget = pg.GraphicsLayoutWidget(self)
        self.pgPlotWidget.setObjectName('imagePlot')
        # The first picture's plot: the node's label code and the context menus
        # ask a frame for one plot item, and which picture they mean is the
        # first one.
        self.plotItem = None
        self.colorBar = None

        self.sliceControls = QVizSliceControls(self)
        self.framesControls = QVizFramesWindow(self)
        # The read calls these attributes by name, so the controls and the
        # pictures cannot be out of date with respect to each other.
        self.sliceControls.changed.connect(self.refresh)
        self.framesControls.moved.connect(self.refresh)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.pgPlotWidget)
        layout.addWidget(self.framesControls)
        layout.addWidget(self.sliceControls)

        if title:
            self.setWindowTitle(title)

    def getPlotAxis(self):
        return self.plotAxis

    def setPlotAxis(self, plotAxis):
        self.plotAxis = plotAxis

    def plot(self, treeNode):
        """Draw one quantity: pictures along one axis, a control per axis left.

        Returns the number of images on the figure.
        """
        if self._pictures:
            raise ValueError('This figure already holds the images of "' +
                             self.dataPathOf(self._treeNode) + '": one quantity '
                             'per figure, because a second one would need its own '
                             'colour scale and its own controls.')

        access = self.accessFor(treeNode)
        self._treeNode = treeNode
        # An image never runs along time: it draws two axes of the quantity, and
        # the dynamic array joins the axes it leaves out.
        axesSpec, _, _, plotted = access.plan(treeNode, self,
                                              as_function_of_time=False)
        self._frames = access.framesFor(treeNode, self, as_function_of_time=False)
        drawn = [position for position in plotted
                 if self._frames is None or position != self._frames.position]
        path = self.dataPathOf(treeNode)

        if len(drawn) < 2:
            raise ValueError('"' + path + '" has one axis to draw: it belongs on a '
                             'curve figure, where its fixed axes get controls too.')
        if len(drawn) > 2:
            raise ValueError('"' + path + '" has ' + str(len(drawn)) +
                             ' axes to draw: no picture shows more than two, and '
                             'the axis read between pictures is taken.')

        # Nothing spread means one picture, not a window of them: the count is
        # the number of images the figure holds, and a figure with no axis between
        # its pictures holds one.
        if self._frames is None:
            self._count = 1
        elif self._frames.length is None:
            self._count = FRAMES
        else:
            self._count = max(min(FRAMES, int(self._frames.length)), 1)
        self._setScreenAxes(axesSpec, drawn)
        # The window is posed before anything is read: the first pictures are
        # taken at the element the tree carries, clamped to where a window of
        # this many can sit, and the control has to show that same number.
        self.framesControls.setWindow(self._frames, self._count)

        frames = self._read()
        if not any(np.asarray(handle.arrayValues).size for handle, _, _ in frames):
            raise ValueError('Nothing to plot for "' + path +
                             '": no values in the image.')

        quantity = self.quantityLabel(treeNode)
        for position, (handle, _, frameLabel) in enumerate(frames):
            self._addPicture(position)
            self._drawPicture(position, handle, axesSpec, drawn)
            title = quantity + (' — ' + frameLabel if frameLabel else '')
            self._pictures[position][0].setTitle(title)

        self.plotItem = self._pictures[0][0]
        # Where the colour scale settles: over every picture on the figure, once.
        self._levels = self._scaleOf([np.asarray(handle.arrayValues)
                                      for handle, _, _ in frames])
        self.colorBar = pg.ColorBarItem(label=quantity, interactive=False)
        self.pgPlotWidget.addItem(self.colorBar, row=0, col=self._count)
        # One bar cannot drive several images -- pyqtgraph 0.13.7 keeps only the
        # last item handed to setImageItem -- so it displays the scale and the
        # scale is applied to each picture by hand.
        self.colorBar.setImageItem(self.images()[0])
        self._applyScale()

        self.addSlices(access.slicesFor(treeNode, plotWidget=self,
                                        as_function_of_time=False,
                                        frames=None if self._frames is None
                                        else self._frames.position))
        return self._count

    def refresh(self):
        """Re-read the window the controls picked, updating the pictures in place.

        Not a re-plot: rebuilding the controls would rebuild the handle the user
        is still holding and reset the colour scale under their hand.
        """
        if not self._pictures:
            return None

        axesSpec, _, _, plotted = self.accessFor(self._treeNode).plan(
            self._treeNode, self, as_function_of_time=False)
        drawn = [position for position in plotted
                 if self._frames is None or position != self._frames.position]

        for position, (handle, _, _) in enumerate(self._read()):
            if position >= len(self._pictures):
                break
            self._drawPicture(position, handle, axesSpec, drawn)
        return self.sliceControls.indices()

    def imageCount(self):
        return len(self._pictures)

    def isDrawing(self):
        return bool(self._pictures)

    def images(self):
        return [image for _, image in self._pictures]

    def plotItems(self):
        return [plot for plot, _ in self._pictures]

    def colourLevels(self):
        return self._levels

    def sliceKeys(self):
        return self.sliceControls.keys()

    def framesKey(self):
        return None if self._frames is None else self._frames.key

    def addSlices(self, slices):
        self.sliceControls.setSlices(slices)

    def _read(self):
        """The window of pictures, as the controls have them now."""
        access = self.accessFor(self._treeNode)
        if self._frames is None:
            return [(access.GetSignal(treeNode=self._treeNode, plotWidget=self,
                                      as_function_of_time=False), 0, '')]
        return access.GetFrames(self._treeNode, plotWidget=self,
                                start=self.framesControls.start(),
                                count=self._count)

    def _addPicture(self, position):
        plotItem = self.pgPlotWidget.addPlot(row=0, col=position)
        imageItem = pg.ImageItem()
        plotItem.addItem(imageItem)
        self._pictures.append((plotItem, imageItem))

    def _drawPicture(self, position, handle, axesSpec, drawn):
        """Lay one read into one picture: values, extent, axis labels."""
        plotItem, imageItem = self._pictures[position]
        values = np.asarray(handle.arrayValues) \
            if isinstance(handle, QVizDataArrayHandle) else np.asarray([])

        if values.size == 0:
            # A slice holding nothing shows nothing. Leaving the previous picture
            # up answers a question the user never asked.
            imageItem.clear()
            return

        imageItem.setImage(self._forScreen(values))
        if self._levels is not None:
            imageItem.setLevels(self._levels)
        # A different element of a static array can carry a grid of its own, so
        # the extent belongs to the slice just read, not to the first one.
        self._setExtent(imageItem, handle)
        self._setAxisLabels(plotItem, axesSpec, drawn)

    def _scaleOf(self, valuesList):
        """The span every picture on the figure is drawn against."""
        spans = [(float(np.min(values)), float(np.max(values)))
                 for values in valuesList if values.size]
        if not spans:
            return None
        return (min(low for low, _ in spans), max(high for _, high in spans))

    def _applyScale(self):
        for image in self.images():
            if self._levels is not None:
                image.setLevels(self._levels)

    def _setExtent(self, imageItem, handle):
        """Span the picture over the coordinates it was taken on.

        Without this an axis labelled in metres carries element ranks under it.
        A coordinate the dictionary names but this case leaves empty leaves the
        image on its ranks, which is what the numbers actually are then.
        """
        extents = []
        for dim in (self._xAxis, self._yAxis):
            try:
                values = np.asarray(handle.getCoordinateValues(dim), dtype=float)
            except (TypeError, ValueError):
                values = np.asarray([])
            if values.size == 0:
                return
            low, high = float(np.min(values)), float(np.max(values))
            if high == low:
                return
            extents.append((low, high))

        (x0, x1), (y0, y1) = extents
        imageItem.setRect(x0, y0, x1 - x0, y1 - y0)

    def _setAxisLabels(self, plotItem, axesSpec, drawn):
        """Label both image axes from the axes the read actually drew.

        The read shapes its values in dictionary order and the frame may lay that
        order out the other way round; both the labels and the picture go through
        the same mapping, so a label cannot end up naming the other axis.
        """
        for side, dim in zip(('bottom', 'left'), (self._xAxis, self._yAxis)):
            axis = axesSpec.axes[drawn[dim - 1]]
            plotItem.setLabel(side, self.axisName(axis), units=axis.units or '')

    def _setScreenAxes(self, axesSpec, drawn):
        """Which axis of the read lies horizontal.

        The dictionary order stands, unless one of the two axes drawn is a time
        axis: a picture of a signal against time is read along time, so the
        samples go horizontal wherever the dictionary places that axis. A radiance
        is stored (bands, samples) and read as time on the abscissa.
        """
        self._xAxis, self._yAxis = 1, 2
        if len(drawn) == 2 and axesSpec.axes[drawn[1]].is_time:
            self._xAxis, self._yAxis = 2, 1

    def _forScreen(self, values):
        """The array as pyqtgraph wants it: its first index lies horizontal.

        Contiguous on purpose: an ImageItem handed the transposed view of a
        re-read array pays for the strides on every repaint.
        """
        return values if self._xAxis == 1 else np.ascontiguousarray(values.T)

    def accessFor(self, treeNode):
        return QVizTensorDataAccess(treeNode.getDataSource())

    def dataPathOf(self, treeNode):
        path = treeNode.getParametrizedDataPath()
        return path if path else treeNode.getName()

    def quantityLabel(self, treeNode):
        quantity = treeNode.getName() or ''
        units = treeNode.getUnits()
        return quantity + '[' + units + ']' if units else quantity

    @staticmethod
    def axisName(axis):
        if axis.coordinate:
            return axis.coordinate.replace('/', '.').rsplit('.', 1)[-1]
        return 'dimension %d' % axis.level
