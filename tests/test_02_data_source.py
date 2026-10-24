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


def test_the_access_layer_major_version_is_no_longer_asked():
    """Nothing asks which Access Layer major version is loaded any more.

    `getVersion()` parsed `AL_VERSION` and every branch that asked it took the
    Access Layer 4 path when it answered 4: an entry built from six positional
    numbers instead of an URI, a `legacy_attributes` dict handed back by
    `build_uri`, an URI box disabled in the GUI. Measured on the stacks this
    application runs on, that answer is 5 — `AL_VERSION` is 5.7.1 here — so
    those branches were dead, and the numbers they carried were read by nothing.
    """
    assert not hasattr(QVizIMASDataSource, 'getVersion')
    source = QVizIMASDataSource('native', CASE_URI)
    assert not hasattr(source, 'legacy_attributes')
    assert not hasattr(source, 'al_version')


def test_a_datasource_starts_without_an_opened_entry():
    dataSource = QVizIMASDataSource('west 54924', CASE_URI)
    assert dataSource.db_entry is None
    assert dataSource.uri == CASE_URI
    assert dataSource.generatedDataTree is None


def test_building_a_uri_from_the_five_parameters():
    """The URI is spelled here now; the Access Layer never had that helper.

    This used to be an xfail: the helper did "from imas import _al_lowlevel as
    ll", and IMAS-Python 2.3.0 exposes no such module, so every call answered
    ImportError -- the *Export to IDS* click and the command line's
    -u -d -s -r -b path among them. The spelling is the one cases on disk are
    opened with. It used to answer a pair, the second element being the
    Access Layer 4 parameters; the URI is the answer now.
    """
    uri = QVizIMASDataSource.build_uri(
        13, 54924, 0, 'g2lfleur', 'west', '3', {})
    assert uri == ('imas:hdf5?user=g2lfleur;shot=54924;run=0;database=west'
                   ';version=3')


@pytest.mark.case
def test_the_reference_case_is_reachable():
    assert case_uri_or_skip() is not None, 'no master.h5 for ' + CASE_URI


@pytest.mark.case
def test_create_dbentry_builds_a_usable_entry_from_its_uri():
    # createDBEntry only builds: the entry it returns is not kept on the source,
    # which reads whatever the registry holds (see test_16).
    dataSource = QVizIMASDataSource('west 54924', CASE_URI)
    entry = dataSource.createDBEntry('r')
    assert entry.mode == 'r'
    entry.close()
