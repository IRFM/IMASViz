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

"""The spectral surface, run on the one read it already holds.

`test_155` pins the math on a synthetic signal; this pins the wiring around
it, the way `test_153` does for events:

* **spectrum** -- the time read of the leaf, its dominant frequency, its
  leading peaks, and the share of the power a named band holds;
* **cross_correlation** -- how far one probe's read lags another's on the
  shared clock, and at what the two ring, both read off the same `get_signal`;
* **the report** -- the same read, the peaks in a table, on the one page the
  other reports keep.

The stand-in refusals (a band named with one bound) need no case; the rest run
on the reference case and skip when it is not reachable, the way `test_153`
does.
"""

import pytest

from mcp_server.core import McpGuiCore

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI,
                      case_uri_or_skip)

FLUX = 'magnetics.flux_loop[3].flux.data'
BPOLO = 'magnetics.bpol_probe[0].field.data'
IDS_NAME = 'magnetics'

pytestmark = [pytest.mark.case, pytest.mark.ui]


@pytest.fixture(scope='module')
def core(qapp, tmp_path_factory):
    """One self-contained session: the case open and magnetics loaded.

    HOME is patched for the module and undone on the way out, and any figure
    left is closed, the way `test_153` keeps the session clean.
    """
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    home = tmp_path_factory.mktemp('spectrumHome')
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


def test_spectrum_answers_the_time_read_of_the_leaf(core):
    out = core.spectrum(CASE_URI, FLUX)
    assert out['dominant']['frequency'] >= 0
    assert isinstance(out['peaks'], list) and len(out['peaks']) >= 1
    for peak in out['peaks']:
        assert peak['power'] >= 0
        assert 0.0 <= peak['fraction'] <= 1.0
    assert out['samples'] >= 8


def test_spectrum_band_holds_a_share_of_the_power(core):
    out = core.spectrum(CASE_URI, FLUX, band_low=0.0, band_high=1e6)
    assert 0.0 <= out['band']['fraction'] <= 1.0


def test_a_band_named_with_one_bound_is_refused(core):
    with pytest.raises(ValueError, match='both or neither'):
        core.spectrum(CASE_URI, FLUX, band_low=0.0)
    with pytest.raises(ValueError, match='both or neither'):
        core.spectrum(CASE_URI, FLUX, band_high=1.0)


def test_cross_correlation_between_two_probes_on_the_shared_clock(core):
    out = core.cross_correlation(CASE_URI, FLUX, BPOLO)
    assert -1.0 <= out['correlation'] <= 1.0
    assert isinstance(out['lag_samples'], int)
    assert out['dominant_shared_frequency'] >= 0
    if out['dominant_shared_frequency'] > 0:
        assert out['dominant_shared_period'] > 0


def test_a_spectral_report_is_a_page_that_keeps_the_facts(core):
    out = core.spectrum_report(CASE_URI, FLUX, name='t156_spectral')
    path = out['saved_to']
    assert path.endswith('t156_spectral.html')
    with open(path) as file:
        text = file.read()
    assert FLUX in text
    assert 'frequency' in text.lower()
    assert 'dominant' in text.lower()
    assert 0 < out['peaks'] <= 5
