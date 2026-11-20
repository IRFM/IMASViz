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

"""Trend arithmetic over a series of per-shot values.

The numpy-free companion of `detect.py` and `spectra.py`: it takes the
per-shot values a caller read off its shots -- one number in the caller's
campaign order, as `campaign` hands it -- and answers what the series
says: the least-squares slope over the shot index, first to last change,
min and max with the shot each came from, and a one-word direction.
Nothing here reads a case.
"""

import math


def trend(values, labels=None):
    """The trend of a series of per-shot numbers.

    `values` is the list of per-shot values, in the caller's campaign
    order; `labels` the same-length list the values are keyed by, so the
    min and max can name which shot each came from. A series that does not
    hold at least two finite numbers -- or that holds all the same one --
    is refused by name: one shot is a value, and an equal-valued campaign
    is the same answer repeated, not a trend to say rising or falling.
    """
    if values is None:
        raise ValueError('a trend is asked of the values it runs on: '
                         'name the per-shot series.')
    values = list(values)
    if len(values) < 2:
        raise ValueError(
            'a trend is asked of at least two shots; %s answers one.'
            % len(values))
    if labels is not None:
        labels = list(labels)
        if len(labels) != len(values):
            raise ValueError('labels holds %d and values %d: they are read'
                             ' over the same shots, so name the same number.'
                             % (len(labels), len(values)))
    finite = []
    for i, v in enumerate(values):
        if v is None:
            raise ValueError(
                'value %d is None: every shot of a trend must answer a '
                'number, and this did not.' % i)
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError('value %d is %r: a number the shot answers, '
                             'not a word or a flag.' % (i, v))
        if not math.isfinite(v):
            raise ValueError(
                'value %d is not finite (%r): a trend is asked of the '
                'shots the case answered, not one that held none.' % (i, v))
        finite.append(float(v))
    if all(v == finite[0] for v in finite):
        raise ValueError(
            'every shot answers %g: a flat campaign is one value over its '
            'shots, not a trend to say rising or falling.' % finite[0])
    n = len(finite)
    mean_x = (n - 1) / 2.0
    mean_y = sum(finite) / n
    numerator = sum((i - mean_x) * (v - mean_y)
                    for i, v in enumerate(finite))
    denominator = sum((i - mean_x) * (i - mean_x)
                      for i in range(n))
    slope = numerator / denominator
    first, last = finite[0], finite[-1]
    change = last - first
    if last > first:
        direction = 'rising'
    elif last < first:
        direction = 'falling'
    else:
        direction = 'flat'
    lo, hi = min(finite), max(finite)
    return {
        'count': n,
        'labels': list(labels) if labels is not None else None,
        'values': finite,
        'first': first,
        'last': last,
        'change': change,
        'slope': slope,              # per shot index, in the caller's order
        'min': lo,
        'max': hi,
        'argmin': finite.index(lo),
        'argmax': finite.index(hi),
        'direction': direction,
    }


__all__ = ['trend']
