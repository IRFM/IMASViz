# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license is deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The agent surface tells a scalar leaf from a curve, by name.

What it pins, on the reference case (WEST 54924 run 0, `magnetics`
occurrence 0), the way a small local model met this case for real:

* `search_nodes` marks every leaf it answers with a `kind` -- `curve` for
  what runs along an abscissa, `scalar` for one value per element;
* `get_signal` on a scalar leaf is refused **before** the read, in words the
  agent can act on (it names the curve the plot wanted), and not with the
  panel's "no explicit dependency on current X axis", a phrase that leaves
  a model without a panel with nothing to do but retry;
* `plot_one` on the same scalar is refused the same way;
* the real curve `flux_loop(3)/flux/data` still reads back, as the app reads
  it, with more than zero non-zero samples.

The point is the loop the user saw: the model asked for the *index* of a
flux loop, the surface answered with a widget phrase, and it asked the same
leaf again until the turn budget ran out. The refusal it should have
answered -- which leaf is the curve -- is what this file makes it answer.
"""

import pytest

from mcp_server.core import McpGuiCore

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI,
                      case_uri_or_skip)

IDS_NAME = 'magnetics'
CURVE_PATH = 'magnetics/flux_loop(3)/flux/data'
CURVE_NAME = 'magnetics.flux_loop[3].flux.data'

pytestmark = [pytest.mark.case, pytest.mark.ui]


@pytest.fixture(scope='module')
def core(qapp, tmp_path_factory):
    """One session of the core, the case opened and `magnetics` loaded."""
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    home = tmp_path_factory.mktemp('scalarCoreHome')
    patch = pytest.MonkeyPatch()
    patch.setenv('HOME', str(home))
    session = McpGuiCore()
    try:
        session.open_case(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
        session.load_ids(CASE_URI, IDS_NAME, 0)
        yield session, home
    finally:
        patch.undo()


def _scalarEntry(session):
    """A scalar leaf of the branch, picked by name, not by position."""
    found = session.search_nodes(CASE_URI, 'flux_loop')
    for entry in found:
        if (entry.get('data_name') or '').endswith('.index') \
                or 'position' in (entry.get('data_name') or ''):
            return entry
    raise AssertionError('no scalar leaf under flux_loop to refuse')


def test_searching_marks_each_leaf_with_a_kind(core):
    session, _home = core
    found = session.search_nodes(CASE_URI, 'flux_loop')
    assert found, 'the needle names leaves under flux_loop'
    for entry in found:
        assert entry['kind'] in ('curve', 'image', 'scalar'), entry

    curve = next(entry for entry in found
                 if entry['data_name'] == CURVE_NAME)
    assert curve['kind'] == 'curve'

    scalar = _scalarEntry(session)
    assert scalar['kind'] == 'scalar'


def test_get_signal_refuses_a_scalar_leaf_by_name(core):
    """The refusal says what the leaf is and points at the curve.

    It is the answer that ends a retry loop, not the panel's phrase about a
    widget the agent does not hold.
    """
    session, _home = core
    scalar = _scalarEntry(session)
    with pytest.raises(ValueError) as exc:
        session.get_signal(CASE_URI, scalar['path'])
    message = str(exc.value)
    assert 'scalar' in message
    assert 'curve' in message
    # The opaque panel phrase a model reads as "no data, ask again":
    assert 'current X axis' not in message


def test_plot_one_refuses_a_scalar_leaf_by_name(core):
    session, _home = core
    scalar = _scalarEntry(session)
    with pytest.raises(ValueError) as exc:
        session.plot_one(CASE_URI, scalar['path'])
    message = str(exc.value)
    assert 'scalar' in message
    assert 'current X axis' not in message


def test_get_signal_on_the_real_curve_still_reads_back(core):
    """The fix refuses the scalar; it must not touch the curve.

    The same read the panel uses, answered with a curve of more than zero
    non-zero samples -- the number the flux loop holds in this case.
    """
    session, _home = core
    answer = session.get_signal(CASE_URI, CURVE_PATH)
    assert answer.get('kind') == 'curve'
    samples = answer.get('samples')
    assert samples and samples > 0
    non_zero = sum(1 for value in answer.get('y') or [] if value != 0)
    assert non_zero > 0, 'the flux loop is not a flat line in this case'
