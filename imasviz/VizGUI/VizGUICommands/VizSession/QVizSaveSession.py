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

Two kinds of window used to be left out and said in the log: the Profiles
plugin's window and the Equilibrium chart. Neither is drawn from a selection of
this session -- the first asks which occurrence to plot through a dialog of its
own, the second is a matplotlib window that registers no node in `figToNodes` at
all. Since version 3 of the format they are saved, as a `<PluginWindow>` under
the case whose gesture opened them: the gesture belongs to a shot view -- its
catalog is what offers the entry -- and the two answers that entry would have
asked are written with it, because a restore has no one to answer a modal
`QInputDialog`. A plugin window is registered in `figureframes` like the four
plot windows, so the same walk meets it; it is saved where that walk finds the
stamp the plugin left (`QVizPluginWindow`), and a frame carrying no stamp is
still named as unsaved.
"""

import logging

from imasviz.VizDataAccess.VizTimeSlices import (ALL_SLICES, ONE_IN_TEN,
                                                 FIRST_SLICE)
from imasviz.VizGUI.VizConfigurations.QVizSessionFile import (
    QVizSessionFile, QVizSessionCase, QVizSessionLoad, QVizSessionExpanded,
    QVizSessionSelection, QVizSessionFigure, QVizSessionQuantity,
    QVizSessionCursor, QVizSessionCursors, QVizSessionView, QVizSessionErrors,
    QVizSessionWindow, QVizSessionPluginWindow,
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
        windows = self.pluginWindowsByCase()
        cases = []
        for view in self.api.DTVlist:
            cases.append(self.caseOf(view, windows.pop(view.dataSource.uri,
                                                       [])))
        for uri, left in windows.items():
            # A plugin window whose case is no longer on screen: its entry
            # belongs to a shot view, so no case in the file can replay it.
            logging.getLogger('logPanel').warning(
                'The plugin window%s %s is not saved: no shot view of the case '
                '"%s" is open, and the entry that drew it belongs to that view.'
                % ('s' if len(left) > 1 else '',
                   ', '.join('"%s"' % window.key for window in left), uri))
        session = QVizSessionFile(cases=cases,
                                  figures=self.figures(),
                                  path=self.path)
        session.write(self.path)
        logging.getLogger('logPanel').info(
            'Session saved to "%s": %d case(s), %d figure(s), %d plugin '
            'window(s).'
            % (self.path, len(session.cases), len(session.figures),
               sum(len(case.pluginWindows) for case in session.cases)))
        return self.path

    def pluginWindowsByCase(self):
        """The plugin windows of the run, under the case that opened each one.

        The key is taken from `figureframes` -- the bookkeeping the Show/Hide and
        Delete menus address a window by -- because measured, neither registered
        plugin window knows its own: the Profiles panel has no `figureKey` and no
        `key` attribute, and the Equilibrium chart has neither. The rest comes
        from the stamp the plugin left, which is the only place the entry number
        and the occurrence it answered are kept.
        """
        windows = {}
        for figureKey, frame in list(self.api.figureframes.items()):
            stamp = getattr(frame, 'pluginWindow', None)
            if stamp is None:
                continue
            windows.setdefault(stamp.uri, []).append(
                QVizSessionPluginWindow(key=figureKey, plugin=stamp.plugin,
                                        entry=stamp.entry, ids=stamp.ids,
                                        occurrence=stamp.occurrence))
        return windows

    # ----------------------------------------------------------------- cases
    def caseOf(self, view, pluginWindows=()):
        return QVizSessionCase(uri=view.dataSource.uri,
                               dd_version=getattr(view.dataSource,
                                                  'dd_version', None),
                               label=self.labelOf(view),
                               loads=self.loadsOf(view),
                               expanded=self.expandedOf(view),
                               selection=self.selectionOf(view),
                               pluginWindows=pluginWindows)

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
        """Every plot window the figure bookkeeping addresses.

        In the order they were opened: `figureframes` is a dict, and the order
        the frames were registered in is the order the user met them. A plugin
        window is not a `<Figure>`: it is saved under its case, and only a frame
        that carries no stamp is named as lost -- measured, the four plugin
        windows of a probe wrote a 432-byte file holding **0** `<Figure>` and
        repeated one warning four times.
        """
        figures = []
        for figureKey, frame in list(self.api.figureframes.items()):
            kind = self.kindOf(frame)
            if kind is None:
                if getattr(frame, 'pluginWindow', None) is not None:
                    continue
                logging.getLogger('logPanel').warning(
                    'The window "%s" is not saved: it is drawn by a plugin that '
                    'says nothing about the window it drew, and a session has no '
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
                                                     ())),
                                 cursors=self.cursorsOf(frame),
                                 view=self.viewOf(figureKey, frame),
                                 errors=self.errorsOf(figureKey, frame),
                                 window=self.windowOf(figureKey, frame))

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

    # ------------------------------------------------ what the user had set on a
    #                                                          figure of version 2
    # Each of these four reads asks the frame what it already keeps, in the words
    # the frame itself uses for it. None of them invents a widget state: a session
    # that recorded a pen or a font is the one that wrote no file at all.

    @staticmethod
    def cursorsOf(frame):
        """Where each slider of the band stands, and whether the band is folded.

        A curve figure and an image window carry their band (`sliceControls`); a
        table and a stacked window keep one band per panel, and those are not
        saved: a panel's sliders belong to a cell, and the file would have to say
        which cell -- that is the same shape as the table's places, and it is not
        what a version 2 `<Cursors>` under a `<Figure>` can say.
        """
        controls = getattr(frame, 'sliceControls', None)
        if controls is None:
            return None
        indices = controls.indices()
        if not indices:
            return None
        return QVizSessionCursors(
            folded=controls.isFolded() if controls.isFoldable() else None,
            cursors=[QVizSessionCursor(key=key, index=index)
                     for key, index in indices.items()])

    @staticmethod
    def viewOf(figureKey, frame):
        """The range the window is looking at, and which axes fit themselves.

        Asked of a curve figure only: that is the one window whose zoom the user
        drives through the right-click menu, and the one with a single view box to
        ask. An image window answers one view box per picture -- a range there is
        a per-picture state, and writing one range for several pictures would say
        something nobody set.
        """
        if not isinstance(frame, QVizCurvePlot):
            return None
        box = frame.pgPlotWidget.getViewBox()
        (x0, x1), (y0, y1) = box.viewRange()
        autoX, autoY = box.state['autoRange'][0], box.state['autoRange'][1]
        xInverted, yInverted = box.xInverted(), box.yInverted()
        if autoX is not False and autoY is not False \
                and not xInverted and not yInverted:
            # Nothing was set: the drawing fits both axes itself, and a stale
            # range written here would pin what the restore is about to choose.
            return None
        return QVizSessionView(x0=x0, x1=x1, y0=y0, y1=y1,
                               autoX=autoX is not False,
                               autoY=autoY is not False,
                               xInverted=xInverted, yInverted=yInverted)

    @staticmethod
    def errorsOf(figureKey, frame):
        """Which of the three right-click lines are on, and at what step.

        Counted off what the frame drew rather than asked back from the menu: a
        bar that is on screen is in `errors.bars`, and the step it was drawn at is
        `errors.stepUsed()`. A curve frame is the only one that owns an
        `QVizCurveErrors`, so an image window answers None and no `<Errors>`.
        """
        errors = getattr(frame, 'errors', None)
        if errors is None:
            return None
        bars = errors.errorBarCount()
        bands = errors.bandCount()
        if not bars and not bands:
            return None
        # The step of the bars that are on screen. None when there are none: a
        # window with only a band must come back with only a band, and answering
        # 1 here would draw bars the user never asked for.
        step = (errors.stepUsed() or 1) if bars else None
        return QVizSessionErrors(bars=step, bands=bool(bands))

    def windowOf(self, figureKey, frame):
        """Where the window sits in the MDI area.

        `mdiWindowOf` is the same reading the Show/Hide and Delete menus use, so
        the geometry is taken for the window those menus address. A frame with no
        window of its own is said rather than skipped quietly: it is a figure the
        file records and the restore will show somewhere Qt puts it.
        """
        window = self.api.mdiWindowOf(frame)
        if window is None:
            logging.getLogger('logPanel').warning(
                'The window "%s" has no place in the MDI area: its geometry is '
                'not saved, and the restore will show it where Qt puts it.'
                % figureKey)
            return None
        geometry = window.geometry()
        return QVizSessionWindow(x=geometry.x(), y=geometry.y(),
                                 w=geometry.width(), h=geometry.height(),
                                 maximized=window.isMaximized(),
                                 hidden=window.isHidden())

