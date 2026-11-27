# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The case gestures of one IMASViz session: opening, listing, and walking a case.

Open the case the way the application does, list what it holds, load an IDS occurrence, draw the selection and read what the tree holds -- the read side of the core, with no figure and no window. A refusal is the named `ValueError` the caller gets back.
"""

from imasviz.VizAgent.core import FIRST, _SLICERS

class CaseOps:
    """One case: its opening, its lists, its selection and its reads."""

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
                'Not found in the tree of %s: %s -- inspect_tree('
                'action="search") names what this case can give, in every '
                'spelling it holds.'
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

    def describe_ids(self, uri, ids_name, occurrence=0):
        """What the data dictionary says about an IDS: comment, homogeneous_time,
        units, time_units, and the data dictionary version the case was written at.

        `ids_properties` is a structure embedded in every IDS; the values are read
        from the IMAS instance of that occurrence. An IDS the case does not hold
        is refused by name, and a property the case does not fill is absent from
        the answer rather than invented.
        """
        view = self._viewForUri(uri)
        if ids_name not in view.IDSRoots:
            available = sorted(view.IDSRoots)
            raise ValueError(
                'The "%s" IDS is not declared in the case %s -- it holds: %s.'
                % (ids_name, uri, ', '.join('"%s"' % n for n in available)
                   or 'none'))
        occKey = '%s/%s' % (ids_name, occurrence)
        root = view.ids_roots_occurrence.get(occKey)
        idsInstance = getattr(root, 'idsRef', None) if root else None
        if idsInstance is None:
            raise ValueError(
                'The "%s" IDS occurrence %s is not loaded in this view: '
                'load it first with manage_idss(action="load").'
                % (ids_name, occurrence))
        props = getattr(idsInstance, 'ids_properties', None)
        if props is None:
            raise ValueError(
                'The "%s" IDS has no ids_properties in its data dictionary.'
                % ids_name)
        answer = {'name': ids_name, 'occurrence': occurrence}
        # comment: the node's documentation, which is ids_properties.comment
        comment = root.getDocumentation()
        if not comment:
            try:
                comment = str(getattr(props, 'comment', '') or '')
            except Exception:
                comment = ''
        if comment:
            answer['comment'] = comment
        # homogeneous_time: set on the occurrence-root node when the tree is built
        ht = root.getHomogeneousTime()
        if ht is None:
            try:
                ht = int(getattr(props, 'homogeneous_time', 1))
            except Exception:
                ht = 1
        answer['homogeneous_time'] = int(ht)
        # units
        units = root.getUnits()
        if units:
            answer['units'] = units
        # time_units
        try:
            tu = str(getattr(props, 'time_units', '') or '')
            if tu:
                answer['time_units'] = tu
        except Exception:
            pass
        # data dictionary version
        try:
            vp = getattr(props, 'version_put', None)
            if vp is not None:
                dd = str(getattr(vp, 'data_dictionary', '') or '')
                if dd:
                    answer['data_dictionary'] = dd
        except Exception:
            pass
        # is_dynamic
        if hasattr(root, 'ids_is_dynamic'):
            answer['is_dynamic'] = bool(root.ids_is_dynamic)
        return answer

    def list_quantities(self, uri, ids_name, occurrence=0):
        """The filled tensors (dimension >= 1) of one occurrence, grouped by the
        array of structures that drives them.

        One entry per **quantity**: the leaf that the tree stands on, its path,
        its units, its data type, and how many elements of its array the case
        holds. A quantity that contains no data (not blue in the tree) is not
        listed, and the scalar leaves (0D) are not tensors and are not listed
        either. This is the "what can be drawn" answer, read off the same tree
        the panel walks, so the count here and the count the panel shows agree.
        An occurrence whose tree was never built is refused by name.
        """
        view = self._viewForUri(uri)
        if ids_name not in view.IDSRoots:
            available = sorted(view.IDSRoots)
            raise ValueError(
                'The "%s" IDS is not declared in the case %s -- it holds: %s.'
                % (ids_name, uri, ', '.join('"%s"' % n for n in available)
                   or 'none'))
        from imasviz.VizPlugins.viz_Profiles.viz_profiles.QVizProfileOffer \
            import QVizProfileOffer
        offer = QVizProfileOffer(view, ids_name, occurrence)
        groups = offer.groups()
        result = []
        for group in groups:
            quantities = []
            for leaf in group.leaves:
                if leaf.is0D():
                    continue
                if not leaf.hasAvailableData():
                    continue
                quantities.append({
                    'path': leaf.getPath(),
                    'data_name': leaf.getDataName(),
                    'parametrized': leaf.getParametrizedDataPath(),
                    'units': leaf.getUnits() or '',
                    'data_type': leaf.getDataType() or '',
                    'elements': group.elementsOf(leaf),
                })
            if quantities:
                result.append({
                    'label': group.label or '(no array of structures)',
                    'along_time': bool(group.alongTime),
                    'quantity_count': len(quantities),
                    'quantities': quantities,
                })
        return {
            'ids': ids_name,
            'occurrence': occurrence,
            'total_quantities': sum(g['quantity_count'] for g in result),
            'groups': result,
        }
