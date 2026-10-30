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
    FIRST, INDEX_PREFIX, cursorKeyText)
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
from imasviz.VizGUI.VizPlot.QVizColourScales import mapNamed, restoreColourScale
from imasviz.VizGUI.VizPlot.QVizPlotStyling import replayCurves, replayText
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot


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
        windows = self.replayPluginWindows(session, views)
        for case in session.cases:
            if views.get(case.uri) is not None:
                self.applySelection(case, views[case.uri])

        logging.getLogger('logPanel').info(
            'Session "%s" restored: %d of %d case(s), %d figure(s), %d plugin '
            'window(s).'
            % (self.path, sum(1 for view in views.values() if view), len(views),
               len(session.figures), windows))
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
        for frame in self.distinctFrames(frames):
            self.showInMDI(frame)
        for frame in self.distinctFrames(frames):
            self.applyState(figure, frame, view)

    @staticmethod
    def distinctFrames(frames):
        """The frames to work on, once each.

        `replayOneNode` answers the same frame for every quantity that joined it,
        and putting a state back twice is a curve re-read twice for nothing.
        """
        once = []
        for frame in frames:
            if frame is not None and not any(frame is seen for seen in once):
                once.append(frame)
        return once

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

    # ---------------------------------------------------- what was set on a window
    def applyState(self, figure, frame, view):
        """Put back what the user had set on that window, in the order that holds.

        The order is not a taste. The styling goes on first -- the pens of a
        figure of curves, then the colours of a window of pictures -- and then the
        sliders:
        moving one re-reads the figure through the band's own `changed` signal
        -- measured on the
        reference case, **0,001 s** for one move over a 17-element array and
        **0,003 s** for five, so a session of a handful of sliders costs
        thousandths of a second. The error lines come *after* those moves: a bar
        drawn over samples the sliders then move is not out of date, it is wrong,
        and `refresh` would have redrawn it a second time for nothing. The view
        range comes after the drawing, because the drawing is what fits the axes
        and only then can the file take that back. The window geometry comes last,
        because it is the only one of the four that Qt answers about a window that
        has to be on screen.

        The numbers are small because the restore replays them, it does not replay
        the drawing -- and the styling comes first of them for that same reason: a
        pen belongs to the trace, and moving a slider re-reads the samples under the
        pen that is already on it (measured on the reference case: a colour set by
        hand survives a `refresh`), so putting the colours back before the sliders
        move costs one pass over the traces and nothing has to be drawn twice. A
        picture window is dressed the same way for a blunter reason: its re-read
        hands the new values to pyqtgraph *with* the level range, so a range put
        back after the first move would be the moved one, not the saved one.
        """
        self.applyStyles(figure, frame, view)
        self.applyColourScale(figure, frame, view)
        self.applyCursors(figure, frame, view)
        self.applyErrors(figure, frame, view)
        self.applyView(figure, frame, view)
        self.applyWindow(figure, frame, view)

    def applyColourScale(self, figure, frame, view):
        """The colours and the level range a hand left on a window of pictures.

        One element for the whole window, because the window answers one scale for
        all its pictures -- so this is put back once, and every picture changes
        colour together. Two things can stop it, and they cost different amounts:

        * a map this node cannot draw -- a name another install wrote, a map
          matplotlib knows and this one does not have. It is named in the log and
          the window keeps the colours it opens with. The **range** still goes on:
          the two are separate answers, and losing a scale because a colour is
          missing would hide the number the user set;
        * a window that holds no colour scale at all -- the file wrote a picture
          and the case now draws curves under that key. Said, and nothing else
          about that window is touched.
        """
        scale = figure.scale
        if scale is None:
            return
        colorMap = scale.map
        if colorMap is not None:
            try:
                mapNamed(colorMap)
            except ValueError as error:
                logging.getLogger(view.uri).warning(
                    'The colour map "%s" of the figure "%s" is not put back: %s '
                    'The pictures keep the colours they open with, and the level '
                    'range of the file still stands.'
                    % (colorMap, figure.key, error))
                colorMap = None
        if colorMap is None and scale.low is None and scale.high is None:
            return
        if not restoreColourScale(frame, name=colorMap, low=scale.low,
                                  high=scale.high):
            logging.getLogger(view.uri).warning(
                'The colour scale of the figure "%s" is not put back: a window of '
                '%s draws no picture to colour.' % (figure.key, figure.kind))

    def applyStyles(self, figure, frame, view):
        """The pens and the labels a hand left on that window, put back.

        A style names a quantity, so it is read back against the node of that view
        standing on the same path and run -- the identity the file writes. What the
        window does not draw is named and left alone: a colour that should have come
        back and did not is worth a line in the log of the case, and a colour put on
        the trace next to it is a lie about the data.
        """
        log = logging.getLogger(view.uri)
        for quantity in figure.quantities:
            if not quantity.styles and not quantity.text:
                continue
            node = self.findNode(view, quantity.path, quantity.occurrence)
            if node is None:
                log.warning(
                    'The styling of "%s" is not put back on the figure "%s" of '
                    '"%s": that quantity is not in the tree of this case, and its '
                    'window draws no trace to dress.'
                    % (quantity.path, figure.key, self.path))
                continue
            if quantity.styles:
                applied = replayCurves(frame, [(node, style.trace,
                                                style.attributes)
                                               for style in quantity.styles])
                if applied < len(quantity.styles):
                    log.warning(
                        'The figure "%s" of "%s" styles %d trace(s) of "%s": this '
                        'window draws %d of them.'
                        % (figure.key, self.path, len(quantity.styles),
                           quantity.path, applied))
            if quantity.text:
                replayText(frame, [(node, style.side, style.attributes)
                                   for style in quantity.text])
        if figure.text:
            # A `<TextStyle>` under the `<Figure>` belongs to the window itself:
            # its title and its four axes. A table and a stacked window own one
            # plot per panel and answer none, so the entry is named rather than
            # spread over the panels, which would style labels nobody styled.
            if replayText(frame, [(None, style.side, style.attributes)
                                  for style in figure.text]) == 0:
                log.warning(
                    'The figure "%s" of "%s" says how its own title and axes were '
                    'written: a %s window has one plot per panel, and its labels '
                    'are saved under the quantity of the panel they belong to.'
                    % (figure.key, self.path, figure.kind))

    def applyCursors(self, figure, frame, view):
        """Move the band's sliders to where the file left them.

        A key the window does not answer is named, not guessed: the same file read
        against a case whose array is shorter, or a quantity that is no longer in
        the tree, asks for a slider that is not on screen -- and moving the nearest
        slider by level would draw a curve the user never moved.
        """
        state = figure.cursors
        if state is None:
            return
        controls = getattr(frame, 'sliceControls', None)
        if controls is None:
            logging.getLogger(view.uri).warning(
                'The figure "%s" of "%s" says where its sliders stood; this %s '
                'window keeps one band per panel, and a session does not carry '
                'those yet.' % (figure.key, self.path, figure.kind))
            return
        for cursor in state.cursors:
            if not controls.setIndex(cursor.key, cursor.index):
                logging.getLogger(view.uri).error(
                    'The figure "%s" of "%s" puts its %s slider at %d: this '
                    'window has no such slider.'
                    % (figure.key, self.path, cursorKeyText(cursor.key),
                       cursor.index))
        if state.folded is not None and controls.isFoldable() \
                and controls.isFolded() != state.folded:
            controls.toggleFold()

    def applyErrors(self, figure, frame, view):
        """The bars and the band the user had switched on, at the step they were at.

        The step is not re-asked: *Show error bars (with slicing)* asks a step once,
        and a restore that asked again would make the user answer their own click.
        A quantity this case holds no error for is named by `QVizCurveErrors`
        itself, on the log of the case it was read from.
        """
        state = figure.errors
        if state is None:
            return
        errors = getattr(frame, 'errors', None)
        if errors is None:
            logging.getLogger(view.uri).warning(
                'The figure "%s" of "%s" had error lines on it: a %s window draws '
                'none.' % (figure.key, self.path, figure.kind))
            return
        if state.bars is not None:
            # Measured on `magnetics/flux_loop(0)/flux/data`: 0,012 s for a bar
            # over every one of 17 344 samples, 0,002 s at a step of 10.
            errors.showErrorBars(step=state.bars)
        if state.bands:
            # 0,051 s for the two borders and the fill between them.
            errors.showConfidenceBands()

    def applyView(self, figure, frame, view):
        """Take back the range the drawing fitted, where the file says it was set.

        Only the axes the file pins are given to pyqtgraph: `setRange` with
        `disableAutoRange` turns auto off for the axes whose range arrives and
        leaves the others to fit themselves, which is what a file naming `x0`/`x1`
        without an `autoY` asks for. Measured, a range put back this way **survives
        the re-read** the sliders cause, and costs 0,0007 s.
        """
        state = figure.view
        if state is None:
            return
        box = self.viewBoxOf(frame)
        if box is None:
            logging.getLogger(view.uri).warning(
                'The figure "%s" of "%s" says what it was zoomed onto: a %s window '
                'answers no single view to put that back on.'
                % (figure.key, self.path, figure.kind))
            return
        xRange = None if state.autoX else [state.x0, state.x1]
        yRange = None if state.autoY else [state.y0, state.y1]
        if xRange is not None or yRange is not None:
            # `padding=0.`, measured: what the file holds is the range that was on
            # screen, and pyqtgraph pads a *requested* range by `suggestPadding` --
            # asking this box for [0, 1] answers [[-0.0416, 1.0416], ...]. Re-padding
            # a stored view would widen the window a little at every save and restore.
            box.setRange(xRange=xRange, yRange=yRange, padding=0.,
                         disableAutoRange=True)
        if state.xInverted:
            box.invertX(True)
        if state.yInverted:
            box.invertY(True)

    @staticmethod
    def viewBoxOf(frame):
        """The one view box of a curve figure, or None for the other windows."""
        if not isinstance(frame, QVizCurvePlot):
            return None
        return frame.pgPlotWidget.getViewBox()

    def applyWindow(self, figure, frame, view):
        """Where the window sat, whether it was maximized, whether it was hidden.

        `setGeometry` then `showMaximized` then `hide`: measured off screen, the
        four numbers round-trip unchanged, a maximized window answers its geometry
        back after a `showNormal`, and a window hidden here stays addressable by
        its key in the Show/Hide menu -- hidden is not closed.
        """
        state = figure.window
        if state is None:
            return
        window = self.api.mdiWindowOf(frame)
        if window is None:
            logging.getLogger(view.uri).warning(
                'The figure "%s" of "%s" says where its window sat: that window is '
                'not in the MDI area.' % (figure.key, self.path))
            return
        window.setGeometry(state.x, state.y, state.w, state.h)
        if state.maximized:
            window.showMaximized()
        if state.hidden:
            window.hide()

    # ---------------------------------------------------------- plugin windows
    def replayPluginWindows(self, session, views):
        """Ask each case's own Plugins menu the entry that drew one of its windows.

        Answers how many windows came back. A plugin window is not drawn by a
        command of this module: it is replayed through the catalog of the view the
        user right-clicked, so the window that comes back owns its tabs, its time
        slider and its line in the Show/Hide menu -- and it comes back under the
        key of the file, because the answers handed to the entry carry it and the
        plugin gives it to `FigureKeyFor`.
        """
        restored = 0
        for case in session.cases:
            if not case.pluginWindows:
                continue
            view = views.get(case.uri)
            for window in case.pluginWindows:
                if view is None:
                    logging.getLogger('logPanel').error(
                        'The plugin window "%s" named by "%s" is not drawn: the '
                        'case "%s", whose Plugins menu offers the %s entry of '
                        'plugin %s, is not open.'
                        % (window.key, self.path, case.uri, window.entry,
                           window.plugin))
                    continue
                if self.restorePluginWindow(window, view):
                    restored += 1
        return restored

    def restorePluginWindow(self, window, view):
        """Replay one entry of that view's catalog, answering it for the user.

        Whether the window came back is read from `figureframes`, not assumed:
        an entry can be offered and still draw nothing -- its case may be missing
        what it needs, and the Profiles plugin logs a warning of its own and
        returns when it finds no profiles. Counting the asks instead would report
        a window that is not on screen.
        """
        from imasviz.VizPlugins.QVizPluginCatalog import QVizPluginCatalog
        from imasviz.VizPlugins.VizPlugin import QVizPluginAnswers

        node = view.IDSRoots.get(window.ids)
        if node is None:
            logging.getLogger(view.uri).error(
                'The plugin window "%s" named by "%s" is not drawn: the %s IDS '
                'has no branch in the tree of %s, and the %s entry of plugin %s '
                'is offered on that branch.'
                % (window.key, self.path, window.ids, view.uri, window.entry,
                   window.plugin))
            return False

        # The same catalog the right click builds, taken from the view when it is
        # already there so the plugins of a view are not imported and built twice.
        catalog = getattr(view, 'pluginCatalog', None)
        if catalog is None:
            catalog = QVizPluginCatalog(view)
            view.pluginCatalog = catalog

        offered = catalog.entriesFor(node)
        entry = next((candidate for candidate in offered
                      if candidate.pluginName == window.plugin
                      and candidate.number == window.entry), None)
        if entry is None:
            logging.getLogger(view.uri).error(
                'The plugin window "%s" named by "%s" is not drawn: the tree of '
                '%s offers %s for the %s IDS, which holds no %s entry of plugin '
                '%s.'
                % (window.key, self.path, view.uri,
                   'nothing' if not offered else
                   ' / '.join('%s entry %s' % (one.pluginName, one.number)
                              for one in offered),
                   window.ids, window.entry, window.plugin))
            return False

        catalog.run(entry, answers=QVizPluginAnswers(
            occurrence=window.occurrence, figureKey=window.key))
        if window.key not in self.api.figureframes:
            logging.getLogger(view.uri).error(
                'The %s entry of plugin %s was asked for the window "%s" of "%s" '
                'and drew nothing: the reason is in the line above, from the '
                'plugin itself.'
                % (window.entry, window.plugin, window.key, self.path))
            return False
        return True

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
