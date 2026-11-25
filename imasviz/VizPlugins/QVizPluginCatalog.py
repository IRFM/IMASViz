# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Which plugins a place may offer, and what each of them offers there.

A place is one of the four scopes a plugin can name: a node of the tree
(``IDS`` for the root, ``NODE`` for a quantity), the case itself (``CASE``), or
the application (``APP``). The catalog a place asks is built **once** for it --
a place nobody asks never pays for importing its plugins -- and the plugins are
imported and built **once per catalog**, each on its own, so the one that
cannot be imported is named in the log and the others keep their lines.

What a place may offer comes from **two** places: the table IMASViz ships
(``RegisteredPlugins``), and this user's own plugin folder -- see
``QVizPluginSource``, which owns that difference. A user plugin is found by
looking, so one created in the middle of a session is on the next place's menu
with nothing else edited. That is also what makes a *reload* something that has
to exist: the cache that stops a view paying twice for the same plugins is the
same cache that would keep an edited plugin running the code it had when the
place was built. ``reload()`` puts one catalog back to what the disk says now;
``reloadEverywhere(api)`` puts every open place back.

The offer a place gets is read off the plugin's declared ``SCOPE`` and
``ACTIONS`` -- the declarative contract of ``VizPlugin`` -- and each is run by
calling the action with a ``QVizPluginContext`` that already carries the api,
the case, the node, the occurrence and the answers a session gave. A plugin does
not test a node to decide where it applies; the framework reads its scope.
"""

import importlib
import logging
import re

import shiboken6

# The base class of `_NoDialogGuard` is asked at import time, so only this name
# comes in here; the rest of Qt this module needs stays inside the methods that
# ask it, as it has always been.
from PySide6.QtCore import QObject

from imasviz.VizPlugins.VizPlugin import (APP, CASE, FIGURE, IDS, NODE,
                                          QVizPluginAction, QVizPluginContext,
                                          getRegisteredPlugins)
from imasviz.VizPlugins.QVizPluginSource import (BUILTIN, USER,
                                                 attachUserPackage,
                                                 builtinSource,
                                                 forgetUserModules,
                                                 userPluginsFolder,
                                                 userSources)

# A .ui plugin whose interface is only Qt classes is built as written. One that
# embeds a widget class of its own cannot: measured with the loader this PySide6
# provides (PySide6 6.6.2 -- `from PySide6 import uic`, which the framework used,
# raises ImportError here), QUiLoader answers
# "QFormBuilder was unable to create a custom widget of the class 'exampleWidget';
# defaulting to base class 'QWidget'" and drops every connection that .ui file
# makes to that class -- 10 for examplePlugin.ui, the only one left in the
# repository since the SOLPS plugin was removed (its window dropped 3, and came
# out with no child of the class it declares). Overriding createWidget changes
# nothing: it is never called. The window that comes out is hollow, so it is not
# shown; the plugin is refused and says which class is missing.
_CUSTOM_WIDGET = re.compile(r'<customwidget>.*?<class>(\w+)</class>', re.S)


class _NoDialogGuard(QObject):
    """Close a dialog a plugin asks while something else already answered.

    An entry that asks its question through a `QDialog` is right from a menu and
    fatal from a tool call or a session replay: the dialog runs a **nested event
    loop on the GUI thread**, so nothing else is served until someone presses a
    button -- and on the web surface nobody is there. Measured on the reference
    case, before the entry was changed to answer for itself, the `equilibrium`
    surfaces entry opened `QInputDialog 'Equilibrium at an instant'` and the caller
    answered `The GUI thread did not answer in 300 s`; the model asked again, and
    again, which is what reached the user as an endless loop, with
    `QPainter::end: Painter ended with 2 saved states` printed by that loop
    painting through itself.

    The guard is the general net under the one entry that was fixed: whatever a
    plugin asks -- a shipped plugin, a plugin of the user's own -- is refused
    rather than left to hold the thread. What is asked is the application's event
    filter, because a plugin builds its own dialog and hands it nowhere the
    framework could reach.

    The same call printed `QPainter::end: Painter ended with 2 saved states` for
    the user; that warning has not been reproduced on its own, and nothing here
    sets out to answer it -- what is answered is the block.

    Two Qt facts decide the shape, both measured on this PySide6 6.6.3:

    * a modal dialog announces itself as a `QEvent.Show` that reaches the
      application filter before its loop is entered, and `isModal()` is already
      true there -- so the dialog is recognised by Qt's own word, not by a list
      of dialog classes a plugin would have to be told to use;
    * `done()` called **inside** that event leaves the loop running: `exec()`
      starts pumping after the event is delivered. Refusing therefore goes
      through a zero `QTimer`, which fires once the loop has started and takes
      the dialog down from the inside -- measured: `exec()` answers 0,
      `QInputDialog.getInt` answers `(default, False)` and a
      `QMessageBox.warning` returns, all without a button.

    `stop()` runs in a `finally` at the call site: a filter left installed by a
    plugin that raised would refuse every dialog of the session, which is a worse
    failure than the one this prevents.
    """

    def __init__(self):
        super().__init__()
        self.asked = []
        self._app = None

    def start(self):
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            return
        self._app = app
        app.installEventFilter(self)

    def stop(self):
        if self._app is not None:
            self._app.removeEventFilter(self)
            self._app = None

    def eventFilter(self, watched, event):
        from PySide6.QtCore import QEvent, QTimer
        from PySide6.QtWidgets import QWidget
        if event.type() == QEvent.Show and isinstance(watched, QWidget) \
                and watched.isModal():
            named = (type(watched).__name__,
                     watched.windowTitle() or type(watched).__name__)
            if named not in self.asked:
                self.asked.append(named)
            QTimer.singleShot(0, lambda dialog=watched: self._takeDown(dialog))
        return False

    def _takeDown(self, dialog):
        from PySide6.QtWidgets import QDialog
        if isinstance(dialog, QDialog):
            dialog.done(0)
        else:
            dialog.close()

    def question(self):
        """What was asked, spelled the way the refusal has to say it."""
        return ', '.join(title for _kind, title in self.asked)


class QVizPluginEntry:
    """One line of a Plugins menu: a plugin, and the action it offers there.

    `number` is the action's key -- the stable identifier the plugin gave it,
    which is also what the session and the agent key it by. `source` says which
    plugin that is and where it came from, which is what lets the menu offer
    *Edit* for a plugin of the user's own and not for one IMASViz shipped. It is
    optional so that a line built without it stays a line: the origin then reads
    as shipped, which is the safe answer -- nothing offers to edit what nobody
    has. `node`, when the line was offered on a node, is that node, and `action`
    / `context` are what `run` hands over to do the work.
    """

    def __init__(self, pluginName, plugin, number, label, description=None,
                 source=None, node=None, action=None, context=None):
        self.pluginName = pluginName
        self.plugin = plugin
        self.number = number
        self.label = label
        self.description = description or pluginName
        self.source = source
        self.node = node
        self.action = action
        self.context = context

    def __repr__(self):
        return '<%s entry %s "%s">' % (self.pluginName, self.number, self.label)

    @property
    def origin(self):
        return self.source.origin if self.source is not None else BUILTIN


class QVizPluginCatalog:
    """The plugins one place may offer, and what each of them offers there.

    Built once per place, on the first menu that needs it. A plugin that cannot
    be imported, built, or offered is named in the log of that place and left
    out; the others keep their lines. A catalog bound to a case answers for an
    ``IDS``, ``NODE`` or ``CASE`` place; one bound to the application (no case)
    answers for an ``APP`` place.
    """

    def __init__(self, dataTreeView=None, api=None):
        if dataTreeView is None and api is None:
            raise ValueError('a plugin catalog needs a case or the '
                             'application to answer for')
        self.dataTreeView = dataTreeView
        self._api = api
        self._plugins = None
        self._sourceOf = {}
        self.refusals = []
        # The same refusals, keyed by plugin name. `refusals` is what the log
        # panel shows, one line per event, in the order they happened; this is
        # what the plugin manager reads to say why a row of its table has no
        # entry -- and reading it back out of the sentences would mean depending
        # on how `_refuse` happens to be worded.
        self.refused = {}

    def _apiObject(self):
        """The api this catalog answers with: the case's, or the one it was given."""
        if self.dataTreeView is not None:
            return self.dataTreeView.imas_viz_api
        return self._api

    def _log(self):
        """The log of the place this catalog answers for."""
        if self.dataTreeView is not None:
            return logging.getLogger(self.dataTreeView.uri)
        return logging.getLogger('logPanel')

    def _refuse(self, pluginName, why):
        """Leave a plugin out of the menu, and say so where the user reads."""
        message = 'Plugin %s is not offered: %s' % (pluginName, why)
        self.refusals.append(message)
        self.refused[pluginName] = why
        self._log().error(message)

    def _sources(self):
        """What this place may offer: the shipped table, then this user's folder.

        The shipped table is asked through the name imported *here*, because that
        is the seam the menu tests replace to hand over a stub plugin; a helper
        called somewhere else would hide it. What comes off the user's folder is
        appended, never merged in place: the order the table holds is the order of
        the menu, and a plugin that arrived later goes last.
        """
        sources = [builtinSource(name, registration)
                   for name, registration in getRegisteredPlugins().items()]
        shipped = {source.name for source in sources}
        for source in userSources(userPluginsFolder()):
            if source.name in shipped:
                # Two plugins of one name is a question the menu cannot answer,
                # and silently letting the user's file replace the shipped one is
                # the worse of the two ways to answer it.
                self._refuse(source.name, 'your plugin folder holds a plugin '
                                          'named %s, which IMASViz already '
                                          'ships -- give yours another name, the '
                                          'shipped one is not replaced'
                             % source.name)
                continue
            sources.append(source)
        return sources

    def _import(self, source):
        """Take the module of one plugin, from wherever it was found to live.

        A shipped plugin keeps the import path it always had. A plugin of the
        user's is imported under the package `QVizPluginSource` puts over their
        folder, which is what keeps its name stable across a reload and lets it
        hold a sub-package of its own.
        """
        if source.origin == USER:
            attachUserPackage(userPluginsFolder())
        return importlib.import_module(source.importName)

    def reload(self):
        """Put this catalog's plugins back to what the disk says now.

        Every module under the package the user's folder is imported under is
        dropped, the folder's own package with it -- not just the plugins this
        catalog happens to have built. `sys.modules` is one table for the process,
        so forgetting only what *this* place imported would leave a plugin another
        place built still on its old code, and a plugin the user deleted
        altogether would never be forgotten at all: it is no longer on the folder
        to be found. What is dropped is therefore the whole subtree of the user's
        folder, however it got there.

        A shipped plugin is never re-imported in the middle of a session: the
        windows already on screen belong to the copy that drew them, and a second
        copy of its classes -- with matplotlib bound to both -- is how a session
        ends up with two figures that refuse each other. What the user just
        changed is their own file, and that is the one that comes back.

        Nothing here opens a window or touches a menu. The menus are rebuilt on
        each gesture, so the next shows what the disk holds; and a place whose
        catalog was never built has nothing to put back, since it will build it
        fresh from the same folder.
        """
        forgetUserModules()
        self._plugins = None
        self._sourceOf = {}
        self.refusals = []
        self.refused = {}

    def _loadUiPlugin(self, pluginName, configuration):
        """Build the window a .ui plugin describes, or refuse it with its reason.

        The configuration is the dictionary the howto shows inside
        **RegisteredPlugins** -- `UiFile`, `dir`, `targetIDSroot`, `targetOccurrence`.
        """
        from PySide6.QtWidgets import QMainWindow, QWidget
        from PySide6.QtUiTools import QUiLoader

        uiFile = configuration.get('UiFile')
        directory = configuration.get('dir')
        if not uiFile or not directory:
            self._refuse(pluginName, 'a plugin built from a .ui file needs '
                                     '"UiFile" and "dir" in its registration')
            return None
        path = directory.rstrip('/') + '/' + uiFile

        declared = _CUSTOM_WIDGET.search(_readFile(path) or '')
        window = QMainWindow(parent=self.dataTreeView)
        try:
            QUiLoader().load(path, window)
        except Exception as error:
            window.deleteLater()
            self._refuse(pluginName, '%s could not be loaded: %s: %s'
                         % (uiFile, type(error).__name__, error))
            return None

        # The window is only worth showing if the class the .ui file was drawn
        # around is really in it.
        if declared is not None:
            main = window.findChild(QWidget, 'mainPluginWidget')
            if main is not None and type(main).__name__ == 'QWidget':
                window.deleteLater()
                self._refuse(pluginName,
                             '%s is drawn around %r, which this Qt cannot build '
                             'from a .ui file: it falls back to a bare QWidget, '
                             'and the connections the interface makes to it are '
                             'dropped. Provide the widget as a Python class, or '
                             'draw the interface with Qt classes only.'
                             % (uiFile, declared.group(1)))
                return None

        window.targetIDSroot = configuration.get('targetIDSroot')
        window.targetOccurrence = configuration.get('targetOccurrence', 0)
        return window

    def _pluginsNow(self):
        """Import and build every plugin this place may offer, once, each on its own."""
        if self._plugins is not None:
            return self._plugins
        self._plugins = []
        for source in self._sources():
            pluginName = source.name
            self._sourceOf[pluginName] = source
            if source.isUi:
                window = self._loadUiPlugin(pluginName, source.registration)
                if window is not None:
                    self._plugins.append((pluginName, window))
                continue
            try:
                module = self._import(source)
                importedClass = getattr(module, pluginName)
                plugin = importedClass()
            except Exception as error:
                # A stale entry in the registration table used to take the whole
                # menu down: ModuleNotFoundError escaped the loop that built it.
                # The same guard is what names a plugin of the user's that no
                # longer parses -- it costs its own line, not the menu.
                self._refuse(pluginName, '%s: %s' % (type(error).__name__, error))
                del self._sourceOf[pluginName]
                continue
            # A plugin that declares no scope is not offered anywhere: it was
            # never a question of which node to gate on -- it simply says nothing
            # about where it sits -- so it is named, not handed a silence.
            if getattr(plugin, 'SCOPE', None) is None:
                self._refuse(pluginName, 'it names no SCOPE (IDS, NODE, CASE or '
                                         'APP), so it is not offered anywhere')
                del self._sourceOf[pluginName]
                continue
            # A user can switch a plugin off in the preferences: it is refused
            # with the same voice as the others -- named in the log, not silent.
            from imasviz.VizUtils import QVizPreferences
            if pluginName in QVizPreferences.Disabled_bricks:
                self._refuse(pluginName, 'disabled by the user in the '
                                         'preferences')
                del self._sourceOf[pluginName]
                continue
            self._plugins.append((pluginName, plugin))
        return self._plugins

    def plugins(self):
        return self._pluginsNow()

    def sourceOf(self, pluginName):
        """Where that plugin came from, once this place has been asked once."""
        self._pluginsNow()
        return self._sourceOf.get(pluginName)

    def _contextFor(self, kind, node=None):
        """The context one line of this place runs in, with nothing yet answered.

        The occurrence is the first the case holds for the IDS -- the same
        default a menu-click used to take -- and a session replay overrides it
        through `answers` at run time.
        """
        api = self._apiObject()
        view = self.dataTreeView
        if kind == APP:
            return QVizPluginContext(api=api, view=None, node=None, scope=APP)
        occurrence = 0
        if view is not None and node is not None:
            idsName = node.getIDSName()
            if idsName is not None:
                occurrences = view.occurrences.occurrencesOf(idsName)
                occurrence = occurrences[0] if occurrences else 0
        return QVizPluginContext(api=api, view=view, node=node, scope=kind,
                                 occurrence=occurrence)

    def _offers(self, kind, node=None):
        """The lines the plugins of this place offer, for this one.

        Each plugin is asked on its own, bound to the place it is offered at: a
        plugin that fails to say what it offers is named and left out, and the
        others keep their lines. A line is an action declared by the plugin; the
        plugin's ``offered`` may offer a subset of them for this place, or refuse.
        """
        from PySide6.QtWidgets import QMainWindow

        offers = []
        for pluginName, plugin in self._pluginsNow():
            source = self._sourceOf.get(pluginName)
            if isinstance(plugin, QMainWindow):
                # A .ui window has no methods to ask: it names one fixed IDS, and
                # its one line is the window itself, offered on that root.
                if kind != IDS or node is None or not node.isIDSRoot() \
                        or plugin.targetIDSroot != node.getIDSName():
                    continue
                action = QVizPluginAction(0, 'Show the %s panel' % pluginName)
                offers.append(QVizPluginEntry(pluginName, plugin, action.key,
                                              action.label, source=source,
                                              node=node, action=action))
                continue

            scope = getattr(plugin, 'SCOPE', None)
            if scope is None:
                continue
            if kind in (IDS, NODE):
                if scope.kind != kind:
                    continue
                if not scope.appliesToNode(node):
                    continue
            elif kind == CASE:
                if not scope.appliesToCase():
                    continue
            elif kind == APP:
                if not scope.appliesToApp():
                    continue
            else:
                continue

            try:
                context = self._contextFor(kind, node)
                actions = plugin.offered(context)
            except Exception as error:
                self._refuse(pluginName, 'it refused this place (%s: %s)'
                             % (type(error).__name__, error))
                continue
            for action in (actions or []):
                if not callable(getattr(action, 'run', None)):
                    self._refuse(pluginName, 'its action %s has no run to call'
                                 % (getattr(action, 'key', action),))
                    continue
                # A label (or a tooltip) may be said once, or of the place it is
                # offered from: the `equilibrium` root earns "the equilibrium IDS"
                # while `magnetics` earns its own under the line, the way the old
                # per-node `getAllEntries()` answered it.
                offers.append(QVizPluginEntry(
                    pluginName, plugin, action.key,
                    _word(action.label, context),
                    _word(action.description, context),
                    source=source, node=node, action=action,
                    context=context))
        return offers

    def entriesFor(self, node):
        """The lines a node earns: what an IDS root earns, and what a quantity does.

        A node is one or the other -- an IDS root (``isIDSRoot``) or a quantity
        under it -- and a plugin is offered at the one it declared, so an
        ``equilibrium`` root earns the plugins that name that IDS and a quantity
        under it the ones that handle it.
        """
        return self._offers(IDS, node) + self._offers(NODE, node)

    def entriesNamed(self, pluginName, nodes):
        """Every line of one plugin among these IDS roots, as ``[(root, entry)]``.

        Asked of the catalog rather than of one node, because a caller that names
        no IDS root does not know which one the plugin claims:
        ``equilibriumsurfaces`` is offered on the ``equilibrium`` branch and on no
        other, so picking a root by hand is how a call ends up asking a plugin
        where it was never offered -- and being refused for it. What this answers
        is where the line *is*: one answer for a plugin that claims one branch,
        several for one that claims any IDS. Several is a question for the caller,
        not a guess for the tool -- the occurrence and the window drawn differ per
        root.
        """
        found = []
        for node in nodes:
            for entry in self.entriesFor(node):
                if entry.pluginName == pluginName:
                    found.append((node.getIDSName(), entry))
        return found

    def caseEntries(self):
        """The lines the case's own menu bar earns -- its ``CASE`` plugins."""
        return self._offers(CASE)

    def appEntries(self):
        """The lines the application menu bar earns -- its ``APP`` plugins."""
        return self._offers(APP)

    def run(self, offer, answers=None):
        """Hand one line to the action it names, with the context it ran in.

        A plugin that refuses says so in the log with its name, and the reason
        comes **back** as the return value -- ``None`` when the action ran. The
        log is where a user at a menu reads it; a tool call has no log panel in
        front of it, and an agent told nothing but ``ran`` would answer that a
        window was drawn when the plugin refused and drew nothing.

        `answers` is what a session already gave in the user's place (a
        `QVizPluginAnswers`); from a menu it is None, and the action asks its own
        question as it always did. The context the action reads is the one this
        line was offered in, with the occurrence a session named taking the place
        of the one the case first holds.

        When answers are handed, an entry that opens a dialog instead of reading
        them is refused: `_NoDialogGuard` takes the dialog down and the reason
        comes back, because a nested modal loop on the GUI thread is how a tool
        call loses three hundred seconds and answers nothing.
        """
        from PySide6.QtWidgets import QMainWindow

        if isinstance(offer.plugin, QMainWindow):
            self._showUiWindow(offer)
            return None
        action = offer.action
        if action is None or not callable(action.run):
            self._refuse(offer.pluginName, 'the line named here has no run to call')
            return ('the %s entry of plugin %s has no run to call'
                    % (action.key if action is not None else '?',
                       offer.pluginName))

        context = QVizPluginContext(
            api=self._apiObject(),
            view=self.dataTreeView,
            node=offer.node,
            scope=(offer.context.scope if offer.context is not None else IDS),
            occurrence=(offer.context.occurrence
                        if offer.context is not None else 0),
            answers=answers)
        if answers is not None:
            # The occurrence a session named is the one drawn -- not the one the
            # case first holds -- so a file naming occurrence 1 of `equilibrium`
            # opens on 1 rather than being quietly answered on 0.
            context.occurrence = answers.occurrence

        self._log().info('Running plugin %s, action %s.'
                         % (offer.pluginName, action.key))
        # Only a call that answers in the user's place pays for the guard: from a
        # menu the dialog *is* the question, asked of someone who is there to
        # answer it.
        guard = _NoDialogGuard() if answers is not None else None
        if guard is not None:
            guard.start()
        try:
            action.run(context)
        except ValueError as error:
            # The plugin's own words, named: this is the refusal the caller has to
            # hear, and re-wording it here is how a session ends up reporting a
            # window it never drew.
            self._log().error('Plugin %s could not run: %s'
                              % (offer.pluginName, error))
            return str(error)
        except Exception as error:
            self._log().error('Plugin %s failed: %s: %s'
                              % (offer.pluginName, type(error).__name__, error))
            return ('plugin %s failed: %s: %s'
                    % (offer.pluginName, type(error).__name__, error))
        finally:
            # Whatever the action did, the filter goes back off: one left on the
            # application after a refusal would take down every dialog of the
            # session, including the ones the user asks for themselves.
            if guard is not None:
                guard.stop()
        if guard is not None and guard.asked:
            # The action answered nothing and asked something instead. It went on
            # as if the user had pressed Cancel, so it may well have drawn
            # nothing; saying only "ran" is how the caller reports a window that
            # is not on the screen.
            reason = ('plugin %s asked a question nobody is there to answer: it '
                      'opened %s as a dialog, while this call already carries '
                      'what a session answers (the occurrence, the figure key, '
                      'the instant). The dialog was closed at once instead of '
                      'left to hold the GUI thread: pass the value the entry '
                      'names, or ask the entry from the menu.'
                      % (offer.pluginName, guard.question()))
            self._log().error('Plugin %s could not run: %s'
                              % (offer.pluginName, reason))
            return reason
        return None

    def _showUiWindow(self, offer):
        """Open the window of a .ui plugin, with the IDS it was drawn around.

        The window used to ask for that IDS through `dataSource.load` with the
        occurrence the registration names, going through the same command as every
        other load keeps the guard on the view and the label of the view.
        """
        from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
            import QVizLoadOccurrence

        window = offer.plugin
        self._log().info('Showing the panel of plugin %s.' % offer.pluginName)
        QVizLoadOccurrence(dataTreeView=self.dataTreeView,
                           idsName=window.targetIDSroot,
                           occurrence=window.targetOccurrence).execute()
        window.show()


