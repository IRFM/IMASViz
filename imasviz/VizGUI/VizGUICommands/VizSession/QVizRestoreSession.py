# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Putting a session back by asking the application the questions it saved.

A file of paths and keys is not a screen. What comes back on the screen is built
by the same commands the user drives: the case is opened the way the *Open* entry
opens it, each occurrence is loaded through `QVizLoadOccurrence`, each quantity
is drawn through `QVizPlotOneNode`, a Table Plot View through `QVizPlotAsTable`,
a Stacked Plot View through `QVizPlotAsStacked`. So a restored window has its
sliders, its abscissa, its legend and its entry in the Show/Hide menu, because it
is one of the frames rather than a description of one -- which is the difference
with the legacy state saving, whose writer serialised pyqtgraph options and whose
reader kept two attributes of them.

Three consequences of replaying rather than restoring, and each is a choice:

* the loads are **synchronous**. The gesture of the manual starts a walk on a
  thread of its own and returns in hundredths of a second; a session being put
  back has to know what each walk produced before it draws the quantities that
  depend on it, and a figure whose tree is still being built is an empty window.
  The cost is measured on the reference case: 3,99 s for the walk of
  `equilibrium` occurrence 0 read whole, 0,10 s read lazily -- which is what
  every load of a session is now;
* a case that cannot be opened costs **its own** windows and nothing else. The
  reason goes to the log, and the other cases of the file are put back;
* the figure keys of the file are honoured. Replaying the gestures and letting
  the api hand out the next key would renumber the windows (measured:
  `SlicesPlot1` came back as `SlicesPlot2`), and the key is the name the
  Show/Hide, Delete and "add to that figure" menus address.

