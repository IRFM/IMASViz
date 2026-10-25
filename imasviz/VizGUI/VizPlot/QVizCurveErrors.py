# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Error bars and confidence bands for the curves a figure drew.

The manual promises three lines in the right-click menu of a plot -- *Show/Hide
error bars*, *Show error bars (with slicing)*, *Show/Hide confidence bands* --
"if data for fields error_upper and/or error_lower are available". Until now only
the Profiles plugin's plots answered them, from a copy of this behaviour written
inside the plugin's view box; the frames the *Plot selected nodes to* entries
draw answer pyqtgraph's own four lines plus the scene's `Export...` and nothing
else -- measured on a drawn curve: `View All`, `X axis`, `Y axis`, `Mouse Mode`,
`Export...`.

This is that behaviour once, so a frame can bind it without copying it. All it
needs from whoever asks are the two things it cannot know itself: the view box to
draw into, and which curve came from which node.

What the reference case (WEST 54924 run 0, dictionary 3.35.0) answers, measured
before this was written:

* of the **6058** signal nodes of `magnetics` occurrence 0, **1681** carry both an
  `_error_upper` and an `_error_lower` sibling in the dictionary, **4377** carry
  neither, and **none** carries only one. So "one sibling and not the other" is
  not a dictionary shape -- it is this case leaving a sibling unfilled, which is
  what reading `magnetics/flux_loop(0)/flux/data` gives: an upper of **17344**
  values and **no** lower. Both cases draw symmetrically, which is what the known
  side of an error means when the other is not held;
* a bar over those 17 344 points would be **0,0042** s wide -- the span over the
  sample count -- and is drawn **0,072851** s wide, the lower bound `span/1000`.
  A bar one sample wide on that record is invisible, which is why the bound is
  there;
* one `ErrorBarItem` over 17 344 points costs **0,016 s**, a band -- two borders
  and the fill between them, three items -- **0,216 s**;
* slicing draws every Nth sample: over 17 344 samples at N = **3** that is
  **5782** bars. The copy asked `x[0:len(x)-1:N]`, which answers **5781** -- it
  drops the last sample, and with it the end of the curve.