def reloadEverywhere(api):
    """Put the plugins of every open place back to what the disk says now.

    One edited file has to reach every place, and a place that has never built
    its catalog needs nothing: it has nothing cached, so it reads the folder the
    next time a menu asks. The modules of the user's plugins are dropped even
    then -- something else may have imported one (the plugin manager does, to tell
    the user what it holds) -- and the answer is how many places were put back,
    because a reload nobody can count is a reload nobody believes. The
    application's own catalog, when one has been built yet, is put back too.
    """
    forgetUserModules()
    places = []
    for view in getattr(api, 'DTVlist', None) or []:
        catalog = getattr(view, 'pluginCatalog', None)
        if catalog is not None:
            places.append(catalog)
    appCatalog = getattr(api, 'appPluginCatalog', None)
    if appCatalog is not None:
        places.append(appCatalog)
    for catalog in places:
        catalog.reload()
    return len(places)


def refusalsOf(api):
    """What the opened places refused, by plugin name.

    Read off the catalogs that already exist, so asking it costs nothing: a plugin
    is refused while a menu is being built, and the reason stays in the catalog of
    that place. A place nobody has asked has no catalog, so an empty answer here
    is not the same as "nothing is wrong" -- the plugin manager says which of the
    two it is rather than leaving the column blank.
    """
    refusals = {}
    for view in getattr(api, 'DTVlist', None) or []:
        catalog = getattr(view, 'pluginCatalog', None)
        if catalog is not None:
            refusals.update(catalog.refused)
    appCatalog = getattr(api, 'appPluginCatalog', None)
    if appCatalog is not None:
        refusals.update(appCatalog.refused)
    return refusals


