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

from conftest import DATA_DICTIONARIES_DIR, IMAS_TEST_VERSION, REPO_ROOT

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
def test_data_dictionary_is_resolved():
    idsdef = QVizGlobalOperations.getIDSDefFile(IMAS_TEST_VERSION)
    assert os.path.exists(idsdef), 'no data dictionary at ' + str(idsdef)
    assert idsdef.startswith(DATA_DICTIONARIES_DIR)


@pytest.mark.dd
def test_major_version_follows_imas_version():
    assert os.environ['IMAS_MAJOR_VERSION'] == IMAS_TEST_VERSION[:1]
