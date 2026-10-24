# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The python HLI the data dictionary is read through, asked once.

The shot view is built by walking the Access Layer metadata of a loaded IDS:
`QVizIDSViewParser.walkIDS` compares `childMeta.data_type` with
`IDSDataType.STRUCTURE` and `IDSDataType.STRUCT_ARRAY`, `dynamicArrayCount` asks
`childMeta.type.is_dynamic` to know how many time slices an occurrence holds, and
`QVizTensorExtractor` walks the `IDSStructArray` elements to reach a leaf. Those
two names are the whole surface this package takes from the python HLI, so they
are asked here, once, instead of at three leaf imports that each died on their own
`ModuleNotFoundError`.

ITER ships a second python HLI: the generated one, `IMAS-AL-Python`, built once
per data dictionary. Measured on
`/gw/swimas/software/IMAS-AL-Python/5.4.0-foss-2023b-DD-3.42.0`: its `imas`
package holds `ids_base.py`, `ids_names.py`, `db_entry.py`, `dd_units.py` and one
generated module per IDS (`equilibrium.py`, `tf.py`, ...), exports `DBEntry`,
`IDSName`, `IDSBase` and `get_al_version`, and the string `IDSDataType` appears in
none of its files. So `import imas` succeeds there and `imas.DBEntry` works, while
the walk cannot start -- there is no metadata to walk. The refusal below therefore
names the package it found rather than the import that failed: the failed import
is a symptom, and what the user has to change is the module they load.

Measured on this node, `IMAS-Python/2.0.1`, `2.1.0` and `2.3.0` all ship
`imas/ids_data_type.py`, and `2.3.0` exposes `IDSDataType` and `IDSStructArray` at
the package root as well. The root is therefore asked first -- what a binding
promises -- and the submodule second, so a binding that keeps the names public
without keeping that file layout still runs.
"""

import importlib
import sys

#: What the walk needs from the python HLI: the name, then where it is kept.
REQUIRED_SURFACE = (('IDSDataType', 'imas.ids_data_type'),
                    ('IDSStructArray', 'imas.ids_struct_array'))


def _lookUp(name, moduleName):
    """The name as the loaded `imas` exposes it, None when it does not.

    None is also returned when there is no `imas` importable at all: the refusal
    then says so, instead of losing the user on a bare
    `ModuleNotFoundError: No module named 'imas'`.
    """
    try:
        imas = importlib.import_module('imas')
    except ImportError:
        return None
    found = getattr(imas, name, None)
    if found is not None:
        return found
    try:
        module = importlib.import_module(moduleName)
    except ImportError:
        return None
    return getattr(module, name, None)


def missingSurface():
    """The required names the loaded python HLI does not provide, in asked order.

    Empty means the HLI can carry the walk. This is the question a test or a
    diagnostic asks without taking the process down.
    """
    return [name for name, moduleName in REQUIRED_SURFACE
            if _lookUp(name, moduleName) is None]


def loadedHLI():
    """Where the `imas` in charge came from, and what it says it is.

    `(None, None, False)` when no `imas` is importable. The third answer is
    whether that package declares one module per IDS (`imas.equilibrium`): the
    tell that it is the generated HLI -- measured True on `IMAS-AL-Python/5.4.0`,
    False on `IMAS-Python/2.3.0`.
    """
    try:
        imas = importlib.import_module('imas')
    except ImportError:
        return None, None, False
    return (getattr(imas, '__file__', None), getattr(imas, '__version__', None),
            hasattr(imas, 'equilibrium'))


def refusalText():
    """Why the application cannot start here, and what to load instead."""
    where, version, generated = loadedHLI()
    lines = ['IMASViz cannot start: the IMAS-Python HLI is not loaded.', '']
    if where is None:
        lines.append('  no python HLI found  : nothing importable as "imas" on sys.path')
    else:
        lines.append('  python HLI in charge : %s' % where)
        lines.append('  it calls itself      : %s' % (version or 'no version'))
    lines.append('  missing from it      : %s' % ', '.join(missingSurface()))
    lines += ['',
              'The shot view walks the Access Layer metadata of each loaded IDS',
              '(idsInstance.metadata, childMeta.data_type, type.is_dynamic), and the',
              'tensor reading walks the arrays of structures themselves. Those two',
              'names are the public surface of the IMAS-Python bindings.']
    if generated:
        lines += ['',
                  'The package above declares one module per IDS (imas.equilibrium,',
                  'imas.tf, ...): that is the generated python HLI, IMAS-AL-Python, and',
                  'it carries no metadata reflection API at all. IMASViz cannot be made',
                  'to run on it.']
    lines += ['',
              'With environment modules on Linux:',
              '',
              '    module avail IMAS-Python            # what this node offers',
              '    module load IMAS-Python/<version>   # e.g. IMAS-Python/2.3.0-foss-2023b',
              '',
              'An IMAS stack that ships only the generated python HLI cannot run IMASViz.']
    return '\n'.join(lines)


IDSDataType = _lookUp('IDSDataType', 'imas.ids_data_type')
IDSStructArray = _lookUp('IDSStructArray', 'imas.ids_struct_array')

if IDSDataType is None or IDSStructArray is None:
    print(refusalText())
    sys.exit(1)