def openEditor(source, parent=None):
    """Show the source of one plugin, and tell it where to announce a save.

    One entry point for every gesture that opens the editor -- the plugin manager
    and the *Edit* line of the Plugins sub-menu -- so the reload cannot be wired
    by one and forgotten by the other. It is a **signal connection**, not a
    callback handed over and stored: a plain helper kept on a widget that answers
    with a bound method of that widget makes a cycle, and a widget freed by the
    cyclic collector is freed on this Qt while it still owes a paint event.
    """
    from imasviz.VizPlugins.QVizPluginEditor import QVizPluginEditor

    editor = QVizPluginEditor(source, parent)
    editor.saved.connect(lambda path: reloadEverywhere(_apiOf(parent)))
    editor.show()
    return editor


def _apiOf(widget):
    """The api of the session a widget belongs to, or None.

    Walked the way the *File* menu walks it -- the window that owns the widget,
    the start window's menu controller, the open gesture's api. `Viz_API` is not
    a singleton, so an api built here would be a second bookkeeping holding none
    of the windows on screen.
    """
    window = widget
    while window is not None and getattr(window, 'sessionApi', None) is None:
        window = window.parent()
    return window.sessionApi() if window is not None else None


def _readFile(path):
    try:
        with open(path) as handle:
            return handle.read()
    except OSError:
        return None


