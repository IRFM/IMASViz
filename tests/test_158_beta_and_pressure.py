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

"""The two remaining feature-3 derived quantities, read off the case.

`test_157` pinned the Greenwald fraction from its formula and the surface that
reads it. These two do not manufacture a number: the case keeps them, and the
methods here name the leaf that holds them --

* **beta_normal** -- the normalized beta over the time the case holds it, read
  off the leaf the case stores for it (the default is
  `equilibrium.time_slice[0].global_quantities.beta_normal`);
* **total_pressure** -- the total p = n_e k_B T_e + n_i k_B T_i profile, read
  off the leaf the case stores for it (the default is the total the equilibrium
  case keeps, `profiles_1d.pressure`).

What each proves: the path that answered (the default, or the one the caller
named), the values read, and the mean/max/min that come out of those values --
not a plausible-looking curve. A case that does not hold a leaf the caller
named is refused by name, which is what a wrong path reads back. This is wiring
and the read, pinned on the reference case, not a physics assertion on the two
numbers.
"""

import pytest

from mcp_server.core import McpGuiCore
from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI,
                      case_uri_or_skip)

BETA_LEAF = 'equilibrium.time_slice[0].global_quantities.beta_normal'
PRESSURE_LEAF = 'equilibrium.time_slice[0].profiles_1d.pressure'


@pytest.fixture(scope='module')
def derived_core(qapp, tmp_path_factory):
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    home = tmp_path_factory.mktemp('derivedHome')
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


# -----------------------------------------------------------------------------
# beta_normal
# -----------------------------------------------------------------------------

@pytest.mark.case
@pytest.mark.ui
def test_beta_normal_reads_the_leaf_the_case_keeps(derived_core):
    out = derived_core.beta_normal(CASE_URI)

    assert out['path'] == BETA_LEAF
    assert out['points'] >= 1
    assert len(out['beta_normal']) == out['points']

    # the stats are the ones that come out of the case's own values, not a
    # guess: the finite max/min bound them and the mean sits between them
    finite = [v for v in out['beta_normal'] if v == v]
    assert finite, 'the reference case holds a finite beta_normal leaf'
    assert out['max'] == max(finite)
    assert out['min'] == min(finite)
    assert out['min'] <= out['mean'] <= out['max']


@pytest.mark.case
@pytest.mark.ui
def test_beta_normal_is_the_same_read_a_figure_of_that_leaf_draws(derived_core):
    out = derived_core.beta_normal(CASE_URI)
    read = derived_core.get_signal(CASE_URI, BETA_LEAF, along=None)
    want = list(read['y'])
    assert out['beta_normal'] == want


@pytest.mark.case
@pytest.mark.ui
def test_beta_normal_on_a_leaf_not_in_the_case_is_refused(derived_core):
    with pytest.raises(ValueError):
        derived_core.beta_normal(CASE_URI, path='not.a.real.beta_leaf')


# -----------------------------------------------------------------------------
# total_pressure
# -----------------------------------------------------------------------------

@pytest.mark.case
@pytest.mark.ui
def test_total_pressure_reads_the_leaf_the_case_keeps(derived_core):
    out = derived_core.total_pressure(CASE_URI)

    assert out['path'] == PRESSURE_LEAF
    assert out['points'] >= 1
    assert len(out['pressure']) == out['points']

    finite = [v for v in out['pressure'] if v == v]
    assert finite, 'the reference case holds a finite total pressure leaf'
    assert out['max'] == max(finite)
    assert out['min'] == min(finite)
    assert out['min'] <= out['mean'] <= out['max']


@pytest.mark.case
@pytest.mark.ui
def test_total_pressure_is_the_same_read_a_figure_of_that_leaf_draws(derived_core):
    out = derived_core.total_pressure(CASE_URI)
    read = derived_core.get_signal(CASE_URI, PRESSURE_LEAF, along=None)
    assert out['pressure'] == list(read['y'])


@pytest.mark.case
@pytest.mark.ui
def test_total_pressure_on_a_leaf_not_in_the_case_is_refused(derived_core):
    with pytest.raises(ValueError):
        derived_core.total_pressure(CASE_URI, path='not.a.real.pressure_leaf')
