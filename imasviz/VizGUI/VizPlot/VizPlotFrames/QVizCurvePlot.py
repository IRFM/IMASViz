# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""A curve figure that says which element of which array each curve came from.

Written against the axes model and the tensor read rather than against the
legacy curve window, for the reasons that window and its command state: a curve
draws one axis, so every other axis of the quantity is fixed somewhere, and a
figure that does not say where it fixed them is showing numbers nobody can
attribute.

Two questions meet on this widget, and they differ in where the indices come
from:

    an element of a tensor    the tree is already standing on 'flux_loop[3]', so
                              that array is fixed for good and spelled out in the
                              legend; only the leaf's own coordinates get a slider
    the tensor itself         "Explore this tensor": every axis the curve leaves
                              out gets a slider, opened where the tree was
                              standing, and the curve on screen follows them.
                              Checking *Keep this curve* freezes that curve at
                              the indices it stands on and starts a new one, so a
                              family of elements piles up on one abscissa

What used to happen was neither. The figure held one index set per *axis*, shared
by every curve on it, and the read took it from there -- so two elements of one
array asked in the same figure were read at the same element. Measured on WEST
54924 with `magnetics.flux_loop[i].flux.data`, which holds 17 elements of 17 344
samples each: plotting element 0 then element 1 answered two curves with
identical samples, and the legend spelled both `flux_loop[i]`, so nothing on
screen said which element either came from, let alone that they were the same
element twice. A trace carries its own index set now.

The loop this closes:

    plot(node)   ask the read what it drew, plot it, then ask the same read which
                 axes it fixed -- a slider for each one the trace lets move
    controls     moving one emits changed
    refresh()    re-read the traces that follow those controls, in place

