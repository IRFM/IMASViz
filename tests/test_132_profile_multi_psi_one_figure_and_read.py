# Copyright holders : Commissariat à l'Energie Atomique et aux Energies
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
"""The multi-psi profile the field runs were owed: ONE figure, and the read.

This file isolates the two halves of the reliable path the agent was
fabricating instead of doing, so that it does not share the module-scoped
``figureframes`` of ``test_100`` (a figure drawn -- and the one closed after
-- there disturbs the order-dependent tests that read the earliest key).
It opens its own case, loads ``equilibrium``, and pins, on the reference case
(WEST 54924 run 0, data dictionary 3.35.0, the same numbers ``test_45`` and
``test_100`` measure):

* ``psi=0`` drawn fresh, then ``psi=10`` and ``psi=50`` piled onto that same
  figure with ``into_figure_key``: the three answer ONE figure key, it is
  drawing, and it holds THREE distinct curves -- the "several psi on the same
  figure" the user asked for and the model kept inventing;
* ``get_signal`` at each of the three psi answers a DIFFERENT element, with
  the peak falling strictly from the axis to the edge and at the measured
  value (50317 / 41096 / 13196 Pa), not a plausible-looking interpolation.

The figure this file draws is closed once it has said what it owed: a plot
frame left shown and open is the ownership hazard the suite punishes.
"""

import pytest

from mcp_server.core import McpGuiCore

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI,
                      case_uri_or_skip)

IDS_NAME = 'equilibrium'
TIME_SAMPLES = 49
PRESSURE_PATH = 'equilibrium.time_slice[0].profiles_1d.pressure'

pytestmark = [pytest.mark.case, pytest.mark.ui]


@pytest.fixture(scope='module')
def core(qapp, tmp_path_factory):
    """One self-contained session: the case open and equilibrium loaded.

    The suite does not isolate ``$HOME``, so patch it for the module the way
    the core fixture of ``test_100`` does, and undo it when the module is
    done. Any figure left in the bookkeeping is closed at teardown, so a
    shown-and-open frame does not outlive the session.
    """
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    home = tmp_path_factory.mktemp('multiPsiHome')
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


def test_multi_psi_slices_stack_onto_one_figure_with_three_curves(core):
    """One pressure profile, several psi slices, all on ONE figure.

    `psi=0` is drawn fresh (it earns a key); `psi=10` and `psi=50` are piled
    onto it with `into_figure_key`. All three answer the SAME figure key, the
    frame is drawing, and it holds THREE distinct curves -- not one element
    re-plotted, not three figures. This is the exact sequence the re-anchor in
    ``agent.py`` sends the model to, so the "grounded" side of that verrou
    has a real, measured path to land on."""
    first = core.plot_one(CASE_URI, PRESSURE_PATH, along=None,
                          indices={'psi': 0})
    assert first['drawing'] is True and first.get('opened_at') == {'psi': 0}
    key = first['figure']

    ten = core.plot_one(CASE_URI, PRESSURE_PATH, along=None,
                        indices={'psi': 10}, into_figure_key=key)
    fifty = core.plot_one(CASE_URI, PRESSURE_PATH, along=None,
                          indices={'psi': 50}, into_figure_key=key)

    assert ten['figure'] == key and ten['drawing'] is True
    assert fifty['figure'] == key and fifty['drawing'] is True
    frame = core.api.figureframes[key]
    assert frame.isDrawing()
    assert frame.curveCount() == 3, \
        'three psi slices on one figure must be three curves, not one'

    # Three psi slices of ONE profile are three DIFFERENT elements of the
    # same array of structures: the three curves must sit at three different
    # indices and answer three different values -- not one element read three
    # times at the index named last (the reported bug: psi slices stacked on
    # one figure all showing one curve, the psi slider on the last one named).
    # The peaks are the same numbers `get_signal` answers below.
    peaks = []
    for trace in frame._curves:
        ys = [v for v in trace.curve.getData()[1] if v == v]
        if ys:
            peaks.append(max(ys))
    assert len(peaks) == 3, peaks
    assert len(set(round(p, 1) for p in peaks)) == 3, \
        'three psi slices must be three distinct elements, not the last one '\
        'read three times: %s' % peaks


def test_per_psi_reads_are_distinct_monotone_and_the_measured_peak(core):
    """`get_signal` at each of the three psi answers a DIFFERENT element, and
    the element is the one the user named. The signature is the physical
    radial decay of a core pressure: the peak falls strictly from the axis
    outward, and the peaks are the measured values of the reference case
    (50317 / 41096 / 13196 Pa), not a plausible-looking interpolation of them.
    The field repros fabricated the in-between values (33761 / 27826 at
    psi 20 and 30; 1627 at psi 100) -- those numbers are refused here
    because they are not what the case holds."""
    peaks = {}
    for psi in (0, 10, 50):
        payload = core.get_signal(CASE_URI, PRESSURE_PATH, along=None,
                                  indices={'psi': psi})
        assert payload['kind'] == 'curve'
        assert payload['samples'] == TIME_SAMPLES
        peaks[psi] = max(float(v) for v in payload['y'] if v == v)

    assert peaks[0] > peaks[10] > peaks[50], \
        'a core profile: the peak must fall from the axis to the edge'
    # The measured peaks (within a small relative band), so a fabricated
    # in-between value cannot masquerade as the read.
    assert abs(peaks[0] - 50317.0) / 50317.0 < 0.05, peaks[0]
    assert abs(peaks[10] - 41096.0) / 41096.0 < 0.05, peaks[10]
    assert abs(peaks[50] - 13196.0) / 13196.0 < 0.05, peaks[50]
