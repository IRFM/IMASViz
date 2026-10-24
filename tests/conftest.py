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

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The reference case and the data dictionary the harness declares; both
# overridable from the shell so the suite can follow a different shot or a
# different dictionary.
#
# IMAS_VERSION is the version of the data dictionary, and IMAS-Python reads that
# variable itself (imas.dd_zip): it is not an Access Layer number and it names no
# file. Measured on IMAS-Python/2.3.0, the distribution bundles 35 dictionary
# versions in a zip inside the package -- 3.22.0 through 4.1.1 -- so 4.0.0 is
# available without a checkout of the imas_data_dictionaries repository, which is
# what the harness used to require.
CASE_URI = os.environ.get(
    'IMASVIZ_TEST_URI',
    'imas:hdf5?path=/afs/eufus.eu/g2itmdev/user/g2lfleur/public/imasdb/west/3/54924/0')
IMAS_TEST_VERSION = os.environ.get('IMASVIZ_TEST_IMAS_VERSION', '4.0.0')

# Data dictionary the reference case was written with. The Access Layer loads
# its own default instead (4.1.1 on the current stack) and IMAS-Python refuses
# to read an IDS across a DD major version, so reading that case needs a pin.
CASE_DATA_DICTIONARY_VERSION = os.environ.get('IMASVIZ_TEST_CASE_DD_VERSION', '3.35.0')

# A second case, chosen because it holds a two-dimension leaf inside a static
# array of structures with values in it: hard_x_rays.channel[i1].radiance.data,
# eight energy bands by 808 time samples in every one of 38 channels. The
# reference case has rank 3 leaves and none of them filled, so everything that
# reads a rank 3 quantity off a real case reads this one. Its run 0 holds the
# IDS through links to the runs that carry the data, which is how a case is
# normally opened.
RANK3_CASE_URI = os.environ.get(
    'IMASVIZ_TEST_RANK3_URI',
    'imas:hdf5?path=/afs/eufus.eu/g2itmdev/user/g2lfleur/public/imasdb/west/3/55799/0')
RANK3_CASE_DATA_DICTIONARY_VERSION = os.environ.get(
    'IMASVIZ_TEST_RANK3_DD_VERSION', '3.35.0')

os.environ['VIZ_PRODUCTION'] = '1'
os.environ['VIZ_HOME'] = REPO_ROOT
os.environ['IMAS_VIZ_VERSION'] = os.environ.get('IMAS_VIZ_VERSION', 'test-suite')
os.environ['UDA_DISABLED'] = '1'
os.environ['IMAS_VERSION'] = IMAS_TEST_VERSION
os.environ['TS_MAPPINGS_DIR'] = os.path.join(REPO_ROOT, 'ts_mapping_files')

# No X display on the batch nodes: build every widget offscreen.
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

# The package is imported from the repository root. sys.path is used instead of
# PYTHONPATH on purpose: assigning PYTHONPATH replaces the value exported by the
# IMAS/PySide6 environment modules and their imports then fail.
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def caseOnDisk(uri):
    """Whether a case's pulse files are where the URI says they are.

    A case is a directory of HDF5 files, not something the suite can synthesise,
    so a test that needs one skips rather than fails when it is not mounted.
    """
    return os.path.exists(os.path.join(uri.split('path=', 1)[-1], 'master.h5'))


def case_uri_or_skip():
    """Return the reference case URI, or None when the case is not reachable."""
    return CASE_URI if caseOnDisk(CASE_URI) else None


def rank3_case_uri_or_skip():
    """Return the rank 3 case URI, or None when that shot is not reachable."""
    return RANK3_CASE_URI if caseOnDisk(RANK3_CASE_URI) else None


@pytest.fixture(autouse=True)
def _every_plot_frame_outlives_its_test(request):
    """A frame a test builds must still be alive when that test is done.

    The application holds the frames it draws in `Viz_API.figureframes`; a test
    has no such holder, so the frame dies with the test's locals and Shiboken
    deletes the C++ object underneath a paint event Qt may still owe it. What
    that costs was measured before this fixture existed: of the 110 plot frames
    a run built, 79 lost their wrapper before the run ended, and the run died
    with a segmentation fault inside pyqtgraph's GraphicsView.paintEvent -- in a
    test several files away from the one that dropped the frame, at a fixed
    position, only under some allocation timings.

    Checking here, at the teardown of the test that built it, names that test
    instead. The recording keeps weak references only: it cannot be what keeps a
    frame alive, which is the difference between measuring this and hiding it.
    """
    from support import ownership

    ownership.builtDuring(request.node.nodeid)
    ownership.watchOfPlotFrames()
    yield
    dead = ownership.deadFrames()
    assert not dead, ('a plot frame went away while Qt can still owe it a paint '
                      'event: ' + ownership.describe(dead)
                      + ' -- hold one with support.ownership.keep(...), or close '
                        'it the way the production refusal paths do')
