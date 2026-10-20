# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""A column of panels, all drawn against the same abscissa.

What this frame adds to a plain stack of panels (`QVizPanel.py`) is that they
share one abscissa and one vertical range: the point of the window is to compare
how several quantities behave over the same span, so panning one panel moves the
others and every curve is read against the same scale. A Table Plot View does
the opposite -- one panel each, each on whatever axis it sits on -- and is the
window to send a user to when the quantities do not agree.

That promise is what the two checkboxes and the refusal are for, and all three
were broken in the old window:

  * the abscissa was never actually shared. `plotItemFirst`, the plot the others
    were linked to, was reset to None at the top of every `plot()` call, so from
    the second panel on nothing was linked and each curve kept its own range --
    measured on two quantities: the first panel linked, the second linked to
    nothing;
  * "Group pan mode" read `self.viewBoxes`, an attribute this class never set, so
    toggling it raised AttributeError;
  * "Display X axis of all plots" only ever changed what the linking had already
    decided, leaving one panel of two with tick labels and the other without.

So the abscissa has to be decided once: the first quantity read fixes it, and a
quantity the read would take along another axis is refused by name rather than
drawn against the wrong one -- which is what the old path did instead, reading
the second quantity along the first one's coordinate and labelling the panel with
the axis its numbers did not come off.

The two axes are linked through the view boxes, not through the axis items: a
linked axis mirrors a range for its own label, while the manual promises that
interacting with one plot moves all of them. Tick labels are a separate policy,
because nothing in the link hides them -- only `GraphicsLayout` does that, and
this frame lays its panels out itself.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QGridLayout, QVBoxLayout, QWidget

from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPanel import (QVizPanel,
                                                            QVizPanelScrollArea)


class QVizStackedPlot(QWidget):
    """The panels of a Stacked Plot View, in the frame the api can manage."""

    def __init__(self, parent=None, title=''):
        super().__init__(parent)
        self.figureKey = None
        self.dataTreeView = None
        self._panels = []
        # The abscissa strategy the entry asked for: 'TIME', or 'DEFAULT' to let
        # each quantity answer for itself.
        self.plotAxis = 'DEFAULT'
        # (key, name) of the abscissa every panel runs along: the first quantity
        # read fixes it, because one column of panels has one abscissa.
        self.abscissa = None

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

        # Both entries are kept -- they are what the manual describes -- but they
        # are wired to what they say. The old window's "Group pan mode" died on a
        # missing attribute and its "Display X axis of all plots" changed nothing
        # that the axis linking had not already decided.
        bar = QHBoxLayout()
        self.groupPanCheck = QCheckBox('Group pan mode', self)
        self.groupPanCheck.setChecked(True)
        self.groupPanCheck.toggled.connect(self.applyLinkPolicy)
        self.xAxisCheck = QCheckBox('Display X axis of all plots', self)
        self.xAxisCheck.toggled.connect(self.applyXLabelsPolicy)
        bar.addWidget(self.groupPanCheck)
        bar.addWidget(self.xAxisCheck)
        bar.addStretch(1)
        layout.addLayout(bar)
        layout.addWidget(self.scroll)

        if title:
            self.setWindowTitle(title)

    def getPlotAxis(self):
        return self.plotAxis

    def setPlotAxis(self, plotAxis):
        self.plotAxis = plotAxis

    def plot(self, treeNode, as_function_of_time=None):
        """Add one quantity to the column and draw it there.

        Returns how many curves the panel holds. A quantity this window cannot
        show raises, naming it: the caller keeps going with the rest of the
        selection.
        """
        panel = QVizPanel(self)
        drawn = panel.plot(treeNode, len(self._panels), as_function_of_time)
        if self.abscissa is not None and panel.abscissa[0] != self.abscissa[0]:
            # Not drawn, not titled, not registered: the panel has no parent yet,
            # so dropping it here leaves nothing on screen. Drawing it anyway
            # would put numbers that came off another axis under an abscissa
            # labelling them wrongly -- the old behaviour, and the reason this
            # window is being rewritten.
            raise ValueError('"%s" is read along %s, not %s: a stacked window '
                             'draws every panel against the abscissa of the '
                             'first quantity read. TablePlotView is the window '
                             'for quantities that do not agree.'
                             % (self.dataPathOf(treeNode),
                                panel.abscissa[1] or 'nothing',
                                self.abscissa[1] or 'nothing'))
        self.abscissa = self.abscissa or panel.abscissa
        self._panels.append(panel)
        self.grid.addWidget(panel, len(self._panels) - 1, 0)
        self.applyLinkPolicy()
        self.applyXLabelsPolicy()
        return drawn

    def applyLinkPolicy(self):
        """Share the first panel's ranges, or hand every panel back its own."""
        if len(self._panels) < 2:
            return
        first = self._panels[0].plotItem().getViewBox()
        together = self.groupPanCheck.isChecked()
        for panel in self._panels[1:]:
            box = panel.plotItem().getViewBox()
            box.setXLink(first if together else None)
            box.setYLink(first if together else None)

    def applyXLabelsPolicy(self):
        """Which panels carry abscissa tick labels: the bottom one, or all.

        Written on every axis because a link hides nothing by itself: the old
        window set the style on the plots it had collected and left the first
        panel of a two-panel selection showing labels while the second showed
        none, in both states of its checkbox.
        """
        bottom = len(self._panels) - 1
        everywhere = self.xAxisCheck.isChecked()
        for index, panel in enumerate(self._panels):
            panel.plotItem().getAxis('bottom').setStyle(
                showValues=everywhere or index == bottom)

    def setSignalData(self, treeNode, signalData):
        """Record the selection entry a panel answers for.

        The figure registry needs it to answer "which quantity is this window
        showing", which is what the Show/Hide and Delete entries list.
        """
        panel = self.panelFor(treeNode)
        if panel is None:
            return False
        panel.signalData = signalData
        panel.plotItem().signalData = signalData
        return True

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

    def abscissaName(self):
        return self.abscissa[1] if self.abscissa else None

    def getPlotItemsDict(self):
        """{plot item: [(row, column)]}, as whoever keys panels by place asks.

        One column: the row is the order the quantities were read in. The old
        window forced `cols` to 1 and still wrote `column = n / cols` and
        `row = n % cols`, which put every panel in row 0 and spread them over
        columns it never drew.
        """
        return {panel.plotItem(): [(index, 0)]
                for index, panel in enumerate(self._panels)}

    def dataPathOf(self, treeNode):
        path = treeNode.getParametrizedDataPath()
        return path if path else treeNode.getName()

    def __repr__(self):
        return '<QVizStackedPlot %s panels=%d abscissa=%s>' % (
            self.windowTitle(), len(self._panels), self.abscissaName())
