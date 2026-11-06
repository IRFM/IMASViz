# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Which plugins a shot view can offer, and what each of them offers.

The framework used to ask this question again on every menu: `QVizPluginsHandler`
called `VizPlugin.getPluginsObjects`, which imported every registered plugin and
built its object anew. Measured on the reference case, in a process that had
opened the shot view and nothing else, the first right click paid **0,999 s** for
that (4,186 s for `getPluginsObjects` alone, cold: it is where matplotlib comes
in), the second 0,0425 s, the third 0,0008 s -- and the launch chain imports no
plugin at all, so the whole cost sits on the gesture. Nothing kept the objects
either, so a plugin built from a **.ui** file would construct a `QMainWindow` and
`sys.path.append` its directory once per click.

What that framework also measured:

* a plugin raising inside `getEntries` took the **whole menu** with it: 0 entries
  left, and the exception escaped the right click;
* the label of an entry was read at its **position** in `getAllEntries()`, so a
  plugin declaring entries `[2]` with two descriptions answered `IndexError`;
* a plugin honouring the documented methods but not inheriting `VizPlugin` was
  **invisible, without a word** -- the gate was an `isinstance`, and the fallback
  was a table naming two plugins that are not registered;
* every entry got the same id, `9999`, under a `# TODO: properly set ID`, and the
  id was then read back and thrown away: the click dispatched on the **position**
  in a list that grew with every menu built on the same handler.

So a catalog belongs to the shot view: the plugins are imported and built once for
it, lazily -- a view nobody right-clicks never pays for them -- and each plugin is
asked on its own, so the one that fails is named and the others are still offered.
An entry carries its own number, which is also what `execute` is asked for,
because the manual documents `getAllEntries` as `[(config number, description)]`
and `execute(vizAPI, pluginEntry)` receives that number.

