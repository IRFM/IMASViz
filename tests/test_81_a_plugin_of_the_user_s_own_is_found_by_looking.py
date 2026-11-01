# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""A plugin of the user's own: where it lives, how it is found, what it must be named.

Before this, **one** way existed to add a plugin: edit the `RegisteredPlugins`
table in `imasviz/VizPlugins/VizPlugin.py`, a file of the package, and put the
code under `$VIZ_HOME/imasviz/VizPlugins/` -- which is where the creator of the
previous pass wrote its scaffold. Two things were wrong about that, and both were
measured before this folder of tests was written:

* an installed IMASViz lives in a module tree the run does not own, so the write
    is the first thing to fail on a workstation;
* and when it did work, the checkout was left holding a file its owner never
    chose, in the one place upstream also writes.

So a user plugin lives in `$HOME/.imasviz/plugins` -- next to `preferences` and
the `.pcfg` files the application already owns -- and is **found by looking**, not
registered. Four things this file pins:

* the scan sees a folder as a plugin when it holds a module declaring a class of
    that module's name (the rule the howto documents), read out of the *source*
    with `ast` -- listing must not import, because importing is where the cost
    is: the shipped set alone is where matplotlib comes in, measured at 4,186 s
    cold in test_43;
* a plugin written a minute ago is on the menu of a view built after it, with no
    file of the package edited;
* a name is a folder, a module and a class at once, so a name that cannot carry
    that is refused before anything is written -- including the name of a plugin
    IMASViz already ships, which is not silently replaced;
* the shipped table stays what it was: a user plugin never lands in it, which is
    what `registerPlugin` used to do, and why that is gone.

`HOME` is pointed at `tmp_path` here for every test: the suite does not isolate
it (`tests/test_39_configurations.py` does the same for the configurations), and
`userPluginsFolder()` reads it **when asked** so that this works at all.
"""

import importlib
import logging
import os
import sys
import types

import pytest

from PySide6.QtWidgets import QTreeWidget

from imasviz.VizPlugins.QVizPluginCatalog import QVizPluginCatalog
from imasviz.VizPlugins.QVizPluginSource import (USER, checkPluginName,
                                                 declaresClass,
                                                 forgetUserModules,
                                                 pluginNameFor,
                                                 userPluginsFolder,
                                                 userSources)
from imasviz.VizPlugins.create_plugin import createPlugin

from support.fakes import FakeTreeNode

# The catalog looks `getRegisteredPlugins` up in its own module, so that is where
# the shipped set is replaced when a test wants a folder of nothing but the user's
# own -- and the same seam test_43 uses for a stub plugin.
CATALOG = importlib.import_module('imasviz.VizPlugins.QVizPluginCatalog')

PLUGIN_SOURCE = '''
from imasviz.VizPlugins.VizPlugin import VizPlugin


class {name}(VizPlugin):
    """A plugin of mine, for the tests."""

    CALLS = []

    def isEnabled(self):
        return True

    def getEntries(self):
        if self.selectedTreeNode.getIDSName() == '{ids}':
            return [0]
        return []

    def getAllEntries(self):
        return [(0, {label!r})]

    def execute(self, vizAPI, pluginEntry, answers=None):
        type(self).CALLS.append(pluginEntry)
'''


@pytest.fixture(autouse=True)
def privatePlugins(tmp_path, monkeypatch):
    """A `$HOME` of this test only, and a `sys.modules` of this test only.

    The second half is not decoration: the user plugins are imported under one
    synthetic package, and `sys.modules` is one table for the process. Without
    this, a plugin imported by the first test would be what the next one gets --
    the same hazard `tests/test_49_export_then_open_what_was_written.py` records
    for the case cache.
    """
    home = tmp_path / 'home'
    home.mkdir()
    monkeypatch.setenv('HOME', str(home))
    forgetUserModules()
    yield home
    forgetUserModules()


class StubView(QTreeWidget):
    """Enough of a shot view for a catalog: an api, a URI to log under, no case."""

    def __init__(self):
        super().__init__()
        self.uri = 'stub?case'
        self.pluginCatalog = None
        self.imas_viz_api = 'the-api-of-this-view'


@pytest.fixture
def view(qtbot):
    widget = StubView()
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def noShippedPlugins(monkeypatch):
    """Look at the user's folder alone."""
    monkeypatch.setattr(CATALOG, 'getRegisteredPlugins', lambda: {})


def writePlugin(name, label='the first thing', ids='equilibrium'):
    """Put one plugin in this test's folder, the way a copy from outside would.

    Written by hand and not through `createPlugin`, because the scan has to work
    for a folder that arrived from somewhere else -- a `cp`, an `scp`, a script.
    """
    folder = os.path.join(userPluginsFolder(), 'viz_' + name.lower())
    os.makedirs(folder)
    path = os.path.join(folder, name + '.py')
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(PLUGIN_SOURCE.format(name=name, label=label, ids=ids))
    return path


