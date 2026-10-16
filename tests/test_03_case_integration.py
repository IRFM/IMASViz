# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Integration against the reference IMAS case.

The whole module is skipped when the case is not reachable, so the rest of the
suite still runs where the WEST database is absent. The case is opened through
the URI form used by QVizIMASDataSource.createDBEntry() (QVizIMASDataSource.py:130).
"""

import imas
import pytest

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip)

pytestmark = pytest.mark.case


@pytest.fixture(scope='module')
def case_uri():
    uri = case_uri_or_skip()
    if uri is None:
        pytest.skip('no master.h5 for ' + CASE_URI)
    return uri


@pytest.fixture
def case_entry(case_uri):
    entry = imas.DBEntry(case_uri, 'r')
    yield entry
    entry.close()


@pytest.fixture
def pinned_case_entry(case_uri):
    entry = imas.DBEntry(case_uri, 'r', dd_version=CASE_DATA_DICTIONARY_VERSION)
    yield entry
    entry.close()


def test_the_case_is_opened_read_only(case_entry):
    assert case_entry.mode == 'r'


def test_the_occurrences_of_an_ids_are_listed(case_entry):
    assert case_entry.list_all_occurrences('equilibrium') == [0, 1, 2, 3]
    assert case_entry.list_all_occurrences('tf') == [0]


def test_filled_paths_are_listed(pinned_case_entry):
    paths = pinned_case_entry.list_filled_paths('equilibrium', 0)
    assert len(paths) > 0
    assert 'time' in paths


@pytest.mark.xfail(strict=True, reason=(
    "with the harness data dictionary (IMAS_VERSION=3.23.3) loaded, the Access "
    "Layer raises packaging InvalidVersion \"+1\" on list_filled_paths for this "
    "case, which was written with DD 3.35.0; opening the entry with "
    "dd_version=3.35.0 works, see test_filled_paths_are_listed"))
def test_listing_paths_across_data_dictionary_versions_fails(case_entry):
    case_entry.list_filled_paths('equilibrium', 0)


def test_the_access_layer_defaults_to_its_own_data_dictionary(case_entry):
    assert case_entry.dd_version != CASE_DATA_DICTIONARY_VERSION


def test_reading_needs_the_data_dictionary_of_the_case(case_entry):
    # IMAS-Python refuses to read an IDS whose stored DD has another major
    # version than the one the Access Layer loaded.
    with pytest.raises(RuntimeError, match='different major version'):
        case_entry.get('tf', 0)


def test_reading_with_the_pinned_data_dictionary_yields_an_ids(pinned_case_entry):
    ids = pinned_case_entry.get('tf', 0)
    assert type(ids).__name__ == 'IDSToplevel'
    assert pinned_case_entry.dd_version == CASE_DATA_DICTIONARY_VERSION


def test_the_app_layer_opens_the_case_from_its_uri(case_uri):
    from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource

    dataSource = QVizIMASDataSource('west 54924', case_uri)
    dataSource.createDBEntry('r')
    assert dataSource.db_entry is not None
    assert dataSource.db_entry.list_all_occurrences('equilibrium') == [0, 1, 2, 3]
    dataSource.db_entry.close()
