# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The window, session, plugin and report gestures of one IMASViz session.

List and focus the windows, run the plugins, save and restore sessions and configurations, and write the three HTML reports. A refusal is the named `ValueError` the caller gets back.
"""

from imasviz.VizAgent.core import _REPORT_CSS

class WindowOps:
    """The windows, the sessions, the plugins and the three reports."""

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

    def focus_window(self, window='app', width=None, height=None):
        """Bring a window forward -- the user's "show me this" command.

        Shown (the hide rule of the close box is undone through
        `setWindowVisible`) and raised to the front. The window keeps
        the size it holds when no side is named -- "montre-moi Plot1"
        does not resize a window the user has placed -- and is sized
        from `width` and `height` when those name pixels, a side left
        out keeping the size the window holds on that side. "app" is the
        main window: it is raised and answers its own size, and no figure
        is touched.

        This is not a default after a draw: a figure the loop drew or
        named is a window of the session, in the *Windows* menu, and a
        draw is not an ask to see it. It is called when the user asks
        ("montre-moi Plot1", "ramène Plot1 devant", "je ne vois pas la
        figure"), and before a requested capture whose window answers
        small, where the readable size the ask names is what `width` and
        `height` hold.

        `width` and `height` are named refusals when they are not
        positive integers: a size is a pair of pixel counts, and a number
        the window cannot hold is one the caller mislabeled.
        """
        def side(name, value):
            try:
                number = int(value)
            except (TypeError, ValueError):
                raise ValueError(
                    '%s=%r is not a pixel count: name it as an integer, '
                    'or leave it out for the size the window holds.'
                    % (name, value))
            if number < 1:
                raise ValueError(
                    '%s=%d has no room to be a window: name %d pixels '
                    'and up, or leave it out.' % (name, number, 1))
            return number

        target = self._resolveWindow(window)
        if window == 'app':
            target.raise_()
            if callable(getattr(target, 'activateWindow', None)):
                target.activateWindow()
            return {'window': window,
                    'visible': bool(target.isVisible()),
                    'size': [target.width(), target.height()]}

        visible = self.api.setWindowVisible(target, True)
        # The shell is the window the user would see: it carries the
        # title bar, so it is what is raised and sized -- the frame it
        # holds follows through its own layout.
        shell = self.api.mdiWindowOf(target)
        base = shell if shell is not None else target
        if width is not None or height is not None:
            width = side('width', width) if width is not None else base.width()
            height = side('height', height) if height is not None else base.height()
            base.resize(width, height)
        base.raise_()
        if shell is not None:
            base.activateWindow()
        size = target.size()
        return {'window': window,
                'visible': bool(visible),
                'size': [size.width(), size.height()]}

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

    def _resolveRoot(self, catalog, view, plugin, entry):
        """Which IDS root a call that named none is asking for.

        The case is searched for the roots that earn that line, and the answer is
        used when it is one. It is not silently used when it is several: a plugin
        offered on any IDS (`VizProfiles_plugin`) earns a line
        on every branch, and the occurrence and the window drawn differ per
        branch -- which is a question for the caller, not a guess for the tool. A
        refusal names what the plugin *does* offer, because a wrong entry number
        is the other half of the state.
        """
        offered = catalog.entriesNamed(plugin, view.IDSRoots.values())
        exact = [(root, one) for root, one in offered if one.number == entry]
        if len(exact) == 1:
            return exact[0]
        uri = view.dataSource.uri
        if len(exact) > 1:
            raise ValueError(
                'Entry %s of plugin "%s" is offered on %d IDS roots of the case '
                '%s (%s): name the ids_name, since the occurrence and the window '
                'it draws differ per root.'
                % (entry, plugin, len(exact), uri,
                   ', '.join(sorted(root for root, _ in exact))))
        if offered:
            self._refuseUnknownEntry(uri, plugin, entry, offered)
        raise ValueError(
            'The case %s offers no entry of plugin "%s" on any of its %d IDS '
            'roots: plugin(action="list") names what a branch earns, and the '
            'log of the case names the plugins it cannot offer at all.'
            % (uri, plugin, len(view.IDSRoots)))

    def _refuseUnknownEntry(self, uri, plugin, entry, offered):
        """Refuse an entry number the plugin does not carry, naming the ones it does."""
        byRoot = {}
        for root, one in offered:
            byRoot.setdefault(root, []).append(one)
        raise ValueError(
            'The case %s does not offer entry %s of plugin "%s": that plugin is '
            'offered on %s, whose entries are %s. plugin(action="list") names '
            'the label of each.'
            % (uri, entry, plugin, ', '.join(sorted(byRoot)),
               '; '.join('%s: %s' % (root, ', '.join('%s (%s)'
                                                     % (one.number, one.label)
                                                     for one in byRoot[root]))
                         for root in sorted(byRoot))))

    def run_plugin(self, uri, plugin, entry, occurrence=0, ids_name=None,
                   time=None):
        """Run one entry of a plugin, with the answers the entry would have asked.

        `QVizPluginAnswers` carries the occurrence and the instant so that
        `catalog.run` passes them into `QVizPluginContext.answers`, where the
        plugin's action reads them. This is what keeps a modal occurrence or time
        question off the path of an agent: an entry that would ask and is handed
        no answer refuses by name rather than open a dialog nobody is there for.

        `ids_name` says which IDS root the line is asked on. Left out, the root is
        resolved by searching the case for the roots that earn that entry: one
        match is used, several or none is refused with them named. The first root
        of the case is not the one a plugin scoped to `equilibrium` lives on.

        An entry whose window already stands is drawn into that window rather
        than opening a second one over it -- the stamp the entry left when it
        drew it (`openWindowOfPluginEntry`) says which window that is, and the
        entry is handed its key with `reuse`. The user asking the same line
        twice wants the same window showing the answer, not two of them:
        measured before this, one call of `equilibriumsurfaces` after a session
        had put that window back left two `EquiSurfaces:` windows on the screen,
        and the transcript of the ask named one gesture.

        `drawn` names the windows the entry drew -- the ones this call opened or
        redrew, not the whole screen -- so a claim about that window stands on
        the call that drew it.
        """
        from imasviz.VizPlugins.VizPlugin import QVizPluginAnswers

        view = self._viewForUri(uri)
        catalog = self._catalog(view)
        if ids_name is None:
            ids_name, chosen = self._resolveRoot(catalog, view, plugin, entry)
        else:
            node = view.IDSRoots.get(ids_name)
            if node is None:
                raise ValueError(
                    '"%s" is not an IDS root of the case %s: %s'
                    % (ids_name, uri, ', '.join(sorted(view.IDSRoots))))
            chosen = next((candidate for candidate in catalog.entriesFor(node)
                           if candidate.pluginName == plugin
                           and candidate.number == entry), None)
            if chosen is None:
                raise ValueError(
                    'The case %s does not offer entry %s of plugin "%s" on its '
                    '%s branch: plugin(action="list") names what it does.'
                    % (uri, entry, plugin, ids_name))
        standing = self.api.openWindowOfPluginEntry(uri, plugin, entry,
                                                    occurrence, time,
                                                    ids_name=ids_name)
        answers = QVizPluginAnswers(occurrence=occurrence, figureKey=standing,
                                    time=time, reuse=standing is not None)
        # What the entry drew, as its own answer. `windows` answers every
        # window of the session: that is the screen, and it names nothing
        # this call did. The loop grounds a claim of work on the keys a call
        # named, and a plugin entry named none of them in the fields it reads
        # (`figure` / `window` / `figures`). So the turn that ran `run_plugin`
        # and answered « j'ai tracé les surfaces sur EquiSurfaces:1 » was
        # refused by the work guard and re-anchored with "do the work: draw
        # it" -- and the model drew it a second time. That is the duplicate
        # window this reports.
        before = set(self.api.figureframes)
        refusal = catalog.run(chosen, answers=answers)
        if refusal is not None:
            # The plugin wrote its reason in the log of the case, where nobody
            # driving a tool is looking. An answer of `ran` there is a wrong
            # answer: it reports a window that was never drawn.
            raise ValueError(refusal)
        drawn = sorted(key for key in self.api.figureframes
                       if key not in before or key == standing)
        if standing is not None and standing in self.api.figureframes:
            # A window the close box only hides keeps its key, so a reused
            # window can be one that is off the screen: showing it is what
            # makes the redraw something the user sees.
            self.api.setWindowVisible(self.api.figureframes[standing], True)
        return {'ran': {'plugin': plugin, 'entry': entry, 'ids': ids_name,
                        'occurrence': occurrence, 'time': time},
                'reused': standing,
                'drawn': drawn,
                'windows': self.list_windows()}

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

    def new_session(self):
        """One clean session, without saving the one it takes away.

        The *New session* entry of the application's *File* menu, on the
        surface the page and the agent share: the case views and every
        figure go off the screen and out of the bookkeeping
        (`Viz_API.closeAll`, named on what it costs the run), and
        **nothing is written** -- a new session is not a save by another
        hand, and the one on disk (the user's `last_session` and the
        saved ones) is left untouched. What it closes is answered by
        name, so the transcript and the page print the same line: the
        figures the user drew are the ones it lost.
        """
        closed = self.api.closeAll()
        return {'closed': len(closed),
                'saved_to': None,
                'note': 'the clean slate, without a save: the sessions '
                        'on disk are untouched'}

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
                'in the same folder are answered by '
                'manage_session(action="list_sessions")).'
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
                'first (manage_idss(action="filled") names them, '
                'manage_idss(action="load") builds the branch).'
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

    def case_ids_report(self, uri, name=None):
        """The IDSs of one case as a self-contained HTML report.

        Three reads under one page, each of them the read the surface
        already answers -- nothing is listed from memory:

        * the case, through ``view.occurrencesOf`` (the same
          ``DBEntry.list_all_occurrences`` that colours the tree): every
          IDS the case's data dictionary declares, the occurrences each
          holds, and which of those this view loaded -- the loaded ones
          from the view's own ``loadedOccurrences``;
        * the header of every loaded occurrence, ``ids_properties``: the
          values of its fields read off the loaded instance, the same
          instance ``describe_ids`` reads -- a structure field is opened
          on its children, an empty one is named empty, and an occurrence
          whose instance this view no longer holds is named as such rather
          than answered from a guess;
        * the available signals of every loaded occurrence: the signals
          the tree holds for it -- ``view.signalsList``, the list the
          selection and the Profiles panel ask -- kept to the ones the
          tree carries as available (``hasAvailableData``, the same test
          the tree's own colouring applies), so what is blue in the tree
          is in the section and what is not blue is named out; a 0-D
          scalar held by the dynamic array (``global_quantities.ip`` on
          the reference case) is a signal the draw runs along the case's
          clock, and it is listed with the scalar type the tree reads it.

        A case that holds no data at all is refused by name, the way
        ``case_report`` refuses a loaded tree with no curve: a page whose
        only sentence is "the case holds nothing" is the refusal spoken
        as a deliverable. ``name`` is the report name under
        ``~/.imasviz/reports``, the guard ``_namedReport`` applies.
        """
        view = self._viewForUri(uri)

        summary = []
        for ids_name in sorted(view.IDSRoots):
            held = sorted(view.occurrencesOf(ids_name))
            loaded = sorted(view.loadedOccurrences(ids_name))
            if loaded:
                state = 'loaded'
            elif held:
                state = 'not loaded'
            else:
                state = 'the case holds no data for it'
            summary.append({'name': ids_name, 'held': held,
                            'loaded': loaded, 'state': state})
        if not any(row['held'] for row in summary):
            raise ValueError(
                'The case %s holds no data at all '
                '(manage_idss(action="filled") answers the same): there is '
                'nothing to report.' % uri)

        sections = []
        for key in sorted(view.ids_roots_occurrence):
            ids_name, _, occurrence = key.rpartition('/')
            occurrence = int(occurrence)
            node = view.ids_roots_occurrence[key]
            instance = getattr(node, 'idsRef', None)
            if instance is not None:
                props = self._idsPropertiesRows(instance)
                propsNote = None if props is not None else (
                    'the data dictionary of this occurrence declares no '
                    'ids_properties structure.')
            else:
                props = None
                propsNote = (
                    'this view no longer holds the loaded instance of %s '
                    'occurrence %d in memory: the header cannot be read '
                    'without a guess.' % (ids_name, occurrence))
            signals = self._availableSignals(view, ids_name, occurrence)
            sections.append({
                'ids': ids_name,
                'occurrence': occurrence,
                'properties': props,
                'propertiesNote': propsNote,
                'signals': signals,
            })

        path = self._namedReport(name, len(sections))
        self._writeIdsReport(
            path,
            title='IDSs of %s' % uri,
            sub='%d IDS(s) declared by the case, %d occurrence(s) loaded'
                % (len(summary), len(sections)),
            summary=summary, sections=sections)
        self._logFor([uri],
                     'case_ids_report wrote %s: %d IDS(s) of %s, '
                     '%d loaded occurrence(s).'
                     % (path, len(summary), uri, len(sections)))
        return {'saved_to': path, 'uri': uri,
                'idss': len(summary), 'loaded': len(sections)}

    def _idsPropertiesRows(self, instance):
        """The (field, type, value) rows of one loaded IDS occurrence.

        Read from the ``ids_properties`` structure the IDS holds -- that is
        where the fields sit, the level ``describe_ids`` reads them at: on
        this HLI the IDS root itself has no such field, and a lookup at the
        root level refused every one of them by name (measured on the
        reference case: ``IDS structure '' has no attribute 'comment'``),
        so the base of the read is the substructure and the dictionary node
        only names the fields. ``None`` when the dictionary of this
        occurrence declares no such structure.
        """
        from imasviz.VizDataAccess.QVizIDSViewParser import \
            dataTypeName, metadataForPath
        propsMeta = metadataForPath(instance.metadata, ['ids_properties'])
        if propsMeta is None:
            return None
        try:
            base = getattr(instance, 'ids_properties')
        except (AttributeError, KeyError) as error:
            return [('(all fields)', 'structure',
                     'unavailable (%s: %s)'
                     % (type(error).__name__, error), False)]
        rows = []
        for field in list(propsMeta):
            text, filled = self._propValue(base, field)
            rows.append((field.name, dataTypeName(field), text, filled))
        return rows

    def _propValue(self, instance, field, limit=8):
        """(text, filled) of one ``ids_properties`` field, for the header.

        Read off the instance, the ``describe_ids`` way: a scalar or a
        string answers its value, an array its count with a bounded
        preview of its first elements, a structure opens on its children,
        and what the read refuses or finds empty comes back named -- the
        page prints the refusal with the ``ref`` colour it wears for a
        refusal, so a value that is not there cannot read as one that is.
        """
        from imasviz.VizDataAccess.QVizAccessLayerHLI import IDSDataType
        try:
            value = getattr(instance, field.name)
        except (AttributeError, KeyError) as error:
            return ('unavailable (%s: %s)'
                    % (type(error).__name__, error), False)
        if field.data_type is IDSDataType.STRUCTURE:
            parts = []
            filled = False
            for child in list(field):
                text, childFilled = self._propValue(value, child, limit)
                parts.append('%s %s' % (child.name, text))
                filled = filled or childFilled
            return ('{ ' + '; '.join(parts) + ' }' if parts else '{ }'), filled
        plain = getattr(value, 'value', None)
        if plain is None:
            plain = value
        if isinstance(plain, bytes):
            plain = plain.decode('utf-8', 'replace')
        if isinstance(plain, str):
            return (plain if plain.strip() else '(empty)',
                    bool(plain.strip()))
        if plain is None:
            return ('(empty)', False)
        try:
            elements = list(plain)
        except TypeError:
            return (self._num(plain) if plain is not None else '(empty)',
                    plain is not None)
        if not elements:
            return ('(empty)', False)
        scalar = all(isinstance(element, (bool, int, float))
                     for element in elements[:limit])
        if not scalar:
            return ('array of %d structures' % len(elements), True)
        shown = ', '.join(self._num(element)
                          for element in elements[:limit])
        more = '' if len(elements) <= limit else ', …'
        return ('[%d] %s%s' % (len(elements), shown, more), True)

    def _availableSignals(self, view, ids_name, occurrence=0):
        """The signals the tree holds for one loaded occurrence, in tree order.

        ``view.signalsList`` -- the same list the selection, the plot
        gestures and the Profiles panel ask -- restricted to the one
        occurrence, kept to the leaves (the structures and the roots are
        not signals), and kept to the ones the tree carries as available:
        ``hasAvailableData`` is the tree's own available-data test, the one
        its colouring applies and the same panel asks a leaf before it
        offers it, so what is blue in the tree is in the list and a signal
        the case never filled is out of it. A 0-D scalar held by the
        dynamic array is a signal -- the one the draw runs along the case's
        clock (measured on the reference case:
        ``equilibrium.time_slice[0].global_quantities.ip`` answers
        ``FLT_0D``, draws a 49-sample curve along ``equilibrium.time``,
        and the arrays-only reads of a report miss it) -- and it is
        listed with the scalar type it has, rather than dropped as if the
        case did not hold it.
        """
        found = []
        for node in view.signalsList:
            try:
                if node.getIDSName() != ids_name:
                    continue
                if int(node.getOccurrence() or 0) != occurrence:
                    continue
                if node.isIDSRoot() \
                        or node.getDataType() in ('structure', 'struct_array'):
                    continue
                if not node.hasAvailableData():
                    continue
            except Exception:
                continue
            found.append({
                'data_name': node.getDataName()
                or node.getPath() or node.getName() or str(node),
                'data_type': node.getDataType() or '',
                'units': node.getUnits() or '',
            })
        return found

    def _writeIdsReport(self, path, title, sub, summary, sections):
        """The self-contained page one ``case_ids_report`` is: the case's
        IDSs under one heading, one section per loaded occurrence -- its
        ``ids_properties`` header first, its available signals under --
        the same style as the other reports, and nothing to fetch."""
        import html
        import time

        parts = [
            '<!doctype html>',
            '<html lang="en"><head><meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            '<title>%s</title><style>%s</style></head><body>' % (
                html.escape(title), _REPORT_CSS),
            '<h1>%s</h1>' % html.escape(title),
            '<p class="sub">%s — %s</p>' % (html.escape(sub),
                                            time.strftime('%Y-%m-%d %H:%M:%S')),
        ]
        parts.append('<h2>The IDSs of the case</h2>')
        parts.append('<table>')
        parts.append('<tr><th>IDS</th><th>occurrences held</th>'
                     '<th>occurrences loaded</th><th>state</th></tr>')
        for row in summary:
            parts.append(
                '<tr><td class="q">%s</td><td class="s">%s</td>'
                '<td class="s">%s</td><td class="%s">%s</td></tr>' % (
                    html.escape(row['name']),
                    ', '.join(str(o) for o in row['held']) or 'none',
                    ', '.join(str(o) for o in row['loaded']) or 'none',
                    '' if row['state'] != 'the case holds no data for it'
                    else 'ref',
                    html.escape(row['state'])))
        parts.append('</table>')
        for section in sections:
            parts.append(
                '<h2>%s — occurrence %d</h2>'
                % (html.escape(section['ids']), section['occurrence']))
            parts.append('<h3>ids_properties</h3>')
            if section['properties'] is None:
                parts.append('<p class="ref">%s</p>'
                             % html.escape(section['propertiesNote']))
            else:
                parts.append('<table>')
                parts.append('<tr><th>field</th><th>type</th>'
                             '<th>value</th></tr>')
                for name, spelling, text, filled in section['properties']:
                    parts.append(
                        '<tr><td class="q">%s</td><td>%s</td>'
                        '<td class="%s">%s</td></tr>' % (
                            html.escape(name), html.escape(spelling),
                            '' if filled else 'ref', html.escape(text)))
                parts.append('</table>')
            parts.append(
                '<h3>Available signals — %d</h3>' % len(section['signals']))
            if not section['signals']:
                parts.append(
                    '<p class="ref">The loaded tree of this occurrence '
                    'holds no signal it carries as available: the tree '
                    'carries it in no blue leaf, and the list says so '
                    'rather than naming one from memory.</p>')
            else:
                parts.append('<table>')
                parts.append(
                    '<tr><th>signal</th><th>data type</th><th>units</th>'
                    '</tr>')
                for signal in section['signals']:
                    parts.append(
                        '<tr><td class="q">%s</td><td>%s</td><td>%s</td>'
                        '</tr>' % (
                            html.escape(signal['data_name']),
                            html.escape(signal['data_type']),
                            html.escape(signal['units'])))
                parts.append('</table>')
        parts.append('</body></html>')
        try:
            with open(path, 'w', encoding='utf-8') as file:
                file.write('\n'.join(parts))
        except OSError as error:
            raise ValueError('The report could not be written to %s: %s'
                             % (path, error))

    def _writeReport(self, path, title, sub, image, rows):
        """The self-contained page the report is: one table, its own
        little style, the image when there is one, and nothing to fetch."""
        import base64
        import html
        import time

        parts = [
            '<!doctype html>',
            '<html lang="en"><head><meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            '<title>%s</title><style>%s</style></head><body>' % (
                html.escape(title), _REPORT_CSS),
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
