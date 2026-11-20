# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The Plugins menu, at the place one plugin is offered from.

A plugin says, in its ``SCOPE``, which place it is offered at -- an IDS root, a
quantity, the case, or the application -- and the framework that draws that place
assembles the catalog for it and hangs the lines the plugins of that place offer.

The gesture is one of three, and each draws the lines the plugins of that place
offer:

* on a node -- right click on an IDS root or a quantity, or Shift+right click,
  into a fresh pop-up the caller builds; an empty set leaves no sub-menu at all;
* on the case -- its own bar's *Plugins* line, kept filled on ``aboutToShow``
  (the same way the application's *File* and *Windows* menus keep themselves);
* on the application -- its own bar's *Plugins* line, kept the same way.

The lines are read off the catalog's offers for the place -- a plugin, the
action it offers, and the words it gives. A plugin of the user's own earns a
second line, *Edit <plugin>*, next to its own: the file that answers this menu is
the one under the cursor, which is where the question "how do I change what it
just did?" arrives. Only for their own: a plugin IMASViz ships is read-only, and
``QVizPluginSource.writeSource`` refuses it the same way, so the line and the
guard cannot disagree.
"""

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu

from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizMenuRefill import refill
from imasviz.VizPlugins.QVizPluginCatalog import QVizPluginCatalog, openEditor
from imasviz.VizPlugins.QVizPluginSource import USER
from imasviz.VizUtils import GlobalIcons


class QVizPluginMenu:
    """Hang the lines the plugins of a place offer, onto that place's menu."""

    EDIT = 'Edit %s...'

    # -- the node gesture: a fresh pop-up the caller builds ----------------

    def buildPluginsMenu(self, node, dataTreeView, parentMenu):
        """Fill a *fresh* menu with what this node earns, and answer how many.

        The caller adds the sub-menu before asking, so the count is what lets it
        take the empty one back out again -- the behaviour measured for every
        place no plugin claims. A node is an IDS root or a quantity, and a plugin
        is offered at the one it declared: an ``equilibrium`` root earns what
        names that IDS, and a quantity under it earns what handles it.
        """
        catalog = self.catalogOf(dataTreeView)
        return self._hang(catalog.entriesFor(node), parentMenu, catalog,
                          dataTreeView)

    def addPluginsMenu(self, node, dataTreeView, parentMenu, title='Plugins'):
        """Add a "Plugins" sub-menu, but only when a plugin has something to say.

        The sub-menu is given its parent at construction, not through
        ``parentMenu.addMenu(title)``: measured, the QMenu that call returns is
        owned by the Python wrapper it comes back in, and the three gestures drop
        that wrapper as soon as this method returns -- reading the sub-menu back
        from its action then answered ``RuntimeError: Internal C++ object
        (PySide6.QtWidgets.QMenu) already deleted``. A menu born with its parent
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

    # -- the case's own bar, kept filled while it is on screen --------------

    def refillCasePluginMenu(self, dataTreeView, menu):
        """Take the case's *Plugins* menu back and refill it with its ``CASE`` lines.

        Called on ``aboutToShow`` so what the case offers does not go stale: a
        plugin the user just edited must not wait for a restart to show on the
        bar, the way the application's *File* and *Windows* menus keep themselves.
        """
        refill(menu)
        catalog = self.catalogOf(dataTreeView)
        return self._hang(catalog.caseEntries(), menu, catalog, dataTreeView)

    # -- the application's own bar, kept filled while it is on screen -------

    def refillAppPluginMenu(self, api, menu, window=None):
        """Take the application's *Plugins* menu back and refill its ``APP`` lines.

        The catalog is built for the application, not a case, and kept on the api
        so the whole run shares one of them and a reload reaches it.
        """
        refill(menu)
        catalog = self.appCatalogOf(api)
        return self._hang(catalog.appEntries(), menu, catalog, window)

    # -- the common shape: draw the offers, one plugin at a time ------------

    def _hang(self, offers, menu, catalog, parentWidget):
        """Add one line per offer, plus the *Edit* of a user's own plugin."""
        if not offers:
            return 0
        already = set()
        for entry in offers:
            action = QAction(GlobalIcons.getCustomQIcon(QApplication, 'new'),
                             entry.label, parentWidget)
            action.setStatusTip(entry.description)
            action.setToolTip(entry.description)
            action.triggered.connect(lambda checked=False, line=entry, cat=catalog:
                                     cat.run(line))
            menu.setToolTipsVisible(True)
            menu.addAction(action)
            if self.editable(entry) and entry.pluginName not in already:
                # Once per plugin, right under the lines that plugin drew: a
                # plugin with several entries would otherwise offer its file
                # several times over, and a menu is not where the user should
                # have to wonder which of the copies is the real one.
                already.add(entry.pluginName)
                menu.addAction(self.editAction(entry, parentWidget))
        return len(offers)

    @staticmethod
    def editable(entry):
        """Whether this entry's file is this user's to change.

        Asked of the origin, not of a path on disk: a shipped plugin is read-only
        whatever folder it lives in, and ``QVizPluginSource.writeSource`` refuses
        it the same way, so the line and the guard cannot disagree.
        """
        source = getattr(entry, 'source', None)
        return source is not None and source.origin == USER and source.writable

    def editAction(self, entry, parentWidget):
        """The *Edit* line for one of the user's own plugins.

        No icon: ``GlobalIcons`` has no picture for "edit", and asking it for one
        answers None, which draws a gap where a glyph should be. The entry lines
        above carry one because their icon says "this adds a window"; this line
        says what it is in words, and the words are the whole answer.
        """
        action = QAction(self.EDIT % entry.pluginName, parentWidget)
        action.setStatusTip('Change %s -- the Plugins menu of every opened case '
                            'answers with what you save.' % entry.pluginName)
        action.setToolTip(action.statusTip())
        action.triggered.connect(lambda checked=False, line=entry:
                                 openEditor(line.source, parent=parentWidget))
        return action

    # -- the catalogs the places draw from ---------------------------------

    @staticmethod
    def catalogOf(dataTreeView):
        """The case's catalog: the plugins are built once for it, not per click.

        Built here rather than in the view's constructor so that a shot view
        nobody asks never pays for importing them -- measured at 0,999 s for the
        first menu of a session, most of it matplotlib.
        """
        catalog = getattr(dataTreeView, 'pluginCatalog', None)
        if catalog is None:
            catalog = QVizPluginCatalog(dataTreeView)
            dataTreeView.pluginCatalog = catalog
        return catalog

    @staticmethod
    def appCatalogOf(api):
        """The application's catalog: built once for a run, and kept on the api.

        Kept on the api -- the session's own object -- so a second *Plugins* menu
        in the same run does not import the plugins twice, and ``reloadEverywhere``
        can reach it whether or not a case is on screen.
        """
        catalog = getattr(api, 'appPluginCatalog', None)
        if catalog is None:
            catalog = QVizPluginCatalog(api=api)
            api.appPluginCatalog = catalog
        return catalog

    def run(self, dataTreeView, entry):
        """One line, run on the case it was offered on (the node gesture's path)."""
        self.catalogOf(dataTreeView).run(entry)
