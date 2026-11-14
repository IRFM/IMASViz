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


# --------------------------------------------------------------------- addressing
#
# `axesAddressing` is the one answer to "which axis does this quantity run
# along, and at which index are its other axes fixed". The read
# (`get_signal`) and the figure (`plot_one`) both route through it, so they
# cannot name one element and draw another. It is a read of the axes only --
# no case open, no data read, no Qt -- and it refuses in words: an `along`
# the quantity cannot run along, an index that names no axis it holds, an
# index out of the extent the tree names, and a name that pins the very axis
# the curve is drawn along.


def _axisName(axis):
    """The one word an axis goes by.

    An array of structures goes by its array name; a leaf coordinate by the
    last node the dictionary spells -- the word a user actually knows, `psi`;
    an axis the dictionary leaves unbounded by its position among the leaf's
    axes.
    """
    from imasviz.VizDataAccess.QVizAxesSpec import QVizAxis

    if axis.origin == QVizAxis.AOS:
        return axis.name or axis.placeholder or ('level %d' % axis.level)
    if axis.coordinate:
        node = str(axis.coordinate).rsplit('.', 1)[-1].rsplit('/', 1)[-1]
        return node.split('[', 1)[0].split('(', 1)[0].strip()
    return 'dimension %d' % axis.level


def _axisWords(axis):
    """The words an axis goes by, lowercased -- its name, plus the clock words
    when it is the quantity's clock."""
    words = {str(_axisName(axis)).strip().lower()}
    if getattr(axis, 'is_time', False):
        words |= {'time', 'temps', 't'}
    return words


def _axisNamed(spec, word, exclude=None):
    """The one axis of `spec` named `word`, or None when no axis answers it.

    None is the refusal the caller says in words (naming the words the quantity
    does hold). A word that answers more than one axis is left ambiguous on
    purpose, because resolving it by first match would fix the wrong element --
    here, one of the two the user actually meant.
    """
    want = str(word).strip().lower()
    hits = [axis for axis in spec.axes
            if axis is not exclude and want in _axisWords(axis)]
    if not hits:
        return None
    if len(hits) > 1:
        raise ValueError(
            '%s answers more than one axis of %s (%s); name the full '
            'spelling that means the one you intend.'
            % (word, spec.dataPath or spec.idsName or 'this quantity',
               ', '.join('"%s"' % _axisName(a) for a in hits)))
    return hits[0]


def _holdRefusal(spec, word, exclude):
    CLOCK = {'time', 'temps', 't'}
    held = sorted({w for axis in spec.axes for w in _axisWords(axis)} - CLOCK)
    drawn = ' it runs along "%s", which is drawn, not pinned.' \
        % _axisName(exclude) if exclude is not None else ''
    return ('"%s" names no axis of %s. This quantity goes by: %s.%s '
            'Name one of those.'
            % (word, spec.dataPath or spec.idsName or 'this quantity',
               ', '.join(held) or 'none', drawn))


def _checkExtent(axis, value):
    word = str(_axisName(axis))
    try:
        index = int(value)
    except (TypeError, ValueError):
        raise ValueError(
            'the index of "%s" must be a whole number, was %r'
            % (word, value))
    if index < 0:
        raise ValueError(
            'index %d of "%s" is negative; name 0 or greater' % (index, word))
    if axis.length is not None and index >= int(axis.length):
        raise ValueError(
            'index %d of "%s" is past the %d elements that axis holds; '
            'name 0 to %d'
            % (index, word, axis.length, axis.length - 1))
    return index


def _scalarRefusal(spec):
    """The named refusal a quantity earns when nothing runs along it.

    A leaf the tree does not hold an axis for is a 0D element of an array of
    structures; a quantity with more than one axis of its own is a picture.
    Both are sayable, and both point at the gesture that would have meant it.
    """
    if not spec.leafAxes():
        return ('\"%s\" is a 0D leaf -- one value held by its array of '
                'structures, with no axis a curve runs along. The sibling '
                '".data" under the same element is usually the curve, or draw '
                'it as a table.'
                % (spec.dataPath or spec.idsName or 'this quantity'))
    return ('%s is not a curve the read can run along one axis: it carries '
            'more than one axis of its own (a picture). Name one of them in '
            '`along`, or draw it as a picture/table.'
            % (spec.dataPath or spec.idsName or 'this quantity'))


def _timeAxis(spec):
    """The axis the quantity's clock is spelled by, if it has one."""
    for axis in spec.axes:
        if getattr(axis, 'is_time', False):
            return axis
    return None


def _abscissaAxis(spec, identity):
    from imasviz.VizDataAccess import QVizCurveAbscissa as AB

    if identity == AB.TIME:
        return _timeAxis(spec)
    for axis in spec.axes:
        try:
            if AB.identityOf(axis) == identity:
                return axis
        except Exception:
            pass
    return None


def _resolveAbcissa(spec, along):
    """The identity the quantity runs along, or a named refusal.

    The options are the ones the read itself offers (`abscissae`): the clock
    when the quantity has one, and the coordinate it carries when it does.
    `along` is `None` for the first of those, a clock word for the clock, or
    the name of the axis the read can run along. Naming an axis none of them
    answers is a refusal that names the ones it does.
    """
    from imasviz.VizDataAccess import QVizCurveAbscissa as AB

    options = AB.abscissae(spec)
    if not options:
        raise ValueError(_scalarRefusal(spec))
    if along is None:
        return options[0]
    word = str(along).strip().lower()
    for option in options:
        if option == AB.TIME:
            clock = _timeAxis(spec)
            words = _axisWords(clock) if clock is not None \
                else {'time', 'temps', 't'}
            if word in words:
                return option
            continue
        ident = str(option[1]) if isinstance(option, tuple) and len(option) > 1 \
            else str(option)
        ident = ident.lower()
        if word in ident.rsplit('.', 1) \
                or word == ident \
                or word in ident.replace('.', ' ').split():
            return option
    spelled = ', '.join(sorted(_identityWord(spec, option)
                               for option in options))
    raise ValueError(
        '%s cannot run along "%s"; it runs along: %s. Name one of those.'
        % (spec.dataPath or spec.idsName or 'this quantity', along, spelled))


