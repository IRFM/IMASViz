# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The colour each trace of a figure is drawn with.

A curve figure is there to compare quantities, and every entry that puts a second
trace on it -- *Plot selected nodes to -> Figure*, the same into an open figure,
a plugin's *plot to figure* -- answers the comparison with two lines nobody can
tell apart. Measured on the reference case (WEST 54924 run 0, dictionary
3.35.0), on `magnetics` occurrence 0:

* pyqtgraph **0.13.7** gives a curve drawn without a pen `opts['pen'] ==
  (200, 200, 200)`, and it is a plain instance default: a `PlotItem` holds **no**
  colour cycle -- `colorCycle`, `colorLists` and `currentColor` appear **0** time
  in the package. So two curves asked the same question twice and got the same
  answer twice;
* a figure holding `magnetics/flux_loop(0)/flux/data` and
  `magnetics/bpol_probe(0)/field/data` -- one quantity, then the other added to
  the same figure -- draws **2** curves, both `tuple(200, 200, 200)`;
* the selection figure does the same: **3** nodes selected, **2** curves drawn
  (the third has no value along the plotted axis and is refused by name), both
  `tuple(200, 200, 200)`;
* the background those lines are drawn on is **black** -- and it is the *view*
  that paints it, not the plot. Measured: `PlotWidget.backgroundBrush()` answers
  `SolidPattern (0, 0, 0, 255)`, from pyqtgraph's own configuration default
  (`'background': 'k'`, `pyqtgraph/__init__.py:45`, applied by
  `GraphicsView.__init__` through `setBackground('default')`); `imasviz` never
  touches it. Do not ask `viewBox.background.brush()` -- that is a
  `QGraphicsRectItem` pyqtgraph only shows when `setBackgroundColor` was called,
  and it was not: measured on both a curve figure and a plugin panel, the item is
  **hidden** and its brush **NoBrush**, while its `color()` still answers
  `(0, 0, 0, 255)`. That reading says nothing about the ground.

So a palette has to be legible on black, which is why this list is **not**
`getRGBColorList()`: that list carries `#FFFF00` on a white assumption, and three
near-whites (`#cce5ff`, `#d3d3d3`, `#C0C0C0`) that read as background noise here,
and its order comes out of `GlobalColors.__dict__`.

The confidence band of `QVizCurveErrors` is filled with `Qt.red`, so this palette
holds **no pure red**: a band and a trace in the same colour is the confusion this
row exists to remove, not one it should reintroduce.

`LIGHT_CURVE_COLOURS` is the same answer for a window that paints the other
ground. The Profiles plugin's table window sets `setBackground((255, 255, 255))`
(`QVizTablePlotView.py:75`), measured `SolidPattern (255, 255, 255, 255)` on its
view: it is the only `setBackground` in the package, and it is white. Half of the
black palette vanishes there -- measured contrast against that white: cyan
**1,25**, chartreuse **1,30**, spring green **1,35**, gold **1,40**, orange
**2,33**, magenta **3,14** -- so the plugin asks this list instead. Its entries
are picked against the same three rules, measured here: a contrast of at least
**4,5** on white (the weakest, teal, answers **4,77**), no pure red (those panels
carry the same `QVizCurveErrors` band as a curve figure), and no colour whose
three channels are all at or above 128 -- a near-white on a white ground. Ordered
so the cycle stays legible where it closes: the smallest squared rgb distance
between two consecutive entries, the last and the first included, is **32 768**.

The plugin draws **one** of these, the first, on every panel -- and not because a
palette of 8 was too small for it. Measured on the reference case, its window
holds **41** panels carrying **41 distinct parametrized paths**, one panel per
path: there is nothing for a colour to group, and cycling would answer the same
colour five times in one window.
"""

import pyqtgraph as pg

# Name first, so a refusal, a test and the log can say which colour was meant.
# Ordered so two consecutive traces are as far apart in hue as this list allows:
# the cycle is what a user sees when a selection is longer than the palette.
CURVE_COLOURS = (
    ('orange', (255, 140, 0)),
    ('cyan', (0, 255, 255)),
    ('chartreuse', (127, 255, 0)),
    ('magenta', (255, 0, 255)),
    ('spring green', (0, 255, 127)),
    ('violet', (191, 0, 255)),
    ('gold', (255, 215, 0)),
    ('dodger blue', (30, 144, 255)),
)

CYCLE = len(CURVE_COLOURS)


def colourFor(index):
    """The rgb triple of the index-th trace, cycling once the palette is used up."""
    return CURVE_COLOURS[index % CYCLE][1]


def nameFor(index):
    """What that colour is called -- for a test, a log line, or the manual."""
    return CURVE_COLOURS[index % CYCLE][0]


def penFor(index):
    """The pen of the index-th trace, of the library's own default width."""
    return pg.mkPen(colourFor(index))


# For a window that paints white, and so cannot use the list above: half of it
# answers a contrast under 2,5 there. Same three rules -- contrast on the ground
# it is painted on, no pure red (the confidence band is red wherever it is drawn),
# no near-white -- and an order that keeps the cycle legible where it closes.
# `lightColourFor(0)` is what the Profiles plugin draws every panel with.
LIGHT_CURVE_COLOURS = (
    ('navy', (0, 0, 128)),
    ('maroon', (128, 0, 0)),
    ('green', (0, 128, 0)),
    ('purple', (128, 0, 128)),
    ('teal', (0, 128, 128)),
    ('dark magenta', (140, 0, 110)),
    ('blue', (0, 0, 255)),
    ('sienna', (160, 82, 45)),
)

LIGHT_CYCLE = len(LIGHT_CURVE_COLOURS)


def lightColourFor(index):
    """The rgb triple of the index-th trace drawn on a white ground."""
    return LIGHT_CURVE_COLOURS[index % LIGHT_CYCLE][1]


def lightNameFor(index):
    """What that colour is called -- for a test, a log line, or the manual."""
    return LIGHT_CURVE_COLOURS[index % LIGHT_CYCLE][0]
