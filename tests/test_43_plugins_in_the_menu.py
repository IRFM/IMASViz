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
from imasviz.VizPlugins.VizPlugin import (IDS, NODE, CASE, APP,
                                          QVizPluginAction, QVizPluginAnswers,
                                          QVizPluginScope,
                                          QVizPluginContext,
                                          VizPlugin)

from conftest import CASE_DATA_DICTIONARY_VERSION, case_uri_or_skip
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

        class _Occ:
            def occurrencesOf(self, ids): return [0]
        self.occurrences = _Occ()
        self.dataSource = types.SimpleNamespace(uri=uri)
        self.IDSRoots = {}


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
    """Every documented attribute, and no inheritance from the base class.

    Declares a scope (any IDS) and three actions -- zero, one and seven -- the
    way the contract says a plugin that honours the contract does. Nothing else
    is asked of it; the framework reads the scope and the actions, and calls
    the action with a context that already holds the api, the case, and the
    node the menu was built on.
    """

    def _run(self, context):
        RAN.append(('DeclaresSeven', context.api, 7))

    def __init__(self):
        BUILT.append('DeclaresSeven')
        self.SCOPE = QVizPluginScope(IDS)
        self.ACTIONS = (
            QVizPluginAction(0, 'the first', run=self._run),
            QVizPluginAction(1, 'the second', run=self._run),
            QVizPluginAction(7, 'the seventh', run=self._run,
                             description='what the seventh entry is for'))

    # Only entry 7 is offered: the same rule the old getEntries() enforced.
    def offered(self, context):
        return [one for one in self.ACTIONS if one.key == 7]


class TakesAnswers(VizPlugin):
    """A session replaying this line hands over what the user answered the first
    time instead of letting the entry ask again: the context it reads is the
    one the catalog built, and `context.answers` is the answer if one was given.
    """

    def _run(self, context):
        RAN.append(('TakesAnswers', context.api, 4, context.answers))

    def __init__(self):
        super().__init__()
        BUILT.append('TakesAnswers')
        self.SCOPE = QVizPluginScope(IDS)
        self.ACTIONS = (QVizPluginAction(4, 'the answered one', run=self._run),)


class ClaimsEquilibriumOnly(VizPlugin):
    """A plugin that offers itself on one IDS name and on no other.

    The scope names the one IDS it claims; the framework checks it on every
    node and offers nothing on any other -- the two refusals an unclaimed IDS
    answers are now the scope test, not a separate `isEnabled` call.
    """

    def _run(self, context):
        RAN.append(('ClaimsEquilibriumOnly', context.api, 3, context.answers))

    def __init__(self):
        super().__init__()
        BUILT.append('ClaimsEquilibriumOnly')
        self.SCOPE = QVizPluginScope(IDS, ids=('equilibrium',))
        self.ACTIONS = (QVizPluginAction(3, 'only on equilibrium',
                                         run=self._run),)


class TakesAnything(VizPlugin):
    """The same contract, reading `answers` off the context rather than from a
    keyword argument -- the session replay is in the context either way."""

    def _run(self, context):
        RAN.append(('TakesAnything', context.api, 5, context.answers))

    def __init__(self):
        super().__init__()
        BUILT.append('TakesAnything')
        self.SCOPE = QVizPluginScope(IDS)
        self.ACTIONS = (QVizPluginAction(5, 'the wide one', run=self._run),)


class UndescribedNumber(VizPlugin):
    """An action whose run is None: the line says what it is, but has no work.

    The old contract answered this by having a number the description table did
    not explain; the new one has no such split, so the guard it tests is the
    one that actually exists now -- an action without a run is named and left
    out, the ones with a keep their line.
    """

    def _run0(self, context): RAN.append(('UndescribedNumber', context.api, 0))
    def _run1(self, context): RAN.append(('UndescribedNumber', context.api, 1))

    def __init__(self):
        super().__init__()
        BUILT.append('UndescribedNumber')
        self.SCOPE = QVizPluginScope(IDS)
        self.ACTIONS = (
            QVizPluginAction(0, 'zero', run=self._run0),
            QVizPluginAction(1, 'one', run=self._run1),
            QVizPluginAction(2, 'the one with no work'))


