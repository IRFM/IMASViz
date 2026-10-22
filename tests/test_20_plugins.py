# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""What a plugin is, and where it is registered.

This file used to pin the machinery around that question as well, and the
measurements of T13 showed that machinery answering nothing useful:

* `getPluginsObjects` imported and built every registered plugin, in 4.186 s
  cold, and was called again on every menu -- 0,999 s for the first right click
  of a session, 0,0425 s for the second, 0,0008 s afterwards;
* `getPluginsNames` answered the keys of the registration table under another
  name;
* `getPluginsConfigurationFor` answered **KeyError** for both plugins that are
  registered -- its table named only the two that are not;
* `getAllEntries` existed twice: the contract stub raising ValueError was
  shadowed by a static lookup table declared below it, so `VizPlugin().
  getAllEntries()` answered `TypeError: missing 1 required positional argument:
  'pluginsName'`, and the contract the manual documents was unreachable;
* `getEntriesFor` was the fallback the menu took for a plugin that does not
  inherit this class, and its table named those same two unregistered plugins --
  which is how a plugin honouring every documented method stayed invisible
  without a word;
* `getMenuItem` read `self.getSubjects()`, which no class in the package
  defines: `AttributeError: 'equilibriumcharts' object has no attribute
  'getSubjects'`.

What is left is the registration table and the contract; deciding what a plugin
offers and running it belongs to `QVizPluginCatalog`, pinned in
`test_43_plugins_in_the_menu.py`.
"""

import importlib.util
import inspect

import pytest

from imasviz.VizPlugins.VizPlugin import (RegisteredPlugins, VizPlugin,
                                          getRegisteredPlugins)

from support.fakes import FakeTreeNode

# The machinery T13 removed, and what each of them answered when asked.
KILLED = ['getPluginsObjects', 'getPluginsNames', 'getPluginsConfigurationFor',
          'getEntriesFor', 'getMenuItem', 'getSubjects']


# --------------------------------------------------------------------------
# The registration table
# --------------------------------------------------------------------------

def test_the_registration_table_is_the_only_place_a_plugin_is_named():
    assert getRegisteredPlugins() is RegisteredPlugins
    assert all(isinstance(key, str) for key in RegisteredPlugins)
    # A dotted path for a Python plugin, a dictionary for a window drawn in Qt
    # Designer -- the two shapes the manual shows.
    assert all(isinstance(value, (str, dict))
               for value in RegisteredPlugins.values())


def test_a_python_registration_names_the_class_it_will_import():
    # The catalog resolves a string registration by taking the class named after
    # the key out of the module the value points at, so the two have to agree.
    for key, modulePath in RegisteredPlugins.items():
        if isinstance(modulePath, dict):
            continue
        assert key.isidentifier()
        assert modulePath.split('.')[-1] == key


def test_the_removed_ets_plugin_stays_unregistered():
    # ETSViz was deleted from the repository: an active entry would now answer
    # ModuleNotFoundError, which the catalog reports by name instead of taking
    # the menu down with it.
    assert 'ETSpluginIMASViz' not in RegisteredPlugins


def test_the_solps_plugin_is_out_of_the_package():
    # 11 files, 1 451 lines. It was never registered, and the five modules of it
    # the sweep could import were reachable by nothing: the window its .ui draws
    # comes out of QUiLoader as a bare QWidget standing in for the SOLPSwidget it
    # declares, with the 3 connections to it dropped.
    assert importlib.util.find_spec('imasviz.VizPlugins.viz_solps') is None
    # Asking for a module inside a package that is gone does not answer None --
    # the parent cannot be imported, and that is what says here.
    for modulePath in ('imasviz.VizPlugins.viz_solps.SOLPSplugin',
                       'imasviz.VizPlugins.viz_solps.SOLPSwidget',
                       'imasviz.VizPlugins.viz_solps.src.getIDS',
                       'imasviz.VizPlugins.viz_solps.src.GGDDialog'):
        with pytest.raises(ModuleNotFoundError) as missing:
            importlib.import_module(modulePath)
        assert 'viz_solps' in str(missing.value)
    assert not any('sol' in str(name + where).lower()
                   for name, where in RegisteredPlugins.items())


@pytest.mark.parametrize('name', KILLED)
def test_a_plugin_is_no_longer_looked_up_by_name_somewhere_else(name):
    # Every one of these named the registered plugins a second time, by hand,
    # and all of them were wrong about which plugins are registered.
    assert not hasattr(VizPlugin, name)
    assert not hasattr(getRegisteredPlugins, name)


def test_the_menu_is_no_longer_built_by_two_deleted_modules():
    for modulePath in ('imasviz.VizGUI.VizGUICommands.VizMenusManagement'
                       '.QVizPluginsHandler',
                       'imasviz.VizGUI.VizGUICommands.VizMenusManagement'
                       '.QVizPluginsPopUpMenu'):
        assert importlib.util.find_spec(modulePath) is None


# --------------------------------------------------------------------------
# The contract a plugin honours
# --------------------------------------------------------------------------

def test_a_fresh_plugin_is_inactive_and_unbound():
    plugin = VizPlugin()
    assert plugin.isEnabled() is False
    assert plugin.selectedTreeNode is None
    assert plugin.dataTreeView is None


def test_a_plugin_takes_the_node_it_is_offered_on_and_the_view_it_reads():
    node = FakeTreeNode(idsName='equilibrium')
    plugin = VizPlugin()
    plugin.setSelectedTreeNode(node)
    plugin.setDataTreeView('a-tree-view')
    assert plugin.selectedTreeNode is node
    assert plugin.dataTreeView == 'a-tree-view'


def test_a_plugin_that_declares_nothing_is_asked_for_it_in_words():
    plugin = VizPlugin()
    for method in ('getEntries', 'getAllEntries', 'execute'):
        with pytest.raises(ValueError) as refused:
            getattr(plugin, method)(None, None) if method == 'execute' \
                else getattr(plugin, method)()
        assert 'should be implemented' in str(refused.value)


def test_getAllEntries_is_reachable_on_the_base_class():
    # Measured before: this answered `TypeError: VizPlugin.getAllEntries()
    # missing 1 required positional argument: 'pluginsName'`, because the
    # contract stub was shadowed by a static table of the same name.
    with pytest.raises(ValueError):
        VizPlugin().getAllEntries()

    # One declaration, taking only the plugin itself.
    assert list(inspect.signature(VizPlugin.getAllEntries).parameters) == ['self']


def test_a_plugin_answers_for_its_own_configuration():
    # The manual asks a plugin for this; the framework never asked it, and asked
    # a per-name table instead -- which answered KeyError for both registered
    # plugins.
    assert VizPlugin().getPluginsConfiguration() is None