"""

import logging
import weakref

import numpy as np
import pyqtgraph as pg

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QInputDialog

# The three lines, spelled once: the frame's menu and the plugin's menu say the
# same thing because they read the same words.
ERROR_BARS = 'Show/Hide error bars'
ERROR_BARS_SLICED = 'Show error bars (with slicing)'
CONFIDENCE_BANDS = 'Show/Hide confidence bands'

STEP_TITLE = 'Enter a step value for slicing'
STEP_LABEL = 'Step:'
DEFAULT_STEP = 10


class QVizCurveErrors:
    """The error bars and the confidence band of one figure's curves.

    Arguments:
        viewBox (pg.ViewBox) : where the items are drawn -- the figure's own.
        owner   (obj)        : the figure, asked when needed for
                               `errorQuantities()`, the `[(treeNode,
                               pg.PlotDataItem), ...]` pairing -- one entry per
                               drawn curve. Who keeps that pairing is the
                               caller's business: the curve frame reads it back
                               off the curves it drew, the plugin off the map its
                               view box maintains.
    """

    def __init__(self, viewBox, owner):
        self.viewBox = viewBox
        # Held weakly, and that is a load-bearing detail rather than tidiness:
        # the figure owns this object, and this object has to ask the figure
        # which curve came from which node. Keeping `owner.errorQuantities` -- a
        # bound method, so a strong reference back -- makes a cycle the collector
        # has to break, and a Qt widget freed by the cyclic collector rather than
        # by its refcount reaching zero is freed in the middle of a paint queue.
        # Measured on this stack: with the bound method held,
        # `tests/test_44_plot_frame_ownership.py` died 2 runs out of 2 with
        # `Fatal Python error: Segmentation fault` inside `gc.collect()`; with
        # anything that is not a reference back, the same file passes 2 out of 2.
        self._owner = weakref.ref(owner)
        # What is drawn right now, and at which step: `refresh` needs both to
        # know that it has to draw anything at all after the frame moved a curve
        # out from under its bars.
        self.bars = []
        # One entry per band, each a (upper, lower, fill) triple -- a flat list
        # would lose which items belong to which quantity.
        self.bands = []
        self.step = None

    def quantities(self):
        """The curves of the figure and the node each came from.

        Empty once the figure is gone: an owner that died has no curve left to
        put a bar on, and this is the answer that keeps a late `refresh` from
        reaching a figure that is not there any more.
        """
        owner = self._owner()
        return owner.errorQuantities() if owner is not None else []

    # ------------------------------------------------------------------- menu

    def addMenuEntries(self, menu):
        """The three lines the manual names, onto that menu."""
        menu.addSeparator()
        for title, slot in [(ERROR_BARS, self.toggleErrorBars),
                            (ERROR_BARS_SLICED, self.toggleSlicedErrorBars),
                            (CONFIDENCE_BANDS, self.toggleConfidenceBands)]:
            action = QAction(title, menu)
            action.triggered.connect(slot)
            menu.addAction(action)

    # ---------------------------------------------------------------- actions

    def toggleErrorBars(self):
        """Bars over every sample, or none -- what a second click answers."""
        if self.bars:
            self.removeBars()
            return False
        self.showErrorBars(step=1)
        return True

    def toggleSlicedErrorBars(self):
        """Bars over every Nth sample, N asked of the user.

        The step is asked here rather than remembered from the last answer: the
        manual says the value is asked, and redrawing bars the user never sized
        is worse than asking twice. A refused question changes nothing.
        """
        step, accepted = QInputDialog.getInt(None, STEP_TITLE, STEP_LABEL,
                                             value=DEFAULT_STEP, minValue=1)
        if not accepted:
            return False
        self.removeBars()
        self.showErrorBars(step=step)
        return True

    def toggleConfidenceBands(self):
        """A band around every curve that can carry one, or none."""
        if self.bands:
            self.removeBands()
            return False
        self.showConfidenceBands()
        return True

    def showErrorBars(self, step=1):
        """Draw bars at that step over whatever is drawn now."""
        self.removeBars()
        for node, curve in self.quantities():
            bar = self.errorBarFor(node, curve, step)
            if bar is not None:
                self.viewBox.addItem(bar)
                self.bars.append(bar)
        self.step = step
        return len(self.bars)

    def showConfidenceBands(self):
        """Draw one band per curve that can carry one."""
        self.removeBands()
        for node, curve in self.quantities():
            band = self.confidenceBandFor(node, curve)
            if band:
                self.bands.append(band)
        return len(self.bands)

    def refresh(self):
        """Draw again what was drawn, after the curves under it changed.

        A frame moving a slice control re-reads its curves; bars left where the
        old samples were are not out of date, they are wrong.
        """
        if self.bars:
            self.showErrorBars(step=self.step or 1)
        if self.bands:
            self.showConfidenceBands()

    # --------------------------------------------------------------- drawing

    def errorBarFor(self, node, curve, step=1):
        """One bar over one curve, or None when this case holds no error for it."""
        top, bottom = self.errorsOf(node, curve)
        if top is None:
            return None
        x, y = curve.getData()
        beam = self.beamOf(x)
        if step > 1:
            x, y = x[::step], y[::step]
            top, bottom = top[::step], bottom[::step]
        return pg.ErrorBarItem(x=np.asarray(x), y=np.asarray(y),
                               top=np.asarray(top), bottom=np.asarray(bottom),
                               beam=beam)

    def confidenceBandFor(self, node, curve):
        """The three items of one band: the two borders and the fill between."""
        top, bottom = self.errorsOf(node, curve)
        if top is None:
            return []
        x, y = curve.getData()
        values = np.asarray(y)
        upper = pg.PlotDataItem(np.asarray(x), values + np.asarray(top))
        lower = pg.PlotDataItem(np.asarray(x), values - np.asarray(bottom))
        fill = pg.FillBetweenItem(lower, upper)
        brush = pg.mkBrush('r')
        brush.setStyle(Qt.DiagCrossPattern)
        brush.setColor(Qt.red)
        fill.setBrush(brush)
        for item in (upper, lower, fill):
            self.viewBox.addItem(item)
        return (upper, lower, fill)

    def errorsOf(self, node, curve):
        """The two sides of the error, or (None, None) when the case holds neither.

        The node answers None for a sibling the dictionary has and the case left
        unfilled -- measured on `magnetics/flux_loop(0)/flux/data`, whose upper
        holds 17 344 values and whose lower holds nothing. One side known and the
        other not draws symmetrically: that is what the known side bounds.
        """
        top = node.get_data_error_upper(curve)
        bottom = node.get_data_error_lower(curve)
        if top is None and bottom is None:
            self.refuse(node)
            return None, None
        if top is None:
            top = bottom
        if bottom is None:
            bottom = top
        return top, bottom

    def refuse(self, node):
        """Say which quantity has no error data, in the log of its own case."""
        logging.getLogger(self.logNameOf(node)).error(
            'No error data available for: %s'
            % (node.getParametrizedDataPath() or node.getName()))

    @staticmethod
    def logNameOf(node):
        """The logger of the case that node came from -- the log panel's name."""
        view = node.getDataTreeView()
        return view.uri if view is not None else 'logPanel'

    @staticmethod
    def beamOf(x):
        """How wide a bar is drawn: a span over the samples, bounded both ways.

        Measured over the 17 344 points of `magnetics/flux_loop(0)/flux/data`:
        the span is 72,851 s, the raw beam 0,0042 s, and what is drawn is the
        lower bound 0,072851 s.
        """
        span = float(np.amax(x) - np.amin(x))
        beam = span / len(x)
        return min(max(beam, span / 1000.), span / 20.)

    # -------------------------------------------------------------- removing

    def removeBars(self):
        for bar in self.bars:
            self.viewBox.removeItem(bar)
        self.bars = []

    def removeBands(self):
        for upper, lower, fill in self.bands:
            self.viewBox.removeItem(fill)
            self.viewBox.removeItem(upper)
            self.viewBox.removeItem(lower)
        self.bands = []

    # ---------------------------------------------------------------- reading

    def errorBarCount(self):
        return len(self.bars)

    def bandCount(self):
        return len(self.bands)

    def stepUsed(self):
        return self.step
