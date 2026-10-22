# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Which plugins a node earns, how they are asked, and what clicking one does.

Everything below was measured on the reference case before the catalog replaced
`QVizPluginsPopUpMenu` (29 lines, whose one method was spelled `upateMenu`) and
`QVizPluginsHandler` (140 lines):

* the first right click of a process paid **0,999 s** for the menu, the second
  **0,0425 s** and the third **0,0008 s** -- `getPluginsObjects` alone took
  **4,186 s** cold, and the launch chain imports no plugin at all, so the whole
  cost (matplotlib among them) sat on the gesture, paid again per view;
* a plugin raising inside `getEntries` left **0 entries** for the other plugins
  and the exception escaped the right click;
* `getEntries()` answering `[2]` with two descriptions answered `IndexError`:
  the label was read at the **position**, not by the **number**;
* a plugin honouring every documented method but not inheriting `VizPlugin` was
  **invisible without a word**;
* every entry carried the id **9999** under a `# TODO: properly set ID`, and the
  click dispatched on the position in a list that grew with every menu built on
  the same handler: two `upateMenu` calls on one menu showed **6 lines instead
  of 3**;
* Shift+right click showed a **menu with no line in it** -- 42 of the reference
  case's 55 IDS names are claimed by no plugin;
* right click on a quantity answered `AttributeError: 'NoneType' object has no
  attribute 'getDataType'`: the menu decided from the view's selection, not from
  the node under the cursor, and with nothing selected there was nothing to ask;
* a **.ui** plugin loads, but Qt answers "QFormBuilder was unable to create a
  custom widget of the class 'exampleWidget'; defaulting to base class 'QWidget'"
  and drops the 10 connections `examplePlugin.ui` makes to it (3 for
  `SOLPSplugin.ui`), so the window that comes out is hollow -- `createWidget` is
  never called. It is refused by name instead of shown.