The selection is applied last, because a Stacked Plot View is filled from the
selection of its view: a stacked window of three quantities would otherwise draw
whatever the session happened to have selected before, and then clear it.
"""

import logging

from imasviz.VizDataAccess.VizTimeSlices import (ALL_SLICES, ONE_IN_TEN,
                                                 FIRST_SLICE, atIndex)
from imasviz.VizGUI.VizConfigurations.QVizConfigurationFile import (
    QVizConfigurationFile, QVizQuantity, PLOT)
from imasviz.VizGUI.VizConfigurations.QVizSessionFile import (
    QVizSessionFile, CURVE, TABLE, STACKED, ALL, ONE_IN_TEN as ONE_IN_TEN_WORD,
    FIRST, INDEX_PREFIX)
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence import \
    QVizLoadOccurrence
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectNodes import \
    QVizSelectNodes
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode import \
    QVizPlotOneNode
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsTable import \
    QVizPlotAsTable
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsStacked import \
    QVizPlotAsStacked


class QVizRestoreSession:
    """Open the cases a file names, load them, draw the windows it lists."""

    def __init__(self, imas_viz_api, path=None, name=None):
        """
        Arguments:
            imas_viz_api      : the session the file is put back into.
            path          str : the file to read.
            name          str : a name inside the configuration folder, for the
                                menu that listed the sessions and answered one.
        """
        self.api = imas_viz_api
        self.path = path
        if path is None and name is not None:
            self.path = QVizSessionFile.named(name)

    def execute(self):
        """Put the session back. Returns {uri: view} for the cases that came.

        A case that refused is None here and its reason is in the log; the rest
        of the file is still put back, because a session usually holds more than
        one shot and an unreachable one is not a reason to lose the others.
        """
        if self.path is None:
            raise ValueError('No session file was named to restore.')
        session = QVizSessionFile.read(self.path)

        views = {}
        for case in session.cases:
            views[case.uri] = self.openCase(case)
        for figure in session.figures:
            self.restoreFigure(figure, views)
        for case in session.cases:
            if views.get(case.uri) is not None:
                self.applySelection(case, views[case.uri])

        logging.getLogger('logPanel').info(
            'Session "%s" restored: %d of %d case(s), %d figure(s).'
            % (self.path, sum(1 for view in views.values() if view), len(views),
               len(session.figures)))
        return views

    # ----------------------------------------------------------------- cases
    def openCase(self, case):
        """Open one case and load the occurrences its file lists.

        Not through `QVizOpenShotView.Open`: that entry answers nothing, so a
        session could not tell an unreachable case from one that opened, and the
        windows of that case would be replayed against no tree at all. The three
        calls it makes are made here, with the reason it swallows kept.
        """
        from imasviz.VizDataSource.QVizDataSourceFactory import \
            QVizDataSourceFactory
        try:
            source = QVizDataSourceFactory().create(case.uri)
            if self.api.isDataSourceAlreadyOpened(source):
                view = self.api.GetDTVFor(source.getKey())
                logging.getLogger('logPanel').info(
                    'The case %s is already open: its windows are put back on '
                    'the view that shows it.' % case.uri)
            else:
                view = self.api.CreateDataTree(source).dataTreeView
                self.api.ShowDataTree(view)
        except ValueError as e:
            logging.getLogger('logPanel').error(
                'The case %s named by "%s" cannot be opened: %s'
                % (case.uri, self.path, e))
            return None

        self.refuseAnotherDictionary(case, view)
        for load in case.loads:
            self.load(view, load)
        for expanded in case.expanded:
            self.expand(view, expanded)
        return view

    def refuseAnotherDictionary(self, case, view):
        """Say when the case came back at another data dictionary than the file's.

        A node path is a name in a dictionary: a session written at 3.35.0 and
        opened on a case stored at 3.42.2 holds a different number of leaves --
        measured, 3519 against 3594 for one occurrence of `equilibrium` -- so a
        quantity can be missing from a tree that otherwise looks identical. This
        does not stop the restore: it says what may be missing, and the paths
        that are missing are named one by one below.
        """
        now = getattr(view.dataSource, 'dd_version', None)
        if case.dd_version and now and case.dd_version != now:
            logging.getLogger(view.uri).warning(
                '"%s" was saved when %s was read at data dictionary %s; it is '
                'open now at %s, so a quantity the file names may be missing '
                'from this tree.'
                % (self.path, case.uri, case.dd_version, now))

    def load(self, view, load):
        """Ask the case for one occurrence, with the slice choice the file says."""
        if self.api.IDSDataAlreadyFetched(view, load.ids, load.occurrence):
            # The case was already open on this screen, or the same session was
            # put back twice: the occurrence is there, and walking it again would
            # rebuild the branch the user may be looking at -- 0,10 s of walk and
            # a new tree for one occurrence of the reference case.
            return
        try:
            QVizLoadOccurrence(dataTreeView=view, idsName=load.ids,
                               occurrence=load.occurrence,
                               sliceSelection=self.sliceSelection(load.slices),
                               asynch=False).execute()
        except ValueError as e:
            # The walk of one occurrence can refuse an index the case does not
            # hold, and that refusal belongs to that occurrence alone: the other
            # loads of the file and the windows that do not use it go ahead.
            logging.getLogger(view.uri).error(
                'Occurrence %d of the %s IDS named by "%s" was not loaded: %s'
                % (load.occurrence, load.ids, self.path, e))

    @staticmethod
    def sliceSelection(word):
        """The choice object the file's word stands for."""
        if word == ALL:
            return ALL_SLICES
        if word == ONE_IN_TEN_WORD:
            return ONE_IN_TEN
        if word == FIRST:
            return FIRST_SLICE
        return atIndex(int(word[len(INDEX_PREFIX):]))

    def expand(self, view, expanded):
        """Unfold the branch the file found unfolded.

        A branch that is not in the tree any more is not an error to report: the
        load that would have built it is refused above, by name.
        """
        if expanded.occurrence is None:
            node = view.IDSRoots.get(expanded.ids)
        else:
            node = view.ids_roots_occurrence.get(
                expanded.ids + '/' + str(expanded.occurrence))
        if node is None:
            return
        try:
            node.setExpanded(True)
        except RuntimeError:
            pass

    # --------------------------------------------------------------- figures
    def restoreFigure(self, figure, views):
        """Draw one window of the file, under the key the file names."""
        view = self.viewOf(figure, views)
        if view is None:
            logging.getLogger('logPanel').error(
                'The figure "%s" named by "%s" is not drawn: none of the cases '
                'it takes its quantities from is open.' % (figure.key, self.path))
            return

        frames = []
        if figure.kind == STACKED:
            frames.append(self.replayStacked(figure, view))
        elif figure.kind == TABLE:
            frames.append(self.replayTable(figure, view))
        else:
            frames.extend(self.replayOneNode(figure, view))
        for frame in frames:
            self.showInMDI(frame)

    def viewOf(self, figure, views):
        """The view to draw this window through: the case of its first quantity.

        A quantity without a URI -- a file corrected by hand -- belongs to the
        only case the file names when there is one, which is what a session of a
        single shot is.
        """
        for quantity in figure.quantities:
            view = views.get(quantity.uri)
            if view is not None:
                return view
        if len(views) == 1:
            return next(iter(views.values()))
        return None

    def replayOneNode(self, figure, view):
        """A curve figure or an image, quantity by quantity.

        The first quantity opens the window under the key of the file; the others
        join it, which is the same gesture as the menu's *Plot X to -> Figure ->*
        the open window. An image window holds one quantity, so the file that
        says otherwise gets one panel and the rest is named in the log by the
        command that refuses it.
        """
        frames = []
        for index, quantity in enumerate(figure.quantities):
            node = self.findNode(view, quantity.path, quantity.occurrence)
            if node is None:
                logging.getLogger(view.uri).error(
                    '"%s" is named by the figure "%s" of "%s" but is not in '
                    'this tree: load the IDS it belongs to.'
                    % (quantity.path, figure.key, self.path))
                continue
            if index == 0:
                command = QVizPlotOneNode(dataTreeView=view, treeNode=node,
                                          figureKey=figure.key,
                                          tensor=figure.tensor)
            else:
                command = QVizPlotOneNode(dataTreeView=view, treeNode=node,
                                          intoFigureKey=figure.key)
            frames.append(command.execute())
        return frames

    def replayTable(self, figure, view):
        """A Table Plot View, from the quantities and the cells the file names.

        The quantities and their places reach the command as a configuration --
        the same shape a ``.pcfg`` hands it -- because the cell a panel sits in is
        only kept when it arrives with the quantity: laying it out again from the
        panel count is what put two panels in one cell.
        """
        configuration = QVizConfigurationFile(
            kind=PLOT, path=self.path, abscissa=figure.axis,
            quantities=[QVizQuantity(path=quantity.path,
                                     occurrence=quantity.occurrence,
                                     row=quantity.row, column=quantity.column,
                                     uri=quantity.uri)
                        for quantity in figure.quantities])
        try:
            return QVizPlotAsTable(dataTreeView=view, plotAxis=figure.axis,
                                   configuration=configuration,
                                   figureKey=figure.key).execute()
        except ValueError as e:
            logging.getLogger(view.uri).error(
                'The table "%s" named by "%s" was not drawn: %s'
                % (figure.key, self.path, e))
            return None

    def replayStacked(self, figure, view):
        """A Stacked Plot View, which is filled from the selection of its view.

        So the selection is set to the quantities of this window first. The
        session's own selection is applied afterwards, over this one.
        """
        QVizSelectNodes(dataTreeView=view).unselectAll()
        for quantity in figure.quantities:
            node = self.findNode(view, quantity.path, quantity.occurrence)
            if node is not None:
                QVizSelectNodes(dataTreeView=view, treeNode=node).selectNode(node)
        try:
            return QVizPlotAsStacked(
                dataTreeView=view,
                plotAxis='TIME' if figure.axis == 'TIME' else 'DEFAULT',
                figureKey=figure.key).execute()
        except ValueError as e:
            logging.getLogger(view.uri).error(
                'The stacked plot "%s" named by "%s" was not drawn: %s'
                % (figure.key, self.path, e))
            return None

    def showInMDI(self, frame):
        """Embed a window the restore built, and only once.

        `QVizPlotOneNode` returns a frame it built and leaves the caller embed it;
        the quantities that joined it return the same frame. Asking whether the
        frame is already in the MDI area is what keeps one window from being put
        in the area twice.
        """
        if frame is None or self.api.mdiWindowOf(frame) is not None:
            return
        self.api.addPlotWidgetToMDI(frame)

    # ------------------------------------------------------------- selection
    def applySelection(self, case, view):
        """Select the quantities the file names, and only those.

        A session is put back as it was, and the selection is part of what was:
        it is what the next *Plot the selection* gesture will draw. A quantity the
        tree does not hold is named and skipped, the same way a node selection
        file is applied.
        """
        QVizSelectNodes(dataTreeView=view).unselectAll()
        for selection in case.selection:
            node = self.findNode(view, selection.path, selection.occurrence)
            if node is None:
                logging.getLogger(view.uri).error(
                    '"%s" is selected by "%s" but is not in this tree: load the '
                    'IDS it belongs to.' % (selection.path, self.path))
                continue
            QVizSelectNodes(dataTreeView=view,
                            treeNode=node).selectNode(node)

    @staticmethod
    def findNode(view, path, occurrence):
        """The node of that view standing on that path and occurrence."""
        for node in view.signalsList:
            if node.getPath() == path and node.getOccurrence() == occurrence:
                return node
        return None