Nothing here decides which axes are plotted: the access does, and the controls
and the axis labels both come out of that one answer.
"""

import logging

import pyqtgraph as pg

from PySide6.QtWidgets import QCheckBox, QVBoxLayout, QWidget

from imasviz.VizDataAccess.QVizAxesSpec import QVizAxesSpec, QVizAxis
from imasviz.VizDataAccess.QVizCurveAbscissa import abscissae
from imasviz.VizDataAccess.QVizCurveAbscissa import choose as chooseAbscissa
from imasviz.VizDataAccess.QVizCurveAbscissa import describe as describeAbscissa
from imasviz.VizDataAccess.QVizCurveAbscissa import labelFor as abscissaLabel
from imasviz.VizDataAccess.QVizSlices import elementLabel
from imasviz.VizDataAccess.QVizTensorDataAccess import QVizTensorDataAccess
from imasviz.VizGUI.VizPlot.QVizCurveColors import penFor
from imasviz.VizGUI.VizPlot.QVizCurveErrors import QVizCurveErrors
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizSliceControls import QVizSliceControls


class QVizTrace:
    """One drawn row, and how it is pinned.

    `fixed` is {axis key: index} for the axes this row pins by itself: the arrays
    of structures the tree was standing on, and for a curve frozen by *Keep this
    curve* every axis it was frozen at. `movable` is the axes whose index is taken
    afresh from the figure's controls at every re-read -- a coordinate two
    quantities share, or, under a tensor exploration, every axis left out.

    A row with no movable axis is frozen: keeping it is what makes it comparable
    with the one still moving, so it is not read again at all.
    """

    def __init__(self, treeNode, row, curve, asFunctionOfTime, fixed, movable,
                 pinned, suffix, legend=None, abscissa=None):
        self.treeNode = treeNode
        self.row = row
        self.curve = curve
        self.asFunctionOfTime = asFunctionOfTime
        # The abscissa this row was read along. A slider re-reads a row, and it
        # has to re-read it along the axis the figure draws -- not along whatever
        # the quantity's own default would have picked, which is a different
        # answer for a quantity in a dynamic array.
        self.abscissa = abscissa
        self.fixed = fixed
        self.movable = movable
        # Every axis this row leaves out, movable or not: what the legend spells
        # the path with.
        self.pinned = pinned
        self.suffix = suffix
        self.legend = legend

    def isFrozen(self):
        return not self.movable

    def __repr__(self):
        return '<QVizTrace %s row=%d fixed=%s movable=%d>' % (
            self.treeNode.getName(), self.row, sorted(self.fixed),
            len(self.movable))


class QVizCurvePlot(QWidget):
    """Curves of one shot view, each drawn at the index set it was asked at."""

    def __init__(self, parent=None, title=''):
        super().__init__(parent)

        # The axis this figure draws along, as `QVizCurveAbscissa` spells its
        # identity -- None until the first curve answers. A curve figure has one
        # abscissa, so the first curve settles it and every later one is read
        # along it: the label under the figure and the numbers under that label
        # then come from one answer. The frame used to carry a `plotAxis` string
        # ('DEFAULT' on every curve frame) that a node read as a question about
        # itself, which is how a figure ended up labelled by whichever curve was
        # added last.
        self.abscissa = None
        # One QVizTrace per drawn row: the node it came from, which row of that
        # node's answer it is, how it was asked for, and the indices it pins. A
        # quantity held by a static array read at several indexes gives several
        # rows, and each has to be updated with its own row on a slice change.
        self._curves = []
        # {axis key: QVizSlice} across every quantity on the figure, in the order
        # the axes first appeared. Merged rather than replaced, because an axis
        # two quantities share is one control: the index that pins one pins the
        # other. That is what an exploration wants and what an element does not,
        # which is why an element pins its arrays by itself instead -- QVizTrace.
        self._slices = {}
        # Whether this figure was asked to explore a tensor: the sliders over the
        # arrays and the *Keep this curve* box belong to that question only.
        self.exploresTensor = False
        # Curves frozen by *Keep this curve*, in the order they were frozen.
        self._kept = []

        self.pgPlotWidget = pg.PlotWidget(self)
        self.pgPlotWidget.setObjectName('curvePlot')
        self.pgPlotWidget.addLegend()

        # The error bars and the confidence band of the curves this figure drew.
        # pyqtgraph builds the view box's menu at construction -- measured: `View
        # All`, `X axis`, `Y axis`, `Mouse Mode`, and the scene adds `Export...`
        # -- and the three lines the manual names go after those. They are added
        # here rather than in a subclass because the menu is an instance's own:
        # unlike a class attribute, nothing here reaches another figure.
        # `self` is handed over, not `self.errorQuantities`: a bound method would
        # be a reference back to this frame, and the cycle it makes is what makes
        # the frame die inside the cyclic collector rather than at its refcount
        # -- which on this Qt stack is a segfault, not a leak. See QVizCurveErrors.
        self.errors = QVizCurveErrors(self.pgPlotWidget.getViewBox(), self)
        self.errors.addMenuEntries(self.pgPlotWidget.getViewBox().menu)

        self.sliceControls = QVizSliceControls(self, foldable=True)
        # The read asks this widget for the indices of the axes a trace lets
        # move, so the controls and the numbers cannot be out of date with
        # respect to each other.
        self.sliceControls.changed.connect(self.refresh)

        self.keepCurveBox = QCheckBox('Keep this curve', self)
        self.keepCurveBox.setVisible(False)
        self.keepCurveBox.setToolTip(
            'Freeze the curve the sliders are moving at the indices it stands on '
            'and start a new one there; uncheck to take the frozen curve back out')
        self.keepCurveBox.toggled.connect(self._onKeepCurve)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.pgPlotWidget)
        layout.addWidget(self.sliceControls)
        layout.addWidget(self.keepCurveBox)

        if title:
            self.setWindowTitle(title)

    def plot(self, treeNode, as_function_of_time=None, tensor=False):
        """Add one quantity to the figure, along the abscissa the figure draws.

        `tensor` is the other representation of the same quantity: the arrays the
        tree already picked become sliders the user moves, instead of staying at
        the element the tree is standing on. The default -- an element -- puts a
        slider on the leaf's own coordinates only and writes the arrays in the
        legend.

        The first curve settles the figure's abscissa; after that the figure
        decides it, and a quantity that cannot be read along it is refused by
        name -- both the abscissa and what the quantity could be read along.
        Before that, each trace asked for itself: measured on a figure opened on
        `equilibrium.time_slice[i].profiles_1d.f`, the first curve ran against
        `psi` (101 points) and the second, `.psi`, ran against its index (101
        points) and rewrote the figure's single bottom label.

        Returns the number of rows drawn.
        """
        access = self.accessFor(treeNode)
        axesSpec = QVizAxesSpec.fromTreeNode(treeNode)
        abscissa = chooseAbscissa(axesSpec, self.abscissa, as_function_of_time)
        if abscissa is None:
            options = abscissae(axesSpec)
            raise ValueError('"' + self.dataPathOf(treeNode) + '" cannot be read '
                             'along ' + describeAbscissa(self.abscissa) +
                             ', which this figure draws; it runs along ' +
                             (' or '.join(describeAbscissa(option)
                                          for option in options)
                              if options else 'nothing of its own') + '.')
        if self.abscissa is None:
            self.abscissa = abscissa

        axesSpec, timeAxis, alongTime, plotted = access.plan(treeNode, self,
                                                             as_function_of_time,
                                                             abscissa)
        pinned = [axis for position, axis in enumerate(axesSpec.axes)
                  if position not in plotted]
        fixed, movable = self._pinning(pinned, tensor)
        slices = self._readSlices(fixed, movable)

        x, y = access.GetSignal(treeNode=treeNode, plotWidget=self,
                                as_function_of_time=as_function_of_time,
                                slices=slices, abscissa=abscissa)
        if x.size == 0 or y.size == 0:
            # Drawing an empty curve silently is the failure this path exists to
            # remove: the axes were pinned somewhere and nothing said where, so
            # an empty result reads as an empty quantity.
            raise ValueError('Nothing to plot for "' + self.dataPathOf(treeNode) +
                             '": no values along the plotted axis.')

        # One colour per trace, in the order the traces were laid down. Asked of
        # the module rather than kept here because the cycle is what makes the
        # palette survive a selection longer than it is long, and because
        # pyqtgraph has no cycle of its own to fall back on: a curve drawn without
        # a pen is `(200, 200, 200)`, measured, twice over on one figure.
        self.exploresTensor = self.exploresTensor or tensor
        self.keepCurveBox.setVisible(self.exploresTensor)
        label = elementLabel(treeNode, pinned, slices)
        for row in range(y.shape[0]):
            # Several rows of one quantity are several traces, and the path alone
            # would name them identically in the legend the figure draws.
            suffix = '' if y.shape[0] == 1 else '[%d]' % row
            curve = self.pgPlotWidget.plot(x[0], y[row], name=label + suffix,
                                           pen=penFor(len(self._curves)))
            self._curves.append(QVizTrace(treeNode, row, curve,
                                          as_function_of_time, fixed, movable,
                                          pinned, suffix,
                                          self.legendLabelFor(label + suffix),
                                          abscissa))

        self.setAbscissaLabel(axesSpec)
        self.setQuantityLabel(treeNode)
        self.addSlices(self._controlsFor(access, treeNode, pinned, tensor,
                                         as_function_of_time, abscissa))
        # A quantity added to a figure already showing bars or a band joins them:
        # the entries answer for every curve on the figure, not for the ones that
        # happened to be there when they were clicked. `refresh` draws only if
        # something is drawn, so on the ordinary case this changes nothing.
        self.errors.refresh()
        return y.shape[0]

    def refresh(self):
        """Re-read every curve that follows a slider, updating each in place.

        Not a re-plot: rebuilding the curves would rebuild the controls the user
        is still holding, and move the colours and legend entries under their
        hand. A frozen curve is skipped: it was kept precisely so that it stops
        moving while another one is looked at.
        """
        for trace in self._curves:
            if trace.isFrozen():
                continue
            slices = self._readSlices(trace.fixed, trace.movable)
            x, y = self.accessFor(trace.treeNode).GetSignal(
                treeNode=trace.treeNode, plotWidget=self,
                as_function_of_time=trace.asFunctionOfTime, slices=slices,
                abscissa=trace.abscissa)
            if y.shape[0] > trace.row and x.shape[0] > 0:
                trace.curve.setData(x[0], y[trace.row])
            else:
                trace.curve.setData([], [])
            # A curve whose sliders moved is not the element the figure opened
            # on: the legend has to say the element it is now.
            if trace.legend is not None:
                trace.legend.setText(self.labelOf(trace, slices))
        # Bars and bands are read off the samples, so they move with them: a bar
        # left over the slice the curve no longer draws is not stale, it is wrong.
        self.errors.refresh()
        return self.sliceControls.indices()

    def keepCurve(self):
        """Freeze the curve the sliders drive, at the indices it stands on.

        The frozen curve keeps those indices and stops answering the sliders; a
        new curve starts at the same place so the figure still shows one that
        moves. That is how a family of elements piles up on one abscissa: check,
        move, check, move. Returns how many curves are kept.
        """
        live = [trace for trace in self._curves if not trace.isFrozen()]
        if not live:
            raise ValueError('Nothing to keep on this figure: no curve follows a '
                             'slider.')
        trace = live[-1]
        trace.fixed = self._readSlices(trace.fixed, trace.movable)
        trace.movable = []
        if trace.legend is not None:
            trace.legend.setText(self.labelOf(trace, trace.fixed))
        self._kept.append(trace)
        self.plot(trace.treeNode, as_function_of_time=trace.asFunctionOfTime,
                  tensor=True)
        return len(self._kept)

    def dropKeptCurve(self):
        """Take back out the curve that was kept last. Returns how many are left."""
        if not self._kept:
            raise ValueError('Nothing to take back: no curve is kept on this figure.')
        trace = self._kept.pop()
        self._curves.remove(trace)
        # Removing the item takes its legend entry with it; a curve left in the
        # plot item while the figure forgets it keeps drawing a trace nobody can
        # move or name any more.
        self.pgPlotWidget.removeItem(trace.curve)
        return len(self._kept)

    def keptCount(self):
        return len(self._kept)

    def _onKeepCurve(self, checked):
        """The box the user checks to keep a curve and unchecks to drop one.

        The one refusal here is unchecking with nothing kept: the box goes back to
        where it was, because the failure of the click is not something the user
        can read out of a traceback printed by a Qt slot.
        """
        try:
            if checked:
                self.keepCurve()
            else:
                self.dropKeptCurve()
        except ValueError as e:
            logging.getLogger(self.logChannel()).error(str(e))
            self.keepCurveBox.blockSignals(True)
            self.keepCurveBox.setChecked(not checked)
            self.keepCurveBox.blockSignals(False)

    def curveCount(self):
        return len(self._curves)

    def isDrawing(self):
        return bool(self._curves)

    def curves(self):
        return [trace.curve for trace in self._curves]

    def traces(self):
        return list(self._curves)

    def errorQuantities(self):
        """Which drawn curve came from which node, as [(node, curve)].

        The error bars and the confidence band are drawn per curve and read from
        that curve's node, and on a figure holding several quantities this is the
        only place holding the pairing.
        """
        return [(trace.treeNode, trace.curve) for trace in self._curves]

    def sliceKeys(self):
        return list(self._slices)

    def addSlices(self, slices):
        for sl in slices:
            if sl.key not in self._slices:
                self._slices[sl.key] = sl
        self.sliceControls.setSlices(list(self._slices.values()))

    @staticmethod
    def _pinning(pinned, tensor):
        """Split the axes a trace leaves out into its own and the figure's.

        An array of structures the tree is standing on belongs to the identity of
        the element the user asked for: another curve of the same array in the
        same figure is a different element, so the two cannot share a control --
        measured, sharing one read the second element at the first one's index. A
        coordinate of the leaf is not: two quantities of one array are sampled on
        the same grid, and one control moving both is what makes them comparable.
        Under `tensor` the array itself is the question, so it goes under a
        slider too.
        """
        fixed = {}
        movable = []
        for axis in pinned:
            if tensor or axis.origin == QVizAxis.LEAF:
                movable.append(axis)
            else:
                fixed[axis.key()] = axis.index
        return fixed, movable

    def _readSlices(self, fixed, movable):
        """{axis key: index} for one read: what the trace fixes, plus the sliders.

        Handed to the read explicitly rather than left to it. `GetSignal` falls
        back on this figure's controls, whose index set belongs to whatever moved
        them last, and that is how the second element of an array ended up read at
        the first element's index.
        """
        chosen = self.sliceControls.indices()
        slices = dict(fixed)
        for axis in movable:
            index = chosen.get(axis.key())
            if index is None:
                index = axis.index
            slices[axis.key()] = 0 if index is None else int(index)
        return slices

    def _controlsFor(self, access, treeNode, pinned, tensor,
                     as_function_of_time, abscissa):
        """The sliders this quantity earns, with the lengths the values answer.

        `slicesFor` answers every axis the read leaves out, because a leaf axis
        length exists only in the values; the element representation keeps the
        arrays of structures out of it, since they are fixed and the legend says
        where.

        The abscissa goes to `slicesFor` with the rest, because which axes are
        left out depends on it: the same quantity offers a coordinate slider on a
        figure drawn against time and a time-slice slider on one drawn against
        that coordinate.
        """
        slices = access.slicesFor(treeNode, plotWidget=self,
                                  as_function_of_time=as_function_of_time,
                                  abscissa=abscissa)
        if tensor:
            return slices
        movable = {axis.key() for axis in pinned if axis.origin == QVizAxis.LEAF}
        return [sl for sl in slices if sl.key in movable]

    def labelOf(self, trace, slices):
        return elementLabel(trace.treeNode, trace.pinned, slices) + trace.suffix

    def legendLabelFor(self, name):
        """The legend label pyqtgraph just made for one curve, or None.

        Kept so the label of a curve whose sliders move can follow them: a legend
        naming the element the figure opened on is wrong once the user moved one.
        Measured on pyqtgraph 0.13.7, `Legend.item(curve)` answers None for the
        `PlotDataItem` a `plot()` call hands back -- the entry is registered under
        the curve item built inside it -- so the entry is taken where it is put:
        last in the legend, matched on the text asked for so that a curve which
        drew no label is not credited with the previous curve's.
        """
        legend = self.pgPlotWidget.getPlotItem().legend
        if legend is None or not legend.items:
            return None
        _, text = legend.items[-1]
        return text if text.text == name else None

    def logChannel(self):
        """The log panel of the shot view the figure's curves came from."""
        for trace in reversed(self._curves):
            uri = getattr(trace.treeNode.getDataSource(), 'uri', None)
            if uri:
                return uri
        return 'IMASViz'

    def accessFor(self, treeNode):
        return QVizTensorDataAccess(treeNode.getDataSource())

    def dataPathOf(self, treeNode):
        path = treeNode.getParametrizedDataPath()
        return path if path else treeNode.getName()

    def setAbscissaLabel(self, axesSpec):
        """Label the abscissa from the abscissa the figure settled on.

        Asked with the abscissa rather than with the answer to "did the read walk
        the dynamic array", because those are not the same question: a quantity
        whose own coordinate *is* a time base is sliced at one element of a static
        array and still runs along the clock, and labelling it `time[s]` is what
        the numbers say.

        Set from the figure, not from the last trace: measured before, a figure
        opened on `profiles_1d.f` was labelled `psi`, and adding `.psi` to it
        relabelled the same axis `dimension 1` -- under a curve nobody had asked
        for, against numbers that had never been taken on that axis.
        """
        name, units = abscissaLabel(axesSpec, self.abscissa)
        if name:
            self.pgPlotWidget.setLabel('bottom', name, units=units)

    def setQuantityLabel(self, treeNode):
        """Label the ordinate with the quantity of this trace, unit and all."""
        quantity = treeNode.getName() or ''
        units = treeNode.getUnits()
        if units:
            quantity += '[' + units + ']'
        self.pgPlotWidget.setLabel('left', quantity)
