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
                'kind': self._leafKind(node),
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

    def _leafKind(self, node):
        """What a plot does with this leaf: `curve`, `image`, or `scalar`.

        Decided by the app's own abscissa rule (`abscissae` of the node's
        axes), the same one the panel's routing uses, so a tool and a click
        cannot disagree about whether a leaf is a curve. A curve runs along
        one abscissa, an image has more than one of its own axes, and a
        scalar has neither -- the one the read refuses with the panel's
        "no explicit dependency on current X axis", a phrase that leaves an
        agent without a panel with nothing to act on.
        """
        from imasviz.VizDataAccess.QVizAxesSpec import QVizAxesSpec
        from imasviz.VizDataAccess.QVizCurveAbscissa import abscissae
        try:
            spec = QVizAxesSpec.fromTreeNode(node)
        except Exception:
            return 'scalar'
        if abscissae(spec):
            return 'curve'
        if spec.leafAxes():
            return 'image'
        return 'scalar'

    def _scalarRefusal(self, path):
        """The named refusal a scalar leaf earns on the tool path.

        It says what the leaf is, and points at the sibling that is the
        curve, because that is the answer that ends a retry loop: the panel's
        "has no explicit dependency on current X axis" names a widget the
        agent does not have, and a model reads it as "no data" and asks again.
        """
        return ('"%s" is a scalar -- one value per element of its array, '
                'not a curve of time or coordinate. search_nodes marks the '
                'curves with "kind": "curve"; for a leaf like this the '
                'sibling "…/data" under the same array element is '
                'usually the one a plot wanted.' % path)

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

    def plot_one(self, uri, path, along_time=None, into_figure_key=None):
        """One quantity, drawn by `QVizPlotOneNode` into the frame its axes call for.

        `along_time` is None for no opinion, which leaves the figure's own
        rule standing; the read that cannot answer is named out of the
        case's log, because the command logs it there and returns nothing.
        """
        view = self._viewForUri(uri)
        from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode \
            import QVizPlotOneNode
        node = self._nodeForPath(view, path)
        if self._leafKind(node) == 'scalar':
            # A scalar with no abscissa at all is refused before the command
            # logs the panel's "no explicit dependency on current X axis" and
            # returns nothing -- the agent gets the answer and the pointer to
            # the curve at once, not an opaque line to retry against.
            raise ValueError(self._scalarRefusal(path))
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
        """The named paths, one panel per quantity, in a Table Plot View."""
        view = self._viewForUri(uri)
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
        if self._leafKind(node) == 'scalar':
            # Refused before the read, in words the agent can act on, rather
            # than the panel's "no explicit dependency on current X axis"
            # after it.
            raise ValueError(self._scalarRefusal(path))
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
