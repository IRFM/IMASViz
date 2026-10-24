# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The environment contract the whole suite depends on.

QVizGlobalValues mutates os.environ at import time and QVizGlobalOperations
exits the process when a mandatory variable is missing, so a broken harness must
fail here rather than somewhere inside an unrelated component test.
"""

import os

import pytest

from conftest import IMAS_TEST_VERSION, REPO_ROOT

from imasviz.VizUtils import QVizGlobalOperations, QVizGlobalValues


def test_mandatory_variables_are_present():
    # checkEnvSettings() calls sys.exit() when one is missing, which would show
    # up as a crashed test rather than a clean failure.
    QVizGlobalOperations.checkEnvSettings()


def test_repository_root_is_used_as_viz_home():
    assert os.environ['VIZ_HOME'] == REPO_ROOT
    assert os.path.isdir(os.path.join(os.environ['VIZ_HOME'], 'imasviz'))


def test_production_mode_is_selected():
    assert QVizGlobalValues.TESTING is False


def test_time_series_mappings_are_found():
    assert os.path.isdir(os.environ['TS_MAPPINGS_DIR'])


@pytest.mark.dd
def test_the_harness_dictionary_is_one_the_distribution_bundles():
    # IMAS_VERSION names a data dictionary, and IMAS-Python reads that variable
    # itself (imas.dd_zip). It has to be a version the package carries, which is
    # what the shot view asks of an entry; it names no file on disk.
    from imas import dd_zip

    versions = dd_zip.dd_xml_versions()
    assert IMAS_TEST_VERSION in versions, ('%r is not bundled: %r'
                                           % (IMAS_TEST_VERSION, versions))


def test_no_data_dictionary_file_is_asked_of_the_environment():
    # The shot view used to parse IDSDef_<IMAS_VERSION>.xml, which made
    # IMAS_DATA_DICTIONARIES_DIR mandatory and IMAS_MAJOR_VERSION a derived
    # companion. Neither is read any more, so neither is required: with both
    # absent, checkEnvSettings() -- which answers sys.exit() on a missing
    # variable -- still accepts the environment.
    for gone in ('IMAS_DATA_DICTIONARIES_DIR', 'IMAS_MAJOR_VERSION'):
        assert gone not in os.environ
    assert not hasattr(QVizGlobalOperations, 'getIDSDefFile')
    QVizGlobalOperations.checkEnvSettings()
