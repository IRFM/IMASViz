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
"""The profile along its own coordinate, and the refusal that costs no figure.

The field repro, twice measured offscreen before this commit, on the
reference case (WEST 54924 run 0, DD 3.35.0, `equilibrium` occurrence 0):

* the user asks "pressure en fonction de psi" -> the model calls
  `plot_one(…time_slice[0].profiles_1d.pressure, along='psi')` and
  gets refused -- "already picks time_slice by its path" -- with steering
  that does not apply ("for another member, plot its own path") because
  the user meant THIS member, drawn along its OWN coordinate. The read
  twin already answered it: `get_signal(same, along='psi')` gives a curve
  of 101 samples, x on the leaf's own coordinate (not the 49 samples
  and ~16 s span the read along the clock gives). The draw refused what
  the read answered, on the same schema and the same resolver. The
  demand that refused it was a control over the family the member is
  picked from by its path -- a band a plain-element figure has no room
  for by design, so the demand was the defect.

* and whatever the refusal, it cost a window: the same refused call left
  a `Plot2` in `figureframes`, `list_windows` reported it `visible:
  True`, and the key was consumed -- after two such refusals the NEXT,
  successful call was numbered `Plot4`. A refusal is a refusal, not a
  ghost figure that later gets reaped by the collector ("released from
  the bookkeeping") and leaves a number no window ever carried.

This file pins both halves on the real case, in its own session and
closing whatever it draws, the way `test_132` does: it does not share
the module-scoped `figureframes` of `test_100`.
"""

import pytest

from mcp_server.core import McpGuiCore

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI,
                      case_uri_or_skip)

IDS_NAME = 'equilibrium'
PRESSURE = 'equilibrium.time_slice[0].profiles_1d.pressure'
PSI_PROFILE_SAMPLES = 101
# The read along the clock holds 49 samples over ~16.4 s; the read along
# the leaf's own coordinate holds 101 samples over a span far below a
# second. That gap is what tells the two apart in an assertion.
CLOCK_SPAN_SECONDS = 16.4

pytestmark = [pytest.mark.case, pytest.mark.ui]


@pytest.fixture(scope='module')
def core(qapp, tmp_path_factory):
    """One self-contained session: the case open and equilibrium loaded.

    HOME is patched for the module the way `test_100`'s fixture does,
    and undone at the end; every figure this file drew is closed before
    the session goes, so a shown-and-open frame does not outlive it.
    """
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    home = tmp_path_factory.mktemp('ownCoordinateHome')
    patch = pytest.MonkeyPatch()
    patch.setenv('HOME', str(home))
    session = McpGuiCore()
    session.open_case(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
    session.load_ids(CASE_URI, IDS_NAME, 0)
    try:
        yield session
    finally:
        for key in list(getattr(session.api, 'figureframes', None) or {}):
            try:
                session.close_window(key)
            except Exception:
                pass
        patch.undo()


def _keys(session):
    return sorted(getattr(session.api, 'figureframes', None) or {})


def test_the_profile_draws_along_its_own_coordinate(core):
    """'pressure en fonction de psi' on slice [0]: one curve, 101 samples,
    x on the leaf's own coordinate -- the figure the read already
    answered, on the same schema (`along`), not a refusal with steering
    that does not apply to the member the path picked."""
    before = _keys(core)
    answer = core.plot_one(CASE_URI, PRESSURE, along='psi')
    assert answer['drawing'] is True, \
        'the profile along its own coordinate is a refusal today: %r' \
        % answer
    key = answer['figure']
    frame = core.api.figureframes[key]
    assert frame.isDrawing()

    read = core.get_signal(CASE_URI, PRESSURE, along='psi')
    assert read['kind'] == 'curve'
    assert read['samples'] == PSI_PROFILE_SAMPLES, read
    xs = [float(v) for v in read['x'] if v == v]
    assert (max(xs) - min(xs)) < CLOCK_SPAN_SECONDS, \
        'x must be the leaf coordinate (%r), not the clock (~%g s)' \
        % (xs, CLOCK_SPAN_SECONDS)

    # The refusal's own steering, had it fired, named the family the
    # member was picked from -- `time_slice` -- which says the demand
    # was on the path-fixed family, not on the coordinate the user
    # asked about.
    assert key not in before, 'a new figure was expected: %r' % _keys(core)


def test_the_refusal_costs_no_figure_nor_a_consumed_key(core):
    """The one refusal that IS genuine -- a different member of the
    family the path fixed, asked by index -- still refuses, in words
    that name the family... and leaves NO figure open and consumes NO
    key. The field measured both defects: a `Plot2` in `figureframes`
    and `list_windows` reporting it visible, and a later successful call
    numbered `Plot4` -- over a number no window ever carried."""
    before = _keys(core)
    windows_before = [w.get('key') for w in core.list_windows()]
    with pytest.raises(ValueError) as exc:
        core.plot_one(CASE_URI, PRESSURE, along='psi',
                      indices={'time_slice': 5})
    message = str(exc.value)
    assert 'time_slice' in message, \
        'the refusal must name the family it cannot move: %s' % message

    after = _keys(core)
    assert after == before, \
        'the refused call left a figure in the bookkeeping: %r -> %r ' \
        '-- a refusal is not a ghost window to reappear as a number the ' \
        'next figure skips over' % (before, after)
    # The property under test: the refusal ADDS nothing on screen. The
    # figure its attempt opened is closed before the refusal is raised, so
    # neither `figureframes` (asserted above) nor `list_windows` may hold a
    # new key. (The other windows are left alone; offscreen may release one
    # it takes away, which is not this call's doing.)
    windows_after = {w.get('key') for w in core.list_windows()}
    assert windows_after <= set(windows_before), \
        'list_windows grew from a refused call: %r' \
        % (windows_after - set(windows_before))
