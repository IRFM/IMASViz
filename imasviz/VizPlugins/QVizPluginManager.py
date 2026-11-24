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

*Active?* is a column of its own beside it, because it answers a different
question: whether the plugin is on at all. The two cannot share a cell, and they
did once -- the check box was added to the header without `refresh` being told,
landed on the column the state word had just been written into, and a plugin the
catalog refused answered a blank cell.
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

from imasviz.VizUtils import QVizPreferences

COLUMNS = ('Plugin', 'Whose', 'Active?', 'State', 'Where it lives')
# The column of each answer, named rather than counted. A cell written by number is
# how this came apart: the active/inactive check box was added to the header without
# `refresh` being told, so it went to column 2 -- the column the state word had just
# been written into -- and a plugin the catalog refused answered an empty cell, which
# reads as "fine". The header order is the authority, and these are its spelling.
WHOSE, ACTIVE, STATE, WHERE = 1, 2, 3, 4
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
        self._refreshing = False
        # A width the user dragged is an answer they gave: the fit below is
        # asked while nobody has given one, and stops being asked after.
        self._handOnWidths = False
        self._fitting = False
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
        header = self.table.horizontalHeader()
        # Every column answers `Interactive`, which is Qt's word for "a hand
        # may drag its edge". A section in `Fixed` or `ResizeToContents` mode
        # cannot be dragged at all, so fitting the widths has to stay a
        # one-shot ask (`fitColumns`) and never become a mode -- and the last
        # column fills the window through `stretchLastSection` rather than by
        # being stretched itself, which would take its edge away from the
        # hand too.
        for column in range(len(COLUMNS)):
            header.setSectionResizeMode(column, QHeaderView.Interactive)
        header.setStretchLastSection(True)
        header.sectionResized.connect(self._onWidthMoved)
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
        self.table.itemChanged.connect(self._onActiveChanged)

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
        self._refreshing = True
        for source in sources:
            row = self.table.rowCount()
            self.table.insertRow(row)
            state = refusals.get(source.name)
            state = ('refused: %s' % state if state is not None
                     else ('ok' if asked else NOT_ASKED))
            for column, text in ((0, source.name),
                                 (WHOSE, MINE if source.origin == USER else SHIPPED),
                                 (STATE, state),
                                 (WHERE, source.fileName or 'no file of its own')):
                self.table.setItem(row, column, QTableWidgetItem(str(text)))
            check = QTableWidgetItem()
            check.setCheckState(Qt.Checked if source.name not in QVizPreferences.Disabled_bricks else Qt.Unchecked)
            check.setFlags(check.flags() | Qt.ItemIsUserCheckable)
            self.table.setItem(row, ACTIVE, check)
        self._sources = {row: source for row, source in enumerate(sources)}
        self._refreshing = False
        self.fitColumns()
        self._enableForRow()
        return len(sources)

    def fitColumns(self):
        """Widths that fit what the rows actually hold.

        Every column used to open at the header's default 100 pixels, which
        is where the refusal sentence went unread: `refused: SyntaxError:
        invalid syntax (MyAnalysisPlugin.py, line 12)` in a 100 pixel column
        reads as `refused: SyntaxE`, and the one column that does hold a long
        path was the only one the hand could not move.

        The fit is an ask, not a mode -- a section in `ResizeToContents` mode
        cannot be dragged -- and it is asked only while nobody has dragged an
        edge: a refresh follows a delete, a reload, a checkbox, and it would
        otherwise take back a width the user chose two seconds ago.
        """
        if self._handOnWidths:
            return
        self._fitting = True
        try:
            self.table.horizontalHeader().resizeSections(
                QHeaderView.ResizeToContents)
        finally:
            self._fitting = False

    def _onWidthMoved(self, column, before, after):
        """A width became the user's own, so no later fit touches it.

        `sectionResized` answers for more than a hand: it fires for the fit
        asked above, and for the last column, whose width moves whenever the
        window does. Only an edge that is dragged counts.
        """
        if self._fitting or column == WHERE:
            return
        self._handOnWidths = True

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

    def _onActiveChanged(self, item):
        """One checkbox moved: persist and put the session back."""
        if getattr(self, '_refreshing', False):
            return
        row = self.table.row(item)
        source = getattr(self, '_sources', {}).get(row)
        if source is None:
            return
        current = set(QVizPreferences.Disabled_bricks)
        if item.checkState() == Qt.Checked:
            current.discard(source.name)
        else:
            current.add(source.name)
        QVizPreferences.persist(Disabled_bricks=','.join(sorted(current)))
        QVizPreferences.Disabled_bricks = frozenset(current)
        self._reload()

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
