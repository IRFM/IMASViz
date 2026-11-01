# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Reading any plugin, writing only your own -- and seeing which is which.

The user asked for two modes: read-only for plugins that are not theirs, read and
write for the ones that are. The boundary is one question -- `writable` -- and this
file pins that it is asked in **three** places that cannot then disagree:

* the text area, which is what the user sees (a greyed-out area, a disabled
  *Save*);
* the *Edit* line of the Plugins sub-menu, which is not offered at all for a plugin
  IMASViz ships -- a menu line that can only answer "no" is a line that teaches the
  user that menus lie;
* `writeSource`, which refuses the write whatever asked for it. A boundary that
  only lives in the widget is one a determined user walks through and a careless
  one finds out about by losing an edit.

Two more things are pinned here because they are what makes the boundary usable
rather than obstructive:

* a shipped plugin can be **read** in the same window, and **copied** into the
  user's folder under a name of their own -- whole folder, sub-packages and all,
  with the class name rewritten wherever it appears. Reading a plugin you cannot
  change is only useful if the way to change one starts from it;
* nothing that does not parse reaches the disk. A plugin is Python the application
  imports, so a half-typed file saved out of habit would replace the module that
  answers the menu today. `compileCheck` runs first and the refusal names the line.

`HOME` is pointed at `tmp_path` for every test here, as in test_81: the user's
folder is under it, and the suite does not isolate it.
"""

import importlib
import os
import sys
import types

import pytest

from PySide6.QtWidgets import QMenu, QTreeWidget

from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizPluginMenu \
    import QVizPluginMenu
from imasviz.VizPlugins.QVizPluginCatalog import QVizPluginCatalog, openEditor
from imasviz.VizPlugins.QVizPluginEditor import QVizPluginEditor
from imasviz.VizPlugins.QVizPluginManager import MINE, SHIPPED, QVizPluginManager
from imasviz.VizPlugins.QVizPluginSource import (BUILTIN, builtinSource,
                                                 builtinSources,
                                                 copyIntoUserFolder,
                                                 forgetUserModules,
                                                 userPluginsFolder,
                                                 userSources, writeSource)

from support.fakes import FakeTreeNode

CATALOG = importlib.import_module('imasviz.VizPlugins.QVizPluginCatalog')
OPERATIONS = importlib.import_module('imasviz.VizUtils.QVizGlobalOperations')

# One row of the table IMASViz really ships. `VizProfiles_plugin` rather than the
# Equilibrium chart because the boundary asked here is about a plugin built out of
# a folder and a sub-package, which is the shape a copy has to keep.
SHIPPED_NAME = 'VizProfiles_plugin'
SHIPPED_REGISTRATION = 'viz_Profiles.VizProfiles_plugin'


@pytest.fixture(autouse=True)
def privatePlugins(tmp_path, monkeypatch):
    home = tmp_path / 'home'
    home.mkdir()
    monkeypatch.setenv('HOME', str(home))
    forgetUserModules()
    yield home
    forgetUserModules()


class StubView(QTreeWidget):
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


def aShippedSource():
    return builtinSource(SHIPPED_NAME, SHIPPED_REGISTRATION)


def aUserPlugin(name='MyAnalysisPlugin', label='the first thing'):
    """Write one of the user's own plugins and answer its source."""
    folder = os.path.join(userPluginsFolder(), 'viz_' + name.lower())
    os.makedirs(folder)
    path = os.path.join(folder, name + '.py')
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write('from imasviz.VizPlugins.VizPlugin import VizPlugin\n\n\n'
                     'class %s(VizPlugin):\n'
                     '    def isEnabled(self):\n'
                     '        return True\n\n'
                     '    def getEntries(self):\n'
                     '        return [0]\n\n'
                     '    def getAllEntries(self):\n'
                     '        return [(0, %r)]\n' % (name, label))
    from imasviz.VizPlugins.QVizPluginSource import QVizPluginSource, USER
    return QVizPluginSource(name, os.path.basename(folder) + '.' + name, USER,
                            folder=folder, fileName=path)


class Api:
    """Enough of `Viz_API` for the manager: the shot views, and nothing else."""

    def __init__(self, *views):
        self.DTVlist = list(views)


