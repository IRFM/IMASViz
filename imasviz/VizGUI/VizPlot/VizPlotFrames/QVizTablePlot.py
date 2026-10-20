# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""A window of panels: one quantity per panel, each with the axes it is read on.

The point of this frame is that a panel holds one quantity. A curve figure puts
every curve on one pair of axes, so the quantities in it have to agree on an
abscissa and share the controls for the axes left out; a panel does not care what
its neighbour is drawn against. That is what makes it the right answer for a
selection of quantities sitting on different coordinates -- and it is why the
gate the old entries hid behind (do these signals share coordinates?) is not
asked here: nothing is shared, so nothing has to agree.

Written against the axes model and the tensor read rather than the old
QVizTablePlotView, which read one abscissa for the whole selection through
Viz_API.GetSignal and drew whatever came back: a quantity with two axes to draw
against a coordinate died with ``'QVizDataArrayHandle' object is not
subscriptable``, and the same quantity read along time came back as a curve of
one of its elements, titled as the whole quantity and with no word saying that
one element had been picked.

Each panel carries the controls for the axes the read fixes rather than draws,
so the element a panel answers for is named and moved on the panel itself.
"""

import pyqtgraph as pg

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QGridLayout, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from imasviz.VizDataAccess.QVizAxesSpec import QVizAxis
from imasviz.VizDataAccess.QVizTensorDataAccess import QVizTensorDataAccess
from imasviz.VizGUI.VizConfigurations.QVizSavePlotConfig import QVizSavePlotConfig
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
    """One quantity: its plot, and the controls for the axes it leaves out.

    Answers what the data access asks of a plot frame, so the read pins the
    axes this panel does not draw at the indices these controls hold.
    """

    addTimeSlider = False
    addCoordinateSlider = False
    sliderGroup = None

    def __init__(self, frame, parent=None):
        super().__init__(parent)
        self._frame = frame

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

        The old window took the abscissa label from whichever node the menu had
        been built on and drew it under every panel, so a selection of quantities
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
    def axisName(axis):
        if axis.coordinate:
            return axis.coordinate.replace('/', '.').rsplit('.', 1)[-1]
        return 'dimension %d' % axis.level


class QVizTablePlot(QWidget):
    """The panels of a Table Plot View, in the frame the api can manage."""

    def __init__(self, parent=None, title=''):
        super().__init__(parent)
        self.figureKey = None
        self.dataTreeView = None
        self._panels = []
        # The abscissa strategy the entry asked for: 'TIME', or 'DEFAULT' to let
        # each quantity answer for itself.
        self.plotAxis = 'DEFAULT'

        self.scroll = QVizPanelScrollArea(self)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setWidgetResizable(True)

        self.gridHost = QWidget(self.scroll)
        self.grid = QGridLayout(self.gridHost)
        self.grid.setContentsMargins(4, 4, 4, 4)
        self.scroll.setWidget(self.gridHost)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # The manual reaches this through the window's own menu bar; a window
        # embedded in the MDI area gets its bar from the frame instead.
        bar = QHBoxLayout()
        self.saveButton = QPushButton('Save Plot Configuration', self)
        self.saveButton.clicked.connect(self.onSavePlotConf)
        bar.addWidget(self.saveButton)
        bar.addStretch(1)
        layout.addLayout(bar)
        layout.addWidget(self.scroll)

        if title:
            self.setWindowTitle(title)

    def getPlotAxis(self):
        return self.plotAxis

    def setPlotAxis(self, plotAxis):
        self.plotAxis = plotAxis

    def onSavePlotConf(self):
        """Write this table out as a '.pcfg' the api can apply again."""
        command = QVizSavePlotConfig(self, dataTreeView=self.dataTreeView)
        command.execute()

    def plot(self, treeNode, as_function_of_time=None):
        """Give this quantity its own panel and draw it there.

        Returns how many curves the panel holds. A quantity the panel cannot
        show raises, naming the quantity: the caller keeps going with the rest of
        the selection.
        """
        panel = QVizPanel(self)
        row = len(self._panels)
        drawn = panel.plot(treeNode, row, as_function_of_time)
        self.addPanelToGrid(panel, row)
        self._panels.append(panel)
        return drawn

    def setSignalData(self, treeNode, signalData):
        """Record the selection entry a panel answers for.

        The configuration file says which node each panel was made for; without
        it on the plot item the save command stops at the first panel and writes
        a configuration holding fewer panels than the window shows.
        """
        panel = self.panelFor(treeNode)
        if panel is None:
            return False
        panel.signalData = signalData
        panel.plotItem().signalData = signalData
        return True

    def addPanelToGrid(self, panel, row):
        columns = self.columnsFor(len(self._panels) + 1)
        self.grid.addWidget(panel, row // columns, row % columns)

    @staticmethod
    def columnsFor(count):
        """How wide the table is, decided by how many panels it holds.

        The old window took the number of columns from the screen width, so the
        same selection came out in one column or in four depending on the
        monitor -- and the row and column it recorded on each panel were the
        other way round from where the panel was laid, which is what the
        configuration file keys panels by.
        """
        if count < 2:
            return 1
        if count < 5:
            return 2
        return 3

    def panels(self):
        return list(self._panels)

    def panelCount(self):
        return len(self._panels)

    def isDrawing(self):
        return any(panel.curveCount() for panel in self._panels)

    def curveCount(self):
        return sum(panel.curveCount() for panel in self._panels)

    def curves(self):
        return [curve for panel in self._panels for curve in panel.curves()]

    def panelFor(self, treeNode):
        """The panel holding this quantity, for whoever adds a curve to it."""
        for panel in self._panels:
            if panel.treeNode is treeNode:
                return panel
        return None

    def getPlotItemsDict(self):
        """{plot item: [(row, column)]}, as the save command asks for it.

        Keyed the way the configuration file writes it -- row then column -- so
        a configuration saved from this window and read back names the same
        panel. The old window wrote one order and compared the other, so only a
        panel on the diagonal of the table was ever found again.
        """
        columns = self.columnsFor(len(self._panels))
        return {panel.plotItem(): [(index // columns, index % columns)]
                for index, panel in enumerate(self._panels)}

    def dataPathOf(self, treeNode):
        path = treeNode.getParametrizedDataPath()
        return path if path else treeNode.getName()

    def __repr__(self):
        return '<QVizTablePlot %s panels=%d>' % (self.windowTitle(),
                                                 len(self._panels))