# ---------------------------------------------------------------------------
# Where the folder is, and what counts as a plugin in it
# ---------------------------------------------------------------------------

def test_the_folder_is_the_one_under_home_and_is_read_when_it_is_asked(monkeypatch):
    """Not frozen at import: a folder resolved at import time would be the real
    `$HOME` for the rest of the process, and no test -- and no second run in one
    Python -- could get a folder of its own."""
    assert userPluginsFolder() == os.path.join(os.environ['HOME'], '.imasviz',
                                               'plugins')

    monkeypatch.setenv('HOME', '/elsewhere')
    assert userPluginsFolder() == '/elsewhere/.imasviz/plugins'


def test_a_folder_that_does_not_exist_yet_is_not_an_error():
    """The state of a first run: nothing has been created, and that is not a
    failure to report."""
    assert userSources() == []


def test_a_folder_holding_a_plugin_is_seen_without_anything_being_registered():
    writePlugin('MyAnalysisPlugin')

    sources = userSources()

    assert [one.name for one in sources] == ['MyAnalysisPlugin']
    assert sources[0].origin == USER
    assert sources[0].writable is True
    assert sources[0].registration == 'viz_myanalysisplugin.MyAnalysisPlugin'
    assert sources[0].fileName.endswith('MyAnalysisPlugin.py')


def test_listing_the_folder_imports_nothing():
    """The scan reads the source with `ast`. Importing is what costs -- the
    shipped set alone is where matplotlib comes in -- and the plugin manager
    lists the folder before anything is run."""
    writePlugin('MyAnalysisPlugin')

    sources = userSources()

    assert sources[0].importName not in sys.modules
    assert 'imasviz_user_plugins' not in sys.modules


def test_a_folder_holding_no_class_of_its_module_name_is_not_a_plugin():
    """The howto's rule -- the module and the class bear one name -- asked off
    the source. A folder holding helpers, a scratch file or a half-written plugin
    is not a plugin, and the menu says nothing about it."""
    folder = os.path.join(userPluginsFolder(), 'viz_notes')
    os.makedirs(folder)
    with open(os.path.join(folder, 'notes.py'), 'w', encoding='utf-8') as handle:
        handle.write('class SomethingElse:\n    pass\n')
    with open(os.path.join(folder, '__init__.py'), 'w', encoding='utf-8') as handle:
        handle.write('')

    assert userSources() == []
    assert declaresClass(os.path.join(folder, 'notes.py'), 'notes') is False


def test_a_folder_holding_a_broken_plugin_is_still_listed_to_be_fixed():
    """A plugin the user broke in the editor is the one they most need to *open*.
    Hiding it from the list because its file no longer parses would leave nothing
    to fix; the catalog is where it is refused, by name."""
    path = writePlugin('MyAnalysisPlugin')
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write('class MyAnalysisPlugin(VizPlugin)\n    broken =\n')

    assert [one.name for one in userSources()] == ['MyAnalysisPlugin']


# ---------------------------------------------------------------------------
# The menu, which is where being found has to land
# ---------------------------------------------------------------------------

def test_a_plugin_in_the_folder_is_offered_by_a_view_built_after_it(
        noShippedPlugins, view):
    writePlugin('MyAnalysisPlugin', label='my own plot')

    entries = QVizPluginCatalog(view).entriesFor(FakeTreeNode(idsName='equilibrium'))

    assert [(entry.number, entry.label) for entry in entries] == \
        [(0, 'my own plot')]
    assert entries[0].pluginName == 'MyAnalysisPlugin'
    # The origin rides on the entry, which is what lets the menu offer *Edit* for
    # this one and refuse it for a shipped one.
    assert entries[0].origin == USER
    assert entries[0].source.writable is True


def test_the_plugin_of_the_user_s_runs_like_any_other(noShippedPlugins, view):
    writePlugin('MyAnalysisPlugin')
    catalog = QVizPluginCatalog(view)
    entry = catalog.entriesFor(FakeTreeNode(idsName='equilibrium'))[0]

    catalog.run(entry)

    assert entry.plugin.CALLS == [0]


def test_a_plugin_that_no_longer_parses_costs_its_own_line_and_not_the_menu(
        noShippedPlugins, view, caplog):
    path = writePlugin('MyAnalysisPlugin')
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write('class MyAnalysisPlugin(VizPlugin)\n    broken =\n')

    with caplog.at_level(logging.ERROR, logger=view.uri):
        catalog = QVizPluginCatalog(view)
        entries = catalog.entriesFor(FakeTreeNode(idsName='equilibrium'))

    assert entries == []
    assert 'MyAnalysisPlugin' in catalog.refused
    assert 'SyntaxError' in catalog.refused['MyAnalysisPlugin']
    assert 'MyAnalysisPlugin' in caplog.text


