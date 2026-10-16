# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Test harness for IMASViz.

The package configures itself from the environment at import time:
QVizGlobalValues reads os.environ and can sys.exit() on a missing variable, and
QVizGlobalOperations.checkEnvSettings() does the same. Everything the suite
needs is therefore set here, at conftest import time, before any test module
imports imasviz.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Data dictionary and reference case; overridable from the shell so the suite
# can follow a different IMAS version or a different shot.
DATA_DICTIONARIES_DIR = os.environ.get(
    'IMASVIZ_TEST_DD_DIR',
    '/afs/eufus.eu/g2itmdev/user/g2lfleur/viz/imas_data_dictionaries')
CASE_URI = os.environ.get(
    'IMASVIZ_TEST_URI',
    'imas:hdf5?path=/afs/eufus.eu/g2itmdev/user/g2lfleur/public/imasdb/west/3/54924/0')
IMAS_TEST_VERSION = os.environ.get('IMASVIZ_TEST_IMAS_VERSION', '3.23.3')

# Data dictionary the reference case was written with. The Access Layer loads
# its own default instead (4.1.1 on the current stack) and IMAS-Python refuses
# to read an IDS across a DD major version, so reading that case needs a pin.
CASE_DATA_DICTIONARY_VERSION = os.environ.get('IMASVIZ_TEST_CASE_DD_VERSION', '3.35.0')

os.environ['VIZ_PRODUCTION'] = '1'
os.environ['VIZ_HOME'] = REPO_ROOT
os.environ['IMAS_VIZ_VERSION'] = os.environ.get('IMAS_VIZ_VERSION', 'test-suite')
os.environ['UDA_DISABLED'] = '1'
os.environ['IMAS_VERSION'] = IMAS_TEST_VERSION
os.environ['IMAS_MAJOR_VERSION'] = IMAS_TEST_VERSION[:1]
os.environ['IMAS_DATA_DICTIONARIES_DIR'] = DATA_DICTIONARIES_DIR
os.environ['TS_MAPPINGS_DIR'] = os.path.join(REPO_ROOT, 'ts_mapping_files')

# No X display on the batch nodes: build every widget offscreen.
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

# The package is imported from the repository root. sys.path is used instead of
# PYTHONPATH on purpose: assigning PYTHONPATH replaces the value exported by the
# IMAS/PySide6 environment modules and their imports then fail.
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def case_uri_or_skip():
    """Return the reference case URI, or None when the case is not reachable."""
    path = CASE_URI.split('path=', 1)[-1]
    return CASE_URI if os.path.exists(os.path.join(path, 'master.h5')) else None
