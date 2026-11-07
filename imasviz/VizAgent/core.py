# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The gestures of one IMASViz session, asked from outside the menus.

Every method below runs **where a click would have run**: it builds the
application's own command (`QVizLoadOccurrence`, `QVizPlotOneNode`, ...) and
calls its `execute()`, so what it does and how it refuses are exactly what
the manual describes and the suite pins. A refusal is never swallowed: the
named `ValueError` of the command is the error that comes back to the
caller, and a gesture the read cannot answer says so through the last line
of the case's log instead of an empty answer.

Imports only `imasviz`, PySide6 and the standard library: this is the layer
the module-stack test suite drives without the MCP SDK installed.
"""

FIRST = 'first'
ALL = 'all'
_SLICERS = {FIRST: 'FIRST_SLICE', ALL: 'ALL_SLICE'}


class McpGuiCore:
    """One application session: its cases, its selection, its windows.

    `main_window` is the `QVizMainWindow` of the running GUI when there is
    one; left out, as in the test suite, the figures are still built and
    kept by `Viz_API`, and the screenshots are asked of the frames.
    """

    def __init__(self, main_window=None, api=None):
        from imasviz.Viz_API import Viz_API
        # The MDI area is the parent the GUI's own apis are built on
        # (`GUIFrame.getMDI`), which is what makes `addPlotWidgetToMDI`
        # embed in the area the user sees.
        self.main_window = main_window
        if api is not None:
            # The in-app agent passes the session's own api
            # (`QVizMainWindow.sessionApi()`), so the *Windows* menu sees
            # the agent's figures alongside the user's.
            self.api = api
        else:
            # `mcp_server` and the test suite do not pass an api: they build
            # their own bookkeeping, the way they always did.
            self.api = Viz_API(getattr(main_window, 'MDI', None))

    # ------------------------------------------------------------------ cases

    def open_case(self, uri, dd_version=None):
        """Open one case the way `QVizOpenShotView.Open` opens it.

        `dd_version` is the data dictionary to read the case at; left out,
        the case is asked which one its own IDSs were written with
        (`QVizIMASDataSource.pinToCaseDictionary`), because a case stored
        under another major is refused at every `get` otherwise.
        """
        from imasviz.VizDataSource.QVizDataSourceFactory import \
            QVizDataSourceFactory

        source = QVizDataSourceFactory().create(uri)
        if dd_version:
            source.dd_version = dd_version
        else:
            source.pinToCaseDictionary()
        already = self.api.isDataSourceAlreadyOpened(source)
        if already:
            view = self.api.GetDTVFor(source.getKey())
        else:
            view = self.api.CreateDataTree(source).dataTreeView
        self.api.ShowDataTree(view)
        return {
            'uri': view.dataSource.uri,
            'dd_version': getattr(view.dataSource, 'dd_version', None),
            'ids': sorted(view.IDSRoots),
            'already_open': already,
        }

    def list_cases(self):
        """The cases open in this session, with what each has loaded."""
        cases = []
        for view in self.api.DTVlist:
            loaded = {}
            for key in view.dataSource.data_entries:
                name, _, occurrence = key.rpartition('/')
                loaded.setdefault(name, []).append(int(occurrence))
            cases.append({
                'uri': view.dataSource.uri,
                'dd_version': getattr(view.dataSource, 'dd_version', None),
                'loaded': loaded,
                'signals': len(view.signalsList),
            })
        return cases

    def close_case(self, uri):
        """Close one case: its view, its windows, its bookkeeping."""
        self._viewForUri(uri)  # refused by name when the case is not open
        self.api.closeCase(uri)
        return {'closed': uri}

    # ------------------------------------------------------------- the tree

    def list_idss(self, uri):
        """Every IDS root of the case, and the occurrences each one holds."""
        view = self._viewForUri(uri)
        from imasviz.VizDataSource.QVizCaseOccurrences import \
            QVizCaseOccurrences
        occurrences = QVizCaseOccurrences(view.dataSource)
        return [{'name': name,
                 'occurrences': sorted(occurrences.occurrencesOf(name))}
                for name in sorted(view.IDSRoots)]

    def list_case_idss(self, uri):
        """Only the IDS the case actually holds -- the short, grounded list.

        `list_idss` answers the dictionary's declaration: every root of the
        case's data dictionary, the ones that hold no data included (an empty
        occurrence list). A long list is what a model that is asked to
        *summarise* it invents around. This one answers what the case names
        through `DBEntry.list_all_occurrences` and keeps only the IDS whose
        occurrence list is non-empty -- "what is in this case", in the words
        the case says, not a list recalled from training. The same
        `QVizCaseOccurrences` the application uses to colour the tree, so the
        names and the counts are the truth the user reads on screen.
        """
        view = self._viewForUri(uri)
        from imasviz.VizDataSource.QVizCaseOccurrences import \
            QVizCaseOccurrences
        occurrences = QVizCaseOccurrences(view.dataSource)
        held = {}
        for name in sorted(view.IDSRoots):
            occ = sorted(occurrences.occurrencesOf(name))
            if occ:
                held[name] = occ
        return [{'name': name, 'occurrences': held[name]}
                for name in sorted(held)]

    def load_ids(self, uri, ids_name, occurrence=0, slices=FIRST):
        """Load one occurrence of one IDS, synchronously, the way a click loads it.

        `slices` is 'first' for the slice a plain load keeps, 'all' for the
        whole dynamic array -- the names of the manual's entry, not a number,
        and an index the case does not hold is refused by the load with its
        reason, which is what comes back here.
        """
        view = self._viewForUri(uri)
        if slices not in _SLICERS:
            raise ValueError(
                'slices must be "first" or "all", got %r.' % (slices,))
        from imasviz.VizDataAccess import VizTimeSlices
        from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
            import QVizLoadOccurrence
        slicer = getattr(VizTimeSlices, _SLICERS[slices])
        if self.api.IDSDataAlreadyFetched(view, ids_name, occurrence):
            if slices == FIRST:
                # Already on the tree, as the manual's plain load left it: the
                # gesture is already done, and the answer says so rather than
                # rebuilding the branch in place.
                return {'loaded': [ids_name, occurrence],
                        'already': True,
                        'signals': len(view.signalsList)}
        QVizLoadOccurrence(view, ids_name, occurrence,
                           sliceSelection=slicer, asynch=False).execute()
        return {'loaded': [ids_name, occurrence],
                'already': False,
                'signals': len(view.signalsList)}

    def search_nodes(self, uri, query='', ids_name=None, limit=200):
        """The leaves of the case, matched by name or path.

        `query` is a case-insensitive substring, matched against the
        dictionary path and the node name; `ids_name` narrows to one IDS.
        The first `limit` matches come back, in tree order.
        """
        view = self._viewForUri(uri)
        needle = (query or '').lower()
        found = []
        for node in view.signalsList:
            if ids_name is not None and node.getIDSName() != ids_name:
                continue
            if needle:
                aliases = [spelling.lower() for spelling
                           in self._aliasesOf(node)]
                if not any(needle in alias for alias in aliases):
                    continue
            found.append({
                'path': node.getPath(),
                'data_name': node.getDataName(),
                'parametrized': node.getParametrizedDataPath(),
                'ids': node.getIDSName(),
                'occurrence': node.getOccurrence(),
            })
            if len(found) >= limit:
                break
        return found[:limit]

    def select_signals(self, uri, paths, additive=True):
        """Put the named paths into the case's selection, as clicks would.

        The paths are the ones `search_nodes` answers, i.e. the node's
        dictionary path plus its place in the tree -- a path the tree does
        not hold is refused by name, not silently dropped.
        """
        view = self._viewForUri(uri)
        from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectNodes \
            import QVizSelectNodes
        command = QVizSelectNodes(view)
        if not additive:
            command.unselectAll()
        resolved = []
        missing = []
        for path in paths:
            node = next((candidate for candidate in view.signalsList
                         if path in self._aliasesOf(candidate)), None)
            if node is None:
                missing.append(path)
            else:
                resolved.append(node)
        if missing:
            raise ValueError(
                'Not found in the tree of %s: %s -- search_nodes names '
                'what this case can give, in every spelling it holds.'
                % (uri, ', '.join('"%s"' % path for path in missing)))
        for node in resolved:
            command.selectNode(node, view)
        return {'selected': list(paths),
                'selection_size': len(view.selectedSignalsDict)}

    def unselect_all(self, uri):
        """Empty the case's selection; answers how many were dropped."""
        view = self._viewForUri(uri)
        from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectNodes \
            import QVizSelectNodes
        return {'dropped': QVizSelectNodes(view).unselectAll()}

    def list_selection(self, uri):
        """The case's current selection, in the order it was put in.

        The one record the selection is (`selectedSignalsDict`), spelled
        the way this tree spells it: empty is an answer here, `count: 0`.
        """
        view = self._viewForUri(uri)
        ordered = sorted(view.selectedSignalsDict.values(),
                         key=lambda entry: entry.get('index', 0))
        selection = []
        for entry in ordered:
            node = entry['QTreeWidgetItem']
            selection.append({
                'path': node.getPath(),
                'data_name': node.getDataName(),
                'ids': node.getIDSName(),
                'occurrence': int(entry.get('occurrence',
                                            node.getOccurrence() or 0)),
                'name': node.getDataName() or node.getName(),
            })
        return {'count': len(selection), 'selection': selection}

    def describe_node(self, uri, path):
        """What this node holds, as the application's documentation says it.

        The same answer the *Node Documentation* panel draws
        (`QVizNodeFacts`): name, dictionary documentation and units, the
        scalar's text for a 0D node, and for an array the size and shape,
        the finite minimum and maximum, the counts of zeros and of the
        nan and inf entries, and a preview the walk bounds. A leaf the
        tree does not hold is refused by name, as every other gesture
        that looks one up is.
        """
        view = self._viewForUri(uri)
        node = self._nodeForPath(view, path)
        from imasviz.VizGUI.VizWidgets.VizNodeDocumentation.QVizNodeFacts \
            import QVizNodeFacts
        facts = QVizNodeFacts(node)
        answer = {
            'name': facts.name,
            'documentation': facts.documentation,
            'status': facts.status,
            'units': facts.units,
        }
        for field in ('value', 'shape', 'size', 'minimum', 'maximum',
                      'zeros', 'nans', 'infs', 'preview'):
            value = getattr(facts, field)
            if value is not None:
                answer[field] = value
        if facts.refusal:
            answer['refusal'] = facts.refusal
        return answer

    # -------------------------------------------------------------- plotting

    def _aliasesOf(self, node):
        """The spellings of the node, in the order the tree knows them.

        The tree carries a display path (`equilibrium/time_slice(0)/...`),
        a data name (`equilibrium.time_slice[0]....`) and a parametrized
        data path (`equilibrium.time_slice[i]....)`; the selection of the
        manual spells one, the node names the other, and an agent answers
        in whatever of the three it was handed.
        """
        spellings = []
        for getter in (node.getPath, node.getDataName,
                       node.getParametrizedDataPath):
            value = getter()
            if value:
                spellings.append(value)
        return spellings

    def _nodeForPath(self, view, path):
        for node in view.signalsList:
            if path in self._aliasesOf(node):
                return node
        raise ValueError(
            '"%s" is not a leaf of the case %s -- search_nodes names '
            'what this tree can give, in every spelling it holds.'
            % (path, view.uri))

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

    def plot_one(self, uri, path, along_time=None, into_figure_key=None,
                 time=None, time_interp=False):
        """One quantity, drawn by `QVizPlotOneNode` into the frame its axes call for.

        `along_time` is None for no opinion, which leaves the figure's own
        rule standing; the read that cannot answer is named out of the
        case's log, because the command logs it there and returns nothing.

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
        if time is not None and along_time:
            raise ValueError(
                'plot_one: along_time and time are contradictory. '
                'along_time draws the quantity as a history along its every '
                'time slice, so one slice cannot be pinned at the same time. '
                'Drop along_time, or drop the time value, and ask again.')
        view = self._viewForUri(uri)

        if time is not None:
            import numpy as np
            node = self._nodeForPath(view, path)
            tbase = self._timeBase(view, node)
            if tbase is None or tbase.size == 0:
                raise ValueError(
                    'plot_one: %r has no time axis to pin to %g: '
                    'the time parameter applies to a quantity held by a '
                    'dynamic time array (e.g. time_slice[i]); this one is '
                    'not, so a time value there has no slice to resolve to.'
                    % (path, float(time)))
            T = float(time)
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
            raise ValueError(
                '"%s" could not be drawn: %s'
                % (path, self.lastLogLine(view) or 'see the log panel'))
        self._embedIfNew(command, frame)
        return {'figure': frame.figureKey,
                'kind': type(frame).__name__,
                'drawing': bool(frame.isDrawing())}


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

    def _leafDataAtTime(self, view, leafPath, T, interp, occurrence):
        """The (x, y(T)) pair of one 1D-profile leaf read through `DBEntry.get_slice`.

        `x` is the coordinate (time-independent, the same reader `plot_one`
        uses to draw a curve); `y(T)` comes from the HLI's own
        `get_slice(ids, T, interp, occurrence)` call. This is the ONE
        path both `plot_slice` and `plot_one(time=…)` use, so the two
        surfaces share one implementation of "the profile at a time"
        rather than carrying two.

        Refuses by name when the leaf is not a 1D profile (a scalar, a
        tensor, or a leaf whose x and y sizes disagree).
        """
        import numpy as np
        ids, dot, rel = leafPath.partition('.')
        if not dot or not rel:
            raise ValueError(
                'plot_slice/plot_one(time=…): %r is not a leaf of an IDS: '
                'the path must name an IDS root and a leaf, e.g. '
                '`equilibrium.time_slice[0].f`.' % leafPath)
        entry = view.dataSource.db_entry
        try:
            slice_ids = entry.get_slice(ids, float(T), int(interp), int(occurrence))
        except Exception as e:
            raise ValueError(
                'plot_slice: `get_slice(%r, %g, interp=%d, occ=%d)` refused '
                'by the Access Layer: %s'
                % (ids, float(T), int(interp), int(occurrence),
                   str(e).split('\n', 1)[0])[:300])
        slice_time = float(getattr(slice_ids, 'time', [T])[0])
        try:
            y_raw = self._sliceWalk(slice_ids, rel)
        except Exception as e:
            raise ValueError(
                'plot_slice: %r is not a 1D profile of %r in the case: %s'
                % (leafPath, ids, str(e).split('\n', 1)[0])[:300])
        # A 1D profile leaf reads one coordinate and one value per point;
        # get_slice answers it as a flat array, and both must be non-empty.
        y = np.asarray(y_raw, dtype=float).ravel()
        if y.size == 0:
            raise ValueError(
                'plot_slice: %r holds no value at this instant in the case: '
                'the branch is empty, so there is nothing to draw.' % leafPath)
        from imasviz.VizDataAccess.QVizTensorDataAccess import QVizTensorDataAccess
        node = self._nodeForPath(view, leafPath)
        try:
            x_raw, _ = QVizTensorDataAccess(view.dataSource).GetSignal(
                treeNode=node, plotWidget=None,
                as_function_of_time=False, time_index=0)
        except Exception as e:
            raise ValueError(
                'plot_slice: %r is not read as a curve by the reader: %s'
                % (leafPath, str(e).split('\n', 1)[0])[:300])
        # The reader's own convention for a curve figure is a (rows, N) pair,
        # one row per trace; ravel to (N,) so the check and the draw treat
        # both as one coordinate and one value per point.
        x = np.asarray(x_raw, dtype=float).ravel()
        if x.size != y.size:
            raise ValueError(
                'plot_slice: %r reads %d coordinates and %d values — not a '
                '1D profile leaf (one coordinate and one value per point). '
                'A 2D leaf is drawn as a picture, a 0D scalar as a point; '
                'neither is what this entry takes.'
                % (leafPath, x.size, y.size))
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
        ids = leaf.split('.', 1)[0]
        if not self.api.IDSDataAlreadyFetched(view, ids, occurrence):
            self.load_ids(uri, ids, occurrence)
        # A time outside the case's own range answers the nearest slice the
        # case holds (the last, or first), not a refusal and not an echo of
        # the ask: the answer reports `time_requested` and `time_slice_time`
        # separately, so a value asked far outside the pulse is still named
        # as the slice the case actually answered with.
        node = self._nodeForPath(view, leaf)
        T = float(time)
        tbase = self._timeBase(view, node)
        if tbase is not None and tbase.size > 0:
            T = float(min(max(T, float(tbase[0])), float(tbase[-1])))
        x, y, slice_t = self._leafDataAtTime(view, leaf, T, interp, occurrence)

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

        frame.pgPlotWidget.plot(x, y, name=leaf)
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

    def plot_slice_all(self, uri, ids, occurrence=0, into_figure_key=None):
        """Every 1D-profile leaf of one IDS that holds a value in this case,
        at the slice the tree is standing on, into one `Plot:` figure.

        The reader answers which leaf is filled and which reads empty, and it
        already knows the structure, so it is the robust way to draw a whole
        slice: an IDS whose profile is filled at a few leaves draws those, and
        the empty ones are counted and said, not mistaken for curves. An IDS
        that holds zero filled 1D-profile at the occurrence is refused by name,
        so the answer is never an empty window. An interpolated value at an
        arbitrary time is `plot_slice`, which is the other surface.
        """
        import numpy as np
        from imasviz.VizDataAccess.QVizNodePlotting import QVizNodePlotting
        from imasviz.VizDataAccess.QVizTensorDataAccess import QVizTensorDataAccess
        from imasviz.VizUtils import FigureTypes
        from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode \
            import QVizPlotOneNode
        from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot

        view = self._viewForUri(uri)
        if not self.api.IDSDataAlreadyFetched(view, ids, occurrence):
            self.load_ids(uri, ids, occurrence)

        def plottedOne(node):
            try:
                return QVizNodePlotting(node).plottedAxes() == 1
            except Exception:
                return False

        nodes = [n for n in view.signalsList
                 if n.getIDSName() == ids
                 and n.getOccurrence() == occurrence
                 and plottedOne(n)]
        if not nodes:
            raise ValueError(
                'plot_slice_all: the case holds no 1D-profile leaf of the %s '
                'IDS at occurrence %d, so there is no slice to draw. '
                'search_nodes names what this tree does hold.'
                % (ids, occurrence))

        try:
            time_index = int(nodes[0].timeValue())
        except Exception:
            time_index = 0
        reader = QVizTensorDataAccess(view.dataSource)

        if into_figure_key is not None:
            command = QVizPlotOneNode(view, nodes[0],
                                      intoFigureKey=into_figure_key)
            frame = command.frameFor()
            if not hasattr(frame, 'pgPlotWidget'):
                command.discardIfEmpty(frame)
                raise ValueError(
                    'plot_slice_all: %r is not a `Plot` figure: name a curve '
                    'figure, e.g. Plot1.' % into_figure_key)
        else:
            command = QVizPlotOneNode(view, nodes[0])
            frame = command.newFigure(FigureTypes.CURVEPLOTTYPE, QVizCurvePlot)

        drawn = 0
        empty = 0
        for node in nodes:
            leaf = node.getPath()
            # The tree path is `core_profiles/profiles_1d(0)/grid/rho_tor_norm`;
            # the legend reads what comes after the IDS root, which keeps the
            # array of structures the profile is held by and stays unique.
            label = leaf[len(ids) + 1:] if leaf.startswith(ids + '/') else leaf
            try:
                x, y = reader.GetSignal(treeNode=node, plotWidget=None,
                                        as_function_of_time=False,
                                        time_index=time_index)
                x = np.asarray(x, dtype=float).ravel()
                y = np.asarray(y, dtype=float).ravel()
            except Exception:
                empty += 1
                continue
            if x.size and x.size == y.size:
                frame.pgPlotWidget.plot(x, y, name=label)
                drawn += 1
            else:
                empty += 1

        if drawn == 0:
            command.discardIfEmpty(frame)
            raise ValueError(
                'plot_slice_all: the %s IDS at occurrence %d holds no filled '
                '1D-profile in this case: all %d read empty, so there is '
                'nothing to draw.' % (ids, occurrence, len(nodes)))

        frame.pgPlotWidget.setLabel('left', ids)
        frame.pgPlotWidget.setTitle(
            'slice of %s (occurrence %d, slice %d): '
            % (ids, occurrence, time_index) + str(drawn)
            + ' of ' + str(len(nodes)) + ' profiles')
        self._embedIfNew(command, frame)
        return {'figure': frame.figureKey,
                'drawn': drawn,
                'empty': empty,
                'candidates': len(nodes),
                'occurrence': occurrence,
                'time_slice_index': time_index,
                'kind': type(frame).__name__}

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
                   coordinate_index=0, time_index=None):
        """The values the tree's read gives for one leaf, as JSON.

        The same read the plots use (`Viz_API.GetSignal`), so what comes
        back is exactly what a panel drew: the coordinate and value arrays
        for a slice, or the named coordinates and values for a quantity of
        more than one array.
        """
        view = self._viewForUri(uri)
        node = self._nodeForPath(view, path)
        result = self.api.GetSignal(view, node,
                                    as_function_of_time=as_function_of_time,
                                    coordinate1_index=coordinate_index,
                                    time_index=time_index)
        payload = self._jsonable(result)
        if isinstance(payload, dict) and payload.get('kind') == 'curve':
            payload['samples'] = len(payload.get('y') or [])
        return payload

    # -------------------------------------------------------------- windows

    def list_windows(self):
        """Every window the session can see, in the order the menus draw them."""
        windows = []
        for record in self.api.openWindows():
            windows.append({
                'kind': record.kindLabel,
                'label': record.label,
                'key': record.figureKey,
                'visible': bool(record.visible()),
                'cases': list(record.cases),
            })
        return windows

    def _windowForKey(self, key):
        for record in self.api.openWindows():
            if record.figureKey == key:
                frame = record.frame()
                if frame is not None:
                    return record, frame
        raise ValueError(
            'No window holds the key "%s" any more -- list_windows names '
            'what is open.' % key)

    def show_window(self, key):
        record, frame = self._windowForKey(key)
        visible = self.api.setWindowVisible(frame, True)
        return {'key': key, 'visible': bool(visible)}

    def hide_window(self, key):
        record, frame = self._windowForKey(key)
        visible = self.api.setWindowVisible(frame, False)
        return {'key': key, 'visible': bool(visible)}

    def close_window(self, key):
        record, frame = self._windowForKey(key)
        self.api.closeWindow(frame)
        return {'closed': key}

    # -------------------------------------------------------------- plugins

    def _catalog(self, view):
        from imasviz.VizPlugins.QVizPluginCatalog import QVizPluginCatalog
        catalog = getattr(view, 'pluginCatalog', None)
        if catalog is None:
            catalog = QVizPluginCatalog(view)
            view.pluginCatalog = catalog
        return catalog

    def list_plugins(self, uri, ids_name):
        """The entries this IDS earns, in registration order.

        The refusal of a plugin that cannot be offered is answered with the
        list, named, because the catalog is where it is said and an agent
        that cannot read the log panel would never see it otherwise.
        """
        view = self._viewForUri(uri)
        if ids_name not in view.IDSRoots:
            raise ValueError(
                '"%s" is not an IDS root of the case %s: %s'
                % (ids_name, uri, ', '.join(sorted(view.IDSRoots))))
        catalog = self._catalog(view)
        entries = catalog.entriesFor(view.IDSRoots[ids_name])
        return {'entries': [{'plugin': entry.pluginName,
                             'entry': entry.number,
                             'label': entry.label,
                             'description': entry.description}
                            for entry in entries],
                'refusals': list(catalog.refusals)}

    def run_plugin(self, uri, plugin, entry, occurrence=0, ids_name=None):
        """Run one entry of a plugin, with the answers the entry would have asked.

        `QVizPluginAnswers` is always handed when the entry can take it,
        which is what keeps a modal question off the path of an agent: the
        occurrence it says is the one asked here, and an entry whose
        `execute` cannot take the answers is run the way the menu runs it.
        """
        import inspect

        from imasviz.VizPlugins.VizPlugin import QVizPluginAnswers

        view = self._viewForUri(uri)
        catalog = self._catalog(view)
        if ids_name is None:
            if view.IDSRoots:
                ids_name = next(iter(view.IDSRoots))
            else:
                raise ValueError('The case %s builds no IDS root.' % uri)
        node = view.IDSRoots.get(ids_name)
        if node is None:
            raise ValueError(
                '"%s" is not an IDS root of the case %s: %s'
                % (ids_name, uri, ', '.join(sorted(view.IDSRoots))))
        chosen = None
        for candidate in catalog.entriesFor(node):
            if candidate.pluginName == plugin and candidate.number == entry:
                chosen = candidate
                break
        if chosen is None:
            raise ValueError(
                'The case %s does not offer entry %s of plugin "%s": '
                'list_plugins names what it does.'
                % (uri, entry, plugin))
        answers = None
        execute = getattr(chosen.plugin, 'execute', None)
        if callable(execute) and self._acceptsAnswers(execute):
            answers = QVizPluginAnswers(occurrence=occurrence,
                                        figureKey=None)
        catalog.run(chosen, answers=answers)
        return {'ran': {'plugin': plugin, 'entry': entry,
                        'occurrence': occurrence if answers is not None
                        else None},
                'windows': self.list_windows()}

    @staticmethod
    def _acceptsAnswers(execute):
        """The same question `QVizPluginCatalog` asks, asked the same way.

        Mirror of that helper, kept local because it is module-private:
        whether the signature answers an `answers=` keyword, and when it
        cannot be inspected at all the safe reading -- the menu path -- is
        the one taken.
        """
        import inspect
        try:
            parameters = inspect.signature(execute).parameters
        except (TypeError, ValueError):
            return False
        parameter = parameters.get('answers')
        return (parameter is not None
                or any(p.kind is inspect.Parameter.VAR_KEYWORD
                       for p in parameters.values()))

    # --------------------------------------------------------------- session

    def save_session(self, name=None, path=None):
        """Write the session, as `QVizSaveSession` writes it."""
        from imasviz.VizGUI.VizGUICommands.VizSession.QVizSaveSession \
            import QVizSaveSession
        if name is None and path is None:
            name = 'mcp_session'
        written = QVizSaveSession(self.api, path=path, name=name).execute()
        return {'saved_to': written}

    def restore_session(self, name=None, path=None):
        """Put a session back, as `QVizRestoreSession` puts it back."""
        from imasviz.VizGUI.VizGUICommands.VizSession.QVizRestoreSession \
            import QVizRestoreSession
        views = QVizRestoreSession(self.api, path=path, name=name).execute()
        return {'cases': [{'uri': uri, 'opened': view is not None}
                          for uri, view in views.items()],
                'windows': self.list_windows()}

    def list_sessions(self):
        """The sessions the configuration folder holds, as the dialog lists them."""
        from imasviz.VizGUI.VizConfigurations.QVizSessionFile import \
            QVizSessionFile
        return {'sessions': QVizSessionFile.listing()}

    def list_configurations(self, kind=None):
        """The plot and selection configurations the folder holds.

        `kind` narrows to one of the two kinds a configuration has
        ('plot' for a .pcfg, 'selection' for a .lsp); a kind the
        application does not answer is refused by name, 'session'
        among them -- the sessions sit beside the configurations in
        that folder, and not in them.
        """
        from imasviz.VizGUI.VizConfigurations.QVizConfigurationFile import \
            QVizConfigurationFile
        if kind not in (None, 'plot', 'selection'):
            raise ValueError(
                '"%s" is not a configuration kind: the kinds this '
                'application holds are plot and selection (the sessions '
                'in the same folder are listed by list_sessions).'
                % kind)
        if kind is None:
            return {'plot': QVizConfigurationFile.listing('plot'),
                    'selection': QVizConfigurationFile.listing('selection')}
        return {kind: QVizConfigurationFile.listing(kind)}

    def select_from_configuration(self, uri, name):
        """Apply one saved configuration: select the quantities it names.

        The same gesture as the application's *Select from configuration*
        (which, like this, loads the IDSs it lacks first), and the same
        reading of the file (a .lsp as a .pcfg: what they name is the
        quantities and nothing else). Answers how many were selected; a
        name the folder does not hold is refused by name, naming the
        ones the folder does hold.
        """
        view = self._viewForUri(uri)
        from imasviz.VizGUI.VizGUICommands.VizDataSelection. \
            QVizSelectFromConfiguration import QVizSelectFromConfiguration
        path = self._namedFile(name, ('.lsp', '.pcfg'))
        selected = QVizSelectFromConfiguration(view, path).execute()
        return {'selected': int(selected), 'from': path}

    def save_selection(self, uri, name):
        """Write the case's selection out as a .lsp, as `QVizSaveNodeSelection` writes it."""
        view = self._viewForUri(uri)
        from imasviz.VizGUI.VizGUICommands.VizDataSelection. \
            QVizSaveNodeSelection import QVizSaveNodeSelection
        written = QVizSaveNodeSelection(view, name=name).execute()
        return {'saved_to': written,
                'count': len(view.selectedSignalsDict)}

    def save_plot_configuration(self, uri, figure_key, name):
        """Write one Table Plot View out as a .pcfg, as `QVizSavePlotConfiguration` does."""
        view = self._viewForUri(uri)
        record, frame = self._windowForKey(figure_key)
        if not (callable(getattr(frame, 'panelsInTable', None))
                and callable(getattr(frame, 'getPlotAxis', None))):
            raise ValueError(
                'The window "%s" is not a Table Plot View: this gesture '
                'writes the window out as it lays its panels, and that '
                'window is a %s. list_windows names the windows that '
                'hold panels.' % (figure_key, record.kindLabel))
        from imasviz.VizGUI.VizConfigurations.QVizSavePlotConfiguration \
            import QVizSavePlotConfiguration
        written = QVizSavePlotConfiguration(view, frame, name=name).execute()
        return {'saved_to': written,
                'panels': int(len(frame.panelsInTable()))}

    def _namedFile(self, name, extensions):
        """A configuration name resolved against the configuration folder.

        The same guard the application applies to a name typed in a text
        field (`QVizConfigurationFile.named`): a name typed with an
        extension loses it, a name naming a place is refused. One of the
        extensions the name may wear is accepted (a .lsp as a .pcfg),
        and a name none of the extensions holds is refused by name,
        naming the ones the folder does hold."""
        import os

        from imasviz.VizGUI.VizConfigurations.QVizConfigurationFile import \
            QVizConfigurationFile
        typed = (name or '').strip()
        for extension in extensions:
            if typed.endswith(extension):
                typed = typed[:-len(extension)]
                break
        if not typed:
            raise ValueError('A configuration needs a name.')
        if os.path.sep in typed or (os.path.altsep and os.path.altsep
                                    in typed) or typed in ('.', '..'):
            raise ValueError(
                '"%s" is not a configuration name: it names a place, not '
                'a configuration. Name one inside the configuration '
                'folder, the way the dialog asks.' % name)
        folder = QVizConfigurationFile.directory()
        for extension in extensions:
            candidate = os.path.join(folder, typed + extension)
            if os.path.isfile(candidate):
                if os.path.dirname(os.path.realpath(candidate)) != \
                        os.path.realpath(folder):
                    raise ValueError(
                        '"%s" would be read outside %s.' % (name, folder))
                return candidate
        held = sorted(set(QVizConfigurationFile.listing('plot'))
                      | set(QVizConfigurationFile.listing('selection')))
        raise ValueError(
            'No configuration "%s" in %s: the folder holds %s.'
            % (name, folder, ', '.join(held) or 'no configuration at all'))

    # ---------------------------------------------------------------- reports

    def plot_report(self, figure_key, name=None):
        """A window of curves as a self-contained HTML report.

        The image of the window, and one row per trace it drew: the
        quantity, the number of samples, the finite minimum and maximum,
        and the counts of the entries that are not numbers. The file
        lands in `~/.imasviz/reports/` under the guard the
        configurations have, and a window that draws no curve it could
        stat is refused by name.
        """
        record, frame = self._windowForKey(figure_key)
        rows = []
        refused = 0
        for source in self._sourcesOf(frame):
            for node, rank, curve in self._tracesOf(source):
                stats = self.curveStats(self._curveData(curve))
                if stats['n'] == 0:
                    refused += 1
                    continue
                rows.append(((self._nodeLabel(node), rank, source), stats))
        if not rows:
            raise ValueError(
                'The window "%s" (%s) holds %d trace(s), none of which '
                'has a number to stat -- the report has nothing to say '
                'about it.' % (figure_key, record.kindLabel, refused))
        image = None
        try:
            image = self.screenshot(figure_key)
        except ValueError:
            image = None
        path = self._namedReport(name, len(rows))
        self._writeReport(path,
                          title='Curves of %s' % figure_key,
                          sub='window %s (%s) — %d trace(s)'
                              % (figure_key, record.kindLabel, len(rows)),
                          image=image, rows=rows)
        self._logFor(record.cases,
                     'plot_report wrote %s: %d trace(s) of the window %s.'
                     % (path, len(rows), figure_key))
        return {'saved_to': path, 'traces': len(rows), 'window': figure_key}

    def case_report(self, uri, name=None):
        """The loaded tree of one case as a self-contained HTML report.

        One row per curve the loaded tree holds -- a non-empty,
        multi-dimensional number (the arrays whose leaves read): with the
        statistics of each, in tree order. A 0-D scalar is a single point
        -- the domain of `describe_node` -- and an empty array has no
        sample to stat, so neither is a curve here. The curves are as many
        as the loads are: an IDS not yet loaded is not a curve, so the
        report says how many curves it answered, and `list_idss` names
        what the case still holds.
        """
        view = self._viewForUri(uri)
        import numpy as np

        from imasviz.VizUtils import QVizGlobalOperations

        rows = []
        for node in view.signalsList:
            try:
                if node.isIDSRoot() \
                        or node.getDataType() in ('structure', 'struct_array'):
                    continue
            except Exception:
                continue
            try:
                values = node.resolvePath(
                    QVizGlobalOperations.makePythonPath(node.getPath()))
            except Exception:
                continue
            if values is None:
                continue
            try:
                array = np.asarray(values)
            except Exception:
                continue
            if array.ndim < 1 or array.dtype.kind not in 'iufc':
                continue
            stats = self.curveStats((array, array))
            if stats['n'] == 0:
                continue
            rows.append(((self._nodeLabel(node),), stats))
        if not rows:
            raise ValueError(
                'The tree of %s holds no curve: load the IDSs it holds '
                'first (list_idss names them, load_ids builds the branch).'
                % uri)
        path = self._namedReport(name, len(rows))
        self._writeReport(path,
                          title='Curves of %s' % uri,
                          sub='data dictionary %s — %d curve(s), in tree order'
                              % (getattr(view.dataSource, 'dd_version', '')
                                 or '?', len(rows)),
                          image=None, rows=rows)
        self._logFor([uri],
                     'case_report wrote %s: %d curve(s) of %s.'
                     % (path, len(rows), uri))
        return {'saved_to': path, 'curves': len(rows), 'uri': uri}

    @staticmethod
    def curveStats(xy):
        """The statistics of one curve, as the report says them.

        ``xy`` is a drawn curve ``(x, y)``. One number per field: the
        count of samples, the finite minimum and maximum of the x axis,
        the mean and standard deviation of the values, and the counts of
        the ``nan`` and ``inf`` entries. An entry that is not a number is
        neither a minimum nor a mean, so it is counted, not silently
        folded into the statistics of the other ones -- the reading the
        documentation panel applies.
        """
        import numpy as np

        _empty = {'n': 0, 'min': None, 'max': None, 'mean': None,
                  'std': None, 'nan': 0, 'inf': 0}

        def statsOf(array):
            if array is None:
                return _empty
            try:
                values = np.asarray(array, dtype=float).ravel()
            except (TypeError, ValueError):
                return _empty
            finite = values[np.isfinite(values)]
            return {
                'n': int(values.size),
                'min': float(finite.min()) if finite.size else None,
                'max': float(finite.max()) if finite.size else None,
                'mean': float(finite.mean()) if finite.size else None,
                'std': float(finite.std()) if finite.size else None,
                'nan': int(np.count_nonzero(np.isnan(values))),
                'inf': int(np.count_nonzero(np.isinf(values))),
            }

        x, y = xy
        xStats = statsOf(x)
        yStats = statsOf(y)
        return {
            'n': yStats['n'],
            'x0': xStats['min'],
            'x1': xStats['max'],
            'min': yStats['min'],
            'max': yStats['max'],
            'mean': yStats['mean'],
            'std': yStats['std'],
            'nan': yStats['nan'],
            'inf': yStats['inf'],
        }

    # ------------------------------------------------------- report helpers

    def _sourcesOf(self, frame):
        """Every part of the window that draws: a curve figure is one, a
        table or stacked window one panel at a time -- the one answer
        `QVizPlotStyling` gives the styling dialogue."""
        from imasviz.VizGUI.VizPlot.QVizPlotStyling import sourcesOf
        return list(sourcesOf(frame))

    def _tracesOf(self, source):
        """[(treeNode, rank, curve)] the traces one source answers --
        the same list the styling dialogue colors, so a report row is
        the trace behind one color."""
        traces = getattr(source, 'tracesForStyling', None)
        if not callable(traces):
            return []
        try:
            return list(traces())
        except Exception:
            return []

    @staticmethod
    def _curveData(curve):
        """The (x, y) of one drawn curve, one dimension each."""
        from numpy import asarray

        def one(values):
            if values is None:
                return None
            return asarray(values).reshape(-1)

        return (one(getattr(curve, 'xData', None)),
                one(getattr(curve, 'yData', None)))

    @staticmethod
    def _nodeLabel(node):
        for getter in (getattr(node, 'getDataName', None),
                       getattr(node, 'getPath', None),
                       getattr(node, 'getName', None)):
            if getter is None:
                continue
            try:
                label = getter()
            except Exception:
                label = None
            if label:
                return label
        return str(node)

    def _logFor(self, cases, line):
        import logging
        uri = next((case for case in cases if case), None)
        logging.getLogger(uri or 'logPanel').info(line)

    def _namedReport(self, name, count):
        """The file one report writes: under `~/.imasviz/reports`, the
        guard of the configurations, and the name the caller said -- or
        the one the report is, when it said none."""
        import os
        import time

        home = os.environ.get('HOME')
        if not home:
            raise ValueError(
                'No HOME in the environment: the reports folder under '
                'it cannot be named.')
        folder = os.path.join(home, '.imasviz', 'reports')
        if not os.path.isdir(folder):
            os.makedirs(folder)
        typed = (name or '').strip()
        if typed.endswith('.html'):
            typed = typed[:-5]
        if not typed:
            typed = 'report-' + time.strftime('%Y%m%d-%H%M%S') + '-%d' % count
        if os.path.sep in typed or (os.path.altsep and os.path.altsep
                                    in typed) or typed in ('.', '..'):
            raise ValueError(
                '"%s" is not a report name: it names a place, not a '
                'report. Name one inside %s.' % (name, folder))
        path = os.path.join(folder, typed + '.html')
        if os.path.dirname(os.path.realpath(path)) != os.path.realpath(folder):
            raise ValueError('"%s" would be written outside %s.'
                             % (name, folder))
        return path

    def _writeReport(self, path, title, sub, image, rows):
        """The self-contained page the report is: one table, its own
        little style, the image when there is one, and nothing to fetch."""
        import base64
        import html
        import time

        style = ("""
        body { font-family: Cantarell, 'Open Sans', 'DejaVu Sans', sans-serif;
               margin: 2rem; color: #182430; background: #ffffff; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #dde3e7; padding: .35rem .6rem;
                 text-align: left; font-size: .95rem; }
        th { background: #f0f4f5; }
        .q  { font-family: 'DejaVu Sans Mono', monospace; font-size: .85rem; }
        .s  { font-variant-numeric: tabular-nums; }
        img { max-width: 90%; border: 1px solid #dde3e7; margin-bottom: 1.2rem; }
        .sub { color: #5a6672; margin-top: .1rem; }
        .ref { color: #a03030; }
        """ )
        parts = [
            '<!doctype html>',
            '<html lang="en"><head><meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            '<title>%s</title><style>%s</style></head><body>' % (
                html.escape(title), style),
            '<h1>%s</h1>' % html.escape(title),
            '<p class="sub">%s — %s</p>' % (html.escape(sub),
                                            time.strftime('%Y-%m-%d %H:%M:%S')),
        ]
        if image:
            parts.append(
                '<img alt="%s" src="data:image/png;base64,%s">' % (
                    html.escape(title),
                    base64.b64encode(image).decode('ascii')))
        parts.append('<table>')
        parts.append('<tr><th>quantity</th><th>n</th><th>x&nbsp;min</th>'
                     '<th>x&nbsp;max</th><th>min</th><th>max</th><th>mean</th>'
                     '<th>std</th><th>nan</th><th>inf</th></tr>')
        for label, stats in rows:
            quantity = label[0]
            parts.append(
                '<tr><td class="q">%s</td><td class="s">%s</td><td class="s">%s</td>'
                '<td class="s">%s</td><td class="s">%s</td><td class="s">%s</td>'
                '<td class="s">%s</td><td class="s">%s</td><td class="s">%s</td>'
                '<td class="s">%s</td></tr>' % (
                    html.escape(quantity),
                    stats['n'],
                    self._num(stats['x0']), self._num(stats['x1']),
                    self._num(stats['min']), self._num(stats['max']),
                    self._num(stats['mean']), self._num(stats['std']),
                    stats['nan'], stats['inf']))
        parts.append('</table></body></html>')
        try:
            with open(path, 'w', encoding='utf-8') as file:
                file.write('\n'.join(parts))
        except OSError as error:
            raise ValueError('The report could not be written to %s: %s'
                             % (path, error))

    @staticmethod
    def _num(value):
        if value is None:
            return '—'
        return ('%g' % float(value)) if isinstance(value, float) else str(value)

    # ---------------------------------------------------------------- export

    def export_to_ids(self, uri, target_uri, dd_version=None):
        """Copy the case's opened IDSs to the target case.

        `target_uri` is the only spelling a scripted caller needs
        (`QVizExportTarget` says so); `dd_version` defaults to the one the
        case was read at, which is the only one the loaded instances are
        valid for.
        """
        view = self._viewForUri(uri)
        from imasviz.VizGUI.VizGUICommands.VizDataExport.QVizExportToIDS \
            import QVizExportToIDS
        from imasviz.VizGUI.VizGUICommands.VizDataExport.QVizExportTarget \
            import QVizExportTarget
        target = QVizExportTarget(uri=target_uri,
                                  dataVersion=dd_version)
        written = QVizExportToIDS(view, target=target,
                                  ddVersion=dd_version).execute()
        return {'written_to': written}

    # ------------------------------------------------------------ screenshots

    def screenshot(self, window='app'):
        """One window as PNG: the application, a figure key, or a case URI.

        `QWidget.grab()` renders the window without asking it to be anywhere
        in particular -- the same reading the theme tests in the suite use
        to sample pixels without entering the paint-queue hazard -- and an
        offscreen application is the one this is asked of first.
        """
        if window == 'app':
            if self.main_window is None:
                raise ValueError(
                    'No application window to capture: this session was '
                    'built without one -- name a figure key or a case URI.')
            target = self.main_window
        else:
            target = None
            if window in self.api.figureframes:
                target = self.api.figureframes[window]
            else:
                view = self._viewForUri(window)
                for frame in self.api.DTVframeList:
                    if frame.dataTreeView is view:
                        target = frame
                        break
            if target is None:
                raise ValueError(
                    '"%s" is neither a figure key nor an open case: '
                    'list_windows names the keys.' % window)
        pixmap = target.grab()
        if pixmap is None or pixmap.isNull():
            raise ValueError('Qt could not render "%s": it answers no image.'
                             % window)
        # This PySide6's QImage exposes neither toBytes nor toByteArray, so
        # the image is encoded into an in-memory device -- the idiom Qt keeps
        # in both bindings.
        from PySide6.QtCore import QBuffer, QByteArray, QIODevice
        image = pixmap.toImage()
        qbytes = QByteArray()
        buffer = QBuffer(qbytes)
        buffer.open(QIODevice.WriteOnly)
        try:
            if not image.save(buffer, 'PNG'):
                raise ValueError(
                    'Qt could not encode "%s" as PNG: the save refused.'
                    % window)
        finally:
            buffer.close()
        return bytes(qbytes)

    def get_screenshot(self, window='app'):
        """Answer the tool name the loop dispatches under: ``TOOLS``
        (``imasviz/VizAgent/tools.py``) offers ``get_screenshot`` to the
        LLM, and ``AgentLoop._dispatch`` asks the core for that name.
        Before this existed, the call refused by name -- the method below
        is the same gesture, and both names must keep answering, which
        ``tests/test_116`` pins.
        """
        return self.screenshot(window)

    # ------------------------------------------------------------- log panel

    def get_logs(self, uri=None, tail=200):
        """The case's log panel, read off the widget the application writes into.

        The panel lives on the shot view's **frame** (`addDockWidgets` builds
        it there and wires the logger of the case to it) -- which is where
        the named refusals end up, and the one place an agent can read them.
        Without `uri`, every open case is answered in order; with it, that
        case's panel, refused by name when the case is not open.
        """
        frames = [frame for frame in self.api.DTVframeList]
        if uri is not None:
            frames = [frame for frame in frames
                      if frame.dataTreeView.dataSource.uri == uri]
            if not frames:
                openUris = [frame.dataTreeView.dataSource.uri
                            for frame in self.api.DTVframeList]
                raise ValueError(
                    'The case %r is not open in this session (it holds: %s). '
                    'Open it with open_case first.'
                    % (uri, ', '.join('"%s"' % u for u in openUris)
                       or 'nothing'))
        logs = []
        for frame in frames:
            view = frame.dataTreeView
            panel = getattr(frame, 'logWidget', None)
            text = panel.toPlainText() if panel is not None else ''
            lines = [line for line in text.splitlines() if line.strip()]
            logs.append({'uri': view.uri, 'lines': lines[-tail:]})
        if len(logs) == 1:
            return {'uri': logs[0]['uri'], 'lines': logs[0]['lines']}
        return {'logs': logs}

    # ---------------------------------------------------------------- helpers

    def _viewForUri(self, uri):
        for view in self.api.DTVlist:
            if view.dataSource.uri == uri:
                return view
        openUris = [getattr(view.dataSource, 'uri', None)
                    for view in self.api.DTVlist]
        raise ValueError(
            'The case %r is not open in this session (it holds: %s). '
            'Open it with open_case first.'
            % (uri, ', '.join('"%s"' % u for u in openUris) or 'nothing'))

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
