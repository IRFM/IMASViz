# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""A curve figure that says which slice of a quantity it drew.

Written against the axes model and the tensor read rather than against
QVizPlotWidget, for the reasons those two modules state: a curve draws one axis,
so every other axis of the quantity is fixed somewhere, and a figure that does
not say where it fixed them is showing numbers nobody can attribute.

The loop this closes:

    plot(node)   ask the read what it drew, plot it, then ask the same read which
                 axes it fixed -- one control each, named and bounded
    controls     moving one emits changed
    refresh()    read again through those controls and update that curve in place

Nothing here decides which axes are plotted: the access does, and the controls
and the axis labels both come out of that one answer.
"""

import pyqtgraph as pg

from PySide6.QtWidgets import QVBoxLayout, QWidget

from imasviz.VizDataAccess.QVizAxesSpec import QVizAxis
from imasviz.VizDataAccess.QVizTensorDataAccess import QVizTensorDataAccess
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizSliceControls import QVizSliceControls


class QVizCurvePlot(QWidget):
    """Curves of one shot view, with a control per axis they leave out."""

    # The data access and the node's own code ask a plot frame these three. This
    # path drives nothing from them -- the slice controls carry the indices --
    # but they are asked, so they are answered without the slider machinery the
    # names imply.
    addTimeSlider = False
    addCoordinateSlider = False
    sliderGroup = None

    def __init__(self, parent=None, title=''):
        super().__init__(parent)

        self.plotAxis = 'DEFAULT'
        # One entry per drawn row: the node it came from, which row of that
        # node's answer it is, and how it was asked for. A quantity held by a
        # static array read at several indexes gives several rows, and each has
        # to be updated with its own row on a slice change.
        self._curves = []
        # {axis key: QVizSlice} across every quantity on the figure, in the order
        # the axes first appeared. Merged rather than replaced, because an axis
        # two quantities share is one control: the index that pins one pins the
        # other.
        self._slices = {}

        self.pgPlotWidget = pg.PlotWidget(self)
        self.pgPlotWidget.setObjectName('curvePlot')
        self.pgPlotWidget.addLegend()

        self.sliceControls = QVizSliceControls(self)
        # The read calls this attribute by name, so the controls and the numbers
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

    def plot(self, treeNode, as_function_of_time=None):
        """Add one quantity to the figure, with a control per axis it fixes.

        Returns the number of rows drawn.
        """
        access = self.accessFor(treeNode)
        axesSpec, timeAxis, alongTime, _ = access.plan(treeNode, self,
                                                       as_function_of_time)
        x, y = access.GetSignal(treeNode=treeNode, plotWidget=self,
                                as_function_of_time=as_function_of_time)
        if x.size == 0 or y.size == 0:
            # Drawing an empty curve silently is the failure this path exists to
            # remove: the axes were pinned somewhere and nothing said where, so
            # an empty result reads as an empty quantity.
            raise ValueError('Nothing to plot for "' + self.dataPathOf(treeNode) +
                             '": no values along the plotted axis.')

        legend = self.dataPathOf(treeNode)
        for row in range(y.shape[0]):
            curve = self.pgPlotWidget.plot(x[0], y[row], name=legend)
            self._curves.append((treeNode, row, curve, as_function_of_time))

        self.setAxisLabels(treeNode, axesSpec, timeAxis, alongTime)
        self.addSlices(access.slicesFor(treeNode, plotWidget=self,
                                        as_function_of_time=as_function_of_time))
        return y.shape[0]

    def refresh(self):
        """Re-read every curve through the controls, updating each in place.

        Not a re-plot: rebuilding the curves would rebuild the controls the user
        is still holding, and move the colours and legend entries under their
        hand.
        """
        for treeNode, row, curve, as_function_of_time in self._curves:
            x, y = self.accessFor(treeNode).GetSignal(
                treeNode=treeNode, plotWidget=self,
                as_function_of_time=as_function_of_time)
            if y.shape[0] > row and x.shape[0] > 0:
                curve.setData(x[0], y[row])
            else:
                curve.setData([], [])
        return self.sliceControls.indices()

    def curveCount(self):
        return len(self._curves)

    def isDrawing(self):
        return bool(self._curves)

    def curves(self):
        return [curve for _, _, curve, _ in self._curves]

    def sliceKeys(self):
        return list(self._slices)

    def addSlices(self, slices):
        for sl in slices:
            if sl.key not in self._slices:
                self._slices[sl.key] = sl
        self.sliceControls.setSlices(list(self._slices.values()))

    def accessFor(self, treeNode):
        return QVizTensorDataAccess(treeNode.getDataSource())

    def dataPathOf(self, treeNode):
        path = treeNode.getParametrizedDataPath()
        return path if path else treeNode.getName()

    def setAxisLabels(self, treeNode, axesSpec, timeAxis, alongTime):
        """Label both axes from the axes the read actually drew.

        The unit comes from the axis itself: a label built from a flag set when
        the figure was created claims seconds for an axis the dictionary says is
        in metres.
        """
        if alongTime:
            self.pgPlotWidget.setLabel('bottom', 'time', units='s')
        else:
            plotted = [axis for axis in axesSpec.axes if axis.origin == QVizAxis.LEAF]
            if plotted:
                axis = plotted[0]
                self.pgPlotWidget.setLabel('bottom', self.axisName(axis),
                                           units=axis.units or '')

        quantity = treeNode.getName() or ''
        units = treeNode.getUnits()
        if units:
            quantity += '[' + units + ']'
        self.pgPlotWidget.setLabel('left', quantity)

    @staticmethod
    def axisName(axis):
        if axis.coordinate:
            return axis.coordinate.replace('/', '.').rsplit('.', 1)[-1]
        return 'dimension %d' % axis.level
