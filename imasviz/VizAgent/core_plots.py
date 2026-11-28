# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The plotting gestures of one IMASViz session: the one quantity drawn, the slices, the equilibrium windows and the raw read.

One quantity, one slice of one quantity and the equilibrium surfaces are drawn through the application's own commands; `get_signal` is the one read every other surface asks for. A refusal is the named `ValueError` the caller gets back.
"""

from imasviz.VizAgent.core import _axisName, _axisWords, axesAddressing

class PlotOps:
    """The drawing path: the one quantity, the slices, the equilibrium windows."""

    def _scalarRefusal(self, path):
        """The named refusal a scalar leaf earns on the tool path.

        It says what the leaf is, and points at the sibling that is the
        curve, because that is the answer that ends a retry loop: the panel's
        "has no explicit dependency on current X axis" names a widget the
        agent does not have, and a model reads it as "no data" and asks again.
        """
        return ('"%s" is a scalar -- one value per element of its array, '
                'not a curve of time or coordinate. inspect_tree('
                'action="search") marks the curves with "kind": "curve"; '
                'for a leaf like this the sibling "…/data" under the same '
                'array element is usually the one a plot wanted.' % path)

    def _embedIfNew(self, command, frame):
        """A frame the command opened is embedded and shown; a joined one is not.

        The rule the pop-up menu applies (`QVizSignalHandling.plotNodeCommand`):
        embedding twice puts one window inside two subwindows, and showing a
        joined figure is what its own owner did.
        """
        if frame is None:
            return
        if getattr(command, 'builtFigure', False):
            self.api.addPlotWidgetToMDI(frame)
            frame.show()

    def _asInstant(self, time, what):
        """`time` is one instant: a number, in seconds on the case clock.

        A list of them is the ask the model reaches for on "j_tor(psi) at
        100, 400, 700s" -- the working shape is `mode="slices"` with
        `times`, one trace per instant on one figure. Refuse the list by
        naming that, not as the `float() ... not 'list'` the loop reads as
        a wrong value and retries into the budget. A bare index of the
        time array belongs in `indices`, not in `time`.
        """
        if isinstance(time, bool) or not isinstance(time, (int, float)):
            raise ValueError(
                '%s: `time` is one instant, a number in seconds on the case '
                'clock. For several instants of the same profile on one '
                'figure, use mode="slices" with `times` -- e.g. times=[100, '
                '400, 700] -- which draws one trace per instant into one '
                'figure; a bare index of the time array belongs in `indices`, '
                'not in `time`.' % what)
        return float(time)

    def _filledSiblings(self, view, node, cap=8):
        """The filled siblings of a leaf, under the same structure, by name.

        Read off the tree's own available-data flag -- the one the tree
        settles by **reading** each leaf at build time, so a 0-length array
        is already known to be empty -- not off `list_filled_paths`, which
        names a 0-length array as filled (measured: it lists `j_tor` while
        `j_tor` reads 0), the exact shape of the empty leaf this points at.
        """
        dataName = node.getDataName() or ''
        if '.' not in dataName:
            return []
        prefix = dataName.rsplit('.', 1)[0] + '.'
        clean, band = [], []
        for other in view.signalsList:
            name = other.getDataName() or ''
            if not name.startswith(prefix) or '.' in name[len(prefix):]:
                continue
            short = name[len(prefix):]
            if name == dataName:
                continue
            try:
                if not other.hasAvailableData():
                    continue
            except Exception:
                continue
            # The `_error_` bounds are a band on another profile, not the
            # profile the ask named: list the clean profiles first, so the
            # pointer lands on pressure / q / elongation, not on a band.
            (band if '_error_' in short else clean).append(short)
        return (sorted(clean) + sorted(band))[:cap]

    def _emptyExplanation(self, view, node, path):
        """A leaf that holds no values earns a refusal that says so, and
        points at what the case DOES hold under the same structure.

        "No values along the plotted axis" is a widget phrase the model reads
        as a wrong axis and retries, and then -- when it stops -- as a table
        it put together from the filled coordinate and invented values. These
        words name the emptiness as the case's own and the siblings that are
        filled, so the answer ends the loop instead of steering it into a
        fabrication.
        """
        message = ('%s holds no values in this case (the leaf is empty), so '
                   'there is nothing to draw and no index or instant to pin '
                   'it at' % path)
        filled = self._filledSiblings(view, node)
        if filled:
            message += ('. Under the same structure the case DOES hold: %s.'
                        % ', '.join('"%s"' % name for name in filled))
        else:
            message += ('. Nothing under the same structure holds values '
                        'either; search_nodes names the leaves the case '
                        'fills.')
        return message

    def plot_one(self, uri, path, along_time=None, into_figure_key=None,
                 time=None, time_interp=False, along=None, indices=None):
        """One quantity, drawn by `QVizPlotOneNode` into the frame its axes call for.

        `along_time` is None for no opinion, which leaves the figure's own
        rule standing; the read that cannot answer is named out of the
        case's log, because the command logs it there and returns nothing.

        `along` and `indices` are the one shared schema (`axesAddressing`, the
        same path `get_signal` takes): `along` is the axis the quantity runs
        along, `indices` fixes each other axis by name at its index. When they
        are named, the figure opens **at** those indices: the abscissa is the
        one the resolver settles, and the frame's slice controls are put on the
        indices the user named rather than the ones the tree happened to carry.
        That is the half of the unified schema the user asked for that was
        missing -- before it, the numbers `get_signal` answered (element at
        index 50) and the figure `plot_one` opened (slider at 0) could be two
        different elements of the same array.

        `time` pins a single slice of a quantity held by a dynamic time array
        (e.g. `time_slice[i]`). The value of that slice is answered by
        `plot_slice`, which reads it through the Access Layer's own
        `DBEntry.get_slice` — the ONE interpolation the two surfaces share,
        so `plot_one` no longer carries a second, manual two-slice lerp of
        its own. `time_interp` only picks the primitive it asks
        (`LINEAR_INTERP` for the value at the exact time, `CLOSEST_INTERP`
        for the slice the case holds nearest). `time_slice_time` is that
        slice's own time, and `time_slice_index` its index, so the answer
        names the slice the case answered with and not the value asked.
        `along_time` and `time` are refused together: one draws every slice,
        the other pins one.
        """
        if time is not None and (along_time or along is not None
                                 or indices is not None):
            raise ValueError(
                'plot_one: along_time / along / indices and time are '
                'contradictory readings of the same array: the first runs '
                'the quantity along an axis at a named index, the second '
                'pins one slice at a clock value. Drop one of the two and '
                'ask only for the other.')
        if along is not None or indices is not None:
            return self._plotOneAddressed(uri, path, along, indices,
                                          into_figure_key=into_figure_key)
        view = self._viewForUri(uri)
        node = self._nodeForPath(view, path)
        if self._leafKind(node) == 'scalar':
            # A scalar with no abscissa at all is refused before the command
            # logs the panel's "no explicit dependency on current X axis" and
            # returns nothing -- the agent gets the answer and the pointer to
            # the curve at once, not an opaque line to retry against. This
            # also fires before the time-slice resolution below: a scalar
            # has no dynamic time array to pin a slice in.
            raise ValueError(self._scalarRefusal(path))
        if time is not None:
            import numpy as np
            T = self._asInstant(time, 'plot_one')
            node = self._nodeForPath(view, path)
            tbase = self._timeBase(view, node)
            if tbase is None or tbase.size == 0:
                raise ValueError(
                    'plot_one: %r has no time axis to pin to %g: '
                    'the time parameter applies to a quantity held by a '
                    'dynamic time array (e.g. time_slice[i]); this one is '
                    'not, so a time value there has no slice to resolve to.'
                    % (path, T))
            time_index = int(np.argmin(np.abs(tbase - T)))
            clamped = bool(T < float(tbase[0]) or T > float(tbase[-1]))
            # The value is answered the same way plot_slice answers one:
            # through `DBEntry.get_slice`, with `time_interp` only choosing
            # between the Access Layer's LINEAR_INTERP and CLOSEST_INTERP.
            result = self.plot_slice(
                uri, path, T,
                interpolation='linear' if time_interp else 'closest',
                into_figure_key=into_figure_key)
            result['drawing'] = True
            result['time_slice_index'] = time_index
            result['time_interp'] = bool(time_interp) and not clamped
            return result

        from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode \
            import QVizPlotOneNode
        node = self._nodeForPath(view, path)
        command = QVizPlotOneNode(view, node,
                                  intoFigureKey=into_figure_key,
                                  alongTime=along_time)
        frame = command.execute()
        if frame is None:
            if not node.hasAvailableData():
                # The leaf is empty in this case (the tree settled that by
                # reading it): say so and name the filled siblings, instead
                # of the widget phrase that steers the model into a retry
                # loop and then a fabricated table.
                raise ValueError(self._emptyExplanation(view, node, path))
            raise ValueError(
                '"%s" could not be drawn: %s'
                % (path, self.lastLogLine(view) or 'see the log panel'))
        self._embedIfNew(command, frame)
        return {'figure': frame.figureKey,
                'kind': type(frame).__name__,
                'drawing': bool(frame.isDrawing()),
                'curves': self._figureCurves(frame)}

    def _plotOneAddressed(self, uri, path, along, indices, into_figure_key=None):
        """`plot_one` through the shared resolver.

        The figure is built by `QVizPlotOneNode` with the abscissa the resolver
        settles, and opened at the indices the resolver fixed -- the same two
        halves `get_signal` uses for its numbers. So the element the numbers
        name and the element the slider sits on are the same element of the
        same array, whatever the depth of the nesting of arrays of structures
        between them (the resolver walks the tree, and every axis it does not
        draw earns a control).

        A quantity the resolver refuses (scalar, ambiguous axis, index past
        the extent the tree names, an axis it already runs along) is refused
        in words before the figure is opened.

        Only a family member the caller fixed through `indices` needs a control
        on the frame: the members the path itself picked carry no band by
        design, and drawing the member along its OWN coordinate (`along`
        named by the leaf's axis) is the read the twin `get_signal` already
        answers, not a contradiction. A coordinate of the leaf itself that the
        caller named needs no control either -- the frame pins that row at the
        index named, because the index is the ask. When a named member has no
        control to hold it, the refusal closes the figure the attempt opened
        before it is raised: a refusal costs no window, and the number that key
        has gone back to the bookkeeping.
        """
        from imasviz.VizDataAccess.QVizAxesSpec import QVizAxesSpec, QVizAxis
        from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode \
            import QVizPlotOneNode

        view = self._viewForUri(uri)
        node = self._nodeForPath(view, path)
        if self._leafKind(node) == 'scalar':
            raise ValueError(self._scalarRefusal(path))
        axesSpec = QVizAxesSpec.fromTreeNode(node)
        _abscissa, as_function_of_time, slices = axesAddressing(
            axesSpec, along=along, indices=indices)
        # The axes the caller fixed, by key and the value it fixed them at:
        # what the row is pinned at, whichever of the figure's rows it is. The
        # reported bug was the first of several psi slices of one pressure
        # keeping the figure's shared psi control while the later ones were
        # frozen: the control then moved exactly the curve the ask had pinned.
        named = set()
        for word in (indices or {}):
            w = str(word).strip().lower()
            for axis in axesSpec.axes:
                if w in _axisWords(axis):
                    named.add(axis.key())
        named_indices = {key: index for key, index in (slices or {}).items()
                         if key in named}
        command = QVizPlotOneNode(view, node, intoFigureKey=into_figure_key,
                                  alongTime=as_function_of_time,
                                  namedIndices=named_indices or None)
        frame = command.execute()
        if frame is None:
            if not node.hasAvailableData():
                # The leaf is empty in this case (the tree settled that by
                # reading it): say so and name the filled siblings, instead
                # of the widget phrase that steers the model into a retry
                # loop and then a fabricated table.
                raise ValueError(self._emptyExplanation(view, node, path))
            raise ValueError(
                '"%s" could not be drawn: %s'
                % (path, self.lastLogLine(view) or 'see the log panel'))
        self._embedIfNew(command, frame)

        controls = getattr(frame, 'sliceControls', None)
        wordByKey = {axis.key(): str(_axisName(axis)) for axis in axesSpec.axes}
        originByKey = {axis.key(): axis.origin for axis in axesSpec.axes}
        openedAt = {}
        for key, index in (slices or {}).items():
            if key not in named:
                continue
            word = wordByKey.get(key, str(key))
            # A coordinate of the leaf the caller named is pinned at that index
            # by the frame itself (`QVizCurvePlot._pinning`), so it is answered
            # without asking the band for it: the index is the ask, and a slider
            # that could move it afterwards would undo the ask.
            if originByKey.get(key) == QVizAxis.LEAF:
                openedAt[word] = index
            elif controls is not None and controls.setIndex(key, index):
                openedAt[word] = index
            else:
                if getattr(command, 'builtFigure', False):
                    # A refusal is not a ghost window: the figure the attempt
                    # opened goes away again, and the key it consumed goes
                    # back to the bookkeeping, instead of reappearing as a
                    # window `list_windows` reports that was never on
                    # screen and a number the next figure skips over.
                    self.api.closeWindow(frame)
                raise ValueError(self._elementIsThePathRefusal(path, word))
        return {'figure': frame.figureKey,
                'kind': type(frame).__name__,
                'drawing': bool(frame.isDrawing()),
                'opened_at': openedAt,
                'curves': self._figureCurves(frame)}

    def _elementIsThePathRefusal(self, path, word):
        """The one axis a family member fixes is not a slider to move: the
        member is the path.

        A single element of a family (`flux_loop[2]`, `bpol_probe[7]`) is its
        own leaf, drawn on a figure that has no band for that family -- the
        element is fixed by the path, so `setIndex` cannot move it. This is
        the one a refusal has to steer off: the previous word, "name a
        different one", is what made the model retry the same refused call into
        the turn budget, and it is false anyway, because a single element has
        no "different one" to name. The move is the OTHER member's path.
        """
        return (
            '"%s" already picks %s by its path: this figure draws that one '
            'member as its own curve, and the family %s has no slider here to '
            'move to a different index. A family member is named by its own '
            'path, not by indices: for another member, draw its own path with '
            'plot(mode="single") (with into_figure_key to put it in this '
            'figure) or manage_selection(action="select") the two '
            'members and plot(mode="selection"). Change the call; '
            'repeating the refused one will not help.'
            % (path, word, word))

    def _timeBase(self, view, node):
        """The dynamic time array's own time values, or None.

        Read from the reader, not cached: one read per ask is acceptable
        because the reader does not touch the leaf; it walks the node to
        find the time base and answers it. None is the refusal signal.
        """
        import numpy as np
        from imasviz.VizDataAccess.QVizAxesSpec import QVizAxesSpec
        from imasviz.VizDataAccess.QVizTensorExtractor import QVizTensorExtractor
        tb = QVizTensorExtractor(node.getIDSRef()).timeBase(
            QVizAxesSpec.fromTreeNode(node))
        if tb is None:
            return None
        return np.asarray(tb, dtype=float)

    _INTERPOLATIONS = {
        'linear':   'LINEAR_INTERP',
        'previous': 'PREVIOUS_INTERP',
        'closest':  'CLOSEST_INTERP',
    }

    def _sliceWalk(self, objs, relpath):
        """Resolve a bracket-path like `profiles_1d[0].electrons.temperature`
        into a struct array, honoring `[i]` indexes as getitem calls.
        """
        obj = objs
        for part in relpath.split('.'):
            if '[' in part:
                name, idx = part.split('[', 1)
                idx = int(idx.rstrip(']'))
                obj = getattr(obj, name)[idx]
            else:
                obj = getattr(obj, part)
        return obj

    def _profileAtTime(self, view, node, T, interp, occurrence,
                       what='plot_slice', time_index=None):
        """The (x, y(T)) pair of one 1D-profile leaf read through `DBEntry.get_slice`.

        `x` is the coordinate (time-independent, the same reader `plot_one`
        uses to draw a curve, read at `time_index` -- the slice the case
        answered with, so a profile whose grid moves with the slice cannot
        be drawn on the grid of the first one); `y(T)` comes from the HLI's
        own `get_slice(ids, T, interp, occurrence)` call. This is the ONE
        path `plot_slice` and `plot_slices` use, so the two surfaces share
        one implementation of "the profile at a time" rather than
        carrying two.

        Refuses by name when the leaf is not a 1D profile (a scalar, a
        tensor, or a leaf whose x and y sizes disagree).
        """
        import numpy as np
        leafPath = node.getDataName() or ''
        ids, dot, rel = leafPath.partition('.')
        if not dot or not rel:
            raise ValueError(
                '%s: %r is not a leaf of an IDS: '
                'the path must name an IDS root and a leaf, e.g. '
                '`equilibrium.time_slice[0].f`.' % (what, leafPath))
        entry = view.dataSource.db_entry
        try:
            slice_ids = entry.get_slice(ids, float(T), int(interp), int(occurrence))
        except Exception as e:
            raise ValueError(
                '%s: `get_slice(%r, %g, interp=%d, occ=%d)` refused '
                'by the Access Layer: %s'
                % (what, ids, float(T), int(interp), int(occurrence),
                   str(e).split('\n', 1)[0])[:300])
        slice_time = float(getattr(slice_ids, 'time', [T])[0])
        if time_index is None:
            # The coordinate is read at the slice the case answered with,
            # not at the first one: a profile whose grid moves with the
            # time would be drawn on the wrong grid otherwise.
            tbase = self._timeBase(view, node)
            if tbase is not None and tbase.size > 0:
                time_index = int(np.argmin(np.abs(tbase - slice_time)))
            else:
                time_index = 0
        try:
            y_raw = self._sliceWalk(slice_ids, rel)
        except Exception as e:
            raise ValueError(
                '%s: %r is not a 1D profile of %r in the case: %s'
                % (what, leafPath, ids, str(e).split('\n', 1)[0])[:300])
        # A 1D profile leaf reads one coordinate and one value per point;
        # get_slice answers it as a flat array, and both must be non-empty.
        y = np.asarray(y_raw, dtype=float).ravel()
        if y.size == 0:
            if not node.hasAvailableData():
                # The leaf is empty in this case: say so and name the filled
                # siblings, instead of the branch-is-empty phrase that leaves
                # the model to read "directly" and invent.
                raise ValueError(self._emptyExplanation(view, node, leafPath))
            raise ValueError(
                '%s: %r holds no value at this instant in the case: '
                'the branch is empty, so there is nothing to draw.'
                % (what, leafPath))
        from imasviz.VizDataAccess.QVizTensorDataAccess import QVizTensorDataAccess
        try:
            x_raw, _ = QVizTensorDataAccess(view.dataSource).GetSignal(
                treeNode=node, plotWidget=None,
                as_function_of_time=False, time_index=time_index)
        except Exception as e:
            raise ValueError(
                '%s: %r is not read as a curve by the reader: %s'
                % (what, leafPath, str(e).split('\n', 1)[0])[:300])
        # The reader's own convention for a curve figure is a (rows, N) pair,
        # one row per trace; ravel to (N,) so the check and the draw treat
        # both as one coordinate and one value per point.
        x = np.asarray(x_raw, dtype=float).ravel()
        if x.size != y.size:
            raise ValueError(
                '%s: %r reads %d coordinates and %d values — not a '
                '1D profile leaf (one coordinate and one value per point). '
                'A 2D leaf is drawn as a picture, a 0D scalar as a point; '
                'neither is what this entry takes.'
                % (what, leafPath, x.size, y.size))
        return x, y, slice_time

    def plot_slice(self, uri, leaf, time, occurrence=0, interpolation='linear',
                   into_figure_key=None):
        """One 1D-profile leaf of one IDS, drawn at a single time through `DBEntry.get_slice`.

        The HLI's `get_slice(ids, time, interp, occurrence)` does the
        interpolation at its end — the values are what the Access Layer
        answers, not a manual lerp in the GUI process. The coordinate is
        read from the same reader `plot_one` uses, so the two share ONE
        implementation of "the profile at a time".

        `interpolation` is one of 'linear' (default; `LINEAR_INTERP`,
        the value at the exact `time`), 'closest' (`CLOSEST_INTERP`,
        the case's own slice nearest to `time`) or 'previous'
        (`PREVIOUS_INTERP`, the one at or before `time`).

        The answer names the figure, `time_slice_time` (the value the
        slice itself holds — equals `time` for 'linear', and the case's
        own slice time otherwise), and how many points the profile holds.
        """
        if interpolation not in self._INTERPOLATIONS:
            raise ValueError(
                'plot_slice: interpolation must be one of %s, got %r.'
                % (', '.join(sorted(self._INTERPOLATIONS)), interpolation))
        import imas.ids_defs as _id
        interp = getattr(_id, self._INTERPOLATIONS[interpolation])

        view = self._viewForUri(uri)
        node = self._nodeForPath(view, leaf)
        leaf = node.getDataName() or leaf
        ids = leaf.split('.', 1)[0]
        if not self.api.IDSDataAlreadyFetched(view, ids, occurrence):
            self.load_ids(uri, ids, occurrence)
        # A time outside the case's own range answers the nearest slice the
        # case holds (the last, or first), not a refusal and not an echo of
        # the ask: the answer reports `time_requested` and `time_slice_time`
        # separately, so a value asked far outside the pulse is still named
        # as the slice the case actually answered with.
        T = self._asInstant(time, 'plot_slice')
        tbase = self._timeBase(view, node)
        if tbase is not None and tbase.size > 0:
            T = float(min(max(T, float(tbase[0])), float(tbase[-1])))
        x, y, slice_t = self._profileAtTime(view, node, T, interp, occurrence,
                                            'plot_slice')

        # Draw into a `Plot:` figure (the same kind `plot_one` uses) so
        # the *Windows* menu, sessions, and `saveShots` all reach it.
        # Refused by name when a non-curve figure is named by key.
        from imasviz.VizUtils import FigureTypes
        from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode \
            import QVizPlotOneNode
        from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
        if into_figure_key is not None:
            command = QVizPlotOneNode(view, node, intoFigureKey=into_figure_key)
            frame = command.frameFor()
            if not hasattr(frame, 'pgPlotWidget'):
                command.discardIfEmpty(frame)
                raise ValueError(
                    'plot_slice: %r is not a `Plot` figure: name a curve '
                    'figure (see list_windows), e.g. Plot1.' % into_figure_key)
        else:
            command = QVizPlotOneNode(view, node)
            frame = command.newFigure(FigureTypes.CURVEPLOTTYPE, QVizCurvePlot)

        # A slice draws like any other trace: one colour per trace from
        # the house palette, continuing the cycle where the figure left
        # it, or the ground is black for every trace and the slices of
        # one profile are indistinguishable. The count is taken off the
        # widget, not the frame's own bookkeeping, because the traces a
        # slice draws are not QVizTrace -- they are static reads, not
        # curves a slider can follow -- and are not in frame.curves().
        from imasviz.VizGUI.VizPlot.QVizCurveColors import penFor
        existing = len(frame.pgPlotWidget.getPlotItem().listDataItems())
        frame.pgPlotWidget.plot(x, y, name=leaf, pen=penFor(existing))
        frame.pgPlotWidget.setLabel('bottom', 'coordinate')
        frame.pgPlotWidget.setLabel('left', leaf)
        frame.pgPlotWidget.setTitle(
            'slice of %s at t=%g (%s)' % (leaf, slice_t, interpolation))

        self._embedIfNew(command, frame)
        self.api.AddNodeToFigure(
            frame.figureKey,
            view.dataSource.dataKey(node),
            (view.dataSource.uri, node))
        return {'figure': frame.figureKey,
                'drawn': int(len(x)),
                'time_requested': T,
                'time_slice_time': slice_t,
                'interpolation': interpolation,
                'kind': type(frame).__name__}

    def plot_slices(self, uri, path, times, occurrence=0, interpolation='linear',
                     into_figure_key=None):
        """One 1D-profile leaf of one IDS, drawn at several instants on ONE figure.

        The one shape the ask "j_tor(psi) at t=100, 400, 700 on the same
        figure" needs: one call, one window of curves, one trace per
        instant, named for the slice it shows. Each instant resolves to
        the case's own slice nearest to it (clamped to the case's range),
        read through the same `DBEntry.get_slice` as `plot_slice` -- the
        values are what the Access Layer answers, not a manual lerp, and
        the coordinate is read at the slice the case answered with.

        A leaf that holds no values answers ONE refusal, before any window
        is opened, naming the instants asked and the filled siblings under
        the same structure. An instant the case refuses is named in the
        answer (one reason per instant, never a retry that eats the turn
        budget); the call succeeds as long as one of them drew. The caller
        is the one that says what the failure means, never this gesture.
        """
        import numpy as np
        if isinstance(times, bool) or not isinstance(times, (list, tuple)):
            if isinstance(times, (int, float)):
                times = [times]
            else:
                raise ValueError(
                    'plot_slices: `times` is the list of instants (seconds '
                    'on the case clock), e.g. times=[100, 400, 700], was %r.'
                    % (times,))
        if len(times) == 0:
            raise ValueError(
                'plot_slices: `times` must name at least one instant, '
                'got an empty list.')
        for entry in times:
            if isinstance(entry, bool) or not isinstance(entry, (int, float)):
                raise ValueError(
                    'plot_slices: every instant in `times` must be a number '
                    '(seconds on the case clock), was %r.' % (times,))
        times = [float(t) for t in times]
        if interpolation not in self._INTERPOLATIONS:
            raise ValueError(
                'plot_slices: interpolation must be one of %s, got %r.'
                % (', '.join(sorted(self._INTERPOLATIONS)), interpolation))
        import imas.ids_defs as _id
        interp = getattr(_id, self._INTERPOLATIONS[interpolation])

        view = self._viewForUri(uri)
        node = self._nodeForPath(view, path)
        leaf = node.getDataName() or path
        ids = leaf.split('.', 1)[0]
        if not self.api.IDSDataAlreadyFetched(view, ids, occurrence):
            self.load_ids(uri, ids, occurrence)

        kind = self._leafKind(node)
        if kind == 'scalar':
            raise ValueError(self._scalarRefusal(path))
        if kind == 'image':
            raise ValueError(
                'plot_slices: %r is a two-dimension leaf, not a 1D profile: '
                'draw it with plot(mode="single") -- a profile at several '
                'instants is a curve, not a picture.' % path)
        # The one refusal the ask asks for: a leaf that holds nothing in
        # this case is named once, with the instants asked and the filled
        # siblings, before any window is opened.
        if not node.hasAvailableData():
            instants = ', '.join('t=%g s' % t for t in times)
            raise ValueError(
                'plot_slices: %s (asked for: %s).'
                % (self._emptyExplanation(view, node, leaf).rstrip('.'),
                   instants))

        tbase = self._timeBase(view, node)
        entries = []
        for requested in times:
            clamped = bool(tbase is not None and tbase.size > 0 and
                           (requested < float(tbase[0]) or
                            requested > float(tbase[-1])))
            T = requested
            if tbase is not None and tbase.size > 0:
                T = float(min(max(requested, float(tbase[0])), float(tbase[-1])))
            try:
                x, y, slice_t = self._profileAtTime(view, node, T, interp,
                                                    occurrence, 'plot_slices')
            except ValueError as e:
                entries.append({'time_requested': requested,
                                'clamped': clamped,
                                'error': str(e)})
                continue
            k = 0
            if tbase is not None and tbase.size > 0:
                k = int(np.argmin(np.abs(tbase - slice_t)))
            entries.append({'time_requested': requested,
                            'time_slice_time': slice_t,
                            'clamped': clamped,
                            'slice_index': k,
                            'drawn': int(len(x)),
                            'samples': int(len(y)),
                            'x': x, 'y': y})

        drawn = [entry for entry in entries if 'error' not in entry]
        if not drawn:
            reasons = '; '.join('t=%g s: %s' % (entry['time_requested'],
                                                entry['error'])
                                for entry in entries)
            raise ValueError(
                'plot_slices: none of the %d instants asked gave a profile '
                'for %r: %s' % (len(entries), leaf, reasons))

        leaf_short = leaf.split('.', 1)[1] if '.' in leaf else leaf
        import re
        leaf_short = re.sub(r'\[[^\]]*\]', '', leaf_short)
        instants_text = ', '.join('t=%g s' % t for t in times)

        from imasviz.VizUtils import FigureTypes
        from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode \
            import QVizPlotOneNode
        from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
        if into_figure_key is not None:
            command = QVizPlotOneNode(view, node, intoFigureKey=into_figure_key)
            frame = command.frameFor()
            if not hasattr(frame, 'pgPlotWidget'):
                command.discardIfEmpty(frame)
                raise ValueError(
                    'plot_slices: %r is not a `Plot` figure: name a curve '
                    'figure (see list_windows), e.g. Plot1.' % into_figure_key)
        else:
            command = QVizPlotOneNode(view, node)
            frame = command.newFigure(FigureTypes.CURVEPLOTTYPE, QVizCurvePlot)

        try:
            # One colour per trace, continuing the cycle where the figure
            # left it (a figure the slice drew into holds the counts of its
            # own curves and the traces earlier slices laid down -- both
            # are on the widget, so the widget is the count that sees
            # both). Traces drawn here are static reads, not curves a
            # slider follows: they are not QVizTrace and are not in
            # frame.curves(), which is why the count is taken off the
            # widget.
            from imasviz.VizGUI.VizPlot.QVizCurveColors import penFor
            existing = len(frame.pgPlotWidget.getPlotItem().listDataItems())
            for i, entry in enumerate(drawn):
                entry['trace'] = '%s @ t=%g s' % (leaf_short,
                                                  entry['time_slice_time'])
                frame.pgPlotWidget.plot(entry['x'], entry['y'],
                                        name=entry['trace'],
                                        pen=penFor(existing + i))
            frame.pgPlotWidget.setLabel('bottom', 'coordinate')
            frame.pgPlotWidget.setLabel('left', leaf_short)
            if not into_figure_key:
                frame.pgPlotWidget.setTitle(
                    'profile of %s at %s' % (leaf_short, instants_text))
        except Exception as e:
            command.discardIfEmpty(frame)
            raise ValueError(
                'plot_slices: could not draw %s onto the figure: %s'
                % (leaf, str(e).split('\n', 1)[0])[:300])

        self._embedIfNew(command, frame)
        self.api.AddNodeToFigure(
            frame.figureKey,
            view.dataSource.dataKey(node),
            (view.dataSource.uri, node))
        return {'figure': frame.figureKey,
                'kind': type(frame).__name__,
                'interpolation': interpolation,
                'occurrence': occurrence,
                'drawn': sum(entry['drawn'] for entry in drawn),
                'traces': [{key: value for key, value in entry.items()
                            if key not in ('x', 'y')}
                           for entry in entries]}

    def _equilibriumRead(self, uri, occurrence):
        """The `(view, reader)` of the `equilibrium` IDS of one open case.

        The read is the IDS-object read (the same as the Equilibrium
        plugin), so it does not walk the tree and costs one lazy `get`;
        a case that holds no `equilibrium` IDS refuses by naming its own.
        """
        view = self._viewForUri(uri)
        if 'equilibrium' not in view.IDSRoots:
            raise ValueError(
                '%s holds no equilibrium IDS, so there is no flux surface '
                'to draw: manage_idss(action="filled") names the IDS this '
                'case does hold.'
                % uri)
        from imasviz.VizDataAccess.QVizEquilibriumRead import \
            QVizEquilibriumRead
        return view, QVizEquilibriumRead(view.dataSource, occurrence)

    def _newEquilibriumFigure(self, view, figure_key=None, reuse=False):
        """The `EquiSurfaces:` frame this read is drawn into.

        Allocated through `QVizPlotOneNode.newFigure` because that is the
        one place a key is handed out against the api's own bookkeeping
        (`figureframes`), which is what the *Windows* menu, its *Delete*
        sub-menu, the sessions and `list_windows` read. `figure_key` is the
        key a session replay names: `newFigure` honours it through
        `FigureKeyFor` (refusing a key a live window already holds), so the
        window comes back under the name the file said rather than a new one.

        `reuse=True` says that key names a window that already stands and is
        to be drawn *again*: `FigureKeyFor` refuses a held key on purpose (two
        windows under one name is how a *Windows* menu line comes to reach
        nothing), so the redraw goes around it -- the key, the place on screen
        and the menu line stay put, which is what "the same figure" means to
        whoever is looking. What the window holds is taken back by the caller
        just before the new row goes down, never here: a read that answers
        nothing must leave the window it was asked to redraw exactly as it was.
        A key naming a window of another kind is refused rather than painted over.
        """
        from imasviz.VizUtils import FigureTypes
        from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode \
            import QVizPlotOneNode
        from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizEquilibriumFigure \
            import QVizEquilibriumFigure
        command = QVizPlotOneNode(view, view.IDSRoots['equilibrium'],
                                  figureKey=figure_key)
        if not reuse:
            frame = command.newFigure(FigureTypes.EQUISURFACES,
                                      QVizEquilibriumFigure)
            return command, frame
        if figure_key is None:
            raise ValueError('equilibrium: redrawing into a window needs the '
                             'key of the window to redraw into.')
        frame = self.api.figureframes.get(figure_key)
        if frame is None:
            raise ValueError('equilibrium: no open window named "%s" to draw '
                             'into.' % figure_key)
        if not isinstance(frame, QVizEquilibriumFigure):
            raise ValueError(
                'equilibrium: the window named "%s" is a %s, not the '
                'flux-surface window this read draws: ask a new window instead '
                'of drawing over it.' % (figure_key, type(frame).__name__))
        return command, frame

    def _equilibriumFrameDrawn(self, command, frame, what):
        """A frame the read left empty is taken back, naming the refusal."""
        if frame.isDrawing():
            return frame
        command.discardIfEmpty(frame)
        raise ValueError(
            'equilibrium: the read answered, but the window of %s holds no '
            'curve at all: the refusal above is the reason it is closed.'
            % what)

    def equilibrium_surfaces(self, uri, times, occurrence=0, figure_key=None,
                             reuse=False):
        """The flux surfaces of `equilibrium`, one frame per named instant.

        `times` is the list of instants asked (a single number is read as a
        list of one; each answers the case's own slice nearest to it, since
        a GGD grid is discrete and an interpolated surface is a drawing no
        one owns). The window is one of the application's own — an
        `EquiSurfaces:` key in `figureframes`, dressed on the black ground
        and the trace palette like a curve figure — with every frame on the
        same bounds, so the instants are compared at equal measure: the same
        levels, the same scale, the same marks (boundary, axis, O-point,
        limiter) at the instants named.

        `figure_key` names the window to draw into; `reuse=True` says that key
        is a window already on the screen, so its row is taken back and laid
        down again instead of a second window being opened beside it.
        """
        if times is None:
            raise ValueError(
                'equilibrium_surfaces: name the instants to draw -- '
                'times is the list of them, e.g. [40, 44, 48].')
        if isinstance(times, (int, float)):
            times = [times]
        try:
            times = [float(t) for t in times]
        except TypeError:
            raise ValueError(
                'equilibrium_surfaces: times must be a list of numbers '
                '(seconds in the case clock), was %r.' % (times,))

        view, reader = self._equilibriumRead(uri, occurrence)
        command, frame = self._newEquilibriumFigure(view, figure_key, reuse)
        try:
            surfaces = []
            frames = []
            for requested in times:
                index, sliceTime, clamped = reader.resolve(requested)
                surface = reader.surfaceAt(index)
                surface['time_slice_time'] = sliceTime
                surfaces.append(surface)
                frames.append({
                    'time_requested': requested,
                    'time_slice_time': sliceTime,
                    'slice_index': index,
                    'clamped': clamped,
                    'b0_T': surface['b0'],
                    'r0_m': surface['r0'],
                })
            # Only now, with every read in hand: a window redrawn into must not
            # lose what it held before a read that answers nothing.
            if reuse:
                frame.clearDrawings()
            frame.drawRow(surfaces, wall=reader.wall())
        except ValueError:
            command.discardIfEmpty(frame)
            raise
        self._equilibriumFrameDrawn(command, frame, 'the row')
        self._embedIfNew(command, frame)
        return {
            'figure': frame.figureKey,
            'kind': type(frame).__name__,
            'occurrence': occurrence,
            'frames': frames,
            'wall': reader.wall() is not None,
        }

    def equilibrium_at_time(self, uri, time, occurrence=0, figure_key=None,
                            reuse=False):
        """One instant of the equilibrium: its flux surface, its radial
        profiles under it, and its global quantities in the answer.

        The frame is the one the case answers for the instant -- `time`
        resolves to the nearest slice the case holds, named back through
        `time_requested` vs `time_slice_time` the way `plot_slice` says it
        -- and under the surface the stack holds, one panel per radial
        quantity the Equilibrium plugin draws (q, elongation,
        triangularities, j_tor, pressure, f_df_dpsi, dpressure_dpsi), all
        on the common abscissa the read settled (`rho_tor_norm`). The
        group pan is on for that abscissa (pan one, they all move), but the
        vertical range is NOT shared: the eight quantities span about four
        orders of magnitude, so a shared range would flatten the smallest
        under the first panel's scale and lift the largest off the screen
        (sharedY=False on the window's stack). The global quantities of the
        slice (Ip, q95, q_axis, li_3, W_mhd, axis position) are values of
        the answer, not a drawing: the window has no axis to spread a
        scalar over.
        """
        try:
            requested = float(time)
        except (TypeError, ValueError):
            raise ValueError(
                'equilibrium_at_time: time must be a number (seconds in the '
                'case clock), was %r.' % (time,))
        view, reader = self._equilibriumRead(uri, occurrence)
        index, sliceTime, clamped = reader.resolve(requested)
        surface = reader.surfaceAt(index)
        surface['time_slice_time'] = sliceTime
        profiles = reader.profilesAt(index)

        command, frame = self._newEquilibriumFigure(view, figure_key, reuse)
        try:
            if reuse:
                frame.clearDrawings()
            frame.drawRow([surface], wall=reader.wall())
            frame.drawProfiles(profiles['x'], profiles['x_label'], '',
                               profiles['profiles'])
        except ValueError:
            command.discardIfEmpty(frame)
            raise
        self._equilibriumFrameDrawn(command, frame, 'the figure')
        self._embedIfNew(command, frame)
        return {
            'figure': frame.figureKey,
            'kind': type(frame).__name__,
            'occurrence': occurrence,
            'time_requested': requested,
            'time_slice_time': sliceTime,
            'slice_index': index,
            'clamped': clamped,
            'b0_T': surface['b0'],
            'r0_m': surface['r0'],
            'wall': reader.wall() is not None,
            'abscissa': profiles['x_label'],
            'profiles': [name for name, _, _ in profiles['profiles']],
            'empty_profiles': profiles['empty'],
            'global': profiles['global'],
        }

    def plot_selection(self, uri):
        """The case's selection, drawn by `QVizPlotAsSlices` from this view alone.

        `all_DTV` stays False on purpose: `QVizPlotAsSlices` defaults to
        True, which draws the selection of every open view -- the seam the
        journey test in the suite pins, and not what "plot what I selected in
        this case" means.
        """
        view = self._viewForUri(uri)
        from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsSlices \
            import QVizPlotAsSlices
        command = QVizPlotAsSlices(view, all_DTV=False)
        frames = command.execute()
        for frame in frames:
            self.api.addPlotWidgetToMDI(frame)
        return {'figures': [frame.figureKey for frame in frames]}

    def plot_table(self, uri, paths, columns=None, plot_axis=None):
        """The named paths, one panel per quantity, in a Table Plot View.

        The window fills its panels from the case's selection, the way the
        manual's entry fills them -- so the named paths are selected first
        and left selected, `plot_stacked`'s reading of its own paths; a
        path the tree does not hold is refused by the selection with its
        name, before the window is opened.
        """
        view = self._viewForUri(uri)
        self.select_signals(uri, paths)
        from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsTable \
            import QVizPlotAsTable
        command = QVizPlotAsTable(view, all_DTV=False,
                                  plotAxis=plot_axis, columns=columns)
        frame = command.execute()
        if frame is not None:
            self.api.addPlotWidgetToMDI(frame)
        if frame is None:
            raise ValueError(
                'Nothing to plot: %s' % (self.lastLogLine(view)
                                         or 'the named quantities gave no '
                                            'value the panels can draw'))
        return {'figure': frame.figureKey,
                'panels': int(frame.panelCount())
                if hasattr(frame, 'panelCount') else None}

    def plot_stacked(self, uri, paths, plot_axis='TIME'):
        """The named paths, stacked one panel per quantity.

        The selection is what `QVizPlotAsStacked` reads, so the paths are
        selected first and left selected: the window's panels are filled
        from that state, and clearing it would take the panels with it.
        """
        view = self._viewForUri(uri)
        from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsStacked \
            import QVizPlotAsStacked
        self.select_signals(uri, paths)
        command = QVizPlotAsStacked(view, all_DTV=False, plotAxis=plot_axis)
        frame = command.execute()
        if frame is not None:
            self.api.addPlotWidgetToMDI(frame)
        if frame is None:
            raise ValueError(
                'Nothing to plot: %s' % (self.lastLogLine(view)
                                         or 'the named quantities gave no '
                                            'value the panels can draw'))
        return {'figure': frame.figureKey}

    def get_signal(self, uri, path, as_function_of_time=None,
                   coordinate_index=0, time_index=None,
                   along=None, indices=None):
        """The values the tree's read gives for one leaf, as JSON.

        The same read the plots use (`Viz_API.GetSignal`), so what comes
        back is exactly what a panel drew: the coordinate and value arrays
        for a slice, or the named coordinates and values for a quantity of
        more than one array.

        `along` is the axis the quantity runs along -- `None` for the one the
        quantity defaults to (its clock, when it has one), a clock word, or the
        name of the axis it can actually be read along. `indices` fixes each
        other axis of the quantity by name at its 0-based index: an array of
        structures (`time_slice`, `profiles_1d`, `ion`, ...) or a leaf
        coordinate (`psi`, ...); several nested arrays are each named and
        fixed on their own.

        Both are read through the one shared resolver `axesAddressing`
        (which `plot_one` uses too), so the value this answers and the element
        a figure of the same leaf draws are the same element of the same
        array. A word no axis answers is a refusal that names the axes the
        quantity holds, and an index past their extent is refused before the
        read is ever asked, not a silent 0.
        """
        view = self._viewForUri(uri)
        node = self._nodeForPath(view, path)
        if self._leafKind(node) == 'scalar':
            # Refused before the read, in words the agent can act on, rather
            # than the panel's "no explicit dependency on current X axis"
            # after it.
            raise ValueError(self._scalarRefusal(path))
        if along is not None or indices is not None:
            from imasviz.VizDataAccess.QVizAxesSpec import QVizAxesSpec

            axesSpec = QVizAxesSpec.fromTreeNode(node)
            abscissa, as_function_of_time, slices = \
                axesAddressing(axesSpec, along=along, indices=indices)
        else:
            abscissa, slices = None, None
        result = self.api.GetSignal(view, node,
                                    as_function_of_time=as_function_of_time,
                                    coordinate1_index=coordinate_index,
                                    time_index=time_index,
                                    slices=slices,
                                    abscissa=abscissa)
        payload = self._jsonable(result)
        if isinstance(payload, dict) and payload.get('kind') == 'curve':
            payload['samples'] = len(payload.get('y') or [])
            if payload['samples'] == 0 and not node.hasAvailableData():
                # The read is empty because the leaf holds no values in this
                # case, not because of a wrong axis or index: say so and name
                # the filled siblings, so a "read it directly" does not come
                # back as a table assembled from the filled coordinate and
                # invented values.
                payload['note'] = self._emptyExplanation(view, node, path)
        return payload

    def _figureCurves(self, frame):
        """The labels of every trace the window holds, in draw order --
        the list an answer is allowed to name the figure by: after a draw
        or a join it is what the window holds, read off the window's own
        trace list, not recalled. A trace that answers through a node is
        labelled like the curve family labels it, and a window that
        answers none is an empty list -- the curve family's refusal names
        the reason, this only says what is."""
        labels = []
        for source in self._sourcesOf(frame):
            for node, _rank, _item in self._tracesOf(source):
                if node is None:
                    continue
                label = self._nodeLabel(node)
                if label and label not in labels:
                    labels.append(label)
        return labels

    def lastLogLine(self, view=None):
        """The last non-empty line of a case's log panel; '' when there is none.

        The panel is on the frame (see `get_logs`), so it is the frame of that
        view that is asked.
        """
        frames = [frame for frame in self.api.DTVframeList
                  if view is None or frame.dataTreeView is view]
        if not frames:
            return ''
        panel = getattr(frames[-1], 'logWidget', None)
        if panel is None:
            return ''
        lines = [line for line in panel.toPlainText().splitlines()
                 if line.strip()]
        return lines[-1].strip('|').strip() if lines else ''

    def _jsonable(self, value):
        """The read's answer as JSON, without naming what it is first.

        `Viz_API.GetSignal` answers a pair of arrays for a curve, and one
        of the `QVizDataArrayHandle` of the read for a quantity the plot
        frames lay out; both are reduced here to what a document can carry.
        """
        from imasviz.VizEntities.QVizDataArrayHandle import \
            QVizDataArrayHandle

        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, QVizDataArrayHandle):
            dimensions = int(value.getArrayDimension() or 0)
            return {
                'kind': 'handle',
                'name': value.getName(),
                'label': value.getLabel(),
                'dimensions': dimensions,
                'coordinates': [
                    {'dimension': i + 1,
                     'path': value.getCoordinatePath(i + 1),
                     'label': value.getCoordinateLabel(i + 1),
                     'values': self._jsonable(value.getCoordinateValues(i + 1))}
                    for i in range(dimensions)],
                'values': self._jsonable(value.arrayValues),
                'itime': value.itimeValue,
            }
        if hasattr(value, 'tolist'):
            return value.tolist()
        if isinstance(value, tuple):
            if len(value) == 2:
                x, y = value
                if not (hasattr(x, 'tolist') and hasattr(y, 'tolist')):
                    return [self._jsonable(part) for part in value]
                # The read wraps a curve in `[1, N]`; a curve is one
                # dimension, so it is flattened here and not in every
                # caller of the tool.
                return {'kind': 'curve',
                        'x': self._flatArray(x),
                        'y': self._flatArray(y)}
            return [self._jsonable(part) for part in value]
        if isinstance(value, list):
            return [self._jsonable(part) for part in value]
        if isinstance(value, dict):
            return {str(key): self._jsonable(part)
                    for key, part in value.items()}
        return str(value)

    @staticmethod
    def _flatArray(values):
        """A curve's array, one dimension, whatever the read wrapped it in."""
        if hasattr(values, 'reshape') and hasattr(values, 'tolist'):
            return values.reshape(-1).tolist()
        if (isinstance(values, list) and len(values) == 1
                and isinstance(values[0], list)):
            return values[0]
        return values