class RaisesWhileAnswering(VizPlugin):
    """A plugin that refuses the question before the framework can read it.

    In the new contract the refusal is a `KeyError` out of `offered` -- the
    framework catches it, names the plugin in the log, and drops the line. No
    entry is left, no other plugin is cost its own.
    """

    def __init__(self):
        super().__init__()
        BUILT.append('RaisesWhileAnswering')
        self.SCOPE = QVizPluginScope(IDS)
        self.ACTIONS = (QVizPluginAction(1, 'would be here',
                                         run=lambda ctx: None),)

    def offered(self, context):
        raise KeyError('profiles_1d')


class OffersNothingForThisNode(VizPlugin):
    """A plugin that declares no actions: an empty ACTIONS tuple.

    The result is the same as the old `getEntries()` answering None -- no
    entry, and no refusal logged: a plugin that offered nothing was not broken,
    it simply had nothing for the node in question.
    """

    def __init__(self):
        super().__init__()
        BUILT.append('OffersNothingForThisNode')
        self.SCOPE = QVizPluginScope(IDS)
        self.ACTIONS = ()


class NotEnabled(VizPlugin):
    """A plugin with no scope at all: the old `isEnabled` answering False.

    The catalog refuses it by name -- "it names no SCOPE" -- in its
    `_pluginsNow`, and no other plugin costs its menu for it. The difference
    from the old contract is that the refusal is now logged, not silent.
    """

    def __init__(self):
        super().__init__()
        BUILT.append('NotEnabled')


class DeclaresZero:
    """Records the entry it was run with, like `DeclaresSeven`."""

    def _run(self, context):
        RAN.append(('DeclaresZero', context.api, 0))

    def __init__(self):
        BUILT.append('DeclaresZero')
        self.SCOPE = QVizPluginScope(IDS)
        self.ACTIONS = (
            QVizPluginAction(0, 'the first', run=self._run),
            QVizPluginAction(1, 'the second', run=self._run))

    # Only entry 0 is offered: the same rule the old getEntries() enforced.
    def offered(self, context):
        return [one for one in self.ACTIONS if one.key == 0]


class ReadsItsOwnView(VizPlugin):
    """Reaches its case through the context -- `context.view.uri` is where the
    uri is now -- rather than off a bound attribute of itself.
    """

    def _run(self, context):
        RAN.append(('ReadsItsOwnView', context.view.uri, 1))

    def __init__(self):
        super().__init__()
        BUILT.append('ReadsItsOwnView')
        self.SCOPE = QVizPluginScope(IDS)
        self.ACTIONS = (QVizPluginAction(1, 'draw the panel of this case',
                                         run=self._run),)


class RefusesToRun(VizPlugin):
    def _run(self, context):
        raise ValueError('this case holds no equilibrium IDS')

    def __init__(self):
        super().__init__()
        BUILT.append('RefusesToRun')
        self.SCOPE = QVizPluginScope(IDS)
        self.ACTIONS = (QVizPluginAction(1, 'draw the panel', run=self._run,
                                         description='draws a panel this '
                                                     'case cannot fill'),)


class CrashesWhileRunning(VizPlugin):
    def _run(self, context):
        raise KeyError('time_slice')

    def __init__(self):
        super().__init__()
        BUILT.append('CrashesWhileRunning')
        self.SCOPE = QVizPluginScope(IDS)
        self.ACTIONS = (QVizPluginAction(3, 'plot the slices', run=self._run),)


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


def test_an_action_with_no_run_is_refused_and_the_others_keep_their_lines(
        monkeypatch, view):
    # In the new contract the failure is a line whose run is not callable:
    # the catalog names it and leaves out that one line, and the ones with a
    # run keep it -- the old "a number getAllEntries did not describe" has no
    # direct equivalent, because an action is both its number and its words.
    registerStubs(monkeypatch, UndescribedNumber)
    catalog = QVizPluginCatalog(view)
    entries = catalog.entriesFor(FakeTreeNode(idsName='equilibrium'))
    assert [entry.number for entry in entries] == [0, 1]
    assert len(catalog.refusals) == 1
    assert 'UndescribedNumber' in catalog.refusals[0]
    assert 'action 2' in catalog.refusals[0]
    assert 'no run' in catalog.refusals[0]


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
    # In the new contract, "disabled" is "no SCOPE declared": the catalog
    # refuses it in _pluginsNow with a named reason rather than silently
    # skipping it the way the old isEnabled answered False.
    registerStubs(monkeypatch, NotEnabled)
    catalog = QVizPluginCatalog(view)
    assert catalog.entriesFor(FakeTreeNode(idsName='equilibrium')) == []
    assert 'NotEnabled' in catalog.refused
    assert 'SCOPE' in catalog.refused['NotEnabled']


