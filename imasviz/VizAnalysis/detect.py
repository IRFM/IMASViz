# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Find events in one time series, in pure numpy.

A signal the surface already reads (the `x` and `y` of `get_signal`) is all
this layer takes. It answers *events of one kind*:

* `peaks` -- sharp excursions away from the baseline, up (`mode='max'`, ELM)
  or down (`mode='min'`, sawtooth crash). Gated by **prominence** (how far
  the excursion rises above the nearest lower contour), with an optional
  value `threshold` and a minimum sample spacing. No scipy: prominence is
  the contour the walk answers, the way `get_signal` keeps to the read.
* `transitions` -- threshold crossings (L-H, H-L, or either) with an
  optional hysteresis band so a wobbling signal does not re-trigger.

`detect` is the dispatch a caller asks: one `kind` word, the signal, and
the kind's own parameters, answered as one normalized block -- the events in
time order, their count, and the period statistics of the times. A refusal
is never silent: a flat signal, a signal too short to carry an event, or a
parameter outside its domain answers a `ValueError` that names what it tried,
the way the rest of the package refuses. No Qt, no IMAS: a test drives it on
a synthetic signal, and the core asks it on the read it already holds.
"""

import math

# ---------------------------------------------------------------------------
# the read this layer takes: one time axis, one value axis, same length
# ---------------------------------------------------------------------------

def _arrays(t, y):
    """The two axes usable: finite, one-dimensional, the same length.

    The non-number entries (a `nan` gap the read can hold) are dropped only
    where the *pair* breaks -- a hole in `y` with a live `t` is refused by
    name rather than read as the value before it.
    """
    import numpy as np

    def one(axis, name):
        try:
            out = np.asarray(axis, dtype=float).reshape(-1)
        except (TypeError, ValueError):
            raise ValueError(
                'The %s axis is %r: a numeric series of one dimension is '
                'what an event is read on.' % (name, axis))
        return out

    t = one(t, 'time')
    y = one(y, 'value')
    if t.size != y.size:
        raise ValueError(
            'The time axis answers %d sample(s), the value axis %d: an '
            'event is read on pairs, so the two must be the same length '
            '(get_signal answers them together).' % (t.size, y.size))
    if t.size < 2:
        raise ValueError(
            'The signal holds %d sample(s): a peak and a transition both need '
            'a neighbour to be read against, so at least two.' % t.size)
    if not (np.isfinite(t).all() and np.isfinite(y).all()):
        raise ValueError(
            'The signal holds %d non-number entr%s: an event is read on the '
            'finite pairs, so the gaps must go first.'
            % (int((~(np.isfinite(t) & np.isfinite(y))).sum()),
               'y' if (np.isfinite(t) & np.isfinite(y)).sum() == 1 else 'ies'))
    return t, y


def _is_number(value, name):
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(float(value)))


# ---------------------------------------------------------------------------
# peaks
# ---------------------------------------------------------------------------

def _local_maxima(top):
    """The indices of the local maxima of `top`, one per plateau.

    A run of equal samples that sits above both its neighbours counts once,
    reported at its rightmost sample -- so a flat ELM top is not missed, and
    a strict single sample is not doubled. `top` is already the shape to look
    for (the signal, or its inverse, for a down crash).
    """
    n = len(top)
    out = []
    i = 0
    while i < n:
        if i > 0 and top[i] <= top[i - 1]:
            i += 1
            continue
        level = top[i]
        j = i
        while j + 1 < n and top[j + 1] == level:
            j += 1
        rises_before = (i == 0) or (top[i - 1] < level)
        drops_after = (j == n - 1) or (top[j + 1] < level)
        if rises_before and drops_after:
            out.append(j)
        i = (j + 1) if j > i else (i + 1)
    return out


def _is_local_max_at(j, top):
    """Whether the sample at `j` is a strict local maximum."""
    n = len(top)
    if j == 0:
        return n > 1 and top[0] > top[1]
    if j == n - 1:
        return n > 1 and top[-1] > top[-2]
    return top[j] > top[j - 1] and top[j] > top[j + 1]


def _prominence(i, top):
    """How far the peak at `i` rises above the nearest lower contour.

    The contour on one side is the lowest level met walking out from the peak
    until a peak as high as this one (or the edge of the signal): the erosion
    level the peak survives, and the prominence is the peak minus the higher
    of the two sides -- exactly what gates a real ELM off the ripple under it.
    """
    peak = top[i]
    n = len(top)
    left = peak
    for j in range(i - 1, -1, -1):
        if _is_local_max_at(j, top) and top[j] >= peak:
            break
        if top[j] < left:
            left = top[j]
    right = peak
    for j in range(i + 1, n):
        if _is_local_max_at(j, top) and top[j] >= peak:
            break
        if top[j] < right:
            right = top[j]
    return peak - max(left, right)


def peaks(t, y, mode='max', threshold=None, prominence=None, min_distance=0):
    """The sharp excursions of the signal, as events in time order.

    `mode` `'max'` (default) looks for the excursions up -- an ELM -- and
    `'min'` for the crashes down -- a sawtooth. `threshold`, when it is a
    number, is a floor on the *value* the peak sits at (a peak below it is
    not reported); it is a gate on the level, not the prominence. `prominence`
    is the gate on how far the excursion rises off the baseline; left out it
    is derived as three tenths of the signal's finite peak-to-peak, and an
    all-flat signal (the peak-to-peak is zero) is refused by name rather than
    read. `min_distance` keeps the most prominent of peaks closer together
    than that many samples apart.
    """
    import numpy as np

    t, y = _arrays(t, y)
    if mode not in ('max', 'min'):
        raise ValueError(
            '`mode` is %r: `max` (an excursion up, an ELM) or `min` (a crash '
            'down, a sawtooth).' % (mode,))
    if threshold is not None and not _is_number(threshold, 'threshold'):
        raise ValueError(
            '`threshold` is %r: a finite number the peak must sit at or past.'
            % (threshold,))
    if prominence is not None and not _is_number(prominence, 'prominence'):
        raise ValueError(
            '`prominence` is %r: a finite number the excursion must rise past.'
            % (prominence,))
    if not _is_number(min_distance, 'min_distance') or float(min_distance) < 0:
        raise ValueError(
            '`min_distance` is %r: a non-negative number of samples the peaks '
            'must stay apart by.' % (min_distance,))

    top = y if mode == 'max' else -y
    if prominence is None:
        finite = y[np.isfinite(y)]
        p2p = float(finite.max() - finite.min())
        if p2p <= 0.0:
            raise ValueError(
                'The signal is flat (its finite peak-to-peak is '
                '%g): a flat trace carries no excursion to read.' % (p2p,))
        prominence = 0.3 * p2p
    prominence = float(prominence)

    events = []
    for i in _local_maxima(top):
        p = _prominence(i, top)
        value = float(y[i])
        if threshold is not None:
            if mode == 'max' and value < threshold:
                continue
            if mode == 'min' and value > threshold:
                continue
        if p < prominence:
            continue
        events.append((i, p, value))

    if min_distance and float(min_distance) > 0:
        # near peaks keep the most prominent of the cluster at the spacing
        spacing = float(min_distance)
        events.sort(key=lambda e: -e[1])
        kept = []
        taken = []
        for i, p, value in events:
            if any(abs(i - k) < spacing for k in taken):
                continue
            taken.append(i)
            kept.append((i, p, value))
        events = kept
    events.sort(key=lambda e: float(t[e[0]]))
    return [{'index': int(i),
             't': float(t[i]),
             'value': float(value),
             'prominence': float(p)}
            for i, p, value in events]


# ---------------------------------------------------------------------------
# transitions
# ---------------------------------------------------------------------------

def transitions(t, y, threshold=None, direction='up', hysteresis=None):
    """The crossings of one level, as events in time order.

    `threshold` is the level crossed; left out it is derived as the median
    of the finite values, and an all-flat signal is refused by name.
    `direction` `'up'` (L-H, the signal rising through the level), `'down'`
    (H-L), or `'both'`. `hysteresis`, when a number, is the band the signal
    must clear on the far side before it may re-trigger the same direction,
    so a signal wobbling about the level does not count an event a sample at
    a time.
    """
    import numpy as np

    t, y = _arrays(t, y)
    if direction not in ('up', 'down', 'both'):
        raise ValueError(
            '`direction` is %r: `up` (L-H), `down` (H-L), or `both`.'
            % (direction,))
    if threshold is None:
        finite = y[np.isfinite(y)]
        if (finite.max() - finite.min()) <= 0.0:
            raise ValueError(
                'The signal is flat (its finite peak-to-peak is '
                '%g): nothing crosses a level.'
                % (finite.max() - finite.min()))
        threshold = float(np.median(finite))
    else:
        if not _is_number(threshold, 'threshold'):
            raise ValueError(
                '`threshold` is %r: a finite number the level sits at.'
                % (threshold,))
    threshold = float(threshold)
    if hysteresis is None:
        hysteresis = 0.0
    else:
        if not _is_number(hysteresis, 'hysteresis') or float(hysteresis) < 0:
            raise ValueError(
                '`hysteresis` is %r: a non-negative number the signal must '
                'clear off the level before it re-triggers.'
                % (hysteresis,))
        hysteresis = float(hysteresis)

    # A crossing is one direction at a time: below->above is an up, and the
    # signal must get back to the other side before it may cross up again.
    # Hysteresis widens the re-arm: once a direction has fired, it arms for
    # that direction again only when the signal clears the far side by the
    # band (below threshold-h to arm up, above threshold+h to arm down), so
    # a signal wobbling about the level does not count an event a sample at
    # a time.
    events = []
    armed_up = float(y[0]) < threshold
    armed_down = float(y[0]) >= threshold
    for i in range(1, len(t)):
        prev = float(y[i - 1])
        cur = float(y[i])
        if armed_up and prev < threshold <= cur:
            if direction in ('up', 'both'):
                events.append({'index': int(i), 't': float(t[i]),
                               'value': cur, 'direction': 'up'})
            armed_up = False
            armed_down = True
        elif armed_down and prev >= threshold > cur:
            if direction in ('down', 'both'):
                events.append({'index': int(i), 't': float(t[i]),
                               'value': cur, 'direction': 'down'})
            armed_down = False
            armed_up = True
        elif hysteresis > 0.0:
            if not armed_up and cur <= threshold - hysteresis:
                armed_up = True
            if not armed_down and cur >= threshold + hysteresis:
                armed_down = True
    return events


def period_stats(times):
    """The timing of the events of one kind, from their times.

    `count` how many, `span` the distance first to last, and `period_mean` /
    `period_std` / `period_min` / `period_max` the spacing between them. A
    single event has no spacing to stat: the period fields answer `None` and
    the count stays, so the caller says one event of one kind, not zero.
    """
    import numpy as np

    arr = np.asarray(times, dtype=float).reshape(-1)
    if arr.size == 0:
        return {'count': 0, 'span': None, 'period_mean': None,
                'period_std': None, 'period_min': None, 'period_max': None,
                'mean_rate_hz': None}
    span = float(arr[-1] - arr[0])
    if arr.size < 2:
        return {'count': int(arr.size), 'span': span, 'period_mean': None,
                'period_std': None, 'period_min': None, 'period_max': None,
                'mean_rate_hz': None}
    diffs = np.diff(arr)
    diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
    if diffs.size == 0:
        return {'count': int(arr.size), 'span': span, 'period_mean': None,
                'period_std': None, 'period_min': None, 'period_max': None,
                'mean_rate_hz': None}
    mean = float(diffs.mean())
    return {'count': int(arr.size), 'span': span,
            'period_mean': mean,
            'period_std': float(diffs.std()),
            'period_min': float(diffs.min()),
            'period_max': float(diffs.max()),
            'mean_rate_hz': (1.0 / mean) if mean > 0 else None}


# ---------------------------------------------------------------------------
# the dispatch
# ---------------------------------------------------------------------------

def detect(kind, t, y, **parameters):
    """One kind of event read off the signal, answered as one block.

    `kind` `'elm'` (an excursion up), `'sawtooth'` (a crash down), or
    `'lh'` (a threshold crossing). `t` and `y` are the two axes `get_signal`
    hands over. The block answers `kind`, the events in time order (each its
    `t`, its `value`, and what gated it), the `count`, and the `period` of
    the event times. A parameter the kind does not take is refused by name,
    not silently dropped, the way the surface refuses a stray argument.
    """
    kind = (kind or '').strip().lower()
    if kind in ('elm', 'e'):
        allowed = ('threshold', 'prominence', 'min_distance')
    elif kind in ('sawtooth', 'saw', 'crash'):
        allowed = ('threshold', 'prominence', 'min_distance')
    elif kind in ('lh', 'l_h', 'mode', 'transition'):
        allowed = ('threshold', 'direction', 'hysteresis')
    else:
        raise ValueError(
            '`kind` is %r: `elm`, `sawtooth`, or `lh`, the kinds of event '
            'one asks this read for.' % (kind,))
    stray = sorted(set(parameters) - set(allowed))
    if stray:
        raise ValueError(
            '`%s` takes %s: %r is not among them.'
            % (kind, ', '.join(allowed), stray))
    if kind in ('elm', 'e'):
        events = peaks(t, y, mode='max', **parameters)
    elif kind in ('sawtooth', 'saw', 'crash'):
        events = peaks(t, y, mode='min', **parameters)
    else:
        events = transitions(t, y, **parameters)
    return {'kind': kind,
            'count': len(events),
            'events': events,
            'period': period_stats([e['t'] for e in events])}