def test_a_user_plugin_named_like_a_shipped_one_is_refused_by_name(view,
                                                                   monkeypatch):
    """Two plugins of one name is a question the menu cannot answer, and letting
    the user's file take the place of the shipped one in silence is the worse of
    the two ways to answer it. The shipped one keeps its line; the user's is named
    in the log of the case with the rule it broke."""
    shipped = types.ModuleType('imasviz.VizPlugins.viz_shipped.MyAnalysisPlugin')

    class MyAnalysisPlugin:
        def setSelectedTreeNode(self, node):
            pass

        def isEnabled(self):
            return True

        def getEntries(self):
            return [1]

        def getAllEntries(self):
            return [(1, 'the shipped one')]

        def execute(self, vizAPI, pluginEntry, answers=None):
            pass

    shipped.MyAnalysisPlugin = MyAnalysisPlugin
    monkeypatch.setitem(sys.modules, shipped.__name__, shipped)
    monkeypatch.setattr(CATALOG, 'getRegisteredPlugins',
                        lambda: {'MyAnalysisPlugin':
                                 'viz_shipped.MyAnalysisPlugin'})
    writePlugin('MyAnalysisPlugin', label='mine')

    catalog = QVizPluginCatalog(view)
    entries = catalog.entriesFor(FakeTreeNode(idsName='equilibrium'))

    assert [entry.label for entry in entries] == ['the shipped one']
    assert 'another name' in catalog.refused['MyAnalysisPlugin']


# ---------------------------------------------------------------------------
# The name a plugin may take
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('asked', ['class', 'two words!', '', '9lives'])
def test_a_name_that_cannot_carry_folder_module_and_class_is_refused(asked):
    """A plugin name is a folder, a module and a class at once, so it has to be a
    plain identifier. Refused before anything is written, which is the only moment
    it is cheap to say so."""
    with pytest.raises(ValueError) as refusal:
        checkPluginName(asked)
    assert ('IMASViz can use' in str(refusal.value)
            or 'needs a name' in str(refusal.value))


def test_a_name_imasviz_already_ships_is_refused_rather_than_replaced():
    """`equilibriumcharts` is the one plugin the shipped table holds that this
    test can name without a stub -- and the guard reads the real table."""
    with pytest.raises(ValueError) as refusal:
        checkPluginName('equilibriumcharts')
    assert 'already ships' in str(refusal.value)


def test_one_naming_rule_for_a_phrase_the_user_typed():
    """The creator and *copy into my plugins* ask the same function, because two
    spellings is how a plugin ends up with a module whose class has another name
    -- the one thing the scan cannot read."""
    assert pluginNameFor('my analysis') == 'MyAnalysisPlugin'
    assert pluginNameFor('my_analysis') == 'MyAnalysisPlugin'
    assert pluginNameFor('MyAnalysisPlugin') == 'MyAnalysisPlugin'
    with pytest.raises(ValueError):
        pluginNameFor('   ')


# ---------------------------------------------------------------------------
# What the creator writes, and what it does not touch
# ---------------------------------------------------------------------------

def test_the_creator_writes_a_working_plugin_into_the_user_folder():
    source = createPlugin('my analysis', targetIds='magnetics')

    assert source.origin == USER
    assert os.path.isdir(source.folder)
    assert source.folder.startswith(userPluginsFolder())
    with open(source.fileName, encoding='utf-8') as handle:
        text = handle.read()
    # It parses -- the same check the editor and the watcher ask before a file
    # replaces what is running.
    compile(text, source.fileName, 'exec')
    assert 'CeCILL-C' in text
    assert 'class MyAnalysisPlugin' in text
    # And it draws through IMASViz's own plot command, not a print: the first
    # click on a fresh plugin has to put a window on screen.
    assert 'QVizPlotOneNode' in text
    assert 'getImasEntry' not in text
    assert [one.name for one in userSources()] == ['MyAnalysisPlugin']


def test_a_created_plugin_is_offered_where_it_said_it_would_be(noShippedPlugins,
                                                               view):
    createPlugin('my analysis', targetIds='magnetics')
    catalog = QVizPluginCatalog(view)

    assert [(entry.number, entry.label)
            for entry in
            catalog.entriesFor(FakeTreeNode(idsName='magnetics'))] != []
    assert catalog.entriesFor(FakeTreeNode(idsName='equilibrium')) == []


def test_the_creator_refuses_a_name_that_is_taken_before_writing_anything():
    createPlugin('my analysis')
    with pytest.raises(ValueError) as refusal:
        createPlugin('my analysis')
    assert 'already holds' in str(refusal.value)
    assert len(userSources()) == 1


def test_a_user_plugin_never_lands_in_the_table_imasviz_ships():
    """`registerPlugin` is gone, and this is why: a catalog is built once per
    shot view, so a plugin injected into that table would be on one view's menu
    for ever and on no other's at all -- and it would make a shipped name look
    editable, when nothing in that table is."""
    from imasviz.VizPlugins.VizPlugin import getRegisteredPlugins

    before = dict(getRegisteredPlugins())
    createPlugin('my analysis')

    assert getRegisteredPlugins() == before
    assert 'MyAnalysisPlugin' not in getRegisteredPlugins()
