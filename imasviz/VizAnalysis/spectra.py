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

"""What a time series oscillates at: the spectral facts of one signal, of two.

Companion of `detect.py` and the same kind of thing: pure, numpy-only, no Qt
and no case beside it. It is driven from a synthetic signal in the test and, on
the surface, from the same read `get_signal` does, so the spectrum and the
figure it is drawn from are one answer. The units are the ones the case gives
(`t` in seconds, `y` in whatever it is) and the frequency in Hz: no unit
conversion is done here, and none is owed.

What is answered, and why those: a series a physicist opens to ask "what does
it do" wants the **dominant frequency** (and its period) and how much of the
power sits there, the share of the power that lives in a **band**, and -- for
two series -- how much one **lags** the other and at what frequency they both
oscillate. Everything a number, and none of it the whole spectrum: the figure,
when there is one, is where a spectrum is read, not the report.
"""

import numpy as np

# A sine with two samples a period is an aliasing guess, not a measurement; and a
# series is read as a constant once its power is below this over its total.
MIN_SAMPLES = 8


def _arrays(t, y):
    """The two finite, strictly-increasing arrays, or a `ValueError` naming why not.

    The frequency a series is asked of comes from its own `t`, so a `t` that is
    not a clock is a refusal, not an answer; the samples are paired (a NaN in
    one keeps the one beside it out) and at least `MIN_SAMPLES` of them must be
    left, or there is no frequency a power could be spread over.
    """
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    if t.shape != y.shape:
        raise ValueError('the series answers %d abscissae to %d ordinates; '
                         'they are one signal, so they must match.'
                         % (t.size, y.size))
    keep = np.isfinite(t) & np.isfinite(y)
    t = t[keep]
    y = y[keep]
    if t.size < MIN_SAMPLES:
        raise ValueError('a series of %d point(s) left after the NaNs are out has '
                         'no frequency its power could be spread over. At least %d '
                         'are needed.' % (t.size, MIN_SAMPLES))
    if np.any(np.diff(t) <= 0):
        raise ValueError('the abscissae are not a strictly increasing clock: '
                         'two equal or out-of-order points would make the '
                         'frequencies of the spectrum ambiguous.')
    return t, y


def _sampling(t):
    """(dt, fs) of the series: the median gap and its reciprocal.

    The median rather than the mean: one gap the read left out (a missing
    sample the case does not hold) must not move the grid every later bin sits on.
    """
    dt = float(np.median(np.diff(t)))
    if dt <= 0 or not np.isfinite(dt):
        raise ValueError('the median gap of the clock is not positive, so no '
                         'sampling the spectrum could be drawn on.')
    return dt, 1.0 / dt


def _power(t, y, freqs):
    """The one-sided power per frequency bin, with the DC taken out.

    The detrend is the mean, because that is the constant a signal is not
    oscillating at; the power is |FFT|^2 and the Nyquist bin is folded back in,
    so the number read is the same whether the count of samples is even.
    """
    n = len(y)
    detrended = y - y.mean()
    spectrum = np.fft.rfft(detrended)
    power = np.abs(spectrum) ** 2
    if n % 2 == 0:
        power[-1] *= 0.5
    power[0] = 0.0  # the DC bin is the mean, already removed: no power there
    return power


def _topPeaks(t, freqs, power, n_peaks):
    """The leading n peak(s) of the power, most power first, one per bin each.

    A peak a neighbour carries more power than is not a peak on its own, so a
    bin is only a candidate when it is the largest of its immediate two -- the
    same rule the event detector uses. The bin of a flat series is refused up
    front (`spectrum` answers the total first), so a zero-power list never comes
    back.
    """
    total = power.sum()
    if total <= 0 or not np.isfinite(total):
        raise ValueError('the series answers no power off its mean, so there is '
                         'no frequency to lead with. It reads flat.')
    candidates = []
    for i in range(1, len(power)):
        left = power[i - 1] if i - 1 > 0 else -1.0
        right = power[i + 1] if i + 1 < len(power) else -1.0
        if power[i] >= left and power[i] >= right and power[i] > 0:
            candidates.append(i)
    candidates.sort(key=lambda i: power[i], reverse=True)
    freqs = np.asarray(freqs)
    peaks = [{'frequency': float(freqs[i]),
              'period': float(1.0 / freqs[i]) if freqs[i] > 0 else None,
              'power': float(power[i]),
              'fraction': float(power[i] / total)}
             for i in candidates[:n_peaks]]
    return peaks, total


