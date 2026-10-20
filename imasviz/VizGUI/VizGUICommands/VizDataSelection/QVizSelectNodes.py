# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The one place a node enters or leaves a shot view's selection.

The selection a plot command draws is ``dataTreeView.selectedSignalsDict``: every
frame built since T3 reads that dictionary. Until now it was not the only record
of the selection -- each tree item also carried ``infoDict['isSelected']`` -- and
the commands wrote both, in whichever order they felt like, and coloured the tree
from the flag. Measured, the two records disagree and the tree then lies to the
user: a node still coloured red that no plot will draw, a node coloured blue while
it is in the selection, and an "Unselect" entry that raises ``KeyError`` instead
of clearing a flag the dictionary already forgot.

So the dictionary decides, and the colour follows it. The node the user asked
about is the node drawn: the old commands coloured ``dataTreeView.selectedItem``
-- whatever the tree happened to have as its current item -- and stored that item
in the entry under the asked node's key, so selecting quantity *a* while the tree
was pointed at quantity *b* recorded **b** twice and never a.

The family the manual calls "all nodes from the same AOS" is read off the
parametrized path, which spells the structures with their index names
(``core.time_slice[i].vector``) rather than their indices. The old entry stripped
every bracketed run from the display path instead, which merged two nested
structures differing only by which element they sit in, and took the same leaf
from every occurrence of the IDS as well.
"""

from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand


class QVizSelectNodes(QVizAbstractCommand):
    """Select or unselect nodes, with the view's dictionary as the only record."""

    def __init__(self, dataTreeView, treeNode=None, all_DTV=False):
        """
        Arguments:
            treeNode (QVizTreeNode) : the node the menu was built on.
            all_DTV  (bool)         : whether an "all databases" entry means what
                                      it says: every opened shot view.
        """
        self.all_DTV = all_DTV
        QVizAbstractCommand.__init__(self, dataTreeView, treeNode)

    def execute(self):
        """The one-by-one gesture of the manual: select, or unselect, this node.

        Returns whether the node is selected afterwards -- which is what the menu
        label has to agree with, and what used to be read out of the node's own
        dictionary instead.
        """
        if self.treeNode is None:
            raise ValueError('Nothing to select: no node was asked for.')
        return self.toggle(self.treeNode)

    # -- one node ---------------------------------------------------------

    def toggle(self, treeNode, view=None):
        view = view or self.viewOf(treeNode)
        if self.isSelected(treeNode, view):
            self.unselectNode(treeNode, view)
            return False
        self.selectNode(treeNode, view)
        return True

    def selectNode(self, treeNode, view=None):
        """Add this node to the view's selection. True if it was not in it."""
        view = view or self.viewOf(treeNode)
        key = self.keyFor(view, treeNode)
        if key in view.selectedSignalsDict:
            # Already selected: keep the order it was recorded in and make sure
            # the label says so. The old entry re-added it and overwrote its
            # place in the selection -- measured, asking the AOS entry twice left
            # every node recorded with the same index.
            self.style(treeNode, view)
            return False
        view.selectedSignalsDict[key] = self.entryFor(view, treeNode)
        self.style(treeNode, view)
        return True

    def unselectNode(self, treeNode, view=None):
        """Take this node out of the view's selection. True if it was in it."""
        view = view or self.viewOf(treeNode)
        key = self.keyFor(view, treeNode)
        wasSelected = key in view.selectedSignalsDict
        # Not a KeyError when the dictionary no longer holds it: the tree can be
        # rebuilt under a selection, and the user asking to unselect a node that
        # is not selected is not an error the application should answer with.
        view.selectedSignalsDict.pop(key, None)
        self.style(treeNode, view)
        return wasSelected

    # -- a family, and everything ----------------------------------------

    def sameAos(self, treeNode=None):
        """Select the leaves of the same structure this node belongs to.

        Returns how many nodes joined the selection. The view's current item is
        left alone: the old entry wrote ``selectedItem`` for every node it walked
        through, which left the tree pointed at whatever the loop touched last --
        and every later command that reads ``selectedItem`` drew that one.
        """
        treeNode = treeNode if treeNode is not None else self.treeNode
        if treeNode is None:
            raise ValueError('Nothing to select: no node was asked for.')
        view = self.viewOf(treeNode)
        return sum(1 for node in self.familyOf(treeNode)
                   if self.selectNode(node, view))

    def unselectAll(self):
        """Empty the selection of every view this command was asked to cover.

        Returns how many entries were dropped. The old command walked the whole
        list of signals of a view for every selected node and compared the
        dictionaries, then deleted by counting on the wrong list: measured, one
        selected node that the tree no longer listed raised IndexError after two
        of three nodes had been dropped, leaving the third red and selected.
        """
        dropped = 0
        for view in self.views():
            for key, entry in list(view.selectedSignalsDict.items()):
                del view.selectedSignalsDict[key]
                dropped += 1
                self.style(entry.get('QTreeWidgetItem'), view)
        return dropped

    # -- what the selection is --------------------------------------------

    def isSelected(self, treeNode, view=None):
        view = view or self.viewOf(treeNode)
        return self.keyFor(view, treeNode) in view.selectedSignalsDict

    def entryFor(self, view, treeNode):
        """The entry a plot command reads for this node.

        The shape the whole selection-plot path expects -- and the node asked
        about, not the tree's current item, which is what used to end up here.
        """
        return {'index': len(view.selectedSignalsDict),
                'QTreeWidgetItem': treeNode,
                'uri': view.dataSource.uri}

    def familyOf(self, treeNode):
        """Every leaf of this view sitting in the same structure as this one.

        The structure is the parametrized path -- index *names*, not indices -- so
        the family is the array of structures the leaf belongs to: every element
        of it, and only the occurrence of the IDS the leaf was reached through.
        The node asked for comes first, so the selection order starts with what
        the user clicked.
        """
        structure = treeNode.getParametrizedDataPath()
        if not structure:
            return [treeNode]
        occurrence = treeNode.getOccurrence()
        return [treeNode] + [node for node in self.viewOf(treeNode).signalsList
                             if node is not treeNode and
                             node.getParametrizedDataPath() == structure and
                             node.getOccurrence() == occurrence]

    def views(self):
        return (self.dataTreeView.imas_viz_api.DTVlist if self.all_DTV
                else [self.dataTreeView])

    # -- what the tree shows ----------------------------------------------

    @staticmethod
    def keyFor(view, treeNode):
        return view.dataSource.dataKey(treeNode)

    def viewOf(self, treeNode):
        """The view a node belongs to.

        The tree sets its own view on every node it builds, so a node reached
        from a right click answers this itself; a node that does not answer it is
        the view this command was built with, which is the only view the caller
        knows about. `QVizTreeNode.getDataTreeView` cannot be used here: it walks
        parents until it finds one and dies on a node above which there is none.
        """
        node = treeNode
        while node is not None:
            view = getattr(node, 'dataTreeView', None)
            if view is not None:
                return view
            node = node.parent()
        return self.dataTreeView

    @staticmethod
    def style(treeNode, view):
        """Colour the label by the selection, which is the only record.

        Guarded because a node whose tree was rebuilt underneath it is a C++
        object Qt may already have taken away: the selection still has to be
        cleared, and a label that cannot be recoloured is not a reason to leave a
        phantom entry behind.
        """
        if treeNode is None:
            return
        try:
            if QVizSelectNodes.keyFor(view, treeNode) in view.selectedSignalsDict:
                treeNode.setStyleWhenSelected()
            else:
                treeNode.setStyleWhenContainingData()
        except RuntimeError:
            pass
