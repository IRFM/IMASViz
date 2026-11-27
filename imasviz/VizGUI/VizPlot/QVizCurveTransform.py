# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""What a curve was read with, and the affine a hand laid on those values.

A curve transform -- `scale_curve`, `shift_curve`, `normalize_curve`, and their
inverse `reset_curve` -- used to be a coat of paint on the pyqtgraph item: the
caller read what the item displayed, wrote `y * factor` back with `setData`, and
for the inverse kept the previous (x, y) on the item under a private marker. The
figure itself knew nothing: no trace recorded that a value had been touched.

Anything that re-reads a trace therefore drew it back at its raw scale.
`QVizCurvePlot.refresh` re-reads every curve that follows a control -- a slider
dragged, `set_slice_index`, `plot(mode="into", indices=...)` posing a row -- and
hands what it read straight to `setData`; the same hole sits in `QVizPanel.refresh`
under a Table Plot View or a Stacked Plot View. Measured on the reference case:
a `magnetics/flux_loop(0)/flux/data` tensor figure normalised to
`(1.0, -0.5371)`, its one row `flux_loop` posed at index 2, answered
`(8.2487, -4.3935)` -- the values the case holds, the division forgotten, and
nothing said about it. Only a curve frozen by *Keep this curve* kept its scale,
because a frozen curve is not re-read at all.

So the values and the transform live beside the trace, and every draw of that
trace goes through them. The rule is an affine on the values as they were last
read -- `displayed = read * factor + offset` -- which composes in the order the
hand asked:

* scale by `f`: `(a * f, b * f)` -- a shift already on the curve is scaled too,
  as it was when the paint did it;
* shift by `d`: `(a, b + d)`;
* normalize by a reference read off the displayed values: `(a / ref, b / ref)`;
* reset: `(1, 0)`.

The factor is settled when the hand asks and stays. Move the row under a
normalised curve and it is the new element divided by the reference of the old
one: re-dividing by the new element's own peak would make the picture answer a
question nobody asked, and would make two curves of the same figure comparable
only by accident.

Two things this deliberately does not hold. The x values are kept as they were
read -- the transform family is a vertical one, and a curve whose abscissa moved
is a different quantity, not a dressed one.

A session, on the other hand, does write it: a `.vsess` `<Figure>` carries a
``<Transform trace factor offset>`` under the `<Quantity>` whose trace was dressed,
for the traces whose affine is not the one a freshly drawn curve answers. It is
written and put back through the three helpers at the bottom of this file, which
walk a window exactly the way `QVizPlotStyling.styledTraces` walks it -- the rank
of a trace among *its own quantity's* traces, one answer per panel of a table --
so the file and the frame cannot name two different traces. See
`tests/test_181_*`.
"""

import numpy as np

from imasviz.VizGUI.VizPlot.QVizPlotStyling import sourcesOf, styleKey


class QVizCurveTransform(object):
    """One curve's last-read values, and the (factor, offset) on top of them."""

    def __init__(self, x, y):
        self.x = np.asarray(x)
        self.raw = np.asarray(y)
        self.factor = 1.0
        self.offset = 0.0
        # Whether a hand is on it at all. `factor == 1 and offset == 0` is not
        # the answer to "was this curve transformed": `scale_curve(key, 1.0)`
        # asked for a transform and got one, and `reset_curve` owes it the
        # restoration it promised rather than a "nothing to take off".
        self.touched = False

    def read(self, x, y):
        """The values a re-read answered: the hand's affine stays on them.

        Called by whoever re-reads the trace (a slider, a posed row), never by a
        transform -- a transform changes the affine, not the values under it.
        """
        self.x = np.asarray(x)
        self.raw = np.asarray(y)

    def set(self, factor, offset):
        """Lay (factor, offset) on the values as last read."""
        self.factor = float(factor)
        self.offset = float(offset)
        self.touched = True

    def clear(self):
        """Take the transform off, the values staying where the read left them."""
        self.factor = 1.0
        self.offset = 0.0
        self.touched = False

    def affine(self):
        return (self.factor, self.offset)

    def isTouched(self):
        return self.touched

    def drawn(self):
        """(x, y) as the curve must be drawn: the read values and the affine."""
        if not self.touched:
            # Nothing on it: hand over what was read rather than a copy of it,
            # so a window nobody dressed holds the numbers the case answered,
            # bit for bit.
            return self.x, self.raw
        return self.x, self.raw * self.factor + self.offset

    def drawInto(self, curve):
        """Redraw that curve from these values."""
        x, y = self.drawn()
        curve.setData(x, y)
        return y

    def __repr__(self):
        return '<QVizCurveTransform factor=%g offset=%g n=%d>' % (
            self.factor, self.offset, len(self.raw))


