# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The equilibrium radial profiles keep their own vertical scale.

The eight radial profiles one stack holds (q, elongation, the two triangularities,
j_tor, pressure, f_df_dpsi, dpressure_dpsi) are eight *different* quantities whose
ranges span about four orders of magnitude on the reference shot. They are stacked
in a `QVizStackedPlot`, whose *Group pan mode* (on by default) links *both* the
abscissa and the vertical range of every panel to the first. For a stack of
comparable quantities that is the point of the window; for the equilibrium stack it
is what the user reported -- "tous les tracés écrasés en Y": every panel is drawn
against the first panel's range, so the small ones flatten to a line under it and
the big ones run off the top.

The fix is a flag the window sets (`sharedY=False`), not a change to the standard
stacked window. This test pins both sides:

* the equilibrium figure's profile stack shares the abscissa (group pan on X) but
  NOT the vertical range -- each panel keeps its own scale;
* the default stacked plot (a Stacked Plot View) still links both, because that is
  the documented behaviour for a stack of comparable quantities (see test_37).

Nothing here opens a case: a raw (x, y) pair is all `drawProfiles` needs, which is
enough to see which side of the Y link each panel ends on.
"""

import pytest
import pyqtgraph as pg

from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizEquilibriumFigure \
    import QVizEquilibriumFigure
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizStackedPlot import QVizStackedPlot

# One abscissa the profiles all run along (rho_tor normalized), and two profiles
# whose ranges do not agree: the first spans a unit, the second spans a hundred.
RHO = [0., 1., 2., 3.]
PROFILE_SMALL = [0.01, 0.05, 0.2, 0.8]
PROFILE_BIG = [10., 50., 200., 800.]


def linkedToFirst(frame):
    """[(shares x, shares y)] for every panel, asked of the view boxes.

    The first panel is the reference, so it answers for itself as the test
    in `test_37_stacked_entries` does.
    """
    first = frame.panels()[0].plotItem().getViewBox()
    return [(panel.plotItem().getViewBox().linkedView(pg.ViewBox.XAxis) is first,
             panel.plotItem().getViewBox().linkedView(pg.ViewBox.YAxis) is first)
            for panel in frame.panels()]


def twoProfiles(sharedY):
    """A stacked frame with two profiles of different magnitude, `sharedY` set."""
    frame = QVizStackedPlot(sharedY=sharedY)
    frame.plotRaw(RHO, PROFILE_SMALL, 'q', name_units='', x_label='rho', x_units='')
    frame.plotRaw(RHO, PROFILE_BIG, 'pressure', name_units='kPa',
                  x_label='rho', x_units='')
    return frame


@pytest.mark.ui
def test_the_equilibrium_profile_stack_keeps_each_panels_own_vertical_range(qapp):
    """The reported defect: the eight radial profiles are different quantities,
    so a shared vertical range flatters the big one and crushes the small.
    The stack the equilibrium figure builds turns that off; the shared abscissa
    (group pan on X) is what the window is for and stays linked."""
    figure = QVizEquilibriumFigure()
    figure.drawProfiles(RHO, 'rho', '',
                        [
                            ('q', PROFILE_SMALL, ''),
                            ('pressure', PROFILE_BIG, 'kPa'),
                        ])
    stack = figure.profilesStack()
    assert stack is not None, 'the equilibrium figure holds a stack of profiles'
    assert stack.sharedY is False, \
        'the equilibrium stack must not share one vertical range across panels'

    # Panel 0 is the reference; the later panel shares the abscissa (X) but keeps
    # its own vertical range (Y), even in group-pan mode.
    linked = linkedToFirst(stack)
    assert linked[0] == (True, True) or linked[0] == (False, False)
    assert linked[1][0] is True, \
        'the profile panels share the abscissa: group pan is on for X'
    assert linked[1][1] is False, \
        'the profile panels must NOT share a vertical range: each keeps its scale'


@pytest.mark.ui
def test_group_pan_mode_off_unlinks_the_abscissa_but_the_stack_uses_sharedY(qapp):
    """Toggling the group-pan box reaches the abscissa only, on a stack that
    opted out of sharing the vertical range: X unlinks, Y was already unlinked
    by `sharedY=False` and stays so."""
    stack = twoProfiles(sharedY=False)
    stack.groupPanCheck.setChecked(True)
    assert linkedToFirst(stack)[1] == (True, False)
    stack.groupPanCheck.setChecked(False)
    assert linkedToFirst(stack)[1] == (False, False)


@pytest.mark.ui
def test_the_default_stacked_window_still_shares_both_axes(qapp):
    """The flag is what changes the equilibrium window, not the standard Stacked
    Plot View: with `sharedY` left at its default a stack of comparable
    quantities still links both the abscissa and the vertical range (the
    behaviour `test_37_stacked_entries` pins for the standard window)."""
    stack = twoProfiles(sharedY=True)
    assert stack.sharedY is True
    stack.groupPanCheck.setChecked(True)
    assert linkedToFirst(stack)[1] == (True, True)