def _identityWord(spec, option):
    from imasviz.VizDataAccess import QVizCurveAbscissa as AB

    if option == AB.TIME:
        clock = _timeAxis(spec)
        return str(_axisName(clock)).strip() if clock is not None else 'time'
    if isinstance(option, tuple) and len(option) > 1:
        return str(option[1]).rsplit('.', 1)[-1]
    return str(option)


def axesAddressing(axesSpec, along=None, indices=None):
    """The one addressing of a quantity: the axis it runs along, and the index
    at which each of its other axes is fixed.

    `axesSpec` is the axes of the quantity. `along` is the axis it runs along
    -- `None` for the clock (or the quantity's own axis), a clock word, or the
    name of the axis it can actually be read along. `indices` holds one entry
    per axis the curve does *not* run along, by that axis's word, at its
    0-based index.

    It answers the three values the read consumes
    (`QVizTensorDataAccess.GetSignal`): the abscissa identity, the
    `as_function_of_time` flag, and the `slices` mapping keyed by axis. The
    read (`get_signal`) and the figure (`plot_one`) route through this, so a
    figure and its numbers cannot point at different elements of the same
    array.

    Named refusals: a quantity nothing runs along; a word no axis answers (or
    that answers more than one); an index past the extent the tree names; and
    a name for the axis the curve already runs along.
    """
    from imasviz.VizDataAccess import QVizCurveAbscissa as AB
    from imasviz.VizDataAccess.QVizAxesSpec import QVizAxis

    if not axesSpec.isPlottable():
        raise ValueError(_scalarRefusal(axesSpec))

    abscissa = _resolveAbcissa(axesSpec, along)
    abscissaAxis = _abscissaAxis(axesSpec, abscissa)

    # Every word `indices` names is checked before a slice is built for it, so
    # the refusal is the answer a model reads, not an empty one. A word that
    # pins the abscissa is a contradiction; a word no axis answers is a miss;
    # a value past the extent is a wrong element presented as the right one.
    for key in (indices or {}):
        word = str(key).strip().lower()
        if abscissaAxis is not None and word in _axisWords(abscissaAxis):
            raise ValueError(
                '\"%s\" is the axis the curve runs along; it is the abscissa '
                'and the abscissa is what the figure draws, not a slice to pin '
                '-- name a different axis, or run the curve along that one.'
                % key)
        axis = _axisNamed(axesSpec, word, exclude=abscissaAxis)
        if axis is None:
            raise ValueError(_holdRefusal(axesSpec, key, abscissaAxis))
        # A static (non-time) AOS with a non-zero index in the path means the
        # node IS a specific member of that family (e.g. flux_loop[1]) -- the
        # figure for it is a single curve with no slider over the other
        # members, so pinning that axis via `indices` is a no-op with an
        # unwanted side effect (a figure created only to be refused). Refuse
        # here, BEFORE the figure is opened, and point at the working move.
        if (axis.origin == QVizAxis.AOS and not axis.is_time
                and axis.index is not None and axis.index > 0):
            raise ValueError(
                '"%s" is already fixed at index %d by the path "%s": this '
                'node is one member of that family, and the figure it draws '
                'is that one member alone -- there is no slider over the '
                'other members of the family. For another member, use its '
                'own path (with into_figure_key to share the figure, or '
                'select_signals + plot_selection for a selection).'
                % (word, axis.index, axesSpec.dataPath or axesSpec.idsName or '?'))
        _checkExtent(axis, (indices or {})[key])

    slices = {}
    for axis in axesSpec.axes:
        if axis is abscissaAxis:
            continue  # the abscissa is drawn, so it takes no slice index
        named = [key for key in (indices or {})
                 if str(key).strip().lower() in _axisWords(axis)]
        if named:
            value = (indices or {})[named[0]]
        else:
            value = axis.index if axis.index is not None else 0
        slices[axis.key()] = _checkExtent(axis, value)

    return abscissa, (abscissa == AB.TIME), slices


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
                'load it first with load_ids.' % (ids_name, occurrence))
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

        Only the axes the caller fixed through `indices` need a control on
        the frame: the members the path itself picked carry no band by
        design, and drawing the member along its OWN coordinate (`along`
        named by the leaf's axis) is the read the twin `get_signal` already
        answers, not a contradiction. When a named index has no control to
        hold it, the refusal closes the figure the attempt opened before it
        is raised: a refusal costs no window, and the number that key has
        gone back to the bookkeeping.
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
        # what a named element is frozen at when it is a different element of
        # the leaf the figure already holds -- several psi slices of one profile
        # stay their own elements instead of all riding the shared control.
        named = set()
        for word in (indices or {}):
            w = str(word).strip().lower()
            for axis in axesSpec.axes:
                if w in _axisWords(axis):
                    named.add(axis.key())
        named_indices = {key: index for key, index in (slices or {}).items()
                         if key in named}
        # Does the figure this element joins already hold a curve of this leaf?
        # Then it is a sibling: frozen at its named index, and the control of
        # the element it joins is left where it sits -- moving that control to
        # this index would drag that element here, and every stacked element to
        # the last one named (the reported "several psi slices show the same
        # curve" bug). A curve of a DIFFERENT leaf is not a sibling: its control
        # stays shared, the comparable case this must not freeze.
        sibling = False
        if into_figure_key is not None:
            existing = self.api.figureframes.get(into_figure_key)
            if existing is not None:
                sibling = bool(getattr(existing, 'hasCurveOf', None)
                               and existing.hasCurveOf(node))
        command = QVizPlotOneNode(view, node, intoFigureKey=into_figure_key,
                                  alongTime=as_function_of_time,
                                  namedIndices=named_indices or None)
        frame = command.execute()
        if frame is None:
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
            # A NAMED leaf axis the figure already holds a curve of (a sibling:
            # a different element of the same array) is frozen at its index by
            # the frame, and the control of the element it joins must not be
            # moved -- moving it here would drag that element to this index, and
            # every stacked element to the last one named. A NAMED family member
            # (an array of structures) is a different element, but it is not a
            # leaf's coordinate: it is fixed by the path, and the refusal is the
            # answer, so it still goes through `setIndex`, which fails.
            if (sibling and originByKey.get(key) == QVizAxis.LEAF):
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
                'opened_at': openedAt}

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
            'path, not by indices: for another member, plot_one its own path '
            '(with into_figure_key to put it in this figure) or select_signals '
            'the two members and plot_selection. Change the call; repeating '
            'the refused one will not help.' % (path, word, word))

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

    # ---------------------------------------------------------- equilibrium

    def _equilibriumRead(self, uri, occurrence):
        """The `(view, reader)` of the `equilibrium` IDS of one open case.

        The read is the IDS-object read (the same as the Equilibrium
        plugin), so it does not walk the tree and costs one lazy `get`;
        a case that holds no `equilibrium` IDS refuses by naming its own.
        """
        view = self._viewForUri(uri)
        if 'equilibrium' not in view.IDSRoots:
            raise ValueError(
                '%s holds no equilibrium IDS, so there is no flux surface to '
                'draw: list_case_idss names the IDS this case does hold.'
                % uri)
        from imasviz.VizDataAccess.QVizEquilibriumRead import \
            QVizEquilibriumRead
        return view, QVizEquilibriumRead(view.dataSource, occurrence)

    def _newEquilibriumFigure(self, view, figure_key=None):
        """The next `EquiSurfaces:` frame, registered like every other figure.

        Allocated through `QVizPlotOneNode.newFigure` because that is the
        one place a key is handed out against the api's own bookkeeping
        (`figureframes`), which is what the *Windows* menu, its *Delete*
        sub-menu, the sessions and `list_windows` read. `figure_key` is the
        key a session replay names: `newFigure` honours it through
        `FigureKeyFor` (refusing a key a live window already holds), so the
        window comes back under the name the file said rather than a new one.
        """
        from imasviz.VizUtils import FigureTypes
        from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode \
            import QVizPlotOneNode
        from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizEquilibriumFigure \
            import QVizEquilibriumFigure
        command = QVizPlotOneNode(view, view.IDSRoots['equilibrium'],
                                  figureKey=figure_key)
        frame = command.newFigure(FigureTypes.EQUISURFACES,
                                  QVizEquilibriumFigure)
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

    def equilibrium_surfaces(self, uri, times, occurrence=0, figure_key=None):
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
        command, frame = self._newEquilibriumFigure(view, figure_key)
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

    def equilibrium_at_time(self, uri, time, occurrence=0, figure_key=None):
        """One instant of the equilibrium: its flux surface, its radial
        profiles under it, and its global quantities in the answer.

        The frame is the one the case answers for the instant -- `time`
        resolves to the nearest slice the case holds, named back through
        `time_requested` vs `time_slice_time` the way `plot_slice` says it
        -- and under the surface the stack holds, one panel per radial
        quantity the Equilibrium plugin draws (q, elongation,
        triangularities, j_tor, pressure, f_df_dpsi, dpressure_dpsi), all
        on the common abscissa the read settled (`rho_tor_norm`), with the
        group pan on. The global quantities of the slice (Ip, q95, q_axis,
        li_3, W_mhd, axis position) are values of the answer, not a drawing:
        the window has no axis to spread a scalar over.
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

        command, frame = self._newEquilibriumFigure(view, figure_key)
        try:
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
        return payload

    # -------------------------------- curves: work on the data the figure holds

    def scale_curve(self, figure_key, factor, curve=None):
        """Multiply a figure's drawn curve(s) by a constant.

        In place, on the curves the figure named, so the reader sees the
        picture change and `curve_stats` / `export_curve` read the value
        back multiplied. `curve` is `None` for every curve the figure holds,
        an index in draw order, or a quantity-name substring. `factor` must
        be a finite number, refused by name when it is not. `reset_curve`
        takes the multiplication off (or `plot_one` redraws the unmultiplied
        curve), because a transform is one of the view, not of the quantity
        in the tree. A window that holds no curve to multiply is refused by
        name, naming what it holds instead.
        """
        import math

        if (isinstance(factor, bool) or not isinstance(factor, (int, float))
                or not math.isfinite(factor)):
            raise ValueError(
                'The factor is %r: a finite number the value may be '
                'multiplied by, not a name, zero, or a boolean.' % (factor,))
        record, curves = self._curveFor(figure_key, curve)
        done = []
        for node, rank, item, source in curves:
            x, y = self._curveData(item)
            if x is None or y is None:
                continue
            self._rememberOrig(item)
            item.setData(x, y * factor)
            done.append(self._curveName(node, rank))
        if not done:
            raise ValueError(
                'The %d curve(s) of "%s" hold no number to multiply, every '
                'one being empty as it stands.' % (len(curves), figure_key))
        self._logFor(record.cases,
                     'scale_curve: %s x %g on %s.'
                     % (', '.join(done), factor, figure_key))
        return {'window': figure_key, 'factor': float(factor),
                'curves': done}

    def shift_curve(self, figure_key, offset, curve=None):
        """Add a constant to a figure's drawn curve(s): a vertical offset.

        The inverse of a subtraction; `reset_curve` takes it off. Everything
        else is the rule of `scale_curve`: in place, `curve` the one or the
        figure's, and the named refusals the figure's holds earn.
        """
        import math

        if (isinstance(offset, bool) or not isinstance(offset, (int, float))
                or not math.isfinite(offset)):
            raise ValueError(
                'The offset is %r: a finite number the value may be shifted '
                'by, not a name or a boolean.' % (offset,))
        record, curves = self._curveFor(figure_key, curve)
        done = []
        for node, rank, item, source in curves:
            x, y = self._curveData(item)
            if x is None or y is None:
                continue
            self._rememberOrig(item)
            item.setData(x, y + offset)
            done.append(self._curveName(node, rank))
        if not done:
            raise ValueError(
                'The %d curve(s) of "%s" hold no number to shift, every one '
                'being empty as it stands.' % (len(curves), figure_key))
        self._logFor(record.cases,
                     'shift_curve: %s + %g on %s.'
                     % (', '.join(done), offset, figure_key))
        return {'window': figure_key, 'offset': float(offset),
                'curves': done}

    def normalize_curve(self, figure_key, mode='max', curve=None):
        """Divide a figure's drawn curve(s) by a reference of their own.

        `mode` is `max` (divide by the largest sample -- the peak goes to 1),
        `first` (divide by the first sample, the one at index 0 -- that
        sample goes to 1), or `mean` (divide by the mean -- the mean goes to
        1); `curve` selects the curve or the figure's as elsewhere. The
        reference is read off the curve as it stands, so a shift already on
        of it is what the reference is taken from. A reference that is zero
        or not a number is refused by name -- the division is then `inf` or
        `nan`, and the reader would read a picture full of them for a
        quantity nobody divided by anything. `reset_curve` restores the
        unnormalized values.
        """
        if mode not in ('max', 'first', 'mean'):
            raise ValueError(
                'The mode is %r: max, first, or mean -- the one the value '
                'is divided by.' % (mode,))
        import numpy as np

        record, curves = self._curveFor(figure_key, curve)
        done = []
        reference = None
        for node, rank, item, source in curves:
            x, y = self._curveData(item)
            if x is None or y is None:
                continue
            values = np.asarray(y, dtype=float)
            if mode == 'max':
                reference = float(np.nanmax(values))
            elif mode == 'first':
                reference = float(values[0])
            else:
                reference = float(np.nanmean(values))
            if not (np.isfinite(reference) and reference != 0.0):
                raise ValueError(
                    'The reference of %s in the %s mode is %r: zero or '
                    'not a number, so the division is undefined (it would '
                    'be the inf or nan of a picture full of no signal). '
                    'Name a curve that holds a non-zero value to %s from.'
                    % (self._curveName(node, rank), mode, reference, mode))
            self._rememberOrig(item)
            item.setData(x, values / reference)
            done.append(self._curveName(node, rank))
        if not done:
            raise ValueError(
                'The %d curve(s) of "%s" hold no number to normalize, every '
                'the value it holds being empty.'
                % (len(curves), figure_key))
        self._logFor(record.cases,
                     'normalize_curve: %s / %s (=%g) on %s.'
                     % (', '.join(done), mode, reference, figure_key))
        return {'window': figure_key, 'mode': mode,
                'reference': float(reference), 'curves': done}

    def reset_curve(self, figure_key, curve=None):
        """Take the transforms off: put the curve(s) back to the data they
        were drawn with.

        Scale, shift and normalize each capture the drawn (x, y) on the
        first they are asked on a curve; this takes it off, and `curve`
        targets the one or the figure's as elsewhere. A curve nobody
        transformed keeps the data it was drawn with and is not in the
        answer's list: nothing to reset is refused by name, saying what is
        held as drawn already and what a re-plot would give back, so the
        caller does not mistake a clean window for an empty one.
        """
        record, curves = self._curveFor(figure_key, curve)
        restored = []
        held = 0
        for node, rank, item, source in curves:
            held += 1
            if not hasattr(item, '_imastemp_orig'):
                continue
            x, y = item._imastemp_orig
            item.setData(x, y)
            del item._imastemp_orig
            restored.append(self._curveName(node, rank))
        if not restored:
            raise ValueError(
                'No transform to take off on "%s": the %d curve(s) it '
                'holds stand as drawn (a reset asks for a curve that was '
                'scaled, shifted, or normalized, or a re-plot with '
                'plot_one).' % (figure_key, held))
        self._logFor(record.cases,
                     'reset_curve: %s back to the data as drawn, on %s.'
                     % (', '.join(restored), figure_key))
        return {'window': figure_key, 'restored': restored}

    def remove_curve(self, figure_key, curve=None):
        """Take a curve off a figure, or every one when `curve` is left out.

        The curve leaves the plot and the figure forgets it: its legend entry
        goes with it, and the figure's `curveCount` answers the rest. The
        figure is the one the curve was drawn in (a curve figure: a table and
        a stacked window each draw a panel and are not a single figure to
        remove a curve from). A name or an index no curve answers is refused
        by name, the curve(s) it does hold being said alongside, and a
        window that holds no curve is refused the same way.
        """
        record, frame = self._windowForKey(figure_key)
        if not hasattr(frame, 'removeCurve'):
            raise ValueError(
                'The window "%s" (%s) is not a single figure a curve can '
                'be removed from: it holds %s, and the figure a single '
                'curve was drawn in is what remove_curve takes.'
                % (figure_key, record.kindLabel, record.kindLabel))
        # `_curveFor` resolves what to drop; this maps it to the indices
        # of the figure's own draw order, so the curves the answer named
        # and the ones the figure forgets are the same, and a name that
        # matched several of them is one removal per match, not one that
        # names all.
        record, curves = self._curveFor(figure_key, curve)
        if curve is None:
            count = frame.removeCurve()
        else:
            indexes = []
            for node, rank, item, source in curves:
                for i, trace in enumerate(frame._curves):
                    if trace.curve is item:
                        indexes.append(i)
                        break
            if not indexes:
                raise ValueError(
                    'The named curve is not on "%s" in a place remove_curve '
                    'can take it from.' % figure_key)
            for i in sorted(indexes, reverse=True):
                frame.removeCurve(i)
            count = frame.curveCount()
        self._logFor(record.cases,
                     'remove_curve: %s left on %s.' % (count, figure_key))
        return {'window': figure_key, 'curves_left': int(count)}

    # -------------------------------- figures: the axes and the view they draw to

    def set_axis_range(self, figure_key, xmin=None, xmax=None, ymin=None,
                       ymax=None, auto=False):
        """The window (the range) of a figure's axes, set by name and number.

        Pin the abscissa's window with `xmin` and `xmax` together, the
        ordinate's with `ymin` and `ymax` together, both at once, or
        `auto=True` to clear the pins and let the view re-fit to the curves.
        Partial (one bound of a pair) is refused because a range is two
        bounds; so is a bound that is not a finite number or in the wrong
        order (`xmin` must be less than `xmax`, `ymin` less than `ymax`)
        -- an inversion is one the reader misreads. The window is what
        pyqtgraph holds on screen after the call, returned so the caller
        reads the same numbers the figure shows.

        A curve figure is one the axis set of; a table, a stacked view and
        the flux-surface figure each draw their own and are not this one,
        so naming one of them is refused by name, the shape that names the
        figure the single curve was drawn in.
        """
        import math

        record, frame = self._windowForKey(figure_key)
        box = self._viewBoxOf(frame, figure_key)

        def finite(bound, value):
            if value is None:
                return
            if (isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)):
                raise ValueError(
                    '%s is %r: a finite number the bound must be, not a '
                    'name or a boolean.' % (bound, value))

        def pair(boundA, a, boundB, b):
            if (a is not None) != (b is not None):
                raise ValueError(
                    'The axis is a pair: name %s and %s together, or leave '
                    'both out.' % (boundA, boundB))

        pair('xmin', xmin, 'xmax', xmax)
        pair('ymin', ymin, 'ymax', ymax)
        finite('xmin', xmin); finite('xmax', xmax)
        finite('ymin', ymin); finite('ymax', ymax)
        if auto and (xmin is not None or xmax is not None
                     or ymin is not None or ymax is not None):
            raise ValueError(
                '`auto` clears the manual pins and is not a bound: pick '
                'the auto ask or the manual one, not both.')

        if auto:
            box.enableAutoRange()
            xR, yR = box.state['viewRange']
            self._logFor(record.cases,
                         'set_axis_range: %s re-fits (the auto range is '
                         'back on).' % figure_key)
            return {'window': figure_key, 'auto': True,
                    'xRange': [float(xR[0]), float(xR[1])],
                    'yRange': [float(yR[0]), float(yR[1])]}

        if xmin is None and ymin is None:
            raise ValueError(
                'A range needs at least one axis to pin: x (`xmin`, '
                '`xmax`), y (`ymin`, `ymax`), or `auto=True` to clear '
                'the pins.')
        if xmin is not None and xmin >= xmax:
            raise ValueError(
                'The x range is inverted (%g >= %g): `xmin` must be less '
                'than `xmax`.' % (xmin, xmax))
        if ymin is not None and ymin >= ymax:
            raise ValueError(
                'The y range is inverted (%g >= %g): `ymin` must be less '
                'than `ymax`.' % (ymin, ymax))
        box.disableAutoRange()
        if xmin is not None:
            box.setXRange(xmin, xmax)
        if ymin is not None:
            box.setYRange(ymin, ymax)
        xR, yR = box.state['viewRange']
        self._logFor(record.cases,
                     'set_axis_range: %s pinned, x=%s, y=%s.'
                     % (figure_key,
                        '[%g..%g]' % (xmin, xmax) if xmin is not None
                        else 'left to re-fit',
                        '[%g..%g]' % (ymin, ymax) if ymin is not None
                        else 'left to re-fit'))
        return {'window': figure_key, 'pinned': True,
                'xRange': [float(xR[0]), float(xR[1])],
                'yRange': [float(yR[0]), float(yR[1])]}

    def set_log_scale(self, figure_key, x=None, y=None):
        """A log axis, by name: `x=True/False` and `y=True/False` for the
        abscissa/ordinate, going to log or linear. Leave the one you are
        not touching out, and name at least one of the two.

        The axis is the one of a curve figure -- a single figure the curves
        were drawn in, the one the range and the inset tools address. Refused
        by name: no axis named, a `True/False` the bound is not, and a log
        axis turned on where the drawn values cross zero or below (log is
        undefined there, and pyqtgraph would hide those points so the figure
        read as "no data" where it holds a half-empty axis). A shift of the
        values (a `shift_curve` to clear negative values) is the honest
        answer for a flux loop that runs through zero.
        """
        import numpy as np

        if x is None and y is None:
            raise ValueError(
                'An axis is named: `x`, `y`, or both -- `True` for log, '
                '`False` for linear.')
        for name, value in (('x', x), ('y', y)):
            if value is None:
                continue
            if not isinstance(value, bool):
                raise ValueError(
                    '%s is %r: `True` to go log, `False` to go back to '
                    'linear.' % (name, value))
        record, frame = self._windowForKey(figure_key)
        box = self._viewBoxOf(frame, figure_key)
        for axis, on in (('x', x), ('y', y)):
            if on is not True:
                continue
            values = []
            for node, rank, item, source in self._curveFor(figure_key)[1]:
                xvals, yvals = self._curveData(item)
                values.append(xvals if axis == 'x' else yvals)
            values = [np.asarray(v, dtype=float).reshape(-1)
                      for v in values if v is not None and len(v)]
            if not values:
                continue
            joined = np.concatenate(values)
            finite = joined[np.isfinite(joined)]
            if finite.size == 0:
                continue
            n_bad = int(np.sum(finite <= 0))
            if n_bad:
                raise ValueError(
                    'A log %s axis is undefined where a value is zero or '
                    'negative: %d of the %d sampled point%s read so. The '
                    'picture would hide them and read as empty where it '
                    'holds a half-empty axis, so the log ask on it is '
                    'refused, and `shift_curve` (up to the zero or above) '
                    'is the answer to give it back.'
                    % (axis, n_bad, int(finite.size),
                       '' if finite.size == 1 else 's'))
        if x is not None:
            box.setLogMode('x', bool(x))
        if y is not None:
            box.setLogMode('y', bool(y))
        logMode = list(box.state.get('logMode') or [None, None])
        self._logFor(record.cases,
                     'set_log_scale: %s, x=%s, y=%s (now %s).'
                     % (figure_key, x, y, str(logMode)))
        return {'window': figure_key, 'x': logMode[0],
                'y': logMode[1], 'logMode': logMode}

    def invert_axis(self, figure_key, x=None, y=None):
        """Invert (flip) an axis: the negative side goes the other way, and
        the reader's reading of the picture follows it.

        `x=True/False` inverts/puts back the abscissa, `y=True/False` the
        ordinate, leaving the one you do not touch out and naming at least
        one of the two. The axis is the one of a figure a single curve was
        drawn in; naming a window that is not one of those is refused by
        name. Inversion and range are independent: a range you have pinned
        keeps it where the values sit, and the picture reads reversed.
        """
        if x is None and y is None:
            raise ValueError(
                'An axis is named: `x`, `y`, or both -- `True` to invert '
                'the picture, `False` to put it back.')
        for name, value in (('x', x), ('y', y)):
            if value is None:
                continue
            if not isinstance(value, bool):
                raise ValueError(
                    '%s is %r: `True` to invert, `False` to put back.'
                    % (name, value))
        record, frame = self._windowForKey(figure_key)
        box = self._viewBoxOf(frame, figure_key)
        if x is not None:
            state = box.state
            state['xInverted'] = bool(x)
            box.setState(state)
        if y is not None:
            state = box.state
            state['yInverted'] = bool(y)
            box.setState(state)
        state = box.state
        self._logFor(record.cases,
                     'invert_axis: %s, x=%s, y=%s.'
                     % (figure_key, x, y))
        return {'window': figure_key,
                'xInverted': bool(state.get('xInverted', False)),
                'yInverted': bool(state.get('yInverted', False))}

    # -------------------------------- figures: read the numbers under the picture

    def curve_stats(self, figure_key, curve=None):
        """The numbers of a figure's drawn curves, one per curve.

        `n` the sample count, `min`/`max`/`mean`/`std` the finite minimum,
        maximum, mean and standard deviation of the values, `nan`/`inf` the
        count of the non-number entries, and -- where both x and y are
        present and the same length -- `peak_value` the largest magnitude
        the values take and `peak_at` the abscissa it sits at. The read is
        the one `get_signal` uses on the same leaf, so a figure it holds
        and its answer agree: the values of a figure of one quantity and the
        values of a tree read of the same quantity differ only by the
        transform this family of gestures has applied to the figure, not
        by a different quantity.

        `curve` targets one (an index in draw order or a name substring) or
        every curve the figure holds; the window is the one a single curve
        was drawn in, the refusal naming the window that draws a picture
        this does not stat.
        """
        import numpy as np

        record, curves = self._curveFor(figure_key, curve)
        out = []
        for node, rank, item, source in curves:
            x, y = self._curveData(item)
            entry = dict(self.curveStats((x, y)))
            label = self._curveName(node, rank)
            if x is not None and y is not None and len(y):
                xs = np.asarray(x, dtype=float).reshape(-1)
                ys = np.asarray(y, dtype=float).reshape(-1)
                if xs.size and ys.size and xs.size == ys.size:
                    mask = np.isfinite(ys)
                    if mask.any():
                        which = int(np.where(mask, np.abs(ys),
                                             0.0).argmax())
                        entry['peak_value'] = float(ys[which])
                        entry['peak_at'] = float(xs[which])
            entry['name'] = label
            entry['rank'] = int(rank)
            out.append(entry)
        if not out:
            raise ValueError(
                'The window "%s" held no curve to stat.' % figure_key)
        self._logFor(record.cases,
                     'curve_stats: %d curve(s) of %s.'
                     % (len(out), figure_key))
        return {'window': figure_key, 'count': len(out), 'curves': out}

    def export_curve(self, figure_key, curve=None, format='csv', name=None):
        """The x/y of a figure's drawn curves, as a file.

        The values as they stand -- any transform this family has put on
        them (a scale, a shift, a normalize) is in the file, so what a
        reader opens is the same as the figure the analyst sees. `curve`
        targets one or the figure's as elsewhere. `format` is `csv`
        (default: one line per sample, two when it is one curve, a header
        per curve in the label order when it is more) or `json` (one object
        per curve, the x and y arrays and the name).

        The file lands in `~/.imasviz/exports` under the guard of the
        configurations, and `name` -- when it is one -- is a name inside
        that folder, not a place (`/` in it is refused by name). A window
        that holds no curve with a value to write is refused the same way,
        saying how many it tried and how many were empty.
        """
        record, curves = self._curveFor(figure_key, curve)
        if format not in ('csv', 'json'):
            raise ValueError(
                '`format` is %r: `csv` or `json`, the shape the file '
                'comes in.' % (format,))
        rows = []
        empty = 0
        for node, rank, item, source in curves:
            x, y = self._curveData(item)
            if x is None or y is None or len(y) == 0:
                empty += 1
                continue
            rows.append((self._curveName(node, rank), x, y))
        if not rows:
            raise ValueError(
                'None of the %d curve(s) of "%s" holds a value to write '
                '(the %d it tried all stand empty as they are).'
                % (len(curves), figure_key, empty))
        path = self._namedExport(name, format, len(rows))
        if format == 'csv':
            with open(path, 'w', newline='') as file:
                for label, x, y in rows:
                    file.write('# %s\n' % label)
                    for i in range(len(y)):
                        file.write('%r,%r\n' % (x[i], y[i]))
        else:
            import json

            with open(path, 'w') as file:
                json.dump(
                    {'window': figure_key,
                     'curves': [{
                         'name': label,
                         'x': [float(value) for value in x],
                         'y': [float(value) for value in y]}
                        for label, x, y in rows]},
                    file, indent=2)
        self._logFor(record.cases,
                     'export_curve wrote %s: %d curve(s) of %s.'
                     % (path, len(rows), figure_key))
        return {'saved_to': path, 'curves': len(rows),
                'empty': int(empty)}

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

    # ------------------------------------------------------- focus, readably

    def focus_window(self, window='app', width=None, height=None):
        """Bring a window forward at a readable size -- the preparation of a
        screenshot.

        `screenshot` paints the window whatever size it is; a figure drawn
        behind the others, or taken off the screen, reads small in the
        picture. This puts it back: shown (the hide rule of the close box is
        undone through `setWindowVisible`), raised to the front, and resized
        to `width` x `height` -- or to `DEFAULT_FIGURE_SIZE`, the same
        constant the embed hands a frame that never got one
        (`Viz_API.addPlotWidgetToMDI`). "app" is the main window: it is
        raised and answers its own size, and no figure is touched.

        `width` and `height` are named refusals when they are not positive
        integers: a size is a pair of pixel counts, and a number the window
        cannot hold is one the caller mislabeled.
        """
        def side(name, value):
            try:
                number = int(value)
            except (TypeError, ValueError):
                raise ValueError(
                    '%s=%r is not a pixel count: name it as an integer, '
                    'or leave it out for the default size.'
                    % (name, value))
            if number < 1:
                raise ValueError(
                    '%s=%d has no room to be a window: name %d pixels '
                    'and up, or leave it out.' % (name, number, 1))
            return number

        from imasviz.Viz_API import DEFAULT_FIGURE_SIZE
        target = self._resolveWindow(window)
        if window == 'app':
            target.raise_()
            if callable(getattr(target, 'activateWindow', None)):
                target.activateWindow()
            return {'window': window,
                    'visible': bool(target.isVisible()),
                    'size': [target.width(), target.height()]}

        width = side('width', width) if width is not None else DEFAULT_FIGURE_SIZE[0]
        height = side('height', height) if height is not None else DEFAULT_FIGURE_SIZE[1]
        visible = self.api.setWindowVisible(target, True)
        shell = self.api.mdiWindowOf(target)
        if shell is not None:
            # The shell is the window the user would see: it carries the
            # title bar, so it is what is raised and resized -- the frame it
            # holds follows through its own layout.
            shell.resize(width, height)
            shell.raise_()
            shell.activateWindow()
        else:
            target.resize(width, height)
            target.raise_()
        size = target.size()
        return {'window': window,
                'visible': bool(visible),
                'size': [size.width(), size.height()]}

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

    def _curveFor(self, figure_key, curve=None):
        """(record, [(node, rank, curve, source)]) for the requested curve.

        `curve` is `None` (every trace the window drew), an index in draw
        order (top of the legend to bottom), or a substring of a quantity's
        name as read from its node. Refused by name: a window that holds no
        curve, a curve index past the last it holds, a curve name it does not
        hold, a curve selector that is not one of the three. For a curve
        figure the `source` is the figure itself; for a window of panels, one
        panel per curve. `record` is the window record the refusal or log
        names, so the log line and the error both say which window it was.
        """
        record, frame = self._windowForKey(figure_key)
        pairs = []
        for source in self._sourcesOf(frame):
            for node, rank, item in self._tracesOf(source):
                pairs.append((node, rank, item, source))
        if not pairs:
            raise ValueError(
                'The window "%s" (%s) holds no curve to work on.'
                % (figure_key, record.kindLabel))
        if curve is None:
            return record, pairs
        if isinstance(curve, bool):
            raise ValueError(
                '"' + str(curve) + '" is a true/false answer; the curve to '
                'work on is a name, a 0-based index, or left out for every '
                'curve the figure holds.')
        if isinstance(curve, int):
            if not (0 <= curve < len(pairs)):
                names = ', '.join(self._nodeLabel(p[0]) for p in pairs)
                raise ValueError(
                    'curve=%d is out of range: "%s" holds %d curve(s) '
                    '(0 to %d): %s.'
                    % (curve, figure_key, len(pairs), len(pairs) - 1, names))
            return record, [pairs[curve]]
        if isinstance(curve, str):
            needle = curve.strip().lower()
            if not needle:
                raise ValueError('A curve name is the substring of a '
                                 'quantity, not the empty string.')
            names = []
            matched = []
            for node, rank, item, source in pairs:
                label = self._nodeLabel(node)
                names.append(label)
                if needle in label.lower():
                    matched.append((node, rank, item, source))
            if not matched:
                seen = []
                for n in names:
                    if n not in seen:
                        seen.append(n)
                raise ValueError(
                    'No curve of "%s" names "%s"; its traces are: %s.'
                    % (figure_key, curve, ', '.join(seen) or 'none'))
            return record, matched
        raise ValueError(
            'The curve is a substring of a quantity name or a 0-based '
            'index into the traces the figure drew, not %r.' % (curve,))

    def _viewBoxOf(self, frame, figure_key=None):
        """The single axis set of a curve figure: `pgPlotWidget`'s ViewBox.

        A curve figure (a QVizCurvePlot) has one plot widget and one axis
        set; a table and a stacked window have one panel per picture, and
        the flux-surface figure draws its own plot inside a graphics
        layout -- none of them have the single `pgPlotWidget.getViewBox()`
        this asks for, and the refusal says why, so the caller learns the
        window is not one the figure-axes tools address.
        """
        pgPlot = getattr(frame, 'pgPlotWidget', None)
        if pgPlot is None or not hasattr(pgPlot, 'getViewBox'):
            raise ValueError(
                'The window "%s" draws no single figure whose axes a range, '
                'a log scale, or an inversion can be set on: a curve figure '
                'does, and the table panels and the flux-surface figure do '
                'not. Name the figure the single curve was drawn in.'
                % (figure_key or 'this window'))
        return pgPlot.getViewBox()

    @staticmethod
    def _curveName(node, rank):
        """The name a manipulated curve carries in an answer.

        The label of the quantity it came from, and its rank among the
        traces that quantity drew when more than one -- the one the legend
        shows and the session files it by.
        """
        label = McpGuiCore._nodeLabel(node)
        return label if rank == 0 else '%s (trace %d)' % (label, rank)

    @staticmethod
    def _rememberOrig(curve):
        """The first call on a curve captures its (x, y) under a marker,
        so `reset_curve` can take the transform off. Subsequent calls leave
        the original it was first asked off, which is the composition the
        analyst expects: scale then shift is scale and then shift, not
        both asked in parallel from the original."""
        try:
            if not hasattr(curve, '_imastemp_orig'):
                curve._imastemp_orig = (curve.xData, curve.yData)
        except Exception:
            pass

    def _namedExport(self, name, ext, count):
        """The file an export writes: under `~/.imasviz/exports`, the guard
        of the configurations, and the name the caller said -- or the one
        the export is, when it said none. `ext` is the extension it writes
        with (`csv` or `json`), and the name that ends in it is stripped
        so the file is `name.csv` under `~/.imasviz/exports` either way."""
        import os
        import time

        home = os.environ.get('HOME')
        if not home:
            raise ValueError(
                'No HOME in the environment: the exports folder under it '
                'cannot be named.')
        folder = os.path.join(home, '.imasviz', 'exports')
        if not os.path.isdir(folder):
            os.makedirs(folder)
        typed = (name or '').strip()
        if typed.endswith('.' + ext):
            typed = typed[:-(len(ext) + 1)]
        if not typed:
            typed = 'export-' + time.strftime('%Y%m%d-%H%M%S') + '-%d' % count
        if os.path.sep in typed or (os.path.altsep and os.path.altsep
                                    in typed) or typed in ('.', '..'):
            raise ValueError(
                '"%s" is not a file name: it names a place, not an export. '
                'Name one inside %s.' % (name, folder))
        path = os.path.join(folder, typed + '.' + ext)
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

    def _resolveWindow(self, window):
        """The widget holding a named window: the app, a figure key, a case URI.

        The one reading `screenshot` and `focus_window` share: "app" is the
        session's main window, a key is the frame registered under it, and a
        URI is that case's shot view. A name none of the three holds is
        refused from `list_windows` itself, the one the *Windows* menu
        draws. The refusal names what IS open, so the model can see the
        right key without inventing another guess.
        """
        if window == 'app':
            if self.main_window is None:
                raise ValueError(
                    'No application window to capture: this session was '
                    'built without one -- name a figure key or a case URI.')
            return self.main_window
        if window in self.api.figureframes:
            return self.api.figureframes[window]
        # Try as a case URI; _viewForUri raises when the case is not open,
        # which is the right outcome for a name that is neither a figure key
        # nor an open case.
        try:
            view = self._viewForUri(window)
        except ValueError as exc:
            # Re-frame the refusal: the caller guessed a figure key; name
            # the figure keys that ARE open so the model can correct the
            # guess without asking the user.
            openFigures = [k for k in self.api.figureframes]
            openCases = [getattr(v.dataSource, 'uri', None)
                         for v in self.api.DTVlist
                         if getattr(v.dataSource, 'uri', None)]
            raise ValueError(
                '"%s" is not an open figure key (%s) or an open case '
                '(holdings: %s). list_windows shows what is open.'
                % (window,
                   ', '.join('"%s"' % k for k in openFigures) or 'none',
                   ', '.join('"%s"' % u for u in openCases) or 'no case open'))
        for frame in self.api.DTVframeList:
            if frame.dataTreeView is view:
                return frame
        raise ValueError(
            '"%s" is a case that is open but has no shot view frame -- '
            'list_windows names the figures.' % window)

    def screenshot(self, window='app'):
        """One window as PNG: the application, a figure key, or a case URI,
        as it stands.

        `QWidget.grab()` renders the window without asking it to be anywhere
        in particular -- the same reading the theme tests in the suite use
        to sample pixels without entering the paint-queue hazard -- and an
        offscreen application is the one this is asked of first. The
        picture is the size the window is, and no bigger: `focus_window`
        exists to give a window a readable size before it is asked for.
        """
        target = self._resolveWindow(window)
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
