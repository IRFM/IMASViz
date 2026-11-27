# Copyright holders: Commissariat à l'Energie Atomique et aux Energies
# Alternatives (CEA), France; and Laboratory for Engineering Design - LECAD,
# University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C
# open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted
# upon downloading the software and/or exercising any of the rights granted
# under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""An index the caller names is the ask: nothing on the figure may move it.

The report: « charge l'équilibre, trace la pression pour psi=0, 30 60 et 100
sur une nouvelle figure ». Four curves came out right, and under them one
slider labelled `psi 0 / 100` -- « changer sa valeur n'a pas de sens puisque
la valeur de ce paramètre est normalement fixée ».

Measured on the reference case (WEST 54924 run 0, DD 3.35.0) before the fix,
for the four-curve figure of that ask:

    sliceControls keys : [('LEAF', 'equilibrium', 'time_slice(itime).profiles_1d.psi')]
    trace 0 movable=[psi] fixed={}      trace 1..3 movable=[] fixed={psi: ...}

so the FIRST slice kept the figure's shared control and the later ones were
pinned: dragging that slider to 50 moved exactly the one curve the ask had
fixed first, its peak going 50317 -> 13195.8 Pa -- the psi[0] curve reading
psi[50] under a label saying psi 0. `QVizCurvePlot._pinning` pinned a named
coordinate of the leaf only when the figure already held another curve of that
same leaf, so the first call -- the one that builds the figure -- was the one
left with a slider.

An axis the caller names is now pinned for its own row whoever made the call,
and earns no control. The other half is pinned here too: a coordinate nobody
named still gets its slider, because that is what the tree's element and
*Explore this tensor* ask for (`test_60`, `test_64`).
"""

import pytest

from mcp_server.core import McpGuiCore

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI,
                      case_uri_or_skip)

IDS_NAME = 'equilibrium'
PRESSURE = 'equilibrium.time_slice[0].profiles_1d.pressure'
# Measured on this case by `test_132`, and by the probe that opened this file:
# the peak of the pressure profile at the named psi index.
AXIS_PEAK = 50317.0
MIDDLE_PEAK = 25338.0
SLICES = (0, 30, 60, 100)

pytestmark = [pytest.mark.case, pytest.mark.ui]


@pytest.fixture(scope='module')
def core(qapp, tmp_path_factory):
    """One self-contained session: the case open and equilibrium loaded."""
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    home = tmp_path_factory.mktemp('namedIndexNoSliderHome')
    patch = pytest.MonkeyPatch()
    patch.setenv('HOME', str(home))
    session = McpGuiCore()
    session.open_case(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
    session.load_ids(CASE_URI, IDS_NAME, 0)
    try:
        yield session
    finally:
        for key in list(getattr(session.api, 'figureframes', []) or {}):
            try:
                session.close_window(key)
            except Exception:
                pass
        patch.undo()


def _psiPins(frame):
    """One entry per drawn curve: the index it pins on the psi axis.

    None when the curve leaves that axis to a control of the figure -- which is
    what the reported figure did for its first curve.
    """
    pins = []
    for trace in frame.traces():
        index = None
        for key, value in trace.fixed.items():
            if str(key[-1]).endswith('.psi'):
                index = value
        pins.append(index)
    return pins


def _psiControls(frame):
    """The axes the figure puts a control under, whose spelling ends on psi."""
    return [key for key in frame.sliceControls.keys()
            if str(key[-1]).endswith('.psi')]


def _peaks(frame):
    """The peak of each drawn curve, in the order they were laid down."""
    peaks = []
    for trace in frame.traces():
        ys = [v for v in trace.curve.getData()[1] if v == v]
        peaks.append(max(ys) if ys else None)
    return peaks


def test_the_four_named_slices_lay_no_control_of_their_own(core):
    """The ask itself: psi at 0, 30, 60 and 100 on one new figure.

    Four curves, and NOTHING under psi to move afterwards. The reported figure
    carried one `psi 0 / 100` slider there, and it drove the first curve.
    """
    answers = [core.plot_one(CASE_URI, PRESSURE, indices={'psi': SLICES[0]})]
    for psi in SLICES[1:]:
        answers.append(core.plot_one(CASE_URI, PRESSURE, indices={'psi': psi},
                                     into_figure_key=answers[0]['figure']))
    key = answers[0]['figure']
    assert all(answer['figure'] == key for answer in answers), answers
    frame = core.api.figureframes[key]
    assert frame.isDrawing()
    assert frame.curveCount() == len(SLICES)

    assert _psiControls(frame) == [], \
        'a coordinate the caller named has no slider: %s' % list(
            frame.sliceControls.keys())
    assert frame.sliceControls.sliceCount() == 0, \
        'the named slice is the only axis this figure pins'
    # Every curve is pinned, at its own index -- not the first one left moving.
    assert _psiPins(frame) == list(SLICES), _psiPins(frame)
    assert all(trace.isFrozen() for trace in frame.traces())


def test_moving_the_figure_moves_none_of_the_four_curves(core):
    """A refresh re-reads what follows a control; here there is nothing to
    follow, so the four rows keep the values the ask named.

    The peaks are the measured ones of this case, falling from the axis to the
    edge: the last slice is the boundary of the closed flux surface, where the
    pressure of this case is nil.
    """
    key = core.plot_one(CASE_URI, PRESSURE, indices={'psi': SLICES[0]})['figure']
    for psi in SLICES[1:]:
        core.plot_one(CASE_URI, PRESSURE, indices={'psi': psi},
                      into_figure_key=key)
    frame = core.api.figureframes[key]
    before = _peaks(frame)
    assert frame.refresh() == {}
    assert _peaks(frame) == before, (before, _peaks(frame))

    assert len(set(round(p, 1) for p in before)) == len(SLICES), before
    assert abs(before[0] - AXIS_PEAK) / AXIS_PEAK < 0.05, before[0]
    assert abs(before[1] - MIDDLE_PEAK) / MIDDLE_PEAK < 0.05, before[1]
    assert before[0] > before[1] > before[2], before
    assert abs(before[3]) < 1.0, before[3]


def test_a_coordinate_nobody_named_keeps_its_slider(core):
    """The other half of the rule: an unnamed coordinate is a control.

    The tree's element sweeps from the element it stands on, so a quantity
    drawn without naming an index still gets its slider -- here one control,
    opening on the tree's index, and moving it to 50 reads the element the
    reported slider used to reach on its own: the measured 13 196 Pa.
    """
    answer = core.plot_one(CASE_URI, PRESSURE)
    frame = core.api.figureframes[answer['figure']]
    assert 'opened_at' not in answer, answer
    controls = _psiControls(frame)
    assert len(controls) == 1, list(frame.sliceControls.keys())
    assert frame.sliceControls.indices()[controls[0]] == 0
    peaks = _peaks(frame)
    assert abs(peaks[0] - AXIS_PEAK) / AXIS_PEAK < 0.05, peaks[0]

    frame.sliceControls.setIndex(controls[0], 50)
    moved = _peaks(frame)
    assert moved != peaks, (peaks, moved)
    assert abs(moved[0] - 13196.0) / 13196.0 < 0.05, moved[0]
