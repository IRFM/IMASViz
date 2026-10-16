# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The plugin framework: registration and the VizPlugin contract.

An unregistered plugin never loads, and a registered name whose module is gone
fails at getPluginsObjects() time, so both sides of that contract are asserted.
"""

import pytest

from imasviz.VizPlugins.VizPlugin import (RegisteredPlugins, VizPlugin,
                                          getRegisteredPlugins)

from support.fakes import FakeTreeNode


def test_the_registered_set_is_exposed_as_a_mapping():
    assert getRegisteredPlugins() is RegisteredPlugins
    assert all(isinstance(name, str) and isinstance(modulePath, str)
               for name, modulePath in RegisteredPlugins.items())


def test_the_removed_ets_plugin_stays_unregistered():
    # ETSViz was deleted from the repository: an active entry would now raise
    # ModuleNotFoundError inside getPluginsObjects.
    assert 'ETSpluginIMASViz' not in RegisteredPlugins


def test_every_registered_plugin_imports_and_instantiates():
    # getPluginsObjects resolves the dotted path and builds the object; a
    # stale entry is a hard error, so this is the regression guard.
    names, objects = VizPlugin.getPluginsObjects(dataTreeView=None,
                                                selectedTreeNode=None)
    assert sorted(names) == sorted(RegisteredPlugins)
    assert len(objects) == len(RegisteredPlugins)
    for plugin in objects:
        assert isinstance(plugin, VizPlugin)


def test_a_fresh_plugin_is_inactive_and_unbound():
    plugin = VizPlugin()
    assert plugin.isEnabled() is False
    assert plugin.selectedTreeNode is None
    assert plugin.dataTreeView is None


def test_the_binding_setters_are_used_by_the_loader():
    node = FakeTreeNode(idsName='equilibrium')
    plugin = VizPlugin()
    plugin.setSelectedTreeNode(node)
    plugin.setDataTreeView('a-tree-view')
    assert plugin.selectedTreeNode is node
    assert plugin.dataTreeView == 'a-tree-view'


def test_getEntries_must_be_implemented_by_a_plugin():
    plugin = VizPlugin()
    with pytest.raises(ValueError):
        plugin.getEntries()


@pytest.mark.xfail(strict=True, reason=(
    "VizPlugin declares getAllEntries twice: the instance stub raising ValueError "
    "(VizPlugin.py:52) is shadowed by the static lookup table further down "
    "(VizPlugin.py:130), so the base-class contract method is unreachable"))
def test_getAllEntries_contract_stub_is_reachable():
    plugin = VizPlugin()
    with pytest.raises(ValueError):
        plugin.getAllEntries()


def test_the_static_lookup_table_serves_the_ui_plugins():
    # What getAllEntries resolves to in practice: a table keyed by plugin name.
    assert VizPlugin.getAllEntries('SOLPS_UiPlugin') == [(0, 'SOLPS overview...')]
    assert VizPlugin.getAllEntries('example_UiPlugin') == [(0, 'Magnetics overview...')]
    with pytest.raises(KeyError):
        VizPlugin.getAllEntries('no_such_plugin')


def test_getPluginsNames_matches_the_registration_table():
    assert sorted(VizPlugin.getPluginsNames()) == sorted(RegisteredPlugins)


def test_an_unknown_plugin_name_has_no_configuration():
    with pytest.raises(KeyError):
        VizPlugin.getPluginsConfigurationFor('no_such_plugin')


def test_entries_of_ui_plugins_are_gated_on_the_selected_ids():
    # The two .ui plugins claim fixed IDSs; anything else gets no entry.
    assert VizPlugin.getEntriesFor('SOLPS_UiPlugin',
                                   FakeTreeNode(idsName='edge_profiles')) == [0]
    assert VizPlugin.getEntriesFor('SOLPS_UiPlugin',
                                   FakeTreeNode(idsName='equilibrium')) == []
    assert VizPlugin.getEntriesFor('example_UiPlugin',
                                   FakeTreeNode(idsName='magnetics')) == [0]
    assert VizPlugin.getEntriesFor('example_UiPlugin',
                                   FakeTreeNode(idsName='interferometer')) == []
