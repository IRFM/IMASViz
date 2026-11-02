# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The Plugins sub-menu of the shot view.

Three gestures open it -- the right click on an IDS root, the right click on a
quantity, and Shift+right click anywhere -- and all three asked the same question
of a framework that answered it again from scratch each time. What that cost, on
the reference case: **0,999 s** for the first right click of a session, 0,0425 s
for the second, 0,0008 s after that; a **sub-menu shown with nothing in it** for
the 42 IDS names of the 55 no plugin claims; and **6 lines instead of 3** when
the same handler was asked twice for the same menu, because the entries it had
already added lived in a list that only grew.

Two of its answers were silent failures rather than messages: a plugin that does
not inherit the base class -- while implementing every documented method -- got
**no line at all**, and a plugin raising while answering took the whole sub-menu
with it. And every line carried the same id, 9999, under a
`# TODO: properly set ID`, which was then read back and ignored: the click found
the plugin by the **position** of its line in a list.

Here the lines are built from the view's catalog, one plugin at a time; a line
carries its plugin and the entry number the plugin declared for it; and the
caller is told how many lines there are, so a menu that would be empty is not
added at all.

A plugin of the user's own gets a second line, *Edit <plugin>...* -- the file
that answers this menu is under the cursor, which is where the question "how do I
change what it just did?" arrives. Only for their own: a plugin IMASViz ships is
read through the Plugins window, where the copy gesture sits next to it, and
offering to edit it here would be a line that can only answer "no".
"""

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu

from imasviz.VizPlugins.QVizPluginCatalog import QVizPluginCatalog, openEditor
from imasviz.VizPlugins.QVizPluginSource import USER
from imasviz.VizUtils import GlobalIcons


class QVizPluginMenu:
    """Add the lines the plugins of this view offer for this node."""

    EDIT = 'Edit %s...'

    def buildPluginsMenu(self, node, dataTreeView, parentMenu):
        """Fill `parentMenu`, and answer how many lines were added.

        The caller adds the sub-menu before asking, so the count is what lets it
        take the empty one back out again -- the behaviour measured for every IDS
        no plugin claims. The count stays the number of **entries**: a plugin that
        offers three features is three lines and one *Edit*, and the caller only
        needs to know whether anything at all can be done here.
        """
        entries = self.catalogOf(dataTreeView).entriesFor(node)
        already = set()
        for entry in entries:
            action = QAction(GlobalIcons.getCustomQIcon(QApplication, 'new'),
                             entry.label, dataTreeView)
            action.setStatusTip(entry.description)
            action.setToolTip(entry.description)
            action.triggered.connect(lambda checked=False, line=entry:
                                     self.run(dataTreeView, line))
            parentMenu.setToolTipsVisible(True)
            parentMenu.addAction(action)
            if self.editable(entry) and entry.pluginName not in already:
                # Once per plugin, right under the lines that plugin drew: a
                # plugin with several entries would otherwise offer its file
                # several times over, and a menu is not where the user should
                # have to wonder which of the copies is the real one.
                already.add(entry.pluginName)
                parentMenu.addAction(self.editAction(entry, dataTreeView))
        return len(entries)

    @staticmethod
    def editable(entry):
        """Whether this entry's file is this user's to change.

        Asked of the origin, not of a path on disk: a shipped plugin is read-only
        whatever folder it lives in, and `QVizPluginSource.writeSource` refuses it
        the same way, so the line and the guard cannot disagree.
        """
        source = getattr(entry, 'source', None)
        return source is not None and source.origin == USER and source.writable

    def editAction(self, entry, dataTreeView):
        """The *Edit* line for one of the user's own plugins.

        No icon: `GlobalIcons` has no picture for "edit", and asking it for one
        answers None, which draws a gap where a glyph should be. The entry lines
        above carry one because their icon says "this adds a window"; this line
        says what it is in words, and the words are the whole answer.
        """
        action = QAction(self.EDIT % entry.pluginName, dataTreeView)
        action.setStatusTip('Change %s -- the Plugins menu of every opened case '
                            'answers with what you save.' % entry.pluginName)
        action.setToolTip(action.statusTip())
        action.triggered.connect(lambda checked=False, line=entry:
                                 openEditor(line.source,
                                            parent=dataTreeView))
        return action

    def addPluginsMenu(self, node, dataTreeView, parentMenu, title='Plugins'):
        """Add a "Plugins" sub-menu, but only when a plugin has something to say.

        The sub-menu is given its parent at construction, not through
        `parentMenu.addMenu(title)`: measured, the QMenu that call returns is
        owned by the Python wrapper it comes back in, and the three gestures drop
        that wrapper as soon as this method returns -- reading the sub-menu back
        from its action then answered `RuntimeError: Internal C++ object
        (PySide6.QtWidgets.QMenu) already deleted`. A menu born with its parent
        belongs to Qt from the start, which is how the rest of this package
        builds a sub-menu.
        """
        subMenu = QMenu(title, parentMenu)
        parentMenu.addMenu(subMenu)
        if self.buildPluginsMenu(node, dataTreeView, subMenu) == 0:
            parentMenu.removeAction(subMenu.menuAction())
            subMenu.deleteLater()
            return None
        return subMenu

    @staticmethod
    def catalogOf(dataTreeView):
        """The view's catalog: the plugins are built once for a view, not per click.

        Built here rather than in the view's constructor so that a shot view
        nobody right-clicks never pays for importing them -- measured at 0,999 s
        for the first menu of a session, most of it matplotlib.
        """
        catalog = getattr(dataTreeView, 'pluginCatalog', None)
        if catalog is None:
            catalog = QVizPluginCatalog(dataTreeView)
            dataTreeView.pluginCatalog = catalog
        return catalog

    def run(self, dataTreeView, entry):
        self.catalogOf(dataTreeView).run(entry)
