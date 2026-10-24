# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""What the application answers when the python HLI in charge is not IMAS-Python.

A node that loaded the generated HLI (`IMAS-AL-Python`) instead of IMAS-Python
used to die on the first leaf import that needs the metadata reflection API, with
a traceback naming neither the package that was loaded nor what to load:

    File ".../VizDataAccess/VizTimeSlices/__init__.py", line 3, in <module>
      from .QVizTimeSliceSelection import *
    File ".../VizTimeSlices/QVizTimeSliceSelection.py", line 40, in <module>
      from imas.ids_data_type import IDSDataType
    ModuleNotFoundError: No module named 'imas.ids_data_type'

`import imas` succeeds there -- that HLI exports `DBEntry`, `IDSName`, `IDSBase`
and one module per IDS -- so the refusal cannot hang on `import imas` either. It
hangs on the two names the walk actually needs, asked once in
`QVizAccessLayerHLI`, and it has to be measured in a **child process**: the
refusal happens during import and takes the process down, which in this suite
would end the run rather than the test.

The stub below mirrors the generated HLI as measured on
`/gw/swimas/software/IMAS-AL-Python/5.4.0-foss-2023b-DD-3.42.0`: `DBEntry`,
`IDSName`, `IDSBase`, `__version__` absent, and neither `IDSDataType` nor
`IDSStructArray` anywhere in the package.
"""

import os
import subprocess
import sys

import pytest

from conftest import REPO_ROOT

import imas

GENERATED_HLI_STUB = '''"""Stand-in for IMAS-AL-Python, the generated python HLI."""
DBEntry = object
IDSName = object
IDSBase = object
equilibrium = None
tf = None
'''


def runWithStubbedHLI(tmp_path, importWhat):
    """A child process whose first `imas` on the path is the generated-HLI stub.

    The stub directory is **prepended** to the inherited PYTHONPATH: replacing it
    drops the paths the PySide6/IMAS-Python modules export, and the child then
    fails on `No module named 'PySide6'` instead of on the HLI question.
    """
    stubPackage = tmp_path / 'generatedHLI' / 'imas'
    stubPackage.mkdir(parents=True)
    (stubPackage / '__init__.py').write_text(GENERATED_HLI_STUB)
    environment = dict(os.environ)
    environment['PYTHONPATH'] = os.pathsep.join(
        [str(tmp_path / 'generatedHLI'), REPO_ROOT]
        + environment.get('PYTHONPATH', '').split(os.pathsep))
    child = subprocess.run([sys.executable, '-c', 'import ' + importWhat],
                           cwd=REPO_ROOT, env=environment,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True)
    return child


@pytest.mark.timeout(60)
def test_the_launch_chain_is_refused_by_name_not_by_moduleNotFoundError(tmp_path):
    child = runWithStubbedHLI(tmp_path, 'imasviz.VizGUI.QtVIZ_GUI')
    assert child.returncode != 0, 'the application started on a HLI it cannot run on'
    printed = child.stdout + child.stderr
    assert 'ModuleNotFoundError' not in printed, (
        'the user still meets a raw import error, not the refusal:\n' + printed)
    # What was loaded, why it is not enough, and what to load instead.
    assert 'IMAS-Python' in printed
    assert str(tmp_path / 'generatedHLI' / 'imas' / '__init__.py') in printed
    assert 'IDSDataType' in printed and 'IDSStructArray' in printed
    assert 'IMAS-AL-Python' in printed
    assert 'module load IMAS-Python' in printed


@pytest.mark.timeout(60)
def test_the_refusal_names_the_two_names_even_with_no_hli_at_all(tmp_path):
    # Nothing but the repository on the path: no `imas`, and the gate module needs
    # only the standard library, so this stays a question about the HLI.
    environment = dict(os.environ)
    environment['PYTHONPATH'] = REPO_ROOT
    child = subprocess.run(
        [sys.executable, '-c',
         'import imasviz.VizDataAccess.QVizAccessLayerHLI'],
        cwd=REPO_ROOT, env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True)
    assert child.returncode != 0
    printed = child.stdout + child.stderr
    assert 'nothing importable as "imas"' in printed, printed
    assert 'module load IMAS-Python' in printed


def test_the_gate_hands_the_walk_the_same_two_objects():
    """The three sites ask the gate, and identity is what the walk compares.

    `QVizIDSViewParser.walkIDS` and `dynamicArrayCount` test
    `childMeta.data_type is IDSDataType.STRUCT_ARRAY`, so a second import of a
    second `IDSDataType` would silently answer False for every node of every IDS.
    """
    from imasviz.VizDataAccess import QVizAccessLayerHLI
    from imasviz.VizDataAccess.QVizIDSViewParser import IDSDataType as parserName
    from imasviz.VizDataAccess.QVizTensorExtractor import IDSStructArray as extractorName
    from imasviz.VizDataAccess.VizTimeSlices.QVizTimeSliceSelection import (
        IDSDataType as slicesName)

    assert QVizAccessLayerHLI.missingSurface() == []
    assert parserName is slicesName is imas.IDSDataType
    assert extractorName is imas.IDSStructArray
