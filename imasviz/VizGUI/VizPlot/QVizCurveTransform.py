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
is a different quantity, not a dressed one. And nothing here is written to a
session: a `.vsess` `<Figure>` has no element for a transform, so a window put
back from a file still comes at its raw scale. That is a format question, with
the `<Style>` / `<ColourScale>` / `<View>` elements as its shape, not this record.
"""

import numpy as np


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
