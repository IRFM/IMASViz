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
from imasviz.VizDataAccess.QVizCurveAbscissa import arraysLeftOut
from imasviz.VizDataAccess.QVizCurveAbscissa import choose as chooseAbscissa
from imasviz.VizDataAccess.QVizCurveAbscissa import describe as describeAbscissa
from imasviz.VizDataAccess.QVizCurveAbscissa import labelFor as abscissaLabel
from imasviz.VizDataAccess.QVizSlices import elementLabel
from imasviz.VizDataAccess.QVizTensorDataAccess import QVizTensorDataAccess
from imasviz.VizGUI.VizPlot.QVizCurveColors import penFor
from imasviz.VizGUI.VizPlot.QVizCurveErrors import QVizCurveErrors
from imasviz.VizGUI.VizPlot.QVizPlotStyling import QVizPlotStyling
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
        # Beside its abscissa, the other half of what a figure of curves *is*:
        # the arrays of structures it puts under a slider. Only a tensor puts an
        # array there, so this is empty until the figure is asked to explore one
        # -- and it grows with every tensor that joins: one array per slider,
        # and a slider moves only the curves of the array it names, so a tensor
        # of another array adds its own band beside the ones already there
        # instead of being refused (`_settleArrays`, `_pinning`).
        self.walkingArrays = frozenset()
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
        # The other line the manual documents on a plot display, *Configure Plot*.
        # The dialogue has been in the package since T32 and only the plots of the
        # Profiles plugin offered it, because its three questions were answered in
        # one place; this frame answers them on itself now, so the entry the manual
        # describes is on the menu of the window the manual describes it on.
        self.styling = QVizPlotStyling(self)
        self.styling.addMenuEntry(self.pgPlotWidget.getViewBox().menu)

        self.sliceControls = QVizSliceControls(self, foldable=True)
        # The read asks this widget for the indices of the axes a trace lets
        # move, so the controls and the numbers cannot be out of date with
        # respect to each other.
        self.sliceControls.changed.connect(self.refresh)

        self.keepCurveBox = QCheckBox('Keep this curve', self)
        self.keepCurveBox.toggled.connect(self._onKeepCurve)
        # Where the box is shown, whether it is enabled, and what its tooltip
        # says all follow from how many live curves the figure holds, answered
        # together so the three cannot drift apart.
        self._updateKeepBox()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.pgPlotWidget)
        layout.addWidget(self.sliceControls)
        layout.addWidget(self.keepCurveBox)

        if title:
            self.setWindowTitle(title)

    def liveCount(self):
        """How many curves still follow the sliders (the ones not frozen).

        *Keep this curve* is a question about that one, so the box answers from
        it rather than from the total, which also counts what was frozen.
        """
        return len([trace for trace in self._curves if not trace.isFrozen()])

    def _keepTooltip(self):
        """Why the box is the way it is, in the words the user reads on hover.

        Enabled: what the click does. Otherwise the reason it is off, said by
        name rather than left a greyed box nobody could ask.
        """
        live = self.liveCount()
        if live == 1:
            return ('Freeze the curve the sliders are moving at the indices it '
                    'stands on and start a new one there; uncheck to take the '
                    'frozen curve back out.')
        if live == 0:
            return ('No curve on this figure follows the sliders, so there is '
                    'nothing to keep.')
        return ('This figure holds ' + str(live) + ' curves following the '
                'sliders; keeping one would be ambiguous about which to freeze, '
                'so *Keep this curve* is off here.')

    def _updateKeepBox(self):
        """Show, enable, and explain the *Keep this curve* box, together.

        The box is shown on a tensor figure and enabled only while it holds
        exactly one live curve: that is the one case the box exists for, and
        the only one a keep is unambiguous in. One live curve survives a whole
        family of snapshots -- each keep freezes that one and hands back a live
        one -- so stacking keeps the box enabled; two curves added by the user
        are two live ones, and the box is refused in advance, with the tooltip
        saying why, rather than freezing the wrong one.
        """
        self.keepCurveBox.setVisible(self.exploresTensor)
        self.keepCurveBox.setEnabled(self.exploresTensor and self.liveCount() == 1)
        self.keepCurveBox.setToolTip(self._keepTooltip())

    def plot(self, treeNode, as_function_of_time=None, tensor=False,
             time_index=None, named_indices=None):
        """Add one quantity to the figure, along the abscissa the figure draws.

        `tensor` is the other representation of the same quantity: the arrays the
        tree already picked become sliders the user moves, instead of staying at
        the element the tree is standing on. The default -- an element -- puts a
        slider on the leaf's own coordinates only and writes the arrays in the
        legend.

        `time_index` pins the element of the dynamic time array a profile is
        read at: a caller that asks "the profile at the 42nd slice" resolves
        the time value to an index elsewhere and passes it down; the read takes
        it verbatim, so a slice the tree is not standing on is still drawn.
        Ignored when the curve draws the time axis itself, because a pin and a
        time history contradict -- and the caller that would ask for both
        refuses before reaching here.

        The first curve settles the figure's abscissa; after that the figure
        decides it, and a quantity that cannot be read along it is refused by
        name -- both the abscissa and what the quantity could be read along.
        Before that, each trace asked for itself: measured on a figure opened on
        `equilibrium.time_slice[i].profiles_1d.f`, the first curve ran against
        `psi` (101 points) and the second, `.psi`, ran against its index (101
        points) and rewrote the figure's single bottom label.

        `named_indices` is the axes the caller fixed to specific indices, by key:
        a named axis the figure already holds a curve of (a named element drawn
        on top of this leaf) is a different element of the array, and is frozen
        at its own index rather than riding the leaf's shared control -- which
        reads it everywhere the control sits, the "psi slices of one profile all
        collapse to the last one named" bug. The figure's one element of a leaf
        keeps the control, so it still carries its slider.

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
        self._settleArrays(axesSpec, abscissa, tensor)

        axesSpec, timeAxis, alongTime, plotted = access.plan(treeNode, self,
                                                             as_function_of_time,
                                                             abscissa)
        pinned = [axis for position, axis in enumerate(axesSpec.axes)
                  if position not in plotted]
        named = dict(named_indices or {})
        # A named axis the figure already holds a curve of (a named element on
        # top of this leaf) is a different element of that array: frozen at its
        # own index, not a view of the one on the shared control (which reads it
        # everywhere the control sits -- psi slices of one profile all reading
        # the last index named). The figure's one element of a leaf keeps the
        # control, so it still carries its slider.
        sibling = bool(named) and self.hasCurveOf(treeNode)
        fixed, movable = self._pinning(pinned, tensor, self.walkingArrays,
                                       named=named, sibling=sibling)
        slices = self._readSlices(fixed, movable)
        # A pinned time slice is the caller's explicit choice, and it must
        # actually move the read: the read's own rule is that a slice for the
        # dynamic axis (built from this figure's controls, or from the element
        # the tree stands on) wins over a bare index. So the pin is put into
        # the mapping itself, for the axis the read takes it from. A curve
        # that draws the time axis does not reach here with a pin, so the
        # guard is defensive.
        if time_index is not None and timeAxis is not None and not alongTime:
            slices = dict(slices or {})
            slices[timeAxis.key()] = int(time_index)

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
        self.addSlices(self._controlsFor(access, treeNode, movable, tensor,
                                         as_function_of_time, abscissa))
        # A quantity added to a figure already showing bars or a band joins them:
        # the entries answer for every curve on the figure, not for the ones that
        # happened to be there when they were clicked. `refresh` draws only if
        # something is drawn, so on the ordinary case this changes nothing.
        self.errors.refresh()
        # The box answers from how many live curves are on screen, so it must be
        # re-asked after this call's own curves are laid down -- a second curve
        # added here is exactly the case that must grey it out.
        self._updateKeepBox()
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
            try:
                x, y = self.accessFor(trace.treeNode).GetSignal(
                    treeNode=trace.treeNode, plotWidget=self,
                    as_function_of_time=trace.asFunctionOfTime, slices=slices,
                    abscissa=trace.abscissa)
            except ValueError as e:
                # A slider moved an index past the end of this trace's array:
                # the read refuses it by name. Naming it here, instead of letting
                # the Qt slot dispatcher print the whole traceback, is what the
                # failure of a slider move costs; the other traces still refresh.
                logging.getLogger(self.logChannel()).error(str(e))
                continue
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
        move, check, move. The figure must hold exactly one live curve: with
        more than one, "keep" would be ambiguous about which to freeze, so it is
        refused by name and the box is greyed rather than freezing the last.
        Returns how many curves are kept.
        """
        live = [trace for trace in self._curves if not trace.isFrozen()]
        if not live:
            raise ValueError('Nothing to keep on this figure: no curve follows a '
                             'slider.')
        if len(live) > 1:
            raise ValueError('This figure holds ' + str(len(live)) +
                             ' curves following the sliders, so keeping one would '
                             'be ambiguous about which curve to freeze.')
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
        self._updateKeepBox()
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

    def hasCurveOf(self, treeNode):
        """True when this figure already holds a curve of this leaf.

        The leaf is the quantity, so a curve of this node at another index is
        already here: adding a named element of the same node is then a different
        element of that array (frozen at its index), not another view of the one
        on the shared control, which reads it at the first element's index. A
        curve of a *different* leaf is not a sibling -- its leaves share a control
        and the figure sweeps both, the comparable case this must not freeze.
        """
        from imasviz.VizDataAccess.QVizNodePlotting import QVizNodePlotting
        try:
            path = QVizNodePlotting(treeNode).path()
        except Exception:
            return any(trace.treeNode is treeNode for trace in self._curves)
        for trace in self._curves:
            if QVizNodePlotting(trace.treeNode).path() == path:
                return True
        return False

    def errorQuantities(self):
        """Which drawn curve came from which node, as [(node, curve)].

        The error bars and the confidence band are drawn per curve and read from
        that curve's node, and on a figure holding several quantities this is the
        only place holding the pairing.
        """
        return [(trace.treeNode, trace.curve) for trace in self._curves]

    # ---------------------------------- what the Configure Plot window is asked

    def styleCurves(self):
        """The traces hand styling may change, in the order they were drawn.

        `listDataItems()` answers the `PlotDataItem`s of the plot and none of what
        this frame adds to it -- error bars, confidence band, legend -- so no list
        of item types to skip is needed to keep the decorations out of the rows.
        """
        return list(self.pgPlotWidget.getPlotItem().listDataItems())

    def styleText(self):
        """The plot item holding this figure's title and its two labels."""
        return self.pgPlotWidget.getPlotItem()

    def styleMargins(self):
        """None: the margins section belongs to a window that lays panels out.

        A figure of curves has one plot over its own controls; a margin there is a
        strip of nothing between the plot and its sliders, not room between panels.
        """
        return None

    def tracesForStyling(self):
        """[(treeNode, index, curve)]; the index ranks a trace among *its* quantity's.

        A session names a trace by the quantity it came from and its rank among the
        traces that quantity drew, because a figure gains and loses quantities
        while a file sits in a folder: a rank over the whole figure would move when
        somebody adds a curve, and style the wrong trace.
        """
        ranks = {}
        entries = []
        for trace in self._curves:
            index = ranks.get(trace.treeNode, 0)
            ranks[trace.treeNode] = index + 1
            entries.append((trace.treeNode, index, trace.curve))
        return entries

    def sliceKeys(self):
        return list(self._slices)

    def addSlices(self, slices):
        for sl in slices:
            if sl.key not in self._slices:
                self._slices[sl.key] = sl
        self.sliceControls.setSlices(list(self._slices.values()))

    def accepts(self, treeNode, tensor=False):
        """Whether this quantity may be drawn here -- the gate the menus ask.

        The abscissa: a curve figure has one bottom label, and
        `QVizCurveAbscissa.choose` answers whether the quantity can be read along
        it. The arrays are not asked here any more, for either representation:
        the sliders are per array, so a tensor carries the slider of the arrays
        it leaves out beside whatever the figure already holds, and an element
        is frozen on the arrays it stands on -- the rule `plot` applies, and the
        only refusal left is an abscissa this quantity cannot run along.

        This answers without reading anything, so a right click can ask it of
        every open figure.
        """
        axesSpec = QVizAxesSpec.fromTreeNode(treeNode)
        return chooseAbscissa(axesSpec, self.abscissa) is not None

    def _settleArrays(self, axesSpec, abscissa, tensor):
        """Which arrays this figure walks, with this trace added to it.

        A tensor puts every array it leaves out under a slider, and the figure
        holds the union of the arrays its tensors walk: a second tensor of
        another array adds that array's slider beside the first, and a slider
        walks only the curves of the array it names -- which is what `_pinning`
        decides per trace, and what `refresh` re-reads per curve. The one that
        settles it first is only the one whose arrays the figure holds before
        any other: a figure that holds none takes the arrays the first tensor
        asks, exactly as it did when the band was one for the whole figure.
        An element adds no array: it is asked as one element, and it stays
        where the tree stands on it -- `_pinning` freezes it on the figure's
        band when there is one, and leaves it pinned on its own when there is
        not yet.
        """
        if tensor:
            self.walkingArrays = self.walkingArrays \
                | arraysLeftOut(axesSpec, abscissa)

    @staticmethod
    def _pinning(pinned, tensor, walkingArrays, named=None, sibling=False):
        """Split the axes a trace leaves out into its own and the figure's.

        An array of structures the tree is standing on belongs to the identity of
        the element the user asked for: another curve of the same array in the
        same figure is a different element, so the two cannot share a control --
        measured, sharing one read the second element at the first one's index. A
        coordinate of the leaf is not: two quantities of one array are sampled on
        the same grid, and one control moving both is what makes them comparable.
        Under `tensor` the array itself is the question, so it goes under a
        slider too.

        An element asked into a figure that *is* walking arrays is the exception:
        there the sliders answer the tensor, and the curve the user asked for as
        one element must not move under them -- it is frozen on every axis it
        leaves out, its own coordinate included, and its legend spells the whole
        index set.

        `named` is the axes the caller fixed to specific indices and `sibling`
        whether the figure already holds a curve of this leaf: a NAMED element on
        top of a curve of the same leaf is one of the different elements above,
        and is frozen at its named index (a shared control would read it at the
        first one's -- the bug); the figure's one element of a leaf stays on the
        control, so a figure of a single element still carries its slider.
        """
        named = dict(named or {})
        fixed = {}
        movable = []
        frozen = bool(walkingArrays) and not tensor
        for axis in pinned:
            if tensor:
                movable.append(axis)
            elif axis.origin == QVizAxis.LEAF and not frozen:
                # A leaf's own coordinate: a control of the figure. If the
                # caller NAMED it and the figure already holds a curve of this
                # leaf (a sibling: a different element of the same array), this
                # element is frozen at its named index -- a shared control would
                # read it at the first element's index, the "psi slices of one
                # profile collapse to the last one named" bug. The sole element
                # of the leaf keeps the control (a slider to sweep), and a leaf
                # no index named still sweeps from the tree's element.
                if (axis.key() in named) and sibling:
                    fixed[axis.key()] = named[axis.key()]
                else:
                    movable.append(axis)
            else:
                # A non-leaf axis (an array of structures) is not a slider to
                # sit on: it names a family member, the one the path fixed.
                # Asking the caller's index for a DIFFERENT member is a
                # different element, not a position on this one -- it is left
                # fixed at the path's index, and the caller's `setIndex` for it
                # fails, which is the genuine refusal (a different member of the
                # family, by index) rather than a silent move to that member.
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

    def _controlsFor(self, access, treeNode, movable, tensor,
                     as_function_of_time, abscissa):
        """The sliders this quantity earns, with the lengths the values answer.

        `slicesFor` answers every axis the read leaves out, because a leaf axis
        length exists only in the values; a control is then kept for the axes this
        trace actually follows, which is what makes an element different from a
        tensor: the element fixes the arrays the tree stands on and keeps only its
        own coordinate, while an element frozen by a tensor figure follows nothing
        and gets no control at all -- its index set is in the legend, and no
        slider may move a curve the user asked for as one element.

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
        movableKeys = {axis.key() for axis in movable}
        return [sl for sl in slices if sl.key in movableKeys]

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