# --------------------------------------------------- what a session asks of a window
# A session writes what a hand left on a window in the words the window itself
# uses for it, and it walks the window the way `QVizPlotStyling` walks it: a figure
# of curves answers for itself, a Table or a Stacked window answers one panel at a
# time. Those two walks have to agree about which trace a rank names, or a file
# dresses the neighbour of the curve the hand was on.

def transformableSources(window):
    """The sources of this window whose traces carry values a hand can move.

    A picture figure is not one of them: it answers neither `tracesForStyling` nor
    `transformOf`, because a scale over a picture is a colour range, not an affine
    on a value. A window a plugin drew is not one either, and a session meets it on
    the way to the four it draws itself.
    """
    return [source for source in sourcesOf(window)
            if all(getattr(source, name, None) is not None
                   for name in ('tracesForStyling', 'transformOf',
                                'setTransform'))]


def drawnTransforms(source):
    """[(treeNode, rank, (factor, offset))] for the traces of one source that carry one.

    The rank is `tracesForStyling`'s own: a trace ranked among the traces *of that
    quantity*, never a position in the window.

    A trace whose affine is (1, 0) is not in the list, whether or not a hand asked
    for it. That is the rule every other state of a session follows -- the identity
    is what a freshly drawn curve answers, so writing it says nothing about the
    screen. It can be recognised by its value here, and does not need the record of
    *which* traces were touched that a pen needs: every trace carries a pen, so a
    colour cannot tell a hand from the palette, while no palette hands out an
    affine. `scale_curve(key, 1.0)` therefore leaves the file silent, and the curve
    it dressed is put back at the same height.
    """
    entries = []
    for treeNode, rank, curve in source.tracesForStyling():
        factor, offset = source.transformOf(curve)
        if factor == 1.0 and offset == 0.0:
            continue
        entries.append((treeNode, rank, (factor, offset)))
    return entries


def touchedTransforms(window):
    """[(treeNode, rank, (factor, offset))] for every trace a hand scaled, shifted or divided."""
    return [entry for source in transformableSources(window)
            for entry in drawnTransforms(source)]


def replayTransforms(window, transforms):
    """Put recorded affines back on the traces of this window; answers how many landed.

    `transforms` is [(treeNode, rank, (factor, offset))], as the session recorded
    them for that window. A trace is found by the identity its quantity writes --
    path and run -- and its rank, through `setTransform`, which is the one place a
    frame lays an affine on the values it read: a replayed transform is therefore
    kept by the record like a hand's, and a session written again from a window
    that came back keeps it. A trace this window does not draw costs its entry and
    nothing else; the caller knows which quantity named it and says so.
    """
    applied = 0
    for source in transformableSources(window):
        drawn = {}
        for treeNode, rank, curve in source.tracesForStyling():
            key = styleKey(treeNode)
            if key is not None:
                drawn[(key, rank)] = curve
        for treeNode, rank, affine in transforms:
            curve = drawn.get((styleKey(treeNode), rank))
            if curve is None:
                continue
            if source.setTransform(curve, affine[0], affine[1]):
                applied += 1
    return applied