def shipAStub(monkeypatch):
    """A plugin that counts as "shipped", without importing the set IMASViz really
    ships -- which is where matplotlib comes in, and none of what it draws has any
    bearing on whose file it is."""
    module = types.ModuleType(
        'imasviz.VizPlugins.viz_stub_shipped.ShippedThingPlugin')

    class ShippedThingPlugin:
        def isEnabled(self):
            return True

        def getEntries(self):
            return [3]

        def getAllEntries(self):
            return [(3, 'the shipped one')]

        def execute(self, vizAPI, pluginEntry, answers=None):
            pass

    module.ShippedThingPlugin = ShippedThingPlugin
    monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setattr(CATALOG, 'getRegisteredPlugins',
                        lambda: {'ShippedThingPlugin':
                                 'viz_stub_shipped.ShippedThingPlugin'})


def aManager(view, watcher=None):
    return QVizPluginManager(None, apiOf=Api(view), watcher=watcher)


def rowOf(manager, name):
    for row in range(manager.table.rowCount()):
        if manager.table.item(row, 0).text() == name:
            return row
    return None


# ---------------------------------------------------------------------------
# The write boundary, at the place that actually holds the file
# ---------------------------------------------------------------------------

def test_a_plugin_imasviz_ships_is_read_here_and_never_written():
    source = aShippedSource()

    assert source.origin == BUILTIN
    assert source.writable is False
    with pytest.raises(ValueError) as refusal:
        writeSource(source, 'x = 1\n')
    assert 'copy it into your own plugins' in str(refusal.value)


def test_a_refused_write_left_the_shipped_file_exactly_as_it_was():
    source = aShippedSource()
    with open(source.fileName, 'rb') as handle:
        before = handle.read()

    with pytest.raises(ValueError):
        writeSource(source, 'this is not what was there\n')

    with open(source.fileName, 'rb') as handle:
        assert handle.read() == before


def test_a_plugin_of_the_user_s_own_is_written_and_answers_where():
    source = aUserPlugin()

    assert source.writable is True
    assert writeSource(source, 'answer = 42\n') == source.fileName
    with open(source.fileName, encoding='utf-8') as handle:
        assert handle.read() == 'answer = 42\n'


# ---------------------------------------------------------------------------
# The editor: what the user sees of that boundary
# ---------------------------------------------------------------------------

def test_the_editor_of_a_shipped_plugin_shows_the_source_says_read_only(qtbot):
    source = aShippedSource()
    editor = QVizPluginEditor(source)
    qtbot.addWidget(editor)

    assert editor.view.toPlainText() == open(source.fileName,
                                             encoding='utf-8').read()
    assert editor.view.isReadOnly() is True
    assert editor.saveButton.isEnabled() is False
    assert 'read here and not changed' in editor.whereLabel.text()
    # And it says the way out, in the same breath: not "no", but "here is how".
    assert userPluginsFolder() in editor.stateLabel.text()


def test_the_editor_of_a_user_plugin_is_ready_to_write(qtbot):
    source = aUserPlugin()
    editor = QVizPluginEditor(source)
    qtbot.addWidget(editor)

    assert editor.view.isReadOnly() is False
    assert editor.saveButton.isEnabled() is True


def test_saving_writes_and_names_the_file(qtbot):
    source = aUserPlugin()
    editor = QVizPluginEditor(source)
    qtbot.addWidget(editor)
    editor.view.setPlainText('answer = 42\n')

    assert editor._save() is True
    with open(source.fileName, encoding='utf-8') as handle:
        assert handle.read() == 'answer = 42\n'
    assert source.fileName in editor.stateLabel.text()


def test_a_saved_plugin_tells_the_session_to_put_itself_back(qtbot):
    """The *Save* of the editor and the reload of the session are one gesture, not
    two the user has to remember. It is a Qt signal and not a stored callback: a
    plain helper kept on a widget that answers with a bound method of that widget
    makes a cycle, and a widget freed by the cyclic collector is freed on this Qt
    while it still owes a paint event."""
    source = aUserPlugin()
    editor = QVizPluginEditor(source)
    qtbot.addWidget(editor)
    editor.view.setPlainText('answer = 43\n')

    with qtbot.waitSignal(editor.saved, timeout=2000) as blocker:
        editor._save()

    assert blocker.args == [source.fileName]


