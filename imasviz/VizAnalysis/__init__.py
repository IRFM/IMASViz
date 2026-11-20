# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
# __init__.py
"""Physical analysis of the signals the surface already reads.

`detect` is the pure layer -- no Qt, no IMAS, numpy only -- that finds
events (ELM, sawtooth, L-H transitions) in a time series and stats their
timing. It is driven by a test on a synthetic signal, and the agent core
(then the GUI, then a report) ask it through the one read `get_signal`
already gives, so what is detected and what is plotted are the same read.
"""

from .spectra import band_power, cross_correlation, spectrum

__all__ = ['detect', 'peaks', 'transitions', 'period_stats',
           'spectrum', 'band_power', 'cross_correlation']
