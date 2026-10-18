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

The dynamic array is one of the fixed axes here. A curve along time draws it and
offers no control for it; an image does not draw it, so its time slice is a
control like any other, and the read takes the control's index rather than the one
the tree happens to carry.

The cells of the image are element ranks, laid over the coordinate extents: a
dictionary grid need not be regular, and pyqtgraph draws an image as a regular
grid. What is exact is the extent, the labels and the slice the colours stand for.
"""

import numpy as np
import pyqtgraph as pg

from PySide6.QtWidgets import QVBoxLayout, QWidget

from imasviz.VizDataAccess.QVizTensorDataAccess import QVizTensorDataAccess
from imasviz.VizEntities.QVizDataArrayHandle import QVizDataArrayHandle
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizSliceControls import QVizSliceControls


class QVizImagePlot(QWidget):
    """One image of one quantity, with a control per axis outside the image."""

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
        self._levels = None
        # Which axis of the read lies horizontal, decided when the picture is
        # drawn and reused by every slice after it.
        self._xAxis, self._yAxis = 1, 2

        self.pgPlotWidget = pg.GraphicsLayoutWidget(self)
        self.pgPlotWidget.setObjectName('imagePlot')
        self.plotItem = self.pgPlotWidget.addPlot(row=0, col=0)
        self.imageItem = None
        self.colorBar = None

        self.sliceControls = QVizSliceControls(self)
        # The read calls this attribute by name, so the controls and the picture
        # cannot be out of date with respect to each other.
        self.sliceControls.changed.connect(self.refresh)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.pgPlotWidget)
        layout.addWidget(self.sliceControls)

        if title:
            self.setWindowTitle(title)

    def getPlotAxis(self):
        return self.plotAxis

    def setPlotAxis(self, plotAxis):
        self.plotAxis = plotAxis

    def plot(self, treeNode):
        """Draw one quantity, with a control per axis the image leaves out.

        Returns the number of images on the figure: one.
        """
        if self.imageItem is not None:
            raise ValueError('This figure already holds an image of "' +
                             self.dataPathOf(self._treeNode) + '": one image per '
                             'figure, because a second picture would need its own '
                             'colour scale and its own controls.')

        access = self.accessFor(treeNode)
        # An image never runs along time: it draws two axes of the quantity, and
        # the dynamic array joins the axes it fixes.
        axesSpec, _, _, plotted = access.plan(treeNode, self,
                                              as_function_of_time=False)
        handle = access.GetSignal(treeNode=treeNode, plotWidget=self,
                                  as_function_of_time=False)
        path = self.dataPathOf(treeNode)

        if not isinstance(handle, QVizDataArrayHandle):
            raise ValueError('"' + path + '" has one axis to draw: it belongs on a '
                             'curve figure, where its fixed axes get controls too.')
        values = np.asarray(handle.arrayValues)
        if values.ndim < 2 or values.size == 0:
            raise ValueError('Nothing to plot for "' + path +
                             '": no values in the image.')

        self._treeNode = treeNode
        self._setScreenAxes(axesSpec, plotted)
        self.imageItem = pg.ImageItem(self._forScreen(values))
        self.plotItem.addItem(self.imageItem)
        self.setExtent(handle)
        self.setAxisLabels(axesSpec, plotted)

        quantity = self.quantityLabel(treeNode)
        self.plotItem.setTitle(quantity)
        self.colorBar = pg.ColorBarItem(label=quantity, interactive=False)
        self.pgPlotWidget.addItem(self.colorBar, row=0, col=1)
        self.colorBar.setImageItem(self.imageItem)

        self.addSlices(access.slicesFor(treeNode, plotWidget=self,
                                        as_function_of_time=False))
        # Where the colour scale settled on the first draw. Comparing two slices
        # means comparing colours, so the scale must not re-fit itself to each one.
        self._levels = self.colourLevels()
        return 1

    def refresh(self):
        """Re-read the slice the controls picked, updating the picture in place.

        Not a re-plot: rebuilding the image would rebuild the controls the user is
        still holding and reset the colour scale under their hand.
        """
        if self.imageItem is None:
            return None

        handle = self.accessFor(self._treeNode).GetSignal(
            treeNode=self._treeNode, plotWidget=self, as_function_of_time=False)
        values = np.asarray(handle.arrayValues) \
            if isinstance(handle, QVizDataArrayHandle) else np.asarray([])

        if values.size == 0:
            # A slice holding nothing shows nothing. Leaving the previous picture
            # up answers a question the user never asked.
            self.imageItem.clear()
        else:
            self.imageItem.setImage(self._forScreen(values))
            if self._levels is not None:
                self.imageItem.setLevels(self._levels)
            # A different element of a static array can carry a grid of its own,
            # so the extent belongs to the slice just read, not to the first one.
            self.setExtent(handle)
        return self.sliceControls.indices()

    def imageCount(self):
        return 0 if self.imageItem is None else 1

    def isDrawing(self):
        return self.imageItem is not None

    def images(self):
        return [] if self.imageItem is None else [self.imageItem]

    def colourLevels(self):
        if self.imageItem is None:
            return None
        levels = self.imageItem.getLevels()
        return None if levels is None else (float(levels[0]), float(levels[1]))

    def sliceKeys(self):
        return self.sliceControls.keys()

    def addSlices(self, slices):
        self.sliceControls.setSlices(slices)

    def setExtent(self, handle):
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
        self.imageItem.setRect(x0, y0, x1 - x0, y1 - y0)

    def setAxisLabels(self, axesSpec, plotted):
        """Label both image axes from the axes the read actually drew.

        The read shapes its values in dictionary order and the frame may lay that
        order out the other way round; both the labels and the picture go through
        the same mapping, so a label cannot end up naming the other axis.
        """
        for side, dim in zip(('bottom', 'left'), (self._xAxis, self._yAxis)):
            axis = axesSpec.axes[plotted[dim - 1]]
            self.plotItem.setLabel(side, self.axisName(axis), units=axis.units or '')

    def _setScreenAxes(self, axesSpec, plotted):
        """Which axis of the read lies horizontal.

        The dictionary order stands, unless one of the two axes drawn is a time
        axis: a picture of a signal against time is read along time, so the
        samples go horizontal wherever the dictionary places that axis. A radiance
        is stored (bands, samples) and read as time on the abscissa.
        """
        self._xAxis, self._yAxis = 1, 2
        if len(plotted) == 2 and axesSpec.axes[plotted[1]].is_time:
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
