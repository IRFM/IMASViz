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

"""The Greenwald fraction, on its formula and on the surface that reads it.

`test_155` pins the spectrum arithmetic; this does it for the derived-quantity
side. Two halves:

* **the formula** -- `f_G = n_e / n_G` with `n_G = (I_pl/A)x1e20`, pinned
  exactly on a known triple, and refused the way the formula is refused:
  a flat input, a length mismatch, no finite row;
* **the surface** -- three leaves named by the caller, read the way a figure
  of the same leaves draws (`get_signal`, the value they show), and the ratio
  that comes out is the one the three answer, not one of the three alone.

The surface uses three leaves the reference case holds; what it proves is the
plumbing (three reads, one pointwise ratio, a refusal the case can answer),
not the specific physics of the triple.
"""

import pytest

from imasviz.VizAnalysis.spectra import greenwald_fraction
from mcp_server.core import McpGuiCore
from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI,
                      case_uri_or_skip)

# -----------------------------------------------------------------------------
# 1. the formula, pinned exactly on a known triple
# -----------------------------------------------------------------------------

def test_the_formula_on_a_known_triple():
    # n_e = 1e20 m^-3, I_pl = 77 MA = 77000 A, A = 0.025 m^2
    ne, ip, area = [1e20], [77000.0 / 1e6], [0.025]
    out = greenwald_fraction(ne, ip, area)
    assert out['points'] == 1
    expected_limit = (ip[0] / area[0]) * 1e20
    assert out['greenwald_limit'] == [expected_limit]
    expected_fg = ne[0] / expected_limit
    assert out['greenwald_fraction'] == [expected_fg]


def test_a_flat_density_series_is_refused():
    with pytest.raises(ValueError, match='flat'):
        greenwald_fraction([0.0, 0.0], [77.0, 77.0], [0.025, 0.025])


def test_three_series_of_different_length_are_refused():
    with pytest.raises(ValueError, match='one length'):
        greenwald_fraction([1e20, 2e20], [77.0], [0.025])


def test_no_finite_row_is_refused():
    with pytest.raises(ValueError, match='none'):
        greenwald_fraction([float('nan')] * 2,
                           [77.0, 77.0], [0.025, 0.025])


# -----------------------------------------------------------------------------
# 2. the surface: three leaves, one pointwise ratio
# -----------------------------------------------------------------------------

# Three 49-point time leaves the reference case holds. `volume` stands in for
# n_e here -- the test is verifying the wiring (three reads, one pointwise
# division, a named refusal), not the physics of the specific triple.
NE_LEAF = 'equilibrium.time_slice[0].global_quantities.volume'
IP_LEAF = 'equilibrium.time_slice[0].global_quantities.ip'
AREA_LEAF = 'equilibrium.time_slice[0].global_quantities.area'


@pytest.fixture(scope='module')
def greenwald_core(qapp, tmp_path_factory):
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    home = tmp_path_factory.mktemp('greenwaldHome')
    patch = pytest.MonkeyPatch()
    patch.setenv('HOME', str(home))
    session = McpGuiCore()
    session.open_case(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
    session.load_ids(CASE_URI, 'equilibrium', 0)
    try:
        yield session
    finally:
        for key in list(getattr(session.api, 'figureframes', []) or {}):
            try:
                session.close_window(key)
            except Exception:
                pass
        patch.undo()


@pytest.mark.case
@pytest.mark.ui
def test_greenwald_reads_three_leaves_and_divides_pointwise(greenwald_core):
    ne = greenwald_core.get_signal(CASE_URI, NE_LEAF, along=None)
    ip = greenwald_core.get_signal(CASE_URI, IP_LEAF, along=None)
    area = greenwald_core.get_signal(CASE_URI, AREA_LEAF, along=None)

    out = greenwald_core.greenwald(CASE_URI, NE_LEAF, IP_LEAF, AREA_LEAF)

    n_e = list(ne['y'])
    i_p = list(ip['y'])
    a_r = list(area['y'])
    expected = [n_e[i] / ((i_p[i] / a_r[i]) * 1e20)
                for i in range(len(out['greenwald_fraction']))]

    assert len(out['greenwald_fraction']) >= 1
    for got, want in zip(out['greenwald_fraction'], expected):
        assert got == pytest.approx(want, rel=1e-6)
    assert out['n_e_path'] == NE_LEAF
    assert out['ip_path'] == IP_LEAF
    assert out['area_path'] == AREA_LEAF


@pytest.mark.case
@pytest.mark.ui
def test_greenwald_on_a_leaf_not_in_the_case_is_refused(greenwald_core):
    with pytest.raises(ValueError):
        greenwald_core.greenwald(
            CASE_URI, 'not.a.real.density_leaf', IP_LEAF, AREA_LEAF)
