# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Every plugin this session can offer, in one table: whose it is, and what it did.

This is where the read-only boundary is *seen*. The Plugins sub-menu of a node
answers a different question -- what can be done to this quantity -- and says
nothing about where a plugin came from. Here the two origins are side by side, a
plugin IMASViz ships is marked as such and opens read-only, and a plugin of this
user's own opens ready to edit, with the copy gesture next to it: reading a shipped
plugin is only useful if what you usually want, changing one, starts from it.

There is no *which IDS does it answer* column, and that is not an oversight. The
only way to answer that is to ask the plugin, and asking it means importing it --
which is exactly the cost the catalog goes lazy to avoid (measured: the shipped
set is where matplotlib comes in, and it used to be paid on the first right click
of a session). What a plugin answers is on the tree: the line appears on the nodes
it claims and not on the others.

The *State* column is read off the catalogs that already exist, so it costs
nothing either. It says one of three things, and the third is said out loud: a
view nobody has right-clicked has not asked its plugins anything yet, and a blank
must not be read as "fine".
"""

import shutil
import weakref

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QHBoxLayout,
                               QHeaderView, QLabel, QPushButton, QTableWidgetItem,
                               QTableWidget, QVBoxLayout)

from imasviz.VizPlugins.QVizPluginCatalog import (openEditor, refusalsOf,
                                                  reloadEverywhere)
from imasviz.VizPlugins.QVizPluginSource import (USER, builtinSources,
                                                 copyIntoUserFolder,
                                                 userPluginsFolder,
                                                 userSources)

COLUMNS = ('Plugin', 'Whose', 'State', 'Where it lives')
SHIPPED = 'IMASViz'
MINE = 'yours'
NOT_ASKED = 'not asked yet'


class QVizPluginManager(QDialog):
    """The plugins of this session, and what may be done to each."""

    def __init__(self, parent=None, apiOf=None, watcher=None):
        """
        Arguments:
            parent (QWidget) : the window this box belongs to.

            apiOf (callable) : answers the api of the session, for the refusals
                the opened views already recorded and for a reload when there is
                no watcher to ask.

            watcher (QVizPluginWatcher) : held weakly, and asked for one thing --
                to put the running session back to what the folder holds.
        """
        super().__init__(parent)
        self._apiOf = apiOf
        self._watcher = weakref.ref(watcher) if watcher is not None else None
        self._sources = {}
        self.setWindowTitle('Plugins')
        self.resize(980, 460)
        self._buildUI()
        self.refresh()

    def _buildUI(self):
        layout = QVBoxLayout(self)

        self.folderLabel = QLabel('Your own plugins live in <code>%s</code>. '
                                  'What is in there is offered as soon as it is '
                                  'there: nothing is registered and IMASViz does '
                                  'not restart.' % userPluginsFolder())
        self.folderLabel.setTextFormat(Qt.RichText)
        self.folderLabel.setWordWrap(True)
        layout.addWidget(self.folderLabel)

        self.table = QTableWidget(0, len(COLUMNS), self)
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.Stretch)
        self.table.itemDoubleClicked.connect(lambda item: self._open())
        layout.addWidget(self.table, 1)

        self.stateLabel = QLabel('')
        self.stateLabel.setWordWrap(True)
        layout.addWidget(self.stateLabel)

        buttons = QHBoxLayout()
        self.newButton = QPushButton('New plugin...')
        self.newButton.clicked.connect(self._new)
        self.openButton = QPushButton('Read...')
        self.openButton.clicked.connect(self._open)
        self.copyButton = QPushButton('Copy into my plugins...')
        self.copyButton.clicked.connect(self._copy)
        self.reloadButton = QPushButton('Reload now')
        self.reloadButton.clicked.connect(self._reload)
        self.deleteButton = QPushButton('Delete')
        self.deleteButton.clicked.connect(self._delete)
        self.closeButton = QPushButton('Close')
        self.closeButton.clicked.connect(self.close)
        for button in (self.newButton, self.openButton, self.copyButton,
                       self.reloadButton, self.deleteButton):
            buttons.addWidget(button)
        buttons.addStretch()
        buttons.addWidget(self.closeButton)
        layout.addLayout(buttons)

        self.table.currentItemChanged.connect(lambda *args: self._enableForRow())

    def sources(self):
        """The shipped plugins first, then this user's own, each by name."""
        return (sorted(builtinSources(), key=lambda one: one.name)
                + sorted(userSources(), key=lambda one: one.name))

    def refresh(self):
        """Rebuild the table from the two folders, and from what the views said."""
        sources = self.sources()
        asked = any(getattr(view, 'pluginCatalog', None) is not None
                    for view in self._views())
        refusals = refusalsOf(self._api())
        self.table.setRowCount(0)
        for source in sources:
            row = self.table.rowCount()
            self.table.insertRow(row)
            state = refusals.get(source.name)
            state = ('refused: %s' % state if state is not None
                     else ('ok' if asked else NOT_ASKED))
            for column, text in enumerate((source.name,
                                           MINE if source.origin == USER
                                           else SHIPPED,
                                           state,
                                           source.fileName or 'no file of its '
                                                              'own')):
                self.table.setItem(row, column, QTableWidgetItem(str(text)))
        self._sources = {row: source for row, source in enumerate(sources)}
        self._enableForRow()
        return len(sources)

    def selected(self):
        row = self.table.currentRow()
        return getattr(self, '_sources', {}).get(row)

    def _enableForRow(self):
        source = self.selected()
        mine = source is not None and source.origin == USER
        self.openButton.setText('Edit...' if mine else 'Read...')
        self.copyButton.setEnabled(source is not None and not mine
                                   and not source.isUi)
        self.deleteButton.setEnabled(mine)

    def _open(self):
        source = self.selected()
        if source is None:
            self.stateLabel.setText('Pick a plugin first.')
            return None
        return openEditor(source, parent=self)

    def _new(self):
        from imasviz.VizPlugins.QVizPluginCreatorDialog \
            import QVizPluginCreatorDialog

        dialog = QVizPluginCreatorDialog(self)
        dialog.exec()
        watcher = self._watcher() if self._watcher is not None else None
        if watcher is not None:
            # The folder may not have existed a moment ago, so it is only watched
            # from now on.
            watcher.watch()
        self.refresh()
        if dialog.created is not None:
            self.stateLabel.setText('<b>%s</b> is written. Right-click a node of '
                                    'the %s IDS to run it.'
                                    % (dialog.created.name,
                                       dialog.created.registration))
            openEditor(dialog.created, parent=self)

    def _copy(self):
        source = self.selected()
        if source is None or source.origin == USER:
            return None
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self, 'Copy %s into your own plugins' % source.name,
            'Name for the copy:')
        if not ok:
            return None
        try:
            copy, touched = copyIntoUserFolder(source, name)
        except ValueError as refusal:
            self.stateLabel.setText('<b>Not copied:</b> %s' % refusal)
            return None
        self.refresh()
        self.stateLabel.setText(
            '<b>%s</b> is a copy of <b>%s</b> in <code>%s</code>%s. It is yours '
            'to change; the one it came from is not touched.'
            % (copy.name, source.name, copy.folder,
               (' (renamed in %d file(s))' % len(touched)) if touched else ''))
        return openEditor(copy, parent=self)

    def _delete(self):
        source = self.selected()
        if source is None or not source.writable:
            self.stateLabel.setText('Only a plugin of your own can be deleted '
                                    'from here.')
            return False
        from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations

        if not QVizGlobalOperations.YesNo(
                parent=self,
                question='Delete %s?\n%s will be taken away from the disk.'
                         % (source.name, source.folder),
                caption='Please confirm'):
            return False
        try:
            shutil.rmtree(source.folder)
        except OSError as error:
            self.stateLabel.setText('<b>Not deleted:</b> %s could not be '
                                    'removed: %s' % (source.folder, error))
            return False
        watcher = self._watcher() if self._watcher is not None else None
        if watcher is not None:
            watcher.reload()
        else:
            # No watcher to ask -- and a plugin taken off the disk has to come off
            # the menu of a case that is already open all the same. The folder is
            # what the scan looks at, so a *fresh* catalog already says nothing;
            # the views that built their plugins before are the ones left holding
            # a line that answers nothing.
            reloadEverywhere(self._api())
        self.refresh()
        self.stateLabel.setText('%s is deleted. Its lines are off the Plugins '
                                'menu of every opened case.' % source.name)
        return True

    def _reload(self):
        """Put the session back to what the folder holds, without waiting."""
        watcher = self._watcher() if self._watcher is not None else None
        views = watcher.reload() if watcher is not None \
            else reloadEverywhere(self._api())
        self.refresh()
        self.stateLabel.setText('Reloaded for %d opened case view(s).' % views)
        return views

    def _api(self):
        return self._apiOf() if callable(self._apiOf) else self._apiOf

    def _views(self):
        api = self._api()
        return list(getattr(api, 'DTVlist', None) or []) if api else []