def _word(word, context):
    """The words of an action's label/tooltip, resolved for the place they are shown.

    A word is either said already (a plain string) or said of the place it is
    offered from -- a ``callable(context)`` that spells it with the node under the
    cursor. The second is how "the ``equilibrium`` IDS" / "the ``magnetics`` IDS"
    lands on the same line, each under its own root.
    """
    if callable(word):
        return word(context)
    return word


def figureMenuFor(frame, menu):
    """Build the sub-menus of FIGURE-scoped plugins on ``menu``, answer how many.

    One sub-menu per FIGURE-scoped plugin (titled by its ``LABEL`` or its
    registered name), one line per offered action. A plugin named in
    ``QVizPreferences.Disabled_bricks`` is not built. A plugin that refuses the
    figure through ``offered`` is not built either. A ``run`` that is not
    callable is dropped from the sub-menu -- the other lines stay.

    Each action's ``run`` receives a ``QVizPluginContext`` with
    ``figure=frame``, so it reaches the frame's domain objects
    (``eventMarks``, ``spectrumMenu``) through the context rather than
    through ``self``.

    This function does not need a ``QVizPluginCatalog`` instance: the frame
    is the place, and there is no per-view cache to maintain. A new frame
    built later in the session re-imports the plugins from ``sys.modules``
    at essentially zero cost.

    T25 holds here: the lambda connects on the frame's view-box menu, so it
    is as long-lived as the frame. Closing over a ``QVizPluginContext`` with
    ``figure=frame`` would make a strong cycle (frame → menu → qaction →
    lambda → context → frame), which is how ``test_58`` measured a frame
    surviving its last ``del``. The lambda instead holds a ``weakref.ref``
    to the frame; the context is built at click time, fresh, on a frame
    that is still alive (the user just clicked its menu).
    """
    import importlib
    import weakref
    from PySide6.QtWidgets import QMenu
    from PySide6.QtGui import QAction
    from imasviz.VizUtils import QVizPreferences

    frame_ref = weakref.ref(frame)
    added = 0
    for name, path in getRegisteredPlugins().items():
        # Only the string path shape is a Python plugin; .ui plugins and
        # dictionary shapes are not FIGURE-scope candidates.
        if not isinstance(path, str):
            continue
        if name in QVizPreferences.Disabled_bricks:
            continue
        try:
            module = importlib.import_module('imasviz.VizPlugins.' + path)
            plugin = getattr(module, name)()
        except Exception:
            # A plugin that cannot be imported or built is not offered on
            # this menu; the frame's log does not exist in this context, so
            # the silence is the answer (a place with a log would name it).
            continue
        scope = getattr(plugin, 'SCOPE', None)
        if scope is None or scope.kind != FIGURE:
            continue
        # Ask what the plugin offers -- a short-lived context for the
        # `offered` call only (not stored in the lambda).
        dummy_ctx = QVizPluginContext(api=getattr(frame, 'imas_viz_api', None),
                                     view=None, node=None, scope=FIGURE,
                                     figure=frame)
        try:
            actions = plugin.offered(dummy_ctx)
        except Exception:
            continue
        if not actions:
            continue
        label = getattr(plugin, 'LABEL', None) or name
        submenu = QMenu(label, menu)
        for action in actions:
            if not callable(getattr(action, 'run', None)):
                continue
            qaction = QAction(action.label, submenu)
            # The lambda closes over `frame_ref` (a weakref) and `a` (the
            # action), NOT over a context holding a strong reference to the
            # frame. At click time `_runFigureAction` builds a fresh context
            # on a frame that is still alive.
            qaction.triggered.connect(
                lambda checked=False, a=action, fr=frame_ref:
                _runFigureAction(a, fr))
            submenu.addAction(qaction)
        menu.addMenu(submenu)
        added += 1
    return added


def _runFigureAction(action, frame_ref):
    """Build a fresh context from the live frame (if still alive) and run the action.

    The ``frame_ref`` is a ``weakref.ref`` held by the lambda; dereferencing
    it gives the frame when it is still alive (the user just clicked its menu),
    or ``None`` when the frame was already freed (a click that arrives too
    late -- safe to ignore). The context handed to ``action.run`` holds a
    strong reference to the frame for the duration of the call, which is
    correct: the frame is alive at that instant, and the reference is dropped
    when the action returns.
    """
    frame = frame_ref()
    if frame is None:
        return
    context = QVizPluginContext(api=getattr(frame, 'imas_viz_api', None),
                                view=None, node=None, scope=FIGURE,
                                figure=frame)
    action.run(context)