What a view can offer comes from **two** places now: the table IMASViz ships, and
this user's own plugin folder -- see `QVizPluginSource`, which owns that
difference. A user plugin is found by looking, so one created in the middle of a
session is on the menu of the next right click with nothing else edited. That is
also what makes a *reload* something that has to exist: the cache that stops a
view paying twice for the same plugins is the same cache that would keep an edited
plugin running the code it had when the view was built. `reload()` puts one view
back to what the disk says now; `reloadEverywhere(api)` puts every open shot view
back, which is what the watcher on the application window calls.
"""

import importlib
import inspect
import logging
import re

import shiboken6

from imasviz.VizPlugins.VizPlugin import getRegisteredPlugins
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


class QVizPluginEntry:
    """One line of the Plugins menu: a plugin, the feature it offers, its words.

    `source` says which plugin that is and where it came from, which is what lets
    the menu offer *Edit* for a plugin of the user's own and not for one IMASViz
    shipped. It is optional so that a line built without it stays a line: the
    origin then reads as shipped, which is the safe answer -- nothing offers to
    edit what nobody has.
    """

    def __init__(self, pluginName, plugin, number, label, description=None,
                 source=None, node=None):
        self.pluginName = pluginName
        self.plugin = plugin
        self.number = number
        self.label = label
        self.description = description or pluginName
        self.source = source
        # The node the entry was offered on: a plugin reads its IDS name from
        # the node it was bound to, and the binding travels with the menu -- an
        # entry asked on the equilibrium root and run a moment later must still
        # be answered on that root, so `run` re-binds it here (measured stale:
        # an `entriesFor` on another node between the offer and the click left
        # the window naming that other node).
        self.node = node

    def __repr__(self):
        return '<%s entry %s "%s">' % (self.pluginName, self.number, self.label)

    @property
    def origin(self):
        return self.source.origin if self.source is not None else BUILTIN


class QVizPluginCatalog:
    """The plugins of one shot view -- shipped and the user's own -- asked one at
    a time.

    Built once per view, on the first menu that needs it. A plugin that cannot be
    imported, built, or asked what it offers is named in the log of that case and
    left out; the others keep their entries.
    """

    def __init__(self, dataTreeView):
        self.dataTreeView = dataTreeView
        self._plugins = None
        self._sourceOf = {}
        self.refusals = []
        # The same refusals, keyed by plugin name. `refusals` is what the log
        # panel shows, one line per event, in the order they happened; this is
        # what the plugin manager reads to say why a row of its table has no
        # entry -- and reading it back out of the sentences would mean depending
        # on how `_refuse` happens to be worded.
        self.refused = {}

    def _log(self):
        return logging.getLogger(self.dataTreeView.uri)

    def _refuse(self, pluginName, why):
        """Leave a plugin out of the menu, and say so where the user reads."""
        message = 'Plugin %s is not offered: %s' % (pluginName, why)
        self.refusals.append(message)
        self.refused[pluginName] = why
        self._log().error(message)

    def _sources(self):
        """What the view may offer: the shipped table, then this user's folder.

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
        """Put this view's plugins back to what the disk says now.

        Every module under the package the user's folder is imported under is
        dropped, the folder's own package with it -- not just the plugins this
        view happens to have built. `sys.modules` is one table for the process, so
        forgetting only what *this* view imported would leave a plugin another view
        built still on its old code, and a plugin the user deleted altogether
        would never be forgotten at all: it is no longer on the folder to be
        found. What is dropped is therefore the whole subtree of the user's
        folder, however it got there.

        A shipped plugin is never re-imported in the middle of a session: the
        windows already on screen belong to the copy that drew them, and a second
        copy of its classes -- with matplotlib bound to both -- is how a session
        ends up with two figures that refuse each other. What the user just
        changed is their own file, and that is the one that comes back.

        Nothing here opens a window or touches a menu. The sub-menu is rebuilt on
        every right click, so the next one shows what the disk holds; and a view
        whose catalog was never built has nothing to put back, since it will build
        it fresh from the same folder.
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
        """Import and build every plugin this view may offer, once, each on its own."""
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
            # A plugin reaches its case through `self.dataTreeView`, which the
            # contract says is set when the menu is built. The catalog bound the
            # node only, so a plugin reading its view answered AttributeError on
            # the first line of execute() -- measured with the Profiles plugin,
            # the one registered plugin that reads it -- and the guard in `run`
            # hid that behind a line saying "Plugin ... failed".
            bindView = getattr(plugin, 'setDataTreeView', None)
            if callable(bindView):
                bindView(self.dataTreeView)
            self._plugins.append((pluginName, plugin))
        return self._plugins

    def plugins(self):
        return self._pluginsNow()

    def sourceOf(self, pluginName):
        """Where that plugin came from, once the view has been asked once."""
        self._pluginsNow()
        return self._sourceOf.get(pluginName)

    def entriesFor(self, node):
        """The lines this node earns, in registration order.

        Each plugin is asked separately and bound to `node` first: the manual
        says a plugin decides from the node it was offered on, and the framework
        used to hand it the view's selection instead of the node under the mouse.
        """
        entries = []
        for pluginName, plugin in self._pluginsNow():
            if isinstance(plugin, dict):
                continue
            try:
                entries.extend(self._entriesOf(pluginName, plugin, node))
            except Exception as error:
                self._refuse(pluginName, 'it failed while answering what it '
                                         'offers (%s: %s)'
                             % (type(error).__name__, error))
        return entries

    def _entriesOf(self, pluginName, plugin, node):
        from PySide6.QtWidgets import QMainWindow

        source = self._sourceOf.get(pluginName)
        if isinstance(plugin, QMainWindow):
            # A .ui window has no methods to ask: it claims one fixed IDS, and
            # its one entry is the window itself.
            if plugin.targetIDSroot != node.getIDSName():
                return []
            return [QVizPluginEntry(pluginName, plugin, 0,
                                   'Show the %s panel' % pluginName,
                                   source=source, node=node)]

        bind = getattr(plugin, 'setSelectedTreeNode', None)
        if callable(bind):
            bind(node)
        if not plugin.isEnabled():
            return []

        numbers = plugin.getEntries()
        if not numbers:
            return []

        descriptions = plugin.getAllEntries()
        if descriptions is None:
            raise ValueError('getAllEntries() answered nothing, so entry %r has '
                             'no text to show' % (numbers,))
        labels = {}
        for described in descriptions:
            labels[described[0]] = described[1]

        description = getattr(plugin, 'getDescription', None)
        tip = description() if callable(description) else pluginName

        entries = []
        for number in numbers:
            if number not in labels:
                # Measured: reading the position instead of the number answered
                # IndexError and took the menu with it.
                self._refuse(pluginName, 'it asks for entry %r, which its '
                                         'getAllEntries() does not describe (it '
                                         'describes %s)'
                             % (number, sorted(labels)))
                continue
            entries.append(QVizPluginEntry(pluginName, plugin, number,
                                          labels[number], tip, source=source,
                                          node=node))
        return entries

    def run(self, entry, answers=None):
        """Hand one entry to the plugin it names.

        Returns nothing; a plugin that refuses says so in the log with its name.
        The framework used to catch everything with a bare `except:` and print a
        traceback on stdout, so the user of the GUI saw the entry do nothing.

        `answers` is what a session already gave the entry in the user's place
        (a `QVizPluginAnswers`); from the menu it is None, and the entry asks its
        own question as it always did. An entry that cannot take the answers is
        refused here rather than run without them: run without them, it would ask
        its question again, and the Profiles plugin asks it through a modal
        `QInputDialog` -- measured, a probe waiting on that dialog sat for 240 s.
        """
        from PySide6.QtWidgets import QMainWindow

        if isinstance(entry.plugin, QMainWindow):
            self._showUiWindow(entry)
            return
        execute = getattr(entry.plugin, 'execute', None)
        if not callable(execute):
            self._refuse(entry.pluginName, 'it has no execute() to run')
            return
        if answers is not None and not _acceptsAnswers(execute):
            self._log().error(
                'The %s entry of plugin %s is not replayed: its execute() takes '
                'no answers, so it would ask its question again -- a session has '
                'no one to answer it.' % (entry.number, entry.pluginName))
            return
        self._log().info('Running plugin %s, entry %s.'
                         % (entry.pluginName, entry.number))
        # The entry is answered on the node it was offered on, whatever the
        # plugin is bound to now: the binding is set by the last `entriesFor`,
        # which need not be the offer this entry came out of. A node the tree
        # took away in between is no node, and the plugin answers for itself.
        node = getattr(entry, 'node', None)
        bind = getattr(entry.plugin, 'setSelectedTreeNode', None)
        if callable(bind) and node is not None and shiboken6.isValid(node):
            bind(node)
        try:
            if answers is None:
                execute(self.dataTreeView.imas_viz_api, entry.number)
            else:
                execute(self.dataTreeView.imas_viz_api, entry.number,
                        answers=answers)
        except ValueError as error:
            self._log().error('Plugin %s could not run: %s'
                              % (entry.pluginName, error))
        except Exception as error:
            self._log().error('Plugin %s failed: %s: %s'
                              % (entry.pluginName, type(error).__name__, error))

    def _showUiWindow(self, entry):
        """Open the window of a .ui plugin, with the IDS it was drawn around.

        The window used to ask for that IDS through `dataSource.load` with the
        occurrence the registration names, which after T12 is the whole question
        an IDS load has to answer; going through the same command as every other
        load keeps the guard on the view and the label of the view.
        """
        from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
            import QVizLoadOccurrence

        window = entry.plugin
        self._log().info('Showing the panel of plugin %s.' % entry.pluginName)
        QVizLoadOccurrence(dataTreeView=self.dataTreeView,
                           idsName=window.targetIDSroot,
                           occurrence=window.targetOccurrence).execute()
        window.show()


def reloadEverywhere(api):
    """Put the plugins of every open shot view back to what the disk says now.

    One edited file has to reach every view, and a view that has never built its
    catalog needs nothing: it has nothing cached, so it reads the folder the next
    time a menu asks. The modules of the user's plugins are dropped even then --
    something else may have imported one (the plugin manager does, to tell the
    user what it holds) -- and the answer is how many views were put back, because
    a reload nobody can count is a reload nobody believes.
    """
    forgetUserModules()
    views = getattr(api, 'DTVlist', None) or []
    reloaded = 0
    for view in views:
        catalog = getattr(view, 'pluginCatalog', None)
        if catalog is None:
            continue
        catalog.reload()
        reloaded += 1
    return reloaded


def refusalsOf(api):
    """What the opened views refused, by plugin name.

    Read off the catalogs that already exist, so asking it costs nothing: a plugin
    is refused while a menu is being built, and the reason stays in the catalog of
    that view. A view nobody has right-clicked has no catalog, so an empty answer
    here is not the same as "nothing is wrong" -- the plugin manager says which of
    the two it is rather than leaving the column blank.
    """
    refusals = {}
    for view in getattr(api, 'DTVlist', None) or []:
        catalog = getattr(view, 'pluginCatalog', None)
        if catalog is not None:
            refusals.update(catalog.refused)
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
    the start window's menu controller, the open gesture's api. `Viz_API` is not a
    singleton, so an api built here would be a second bookkeeping holding none of
    the windows on screen.
    """
    window = widget
    while window is not None and getattr(window, 'sessionApi', None) is None:
        window = window.parent()
    return window.sessionApi() if window is not None else None


def _acceptsAnswers(execute):
    """Whether this `execute` can take an `answers=` keyword.

    Asked of the signature, not tried and caught: running an entry that cannot
    take the answers would not fail, it would open its own question -- and the
    Profiles plugin asks its one through a modal `QInputDialog` parented to the
    shot view, which is where a probe once sat for 240 s with no one to answer.
    A plugin written against the older two-argument contract is therefore named
    and left alone, and the session keeps the rest of the screen.
    """
    try:
        parameters = inspect.signature(execute).parameters
    except (TypeError, ValueError):
        # A callable this Python cannot describe: assume the older contract,
        # which is the safe answer -- the entry is refused rather than run blind.
        return False
    parameter = parameters.get('answers')
    return (parameter is not None
            or any(p.kind is inspect.Parameter.VAR_KEYWORD
                   for p in parameters.values()))


def _readFile(path):
    try:
        with open(path) as handle:
            return handle.read()
    except OSError:
        return None
