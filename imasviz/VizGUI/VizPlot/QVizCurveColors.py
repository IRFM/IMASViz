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
* the background those lines are drawn on is **black**: the configuration default
  is `background 'k'`, and the view box of the figure built by *Plot X to ->
  Figure* paints `(0, 0, 0, 255)`. Nothing in `imasviz` changes it -- the only
  `setBackground` in the package is the Profiles plugin's own table window, which
  sets white. So a palette has to be legible on black, which is why this list is
  **not** `getRGBColorList()`: that list carries `#FFFF00` on a white assumption,
  and three near-whites (`#cce5ff`, `#d3d3d3`, `#C0C0C0`) that read as background
  noise here, and its order comes out of `GlobalColors.__dict__`.

The confidence band of `QVizCurveErrors` is filled with `Qt.red`, so this palette
holds **no pure red**: a band and a trace in the same colour is the confusion this
row exists to remove, not one it should reintroduce.
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
