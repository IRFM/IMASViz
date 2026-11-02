# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""A plugin the user saves answers the session that is already running.

Two caches stand between a saved file and the next right click: the plugins each
shot view builds **once for itself**, and Python's own module table. Either one
left alone is a session that keeps running the code it had when it started, which
is the thing the user cannot explain -- they saved, the menu is unchanged, and
nothing said so.

Three things were measured on this Qt before the watcher was written, and they
decide its shape:

* writing a file **in place** emits one `fileChanged`;
* saving the way vim and emacs do -- a temporary file and a rename over the watched
  one -- emits **two** signals, a directory change and a file change naming the
  *old* path, and afterwards the file is **no longer in `files()`**: without a
  second `watch()` after every flush, the first save from such an editor is the
  last one anyone sees;
* a file that **appears** under a watched folder announces itself only as a
  `directoryChanged`, never as a file change -- it was never watched to begin with.

So: one debounce timer for a burst that is one save, a re-`watch` at the end of
every flush, and a `compileCheck` **before** anything is replaced, so a half-typed
file costs its own entry and not the plugin that works today.

Everything here runs on the GUI thread, and nothing here opens or closes a window:
a worker computes and logs, it does not touch a widget -- the hang that cost was
measured in `QVizIDSViewParser` (T18). And no menu surgery is needed to change what
is on the Plugins sub-menu, because the three gestures rebuild it on every right
click: invalidating the catalog is enough.
"""

import importlib
import logging
import os
import shutil
import sys

import pytest

from PySide6.QtWidgets import QMenu, QTreeWidget, QWidget

from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizFileMenu import \
    QVizFileMenu
from imasviz.VizPlugins.QVizPluginCatalog import (QVizPluginCatalog,
                                                  openEditor,
                                                  reloadEverywhere)
from imasviz.VizPlugins.QVizPluginManager import QVizPluginManager
from imasviz.VizPlugins.QVizPluginSource import (attachUserPackage,
                                                 compileCheck,
                                                 findUserSource,
                                                 forgetUserModules,
                                                 userPluginsFolder)
from imasviz.VizPlugins.QVizPluginWatcher import QVizPluginWatcher

from support.fakes import FakeTreeNode

CATALOG = importlib.import_module('imasviz.VizPlugins.QVizPluginCatalog')

PLUGIN = '''
from imasviz.VizPlugins.VizPlugin import VizPlugin


class MyAnalysisPlugin(VizPlugin):
    def isEnabled(self):
        return True

    def getEntries(self):
        return [0]

    def getAllEntries(self):
        return [(0, %r)]

    def execute(self, vizAPI, pluginEntry, answers=None):
        pass
'''


@pytest.fixture(autouse=True)
def privatePlugins(tmp_path, monkeypatch):
    home = tmp_path / 'home'
    home.mkdir()
    monkeypatch.setenv('HOME', str(home))
    # The user's folder alone: nothing shipped has to be imported to ask what a
    # reload reaches.
    monkeypatch.setattr(CATALOG, 'getRegisteredPlugins', lambda: {})
    forgetUserModules()
    yield home
    forgetUserModules()


class StubView(QTreeWidget):
    def __init__(self, uri='stub?case'):
        super().__init__()
        self.uri = uri
        self.pluginCatalog = None
        self.imas_viz_api = 'the-api-of-this-view'


class Api:
    def __init__(self, *views):
        self.DTVlist = list(views)


class AWindow(QWidget):
    """A window that knows the session, the way `QVizMainWindow` does.

    It holds the views and nothing holds it back: a helper stored on a Qt widget
    that answers with a bound method of that same widget makes a cycle, and a
    widget freed by the cyclic collector is freed on this Qt while it still owes a
    paint event.
    """

    def __init__(self, *views):
        super().__init__()
        self._views = list(views)

    def sessionApi(self):
        return Api(*self._views)


@pytest.fixture
def view(qtbot):
    widget = StubView()
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def watcherOf(qtbot):
    """A watcher owned by a window, so its timer and its file watcher die with it
    instead of being collected underneath the next test."""

    def make(*views):
        window = AWindow(*views)
        qtbot.addWidget(window)
        return QVizPluginWatcher(window.sessionApi, parent=window)

    return make


def pluginFile():
    folder = os.path.join(userPluginsFolder(), 'viz_myanalysisplugin')
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, 'MyAnalysisPlugin.py')


def writePlugin(label='the first thing'):
    path = pluginFile()
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(PLUGIN % label)
    return path


def labelsOf(catalog, idsName='equilibrium'):
    return [entry.label for entry in catalog.entriesFor(
        FakeTreeNode(idsName=idsName))]


# ---------------------------------------------------------------------------
# The two caches a reload has to beat
# ---------------------------------------------------------------------------

def test_a_view_holds_its_plugins_until_something_puts_them_back(qtbot):
    """Not a bug -- the reason. This is what stops a view paying for the shipped
    set on every right click, and it is also what would keep an edited plugin
    running the code it had when the view was built."""
    view = StubView()
    qtbot.addWidget(view)
    writePlugin('the first thing')
    catalog = QVizPluginCatalog(view)
    assert labelsOf(catalog) == ['the first thing']

    writePlugin('the second thing')

    assert labelsOf(catalog) == ['the first thing']


def test_a_reloaded_view_answers_the_file_that_is_on_the_disk_now(qtbot):
    view = StubView()
    qtbot.addWidget(view)
    writePlugin('the first thing')
    catalog = QVizPluginCatalog(view)
    assert labelsOf(catalog) == ['the first thing']

    writePlugin('the second thing')
    catalog.reload()

    assert labelsOf(catalog) == ['the second thing']
    # The plugin object is the new one, not the same instance re-read: a plugin
    # that changed what it offers changed its class, not a field of it.
    assert labelsOf(catalog) == ['the second thing']


def test_a_reload_forgets_the_plugin_and_the_sub_package_it_came_with():
    """`importlib.reload` of one module is not enough: a plugin is a folder before
    it is a module, and the parent package holds the module attribute it already
    cached -- so a plugin the user deleted altogether would never be forgotten."""
    folder = os.path.join(userPluginsFolder(), 'viz_myanalysisplugin')
    os.makedirs(os.path.join(folder, 'helpers'))
    with open(os.path.join(folder, 'helpers', '__init__.py'), 'w',
              encoding='utf-8') as handle:
        handle.write('')
    with open(os.path.join(folder, 'helpers', 'work.py'), 'w',
              encoding='utf-8') as handle:
        handle.write('answer = 1\n')
    with open(os.path.join(folder, 'MyAnalysisPlugin.py'), 'w',
              encoding='utf-8') as handle:
        handle.write(PLUGIN % 'the first thing')
    attachUserPackage()

    from imasviz_user_plugins.viz_myanalysisplugin.helpers import work
    from imasviz_user_plugins.viz_myanalysisplugin.MyAnalysisPlugin import \
        MyAnalysisPlugin
    assert work.answer == 1 and MyAnalysisPlugin is not None

    forgotten = forgetUserModules()

    assert forgotten == [
        'imasviz_user_plugins',
        'imasviz_user_plugins.viz_myanalysisplugin',
        'imasviz_user_plugins.viz_myanalysisplugin.MyAnalysisPlugin',
        'imasviz_user_plugins.viz_myanalysisplugin.helpers',
        'imasviz_user_plugins.viz_myanalysisplugin.helpers.work']
    for name in forgotten:
        assert name not in sys.modules


def test_reload_everywhere_reaches_every_open_view_and_says_how_many(qtbot):
    """One edited file, every case on screen. The count is what makes the answer
    checkable: a reload nobody can count is a reload nobody believes."""
    first, second = StubView('case?one'), StubView('case?two')
    qtbot.addWidget(first)
    qtbot.addWidget(second)
    writePlugin('the first thing')
    first.pluginCatalog = QVizPluginCatalog(first)
    second.pluginCatalog = QVizPluginCatalog(second)
    assert labelsOf(first.pluginCatalog) == ['the first thing']

    writePlugin('the second thing')
    views = reloadEverywhere(Api(first, second))

    assert views == 2
    assert labelsOf(first.pluginCatalog) == ['the second thing']
    assert labelsOf(second.pluginCatalog) == ['the second thing']


def test_a_view_that_never_built_its_plugins_costs_nothing_and_builds_nothing():
    """A view nobody right-clicked has nothing cached, so there is nothing to put
    back -- and a reload must not be what pays for importing its plugins."""
    writePlugin('the first thing')
    untouched = StubView()

    assert reloadEverywhere(Api(untouched)) == 0
    assert untouched.pluginCatalog is None


# ---------------------------------------------------------------------------
# The watcher: what a save announces, and what is done with it
# ---------------------------------------------------------------------------

def test_the_folder_and_the_plugins_it_holds_are_watched_from_the_start(watcherOf):
    writePlugin()
    watcher = watcherOf()

    assert userPluginsFolder() in watcher.watched()
    assert pluginFile() in watcher.watched()


def test_a_folder_that_does_not_exist_yet_is_not_watched_and_costs_nothing(watcherOf):
    """A first run has no such folder, and `QFileSystemWatcher` cannot watch what
    is not there. Nothing to say, nothing to reload, no refusal."""
    watcher = watcherOf()

    assert watcher.watch() == []
    assert watcher.watched() == []
    assert watcher.reload() == 0


def test_one_save_is_one_reload_however_many_signals_it_emitted(view, watcherOf):
    """Measured: a save by rename emits two signals -- a directory change and a
    file change naming the old path. Without the debounce that is two reloads of
    every view for one press of the save key."""
    path = writePlugin('the first thing')
    view.pluginCatalog = QVizPluginCatalog(view)
    assert labelsOf(view.pluginCatalog) == ['the first thing']
    watcher = watcherOf(view)
    writePlugin('the second thing')

    watcher._directoryChanged(userPluginsFolder())
    watcher._fileChanged(path)
    # Nothing has happened yet: the timer is what decides, not the signals.
    assert labelsOf(view.pluginCatalog) == ['the first thing']

    assert watcher.flush() == 1
    assert labelsOf(view.pluginCatalog) == ['the second thing']
    assert watcher.views == 1


def test_a_file_saved_by_rename_is_watched_again_after_the_flush(view, watcherOf):
    """Measured: after `os.replace` over a watched file, `files()` is empty. So
    without the second `watch` at the end of a flush, the first save from such an
    editor is the last one anyone ever sees change."""
    path = writePlugin('the first thing')
    watcher = watcherOf(view)
    assert path in watcher.watched()

    temporary = path + '.new'
    with open(temporary, 'w', encoding='utf-8') as handle:
        handle.write(PLUGIN % 'the second thing')
    os.replace(temporary, path)

    watcher._directoryChanged(userPluginsFolder())
    watcher._fileChanged(path)
    watcher.flush()

    assert path in watcher.watched()


def test_a_plugin_folder_created_outside_the_application_is_picked_up(view,
                                                                      watcherOf):
    """A new file under a watched folder announces itself only as a directory
    change -- it was never watched to begin with. That is the whole of how a folder
    copied in, or written by a script, gets in."""
    watcher = watcherOf(view)
    assert watcher.watch() == []
    view.pluginCatalog = QVizPluginCatalog(view)
    assert labelsOf(view.pluginCatalog) == []

    writePlugin('the first thing')
    watcher._directoryChanged(userPluginsFolder())
    watcher.flush()

    assert pluginFile() in watcher.watched()
    assert labelsOf(view.pluginCatalog) == ['the first thing']


def test_a_file_that_no_longer_parses_keeps_the_module_that_answers_today(view,
                                                                          watcherOf,
                                                                          caplog):
    """The half-typed file saved out of habit must not take down the entry that
    works today. What parses replaces what was running; what does not is named in
    the log of the case with the line that stopped it, and its module stays."""
    path = writePlugin('the first thing')
    view.pluginCatalog = QVizPluginCatalog(view)
    assert labelsOf(view.pluginCatalog) == ['the first thing']
    watcher = watcherOf(view)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write('class MyAnalysisPlugin(VizPlugin\n   = =\n')

    with caplog.at_level(logging.ERROR, logger=view.uri):
        watcher._fileChanged(path)
        changed = watcher.flush()

    assert changed == 0
    assert [os.path.basename(one) for one, _ in watcher.refusals] == \
        ['MyAnalysisPlugin.py']
    assert labelsOf(view.pluginCatalog) == ['the first thing']
    assert 'was not put back' in caplog.text
    assert 'MyAnalysisPlugin.py line' in caplog.text


def test_the_plugin_that_parses_again_is_put_back_by_the_next_save(view,
                                                                   watcherOf):
    path = writePlugin('the first thing')
    view.pluginCatalog = QVizPluginCatalog(view)
    assert labelsOf(view.pluginCatalog) == ['the first thing']
    watcher = watcherOf(view)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write('class MyAnalysisPlugin(VizPlugin\n   =\n')
    watcher._fileChanged(path)
    watcher.flush()
    assert labelsOf(view.pluginCatalog) == ['the first thing']

    writePlugin('fixed at last')
    watcher._fileChanged(path)
    watcher.flush()

    assert labelsOf(view.pluginCatalog) == ['fixed at last']
    assert watcher.refusals == []


def test_the_watch_of_a_deleted_plugin_raises_nothing_and_leaves_no_line(view,
                                                                         watcherOf):
    """A deleted plugin leaves the watch list by itself and comes off the menu for
    the same reason it was found: the folder is what is looked at."""
    path = writePlugin('the first thing')
    view.pluginCatalog = QVizPluginCatalog(view)
    watcher = watcherOf(view)
    assert labelsOf(view.pluginCatalog) == ['the first thing']

    shutil.rmtree(os.path.dirname(path))
    watcher._fileChanged(path)
    watcher.flush()

    assert labelsOf(view.pluginCatalog) == []


def test_the_reload_is_said_in_the_log_of_every_open_case(view, watcherOf,
                                                          caplog):
    """A shot view wires its panel to the logger named after its URI, so a plain
    `logging.info` would go where nobody in the GUI is reading."""
    path = writePlugin('the first thing')
    view.pluginCatalog = QVizPluginCatalog(view)
    watcher = watcherOf(view)
    writePlugin('the second thing')

    with caplog.at_level(logging.INFO, logger=view.uri):
        watcher._fileChanged(path)
        watcher.flush()

    assert any('reloaded for 1 shot view' in one.getMessage()
               for one in caplog.records)


def test_a_session_with_no_case_open_still_watches_the_folder(watcherOf):
    """The watcher is made when the window is, before any case exists: a plugin
    saved then has to be ready for the first view opened later -- and a reload with
    no view open answers zero rather than raising."""
    watcher = watcherOf()
    assert userPluginsFolder() not in watcher.watched()

    writePlugin()
    watcher.watch()

    assert pluginFile() in watcher.watched()
    assert watcher.reload() == 0
    assert watcher._views() == []


# ---------------------------------------------------------------------------
# The two ways the session asks for it
# ---------------------------------------------------------------------------

def test_saving_in_the_editor_puts_the_open_cases_back_without_a_watcher(qtbot,
                                                                         view):
    """The editor's *Save* and the file watcher answer the same question and both
    are wired: a file written in IMASViz's own editor has to reach the menu of a
    case that is already open even when nothing is watching the folder."""
    window = AWindow(view)
    qtbot.addWidget(window)
    writePlugin('the first thing')
    view.pluginCatalog = QVizPluginCatalog(view)
    source = findUserSource('MyAnalysisPlugin')
    editor = openEditor(source, parent=window)
    editor.view.setPlainText(PLUGIN % 'the second thing')

    editor._save()

    assert labelsOf(view.pluginCatalog) == ['the second thing']
    editor.deleteLater()


def test_the_file_menu_hands_the_window_s_watcher_to_the_manager(qtbot, view):
    """One watcher serves the session. The *File* menu reaches the one the window
    made instead of making a second, which would watch the same folder twice and
    reload every open view twice for one save."""
    window = AWindow(view)
    qtbot.addWidget(window)
    watcher = QVizPluginWatcher(window.sessionApi, parent=window)
    window.pluginWatcher = watcher
    bar = QMenu()
    qtbot.addWidget(bar)
    fileMenu = QVizFileMenu(bar, window).show()

    manager = fileMenu.openPluginManager()

    assert manager is not None
    assert manager._watcher() is watcher


def test_the_manager_s_reload_button_answers_the_views_it_put_back(qtbot, view):
    """The button next to the table, for the moment the watcher is not enough: the
    folder on a remote file system, an editor that writes through a path the
    watcher never saw."""
    writePlugin('the first thing')
    view.pluginCatalog = QVizPluginCatalog(view)
    writePlugin('the second thing')
    manager = QVizPluginManager(None, apiOf=Api(view))
    qtbot.addWidget(manager)

    assert manager._reload() == 1
    assert labelsOf(view.pluginCatalog) == ['the second thing']


def test_the_compile_check_names_the_file_and_the_line_it_stopped_at():
    """The message every refusal about a plugin source carries, checked at the
    source of it: the editor, the watcher and the creator all ask this one."""
    with pytest.raises(ValueError) as refusal:
        compileCheck('x = (\n', '/here/my_plugin.py')
    assert str(refusal.value).startswith('/here/my_plugin.py line')