def test_a_source_that_does_not_parse_is_refused_and_names_the_line(qtbot):
    """Nothing was written, and the box says where the interpreter stopped. The
    module that answers the menu right now is still the one that ran before."""
    source = aUserPlugin()
    editor = QVizPluginEditor(source)
    qtbot.addWidget(editor)
    with open(source.fileName, encoding='utf-8') as handle:
        before = handle.read()
    editor.view.setPlainText('class Broken(VizPlugin\n    = =\n')

    assert editor._save() is False
    with open(source.fileName, encoding='utf-8') as handle:
        assert handle.read() == before
    assert 'Not written' in editor.stateLabel.text()
    assert 'line' in editor.stateLabel.text()


# ---------------------------------------------------------------------------
# Reading a shipped plugin is only useful if changing one starts from it
# ---------------------------------------------------------------------------

def test_a_shipped_plugin_copied_into_the_folder_is_the_user_s_to_change():
    copy, touched = copyIntoUserFolder(aShippedSource(), 'my profiles')

    assert copy.origin != BUILTIN
    assert copy.writable is True
    assert copy.name == 'MyProfilesPlugin'
    assert copy.folder.startswith(userPluginsFolder())
    # The module bears the class name, because that is the rule the scan reads.
    assert copy.fileName.endswith('MyProfilesPlugin.py')
    assert os.path.exists(copy.fileName)
    # A plugin is a folder before it is a module: the Profiles plugin is one module
    # and a sub-package of four, and the copy has to hang together the same way.
    assert len(touched) == 3
    for path in touched:
        with open(path, encoding='utf-8') as handle:
            text = handle.read()
        assert SHIPPED_NAME not in text
        compile(text, path, 'exec')
    compile(open(copy.fileName, encoding='utf-8').read(), copy.fileName, 'exec')


def test_the_copy_is_found_by_the_scan_and_offered_by_a_view_built_after_it(
        noShipped, view):
    copy, _ = copyIntoUserFolder(aShippedSource(), 'my profiles')

    assert [one.name for one in userSources()] == ['MyProfilesPlugin']
    entries = QVizPluginCatalog(view).entriesFor(
        FakeTreeNode(idsName='equilibrium'))
    # What it offers is what the plugin it came from offers -- the copy is a
    # starting point, not a port. What changed is whose file it is.
    assert entries
    assert {entry.pluginName for entry in entries} == {'MyProfilesPlugin'}
    assert all(entry.source.writable for entry in entries)


@pytest.fixture
def noShipped(monkeypatch):
    """The user's folder alone, so a copy of a shipped plugin is the only thing a
    catalog can offer."""
    monkeypatch.setattr(CATALOG, 'getRegisteredPlugins', lambda: {})


def test_two_copies_of_one_shipped_plugin_can_live_side_by_side():
    first, _ = copyIntoUserFolder(aShippedSource(), 'first look')
    second, _ = copyIntoUserFolder(aShippedSource(), 'second look')

    assert first.folder != second.folder
    assert sorted(one.name for one in userSources()) == \
        ['FirstLookPlugin', 'SecondLookPlugin']


# ---------------------------------------------------------------------------
# The manager: the two origins in one table
# ---------------------------------------------------------------------------

def test_the_manager_shows_what_imasviz_ships_and_what_this_user_wrote(qtbot,
                                                                       view):
    aUserPlugin('MyAnalysisPlugin')
    manager = aManager(view)
    qtbot.addWidget(manager)

    assert rowOf(manager, SHIPPED_NAME) is not None
    assert rowOf(manager, 'MyAnalysisPlugin') is not None
    assert manager.table.item(rowOf(manager, SHIPPED_NAME),
                              1).text() == SHIPPED
    assert manager.table.item(rowOf(manager, 'MyAnalysisPlugin'),
                              1).text() == MINE
    # Every row says where the file lives -- which is how a plugin of the user's
    # own is told apart from a name on a list.
    assert manager.table.item(rowOf(manager, 'MyAnalysisPlugin'),
                              3).text().endswith('MyAnalysisPlugin.py')


