# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""What a session holds, taken from the application as it stands.

The session is not stored anywhere today: closing the window drops the cases,
the occurrences that were loaded, the selection, and every figure that was drawn
-- and the user rebuilds all of it by hand the next day, one right click at a
time. The manual keeps plot configurations and node selections for exactly that
rebuilding, but neither says which windows were open together: a configuration
names quantities and a place in a table, and the abscissa of one window.

So this command reads what the api already keeps, and writes it as questions
rather than as answers: a case URI, an IDS name, an occurrence, a slice choice,
a node path, a figure key. The figures come from `figureframes` and `figToNodes`
-- which is what the Show/Hide and Delete menus read, so what is saved is the set
of windows the menus address, not a parallel list that can drift. The tree state
is taken from the items themselves (`isExpanded`), because "which branches were
open" is only recorded there.

Two kinds of window are left out, and said in the log rather than kept quiet:
the Profiles plugin's window and the Equilibrium chart. Neither is drawn from a
selection of this session -- the first asks which occurrence to plot through a
dialog of its own, the second is a matplotlib window that registers no node in
`figToNodes` at all -- so a file recording them would promise a window the
restore has no gesture to replay.
"""

import logging

from imasviz.VizDataAccess.VizTimeSlices import (ALL_SLICES, ONE_IN_TEN,
                                                 FIRST_SLICE)
from imasviz.VizGUI.VizConfigurations.QVizSessionFile import (
    QVizSessionFile, QVizSessionCase, QVizSessionLoad, QVizSessionExpanded,
    QVizSessionSelection, QVizSessionFigure, QVizSessionQuantity,
    CURVE, IMAGE, TABLE, STACKED, ALL, ONE_IN_TEN as ONE_IN_TEN_WORD,
    FIRST, INDEX_PREFIX)
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizImagePlot import QVizImagePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizTablePlot import QVizTablePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizStackedPlot import QVizStackedPlot


class QVizSaveSession:
    """Write down the cases, the loads, the selection and the figures."""

    def __init__(self, imas_viz_api, path=None, name=None):
        """
        Arguments:
            imas_viz_api      : the session itself -- its shot views and its
                                figures are what is saved.
            path          str : the file to write.
            name          str : a name inside the configuration folder, for the
                                menu that asked one. The guard that keeps a typed
                                name inside that folder belongs to the format.
        """
        self.api = imas_viz_api
        self.path = path
        if path is None and name is not None:
            self.path = QVizSessionFile.named(name)

    def execute(self):
        """Write the session, and answer with the file that holds it."""
        if self.path is None:
            raise ValueError('No file was named to save the session to.')
        session = QVizSessionFile(cases=[self.caseOf(view)
                                         for view in self.api.DTVlist],
                                  figures=self.figures(),
                                  path=self.path)
        session.write(self.path)
        logging.getLogger('logPanel').info(
            'Session saved to "%s": %d case(s), %d figure(s).'
            % (self.path, len(session.cases), len(session.figures)))
        return self.path

    # ----------------------------------------------------------------- cases
    def caseOf(self, view):
        return QVizSessionCase(uri=view.dataSource.uri,
                               dd_version=getattr(view.dataSource,
                                                  'dd_version', None),
                               label=self.labelOf(view),
                               loads=self.loadsOf(view),
                               expanded=self.expandedOf(view),
                               selection=self.selectionOf(view))

    @staticmethod
    def labelOf(view):
        """What the window of that shot view is called -- a comment in the file.

        The case is reopened by its URI, so this is for the user reading the file
        over, not for the restore.
        """
        frame = getattr(view, 'parent', None)
        title = getattr(frame, 'windowTitle', None)
        return title() if title else None

    def loadsOf(self, view):
        """Which occurrences this view displays, and how each was asked for."""
        return [QVizSessionLoad(idsName, occurrence,
                                self.sliceWord(view.sliceSelectionFor(
                                    idsName, occurrence)))
                for idsName in sorted(view.IDSRoots)
                for occurrence in sorted(view.loadedOccurrences(idsName))]

    @staticmethod
    def sliceWord(selection):
        """The word the file writes for one of the four slice choices.

        Nothing is guessed here: an object that is none of the three named
        choices and carries no index is refused by name, because writing "first"
        for a choice this module does not recognise is how a session comes back
        showing something other than what the user had.
        """
        if selection is ALL_SLICES:
            return ALL
        if selection is ONE_IN_TEN:
            return ONE_IN_TEN_WORD
        if selection is FIRST_SLICE:
            return FIRST
        index = selection.index()
        if index is not None:
            return '%s%d' % (INDEX_PREFIX, index)
        raise ValueError('%r is not one of the four slice choices this '
                         'application writes.' % (selection,))

    def expandedOf(self, view):
        """Which branches of that tree the user had open.

        The IDS branch and the occurrence nodes under it, which is as far as a
        session file goes in version 1: the quantities that matter come back as
        the selection and the figures, and a branch below an occurrence is
        restored folded.
        """
        expanded = []
        for idsName in sorted(view.IDSRoots):
            root = view.IDSRoots[idsName]
            if self.isOpen(root):
                expanded.append(QVizSessionExpanded(idsName, None))
            for occurrence in sorted(view.loadedOccurrences(idsName)):
                entry = view.ids_roots_occurrence.get(
                    idsName + '/' + str(occurrence))
                if entry is not None and self.isOpen(entry):
                    expanded.append(QVizSessionExpanded(idsName, occurrence))
        return expanded

    @staticmethod
    def isOpen(node):
        """Whether a tree item is unfolded, answering False for one Qt took away."""
        try:
            return node.isExpanded()
        except RuntimeError:
            return False

    def selectionOf(self, view):
        """The quantities selected in that view, in the order they were picked."""
        return [QVizSessionSelection(path=node.getPath(),
                                     occurrence=node.getOccurrence())
                for node in (entry['QTreeWidgetItem']
                             for entry in view.selectedSignalsDict.values())]

    # --------------------------------------------------------------- figures
    def figures(self):
        """Every window the figure bookkeeping addresses.

        In the order they were opened: `figureframes` is a dict, and the order
        the frames were registered in is the order the user met them.
        """
        figures = []
        for figureKey, frame in list(self.api.figureframes.items()):
            kind = self.kindOf(frame)
            if kind is None:
                logging.getLogger('logPanel').warning(
                    'The window "%s" is not saved: it is drawn by a plugin, '
                    'from a question the plugin asks, and a session has no '
                    'gesture to replay it.' % figureKey)
                continue
            figures.append(self.figureOf(figureKey, frame, kind))
        return figures

    @staticmethod
    def kindOf(frame):
        """Which of the four windows this frame is, or None for a plugin's own."""
        if isinstance(frame, QVizCurvePlot):
            return CURVE
        if isinstance(frame, QVizImagePlot):
            return IMAGE
        if isinstance(frame, QVizTablePlot):
            return TABLE
        if isinstance(frame, QVizStackedPlot):
            return STACKED
        return None

    def figureOf(self, figureKey, frame, kind):
        return QVizSessionFigure(key=figureKey, kind=kind,
                                 quantities=self.quantitiesOf(figureKey, frame,
                                                              kind),
                                 axis=self.axisOf(frame),
                                 tensor=bool(getattr(frame, 'walkingArrays',
                                                     ())))

    def quantitiesOf(self, figureKey, frame, kind):
        """The quantities that figure holds, as the figure bookkeeping knows them.

        `figToNodes` is the record the "add this quantity to that figure" entries
        fill, so a figure saved from it is the figure the menus address. For a
        table, the cell each panel sits in is read from the layout -- the same
        reading the plot configuration saves use, because a place computed from
        the panel count is what put two panels in one cell.
        """
        places = self.placesOf(frame)
        quantities = []
        for uri, treeNode in self.api.figToNodes.get(figureKey, {}).values():
            place = places.get(treeNode)
            quantities.append(QVizSessionQuantity(
                path=treeNode.getPath(),
                occurrence=treeNode.getOccurrence(),
                uri=uri,
                row=None if place is None else place[0],
                column=None if place is None else place[1]))
        return quantities

    @staticmethod
    def placesOf(frame):
        return {panel.treeNode: (row, column)
                for row, column, panel in frame.panelsInTable()} \
            if isinstance(frame, QVizTablePlot) else {}

    @staticmethod
    def axisOf(frame):
        """The abscissa strategy of a table or a stacked window.

        A curve figure has no such strategy to record: its abscissa is settled by
        the first quantity drawn into it, so replaying that quantity settles the
        same one again.
        """
        if isinstance(frame, (QVizTablePlot, QVizStackedPlot)):
            return frame.getPlotAxis()
        return None