def test_a_plugin_decides_from_the_node_the_menu_was_built_on(monkeypatch,
                                                              view):
    # Each offer carries the node it was offered on: the context the catalog
    # builds for one call does not leak into the next, and a plugin that
    # reads its node from the context reads the one it was offered on, not
    # the most recent one the catalog was asked for.
    registerStubs(monkeypatch, DeclaresSeven)
    catalog = QVizPluginCatalog(view)
    first = FakeTreeNode(idsName='equilibrium')
    second = FakeTreeNode(idsName='core_profiles')
    firstOffer = catalog.entriesFor(first)
    secondOffer = catalog.entriesFor(second)
    assert firstOffer[0].context.node is first
    assert secondOffer[0].context.node is second


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
    assert 'Running plugin DeclaresSeven, action 7.' in caplog.text


class AnswersOnItsOfferNode(VizPlugin):
    """A plugin that reads the IDS it was offered on -- like the registered two do.

    The window a plugin draws names that IDS (the title and the session stamp),
    so it is what the entry was *offered* on, not whatever node the catalog was
    last built for. In the new contract the node lives in the context the action
    was handed, and each offer carries its own; running an older offer reads the
    older node, not the most recent one the catalog was asked for since.
    """

    def _run(self, context):
        RAN.append(('AnswersOnItsOfferNode', context.node.getIDSName()))

    def __init__(self):
        super().__init__()
        self.SCOPE = QVizPluginScope(IDS)
        self.ACTIONS = (QVizPluginAction(1, 'the one the node decides',
                                         run=self._run),)


def test_an_entry_runs_on_the_node_it_was_offered_on(monkeypatch, view):
    """An offer on one root keeps its node until the click, wherever the catalog was asked since.

    Measured on the reference case: an `entriesFor` on a *different* IDS root
    between the offer and the run left the plugin bound to that other root, and
    the window it drew named that IDS in its title and its session stamp. In
    the new contract each offer carries its own context with its own node, and
    running the first offer reads the first node -- not whatever the catalog
    was asked for most recently.
    """
    registerStubs(monkeypatch, AnswersOnItsOfferNode)
    catalog = QVizPluginCatalog(view)
    offeredOn = FakeTreeNode(idsName='equilibrium')
    entry = catalog.entriesFor(offeredOn)[0]
    assert entry.node is offeredOn
    # The menu of another node is built in between: a different offer, still
    # its own, with its own node.
    elsewhere = FakeTreeNode(idsName='core_profiles')
    others = catalog.entriesFor(elsewhere)
    assert len(others) == 1 and others[0].pluginName == entry.pluginName
    assert others[0].context.node is elsewhere
    catalog.run(entry)
    assert RAN == [('AnswersOnItsOfferNode', 'equilibrium')]


# --------------------------------------------------------------------------
# The answers a session gives in the user's place
# --------------------------------------------------------------------------

def test_the_answers_a_session_gave_are_the_answers_the_entry_is_handed(
        monkeypatch, view):
    registerStubs(monkeypatch, TakesAnswers)
    catalog = QVizPluginCatalog(view)
    entry = catalog.entriesFor(FakeTreeNode(idsName='equilibrium'))[0]
    answers = QVizPluginAnswers(occurrence=2, figureKey='PlotView:1')
    catalog.run(entry, answers=answers)

    assert RAN == [('TakesAnswers', 'the-api-of-this-view', 4, answers)]


def test_the_menu_hands_no_answers_at_all(monkeypatch, view):
    """From the menu the user is there to answer, so nothing is answered for them.

    This is the difference the keyword marks: the same entry, asked from a right
    click, still asks its own question, exactly as it did before sessions.
    """
    registerStubs(monkeypatch, TakesAnswers)
    catalog = QVizPluginCatalog(view)
    catalog.run(catalog.entriesFor(FakeTreeNode(idsName='equilibrium'))[0])

    assert RAN == [('TakesAnswers', 'the-api-of-this-view', 4, None)]


