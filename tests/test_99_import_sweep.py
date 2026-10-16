# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Smoke check: every module of the package imports against the real Qt binding.

This is what catches Qt-binding drift (QVariant, pyqtProperty, widgets living in
the wrong module) without needing a case or a data dictionary. The modules that
cannot import are listed with the reason instead of being dropped silently.
"""

import importlib
import os

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE = 'imasviz'

# Qt Designer custom-widget scaffolding. QPyDesignerCustomWidgetPlugin does not
# exist in PySide6 6.6 (QtDesigner only exports QPyDesignerCustomWidgetCollection),
# and the viz_solps/src subtree imports its siblings as `src.<mod>`, which needs
# viz_solps/src itself on sys.path. None of them is registered in
# VizPlugins.VizPlugin.RegisteredPlugins, so none is on a code path.
KNOWN_UNIMPORTABLE = {
    'imasviz.VizPlugins.viz_example.exampleplugin':
        'QPyDesignerCustomWidgetPlugin is gone in PySide6 6.6',
    'imasviz.VizPlugins.viz_solps.SOLPSplugin':
        'QPyDesignerCustomWidgetPlugin is gone in PySide6 6.6',
    'imasviz.VizPlugins.viz_solps.src.getIDSplugin':
        'QPyDesignerCustomWidgetPlugin is gone in PySide6 6.6',
    'imasviz.VizPlugins.viz_solps.SOLPSwidget':
        'imports its siblings as src.<mod>, needs viz_solps/src on sys.path',
    'imasviz.VizPlugins.viz_solps.src.GGDDialog':
        'imports its siblings as src.<mod>, needs viz_solps/src on sys.path',
}

# Demo scripts and standalone runners are not importable modules: they build a
# QApplication and call app.exec_() at module level.
SKIPPED_DIRS = {'VizExamples'}
SKIPPED_FILES = {'run_plugin_ui_standalone.py'}


def is_standalone_script(fileName):
    return fileName.startswith('test_') or fileName in SKIPPED_FILES


def collect_module_names():
    names = []
    root = os.path.join(REPO_ROOT, PACKAGE)
    for dirpath, dirnames, fileNames in os.walk(root):
        if '.git' in dirpath:
            continue
        packageName = dirpath[len(REPO_ROOT) + 1:].replace(os.sep, '.')
        if any(part in SKIPPED_DIRS for part in packageName.split('.')):
            continue
        for fileName in sorted(fileNames):
            if not fileName.endswith('.py') or is_standalone_script(fileName):
                continue
            moduleName = fileName[:-3]
            names.append(packageName if moduleName == '__init__'
                         else packageName + '.' + moduleName)
    return sorted(set(names))


MODULE_NAMES = collect_module_names()


def test_the_walk_finds_the_package():
    # Guards against a broken discovery: an empty list would silently pass.
    assert len(MODULE_NAMES) > 100


@pytest.mark.parametrize('moduleName', MODULE_NAMES)
def test_module_imports(moduleName):
    if moduleName in KNOWN_UNIMPORTABLE:
        pytest.xfail(KNOWN_UNIMPORTABLE[moduleName])
    importlib.import_module(moduleName)


def test_known_unimportable_list_is_not_stale():
    # A fixed module must be removed from the xfail list.
    still_broken = []
    for moduleName in KNOWN_UNIMPORTABLE:
        try:
            importlib.import_module(moduleName)
        except Exception:
            still_broken.append(moduleName)
    assert len(still_broken) == len(KNOWN_UNIMPORTABLE), (
        'these modules import now, drop them from KNOWN_UNIMPORTABLE: '
        + ', '.join(sorted(set(KNOWN_UNIMPORTABLE) - set(still_broken))))
