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

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QGridLayout, QPushButton,
                               QVBoxLayout, QWidget)

from imasviz.VizGUI.VizConfigurations.QVizSavePlotConfiguration import \
    QVizSavePlotConfiguration
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPanel import (QVizPanel,
                                                            QVizPanelScrollArea)


class QVizTablePlot(QWidget):
    """The panels of a Table Plot View, in the frame the api can manage."""

    #: The room between the rows of panels, set on the grid below. Left to a
    #: style the grid answers 6 on this node, which lays a panel's curve flush
    #: against the one below it. A little more -- room, not a gap -- is the
    #: vertical move the rows stack and the panels do not.
    ROW_SPACING = 10

    def __init__(self, parent=None, title=''):
        super().__init__(parent)
        self.figureKey = None
        self.dataTreeView = None
        self._panels = []
        # {panel: (row, column)} for the panels a saved configuration named a
        # place for. They keep that cell; the rest fill what is left.
        self._places = {}
        # The abscissa strategy the entry asked for: 'TIME', or 'DEFAULT' to let
        # each quantity answer for itself.
        self.plotAxis = 'DEFAULT'
        # How many panels a row holds when it is told; None is the width the
        # page size answers, which is what `layoutTable` asks by default.
        self._columns = None

        self.scroll = QVizPanelScrollArea(self)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setWidgetResizable(True)

        self.gridHost = QWidget(self.scroll)
        self.grid = QGridLayout(self.gridHost)
        self.grid.setContentsMargins(4, 4, 4, 4)
        # The row is the one that stacks the panels, so it is the one that
        # needs the room: see `ROW_SPACING`.
        self.grid.setVerticalSpacing(self.ROW_SPACING)
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

    def columns(self):
        """How many panels a row holds, or None for the width of the page size.

        Asked by whoever lays the table out and by whoever wants to say which
        one it is. `None` is the width `columnsFor` answers for how many panels
        the table holds -- the width the page has always had -- and the one a
        saved configuration's `row`/`column` were measured against when no width
        was told to them.
        """
        return self._columns

    def setColumns(self, columns):
        """How many panels a row holds, or None to go back to the page size.

        The width is asked of `layoutTable` once a row is laid, from here, rather
        than from the panel count, so a width told to this window is the width
        its rows are laid at. A zero or negative width is not a width, and is
        refused by the name rather than laid out as one column.
        """
        if columns is not None and columns < 1:
            raise ValueError(
                'the table is told %r panels per row: a row holds at least '
                'one, or nothing at all for the page size to answer'
                % (columns,))
        self._columns = columns

    def onSavePlotConf(self):
        """Write this table out as a '.pcfg' the api can apply again.

        A configuration that cannot be written -- a name the user typed that
        names a place rather than a configuration -- is said in the log panel of
        the shot view the window belongs to, not left as a traceback out of the
        button.
        """
        try:
            QVizSavePlotConfiguration(self.dataTreeView, self).execute()
        except ValueError as e:
            logging.getLogger(self.dataTreeView.uri).error(str(e))

    def plot(self, treeNode, as_function_of_time=None, place=None):
        """Give this quantity its panel, and the reason in it when it cannot draw.

        `place` is the (row, column) a saved configuration said this panel sat
        at; left out, the panel goes where the next free slot of the table is.

        Returns how many curves the panel holds -- zero when the read of this
        quantity raised, the panel kept with the refusal in it, the reason
        named in the log of the case, and the rest of the page drawn on:
        a page is a window of panels, and taking the panel of the quantity
        that raised used to leave the user one window short with the
        exception only in the log. The name under the words is the one the
        window itself would label the panel with, so a refusal under
        `time_slice/i/point.r` is not mistaken for the same name in another
        array of structures.
        """
        panel = QVizPanel(self)
        drawn = 0
        try:
            drawn = panel.plot(treeNode, len(self._panels), as_function_of_time)
        except Exception as e:
            # The read of this quantity raised; the page keeps its cell, with
            # the reason holding it -- not a hole in the grid and a hole in
            # the count the user is keeping.
            panel.showRefusal(self.dataPathOf(treeNode), str(e))
            if self.dataTreeView is not None:
                logging.getLogger(self.dataTreeView.uri).error(str(e))
        self._panels.append(panel)
        if place is not None:
            self._places[panel] = (place[0], place[1])
        self.layoutTable()
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

    def layoutTable(self):
        """Lay every panel in a cell of its own, on a grid of one width.

        The width is asked once for the whole table: from the width told to the
        window, or, told none, from how many panels it holds. Asked per panel as
        it arrives -- which is what this file did -- it
        answers 1 for the first panel, 2 until the fifth and 3 after, so the
        first panels are laid on a narrower grid than the rest: measured, panels
        3 and 4 both land in cell (1,1) from five panels on, cell (0,2) is never
        filled, and a 16-panel table grows a sixth row holding one panel. A
        QGridLayout puts two widgets in one cell **without a word of warning**,
        so the overlap is only what the user sees.

        A panel whose cell came from a saved configuration keeps that cell; the
        others fill the first cell left free, row by row. The table is filled
        before it is shown (QVizPlotAsTable.execute), so relaying it as panels
        arrive costs nothing on screen.
        """
        if self._columns is None:
            columns = self.columnsFor(len(self._panels))
        else:
            columns = self._columns
        named = self._namedCells()
        free = self._freeCells(columns, set(named.values()))
        for panel in self._panels:
            cell = named[panel] if panel in named else next(free)
            slot = self.grid.indexOf(panel)
            if slot >= 0 and self.grid.getItemPosition(slot)[:2] == cell:
                continue
            if slot >= 0:
                self.grid.removeWidget(panel)
            self.grid.addWidget(panel, cell[0], cell[1])

    def _namedCells(self):
        """{panel: (row, column)} for the panels a configuration named a place for.

        The first panel to claim a cell keeps it and the rest are laid with the
        others: a configuration written before this layout was fixed names one
        cell twice, and laying those two panels on top of one another again is
        the defect travelling through a file.
        """
        named = {}
        taken = set()
        for panel in self._panels:
            cell = self._places.get(panel)
            if cell is not None and cell not in taken:
                taken.add(cell)
                named[panel] = cell
        return named

    @staticmethod
    def _freeCells(columns, taken):
        """The cells of a `columns`-wide table that no panel claimed, row by row."""
        row = 0
        while True:
            for column in range(columns):
                if (row, column) not in taken:
                    yield (row, column)
            row += 1

    def panelsInTable(self):
        """[(row, column, panel)] -- where each panel actually sits.

        Read from the layout rather than computed from the order the panels were
        asked for: the old window computed a place the other way round from where
        it had laid the panel, and the configuration keyed by that place then
        only found its panel again on the diagonal of the table. Every panel
        reaches the layout through layoutTable, so there is nothing to fall back
        to -- the panel of a read that refused its quantity is taken back in
        plot(), which is the only way a panel used to end up outside the grid.
        """
        return [(self.grid.getItemPosition(self.grid.indexOf(panel))[:2] +
                 (panel,)) for panel in self._panels]

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

    def styleMargins(self):
        """The room between panels, which belongs to the window laying them out.

        This is what the *Plot Design Properties* section of *Configure Plot*
        writes, asked through the panel whose right click opened the dialogue.
        One answer per window, never per panel, because one grid lays the whole
        table out -- the same reason `layoutTable` asks its width once.
        """
        return self.grid

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
        panel. It reads the same layout `panelsInTable` reads, because computing
        the places a second time from the panel count is what wrote a file
        naming a cell no panel sat in, and naming one cell twice: measured, a
        15-panel table laid two panels in (1,1) while this answer listed (0,2),
        and reloading that file laid the overlap again.
        """
        return {panel.plotItem(): [(row, column)]
                for row, column, panel in self.panelsInTable()}

    def dataPathOf(self, treeNode):
        path = treeNode.getParametrizedDataPath()
        return path if path else treeNode.getName()

    def __repr__(self):
        return '<QVizTablePlot %s panels=%d>' % (self.windowTitle(),
                                                 len(self._panels))
