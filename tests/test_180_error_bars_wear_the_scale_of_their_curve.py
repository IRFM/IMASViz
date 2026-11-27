# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The error bars and the band of a curve wear the scale that curve was given.

A bar is not a value, it is an **extent**: it is drawn from the displayed y of the
curve and the two sides of the error the case holds for it. `QVizCurveErrors`
reads the first off the item (`curve.getData()`, so it follows every transform the
figure holds) and the second off the node (`get_data_error_upper` /
`get_data_error_lower`, which is what the Access Layer answered -- the raw
uncertainty). Those two readings came from two different scales, so a hand asking
for a factor moved the curve and left its bars where they were: on
`magnetics/flux_loop(0)/flux/data`, whose upper error holds 17 344 values around
**0,01** at the first sample, a curve multiplied by 10 stands at 0,0619... with a
bar of +-0,01 over it -- a tenth of what the case says the uncertainty is, and on
a factor under zero a bar even crosses to the wrong side of its curve.

The band has the same shape and is worse, because its two borders are built by
hand: `values + top` and `values - bottom`, the first from displayed values and
the second from raw ones. The fill between them is then neither the error nor a
scaled error, it is the sum of the two scales.

So the affine the figure holds for a trace is asked here too, and the two sides
come back at the scale of the curve they belong to. The offset cancels by itself:
`raw*factor + offset + err` is `displayed + factor*err`, so only the factor is
asked of the record. A factor under zero flips which raw side lands above the
curve, and `ErrorBarItem` takes its two arguments as extents above and below, so
both come back positive.

What this costs when a transform is asked with bars already on screen is one
redraw of those bars -- the same redraw `refresh` already does when a slider moves
the curve under them, and the reason it is done from `setTransform` /
`clearTransform` rather than left to the caller: the bars are the figure's, and a
gesture that changes the figure redraws what the figure draws.

"""

import pytest

import numpy as np
import pyqtgraph as pg

from mcp_server.core import McpGuiCore

from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode \
    import QVizPlotOneNode

from conftest import CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip
from support import ownership

IDS_NAME = 'magnetics'
# The two quantities `test_58` measures the bars on: one whose case fills an
# `_error_upper` sibling, one to join the same window afterwards.
FLUX0 = 'magnetics.flux_loop[0].flux.data'
BPOL0 = 'magnetics.bpol_probe[0].field.data'

# What the case holds at the first sample of `flux/data`, along time: the value
# and the known side of its error. `test_58` pins the pair as
# 0,006196762900799513 and 0,016196762677282095 -- an error of 0,01.
ERROR_AT_FIRST = 0.009999999776482582

pytestmark = [pytest.mark.case, pytest.mark.ui]


@pytest.fixture(scope='module')
def core(qapp, tmp_path_factory):
    """One agent session on the reference case, $HOME patched apart.

    The transforms are asked through the tool surface, so they belong to a core
    session -- and that session must not reach the real `~/.imasviz`.
    """
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    home = tmp_path_factory.mktemp('errorsHome')
    patch = pytest.MonkeyPatch()
    patch.setenv('HOME', str(home))
    session = McpGuiCore()
    session.open_case(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
    # The leaves a bar is read from only exist once the occurrence is loaded: an
    # unloaded IDS answers no leaf of itself to a path.
    session.load_ids(CASE_URI, IDS_NAME, 0)
    try:
        yield session
    finally:
        patch.undo()


def figureOf(session, path=FLUX0):
    """One quantity drawn along time, held for the run, with the key it answers to.

    The command the shot view uses, on the view of the core's own session: the
    figure then lives in the api the transforms are asked of, which is what
    `_curveFor` looks in.
    """
    view = next(iter(session.api.DTVlist))
    node = session._nodeForPath(view, path)
    frame = QVizPlotOneNode(dataTreeView=view, treeNode=node,
                            alongTime=True).execute()
    assert frame is not None, 'nothing was drawn for %s' % path
    ownership.keep(frame)
    return frame, session.api.GetFigureKeyOf(frame)


def barsOf(frame):
    return [item for item in frame.pgPlotWidget.getViewBox().addedItems
            if isinstance(item, pg.ErrorBarItem)]


def bordersOf(frame):
    """The band's own two borders: its curves, not the ones this figure drew."""
    return [item for item in frame.pgPlotWidget.getViewBox().addedItems
            if isinstance(item, pg.PlotDataItem)
            and item not in frame.curves()]


def curveValues(frame, index=0):
    _x, y = frame.curves()[index].getData()
    return np.asarray(y, dtype=float)


# ---------------------------------------------------------------------- bars

@pytest.mark.ui
def test_a_scaled_curve_scales_the_bars_over_it(core):
    """The bar is the error at the scale of the curve, not the raw one."""
    frame, key = figureOf(core)
    frame.errors.toggleErrorBars()
    assert len(barsOf(frame)) == 1
    rawTop = barsOf(frame)[0].opts['top'].copy()
    rawBottom = barsOf(frame)[0].opts['bottom'].copy()
    assert float(rawTop[0]) == pytest.approx(ERROR_AT_FIRST, rel=1e-9)

    core.scale_curve(key, 10.0)

    bar = barsOf(frame)[0]
    assert bar.opts['top'] == pytest.approx(10. * rawTop, rel=1e-9)
    assert bar.opts['bottom'] == pytest.approx(10. * rawBottom, rel=1e-9)
    # And the bar stands on the curve the figure actually draws.
    assert (bar.opts['y'] == curveValues(frame)).all()