def test_a_view_that_never_asked_says_so_instead_of_looking_fine(qtbot, view):
    """A blank *State* column would be read as "nothing is wrong", when the truth
    is that no menu has been built on that view yet."""
    manager = aManager(view)
    qtbot.addWidget(manager)

    assert manager.table.item(rowOf(manager, SHIPPED_NAME),
                              2).text() == 'not asked yet'


def test_a_plugin_a_view_refused_is_named_in_the_table_it_is_in(qtbot, view,
                                                                monkeypatch):
    """The reason is read off the catalog that refused it, under the name of the
    plugin -- which is why `refused` is a table and not only the list the log
    panel shows."""
    monkeypatch.setattr(CATALOG, 'getRegisteredPlugins', lambda: {})
    source = aUserPlugin('MyAnalysisPlugin')
    with open(source.fileName, 'w', encoding='utf-8') as handle:
        handle.write('class MyAnalysisPlugin(VizPlugin\n   =\n')
    view.pluginCatalog = QVizPluginCatalog(view)
    view.pluginCatalog.entriesFor(FakeTreeNode(idsName='equilibrium'))

    manager = aManager(view)
    qtbot.addWidget(manager)

    state = manager.table.item(rowOf(manager, 'MyAnalysisPlugin'), 2).text()
    assert state.startswith('refused: SyntaxError')


def test_the_manager_offers_edit_only_for_a_plugin_of_the_user_s_own(qtbot,
                                                                     view):
    aUserPlugin('MyAnalysisPlugin')
    manager = aManager(view)
    qtbot.addWidget(manager)

    manager.table.setCurrentCell(rowOf(manager, SHIPPED_NAME), 0)
    assert manager.openButton.text() == 'Read...'
    assert manager.copyButton.isEnabled() is True
    assert manager.deleteButton.isEnabled() is False

    manager.table.setCurrentCell(rowOf(manager, 'MyAnalysisPlugin'), 0)
    assert manager.openButton.text() == 'Edit...'
    # Nothing to copy: it is already the user's, and copying it would only make a
    # second file to wonder about.
    assert manager.copyButton.isEnabled() is False
    assert manager.deleteButton.isEnabled() is True


def test_the_manager_refuses_to_delete_a_plugin_imasviz_ships(qtbot, view,
                                                              monkeypatch):
    asked = []
    monkeypatch.setattr(OPERATIONS, 'QVizGlobalOperations',
                        type('NeverAsk', (), {'YesNo': staticmethod(
                            lambda **kwargs: asked.append(kwargs) or True)}))
    manager = aManager(view)
    qtbot.addWidget(manager)
    source = aShippedSource()
    manager._sources = {rowOf(manager, SHIPPED_NAME): source}
    manager.table.setCurrentCell(rowOf(manager, SHIPPED_NAME), 0)

    assert manager._delete() is False
    assert asked == []
    assert os.path.exists(source.folder)


def test_deleting_a_plugin_of_the_user_s_takes_its_folder_away(qtbot, view,
                                                               monkeypatch):
    monkeypatch.setattr(OPERATIONS, 'QVizGlobalOperations',
                        type('AlwaysAsk', (), {'YesNo': staticmethod(
                            lambda **kwargs: True)}))
    source = aUserPlugin('MyAnalysisPlugin')
    manager = aManager(view)
    qtbot.addWidget(manager)
    manager.table.setCurrentCell(rowOf(manager, 'MyAnalysisPlugin'), 0)

    assert manager._delete() is True
    assert not os.path.exists(source.folder)
    assert userSources() == []


