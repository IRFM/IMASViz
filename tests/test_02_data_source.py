# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""VizDataSource: the URI/DBEntry layer that opens a case.

With AL5 the datasource opens a case through the URI form of the Access Layer,
imas.DBEntry(uri, mode), so the reference case is enough to exercise it.
"""

import pytest

from conftest import CASE_URI, case_uri_or_skip

from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource


def test_the_access_layer_major_version_is_derived(monkeypatch):
    monkeypatch.setenv('AL_VERSION', '5.7.1-foss-2023b')
    assert QVizIMASDataSource.getVersion() == 5

    monkeypatch.setenv('AL_VERSION', '4.9.3')
    assert QVizIMASDataSource.getVersion() == 4


def test_a_missing_access_layer_version_is_reported(monkeypatch):
    monkeypatch.delenv('AL_VERSION', raising=False)
    with pytest.raises(ValueError):
        QVizIMASDataSource.getVersion()


def test_a_datasource_starts_without_an_opened_entry():
    dataSource = QVizIMASDataSource('west 54924', CASE_URI)
    assert dataSource.db_entry is None
    assert dataSource.uri == CASE_URI
    assert dataSource.generatedDataTree is None


@pytest.mark.xfail(strict=True, reason=(
    "build_legacy_uri does 'from imas import _al_lowlevel as ll' "
    "(QVizIMASDataSource.py:45) but IMAS-Python 2.3.0 exposes no _al_lowlevel, "
    "so URI building from legacy parameters raises ImportError"))
def test_building_a_uri_from_legacy_parameters():
    uri, attributes = QVizIMASDataSource.build_uri(
        13, 54924, 0, 'g2lfleur', 'west', '3', {})
    assert 'hdf5' in uri


@pytest.mark.case
def test_the_reference_case_is_reachable():
    assert case_uri_or_skip() is not None, 'no master.h5 for ' + CASE_URI


@pytest.mark.case
def test_create_dbentry_opens_the_case_from_its_uri():
    dataSource = QVizIMASDataSource('west 54924', CASE_URI)
    dataSource.createDBEntry('r')
    assert dataSource.db_entry is not None
    assert dataSource.db_entry.mode == 'r'
    dataSource.db_entry.close()