@pytest.mark.ui
def test_a_normalised_curve_divides_its_bars_by_the_same_reference(core):
    """The reference a normalisation settles is the reference of the error too."""
    frame, key = figureOf(core)
    frame.errors.toggleErrorBars()
    rawTop = barsOf(frame)[0].opts['top'].copy()

    answer = core.normalize_curve(key, mode='max')
    reference = answer['reference']
    assert reference != 1.0, 'nothing divided here: the peak was already 1'

    assert barsOf(frame)[0].opts['top'] == pytest.approx(rawTop / reference,
                                                         rel=1e-9)


@pytest.mark.ui
def test_an_offset_moves_the_curve_and_leaves_the_bar_extents_alone(core):
    """A bar is an extent: adding to the value adds to neither side.

    `raw*factor + offset + err` is `displayed + factor*err` -- the offset cancels,
    so a shift costs the bars nothing but the height they hang from.
    """
    frame, key = figureOf(core)
    frame.errors.toggleErrorBars()
    rawTop = barsOf(frame)[0].opts['top'].copy()
    rawBottom = barsOf(frame)[0].opts['bottom'].copy()

    core.shift_curve(key, 5.0)

    bar = barsOf(frame)[0]
    assert bar.opts['top'] == pytest.approx(rawTop, rel=1e-9)
    assert bar.opts['bottom'] == pytest.approx(rawBottom, rel=1e-9)
    assert (bar.opts['y'] == curveValues(frame)).all()


@pytest.mark.ui
def test_a_negative_factor_keeps_both_sides_on_their_own_side(core):
    """A factor under zero swaps which raw side is which, not which is above.

    `ErrorBarItem` takes `top` and `bottom` as extents above and below the point,
    so a negative factor must not hand it a negative extent: the bar would cross
    to the other side of its curve.
    """
    frame, key = figureOf(core)
    frame.errors.toggleErrorBars()
    rawTop = barsOf(frame)[0].opts['top'].copy()

    core.scale_curve(key, -2.0)

    bar = barsOf(frame)[0]
    assert (bar.opts['top'] >= 0).all()
    assert (bar.opts['bottom'] >= 0).all()
    assert bar.opts['top'] == pytest.approx(2. * rawTop, rel=1e-9)


@pytest.mark.ui
def test_the_bars_are_replaced_and_not_piled_up_when_the_transform_changes(core):
    """One bar over one curve, however many times the hand dressed it.

    `refresh` takes the old items down before drawing: a transform that left its
    bars in place and drew a second set would double every uncertainty on screen,
    with nothing but a count saying it.
    """
    frame, key = figureOf(core)
    frame.errors.toggleErrorBars()
    items = len(frame.pgPlotWidget.getViewBox().addedItems)

    core.scale_curve(key, 3.0)
    core.shift_curve(key, 1.0)
    core.normalize_curve(key, mode='mean')

    assert frame.errors.errorBarCount() == 1
    assert len(barsOf(frame)) == 1
    assert len(frame.pgPlotWidget.getViewBox().addedItems) == items


@pytest.mark.ui
def test_reset_curve_puts_the_bars_back_at_the_error_the_case_holds(core):
    """Taking the transform off takes it off the bars too."""
    frame, key = figureOf(core)
    frame.errors.toggleErrorBars()
    rawTop = barsOf(frame)[0].opts['top'].copy()

    core.scale_curve(key, 10.0)
    assert barsOf(frame)[0].opts['top'] == pytest.approx(10. * rawTop,
                                                         rel=1e-9)

    core.reset_curve(key)
    assert barsOf(frame)[0].opts['top'] == pytest.approx(rawTop, rel=1e-9)


# --------------------------------------------------------------------- bands

@pytest.mark.ui
def test_the_borders_of_a_band_follow_the_factor(core):
    """The band is drawn from the curve and its error, at one scale.

    Its borders are built by hand -- `values + top`, `values - bottom` -- so the
    two readings had to be brought to the same scale or the fill between them is
    the sum of a displayed value and a raw uncertainty.
    """
    frame, key = figureOf(core)
    frame.errors.toggleConfidenceBands()
    assert len(bordersOf(frame)) == 2

    core.scale_curve(key, 10.0)

    values = curveValues(frame)
    borders = bordersOf(frame)
    tops = sorted(border.getData()[1][0] for border in borders)
    base = values[0]
    assert tops[1] == pytest.approx(base + 10. * ERROR_AT_FIRST, rel=1e-6)
    assert tops[0] == pytest.approx(2 * base - tops[1], rel=1e-6)


# ------------------------------------------------- the transform is per curve

@pytest.mark.ui
def test_a_curve_that_joined_afterwards_keeps_the_scale_of_its_own_error(core):
    """The factor belongs to the trace it was asked on -- bars included.

    A second quantity joining a dressed window is drawn as the case holds it, so
    its bars are the raw error while its neighbour's wear the hand's factor. A
    single scale for the figure would dress a curve nobody dressed.
    """
    frame, key = figureOf(core)
    core.scale_curve(key, 10.0)
    view = next(iter(core.api.DTVlist))
    joinedNode = core._nodeForPath(view, BPOL0)
    assert frame.plot(joinedNode) == 1
    assert frame.curveCount() == 2

    frame.errors.toggleErrorBars()
    assert frame.errors.errorBarCount() == 2

    dressed, joined = barsOf(frame)
    assert float(dressed.opts['top'][0]) == pytest.approx(
        10. * ERROR_AT_FIRST, rel=1e-6)
    # The neighbour's own error, as the case holds it: the hand's factor never
    # reaches a curve it was not asked on.
    raw = joinedNode.get_data_error_upper(frame.curves()[1])
    assert float(joined.opts['top'][0]) == pytest.approx(float(np.asarray(raw)[0]),
                                                         rel=1e-9)