def test_the_manager_takes_a_deletion_out_of_an_already_built_catalog(qtbot,
                                                                      view,
                                                                      monkeypatch):
    """The folder is what the scan looks at, so the plugin comes off a *fresh*
    catalog by itself -- but a view that already built its plugins holds them, and
    a deletion that leaves its lines on the menu of an open case is a gesture that
    did not happen."""
    monkeypatch.setattr(OPERATIONS, 'QVizGlobalOperations',
                        type('AlwaysAsk', (), {'YesNo': staticmethod(
                            lambda **kwargs: True)}))
    monkeypatch.setattr(CATALOG, 'getRegisteredPlugins', lambda: {})
    source = aUserPlugin('MyAnalysisPlugin')
    catalog = QVizPluginCatalog(view)
    view.pluginCatalog = catalog
    assert catalog.entriesFor(FakeTreeNode(idsName='equilibrium')) != []
    manager = aManager(view)
    qtbot.addWidget(manager)
    manager.table.setCurrentCell(rowOf(manager, 'MyAnalysisPlugin'), 0)

    manager._delete()

    assert source.name not in {entry.pluginName for entry in
                               catalog.entriesFor(FakeTreeNode('equilibrium'))}


# ---------------------------------------------------------------------------
# The same boundary in the Plugins sub-menu of a node
# ---------------------------------------------------------------------------

def menuLines(view, node, qtbot):
    parent = QMenu()
    parent.setParent(view)
    qtbot.addWidget(parent)
    subMenu = QVizPluginMenu().addPluginsMenu(node, view, parent)
    return [] if subMenu is None else [action.text()
                                       for action in subMenu.actions()]


def test_the_plugins_menu_offers_edit_for_a_plugin_of_the_user_s_own(
        noShipped, view, qtbot):
    aUserPlugin('MyAnalysisPlugin', label='my own plot')

    assert menuLines(view, FakeTreeNode(idsName='equilibrium'), qtbot) == \
        ['my own plot', 'Edit MyAnalysisPlugin...']


def test_the_plugins_menu_offers_no_edit_line_for_a_shipped_plugin(view, qtbot,
                                                                   monkeypatch):
    """A line that can only answer "no" is a line that teaches the user that menus
    lie. The copy gesture is in the Plugins window, next to the row that says whose
    the plugin is."""
    shipAStub(monkeypatch)

    assert menuLines(view, FakeTreeNode(idsName='equilibrium'), qtbot) == \
        ['the shipped one']


def test_a_shipped_entry_is_not_editable_and_a_user_entry_is(noShipped, view,
                                                             monkeypatch):
    """Both answers come from the one `writable` on the source, which is why the
    menu line and `writeSource` cannot drift apart."""
    shipAStub(monkeypatch)
    shippedEntry = QVizPluginCatalog(view).entriesFor(
        FakeTreeNode(idsName='equilibrium'))[0]
    assert QVizPluginMenu.editable(shippedEntry) is False

    monkeypatch.setattr(CATALOG, 'getRegisteredPlugins', lambda: {})
    forgetUserModules()
    aUserPlugin('MyAnalysisPlugin')
    mine = QVizPluginCatalog(view).entriesFor(
        FakeTreeNode(idsName='equilibrium'))[0]
    assert QVizPluginMenu.editable(mine) is True


def test_the_edit_line_of_the_menu_opens_the_file_of_that_plugin(noShipped,
                                                                 view, qtbot):
    source = aUserPlugin('MyAnalysisPlugin', label='my own plot')
    catalog = QVizPluginCatalog(view)
    view.pluginCatalog = catalog
    entry = catalog.entriesFor(FakeTreeNode(idsName='equilibrium'))[0]
    parent = QMenu()
    parent.setParent(view)
    qtbot.addWidget(parent)
    QVizPluginMenu().buildPluginsMenu(FakeTreeNode(idsName='equilibrium'), view,
                                      parent)
    editLine = [action for action in parent.actions()
                if action.text().startswith('Edit ')][0]

    editLine.trigger()

    editors = [child for child in view.children()
               if isinstance(child, QVizPluginEditor)]
    assert len(editors) == 1
    assert editors[0].source.fileName == source.fileName
    assert editors[0].view.isReadOnly() is False


def test_opening_a_shipped_plugin_from_the_manager_reads_it(qtbot, view):
    manager = aManager(view)
    qtbot.addWidget(manager)
    manager._sources = {rowOf(manager, SHIPPED_NAME): aShippedSource()}
    manager.table.setCurrentCell(rowOf(manager, SHIPPED_NAME), 0)

    editor = manager._open()

    assert isinstance(editor, QVizPluginEditor)
    assert editor.view.isReadOnly() is True
    editor.deleteLater()
