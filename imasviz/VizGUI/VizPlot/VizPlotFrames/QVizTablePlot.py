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

The panel itself -- the curve, the axis labels, the controls for the axes the
read pins -- is in `QVizPanel.py`: a Stacked Plot View lays the same panels in
one column and makes them share one abscissa, and only the layout differs.

Written against the axes model and the tensor read rather than the old
QVizTablePlotView, which read one abscissa for the whole selection through
Viz_API.GetSignal and drew whatever came back: a quantity with two axes to draw
against a coordinate died with ``'QVizDataArrayHandle' object is not
subscriptable``, and the same quantity read along time came back as a curve of
one of its elements, titled as the whole quantity and with no word saying that
one element had been picked.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QGridLayout, QPushButton,
                               QVBoxLayout, QWidget)

from imasviz.VizGUI.VizConfigurations.QVizSavePlotConfig import QVizSavePlotConfig
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPanel import (QVizPanel,
                                                            QVizPanelScrollArea)


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