"""

import gc
import importlib
import logging
import os
import sys
import types

import pytest
import shiboken6

from PySide6.QtWidgets import QMenu, QTreeWidget

from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
    import QVizLoadOccurrence
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizHandleShiftAndRightClick \
    import QVizHandleShiftAndRightClick
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizPluginMenu \
    import QVizPluginMenu
from imasviz.VizPlugins.QVizPluginCatalog import QVizPluginCatalog
from imasviz.VizPlugins.VizPlugin import VizPlugin

from conftest import (CASE_DATA_DICTIONARY_VERSION, IMAS_TEST_VERSION,
                      case_uri_or_skip)
from support.fakes import FakeTreeNode

# The catalog looks `getRegisteredPlugins` up in its own module, so that is where
# a registration has to be replaced for a stub to be seen.
CATALOG = importlib.import_module('imasviz.VizPlugins.QVizPluginCatalog')
LOADING = importlib.import_module('imasviz.VizGUI.VizGUICommands.VizDataLoading'
                                  '.QVizLoadOccurrence')

STUB_PACKAGE = 'viz_stubs_for_the_plugin_menu_tests.stub'

# What the stub plugins report back.
BUILT = []
RAN = []


class StubView(QTreeWidget):
    """Enough of a shot view for a catalog and the menu that reads it.

    A real `QTreeWidget`, not a stand-in object: a window drawn from a .ui file
    is built with the view as its Qt parent, and Qt refuses anything else.
    """

    def __init__(self, uri='stub?case'):
        super().__init__()
        self.uri = uri
        self.pluginCatalog = None
        self.imas_viz_api = 'the-api-of-this-view'


@pytest.fixture
def view(qtbot):
    widget = StubView()
    # The view owns the menus and the .ui windows built on it: dropping it here
    # takes them down in the middle of a later test.
    qtbot.addWidget(widget)
    return widget


@pytest.fixture(autouse=True)
def _empty_counters():
    BUILT.clear()
    RAN.clear()


def registerStubs(monkeypatch, *plugins):
    """Register stub classes the way the catalog reads a Python plugin.

    A string registration is resolved by importing `imasviz.VizPlugins.<path>`
    and taking the class named after the key, so the stubs are handed over as
    such a module: the import path the production code walks stays the one under
    test.
    """
    module = types.ModuleType('imasviz.VizPlugins.' + STUB_PACKAGE)
    for plugin in plugins:
        setattr(module, plugin.__name__, plugin)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setattr(CATALOG, 'getRegisteredPlugins',
                        lambda: {plugin.__name__: STUB_PACKAGE
                                 for plugin in plugins})


def registerUiPlugins(monkeypatch, registrations):
    """Register .ui plugins under the dictionary shape the manual shows."""
    monkeypatch.setattr(CATALOG, 'getRegisteredPlugins',
                        lambda: registrations)


# --------------------------------------------------------------------------
# The stubs, one per behaviour a plugin can have
# --------------------------------------------------------------------------

class DeclaresSeven:
    """Every documented method, and no inheritance from the base class.

    Measured: the framework gated on `isinstance(plugin, VizPlugin)` and fell
    back on a table naming two plugins that are not registered, so this plugin
    got no line in the menu at all, and nothing was logged.
    """

    def __init__(self):
        BUILT.append('DeclaresSeven')
        self.askedOn = []

    def setSelectedTreeNode(self, node):
        self.askedOn.append(node)

    def isEnabled(self):
        return True

    def getEntries(self):
        return [7]

    def getAllEntries(self):
        return [(0, 'the first'), (1, 'the second'), (7, 'the seventh')]

    def getDescription(self):
        return 'what the seventh entry is for'

    def execute(self, vizAPI, pluginEntry):
        RAN.append(('DeclaresSeven', vizAPI, pluginEntry))


class UndescribedNumber(VizPlugin):
    """Asks for an entry its `getAllEntries` says nothing about."""

    def __init__(self):
        super().__init__()
        BUILT.append('UndescribedNumber')

    def isEnabled(self):
        return True

    def getEntries(self):
        return [2]

    def getAllEntries(self):
        return [(0, 'zero'), (1, 'one')]


class RaisesWhileAnswering(VizPlugin):
    def __init__(self):
        super().__init__()
        BUILT.append('RaisesWhileAnswering')

    def isEnabled(self):
        return True

    def getEntries(self):
        raise KeyError('profiles_1d')


class OffersNothingForThisNode(VizPlugin):
    """What `VizProfiles_plugin.getEntries` answers for an IDS it does not claim.

    It falls off the end of the method and answers None; the old menu read that
    as an empty list only by accident.
    """

    def __init__(self):
        super().__init__()
        BUILT.append('OffersNothingForThisNode')

    def isEnabled(self):
        return True

    def getEntries(self):
        return None


class NotEnabled(VizPlugin):
    def __init__(self):
        super().__init__()
        BUILT.append('NotEnabled')

    def isEnabled(self):
        return False

    def getEntries(self):
        raise AssertionError('a disabled plugin was asked what it offers')


class DeclaresZero:
    """Records the entry it was run with, like `DeclaresSeven`."""

    def __init__(self):
        BUILT.append('DeclaresZero')

    def setSelectedTreeNode(self, node):
        pass

    def isEnabled(self):
        return True

    def getEntries(self):
        return [0]

    def getAllEntries(self):
        return [(0, 'the first'), (1, 'the second')]

    def execute(self, vizAPI, pluginEntry):
        RAN.append(('DeclaresZero', vizAPI, pluginEntry))


class RefusesToRun(VizPlugin):
    def __init__(self):
        super().__init__()
        BUILT.append('RefusesToRun')

    def isEnabled(self):
        return True

    def getEntries(self):
        return [1]

    def getAllEntries(self):
        return [(1, 'draw the panel')]

    def getDescription(self):
        return 'draws a panel this case cannot fill'

    def execute(self, vizAPI, pluginEntry):
        raise ValueError('this case holds no equilibrium IDS')


class CrashesWhileRunning(VizPlugin):
    def __init__(self):
        super().__init__()
        BUILT.append('CrashesWhileRunning')

    def isEnabled(self):
        return True

    def getEntries(self):
        return [3]

    def getAllEntries(self):
        return [(3, 'plot the slices')]

    def execute(self, vizAPI, pluginEntry):
        raise KeyError('time_slice')


def menuOn(view, node, parent=None):
    """The Plugins sub-menu this node earns, as Qt builds it."""
    parent = parent or QMenu()
    parent.setParent(view)
    return QVizPluginMenu().addPluginsMenu(node, view, parent)


# --------------------------------------------------------------------------
# What a plugin is asked, and what its answer means
# --------------------------------------------------------------------------

def test_an_entry_is_found_by_the_number_the_plugin_declared(monkeypatch, view):
    # Measured: `getEntries()` answering [2] with two descriptions answered
    # IndexError, because the label was read at the position in getAllEntries().
    registerStubs(monkeypatch, DeclaresSeven)
    entries = QVizPluginCatalog(view).entriesFor(
        FakeTreeNode(idsName='equilibrium'))
    assert [(entry.number, entry.label) for entry in entries] == \
        [(7, 'the seventh')]
    assert entries[0].description == 'what the seventh entry is for'


def test_a_number_the_plugin_does_not_describe_is_refused_with_the_ones_it_does(
        monkeypatch, view):
    registerStubs(monkeypatch, UndescribedNumber)
    catalog = QVizPluginCatalog(view)
    assert catalog.entriesFor(FakeTreeNode(idsName='equilibrium')) == []
    assert len(catalog.refusals) == 1
    assert 'UndescribedNumber' in catalog.refusals[0]
    assert 'entry 2' in catalog.refusals[0]
    assert '[0, 1]' in catalog.refusals[0]


def test_a_plugin_raising_while_answering_leaves_the_others_their_lines(
        monkeypatch, view, caplog):
    # Measured: 0 entries left, and the exception escaped the right click.
    registerStubs(monkeypatch, DeclaresSeven, RaisesWhileAnswering)
    catalog = QVizPluginCatalog(view)
    with caplog.at_level(logging.ERROR, logger=view.uri):
        entries = catalog.entriesFor(FakeTreeNode(idsName='equilibrium'))
    assert [entry.label for entry in entries] == ['the seventh']
    assert 'RaisesWhileAnswering' in catalog.refusals[0]
    assert "KeyError: 'profiles_1d'" in caplog.text


def test_a_registration_that_no_longer_resolves_is_refused_by_name(
        monkeypatch, view):
    # A stale entry used to raise ModuleNotFoundError out of the loop that built
    # the menu, taking every other plugin with it.
    monkeypatch.setattr(CATALOG, 'getRegisteredPlugins',
                        lambda: {'gone_plugin': 'viz_gone.gone_plugin',
                                 'DeclaresSeven': STUB_PACKAGE})
    module = types.ModuleType('imasviz.VizPlugins.' + STUB_PACKAGE)
    module.DeclaresSeven = DeclaresSeven
    monkeypatch.setitem(sys.modules, module.__name__, module)

    catalog = QVizPluginCatalog(view)
    entries = catalog.entriesFor(FakeTreeNode(idsName='equilibrium'))
    assert [entry.pluginName for entry in entries] == ['DeclaresSeven']
    assert 'ModuleNotFoundError' in catalog.refusals[0]
    assert 'gone_plugin' in catalog.refusals[0]


def test_a_plugin_outside_the_base_class_is_offered_like_the_others(
        monkeypatch, view):
    assert not issubclass(DeclaresSeven, VizPlugin)
    registerStubs(monkeypatch, DeclaresSeven)
    assert QVizPluginCatalog(view).entriesFor(
        FakeTreeNode(idsName='equilibrium')) != []


def test_a_plugin_with_nothing_for_this_node_answers_nothing(monkeypatch, view):
    registerStubs(monkeypatch, OffersNothingForThisNode)
    catalog = QVizPluginCatalog(view)
    assert catalog.entriesFor(FakeTreeNode(idsName='magnetics')) == []
    # Offering nothing is not a failure; nothing is logged against the plugin.
    assert catalog.refusals == []


def test_a_disabled_plugin_is_not_asked_what_it_offers(monkeypatch, view):
    registerStubs(monkeypatch, NotEnabled)
    catalog = QVizPluginCatalog(view)
    assert catalog.entriesFor(FakeTreeNode(idsName='equilibrium')) == []
    assert catalog.refusals == []


def test_a_plugin_decides_from_the_node_the_menu_was_built_on(monkeypatch,
                                                              view):
    # The framework handed the plugin the view's selection instead.
    registerStubs(monkeypatch, DeclaresSeven)
    catalog = QVizPluginCatalog(view)
    first = FakeTreeNode(idsName='equilibrium')
    second = FakeTreeNode(idsName='core_profiles')
    catalog.entriesFor(first)
    catalog.entriesFor(second)
    plugin = catalog.plugins()[0][1]
    assert plugin.askedOn == [first, second]


def test_the_plugins_of_a_view_are_built_once_however_many_menus_are_built(
        monkeypatch, view):
    # Measured: 0,999 s for the first right click of a process, 0,0425 s for the
    # second, 0,0008 s afterwards -- every menu imported and built them again.
    registerStubs(monkeypatch, DeclaresSeven)
    node = FakeTreeNode(idsName='equilibrium')
    menu = QMenu()
    menu.setParent(view)
    assert QVizPluginMenu().buildPluginsMenu(node, view, menu) == 1
    assert QVizPluginMenu().buildPluginsMenu(node, view, menu) == 1
    assert BUILT == ['DeclaresSeven']
    assert view.pluginCatalog.plugins() is view.pluginCatalog.plugins()


# --------------------------------------------------------------------------
# Running the entry a line stands for
# --------------------------------------------------------------------------

def test_the_number_a_plugin_declared_is_the_number_it_is_asked_for(monkeypatch,
                                                                   view):
    # The old click dispatched on the position in the menu, and gave every entry
    # the same id, 9999, then read it back and threw it away.
    registerStubs(monkeypatch, DeclaresSeven)
    entry = QVizPluginCatalog(view).entriesFor(
        FakeTreeNode(idsName='equilibrium'))[0]
    QVizPluginCatalog(view).run(entry)
    assert RAN == [('DeclaresSeven', 'the-api-of-this-view', 7)]


def test_the_line_of_a_menu_carries_its_own_plugin_and_its_own_number(
        monkeypatch, view):
    # The old click found the plugin by the position of the line in a list that
    # grew with every menu built on the same handler, and gave every entry the
    # same id, 9999.
    registerStubs(monkeypatch, DeclaresZero, DeclaresSeven)
    menu = QMenu()
    menu.setParent(view)
    assert QVizPluginMenu().buildPluginsMenu(FakeTreeNode(idsName='equilibrium'),
                                             view, menu) == 2
    actions = menu.actions()
    assert [action.text() for action in actions] == ['the first', 'the seventh']
    actions[-1].trigger()
    assert RAN == [('DeclaresSeven', 'the-api-of-this-view', 7)]


def test_a_plugin_that_refuses_says_why_under_its_own_name(monkeypatch, view,
                                                           caplog):
    # The framework caught everything with a bare `except:` and printed a
    # traceback on stdout: in the GUI the entry simply did nothing.
    registerStubs(monkeypatch, RefusesToRun)
    catalog = QVizPluginCatalog(view)
    entry = catalog.entriesFor(FakeTreeNode(idsName='equilibrium'))[0]
    with caplog.at_level(logging.INFO, logger=view.uri):
        catalog.run(entry)
    assert 'Plugin RefusesToRun could not run: this case holds no ' \
           'equilibrium IDS' in caplog.text


def test_a_plugin_that_crashes_is_named_with_the_exception_that_came_out(
        monkeypatch, view, caplog):
    registerStubs(monkeypatch, CrashesWhileRunning)
    catalog = QVizPluginCatalog(view)
    entry = catalog.entriesFor(FakeTreeNode(idsName='equilibrium'))[0]
    with caplog.at_level(logging.INFO, logger=view.uri):
        catalog.run(entry)
    assert "Plugin CrashesWhileRunning failed: KeyError: 'time_slice'" \
        in caplog.text


def test_an_entry_is_logged_before_it_is_handed_over(monkeypatch, view, caplog):
    registerStubs(monkeypatch, DeclaresSeven)
    catalog = QVizPluginCatalog(view)
    with caplog.at_level(logging.INFO, logger=view.uri):
        catalog.run(catalog.entriesFor(FakeTreeNode(idsName='equilibrium'))[0])
    assert 'Running plugin DeclaresSeven, entry 7.' in caplog.text


# --------------------------------------------------------------------------
# The sub-menu itself
# --------------------------------------------------------------------------

def test_a_menu_no_plugin_fills_is_not_added_at_all(monkeypatch, view):
    # Measured: the 'Plugins' sub-menu was added before anyone knew whether it
    # had anything to put in it, and showed empty.
    registerStubs(monkeypatch, OffersNothingForThisNode)
    parent = QMenu()
    parent.setParent(view)
    assert QVizPluginMenu().addPluginsMenu(FakeTreeNode(idsName='magnetics'),
                                           view, parent) is None
    assert [action.text() for action in parent.actions()] == []


def test_a_menu_a_plugin_fills_is_added_once_with_its_lines(monkeypatch, view):
    registerStubs(monkeypatch, DeclaresSeven)
    parent = QMenu()
    parent.setParent(view)
    subMenu = QVizPluginMenu().addPluginsMenu(
        FakeTreeNode(idsName='equilibrium'), view, parent)
    assert [action.text() for action in parent.actions()] == ['Plugins']
    assert subMenu is not None
    assert [action.text() for action in subMenu.actions()] == ['the seventh']
    # The description is what the status bar says while the line is under the
    # mouse, and what a two-line entry shows as a tooltip.
    assert subMenu.actions()[0].statusTip() == 'what the seventh entry is for'
    assert subMenu.toolTipsVisible() is True


def test_the_sub_menu_outlives_the_one_who_built_it(monkeypatch, view):
    # Measured with `parentMenu.addMenu(title)`: the three gestures drop the
    # wrapper that call returns as soon as they are done, and reading the
    # sub-menu back from its action then answered `RuntimeError: Internal C++
    # object (PySide6.QtWidgets.QMenu) already deleted` -- in the GUI only after
    # the gesture's own frame had gone, which is why it went unnoticed.
    registerStubs(monkeypatch, DeclaresSeven)
    parent = QMenu()
    parent.setParent(view)
    QVizPluginMenu().addPluginsMenu(FakeTreeNode(idsName='equilibrium'), view,
                                    parent)
    gc.collect()
    subMenu = parent.actions()[0].menu()
    assert shiboken6.isValid(subMenu)
    assert [action.text() for action in subMenu.actions()] == ['the seventh']


# --------------------------------------------------------------------------
# A window drawn in Qt Designer
# --------------------------------------------------------------------------

PLAIN_UI = '''<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>MainWindow</class>
 <widget class="QMainWindow" name="plainPanel">
  <widget class="QWidget" name="plainPluginWidget">
   <layout class="QVBoxLayout" name="layout">
    <item>
     <widget class="QLabel" name="greeting">
      <property name="text"><string>Nothing to see here</string></property>
     </widget>
    </item>
   </layout>
  </widget>
 </widget>
</ui>
'''


def registerPlainUi(monkeypatch, tmp_path, idsRoot='magnetics'):
    path = tmp_path / 'plainPanel.ui'
    path.write_text(PLAIN_UI)
    registerUiPlugins(monkeypatch, {
        'plainUiPlugin': {'UiFile': 'plainPanel.ui', 'dir': str(tmp_path),
                          'targetIDSroot': idsRoot, 'targetOccurrence': 0}})


def test_a_window_drawn_with_qt_classes_only_is_offered_for_the_ids_it_names(
        monkeypatch, view, tmp_path):
    registerPlainUi(monkeypatch, tmp_path)
    catalog = QVizPluginCatalog(view)
    entries = catalog.entriesFor(FakeTreeNode(idsName='magnetics'))
    assert [entry.label for entry in entries] == ['Show the plainUiPlugin panel']
    assert entries[0].plugin.targetIDSroot == 'magnetics'
    assert entries[0].plugin.targetOccurrence == 0
    # The window claims one IDS and no other, whatever node is clicked.
    assert catalog.entriesFor(FakeTreeNode(idsName='interferometer')) == []


def test_opening_that_window_loads_the_ids_it_was_drawn_around(monkeypatch,
                                                               view, tmp_path,
                                                               caplog):
    registerPlainUi(monkeypatch, tmp_path)

    # The window loads through a local import, so the module attribute is what
    # has to be replaced -- and it is the class every other load goes through.
    assert getattr(LOADING, 'QVizLoadOccurrence') is QVizLoadOccurrence

    class StubLoad:
        asked = []

        def __init__(self, **kwargs):
            StubLoad.asked.append(kwargs)

        def execute(self):
            pass

    monkeypatch.setattr(LOADING, 'QVizLoadOccurrence', StubLoad)
    catalog = QVizPluginCatalog(view)
    with caplog.at_level(logging.INFO, logger=view.uri):
        catalog.run(catalog.entriesFor(FakeTreeNode(idsName='magnetics'))[0])
    # Measured: the window used to load through `dataSource.load`, which since
    # T12 is not a whole load any more -- no guard, no slice, no label.
    assert StubLoad.asked == [{'dataTreeView': view, 'idsName': 'magnetics',
                               'occurrence': 0}]
    assert 'Showing the panel of plugin plainUiPlugin.' in caplog.text


@pytest.mark.parametrize('uiFile, widgetClass', [
    ('examplePlugin.ui', 'exampleWidget'),
    ('SOLPSplugin.ui', 'SOLPSwidget'),
])
def test_a_window_drawn_around_a_widget_this_qt_cannot_build_is_refused_by_name(
        monkeypatch, view, uiFile, widgetClass):
    # Measured: the file loads, Qt answers "unable to create a custom widget of
    # the class 'exampleWidget'; defaulting to base class 'QWidget'" and drops
    # the 10 connections that .ui makes to it (3 for SOLPSplugin.ui). Overriding
    # createWidget changes nothing: it is never called.
    directory = os.environ['VIZ_HOME'] + '/imasviz/VizPlugins/viz_' + \
        ('example' if 'example' in uiFile else 'solps') + '/'
    registerUiPlugins(monkeypatch, {
        'someUiPlugin': {'UiFile': uiFile, 'dir': directory,
                         'targetIDSroot': 'magnetics', 'targetOccurrence': 0}})
    catalog = QVizPluginCatalog(view)
    assert catalog.entriesFor(FakeTreeNode(idsName='magnetics')) == []
    assert widgetClass in catalog.refusals[0]
    assert uiFile in catalog.refusals[0]


def test_a_window_that_cannot_be_opened_is_refused_with_the_file_it_is(monkeypatch,
                                                                      view,
                                                                      tmp_path):
    # Measured: QUiLoader does not return None for an unreadable file, it raises
    # RuntimeError: Unable to open/read ui device.
    registerUiPlugins(monkeypatch, {
        'missingUiPlugin': {'UiFile': 'no_such_window.ui', 'dir': str(tmp_path),
                            'targetIDSroot': 'magnetics',
                            'targetOccurrence': 0}})
    catalog = QVizPluginCatalog(view)
    assert catalog.entriesFor(FakeTreeNode(idsName='magnetics')) == []
    assert 'no_such_window.ui could not be loaded' in catalog.refusals[0]


def test_a_window_registered_without_saying_where_it_is_refused(monkeypatch,
                                                                view):
    registerUiPlugins(monkeypatch, {'namelessUiPlugin': {
        'targetIDSroot': 'magnetics', 'targetOccurrence': 0}})
    catalog = QVizPluginCatalog(view)
    assert catalog.entriesFor(FakeTreeNode(idsName='magnetics')) == []
    assert 'UiFile' in catalog.refusals[0]


# --------------------------------------------------------------------------
# The two plugins this application really registers, on the reference case
# --------------------------------------------------------------------------

def aShotView(qapp):
    """One shot view of the reference case, held for as long as its menus are."""
    from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource
    from imasviz.VizGUI.VizTreeView.QVizDataTreeView import QVizDataTreeViewFrame
    from imasviz.VizUtils import QVizGlobalOperations, QVizPreferences

    QVizPreferences().build()
    source = QVizIMASDataSource('west 54924', case_uri_or_skip())
    source.dd_version = CASE_DATA_DICTIONARY_VERSION
    frame = QVizDataTreeViewFrame(None, [], source,
                                  QVizGlobalOperations.getIDSDefFile(
                                      IMAS_TEST_VERSION),
                                  None)
    # The frame, not the view: the view is what owns the menus built on it, and
    # an owner dropped by a helper takes them down in a later test.
    return frame


@pytest.mark.case
@pytest.mark.ui
@pytest.mark.dd
def test_the_reference_case_offers_three_lines_for_equilibrium(qtbot):
    frame = aShotView(qtbot)
    qtbot.addWidget(frame)
    entries = QVizPluginCatalog(frame.dataTreeView).entriesFor(
        frame.dataTreeView.IDSRoots['equilibrium'])
    # equilibriumcharts offers one, VizProfiles_plugin two -- and the numbers
    # they run under are theirs, not their place in the menu.
    assert [(entry.pluginName, entry.number, entry.label)
            for entry in entries] == [
        ('equilibriumcharts', 0, 'Equilibrium overview...'),
        ('VizProfiles_plugin', 0, 'Visualization of 1D nodes from '
                                  'time_slice(itime) along coordinate1 axis...'),
        ('VizProfiles_plugin', 1, 'Visualization of 0D/1D nodes from '
                                  'time_slice(itime) along time axis...')]


@pytest.mark.case
@pytest.mark.ui
@pytest.mark.dd
def test_the_reference_case_offers_two_lines_for_core_profiles(qtbot):
    frame = aShotView(qtbot)
    qtbot.addWidget(frame)
    entries = QVizPluginCatalog(frame.dataTreeView).entriesFor(
        frame.dataTreeView.IDSRoots['core_profiles'])
    assert [(entry.pluginName, entry.number) for entry in entries] == \
        [('VizProfiles_plugin', 0), ('VizProfiles_plugin', 1)]


@pytest.mark.case
@pytest.mark.ui
@pytest.mark.dd
def test_an_ids_no_plugin_claims_gets_no_plugins_sub_menu(qtbot):
    # Measured: 42 of the 55 IDS names of this case are claimed by no plugin,
    # and every one of them got a 'Plugins' sub-menu with nothing in it.
    frame = aShotView(qtbot)
    qtbot.addWidget(frame)
    view = frame.dataTreeView
    parent = QMenu()
    parent.setParent(view)
    assert QVizPluginMenu().addPluginsMenu(view.IDSRoots['magnetics'], view,
                                           parent) is None
    assert [action.text() for action in parent.actions()] == []


@pytest.mark.case
@pytest.mark.ui
@pytest.mark.dd
def test_the_shift_right_click_of_an_unclaimed_ids_logs_instead_of_opening_a_menu(
        qtbot, caplog):
    # This gesture offers the plugins and nothing else, so it used to open an
    # empty menu on 42 IDSs out of 55.
    frame = aShotView(qtbot)
    qtbot.addWidget(frame)
    view = frame.dataTreeView
    with caplog.at_level(logging.INFO, logger=view.uri):
        QVizHandleShiftAndRightClick(view).execute(view.IDSRoots['magnetics'])
    assert 'No plugin offers anything for the magnetics IDS.' in caplog.text


@pytest.mark.case
@pytest.mark.ui
@pytest.mark.dd
def test_the_right_click_menu_of_a_node_offers_the_plugins_of_that_node(qtbot):
    # Measured: right click on a quantity with nothing selected answered
    # AttributeError: 'NoneType' object has no attribute 'getDataType' -- the
    # menu decided from the view's selection, which was None.
    from imasviz.Viz_API import Viz_API
    from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
        import QVizSignalHandling

    frame = aShotView(qtbot)
    qtbot.addWidget(frame)
    view = frame.dataTreeView
    view.imas_viz_api = Viz_API()
    handling = QVizSignalHandling(view)
    handling.buildContextMenu(view.IDSRoots['equilibrium'])
    # The gesture keeps no reference of its own to the sub-menu it added, so
    # this reads it back the way Qt shows it -- see
    # test_the_sub_menu_outlives_the_one_who_built_it.
    plugins = [action for action in handling.contextMenu.actions()
               if action.text() == 'Plugins'][0].menu()
    assert shiboken6.isValid(plugins)
    assert [action.text() for action in plugins.actions()] == [
        'Equilibrium overview...',
        'Visualization of 1D nodes from time_slice(itime) along coordinate1 '
        'axis...',
        'Visualization of 0D/1D nodes from time_slice(itime) along time '
        'axis...']


@pytest.mark.case
@pytest.mark.ui
@pytest.mark.dd
def test_a_view_asks_its_two_plugins_once_across_its_menus(qtbot):
    frame = aShotView(qtbot)
    qtbot.addWidget(frame)
    view = frame.dataTreeView
    first = QVizPluginMenu().catalogOf(view)
    second = QVizPluginMenu().catalogOf(view)
    assert first is second is view.pluginCatalog
    assert sorted(name for name, _ in first.plugins()) == \
        ['VizProfiles_plugin', 'equilibriumcharts']
    equilibrium = view.IDSRoots['equilibrium']
    for _ in range(3):
        menu = QMenu()
        menu.setParent(view)
        assert QVizPluginMenu().buildPluginsMenu(equilibrium, view, menu) == 3