def test_an_entry_taking_its_keywords_by_star_is_not_refused(monkeypatch, view):
    """The check asks the signature, and `**keywords` takes the answers too."""
    registerStubs(monkeypatch, TakesAnything)
    catalog = QVizPluginCatalog(view)
    entry = catalog.entriesFor(FakeTreeNode(idsName='equilibrium'))[0]
    answers = QVizPluginAnswers(occurrence=0, figureKey='PlotView:1')
    catalog.run(entry, answers=answers)

    assert RAN == [('TakesAnything', 'the-api-of-this-view', 5, answers)]


def test_a_plugin_is_bound_to_the_view_whose_catalog_built_it(monkeypatch,
                                                              view):
    # In the new contract the view is not set on the plugin, it is in the
    # context the action is handed: a plugin that reads its case through
    # `context.view` reads the one the catalog was built for, not a copy.
    registerStubs(monkeypatch, ReadsItsOwnView)
    catalog = QVizPluginCatalog(view)
    entries = catalog.entriesFor(FakeTreeNode(idsName='equilibrium'))
    assert entries[0].context.view is view


def test_a_plugin_that_reaches_its_case_through_its_view_runs(monkeypatch,
                                                              view):
    # Without the binding this answers [] -- the AttributeError happens inside
    # execute, and the guard in `run` turns it into a log line, so the entry
    # looks broken rather than unbound.
    registerStubs(monkeypatch, ReadsItsOwnView)
    catalog = QVizPluginCatalog(view)
    entry = catalog.entriesFor(FakeTreeNode(idsName='equilibrium'))[0]
    catalog.run(entry)
    assert RAN == [('ReadsItsOwnView', 'stub?case', 1)]


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


def test_a_window_drawn_around_a_widget_this_qt_cannot_build_is_refused_by_name(
        monkeypatch, view, tmp_path):
    # Measured: the file loads, Qt answers "unable to create a custom widget
    # of the class '...'; defaulting to base class 'QWidget'" and drops the
    # connections the .ui makes to it. Overriding createWidget changes
    # nothing: it is never called (PySide6 6.6.3, this node). A .ui with
    # a custom widget class is thus not a plugin the run can show, and is
    # refused by name so the user reads the class and the file, not an
    # empty window.
    ui_dir = str(tmp_path)
    with open(os.path.join(ui_dir, 'custom.ui'), 'w') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<ui version="4.0">\n'
                ' <class>MainWindow</class>\n'
                ' <widget class="QMainWindow" name="MainWindow">\n'
                '  <widget class="QWidget" name="centralwidget">\n'
                '   <widget class="noSuchWidgetClass" name="mainPluginWidget"/>\n'
                '  </widget>\n'
                ' </widget>\n'
                ' <customwidgets>\n'
                '  <customwidget>\n'
                '   <class>noSuchWidgetClass</class>\n'
                '   <extends>QWidget</extends>\n'
                '  </customwidget>\n'
                ' </customwidgets>\n'
                '</ui>\n')
    registerUiPlugins(monkeypatch, {
        'someUiPlugin': {'UiFile': 'custom.ui', 'dir': ui_dir,
                         'targetIDSroot': 'magnetics', 'targetOccurrence': 0}})
    catalog = QVizPluginCatalog(view)
    assert catalog.entriesFor(FakeTreeNode(idsName='magnetics')) == []
    assert 'noSuchWidgetClass' in catalog.refusals[0]
    assert 'custom.ui' in catalog.refusals[0]


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
    from imasviz.VizUtils import QVizPreferences

    QVizPreferences().build()
    source = QVizIMASDataSource('west 54924', case_uri_or_skip())
    source.dd_version = CASE_DATA_DICTIONARY_VERSION
    frame = QVizDataTreeViewFrame(None, [], source, None)
    # The frame, not the view: the view is what owns the menus built on it, and
    # an owner dropped by a helper takes them down in a later test.
    return frame


