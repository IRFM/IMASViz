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
"""

import importlib
import logging
import re

from imasviz.VizPlugins.VizPlugin import getRegisteredPlugins

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
    """One line of the Plugins menu: a plugin, the feature it offers, its words."""

    def __init__(self, pluginName, plugin, number, label, description=None):
        self.pluginName = pluginName
        self.plugin = plugin
        self.number = number
        self.label = label
        self.description = description or pluginName

    def __repr__(self):
        return '<%s entry %s "%s">' % (self.pluginName, self.number, self.label)


class QVizPluginCatalog:
    """The registered plugins of one shot view, asked one at a time.

    Built once per view, on the first menu that needs it. A plugin that cannot be
    imported, built, or asked what it offers is named in the log of that case and
    left out; the others keep their entries.
    """

    def __init__(self, dataTreeView):
        self.dataTreeView = dataTreeView
        self._plugins = None
        self.refusals = []

    def _log(self):
        return logging.getLogger(self.dataTreeView.uri)

    def _refuse(self, pluginName, why):
        """Leave a plugin out of the menu, and say so where the user reads."""
        message = 'Plugin %s is not offered: %s' % (pluginName, why)
        self.refusals.append(message)
        self._log().error(message)

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
        """Import and build every registered plugin once, each on its own."""
        if self._plugins is not None:
            return self._plugins
        self._plugins = []
        for pluginName, registration in getRegisteredPlugins().items():
            if isinstance(registration, dict):
                window = self._loadUiPlugin(pluginName, registration)
                if window is not None:
                    self._plugins.append((pluginName, window))
                continue
            try:
                module = importlib.import_module('imasviz.VizPlugins.'
                                                 + registration)
                importedClass = getattr(module, pluginName)
                plugin = importedClass()
            except Exception as error:
                # A stale entry in the registration table used to take the whole
                # menu down: ModuleNotFoundError escaped the loop that built it.
                self._refuse(pluginName, '%s: %s' % (type(error).__name__, error))
                continue
            self._plugins.append((pluginName, plugin))
        return self._plugins

    def plugins(self):
        return self._pluginsNow()

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

        if isinstance(plugin, QMainWindow):
            # A .ui window has no methods to ask: it claims one fixed IDS, and
            # its one entry is the window itself.
            if plugin.targetIDSroot != node.getIDSName():
                return []
            return [QVizPluginEntry(pluginName, plugin, 0,
                                   'Show the %s panel' % pluginName)]

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
                                          labels[number], tip))
        return entries

    def run(self, entry):
        """Hand one entry to the plugin it names.

        Returns nothing; a plugin that refuses says so in the log with its name.
        The framework used to catch everything with a bare `except:` and print a
        traceback on stdout, so the user of the GUI saw the entry do nothing.
        """
        from PySide6.QtWidgets import QMainWindow

        if isinstance(entry.plugin, QMainWindow):
            self._showUiWindow(entry)
            return
        execute = getattr(entry.plugin, 'execute', None)
        if not callable(execute):
            self._refuse(entry.pluginName, 'it has no execute() to run')
            return
        self._log().info('Running plugin %s, entry %s.'
                         % (entry.pluginName, entry.number))
        try:
            execute(self.dataTreeView.imas_viz_api, entry.number)
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


def _readFile(path):
    try:
        with open(path) as handle:
            return handle.read()
    except OSError:
        return None
