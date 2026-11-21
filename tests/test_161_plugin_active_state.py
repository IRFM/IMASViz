# Copyright holders : Commissariat à l'Energie Atomique et aux Energies
# Alternatives (CEA), France; and Laboratory for Engineering Design - LECAD,
# University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C
# open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted
# upon downloading the software and/or exercising any of the rights granted
# under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The active / inactive state of a plugin the user can switch in the preferences file.

`test_43` pins "disabled" as "no SCOPE at all". This pins the other meaning:
a plugin the user has explicitly switched off in the preferences file, and the
catalog refusing it by name.

Three halves, measured before writing:

* the parser (`QVizPreferences.disabledBricks`): an empty string is no plugin
  disabled (the default), any number of valid names is exactly those, and an
  unknown name is refused by name -- the names IMASViz actually ships being
  spelled out so the user can fix the typo on the spot;
* the catalog: a name in `Disabled_bricks` is refused like any other refusal
  (named in the log of the case, not a silent absence); and the same plugin
  is offered again once the name is taken out of the set;
* the round trip: `persist(Disabled_bricks='name1,name2')` writes the line
  to the preferences file; `build()` reads that line back into a frozenset,
  resetting the in-memory default in the process.

The stub plugin is registered the way `test_43` registers its stubs: under a
synthetic module in `sys.modules`, the production import path (`imasviz.
VizPlugins.viz_stub_active_state.one`) so the catalog's `importlib.import_module`
finds it without a file on disk.
"""

import importlib
import sys
import types

import pytest

from PySide6.QtWidgets import QTreeWidget

from imasviz.VizPlugins.VizPlugin import (
    IDS,
    QVizPluginAction,
    QVizPluginScope,
    VizPlugin,
)
from imasviz.VizPlugins.QVizPluginCatalog import QVizPluginCatalog
from imasviz.VizUtils import QVizPreferences

CATALOG_MOD = importlib.import_module('imasviz.VizPlugins.QVizPluginCatalog')
VIZPLUGIN_MOD = importlib.import_module('imasviz.VizPlugins.VizPlugin')

# The stub registration: name -> dotted path (same shape as RegisteredPlugins).
STUB_NAME = 'StubBrickForActiveState'
STUB_PACKAGE = 'viz_stub_active_state.one'
STUB_IMPORT = 'imasviz.VizPlugins.' + STUB_PACKAGE     # the name _import uses


class StubBrick(VizPlugin):
    """A minimal plugin: one SCOPE, one ACTION with a run; enough for the catalog to see it."""

    def _run(self, context):
        pass

    def __init__(self):
        super().__init__()
        self.SCOPE = QVizPluginScope(IDS)
        self.ACTIONS = (QVizPluginAction(0, 'stub action', run=self._run),)


def _registerStub(monkeypatch):
    """Register the stub the way the production path finds it: a module in sys.modules."""
    module = types.ModuleType(STUB_IMPORT)
    setattr(module, STUB_NAME, StubBrick)
    monkeypatch.setitem(sys.modules, STUB_IMPORT, module)
    monkeypatch.setattr(
        CATALOG_MOD, 'getRegisteredPlugins',
        lambda: {STUB_NAME: STUB_PACKAGE})


def _view(qtbot):
    """A minimal shot view: a real QTreeWidget the catalog can build against."""
    v = QTreeWidget()
    v.uri = 'stub?case'
    v.imas_viz_api = 'the-api'

    class _Occ:
        def occurrencesOf(self, ids):
            return [0]

    v.occurrences = _Occ()
    v.dataSource = types.SimpleNamespace(uri=v.uri)
    v.IDSRoots = {}
    v.pluginCatalog = None
    qtbot.addWidget(v)
    return v


def _saved_pref():
    return QVizPreferences.Disabled_bricks


@pytest.fixture(autouse=True)
def _restore_pref():
    saved = _saved_pref()
    yield
    QVizPreferences.Disabled_bricks = saved


# ------------------------------------------------------------------ the parser

def test_empty_string_is_nothing_disabled(monkeypatch):
    # The default state: no plugin has been switched off, the set is empty.
    monkeypatch.setattr(
        VIZPLUGIN_MOD, 'getRegisteredPlugins',
        lambda: {'a': 'somepath', 'b': 'other'})
    assert QVizPreferences.disabledBricks('') == frozenset()


def test_whitespace_only_is_nothing_disabled(monkeypatch):
    monkeypatch.setattr(
        VIZPLUGIN_MOD, 'getRegisteredPlugins',
        lambda: {'a': 'somepath'})
    assert QVizPreferences.disabledBricks('   ') == frozenset()
    assert QVizPreferences.disabledBricks(',') == frozenset()


def test_valid_names_are_in_the_resulting_set(monkeypatch):
    monkeypatch.setattr(
        VIZPLUGIN_MOD, 'getRegisteredPlugins',
        lambda: {'alpha': 'p.a', 'beta': 'p.b'})
    assert QVizPreferences.disabledBricks('alpha') == frozenset({'alpha'})
    assert QVizPreferences.disabledBricks('alpha,beta') == frozenset({'alpha', 'beta'})
    # Whitespace around names is stripped.
    assert QVizPreferences.disabledBricks(' alpha , beta ') == frozenset({'alpha', 'beta'})


def test_unknown_name_is_refused_by_name(monkeypatch):
    monkeypatch.setattr(
        VIZPLUGIN_MOD, 'getRegisteredPlugins',
        lambda: {'alpha': 'p.a'})
    with pytest.raises(ValueError, match='gamma'):
        QVizPreferences.disabledBricks('gamma')
    # The list of names IMASViz does ship is in the message.
    with pytest.raises(ValueError, match='alpha'):
        QVizPreferences.disabledBricks('gamma')


# ------------------------------------------------------------------- the catalog

def test_a_disabled_plugin_is_refused_by_name(monkeypatch, qtbot):
    _registerStub(monkeypatch)
    view = _view(qtbot)
    QVizPreferences.Disabled_bricks = frozenset({STUB_NAME})
    catalog = QVizPluginCatalog(view)
    import types
    from support.fakes import FakeTreeNode
    entries = catalog.entriesFor(FakeTreeNode(idsName='equilibrium'))
    assert entries == []
    assert STUB_NAME in catalog.refused
    assert 'disabled' in catalog.refused[STUB_NAME]


def test_a_plugin_not_in_disabled_bricks_is_offered(monkeypatch, qtbot):
    _registerStub(monkeypatch)
    view = _view(qtbot)
    QVizPreferences.Disabled_bricks = frozenset()
    catalog = QVizPluginCatalog(view)
    from support.fakes import FakeTreeNode
    entries = catalog.entriesFor(FakeTreeNode(idsName='equilibrium'))
    assert len(entries) == 1
    assert entries[0].pluginName == STUB_NAME


def test_a_disabled_plugin_is_not_in_the_log_of_other_refusals(monkeypatch, qtbot):
    # A refusal for "disabled" must not be confused with a refusal for "no SCOPE".
    _registerStub(monkeypatch)
    view = _view(qtbot)
    QVizPreferences.Disabled_bricks = frozenset({STUB_NAME})
    catalog = QVizPluginCatalog(view)
    from support.fakes import FakeTreeNode
    catalog.entriesFor(FakeTreeNode(idsName='equilibrium'))
    # Exactly one refusal, for exactly our reason.
    assert len(catalog.refusals) == 1
    assert 'disabled' in catalog.refusals[0]
    assert 'SCOPE' not in catalog.refusals[0]


# --------------------------------------------------------------- the round trip

def test_persist_writes_the_line_and_build_reads_it_back(monkeypatch, tmp_path):
    """`persist` + `build` is a round trip: what goes on disk is what comes back in memory.

    The `HOME` is redirected to `tmp_path` so the preferences file does not
    touch the real user's folder.
    """
    monkeypatch.setenv('HOME', str(tmp_path))
    # Register at least one plugin so that the name is accepted by disabledBricks.
    monkeypatch.setattr(
        VIZPLUGIN_MOD, 'getRegisteredPlugins',
        lambda: {'pluginA': 'p.a', 'pluginB': 'p.b'})

    # Save the current state so we can restore it afterwards.
    saved_disabled = QVizPreferences.Disabled_bricks
    saved_initialized = QVizPreferences.userPreferencesInitialized

    try:
        prefs = tmp_path / '.imasviz' / 'preferences'
        assert not prefs.exists()

        # Write: both names go on one line.
        QVizPreferences.persist(Disabled_bricks='pluginA,pluginB')
        assert prefs.exists()
        content = prefs.read_text()
        assert 'Disabled_bricks=pluginA,pluginB' in content

        # Reset in-memory to the default, then ask the reader to read the file.
        QVizPreferences.Disabled_bricks = ''
        QVizPreferences.userPreferencesInitialized = False
        QVizPreferences().build()
        assert QVizPreferences.Disabled_bricks == frozenset({'pluginA', 'pluginB'})

        # A second persist with an empty set writes an empty value; build reads nothing.
        QVizPreferences.persist(Disabled_bricks='')
        assert 'Disabled_bricks=' in prefs.read_text()
        QVizPreferences.Disabled_bricks = frozenset({'pluginA'})
        QVizPreferences.userPreferencesInitialized = False
        QVizPreferences().build()
        assert QVizPreferences.Disabled_bricks == frozenset()
    finally:
        QVizPreferences.Disabled_bricks = saved_disabled
        QVizPreferences.userPreferencesInitialized = saved_initialized