def spectrum(t, y, n_peaks=5):
    """What the series oscillates at, and how much of its power is where.

    Answers the dominant frequency and period, the leading `n_peaks` (most
    power first) with their power and share of the total, and the total. A
    series that is flat, or too short, or not on an increasing clock is refused
    by the reason it is.
    """
    if n_peaks is None or int(n_peaks) < 1:
        raise ValueError('how many peaks is a number from 1; it was %s.'
                         % (n_peaks,))
    t, y = _arrays(t, y)
    dt, fs = _sampling(t)
    freqs = np.fft.rfftfreq(len(y), d=dt)
    power = _power(t, y, freqs)
    peaks, total = _topPeaks(t, freqs, power, int(n_peaks))
    if not peaks:
        raise ValueError('the series answers power, but it is not binned to any '
                         'single frequency here: it is not a set of oscillations '
                         'the leading peak could name.')
    dominant = peaks[0]
    return {'peaks': peaks, 'total_power': float(total),
            'dominant': {'frequency': dominant['frequency'],
                         'period': dominant['period'],
                         'power': dominant['power'],
                         'fraction': dominant['fraction']},
            'samples': int(len(y))}


def band_power(t, y, fmin, fmax):
    """The share of the series' power between `fmin` and `fmax` (inclusive).

    The bounds are in the same Hz the spectrum uses; a band that cannot contain
    a frequency of the grid -- the highest the sampling allows -- is refused by
    the grid it is named against.
    """
    for name, value in (('fmin', fmin), ('fmax', fmax)):
        if value is None or not np.isfinite(value) or value < 0:
            raise ValueError('%s is %s: a band is two non-negative numbers.'
                             % (name, value))
    if fmin > fmax:
        raise ValueError('the lower bound of the band (%g) is above the upper '
                         '(%g); swap them or pick a band that contains a '
                         'frequency.' % (fmin, fmax))
    t, y = _arrays(t, y)
    dt, fs = _sampling(t)
    freqs = np.fft.rfftfreq(len(y), d=dt)
    power = _power(t, y, freqs)
    total = power.sum()
    inBand = float(power[(freqs >= fmin) & (freqs <= fmax)].sum())
    if total <= 0:
        raise ValueError('the series answers no power off its mean, so the share '
                         'a band could hold of it is not a number. It reads flat.')
    return {'fraction': inBand / total,
            'band_power': inBand,
            'total_power': float(total),
            'band': (float(fmin), float(fmax))}


def cross_correlation(t1, y1, t2, y2):
    """How much series 2 lags or leads series 1, and at what they both ring.

    The lag is the offset at which one series, shifted against the other, is
    most alike, answered in both samples and the time that samples is on this
    clock; the coefficient of the peak is the correlation at that offset, and
    the frequency the two agree to oscillate at is the one the cross-spectrum
    rings loudest. Two clocks that do not match -- length, or the spacing of
    the samples -- are a refusal, not a pair to correlate, because a lag read
    off a mis-spaced clock is a number that means nothing.
    """
    if not (len(y1) == len(y2)):
        raise ValueError('the two series answer %d and %d points: a lag is read '
                         'off the matching point, so they must be of one length.'
                         % (len(y1), len(y2)))
    t1, y1 = _arrays(t1, y1)
    t2, y2 = _arrays(t2, y2)
    dt1, fs1 = _sampling(t1)
    dt2, fs2 = _sampling(t2)
    if abs(dt1 - dt2) > 1e-9 * max(dt1, dt2):
        raise ValueError('the two series are spaced %gs apart from one another '
                         '(%gs against %gs): a lag read across that would not be '
                         'a lag. Sample them on one clock.' % (t1[1] - t1[0], dt1, dt2))
    n = len(y1)
    a = y1 - y1.mean()
    b = y2 - y2.mean()
    if np.allclose(a, 0) or np.allclose(b, 0):
        raise ValueError('one of the two series is flat, so the two cannot be '
                         'shifted against one another until one moves.')
    # The cross-correlation of two unit-variance-detrended series, lags
    # [-n/2, n/2], taken by the FFT so a long series does not cost n*n.
    size = 1
    while size < 2 * n:
        size <<= 1
    A = np.fft.rfft(a, size)
    B = np.fft.rfft(b, size)
    lags = np.fft.irfft(B * np.conj(A), size)[:n]
    # The order matters: `B * conj(A)` reads a positive lag as "bring series 2
    # left to land it on series 1", so a series 2 that trails series 1 by k
    # samples answers k. (`A * conj(B)` is the mirror and reports that same
    # alignment as lag 0 while series 1 trails, which is the wrong way round.)
    half = n // 2
    best = int(np.argmax(lags))
    lagIndex = best if best <= half else best - n
    norm = np.sqrt((a ** 2).sum() * (b ** 2).sum()) or 1.0
    corr = float(lags[best] / norm)
    # The frequency both agree to oscillate at: the cross-spectrum magnitude,
    # loudest bin (the DC is not an oscillation, so it is left out).
    cross = np.abs(A * np.conj(B))
    crossFreq = np.fft.rfftfreq(size, d=dt1)
    ringIndex = int(np.argmax(cross[1:]) + 1) if len(cross) > 1 else 0
    dominantFreq = float(crossFreq[ringIndex])
    return {'lag_samples': lagIndex,
            'lag_time': float(lagIndex * dt1),
            'correlation': corr,
            'dominant_shared_frequency': dominantFreq,
            'dominant_shared_period': float(1.0 / dominantFreq) if dominantFreq > 0 else None}
