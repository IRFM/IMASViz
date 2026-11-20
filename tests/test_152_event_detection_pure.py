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

"""The pure layer that finds events in a time series.

No IMAS, no Qt: a synthetic signal is all this layer wants, so the rules a
caller is offered against are pinned without a case and without a figure.
The core (and then the GUI and a report) will ask it through the one read
``get_signal`` already gives, so what it detects and what is plotted are the
same read: this tests only the reading, not the wiring.

* **ELM** -- an excursion up, gated by prominence, with the value floor and
  the minimum spacing;
* **sawtooth** -- the same read inverted, a crash down;
* **L-H** -- a threshold crossing, one direction or both, with the hysteresis
  band that stops a wobble from re-triggering;
* **the timing** -- the period of the event times, and the single-event and
  empty answers; and
* **the refusals** -- a flat signal, a signal too short, a parameter the kind
  does not take, each in words.
"""

import numpy as np
import pytest

from imasviz.VizAnalysis.detect import detect as ask
from imasviz.VizAnalysis.detect import peaks, period_stats


def _elmSignal(n=120, spike=5.0):
    """A flat baseline with three excursions up, sharp and known."""
    t = np.arange(n, dtype=float)
    y = np.zeros(n, dtype=float)
    y[10], y[50], y[90] = spike, 0.8 * spike, 1.2 * spike
    return t, y


# ---------------------------------------------------------------------------
# the three kinds, on a known signal
# ---------------------------------------------------------------------------

def test_an_excursion_up_is_one_elm_with_its_timing():
    t, y = _elmSignal()
    block = ask('elm', t, y)

    assert block['kind'] == 'elm'
    assert block['count'] == 3
    # in time order, each its abscissa and its value, the value floor left out
    # so all three of different heights are kept
    assert [e['index'] for e in block['events']] == [10, 50, 90]
    assert [e['value'] for e in block['events']] == [5.0, 4.0, 6.0]
    # the period of the event times: first to last, and the mean spacing
    assert block['period']['count'] == 3
    assert block['period']['span'] == 80.0
    assert block['period']['period_mean'] == 40.0


def test_a_crash_down_is_a_sawtooth_on_the_same_read():
    t, _ = _elmSignal()
    y = np.zeros(len(t), dtype=float)
    y[10], y[50], y[90] = -5.0, -4.0, -6.0
    block = ask('sawtooth', t, y)

    assert block['count'] == 3
    assert [e['index'] for e in block['events']] == [10, 50, 90]
    # the value is reported as the crash sits, negative, not its magnitude
    assert [e['value'] for e in block['events']] == [-5.0, -4.0, -6.0]


def test_a_level_crossing_is_a_transition_in_each_direction():
    t = np.arange(12, dtype=float)
    y = np.array([0, 0, 0, 10, 10, 10, 0, 0, 0, 10, 10, 10], dtype=float)

    both = ask('lh', t, y, threshold=5, direction='both')
    assert [e['index'] for e in both['events']] == [3, 6, 9]
    assert [e['direction'] for e in both['events']] == ['up', 'down', 'up']

    ups = ask('lh', t, y, threshold=5, direction='up')
    assert [e['index'] for e in ups['events']] == [3, 9]


def test_the_default_transition_level_is_the_median_of_the_signal():
    t = np.arange(8, dtype=float)
    # the finite median is 5, mid-span: every 0->10 is a rise through it and
    # every 10->0 a fall, so a signal that alternates crosses once a sample
    y = np.array([0, 10, 0, 10, 0, 10, 0, 10], dtype=float)
    block = ask('lh', t, y, direction='both')
    # starts below (armed up), so the first step is a rise: seven crossings,
    # up first, then alternately
    assert block['count'] == 7
    assert [e['direction'] for e in block['events']] == \
        ['up', 'down', 'up', 'down', 'up', 'down', 'up']


# ---------------------------------------------------------------------------
# the parameters the caller is offered against
# ---------------------------------------------------------------------------

def test_the_value_floor_keeps_only_the_peaks_past_it():
    t, y = _elmSignal()
    # a floor just under the middle peak keeps the two high ones and drops the
    # low one; it is a gate on the level, not on the prominence
    kept = ask('elm', t, y, threshold=4.5)
    assert [e['value'] for e in kept['events']] == [5.0, 6.0]


def test_the_min_spacing_keeps_the_most_prominent_of_a_cluster():
    t = np.arange(40, dtype=float)
    y = np.zeros(40, dtype=float)
    y[10], y[12] = 5.0, 4.0          # a cluster two samples apart
    y[30] = 6.0
    kept = ask('elm', t, y, min_distance=5)
    assert 30 in [e['index'] for e in kept['events']]
    # of the cluster, the higher one (5.0) survives, the lower dropped
    assert [e['value'] for e in kept['events']
            if e['index'] < 20] == [5.0]


def test_a_prominence_below_the_gate_is_not_an_event():
    t = np.arange(40, dtype=float)
    y = np.full(40, 1.0, dtype=float)
    y[10] = 1.4                     # a ripple above a flat baseline
    y[30] = 5.0                     # a real excursion
    kept = ask('elm', t, y, prominence=1.0)
    assert [e['index'] for e in kept['events']] == [30]


# ---------------------------------------------------------------------------
# the timing
# ---------------------------------------------------------------------------

def test_a_single_event_has_a_count_but_no_period():
    stat = period_stats([5.0])
    assert stat['count'] == 1
    assert stat['period_mean'] is None
    assert stat['period_std'] is None


def test_the_empty_list_has_no_timing_at_all():
    stat = period_stats([])
    assert stat['count'] == 0
    assert stat['span'] is None


def test_the_spacing_is_stated_in_seconds_when_the_time_is():
    stat = period_stats([0.0, 0.5, 1.5])
    assert stat['span'] == pytest.approx(1.5)
    assert stat['period_mean'] == pytest.approx(0.75)
    assert stat['mean_rate_hz'] == pytest.approx(1.0 / 0.75)


# ---------------------------------------------------------------------------
# the refusals, in words
# ---------------------------------------------------------------------------

def test_a_flat_signal_carries_no_event():
    with pytest.raises(ValueError, match='flat'):
        ask('elm', np.arange(5, dtype=float), np.ones(5))


def test_a_signal_too_short_to_carry_a_neighbour():
    with pytest.raises(ValueError, match='at least two'):
        ask('elm', [0.0], [1.0])


def test_mismatched_axis_lengths_are_rejected_before_the_read():
    with pytest.raises(ValueError, match='same length'):
        peaks([0.0, 1.0], [0.0])


def test_a_kind_that_is_not_one_of_the_three():
    t, y = _elmSignal()
    with pytest.raises(ValueError, match='`elm`, `sawtooth`, or `lh`'):
        ask('burst', t, y)


def test_a_parameter_the_kind_does_not_take_is_rejected_by_name():
    t, y = _elmSignal()
    with pytest.raises(ValueError, match='not among them'):
        ask('elm', t, y, direction='up')


def test_a_negative_spacing_is_rejected_by_name():
    t, y = _elmSignal()
    with pytest.raises(ValueError, match='non-negative'):
        peaks(t, y, min_distance=-3)


def test_a_mode_that_is_not_max_or_min():
    t, y = _elmSignal()
    with pytest.raises(ValueError, match='`max`.*`min`'):
        peaks(t, y, mode='sideways')
