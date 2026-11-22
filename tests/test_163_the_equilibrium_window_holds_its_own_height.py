# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The equilibrium window holds its own height: the frames fill the window.

Reported on WEST 54924 at t = 44 s, from the web surface: "*une image blanche,
sans aucune courbe visible*". The window was not empty -- the read answered a
**7229** point grid, **30** levels cut into **14728** points of contour, a
**335** point boundary, a **164** point limiter, and eight profiles of **101**
points: `curveCount()` answered **13**. What the user saw was the picture those
thirteen curves were painted into:

    whole window       1272 x 772   18397 samples of empty body / 1726 of ground
    graphics widget    QRect(0, 0, 1272, 68)
    profiles stack     QRect(0, 0, 100, 30), layout index -1

Two defects of one layout, and neither is a curve count or a null-pixmap check:

* the graphics widget was added to the window's `QVBoxLayout` at stretch **0**
  with an invisible `addStretch(1)` below it, so the spacer took the window's
  height and the frames were left their **68** px minimum -- 91% of the capture
  said nothing;
* `drawProfiles` built the stack with the window as its **parent** and never
  put it in the window's **layout**, so the eight panels kept the geometry Qt
  gives a child at birth (`100 x 30`) while the stack's own layout asked **592**
  px for them.

The fix is the two shares of `QVizEquilibriumFigure` (`ROW_SHARE`,
`PROFILES_SHARE`). Measured after it, on the same case at the same instant and
the same window size: the row answered `QRect(0, 0, 1192, 383)`, the stack
`QRect(0, 389, 1192, 383)`, and the capture answered **15169** samples of the
black ground against **1545** of empty body.

Nothing here opens a case: `drawRow` needs a grid, not a pulse, so the surface
below is a four-point square -- the levels are cut on a raster over the grid's
extents, so a coarse grid still answers contours.
"""

import numpy as np
import pytest

from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizEquilibriumFigure \
    import QVizEquilibriumFigure

from support import ownership

# The read answers numpy arrays and `_RasterField` asks them as such (`R.min()`),
# so the stand-in grid is built the same shape: a square of four points and two
# triangles is all `drawRow` needs, because the levels are cut on a raster over
# the grid's extents and a coarse grid still answers contours.
SQUARE_R = np.array([0., 1., 1., 0.])
SQUARE_Z = np.array([0., 0., 1., 1.])
SQUARE_TRIANGLES = np.array([[0, 1, 2], [0, 2, 3]], dtype=int)
SQUARE_PSI = np.array([0., 0.3, 1.0, 0.7])

# Two profiles whose ranges do not agree, to give the stack two panels.
RHO = [0., 1., 2., 3.]
PROFILE_SMALL = [0.01, 0.05, 0.2, 0.8]
PROFILE_BIG = [10., 50., 200., 800.]

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800


def surfaceOne():
    return {'R': SQUARE_R, 'Z': SQUARE_Z, 'triangles': SQUARE_TRIANGLES,
            'psi': SQUARE_PSI, 'levels': [0.2, 0.5, 0.8],
            'boundary': (SQUARE_R, SQUARE_Z), 'axis': (0.5, 0.5),
            'x_point': None, 'index': 0, 'b0': 1.0, 'r0': 0.5,
            'time_slice_time': 1.0}


def drawnShare(frame):
    """What part of the window's height the widgets it manages really hold.

    A spacer answers no widget, so it contributes nothing to the share asked
    here -- which is the whole point of the measure: the reported window held
    68 of its 772 px, and the number says so.
    """
    layout = frame.layout()
    assert layout is not None, 'the equilibrium figure owns a layout'
    held = sum(layout.itemAt(index).widget().height()
               for index in range(layout.count())
               if layout.itemAt(index).widget() is not None)
    return held / float(max(frame.height(), 1))


@pytest.mark.ui
def test_the_row_of_frames_holds_the_window_it_was_given(qapp):
    """Entry 0 (the row alone): the frames are the window, not a strip of it.

    Measured before the fix, on the reference case: the graphics widget of a
    1272 x 772 window answered `QRect(0, 0, 1272, 68)`, and the capture of that
    window was 18397 samples of empty body against 1726 of the ground the
    surfaces are painted on.
    """
    figure = ownership.keep(QVizEquilibriumFigure())
    figure.drawRow([surfaceOne()])
    figure.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
    figure.show()
    qapp.processEvents()
    assert drawnShare(figure) > 0.9, \
        'the row of frames is what fills the window: %r of its height is held' \
        % drawnShare(figure)
    assert figure.pgPlotWidget.height() > 0.9 * figure.height()


@pytest.mark.ui
def test_the_profiles_stack_lands_under_the_row_in_the_layout(qapp):
    """Entry 1: "under the row" is a word about the layout, not about the parent.

    `drawProfiles` built the stack with the window as its parent and never told
    the layout about it, so the eight panels kept the geometry Qt gives a child
    at birth -- measured `QRect(0, 0, 100, 30)`, with the stack's own layout
    asking 592 px of height for them. Both halves now carry a share, so each is
    a real part of the window rather than an overlap of the other.
    """
    figure = ownership.keep(QVizEquilibriumFigure())
    figure.drawRow([surfaceOne()])
    figure.drawProfiles(RHO, 'rho', '',
                        [('q', PROFILE_SMALL, ''),
                         ('pressure', PROFILE_BIG, 'kPa')])
    figure.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
    figure.show()
    qapp.processEvents()
    stack = figure.profilesStack()
    layout = figure.layout()
    assert layout.indexOf(stack) != -1, \
        'the profiles stack is a line of the window layout, not a free child'
    assert drawnShare(figure) > 0.9, \
        'the row and the stack together fill the window: %r of its height is ' \
        'held' % drawnShare(figure)
    # Neither half is left to its minimum against the other: an aspect-locked
    # flux surface at 68 px tall is a picture nobody can read, and so is a
    # stack of profiles squeezed into a 30 px band.
    assert figure.pgPlotWidget.height() > 0.25 * figure.height(), \
        'the row keeps a share of the window'
    assert stack.height() > 0.25 * figure.height(), \
        'the stack keeps a share of the window'
