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

"""The spectral facts of a series, pinned on a synthetic signal before a case.

`detect.py` has its own synthetic pin in `test_152`. This does it for the
spectrum side: the dominant frequency and period of a known sine, that noise
does not displace that peak, the louder of two sines leading with both still
answerable, a band that does and does not contain the series, and for two
series -- how far one lags the other, and at what they both ring. Every refusal
is checked against the reason it is refused, the way `detect` is.

The sampling here is the one IMAS time series share (a uniform gap, `t` in
seconds), so the frequencies read are the ones Hz means.
"""

import numpy as np
import pytest

from imasviz.VizAnalysis.spectra import band_power, cross_correlation, spectrum

DT = 0.01
N = 200
T = np.arange(N) * DT


def sine(freq, amp=1.0):
    return amp * np.sin(2.0 * np.pi * freq * T)


# ---------------------------------------------------------------- the series itself

def test_a_pure_sine_answers_its_frequency_and_period():
    out = spectrum(T, sine(5.0))
    assert out['dominant']['frequency'] == pytest.approx(5.0, rel=0.02)
    assert out['dominant']['period'] == pytest.approx(0.2, rel=0.02)
    assert out['samples'] == N


def test_noise_does_not_displace_the_leading_peak():
    rng = np.random.default_rng(0)
    out = spectrum(T, sine(5.0) + 0.1 * rng.standard_normal(N))
    assert out['dominant']['frequency'] == pytest.approx(5.0, rel=0.05)
    assert out['dominant']['fraction'] > 0.5


def test_the_louder_of_two_sines_leads_and_both_are_answered():
    out = spectrum(T, sine(8.0) + 0.5 * sine(3.0), n_peaks=6)
    assert out['dominant']['frequency'] == pytest.approx(8.0, rel=0.02)
    freqs = [p['frequency'] for p in out['peaks']]
    assert any(abs(f - 3.0) < 0.1 for f in freqs), freqs


# ------------------------------------------------------------------- band power

def test_band_power_in_and_out_of_the_series():
    sig = sine(5.0)
    inBand = band_power(T, sig, 4.5, 5.5)
    outBand = band_power(T, sig, 10.0, 12.0)
    assert inBand['fraction'] > 0.9
    assert outBand['fraction'] < 0.05
    assert inBand['total_power'] == pytest.approx(outBand['total_power'])


# ------------------------------------------------------------------- two series

def test_one_series_lags_the_other_by_the_shift_and_rings_high():
    y1 = np.exp(-((T - 0.45) ** 2) / 0.005)
    y2 = np.exp(-((T - 0.50) ** 2) / 0.005)   # the same bump, 5 samples later
    out = cross_correlation(T, y1, T, y2)
    assert min(abs(out['lag_samples']), N - abs(out['lag_samples'])) == 5
    assert out['lag_time'] == pytest.approx(5.0 * DT, abs=1e-9)
    assert out['correlation'] > 0.75


def test_two_series_ring_together_at_their_common_frequency():
    y1 = sine(4.0)
    y2 = 0.7 * sine(4.0) + 0.2 * sine(11.0)
    out = cross_correlation(T, y1, T, y2)
    assert out['dominant_shared_frequency'] == pytest.approx(4.0, rel=0.05)


# ----------------------------------------------------------------------- refusals

def test_a_flat_series_has_no_frequency_to_lead_with():
    with pytest.raises(ValueError, match='flat'):
        spectrum(T, np.ones(N) * 3.14)


def test_a_series_too_short_to_spread_power_over_a_frequency():
    with pytest.raises(ValueError, match='At least'):
        spectrum(T[:5], sine(5.0)[:5])


def test_a_clock_that_is_not_strictly_increasing():
    tBad = T.copy()
    tBad[-1] = tBad[-2]
    with pytest.raises(ValueError, match='increasing'):
        spectrum(tBad, sine(5.0))


def test_a_band_whose_bounds_do_not_order():
    with pytest.raises(ValueError):
        band_power(T, sine(5.0), 5.0, 2.0)


def test_two_series_of_different_length_are_not_a_pair_to_correlate():
    with pytest.raises(ValueError, match='length'):
        cross_correlation(T, sine(5.0), T[:N - 1], sine(5.0)[:-1])


def test_how_many_peaks_is_a_positive_number():
    with pytest.raises(ValueError):
        spectrum(T, sine(5.0), n_peaks=0)