@pytest.mark.case
@pytest.mark.ui
@pytest.mark.dd
def test_the_reference_case_offers_the_lines_for_equilibrium(qtbot):
    frame = aShotView(qtbot)
    qtbot.addWidget(frame)
    entries = QVizPluginCatalog(frame.dataTreeView).entriesFor(
        frame.dataTreeView.IDSRoots['equilibrium'])
    # equilibriumcharts offers one, equilibriumsurfaces two (surfaces of three
    # instants, or one instant with its profiles), VizProfiles_plugin one and
    # VizSlicePlugin one -- and the numbers they run under are theirs, not their
    # place in the menu. The order is the registration order, each plugin's
    # entries in the numbers it declared. The Profiles plugin used to answer two
    # lines here, each spelling the array of structures and the abscissa in its
    # text; the window asks both with a control now.
    assert [(entry.pluginName, entry.number, entry.label)
            for entry in entries] == [
        ('equilibriumcharts', 0, 'Equilibrium overview...'),
        ('equilibriumsurfaces', 0, 'Surfaces de flux (début, milieu, fin)...'),
        ('equilibriumsurfaces', 1, 'Équilibre à un instant (surface + profils)...'),
        ('VizProfiles_plugin', 0, 'Plot what the equilibrium IDS holds...'),
        ('VizSlicePlugin', 0, 'Draw the slice of the equilibrium IDS…')]


@pytest.mark.case
@pytest.mark.ui
@pytest.mark.dd
def test_the_reference_case_offers_lines_for_core_profiles(qtbot):
    frame = aShotView(qtbot)
    qtbot.addWidget(frame)
    entries = QVizPluginCatalog(frame.dataTreeView).entriesFor(
        frame.dataTreeView.IDSRoots['core_profiles'])
    # An IDS with no list of quantities of its own used to get no line at all: the
    # Profiles plugin knew five IDSs by name. What it can offer is the tree's
    # answer, so any IDS root earns the line -- and the slice entry is offered on
    # every IDS root the same way, so this one earns that line too.
    assert [(entry.pluginName, entry.number) for entry in entries] == \
        [('VizProfiles_plugin', 0), ('VizSlicePlugin', 0)]


@pytest.mark.case
@pytest.mark.ui
@pytest.mark.dd
def test_an_ids_no_plugin_claims_gets_no_plugins_sub_menu(qtbot, monkeypatch):
    # Measured: 42 of the 55 IDS names of this case are claimed by no plugin,
    # and every one of them got a 'Plugins' sub-menu with nothing in it. The
    # Profiles plugin no longer claims five IDSs by name -- every IDS earns its
    # line -- so the refusal is pinned on a stub that still refuses by name.
    registerStubs(monkeypatch, ClaimsEquilibriumOnly)
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
        qtbot, caplog, monkeypatch):
    # This gesture offers the plugins and nothing else, so it used to open an
    # empty menu on 42 IDSs out of 55.
    registerStubs(monkeypatch, ClaimsEquilibriumOnly)
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
        'Surfaces de flux (début, milieu, fin)...',
        'Équilibre à un instant (surface + profils)...',
        'Plot what the equilibrium IDS holds...',
        'Draw the slice of the equilibrium IDS…']


@pytest.mark.case
@pytest.mark.ui
@pytest.mark.dd
def test_a_view_asks_its_plugins_once_across_its_menus(qtbot):
    frame = aShotView(qtbot)
    qtbot.addWidget(frame)
    view = frame.dataTreeView
    first = QVizPluginMenu().catalogOf(view)
    second = QVizPluginMenu().catalogOf(view)
    assert first is second is view.pluginCatalog
    assert sorted(name for name, _ in first.plugins()) == \
        ['VizEventDetection', 'VizProfiles_plugin', 'VizSlicePlugin',
         'VizSpectral', 'equilibriumcharts', 'equilibriumsurfaces']
    equilibrium = view.IDSRoots['equilibrium']
    for _ in range(3):
        menu = QMenu()
        menu.setParent(view)
        # Five lines on equilibrium: equilibriumcharts one, equilibriumsurfaces
        # two, VizProfiles_plugin one, VizSlicePlugin one.
        assert QVizPluginMenu().buildPluginsMenu(equilibrium, view, menu) == 5
