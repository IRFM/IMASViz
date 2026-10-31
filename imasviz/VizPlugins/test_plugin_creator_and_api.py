# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Tests for the plugin creator tool, CLI/API scaffolding, and simplified VizPlugin contract."""

import os
import sys
import pytest

from imasviz.VizPlugins.create_plugin import createPlugin
from imasviz.VizPlugins.VizPlugin import getRegisteredPlugins, registerPlugin, VizPlugin


def test_plugin_scaffolding(tmp_path, monkeypatch):
    monkeypatch.setenv('VIZ_HOME', str(tmp_path))
    className, dirName = createPlugin(
        'test_dynamic_plugin',
        targetIds='equilibrium',
        description='Test dynamic plugin description.',
        menuTitle='Test Dynamic Action'
    )

    pluginDir = tmp_path / 'imasviz' / 'VizPlugins' / dirName
    pyFile = pluginDir / f'{className}.py'
    initFile = pluginDir / '__init__.py'

    assert pyFile.exists()
    assert initFile.exists()

    content = pyFile.read_text()
    assert 'CeCILL-C' in content
    assert className in content
    assert 'equilibrium' in content
    assert 'Test Dynamic Action' in content


def test_simplified_viz_plugin_defaults():
    class DummyPlugin(VizPlugin):
        def execute(self, vizAPI, pluginEntry=None, answers=None):
            return "ok"

    plugin = DummyPlugin()
    assert plugin.isEnabled() is True
    assert plugin.getEntries() == [0]
    assert len(plugin.getAllEntries()) == 1
    assert plugin.execute(None) == "ok"


def test_plugin_registration():
    registerPlugin('TestPluginRegistered', 'viz_test.TestPluginRegistered')
    reg = getRegisteredPlugins()
    assert 'TestPluginRegistered' in reg
    assert reg['TestPluginRegistered'] == 'viz_test.TestPluginRegistered'
