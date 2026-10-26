# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""One panel: a quantity, its curve, and the controls for the axes it leaves out.

Held apart from the windows that lay panels out, because two of them need the
same thing: a Table Plot View puts panels side by side and lets each run along
whatever axis it sits on, a Stacked Plot View stacks them in one column and
makes them share one abscissa. What a panel is -- one quantity, one curve, the
controls for the axes the read pins rather than draws -- does not depend on
which of the two windows holds it.

The panel answers what the data access asks of a plot frame, so the read pins
the axes this panel does not draw at the indices these controls hold; that is
what keeps the element a curve answers for both visible and movable, which the
old windows did by hiding a slider behind the whole selection.

Written against the axes model and the tensor read rather than the legacy curve
window, which drew one curve per signal against one abscissa taken from the node
the menu had been built on: a quantity with two axes to draw died on the read,
and a quantity read along another quantity's abscissa came out labelled with the
wrong axis.
"""

import pyqtgraph as pg

from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from imasviz.VizDataAccess.QVizAxesSpec import QVizAxis
from imasviz.VizDataAccess.QVizTensorDataAccess import QVizTensorDataAccess
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizSliceControls import QVizSliceControls


class QVizPanelScrollArea(QScrollArea):
    """The scroll area around the panels, which leaves the wheel to the plot.

    The manual says the wheel zooms a panel and that scrolling is done with the
    bar: a wheel that did both would zoom whatever happened to be under the
    pointer while the user was trying to reach the panel below it.
    """

    def wheelEvent(self, event):
        event.ignore()


class QVizPanel(QWidget):
    """One quantity: its plot, and the controls for the axes it leaves out."""

    def __init__(self, frame, parent=None):
        super().__init__(parent)
        self._frame = frame
        # (key, name) of the axis the curve runs along, filled by plot().
        self.abscissa = (None, None)

        self.pgPlotWidget = pg.PlotWidget(self)
        self.pgPlotWidget.showGrid(x=True, y=True)
        self.sliceControls = QVizSliceControls(self)
        self.sliceControls.changed.connect(self.refresh)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.pgPlotWidget)
        layout.addWidget(self.sliceControls)

    def getPlotAxis(self):
        """The abscissa strategy of the window this panel sits in.

        Asked by the read, through the node, to decide whether a quantity in a
        dynamic array is drawn along time or along its own first axis.
        """
        return self._frame.getPlotAxis()

    def plotItem(self):
        return self.pgPlotWidget.getPlotItem()

    def plot(self, treeNode, row, as_function_of_time=None):
        """Draw one quantity here. Returns how many curves were drawn."""
        self.treeNode = treeNode
        self.row = row
        self.asFunctionOfTime = as_function_of_time
        access = self.accessFor(treeNode)
        axesSpec, timeAxis, alongTime, plotted = access.plan(treeNode, self,
                                                             as_function_of_time)
        self.abscissa = self.abscissaOf(axesSpec, alongTime)
        if len(plotted) > 1:
            # A panel draws one axis. Two axes to draw is a picture, and a
            # picture needs its colour scale and its drawn time axis: the panel
            # says which, rather than picking an element of the quantity and
            # drawing it as if it were the whole thing.
            raise ValueError('"%s" has %d axes to draw: a panel holds a curve, '
                             'and a picture needs a window of its own.'
                             % (self._frame.dataPathOf(treeNode), len(plotted)))

        x, y = access.GetSignal(treeNode=treeNode, plotWidget=self,
                                as_function_of_time=as_function_of_time)
        if x.size == 0 or y.size == 0:
            raise ValueError('Nothing to plot for "' +
                             self._frame.dataPathOf(treeNode) +
                             '": no values along the plotted axis.')

        self.pgPlotWidget.clear()
        self._curves = []
        for index in range(y.shape[0]):
            self._curves.append(self.pgPlotWidget.plot(x[0], y[index]))

        self.pgPlotWidget.setTitle(self._frame.dataPathOf(treeNode))
        self.setAxisLabels(treeNode, axesSpec, alongTime)
        self.sliceControls.setSlices(access.slicesFor(treeNode, plotWidget=self,
                                                      as_function_of_time=as_function_of_time))
        return y.shape[0]

    def refresh(self):
        """Re-read this panel through its own controls."""
        if not getattr(self, '_curves', None):
            return
        for row, curve in enumerate(self._curves):
            x, y = self.accessFor(self.treeNode).GetSignal(
                treeNode=self.treeNode, plotWidget=self,
                as_function_of_time=self.asFunctionOfTime)
            if y.shape[0] > row and x.shape[0] > 0:
                curve.setData(x[0], y[row])
            else:
                curve.setData([], [])

    def curveCount(self):
        return len(getattr(self, '_curves', []))

    def curves(self):
        return list(getattr(self, '_curves', []))

    def setAxisLabels(self, treeNode, axesSpec, alongTime):
        """Label both axes from the axes the read actually drew.

        The old windows took the abscissa label from whichever node the menu had
        been built on and drew it under every plot, so a selection of quantities
        on different coordinates came back with one label naming one of them.
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

    def accessFor(self, treeNode):
        return QVizTensorDataAccess(treeNode.getDataSource())

    @staticmethod
    def abscissaOf(axesSpec, alongTime):
        """(key, name) of the axis the curve runs along.

        Asked of the plan rather than of the node, because the strategy decides
        it: the same quantity is against its own coordinate in one window and
        against time in the next. Keyed by `QVizAxis.key()` so two quantities
        sharing a coordinate name the same abscissa and two sitting on different
        ones do not, which is what lets a window stack several panels against one
        abscissa and name the refusal when a quantity does not run along it.
        """
        if alongTime:
            return 'time', 'time'
        plotted = [axis for axis in axesSpec.axes if axis.origin == QVizAxis.LEAF]
        if not plotted:
            return (None, None)
        return plotted[0].key(), QVizPanel.axisName(plotted[0])

    @staticmethod
    def axisName(axis):
        if axis.coordinate:
            return axis.coordinate.replace('/', '.').rsplit('.', 1)[-1]
        return 'dimension %d' % axis.level
