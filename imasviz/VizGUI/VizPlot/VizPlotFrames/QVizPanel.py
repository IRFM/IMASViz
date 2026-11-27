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

import numpy as np
import pyqtgraph as pg

from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from imasviz.VizDataAccess.QVizAxesSpec import QVizAxis
from imasviz.VizDataAccess.QVizCurveAbscissa import TIME, describe, identityOf
from imasviz.VizDataAccess.QVizTensorDataAccess import QVizTensorDataAccess
from imasviz.VizDataAccess.QVizTensorExtractor import QVizTensorExtractor
from imasviz.VizDataAccess.QVizSlices import elementLabel
from imasviz.VizGUI.VizGuiCustomization import QVizStyle
from imasviz.VizGUI.VizPlot.QVizCurveColors import penFor
from imasviz.VizGUI.VizPlot.QVizCurveTransform import QVizCurveTransform
from imasviz.VizGUI.VizPlot.QVizPlotStyling import QVizPlotStyling
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizSliceControls import QVizSliceControls
from imasviz.VizUtils import QVizGlobalValues


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
        # The *Configure Plot* entry on this panel's own right click, as the
        # Profiles plugin offers it on its panels: the menu pyqtgraph built is the
        # view box's own, so styling one panel cannot reach another.
        self.styling = QVizPlotStyling(self)
        self.styling.addMenuEntry(self.pgPlotWidget.getViewBox().menu)
        # The words the panel holds instead of a curve, when the read refused
        # the quantity: read by whoever wants to say which panel refused what.
        self.refusalText = None
        # {curve: QVizCurveTransform} -- what each curve of this panel was read
        # with, and the (factor, offset) a hand laid on those values. A panel is
        # a source of traces like a curve figure is: its own controls re-read it
        # through `refresh`, and a transform asked on one of its curves has to
        # survive that read or it is a coat of paint, not a state. See
        # `QVizCurveTransform`.
        self._transforms = {}

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.pgPlotWidget)
        self.layout.addWidget(self.sliceControls)

    def getPlotAxis(self):
        """The abscissa strategy of the window this panel sits in.

        Asked by the read, through the node, to decide whether a quantity in a
        dynamic array is drawn along time or along its own first axis.
        """
        return self._frame.getPlotAxis()

    def plotItem(self):
        return self.pgPlotWidget.getPlotItem()

    def showRefusal(self, quantity, message):
        """Say, in this panel, why the quantity it was built for does not draw.

        The read of one quantity of a page raised -- and the window keeps its
        cell, with the reason under the name, rather than losing the panel to
        the read that refused it and the user to a window with a hole. The
        curve's widgets stand hidden under the words: the panel is still a
        panel the window lays out, it is just not drawn.
        """
        self.refusalText = message
        self.pgPlotWidget.hide()
        self.sliceControls.hide()
        words = QLabel('"%s": %s' % (quantity, message), self)
        words.setWordWrap(True)
        words.setStyleSheet('color: %s;' % QVizStyle.colour('log-error'))
        self.refusalLabel = words
        self.layout.insertWidget(0, words)

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
        self._transforms = {}
        # The legend tells which element of which array the panel holds. The
        # AOS index is spelled into the path (elementLabel, on the same reading
        # as the curve figure uses), and for a time-based AOS the value at that
        # element is appended too: two panels of one array drawn side by side
        # carry the same array name, and once there is no slider to say where,
        # the index is the only answer.
        label = self._curveLabel(treeNode, axesSpec, plotted)
        self.pgPlotWidget.addLegend()
        for index in range(y.shape[0]):
            suffix = '' if y.shape[0] == 1 else '[%d]' % index
            curve = self.pgPlotWidget.plot(x[0], y[index],
                                           pen=penFor(index),
                                           name=label + suffix)
            self._curves.append(curve)
            self._transforms[curve] = QVizCurveTransform(x[0], y[index])

        self.pgPlotWidget.setTitle(self._frame.dataPathOf(treeNode))
        self.setAxisLabels(treeNode, axesSpec, alongTime)
        self.sliceControls.setSlices(access.slicesFor(treeNode, plotWidget=self,
                                                      as_function_of_time=as_function_of_time))
        return y.shape[0]

    def plotRaw(self, x, y, name, name_units='', x_label='', x_units=''):
        """Draw a raw (x, y) pair here.

        The value the Access Layer answered at a named instant (a profile of
        the equilibrium read, `QVizEquilibriumRead.profilesAt`), not a
        quantity the tree is standing on: the read there is an IDS-object
        read the axes model does not carry, and the panel is still the same
        panel -- one curve in the palette's order, a title and a label. It
        keeps no band, because there is no read for the band to fix.
        """
        values = (np.asarray(x, dtype=float), np.asarray(y, dtype=float))
        curve = self.pgPlotWidget.plot(values[0], values[1], pen=penFor(0),
                                       name=name)
        self._curves = [curve]
        self._transforms = {curve: QVizCurveTransform(*values)}
        # The abscissa the curve runs along: the window that stacks the
        # panels (`QVizStackedPlot`) settles it on this first panel and
        # checks the rest against it, on the same identity both sides spell.
        self.abscissa = (str(x_label), x_label)
        self.pgPlotWidget.setTitle(name)
        quantity = name if not name_units else name + '[' + name_units + ']'
        self.pgPlotWidget.setLabel('left', quantity)
        self.pgPlotWidget.setLabel('bottom', x_label, units=x_units or '')
        self.sliceControls.setVisible(False)
        return 1

    def refresh(self):
        """Re-read this panel through its own controls.

        The values a re-read answers go back *under* the affine the curve
        carries, as they do in a curve figure: a panel whose controls moved is
        another element of its quantity, not a reason to draw it at the raw
        scale a hand left.
        """
        if not getattr(self, '_curves', None) or getattr(self, 'treeNode', None) is None:
            return
        for row, curve in enumerate(self._curves):
            x, y = self.accessFor(self.treeNode).GetSignal(
                treeNode=self.treeNode, plotWidget=self,
                as_function_of_time=self.asFunctionOfTime)
            record = self._transforms[curve]
            if y.shape[0] > row and x.shape[0] > 0:
                record.read(x[0], y[row])
            else:
                record.read([], [])
            record.drawInto(curve)

    def curveCount(self):
        return len(getattr(self, '_curves', []))

    def curves(self):
        return list(getattr(self, '_curves', []))

    def _curveLabel(self, treeNode, axesSpec, plotted):
        """The legend label for a panel's curve: the AOS index, and the time
        at that index when the AOS is time-based.

        A panel holds one element of its quantity, fixed by the tree the user
        is standing on. Two panels of one array therefore carry the same name
        if the label only names the array, and once there is no slider to say
        where (a panel is a quantity with fixed controls, not a curve a slider
        moves), the index is the only answer. `elementLabel` spells it into
        the path on the same reading the curve figure uses; for a time-based
        AOS the value at that element is appended too, so two panels of one
        array three slices apart are not read as the same comparison.
        """
        pinned = [axis for position, axis in enumerate(axesSpec.axes)
                  if position not in plotted]
        slices = {}
        for axis in pinned:
            if axis.origin == QVizAxis.AOS:
                letter = QVizGlobalValues.indices.get(str(axis.level))
                if letter is not None:
                    index = treeNode.parameters_values.get(letter)
                    if index is not None:
                        slices[axis.key()] = int(index)
        label = elementLabel(treeNode, pinned, slices)
        for axis in pinned:
            if axis.origin == QVizAxis.AOS and axis.is_time:
                value = self._timeValue(treeNode, axesSpec, axis)
                if value is not None:
                    label += ' (t = %g %s)' % (value, axis.units or 's')
                    break
        return label

    def _timeValue(self, treeNode, axesSpec, axis):
        """The time (in seconds) at the index-th element of a time-based AOS,
        or None when it cannot be read."""
        letter = QVizGlobalValues.indices.get(str(axis.level))
        if letter is None:
            return None
        index = treeNode.parameters_values.get(letter)
        if index is None:
            return None
        try:
            timeBase = QVizTensorExtractor(treeNode.getIDSRef()).timeBase(axesSpec)
            if timeBase is not None and len(timeBase) > int(index):
                return float(timeBase[int(index)])
        except Exception:
            pass
        return None

    # ---------------------------------- what the Configure Plot window is asked

    def styleCurves(self):
        """The traces of this panel hand styling may change."""
        return list(self.pgPlotWidget.getPlotItem().listDataItems())

    def styleText(self):
        """The plot item holding this panel's title and its two labels."""
        return self.pgPlotWidget.getPlotItem()

    def styleMargins(self):
        """The room between panels, which belongs to the window laying them out.

        Asked of the frame, because a panel has no margins of its own: a Table
        Plot View and a Stacked Plot View answer the grid their panels live in,
        and a figure of curves answers None -- it holds one plot, and a margin
        there is a strip of nothing between it and its own sliders. Refusing here
        instead would leave that section with no caller at all, since the window
        that used to answer it was the Profiles plugin's own grid.
        """
        asked = getattr(self._frame, 'styleMargins', None)
        return asked() if asked is not None else None

    def tracesForStyling(self):
        """[(treeNode, index, curve)] -- one quantity per panel, so one rank each."""
        node = getattr(self, 'treeNode', None)
        return [(node, index, curve)
                for index, curve in enumerate(self.curves())]

    # ------------------------- what the curve transforms ask of the panel

    def transformOf(self, curve):
        """The (factor, offset) this panel has on that curve, (1, 0) when none."""
        record = self._transforms.get(curve)
        return record.affine() if record is not None else (1.0, 0.0)

    def setTransform(self, curve, factor, offset):
        """Lay (factor, offset) on the values this curve was read with, and redraw.

        False when the curve is not one this panel drew.
        """
        record = self._transforms.get(curve)
        if record is None:
            return False
        record.set(factor, offset)
        record.drawInto(curve)
        return True

    def clearTransform(self, curve):
        """Take the transform off that curve, leaving the values the read left."""
        record = self._transforms.get(curve)
        if record is None:
            return False
        was = record.isTouched()
        record.clear()
        record.drawInto(curve)
        return was

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
        """(identity, name) of the abscissa the curve runs along.

        The identity is the one the curve figure uses -- `QVizCurveAbscissa` --
        rather than a key this panel spelled for itself, because the panel's
        window (a Stacked Plot View) stacks a quantity the read may carry
        **either** by walking the dynamic array **or** by slicing at a
        coordinate of its own, and both roads can run along the same clock:
        `alongTime` covers the walk, and `identityOf` covers the slice, since
        it answers `TIME` for a leaf axis that **is** a time base
        (`axis.is_time`, set by `QVizAxesSpec` from the coordinate's spelling)
        -- `flux_loop(i1).flux.time` and `bpol_probe(i1).field.time` on the
        reference case, both resolved by the read to `magnetics.time` (17 344
        samples): the curve figure of test_59 draws them as two traces, while
        the keying this method used to do refused the pair, "is read along
        time, not time" -- two raw coordinates, one clock, two keys, one name.

        Asked of the plan rather than of the node, because the strategy decides
        it: the same quantity is against its own coordinate in one window and
        against time in the next. The name comes with the identity
        (`describe`), and two different identities cannot agree on one --
        which is what keeps a refusal from spelling the same word twice.
        """
        if alongTime:
            # A scalar held by a dynamic array answers here: it has no axis of
            # its own, so nothing below may be asked of it.
            return TIME, describe(TIME)
        plotted = [axis for axis in axesSpec.axes if axis.origin == QVizAxis.LEAF]
        if not plotted:
            return (None, None)
        identity = identityOf(plotted[0])
        return identity, describe(identity)

    @staticmethod
    def axisName(axis):
        if axis.coordinate:
            return axis.coordinate.replace('/', '.').rsplit('.', 1)[-1]
        return 'dimension %d' % axis.level
