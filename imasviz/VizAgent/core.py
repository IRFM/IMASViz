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

# A curve figure carries at most this many event marks: past it, a mark per
# event is a wall, and the report is the shape that many events want.
EVENT_MARKER_CAP = 40


# The little style every report wears: self-contained, no fetch, the same
# ground on every page. `.ref` is the word for what the read refused or
# found empty, so the page says so in the same colour a refusal does.
_REPORT_CSS = """
body { font-family: Cantarell, 'Open Sans', 'DejaVu Sans', sans-serif;
       margin: 2rem; color: #182430; background: #ffffff; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #dde3e7; padding: .35rem .6rem;
         text-align: left; font-size: .95rem; }
th { background: #f0f4f5; }
h2 { margin-top: 1.8rem; border-bottom: 1px solid #dde3e7; padding-bottom: .2rem; }
.q  { font-family: 'DejaVu Sans Mono', monospace; font-size: .85rem; }
.s  { font-variant-numeric: tabular-nums; }
img { max-width: 90%; border: 1px solid #dde3e7; margin-bottom: 1.2rem; }
.sub { color: #5a6672; margin-top: .1rem; }
.ref { color: #a03030; }
"""


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


# ------------------------------------------------------------------ figures
#
# `resolveFigureKey` is the one answer to "which window does the user mean
# when they name a figure by the way a person names it". The held keys spell
# the application's own kind and number (`Plot3`, `TablePlotView:1`,
# `SlicesPlot3`); the user spells the number ("plot3", "3"), or the newest
# ("la dernière figure"). The core reaches it before it shows a window or
# grabs a frame (a show, a screenshot), and the capture of a turn reaches it
# before it saves a PNG -- the two must resolve the same name to the same
# key, or a "montre-moi plot3" that shows one figure would save another.
#
# A name that names several figures is not a guess to settle but an ask that
# stands refused: the loop answers every such ask in words, and the caller
# corrects the call with the one it meant.


def _figureNumber(key):
    """The number a figure key ends with: `Plot3` is 3, `TablePlotValue:1`
    is 1, `EquiPlotView:12` is 12. No digits, no number -- the kind is a
    word and the number is at its end."""
    import re

    found = re.findall(r'\d+', str(key))
    return int(found[-1]) if found else None


def _figureIsLast(reference):
    """Whether a figure reference points at the newest: "last", "the last
    figure", "la dernière figure". Asked of the reference as it stands, so
    the caller spells it the way the user does."""
    import re

    text = (reference or ' ').strip().lower()
    return bool(re.search(r'\blast\b', text)) or \
        ('dernier' in text or 'dernière' in text or 'derniere' in text)


# A loose reference with no number is a word a person uses for a figure --
# in the languages the user speaks the window to. It is what separates "the
# figure" from a name the session does not hold: the former is a reference
# the sole open figure answers, the latter a fabricated key, and resolving a
# fabricated key to the only window that happens to be open is a wrong guess
# reaching a wrong window silently.
_FIGURE_WORDS = frozenset((
    'figure', 'figures', 'figure', 'figures', 'figure', 'figures',
    'plot', 'plots', 'plot', 'plots', 'image', 'images', 'table', 'tables',
    'stack', 'stacks', 'stacked', 'courbe', 'courbes', 'curve', 'curves',
    'vue', 'fenetre', 'fenêtre', 'graph', 'graphe', 'graphique', 'graphiques',
    'diagram', 'diagramme', 'diagrammes', 'schéma', 'schema'))


def _figuresMention(name):
    """Whether a figure reference names a figure: at least one word of it is
    a word a person uses for a figure, in the languages the report is in."""
    import re

    words = re.findall(r'[a-zà-öø-ÿ]+', (name or ' ').lower())
    return bool(words) and any(word in _FIGURE_WORDS for word in words)


def resolveFigureKey(name, held, order=None):
    """The one held key a loose figure reference stands for.

    `held` is the collection of the keys the session holds; `order`, when
    named, is their creation order (earliest to latest) and is what a "last"
    reference takes -- the newest figure -- and it is the order the caller
    already keeps when it is left out. The same function serves the core
    (where `held` is the session's own figure keys) and the capture of a
    turn (where a stand-in holds what it holds), so the two cannot drift.

    A key the session answers exactly is the one it is. A reference with a
    number is the one figure the session holds at that number, the kind the
    number already fixes, and the number the user spells however --
    "plot3", "3", "figure 3". A reference with no number and not "last"
    names a figure -- at least one word of it is a word a person uses for a
    figure ("figure", "plot", "la table") -- and is the only open figure
    when there is one.

    A name no figure word in it mentions at all is not a reference but a
    fabricated key, and it is refused, naming the figures the session does
    hold -- handed over to the only window that happens to be open, the
    wrong guess would reach a wrong window silently, and the model would
    believe it asked for the window it named. When there are several open
    figures the no-number name is refused the same way.
    `tests/test_100` pins the refusal at the screenshot and `tests/test_146`
    the loose side of the line.
    """
    held = list(held)
    if name in held:
        return name
    if not held:
        raise ValueError(
            '%r is not a figure this session holds: it holds none open'
            % (name,))
    if _figureIsLast(name):
        ordered = list(order) if order is not None else held
        return ordered[-1]
    import re

    numbers = re.findall(r'\d+', (name or ' '))
    if numbers:
        number = int(numbers[-1])
        matches = [key for key in held
                   if _figureNumber(key) == number]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(
                '%r names several open figures -- %s -- name the one you '
                'mean among them' % (name, ', '.join(sorted(matches))))
        raise ValueError(
            'no open figure is numbered %d -- the session holds: %s'
            % (number, ', '.join(sorted(held))))
    if len(held) == 1 and _figuresMention(name):
        return held[0]
    raise ValueError(
        '%r does not name one of the open figures -- the session holds: %s'
        % (name, ', '.join(sorted(held))))


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

        A curve figure takes one axis set. A picture window takes the same
        span on the axis set of **each** of its pictures -- the window is
        one scale and one span, so a time zoom of a strip whose abscissa is
        its time is the `x` range, in the seconds its time axis holds, and
        the answer reports that one span. A table and a stacked view keep
        one axis set per panel and are refused by name.
        """
        import math

        record, frame = self._windowForKey(figure_key)
        boxes = self._viewBoxesOf(frame, figure_key)

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
            for box in boxes:
                box.enableAutoRange()
            xR, yR = boxes[0].state['viewRange']
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
        for box in boxes:
            box.disableAutoRange()
        for box in boxes:
            if xmin is not None:
                box.setXRange(xmin, xmax)
            if ymin is not None:
                box.setYRange(ymin, ymax)
        xR, yR = boxes[0].state['viewRange']
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

    def set_image_window(self, figure_key, start=None, count=None):
        """The window a figure's pictures sit on: moved, or resized, by name.

        `start` is where the window sits on the axis it reads across -- the
        pictures are re-read in place, one of them per element, and the scale
        and the controls stay put while the window moves; `count` is how
        many pictures the window holds and the resize rebuilds them on the
        same start, the same pinned axes, and the scale a hand settled.
        The ask names neither bound and is refused: a window someone moved
        is named by where it sits and how wide it is, and an ask that says
        nothing is not a move the window can answer.

        The answer is the state the window holds after the call -- the axis
        it reads across, its start and its count, the extent the axis holds,
        and the label of each picture the window shows, the element it is
        and, when the axis carries a value at that element (a time axis does),
        the value it carries, so a window of three pictures answers the three
        elements it holds and the answer is the same numbers the titles of
        the pictures spell.

        Refused by name, and each refusal says the shape of the window that
        was tried and the gesture that answers the question instead of
        repeating the one that failed: a window that is not an image window
        has no pictures and no axis read across them; an image window that
        holds a single picture has no window to move or resize, and the span
        of that one picture is the axis range -- `set_axis_range` -- of the
        axis it drew; a `start` or `count` past the extent the axis holds is
        the extent itself, named, not a slip past it.
        """
        record, frame = self._windowForKey(figure_key)
        pictures = getattr(frame, 'plotItems', None)
        if not callable(pictures):
            # Naming the shape the window holds is what tells the caller
            # which gesture it asked -- the curves one, or the panels' own.
            pgPlot = getattr(frame, 'pgPlotWidget', None)
            if pgPlot is not None and hasattr(pgPlot, 'getViewBox'):
                raise ValueError(
                    'The window "%s" is a figure of curves: it holds traces, '
                    'not a window of pictures, so there is no window to move '
                    'or resize on it, and the span of its axes is the one '
                    'set_axis_range pins. Name the figure the pictures were '
                    'drawn in.' % figure_key)
            raise ValueError(
                'The window "%s" is not an image window: it is not a figure '
                'of pictures, so there is no window of them to move or '
                'resize, and the panels it holds each keep their own '
                'answers. Name the figure the pictures were drawn in.'
                % figure_key)
        sl = getattr(frame, 'frameAxis', None)
        sl = sl() if callable(sl) else None
        if sl is None:
            raise ValueError(
                'The window "%s" holds one picture, not a window of them: '
                'it was not read across an axis, so there is no window to '
                'move or resize, and the span of the one it holds is what '
                'set_axis_range pins on the axis it drew.' % figure_key)
        controls = getattr(frame, 'framesControls', None)
        if controls is None:
            raise ValueError(
                'The window "%s" is an image window but holds no control on '
                'the axis it reads across, so the window there is not one '
                'that can be moved or resized.' % figure_key)
        if start is None and count is None:
            raise ValueError(
                'A window moved, or resized: `start` is where it sits on '
                'the axis it reads across, `count` how many pictures it '
                'holds -- and naming neither says nothing the window can '
                'answer.')
        if start is not None:
            try:
                start = int(start)
            except (TypeError, ValueError):
                raise ValueError(
                    'The window sits on the axis its pictures are '
                    'elements of, at a whole element: %r is not one.'
                    % (start,))
            if start < 0:
                raise ValueError(
                    'The window sits from element 0 of the axis its '
                    'pictures are elements of, and %d is before it.'
                    % start)
            if length_known := (getattr(sl, 'length', None) is not None):
                extent = int(sl.length)
                if start >= extent:
                    raise ValueError(
                        'The axis this window reads across holds %d '
                        'elements (0 to %d), and %d is past the last one: '
                        'a window with no picture to draw would be blank '
                        'to the eye and blank to the answer.'
                        % (extent, extent - 1, start))

        if count is not None:
            # The resize is the window's own: it derives the slider's reach
            # from the new count and rebuilds the pictures on the start the
            # window holds, refusing by name a count the axis cannot hold.
            frame.frameCount(count)
        if start is not None:
            frames = controls.setStart(start)
            if frames is False:
                raise ValueError(
                    'The window "%s" has no control on the axis its '
                    'pictures are elements of, so a position to sit it at '
                    'is not one it holds.' % figure_key)

        count_actual = int(controls.count())
        start_actual = int(controls.start())
        length = None if getattr(sl, 'length', None) is None \
            else int(sl.length)
        # The label of each picture the window shows -- the element it is,
        # and the value the axis carries at that element when it carries
        # one. A time axis does, and a window of three slices is the only
        # way to compare them, so the answer says the three times, not
        # three element ranks. The value is read once, and the label is
        # posed on it per element, in the same shape the titles of the
        # pictures spell.
        axis = getattr(sl, 'axis', None)
        values = None
        if axis is not None and getattr(axis, 'is_time', False):
            try:
                from imasviz.VizDataAccess.QVizTensorDataAccess \
                    import QVizTensorExtractor
                node = frame.treeNode()
                axesSpec = frame.accessFor(node).plan(
                    node, frame, as_function_of_time=False)[0]
                values = QVizTensorExtractor(node.getIDSRef()).timeBase(axesSpec)
            except Exception:
                values = None
        images = []
        for index in range(start_actual, start_actual + count_actual):
            if values is not None:
                from imasviz.VizDataAccess.QVizSlices import frameLabel
                images.append(frameLabel(axis, index, values))
            else:
                images.append(index)
        self._logFor(record.cases,
                     'set_image_window: %s moved to start=%d, %d picture(s) '
                     'of the %s it reads across.'
                     % (figure_key, start_actual, count_actual,
                        getattr(sl, 'label', 'axis')))
        return {'window': figure_key,
                'axis': getattr(sl, 'label', None),
                'start': start_actual,
                'count': count_actual,
                'length': length,
                'pictures': images}

    def set_slice_index(self, figure_key, axis=None, index=None):
        """The slider of a band, posed at a named index, on the window
        that holds the band.

        `axis` is the row of the band the gesture names -- `time_slice`,
        `psi`, `profiles_2d` -- in the words the band spells the axis in,
        and `index` is the element the row is posed at, the bound the row
        holds being the one a refusal names when the index passes it. The
        row moves the band the way the user moves it: the slider of the
        row, and the window re-reads the one the row is posed at, without
        the other rows moving under them.

        The answer is the state the band holds after the call: the rows
        it is, the one that moved, the index it is posed at, and its
        length -- so the caller reads back the state the window holds,
        and a row the band holds that the gesture did not move says so
        in the answer, not in a guess.

        Refused by name, each refusal saying the shape of the window
        that was tried and the gesture that answers the question instead
        of repeating the one that failed: a window not one the band of
        the gesture sits on (a table keeps one answer per panel, and a
        stacked window one per panel of the two); a window that is a
        picture window but holds no band for it (a strip whose axis the
        pictures were laid on is on screen, side by side, and is what
        the `set_image_window` gesture moves and resizes -- there is no
        row for an axis the window already shows); a window that holds
        the band but not the axis it was asked to move (the rows it does
        hold are the ones the refusal names, and the span of the axis it
        drew is `set_axis_range`); an index outside the extent the row
        holds (the bound it holds, named, not a slip past it).
        """
        record, frame = self._windowForKey(figure_key)

        def _framesPointer():
            # The axis the pictures are laid across: it is already on
            # screen, one picture per element, so a row of a band would
            # ask for what the window shows -- the window it sits on is
            # what `set_image_window` moves and resizes. The frame axis
            # is a QVizSlice; its `label` is the `sliceLabel` of the
            # axis underneath it, already spelled the way the band
            # spells the axes it holds.
            sl_axis = getattr(frame, 'frameAxis', None)
            sl_axis = sl_axis() if callable(sl_axis) else None
            word = (str(sl_axis.label)
                    if sl_axis is not None else 'the strip')
            return ValueError(
                'The window "%s" holds no row for that axis: its '
                'pictures are the axis it reads across (here %s), one '
                'picture per element, side by side, and the window '
                'they sit on is what set_image_window moves (start) '
                'and resizes (count) -- a row of a band is not one '
                'for an axis the window already shows.'
                % (figure_key, word))

        def _frameAxisWord():
            sl_axis = getattr(frame, 'frameAxis', None)
            sl_axis = sl_axis() if callable(sl_axis) else None
            return str(getattr(sl_axis, 'label', '')
                       or '') if sl_axis is not None else ''

        frames_key = getattr(frame, 'framesKey', None)
        frames_key = frames_key() if callable(frames_key) else None
        sliceControls = getattr(frame, 'sliceControls', None)
        if sliceControls is None:
            raise ValueError(
                'The window "%s" is not one the band of sliders of the '
                'gesture sits on: a curve figure of one axis is (the rows '
                'of the band the gesture addresses), an image window is '
                '(one row per axis it pins), and this one is not, holding '
                'no band and no row to move. Name the curve figure, or '
                'the image window, that holds the axis.' % figure_key)
        rows = list(sliceControls.rows())
        word = str(axis if axis is not None else '').strip().lower()
        if not rows:
            fa_word = _frameAxisWord()
            if frames_key is not None:
                if not word or word == fa_word:
                    # The axis the gesture named is the one the window
                    # is read across, or it is not one at all: the
                    # refusal is the one that moves the window, and it
                    # names the axis the window moves on.
                    raise _framesPointer()
                # The axis is drawn inside the pictures, where a slider
                # would sit under it: it is on screen, not a control,
                # and its span is the range set_axis_range pins on each
                # of the pictures.
                raise ValueError(
                    'The window "%s" holds no row for that axis: it is '
                    'drawn inside the pictures, and a slider under an '
                    'axis that is on screen would move a window the '
                    'picture already shows. Its pictures are the axis the '
                    'window is read across (here %s), which is what '
                    'set_image_window moves (start) and resizes (count); '
                    'the span of the axis it drew is what set_axis_range '
                    'pins, on each of its pictures.'
                    % (figure_key, fa_word or 'the strip'))
            raise ValueError(
                'The window "%s" holds no band of sliders: the axes it '
                'pins are none, so the axis the gesture names is not a '
                'row of it, and the one it drew is on screen rather than '
                'a control to move -- the span of the axes it drew is '
                'what set_axis_range pins.' % figure_key)
        if not word:
            raise ValueError(
                'The axis of the row to move is named in the words the '
                'band spells the axes it holds, not the empty string: %s.'
                % ', '.join(sorted(row.label for row in rows)))
        if frames_key is not None and word == _frameAxisWord():
            # The axis the pictures are laid across is already on
            # screen: a row for it would ask for what they show.
            raise _framesPointer()
        exact = [row for row in rows
                 if str(row.label).strip().lower() == word
                 or str(row.key).strip().lower() == word]
        if exact:
            row = exact[0]
        else:
            partial = [row for row in rows
                       if word in str(row.label).strip().lower()
                       or word in str(row.key).strip().lower()]
            if not partial:
                raise ValueError(
                    'The band of the window "%s" holds: %s -- "%s" names '
                    'no row this band holds. Name one of the rows of the '
                    'band this figure holds, in the words the band spells '
                    'the axis it pins.'
                    % (figure_key,
                       ', '.join(sorted(row.label for row in rows)),
                       axis))
            if len(partial) > 1:
                raise ValueError(
                    '"%s" names several rows of the band of the window '
                    '"%s": %s -- name the one, in full, that the gesture '
                    'is moving.'
                    % (axis, figure_key,
                       ', '.join(sorted(row.label for row in partial))))
            row = partial[0]
        try:
            index = int(index)
        except (TypeError, ValueError):
            raise ValueError(
                'The index of the row "%s" is a whole number, not %r: the '
                'row holds a range from 0 to its extent, and a value in '
                'that range is what the row is posed at.'
                % (row.label, index))
        if row.length is not None:
            bound = max(int(row.length), 1)
            if index < 0 or index >= bound:
                raise ValueError(
                    'The row "%s" of the window "%s" holds an element '
                    'from 0 to %d, and %d is outside it: the bound the '
                    'row holds is the one the row holds, not a guess '
                    'past the extent the tree names.'
                    % (row.label, figure_key, bound - 1, index))
        # The row moves and the window re-reads the one the row is posed
        # at, in the place the row is posed to move it: the other rows of
        # the band stay where they are, because the gesture is one row,
        # one index, and the window is the one the slider of the row is
        # the control of.
        row.setIndex(index)
        self._logFor(record.cases,
                     'set_slice_index: %s posed the row "%s" at index %d '
                     '(%s held, %d to %d).'
                     % (figure_key, row.label, index,
                        'the bound' if row.length is None
                        else 'held', 0, max(int(row.length or 1), 1) - 1))
        return {'window': figure_key,
                'axis': row.label,
                'index': int(row.index()),
                'length': (None if row.length is None else int(row.length)),
                'rows': {row2.label: int(row2.index()) for row2 in rows}}

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

    # -------------------------------------------------------------- events

    def _readSignalForEvents(self, uri, path, along, indices):
        """The two axes an event is read on: what get_signal answers for the
        leaf, one array at a time. A leaf the read answers as more than one
        array is refused by name, because one event kind is read on one axis
        -- the value a figure of the same leaf draws, so detection and the
        plot are the same read."""
        payload = self.get_signal(
            uri, path, along=along,
            indices=None if indices is None else indices)
        if not isinstance(payload, dict) or payload.get('kind') != 'curve':
            kind = payload.get('kind') if isinstance(payload, dict) \
                else type(payload).__name__
            raise ValueError(
                'The leaf "%s" answers %r: an event is read on the one '
                'axis the read gives (name it with `along` and `indices`), '
                'not on a multi-array answer.' % (path, kind))
        x = payload.get('x')
        y = payload.get('y')
        if x is None or y is None:
            raise ValueError(
                'The read of "%s" answered but has no x and y an event can '
                'be read off: name the axis it runs on, or the element it '
                'is fixed on.' % path)
        return x, y

    def _readCurveSignal(self, uri, path, along, indices):
        """The two axes the leaf answers as a curve, one array at a time.

        The generic read the event detection, the spectrum and the
        cross-correlation all run on -- the value a figure of the same leaf
        draws, so the analysis and the plot are one read. `_readSignalForEvents`
        is that same read, kept under the earlier name."""
        return self._readSignalForEvents(uri, path, along, indices)

    def _addEventMarkers(self, frame, figure_key, block):
        """The event marks on a curve figure: one vertical per event, capped.

        A mark is a pyqtgraph InfiniteLine on the abscissa the curve runs
        along; the frame holds the set so clear_event_marks takes them off.
        More than the cap is refused by name, because dozens of lines are a
        wall across the curve, and the report is the shape that many events
        want.
        """
        import pyqtgraph as pg

        events = block['events']
        if len(events) > EVENT_MARKER_CAP:
            raise ValueError(
                'The signal holds %d %s event(s): a figure carries at most '
                '%d marks, and past that the lines are a wall -- the report '
                'is the shape that many want.'
                % (len(events), block['kind'], EVENT_MARKER_CAP))
        plot = getattr(frame, 'pgPlotWidget', None)
        if plot is None or not hasattr(plot, 'addItem'):
            raise ValueError(
                'The window "%s" is not a curve figure: a mark sits on the '
                'axis a curve was drawn along, so name the figure a curve '
                'was drawn in.' % figure_key)
        pen = pg.mkPen((255, 122, 40), width=2)
        markers = []
        for event in events:
            line = pg.InfiniteLine(pos=float(event['t']), angle=90,
                                   pen=pen, movable=False)
            plot.addItem(line)
            markers.append(line)
        frame._eventMarkers = markers
        return len(markers)

    def detect_events(self, uri, path, kind, threshold=None,
                      prominence=None, min_distance=None, direction=None,
                      hysteresis=None, along=None, indices=None,
                      figure_key=None):
        """The events of one kind, read off the leaf's signal.

        `kind` `'elm'` (an excursion up), `'sawtooth'` (a crash down), or
        `'lh'` (a threshold crossing). The signal is the one `get_signal`
        answers for the leaf -- the value a figure of the same leaf draws --
        so what is detected and what is plotted are the same read. `threshold`
        / `prominence` / `min_distance` gate an ELM or a sawtooth;
        `threshold` / `direction` / `hysteresis` gate an L-H crossing, and a
        kind the caller did not pick refuses a parameter it does not take,
        by name. `along` and `indices` address the leaf the way `plot_one`
        and `get_signal` do, so the read is theirs.

        When `figure_key` names a curve figure, the events are marked on it
        (capped; clear_event_marks takes the marks off). A figure that is
        not a curve figure, or a leaf the read answers as more than one
        axis, is refused by name.
        """
        from imasviz.VizAnalysis.detect import detect

        x, y = self._readSignalForEvents(uri, path, along, indices)
        params = {}
        for pname, given in (('threshold', threshold),
                             ('prominence', prominence),
                             ('min_distance', min_distance),
                             ('direction', direction),
                             ('hysteresis', hysteresis)):
            if given is not None:
                params[pname] = given
        block = detect(kind, x, y, **params)
        self._logFor([uri],
                     'detect_events: %d %s event(s) read off %s (the mean '
                     'spacing is %s s).'
                     % (block['count'], block['kind'], path,
                        block['period']['period_mean']))
        answer = dict(block)
        if figure_key is not None:
            _record, frame = self._windowForKey(figure_key)
            answer['figure'] = figure_key
            answer['markers'] = self._addEventMarkers(frame, figure_key,
                                                       block)
        return answer

    def clear_event_marks(self, figure_key):
        """The event marks off a curve figure, one the detect_events put there.

        Safe to call when the figure holds no marks: it answers the number
        it took off, which is zero in that case. A figure that is not in the
        session is refused the way the rest of the window gestures refuse.
        """
        record, frame = self._windowForKey(figure_key)
        markers = list(getattr(frame, '_eventMarkers', None) or [])
        plot = getattr(frame, 'pgPlotWidget', None)
        if plot is not None:
            for line in markers:
                try:
                    plot.removeItem(line)
                except Exception:
                    pass
        frame._eventMarkers = []
        self._logFor(record.cases,
                     'clear_event_marks: %d mark(s) off %s.'
                     % (len(markers), figure_key))
        return {'figure': figure_key, 'cleared': len(markers)}

    def events_report(self, uri, path, kind, threshold=None,
                      prominence=None, min_distance=None, direction=None,
                      hysteresis=None, along=None, indices=None,
                      figure_key=None, name=None):
        """The events of one kind as a self-contained HTML report.

        The same read and the same detection detect_events uses -- nothing is
        detected from memory -- with the events in their own table, the
        period of their times, and the figure when one is named (the picture
        of it). The file lands under `~/.imasviz/reports` like the other
        reports, and a name that names a place, not a report, is refused by
        name.
        """
        from imasviz.VizAnalysis.detect import detect

        x, y = self._readSignalForEvents(uri, path, along, indices)
        params = {}
        for pname, given in (('threshold', threshold),
                             ('prominence', prominence),
                             ('min_distance', min_distance),
                             ('direction', direction),
                             ('hysteresis', hysteresis)):
            if given is not None:
                params[pname] = given
        block = detect(kind, x, y, **params)

        image = None
        if figure_key is not None:
            try:
                image = self.screenshot(figure_key)
            except ValueError:
                image = None

        out = self._namedReport(name, block['count'])
        self._writeEventReport(out, kind=kind, uri=uri, leaf=path,
                               block=block, image=image)
        cases = [uri] + ([figure_key] if figure_key is not None else [])
        self._logFor(cases,
                     'events_report wrote %s: %d %s event(s) read off %s.'
                     % (out, block['count'], block['kind'], path))
        return {'saved_to': out, 'count': block['count'],
                'kind': block['kind']}

    def _writeEventReport(self, path, kind, uri, leaf, block, image):
        """The event report's own page: the events in a table, the period of
        their times, the image when there is one, and nothing to fetch --
        the shape the other reports keep, in the same little style."""
        import base64
        import html

        period = block['period']

        if kind in ('lh', 'l_h', 'mode', 'transition'):
            header = ('<tr><th>#</th><th>time</th><th>value</th>'
                      '<th>direction</th></tr>')

            def row(i, event):
                return (
                    '<tr><td class="s">%d</td><td class="s">%s</td>'
                    '<td class="s">%s</td><td class="s">%s</td></tr>'
                    % (i, self._num(event['t']), self._num(event['value']),
                       html.escape(str(event.get('direction', '')))))
        else:
            header = ('<tr><th>#</th><th>time</th><th>value</th>'
                      '<th>prominence</th></tr>')

            def row(i, event):
                return (
                    '<tr><td class="s">%d</td><td class="s">%s</td>'
                    '<td class="s">%s</td><td class="s">%s</td></tr>'
                    % (i, self._num(event['t']), self._num(event['value']),
                       self._num(event.get('prominence'))))

        def show(value):
            if value is None:
                return '—'
            return ('%g' % float(value)) if isinstance(value, float) \
                else str(value)

        parts = [
            '<!doctype html>',
            '<html lang="en"><head><meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            '<title>%s</title><style>%s</style></head><body>' % (
                html.escape('%s events' % kind), _REPORT_CSS),
            '<h1>%s</h1>' % html.escape('%s events read off %s' % (kind, leaf)),
            '<p class="sub">%s — %d event(s) · mean spacing %s s</p>' % (
                html.escape(uri), block['count'],
                show(period['period_mean'])),
        ]
        if image:
            parts.append(
                '<img alt="%s events" src="data:image/png;base64,%s">' % (
                    html.escape(kind),
                    base64.b64encode(image).decode('ascii')))
        parts.append('<table>')
        parts.append(header)
        for i, event in enumerate(block['events']):
            parts.append(row(i, event))
        parts.append('</table>')
        parts.append(
            '<p class="sub">count %d · span %s · mean %s · min %s · '
            'max %s · rate %s Hz</p>'
            % (block['count'], show(period['span']),
               show(period['period_mean']), show(period['period_min']),
               show(period['period_max']), show(period['mean_rate_hz'])))
        parts.append('</body></html>')
        try:
            with open(path, 'w', encoding='utf-8') as file:
                file.write('\n'.join(parts))
        except OSError as error:
            raise ValueError('The report could not be written to %s: %s'
                             % (path, error))

    # ------------------------------------------------------------ the spectrum
    # The read the three spectral asks run on is the one a figure of the same
    # leaf draws, so a leaf that is not a time series along `along` is refused
    # the way the event read refuses a multi-array answer.

    def spectrum(self, uri, path, n_peaks=None, band_low=None, band_high=None,
                 along=None, indices=None):
        """What the leaf's time series oscillates at, and where its power is.

        The read is the one `spectrum` is drawn from -- `get_signal`, the value
        a figure of the same leaf shows -- so the frequency read is the one the
        curve is. `n_peaks` is how many leading peaks come back (five); a band
        is two bounds, `band_low` and `band_high`, and a band asked for only one
        of them is refused by name; the share of the power in it is `band`.
        `along` and `indices` address the leaf the way `plot_one` and
        `get_signal` do.

        A flat series, or one too short to spread its power over a frequency,
        is refused the way the analysis layer says it, never a plausible-looking
        number.
        """
        from imasviz.VizAnalysis.spectra import band_power
        from imasviz.VizAnalysis.spectra import spectrum as ask

        if (band_low is None) != (band_high is None):
            present, absent = (('band_high', 'band_low')
                               if band_low is None else ('band_low', 'band_high'))
            raise ValueError(
                '%s is named with %s absent: a band is its two bounds, so name '
                'both or neither.' % (present, absent))
        x, y = self._readCurveSignal(uri, path, along, indices)
        block = ask(x, y, n_peaks=5 if n_peaks is None else int(n_peaks))
        dominant = block['dominant']
        answer = dict(block)
        if band_low is not None and band_high is not None:
            answer['band'] = band_power(x, y, band_low, band_high)
        self._logFor([uri], 'spectrum: %s reads dominant %g Hz (period %g s), '
                     '%d peak(s) answered.'
                     % (path, dominant['frequency'],
                        dominant['period'] or -1.0, len(block['peaks'])))
        return answer

    def cross_correlation(self, uri, path, path_b, along=None, indices=None,
                          indices_b=None):
        """How far `path_b` lags or leads `path`, and at what the two ring.

        Both reads are the ones a figure draws (`get_signal`, the value the two
        curves carry), so a pair the case does not hold at one length, or on two
        clocks, is refused the way the analysis says it, not a lag that would
        not mean one. The lag is in samples and in the time those samples are on
        the shared clock; the correlation is that of the peak; the shared
        frequency is the one the two agree to oscillate at.
        """
        from imasviz.VizAnalysis.spectra import cross_correlation as ask

        x, y = self._readCurveSignal(uri, path, along, indices)
        xb, yb = self._readCurveSignal(uri, path_b, along, indices_b)
        answer = ask(x, y, xb, yb)
        self._logFor([uri], 'cross_correlation: %s lags %s by %d sample(s) '
                     '(%g s), correlation %g, ringing together at %g Hz.'
                     % (path_b, path, answer['lag_samples'],
                        answer['lag_time'], answer['correlation'],
                        answer['dominant_shared_frequency']))
        return answer

    def spectrum_report(self, uri, path, n_peaks=None, band_low=None,
                        band_high=None, along=None, indices=None, figure_key=None,
                        name=None):
        """The spectral facts of a leaf's series as a self-contained HTML page.

        The same read and the same `spectrum` the facts run on -- nothing is
        read from memory -- with the leading peaks in a table, the band when one
        is named, and the picture of the figure when a curve figure is named.
        The file lands under `~/.imasviz/reports` like the other reports.
        """
        from imasviz.VizAnalysis.spectra import band_power
        from imasviz.VizAnalysis.spectra import spectrum as ask

        if (band_low is None) != (band_high is None):
            raise ValueError('a band is its two bounds, so name both or neither')
        x, y = self._readCurveSignal(uri, path, along, indices)
        block = ask(x, y, n_peaks=5 if n_peaks is None else int(n_peaks))
        band = band_power(x, y, band_low, band_high) \
            if (band_low is not None and band_high is not None) else None
        image = None
        if figure_key is not None:
            try:
                image = self.screenshot(figure_key)
            except ValueError:
                image = None
        out = self._namedReport(name, len(block['peaks']))
        self._writeSpectrumReport(out, uri=uri, leaf=path, block=block,
                                  band=band, figure_key=figure_key,
                                  image=image)
        cases = [uri] + ([figure_key] if figure_key is not None else [])
        self._logFor(cases, 'spectrum_report wrote %s: %s dominant %g Hz.'
                     % (out, path, block['dominant']['frequency']))
        return {'saved_to': out,
                'dominant_frequency': block['dominant']['frequency'],
                'peaks': len(block['peaks'])}

    def _writeSpectrumReport(self, path, uri, leaf, block, band,
                             figure_key, image):
        """The spectrum page: the leading peaks in a table, the band when there
        is one, the figure's picture when it is named, nothing to fetch -- the
        shape the other reports keep, in the same little style."""
        import base64
        import html

        def show(value):
            if value is None:
                return '—'
            return ('%g' % float(value)) if isinstance(value, float) \
                else str(value)

        dominant = block['dominant']
        parts = [
            '<!doctype html>',
            '<html lang="en"><head><meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            '<title>%s</title><style>%s</style></head><body>' % (
                html.escape('spectrum of %s' % leaf), _REPORT_CSS),
            '<h1>%s</h1>' % html.escape('spectrum of %s' % leaf),
            '<p class="sub">%s — dominant %s Hz (period %s s) · '
            '%d sample(s)</p>'
            % (html.escape(uri), show(dominant['frequency']),
               show(dominant['period']), block['samples']),
        ]
        if image:
            parts.append(
                '<img alt="figure" src="data:image/png;base64,%s">' %
                base64.b64encode(image).decode('ascii'))
        parts.append('<table>')
        parts.append('<tr><th>#</th><th>frequency (Hz)</th><th>period (s)</th>'
                     '<th>power</th><th>share</th></tr>')
        for i, peak in enumerate(block['peaks']):
            parts.append(
                '<tr><td class="s">%d</td><td class="s">%s</td>'
                '<td class="s">%s</td><td class="s">%s</td>'
                '<td class="s">%s</td></tr>'
                % (i, self._num(peak['frequency']), self._num(peak['period']),
                   self._num(peak['power']),
                   ('%.3f' % peak['fraction']) if peak['fraction'] is not None
                   else '—'))
        parts.append('</table>')
        foot = 'total power %s' % show(block['total_power'])
        if band is not None:
            lo, hi = band['band']
            foot += (' · band %g—%g Hz holds %.1f%% of it'
                     % (lo, hi, 100.0 * band['fraction']))
        parts.append('<p class="sub">%s</p>' % foot)
        parts.append('</body></html>')
        try:
            with open(path, 'w', encoding='utf-8') as file:
                file.write('\n'.join(parts))
        except OSError as error:
            raise ValueError('The report could not be written to %s: %s'
                             % (path, error))

    def greenwald(self, uri, n_e_path, ip_path, area_path,
                  along=None, indices=None, indices_ip=None, indices_area=None):
        """The Greenwald fraction of a case, over the time the three read.

        `f_G` = `n_e / n_G`, with the Greenwald limit the standard gives,
        `n_G = (I_pl / A) x 1e20`, `I_pl` in mega-Ampere and `A` in square
        metre, so the ratio is metre-cubed. The three reads are the ones a
        figure draws -- `get_signal`, the value the three leaves show -- so a
        case that does not hold one, or holds the three at different lengths,
        is refused the way `cross_correlation` refuses a pair it cannot hold.
        The answer is the fraction, the limit, and the three leaves, so the
        numbers a physicist checks come from the case, not from this method.
        """
        from imasviz.VizAnalysis.spectra import greenwald_fraction as ask

        ne = self._readCurveSignal(uri, n_e_path, along, indices)
        ip = self._readCurveSignal(uri, ip_path, along, indices_ip)
        area = self._readCurveSignal(uri, area_path, along, indices_area)
        answer = ask(ne[1], ip[1], area[1])
        answer['n_e_path'] = n_e_path
        answer['ip_path'] = ip_path
        answer['area_path'] = area_path
        limit = answer['greenwald_limit']
        frac = answer['greenwald_fraction']
        self._logFor([uri], 'greenwald: f_G = %g at t=%g, '
                     'n_G = %g (n_e=%s / n_G=%s x 1e20), on %d point(s).'
                     % (frac[0] if frac else -1.0,
                        ne[0][0] if ne[0] is not None and ne[0] else -1.0,
                        limit[0] if limit else -1.0,
                        n_e_path, area_path, answer['points']))
        return answer

    # The two remaining feature-3 derived quantities. Neither fabricates a
    # number: the case keeps them, and these name the leaf that holds them, the
    # formula, and the values the case answers -- the same read a figure of the
    # same leaf would draw. A case that does not hold the leaf is refused by
    # name, never a plausible-looking value.

    def _scalarCurve(self, name, uri, path, x, y):
        """The values of a curve read, with the path that named them, the stats
        finite and None-where-empty, and one log line naming the numbers."""
        y = list(y)
        finite = [v for v in y if v == v]
        answer = {
            name: y,
            'path': path,
            'points': len(y),
            'mean': (sum(finite) / len(finite)) if finite else None,
            'max': max(finite) if finite else None,
            'min': min(finite) if finite else None,
        }
        self._logFor([uri], '%s: %d point(s) read off %s; mean %s, max %s, '
                     'min %s.' % (name, len(y), path,
                                 '%g' % answer['mean'] if finite else '-',
                                 '%g' % answer['max'] if finite else '-',
                                 '%g' % answer['min'] if finite else '-'))
        return answer

    def beta_normal(self, uri, path=None, along=None, indices=None):
        """The case's normalized beta, over the time it is held.

        `path` is the leaf to read; the default is the one the equilibrium case
        keeps for it (`global_quantities.beta_normal`), but any path the case
        holds as a curve answers the same. The answer is the case's own number,
        spelled under its name, with its mean, peak and floor -- not a beta
        this method did. A case that does not hold the path is refused by name.
        """
        path = path or 'equilibrium.time_slice[0].global_quantities.beta_normal'
        x, y = self._readCurveSignal(uri, path, along, indices)
        return self._scalarCurve('beta_normal', uri, path, x, y)

    def total_pressure(self, uri, path=None, along=None, indices=None):
        """The case's total pressure p = n_e k_B T_e + n_i k_B T_i.

        `path` is the leaf to read; the default is the total (the one the
        equilibrium case keeps, `profiles_1d.pressure`) -- the case is the one
        that summed electrons and ions, and these two lines document that sum
        rather than pretend to have done it. A case that does not hold the path
        is refused by name, never a plausible-looking profile.
        """
        path = path or 'equilibrium.time_slice[0].profiles_1d.pressure'
        x, y = self._readCurveSignal(uri, path, along, indices)
        return self._scalarCurve('pressure', uri, path, x, y)

    # Trend / campaign: read the same leaf from several shots and say whether
    # it is rising, falling, or flat. Neither the values nor the order come
    # from this method: the caller names the shots, in campaign order, and the
    # read is the same `get_signal` a figure of the same leaf would draw.
    # A shot the case does not hold the leaf in is refused by name; a
    # campaign of one, or of all-equal values, is refused too, because
    # neither says rising or falling.

    def _shotValue(self, uri, path, at, which, along, indices):
        """The one value per shot the trend is asked of.

        `at` is the 0-based index into the curve `get_signal` answers;
        `which` is `'mean'`, `'max'`, or `'min'` over that curve. Name one
        or the other, not both: the shot values the caller asked for and
        the shot values the case holds are two different things, and the
        trend must not mix them.
        """
        payload = self.get_signal(uri, path, along=along, indices=indices)
        if not isinstance(payload, dict) or payload.get('kind') != 'curve':
            kind = payload.get('kind') if isinstance(payload, dict) \
                else type(payload).__name__
            raise ValueError(
                'shot %s answers %r for %s: a per-shot value is read off a '
                'curve the case draws along one axis -- name it with `along` '
                'and `indices` -- not a multi-array answer.'
                % (uri, kind, path))
        y = list(payload.get('y') or [])
        if not y:
            raise ValueError(
                'shot %s answers no value for %s: name the axis or element '
                'the case holds the leaf on.' % (uri, path))
        if at is not None:
            if isinstance(at, bool):
                raise ValueError('`at` is a 0-based index into the curve '
                                 'the shot answers, not a true/false flag.')
            if isinstance(at, str) and at.strip().isdigit():
                at = int(at.strip())
            if not isinstance(at, int):
                raise ValueError('`at` is a 0-based index into the curve '
                                 'the shot answers, got %r.' % (at,))
            if not (0 <= at < len(y)):
                raise ValueError(
                    'shot %s holds %d values for %s and at=%d is out of '
                    'range (0 to %d).' % (uri, len(y), path, at, len(y) - 1))
            value = float(y[at])
        else:
            which = (which or 'mean').strip().lower()
            if which not in ('mean', 'max', 'min'):
                raise ValueError('`which` is "mean", "max" or "min", '
                                 'got %r.' % (which,))
            finite = [v for v in y
                      if v is not None and isinstance(v, (int, float))
                      and v == v and abs(v) != float('inf')]
            if not finite:
                raise ValueError(
                    'shot %s answers no finite value for %s: the case does '
                    'not hold the leaf there, so there is no number to '
                    'take the trend on.' % (uri, path))
            if which == 'mean':
                value = sum(finite) / len(finite)
            elif which == 'max':
                value = max(finite)
            else:
                value = min(finite)
        return value

    def campaign(self, cases, path, at=None, which='mean',
                 along=None, indices=None):
        """The trend of a leaf, across a series of shots, in campaign order.

        `cases` is the list of shot URIs, in the order the campaign runs;
        `path` the leaf to read from each shot; `at` the 0-based index into
        the curve the shot answers, or `which` ('mean', 'max', 'min') over
        that curve -- one of the two, not both. The answer carries the
        per-shot values, the least-squares slope over the shot index, first
        to last, min/max and the shots they came from, and a direction.
        `cases` of one, a shot the case does not hold the leaf in, or a
        campaign of all-equal values refuses by name -- each in the words
        that mean it.
        """
        if not isinstance(cases, (list, tuple)):
            raise ValueError('`cases` is the list of shot URIs, in campaign '
                             'order, and %r is not one.' % (cases,))
        if len(cases) < 2:
            raise ValueError('a trend is asked of at least two shots; the '
                             'campaign holds %d.' % len(cases))
        if at is not None and which is not None and \
                which != 'mean':
            raise ValueError('name one of `at` or `which`: the shot-value '
                             'the curve answers and the shot-value the '
                             'caller asked for are two reads, and the trend '
                             'runs on one of them, not a mix of the two.')
        rows = []
        for uri in cases:
            value = self._shotValue(uri, path, at, which, along, indices)
            rows.append({'uri': uri, 'value': value})
        from imasviz.VizAnalysis.trend import trend as ask
        trend = ask([r['value'] for r in rows],
                    labels=[r['uri'] for r in rows])
        self._logFor([r['uri'] for r in rows],
                     'campaign on %s: %d shot(s) -- %s, change %g, '
                     'slope %g per shot, min %g at shot %d, max %g at '
                     'shot %d.'
                     % (path, len(rows), trend['direction'],
                        trend['change'], trend['slope'],
                        trend['min'], trend['argmin'],
                        trend['max'], trend['argmax']))
        return {'path': path, 'rows': rows, 'trend': trend}

    def campaign_report(self, cases, path, at=None, which='mean',
                        along=None, indices=None, name=None):
        """The campaign answer, as a self-contained HTML page: the per-shot
        table, the trend, and the shape it makes across the shots. The file
        lands under `~/.imasviz/reports` like the other reports."""
        answer = self.campaign(cases, path, at=at, which=which,
                               along=along, indices=indices)
        out = self._namedReport(name, len(answer['rows']))
        self._writeCampaignReport(out, leaf=path, rows=answer['rows'],
                                   trend=answer['trend'])
        self._logFor([r['uri'] for r in answer['rows']],
                     'campaign_report wrote %s: %s, %s over %d shot(s).'
                     % (out, path, answer['trend']['direction'],
                        len(answer['rows'])))
        return {'saved_to': out, 'trend': answer['trend']}

    def _writeCampaignReport(self, path, leaf, rows, trend):
        """The campaign page: the per-shot table, the trend numbers, and the
        line the shot values make across the shots. Inline SVG, no fetch, the
        same little style the other reports wear."""
        import html

        def show(value):
            return ('%g' % float(value)) if isinstance(value, float) \
                else str(value)

        # one point per shot, across the width; values mapped to the height
        # on the campaign's own min/max so the line shows the shape, even
        # where the shots cluster
        vmin, vmax = float(trend['min']), float(trend['max'])
        span = (vmax - vmin) or 1.0
        width, height, pad = 340, 120, 16
        n = len(rows)
        step_x = (width - 2 * pad) / max(1, n - 1)
        step_y = (height - 2 * pad) / span
        points = []
        dots = []
        for i, r in enumerate(rows):
            x = pad + i * step_x
            y = pad + (vmax - float(r['value'])) * step_y
            points.append(('%g %g' % (x, y)))
            dots.append('<circle cx="%g" cy="%g" r="2.5"/>' % (x, y))
        parts = [
            '<!doctype html>',
            '<html lang="en"><head><meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, '
            'initial-scale=1">',
            '<title>%s</title><style>%s</style></head><body>' % (
                html.escape('campaign of %s' % leaf), _REPORT_CSS),
            '<h1>%s</h1>' % html.escape('campaign of %s' % leaf),
            '<p class="sub">%d shot(s) · %s · change %s · slope %s/shot · '
            'min %s (shot %d) · max %s (shot %d)</p>'
            % (len(rows), trend['direction'], show(trend['change']),
               show(trend['slope']), show(trend['min']), trend['argmin'],
               show(trend['max']), trend['argmax']),
            '<svg width="%d" height="%d" role="img" '
            'aria-label="the trend of %s across the campaign">'
            % (width, height, html.escape(leaf)),
            '<line x1="%g" y1="%g" x2="%g" y2="%g" '
            'stroke="#dde3e7" stroke-width="1"/>'
            % (pad, height - pad, width - pad, height - pad),
            '<polyline fill="none" stroke="#3a707a" stroke-width="1.5" '
            'points="%s"/>' % ' '.join(points),
            ' '.join(dots),
            '</svg>',
            '<table>',
            '<tr><th>shot</th><th>value</th><th>uri</th></tr>',
        ]
        for i, r in enumerate(rows):
            parts.append('<tr><td class="s">%d</td><td class="s">%s</td>'
                         '<td class="q">%s</td></tr>'
                         % (i, show(r['value']), html.escape(r['uri'])))
        parts.append('</table>')
        parts.append('</body></html>')
        try:
            with open(path, 'w', encoding='utf-8') as file:
                file.write('\n'.join(parts))
        except OSError as error:
            raise ValueError('the report could not be written to %s: %s'
                             % (path, error))

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

    # ------------------------------------------------------- focus, shown

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
            'roots: list_plugins names what a branch earns, and the log of the '
            'case names the plugins it cannot offer at all.'
            % (uri, plugin, len(view.IDSRoots)))

    def _refuseUnknownEntry(self, uri, plugin, entry, offered):
        """Refuse an entry number the plugin does not carry, naming the ones it does."""
        byRoot = {}
        for root, one in offered:
            byRoot.setdefault(root, []).append(one)
        raise ValueError(
            'The case %s does not offer entry %s of plugin "%s": that plugin is '
            'offered on %s, whose entries are %s. list_plugins names the label of '
            'each.'
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
                    '%s branch: list_plugins names what it does.'
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
                'The case %s holds no data at all (list_case_idss answers '
                'the same): there is nothing to report.' % uri)

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

    # ---------------------------------------------------------------- journals

    def _noteEmbedder(self):
        """The ``text -> vector`` the journal index answers, or ``None``.

        The one the preferences name (``AgentEmbedEndpoint`` /
        ``AgentEmbedModel``), the ``EmbeddingClient`` the run built for it;
        left unnamed, the index is served on the keyword alone (its text
        is still kept in step, and a ``reindex_journals`` under a named
        endpoint is the one that vectors it). A client the caller cannot
        build is the ``None`` the search answers alone on the keyword —
        the read is never one the endpoint is absent from."""
        from imasviz.VizUtils import QVizPreferences
        endpoint = (QVizPreferences.AgentEmbedEndpoint or '').strip()
        if not endpoint:
            return None
        from imasviz.VizAgent.llm_client import EmbeddingClient
        return EmbeddingClient()

    def _syncJournalWrite(self, scope, answer, kind='add'):
        """Keep the journal's index in step with a write the run answered.

        ``answer`` is the one ``add_note`` / ``edit_note`` holds (a dict
        the ``journals`` store handed back, the keys the note's fields),
        and this upserts it under the journal's store (the text
        ``journals_index.noteText`` composes: the title, the filters, the
        body), re-embedding when the body moved and keeping it otherwise
        (the ``rag_store.upsert`` incremental rule). The write the run is
        answering is never one the index cost a refusal: a store the run
        cannot open (the shared folder not named) or an embedder that
        refuses are logged, and the note stands on the disk the writers
        hold — the read falls to the keyword the journal ranks while the
        index is not in step, and a ``reindex_journals`` is the one that
        sets the two in step.
        """
        import logging
        try:
            from imasviz.VizAgent import journals_index
            journals_index.upsertNote(
                scope, answer, embedder=self._noteEmbedder())
        except Exception as e:
            logging.getLogger('logPanel').info(
                'the %s %s of note %s did not keep its index in step: %s '
                '(the note itself stands on the disk the writers hold)'
                % (scope, kind, answer.get('id', '?'), e))

    def search_journals(self, scope=None, query=None, limit=20,
                        machine=None, campaign=None, shot=None,
                        date_from=None, date_to=None, author=None):
        """The RAG of the two journals.

        Two steps, in that order:
        0. the eager index — the one ``add_note`` / ``edit_note`` /
           ``delete_note`` keep in step and ``reindex_journals`` builds
           (one SQLite per journal under ``~/.imasviz`` and the shared
           folder) — is asked of first when it holds rows: the BM25 over
           the notes' text fused with the cosine of the query against
           the same (the ``rag_store``'s RRF). It answers
           ``method: 'hybrid'`` / ``'embeddings'`` / ``'keyword'``, and
           a store written under an embedder the run is not under
           answers ``guarded`` with the ``guard_reason`` (vectors
           ignored, keyword alone) — the one ``reindex_journals`` sets
           right;
        1. the structured filter (``machine``/``campaign``/``shot``/
           ``date_from``/``date_to``/``author``) narrows to the notes
           that name each of the fields the caller asked of;
        2. the ranking of what is left — by the lazy cache when the
           ``AgentEmbedEndpoint`` preference is named and the endpoint
           answers (the cosine between the query's vector and each
           note's, through the local cache under the journal's folder),
           and by keyword (a light BM25, no dependency) when it is not
           or when the endpoint does not answer — the one the run holds
           while a journal has not been indexed yet, the answer the
           reader gets until a ``reindex_journals`` fills the store.

        An empty filter answer (a note the filters narrowed out) is the
        ``total: 0`` the answer holds, and a fallback from embeddings
        to keyword — the endpoint named but not answering, or answering
        a shape ``rankByVector`` does not read — is named in the answer
        as ``method: 'keyword'`` and ``fallback_reason``: the run that
        read it does not present it as an embeddings answer.
        """
        from imasviz.VizAgent import journals
        notes = journals.JournalStore.list_notes(
            scope=scope, machine=machine, campaign=campaign, shot=shot,
            date_from=date_from, date_to=date_to, author=author)
        total = len(notes)
        try:
            limit = max(1, int(limit))
        except (TypeError, ValueError):
            limit = 20
        if not query or not str(query).strip():
            return {
                'scope': scope or 'both', 'query': None, 'total': total,
                'returned': min(total, limit), 'method': 'list',
                'notes': [note.asSearchResult() for note in notes[:limit]],
            }
        query = str(query).strip()
        # The eager index — the one ``add_note`` / ``edit_note`` /
        # ``delete_note`` keep in step and ``reindex_journals`` builds — is
        # the ranking asked of first: the BM25 over the notes' text fused
        # with the cosine of the query against the same, the one
        # ``rag_store`` answers. A journal the run has not indexed is empty
        # and the read falls to the keyword the ``journals`` store ranks
        # (the lazy path below), the note the index did not reach being
        # still the one the disk holds: the read does not pretend the index
        # answered when it did not.
        from imasviz.VizAgent import journals_index
        include_ids = set(note.id for note in notes)
        embedder = self._noteEmbedder()
        indexed = journals_index.search(
            scope=scope, include_ids=include_ids, query=query,
            embedder=embedder, limit=limit)
        if indexed.get('note_ids'):
            by_id = {note.id: note for note in notes}
            answer = {
                'scope': scope or 'both', 'query': query, 'total': total,
                'returned': min(total, len(indexed['note_ids'])),
                'method': indexed['method'],
                'indexed': True,
                'notes': [by_id[rid].asSearchResult()
                          for rid in indexed['note_ids'] if rid in by_id],
            }
            if indexed.get('guard_reason'):
                answer['guarded'] = True
                answer['guard_reason'] = indexed['guard_reason']
            return answer
        from imasviz.VizUtils import QVizPreferences
        endpoint = (QVizPreferences.AgentEmbedEndpoint or '').strip()
        if endpoint:
            from imasviz.VizAgent.llm_client import EmbeddingClient
            cacheFolders = {}
            if scope in (None, 'personal'):
                try:
                    cacheFolders['personal'] = \
                        journals.JournalStore.personalDirectory()
                except ValueError:
                    pass
            if scope in (None, 'shared'):
                try:
                    cacheFolders['shared'] = \
                        journals.JournalStore.sharedDirectory()
                except ValueError:
                    pass
            try:
                embedder = EmbeddingClient()
                # A query the embedder refuses is a refusal the ranking
                # does not hide: the keyword answers the same question
                # the embeddings could not, and the answer says it fell
                # back and why (the same rule the ``rankByVector``'s
                # own `ValueError` is, one the caller reads).
                try:
                    ranked = journals.rankByVector(
                        notes, query, embedder, cacheFolders=cacheFolders,
                        limit=limit)
                except ValueError as e:
                    # A query the endpoint does not vectorise is not an
                    # error: it is the keyword, with the reason named.
                    # A note the endpoint could not vectorise is not
                    # one the ranked list holds, and the search does
                    # not say it does not exist either.
                    ranked = journals.rankByKeyword(notes, query, limit=limit)
                    return {
                        'scope': scope or 'both', 'query': str(query).strip(),
                        'total': total, 'returned': len(ranked),
                        'method': 'keyword',
                        'fallback_from': 'embeddings',
                        'fallback_reason': str(e),
                        'notes': [n.asSearchResult() for n in ranked],
                    }
                answered = bool(ranked)
                # The query that answered nothing through the embeddings
                # is one the keyword answers in its own name: the
                # ranked list is empty, but the note the keyword would
                # rank is not a note that is not there — it is one
                # the embeddings did not reach. The answer says which
                # method the run used, and the caller names the note
                # it could not rank.
                if not answered:
                    keyword = journals.rankByKeyword(notes, query,
                                                     limit=limit)
                    return {
                        'scope': scope or 'both', 'query': str(query).strip(),
                        'total': total, 'returned': len(keyword),
                        'method': 'keyword (no embeddings ranked this)',
                        'notes': [n.asSearchResult() for n in keyword],
                    }
                return {
                    'scope': scope or 'both', 'query': str(query).strip(),
                    'total': total, 'returned': len(ranked),
                    'method': 'embeddings',
                    'notes': [note.asSearchResult() for note in ranked],
                }
            except (ConnectionError, RuntimeError) as e:
                # An endpoint that does not answer is the keyword, with
                # the reason named: the keyword reads the same notes
                # and ranks them by what they hold, not nothing.
                ranked = journals.rankByKeyword(notes, query, limit=limit)
                return {
                    'scope': scope or 'both', 'query': str(query).strip(),
                    'total': total, 'returned': len(ranked),
                    'method': 'keyword',
                    'fallback_from': 'embeddings',
                    'fallback_reason': str(e),
                    'notes': [n.asSearchResult() for n in ranked],
                }
        ranked = journals.rankByKeyword(notes, query, limit=limit)
        return {
            'scope': scope or 'both', 'query': str(query).strip(),
            'total': total, 'returned': len(ranked),
            'method': 'keyword',
            'notes': [note.asSearchResult() for note in ranked],
        }

    def read_note(self, scope, note_id):
        """The full body of one note of one journal, by its id (the
        file name without ``.md``). Not in the journal is a refusal by
        name, naming the ids it does hold; a note whose file is there
        but does not parse as one (no ``author``) is the same refusal,
        the shape ``journal`` does not answer is one the read does
        not hide."""
        from imasviz.VizAgent import journals
        return journals.JournalStore.read_note(scope, note_id)

    def list_notes(self, scope=None, machine=None, campaign=None, shot=None,
                   date_from=None, date_to=None, author=None):
        """The notes the two journals hold, filtered (the author is
        the one required on every note, the others optional), newest
        first. ``date_from`` and ``date_to`` bound the shot date the
        note carries (``YYYY-MM-DD``); a note that names no date is
        excluded only when the caller names a window. An empty list is
        the answer the caller reads as an answer, not a refusal: the
        folder holds no note of the shape the filters ask of, and that
        is what the answer says."""
        from imasviz.VizAgent import journals
        notes = journals.JournalStore.list_notes(
            scope=scope, machine=machine, campaign=campaign, shot=shot,
            date_from=date_from, date_to=date_to, author=author)
        return {'scope': scope or 'both',
                'count': len(notes),
                'notes': [note.asSearchResult() for note in notes]}

    def journal_stats(self):
        """The state of the two journals, their embeddings, and their
        indexes: the folder the personal and the shared are each under
        (a ``refusal`` when no folder is named / not a directory), the
        count of notes each holds, the state of the embeddings (is the
        endpoint named in the preferences, and if so, what model it
        names), and the one each journal's index holds — its file, its
        rows and vectors, its ``embed_sig`` and ``dim``, and its
        ``built_at`` (a ``refusal`` the same way when the shared folder
        is not named). The caller reads those to decide the method a
        run will rank with (index then keyword, embeddings then
        keyword), and one ``reindex_journals`` sets the two in step."""
        from imasviz.VizAgent import journals
        from imasviz.VizAgent import journals_index
        stats = journals.JournalStore.stats()
        try:
            stats['indexes'] = journals_index.stats()
        except Exception:
            stats['indexes'] = {}
        return stats

    def reindex_journals(self, scope=None):
        """The two (or the one) journals, in step with their indexes.

        The eager rebuild the read asks of when an index is empty, stale
        or guarded: it walks the notes the ``journals`` store holds,
        upserts each into the journal's store (re-embedding only what
        moved, under the endpoint the preferences name), and purges the
        rows the store holds that the journal no longer keeps. The answer
        is one line per journal it held (``upserted``/``kept``/``purged``/
        ``total``), a ``refusal`` the one it could not open (the shared
        folder not named), and the ``embedder_named`` flag — whether the
        run vectorized this pass or kept the text alone for the keyword
        (the embed the later run under a named endpoint will pay). A
        journal the writer emptied on one side is not purged by it (an
        empty source is not an ask to take the other writer's rows away);
        that one answers ``skipped_empty``.
        """
        from imasviz.VizAgent import journals_index
        embedder = self._noteEmbedder()
        out = journals_index.reindex(scope=scope, embedder=embedder)
        return {'scopes': out, 'embedder_named': embedder is not None}

    # ---------------------------------------------------------------- documents

    def _docsEmbedder(self):
        """The ``text -> vector`` the documents corpus answers, or
        ``None`` (the corpus served on the keyword alone). The one the
        preferences name (``AgentEmbedEndpoint`` / ``AgentEmbedModel``);
        left unnamed, the corpus is served on the keyword (a document's
        text is still kept in step with the store, and the one a later
        ``reindex_documents`` under a named endpoint pays to vector)."""
        from imasviz.VizAgent import rag_docs
        return rag_docs.docsEmbedder()

    def list_documents(self):
        """The documents the corpus reads: every ``.md``/``.txt``/``.pdf``
        the folder ``AgentDocsDir`` names holds (its name, its size, its
        date, and the ``rel`` the search answers by). A corpus run cannot
        read (no folder named, the folder not a directory) is a refusal by
        name, naming the one it could not read — the same shape the shared
        journal answers for its folder."""
        from imasviz.VizAgent import rag_docs
        return {'documents': rag_docs.listDocuments()}

    def read_document(self, rel):
        """The full text of one document of the corpus, by its ``rel`` (the
        one a search hits back by). Not in the corpus is a refusal by name,
        naming the ones it does read; a document it does not read is the
        same — the corpus does not cost a crash to a read it cannot answer."""
        from imasviz.VizAgent import rag_docs
        return {'rel': rel, 'text': rag_docs.readDocument(rel)}

    def reindex_documents(self):
        """The whole corpus, in step with the store: the one the user runs
        on adding a document to the corpus folder, or changing the endpoint
        (the two are then not the same space, and this sets them in step).
        It walks the documents the corpus reads, upserts each (re-embedding
        only what moved, under the endpoint the preferences name), and
        purges the rows the store holds that the corpus no longer holds (a
        document that left the folder). A corpus the run cannot read is a
        refusal by name (``refusal`` in the answer); a corpus that holds no
        document is kept as it was (``skipped_empty``, not emptied).
        The ``embedder_named`` flag says whether the run vectorized this
        pass or kept the text alone for the keyword."""
        from imasviz.VizAgent import rag_docs
        embedder = self._docsEmbedder()
        out = rag_docs.reindex(embedder=embedder)
        out['embedder_named'] = embedder is not None
        return out

    def search_documents(self, query, limit=8):
        """The corpus's rank: the one a ``search_documents`` asks of. The
        BM25 over the documents' chunks fused with the cosine of the query
        against the same (the ``rag_store``'s RRF), one hit per chunk (the
        document's ``rel``, the chunk's index, a snippet of its text). A
        corpus the run cannot read is a refusal by name; a search that
        hits no chunk is an ``empty`` the answer holds (not a crash, not a
        guess). The answer holds the ``method`` (``hybrid`` /
        ``embeddings`` / ``keyword`` / ``empty``) and, when a store's
        ``embed_sig`` is not the one the run is under, the ``guarded``
        flag with the ``guard_reason`` (vectors ignored, the keyword
        stands, and the reason names the embedder so a
        ``reindex_documents`` sets the two in step).
        """
        from imasviz.VizAgent import rag_docs
        embedder = self._docsEmbedder()
        return rag_docs.search(query, embedder=embedder, limit=limit)

    def documents_stats(self):
        """The state of the corpus: how many documents and chunks it
        holds, its ``embed_sig`` and ``dim``, and its ``built_at``. A
        corpus the run cannot read (no folder) answers a ``refusal`` the
        caller reads as the one the index could not open, not a zero it
        would read as empty. The caller reads those to decide the method a
        run will rank with (index then keyword, embeddings then keyword),
        and one ``reindex_documents`` sets the two in step."""
        from imasviz.VizAgent import rag_docs
        return rag_docs.stats()

    def add_note(self, scope, text, author=None, machine=None,
                 campaign=None, shot=None, date=None, title=None):
        """One new note in one journal.

        The author is required on every write: ``author`` named by the
        caller, or ``$USER`` when the caller left it out — a run with
        no ``$USER`` and no ``author`` is a named refusal, because a
        writer it cannot attribute to is one the journal does not hold.
        A note with no body is the same refusal, and the file is not
        written: the shape the journal does not hold is not one the
        write will cost.
        """
        from imasviz.VizAgent import journals
        answer = journals.JournalStore.add_note(
            scope, text, author=author, machine=machine, campaign=campaign,
            shot=shot, date=date, title=title)
        # The eager index on the write: the note is in the journal's store
        # the same turn it is on the disk, so the next search of it ranks
        # the body the writer just wrote (the ``add_note`` of the run is
        # the one the index answers, not one it recomputes on the read).
        # A store the run cannot keep in step (the shared folder not
        # named, the embedder refused) is logged and the write stands:
        # the note is on the disk the writers hold, and the read falls to
        # the keyword the journal ranks while the index is not in step.
        self._syncJournalWrite(scope, answer, kind='add')
        return answer

    def edit_note(self, scope, note_id, text=None, author=None, machine=None,
                  campaign=None, shot=None, date=None, title=None):
        """One note of one journal, changed in place: the note keeps the
        id the other writers read it under, and the fields the caller
        names take the place of the ones it held (a field left out
        keeps the one it held, an empty one clears it — except the
        author and the body, the two a note does not go without:
        an edit that empties either is the named refusal the add does
        not take, and the note on disk is not touched)."""
        from imasviz.VizAgent import journals
        answer = journals.JournalStore.edit_note(
            scope, note_id, text=text, author=author, machine=machine,
            campaign=campaign, shot=shot, date=date, title=title)
        # The eager index on the edit: the row keeps the id the edit kept,
        # and its text is the one the edit wrote (re-embedded when the body
        # moved, kept when it did not — the ``rag_store.upsert`` rule).
        self._syncJournalWrite(scope, answer, kind='edit')
        return answer

    def delete_note(self, scope, note_id):
        """One note of one journal, gone: the file and the cache entry
        the run holds for it. Not in the journal is a named refusal,
        naming the ids it does hold, and the cache is invalidated by
        the same rule the write is: a note the run deleted is one the
        next search does not rank, because its file is not there."""
        from imasviz.VizAgent import journals
        answer = journals.JournalStore.delete_note(scope, note_id)
        # The eager index on the delete: the row leaves the journal's store
        # the same turn the note's file does, so the next search does not
        # rank the line the writer took out (the note the run deleted is
        # one the index dropped, not one it recomputes).
        note_id = answer.get('id', note_id)
        try:
            from imasviz.VizAgent import journals_index
            journals_index.removeNote(scope, note_id)
        except Exception as e:
            import logging
            logging.getLogger('logPanel').info(
                'the %s journal could not drop its index row for %s: %s '
                '(the note itself is gone from the disk the writers hold)'
                % (scope, note_id, e))
        return answer

    # ------------------------------------------------- the prompt catalogue

    def _promptContext(self):
        """What this session already knows, under the names a prompt's
        holes may carry: ``case``, ``uri``, ``shot``, ``run``,
        ``database``, ``figure``.

        This is what makes re-running a prompt cost no typing: the shot
        the user is looking at is the shot the prompt means, and it is
        read off the case the session has open —
        ``QVizIMASDataSource._readCaseFromUri`` is the one place a URI
        spells a case, so the number comes from the case, not from what a
        model recalls of the session. ``figure`` is the key of the one
        figure window the session holds, the same key the *Windows* menu
        and the other gestures take.

        Nothing is guessed: with two cases open, ``case``/``uri``/``shot``
        /``run``/``database`` are left unanswered — which one the prompt
        means is not said, so the user is asked for the value instead of
        getting the first view the walk reached. The reason is in
        ``note``, and the fill shows it.
        """
        out = {}
        note = []
        views = []
        try:
            views = list(self.api.DTVlist)
        except AttributeError:
            views = []
        if len(views) == 1:
            uri = views[0].dataSource.uri
            from imasviz.VizDataSource.QVizIMASDataSource import (
                _readCaseFromUri, caseLabel)
            database, shot, run = _readCaseFromUri(uri)
            out['uri'] = uri
            out['case'] = caseLabel(uri)
            for name, value in (('database', database), ('shot', shot),
                                ('run', run)):
                if value is not None:
                    out[name] = str(value)
        elif len(views) > 1:
            note.append('%d cases are open, so the prompt cannot be told '
                        'which one it means: name %s yourself.'
                        % (len(views), ', '.join(
                            '{%s}' % name for name in
                            ('case', 'uri', 'shot', 'run', 'database'))))
        else:
            note.append('no case is open, so the session answers no case '
                        'value: name the one the prompt means.')
        try:
            keys = [one['key'] for one in self.list_windows()
                    if one['kind'] != 'Agent']
        except Exception:
            keys = []
        if len(keys) == 1:
            out['figure'] = keys[0]
        elif keys:
            note.append('%d windows are open (%s), so the figure the '
                        'prompt means is not said: name {figure} yourself.'
                        % (len(keys), ', '.join(keys[:8])))
        else:
            note.append('no window is open, so the session answers no '
                        '{figure}.')
        if note:
            out['note'] = ' '.join(note)
        return out

    def list_prompts(self, scope=None, category=None, query=None,
                     limit=100):
        """The catalogue: the prompts the user can ask again, and what
        each one is.

        One entry per prompt — its id (what a gesture takes), its display
        name, its category, its one-line description, its holes and their
        defaults — category first then name, so the list reads as the
        catalogue the user wrote. ``category`` and ``query`` narrow it;
        ``query`` is read against the name, the description, the category
        and the id, because a reader remembers a word of the description,
        not the id. ``categories`` answers how many prompts each category
        holds — the filter the page and the panel build their chips from.
        ``context`` says what this session would answer for free.

        ``scope`` is the personal catalogue, the shared one
        (``SharedPromptsDir``), or both — the default. A shared catalogue
        with no folder named is not a refusal of the list: the personal
        prompts still answer, and the reason the shared half is missing is
        in ``catalogues_unavailable``, not left out.
        """
        from imasviz.VizAgent import prompts
        entries = prompts.PromptStore.list_prompts(scope=scope,
                                                   category=category,
                                                   query=query)
        out = {
            'prompts': [one.asLine() for one in entries[:int(limit)]],
            'total': len(entries),
            'categories': prompts.PromptStore.categories(scope=scope),
            'context': self._promptContext(),
        }
        unavailable = prompts.PromptStore.unavailable(scope)
        if unavailable:
            out['catalogues_unavailable'] = unavailable
        if len(entries) > int(limit):
            out['truncated'] = (
                '%d of %d prompts are answered: raise `limit` or narrow '
                'the ask.' % (int(limit), len(entries)))
        return out

    def prompt_detail(self, name, scope=None):
        """One prompt of the catalogue, whole: its body, its holes, and
        where each value would come from if it were asked right now.

        ``name`` is the id or the display name — a catalogue is read out
        loud ("relance Profils du plat-top"), and the answer names both.
        A name two prompts carry is refused naming their ids, never
        answered with the first one the walk reached.

        The ``values`` preview is not a guess and not a fill: it answers,
        per hole, the value the four sources would give (what the user
        named last time, what this session knows, what the file declares)
        and ``null`` for the holes that still need typing. Nothing is
        remembered by this call — asking what a prompt would answer is not
        typing an answer in.
        """
        from imasviz.VizAgent import prompts
        entry = prompts.PromptStore.find(name, scope=scope)
        context = self._promptContext()
        answer = entry.asDict()
        answer['values'] = prompts.resolveValues(entry, context=context,
                                                 remember=False)
        answer['context'] = context
        return answer

    def fill_prompt(self, name, values=None, scope=None):
        """The prompt as it will be asked, its holes filled — and nothing
        run.

        This is what a catalogue click costs: the page puts the text in
        its box or sends it as a turn, the panel puts it in its box, the
        client runs it. Filling is the gesture because running from here
        would stand inside the agent's own loop and ask it a second turn,
        which is not what a button asks.

        A hole is filled from the first source that answers it — what this
        call names, what was typed last time for that prompt, what this
        session knows, what the file declares — and the answer says which
        one it was, because a value the user did not type is a value they
        are entitled to see. A hole none of them answers is a refusal
        naming the holes that are still empty: a prompt is not sent with
        ``{shot}`` in it, and not sent with a guess in its place. The
        values this call names are kept for the next one (locally, never
        in the shared catalogue).
        """
        from imasviz.VizAgent import prompts
        entry = prompts.PromptStore.find(name, scope=scope)
        answers = prompts.resolveValues(entry, given=values,
                                        context=self._promptContext())
        filled = dict((name, one['value']) for name, one in answers.items()
                      if one['value'] is not None)
        text = prompts.fillTemplate(entry.body, filled)
        return {
            'id': entry.id, 'name': entry.name, 'scope': entry.scope,
            'category': entry.category, 'text': text, 'values': answers,
        }

    def save_prompt(self, name, text, category=None, description=None,
                    variables=None, scope='personal', prompt_id=None):
        """One prompt into the catalogue, under a name and a description.

        The prompt a turn just ran is the one worth filing: the user asks
        for it once, the wording works, and the next run should not have
        to type it again — which is what ``save_prompt`` is asked of on an
        explicit ask, never on a turn that merely drew something (the rule
        the shared journal's write answers by, for the same reason: it is
        a line other people read).

        ``variables`` left out is read off the text: every ``{hole}`` it
        opens, with no default. The hole is then asked for on every run,
        which is the safe reading of a prompt the user filed in a hurry.
        A hole declared and never opened in the text is refused by name.
        The shared catalogue is written to only when ``scope='shared'``
        and ``SharedPromptsDir`` names a folder — a write silently filed
        in the personal folder is a prompt its author believes shared.
        """
        from imasviz.VizAgent import prompts
        entry = prompts.PromptStore.add_prompt(
            text, name=name, category=category, description=description,
            variables=variables, scope=scope, prompt_id=prompt_id)
        return entry.asDict()

    def edit_prompt(self, name, text=None, category=None, description=None,
                    variables=None, scope=None):
        """One prompt of the catalogue, changed in place: it keeps the id
        the pages, the sessions and the remembered values read it under.

        A field left out keeps the one the prompt held; a field named
        takes the place of the one it held; an empty one clears it. The
        body is the one field an edit cannot empty, and the id is not a
        field an edit moves — a new prompt is ``save_prompt``.
        """
        from imasviz.VizAgent import prompts
        entry = prompts.PromptStore.find(name, scope=scope)
        changed = prompts.PromptStore.edit_prompt(
            entry.scope, entry.id, body=text, category=category,
            description=description, variables=variables)
        return changed.asDict()

    def delete_prompt(self, name, scope=None):
        """One prompt out of the catalogue, and the values remembered for
        it. Not there is a refusal naming the ids the catalogue holds."""
        from imasviz.VizAgent import prompts
        entry = prompts.PromptStore.find(name, scope=scope)
        return prompts.PromptStore.delete_prompt(entry.scope, entry.id)

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
        name as read from its node. An index may be spelled as a string of
        digits -- the schema says a 0-based index, and a model that sends it
        as `"2"` means the third curve, not a name that holds the digit: it
        takes the integer path and its range refusal. Refused by name: a
        window that holds no curve, a curve index past the last it holds, a
        curve name it does not hold, a curve selector that is not one of the
        three. For a curve figure the `source` is the figure itself; for a
        window of panels, one panel per curve. `record` is the window record
        the refusal or log names, so the log line and the error both say
        which window it was.
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
        if isinstance(curve, str) and curve.strip().isdigit():
            # The 0-based index the schema names, spelled as a string: it
            # takes the integer path, so a name that holds the digit is
            # not what a bare digit reaches -- a quantity named "psi=20"
            # is still addressed by "psi=20", never by "2".
            curve = int(curve.strip())
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

    def _viewBoxesOf(self, frame, figure_key=None):
        """One axis set per drawn picture: the one of a curve figure, or the
        one of each picture of a picture window, in screen order.

        A picture window answers the span with **one** number pair and wears
        it on all of its pictures: the window is one scale and one span, so
        a time zoom of a strip whose abscissa is its time is the `x` range
        in the seconds the time axis holds. A curve figure answers with its
        single `pgPlotWidget.getViewBox()`. A table and a stacked view keep
        one axis set per panel, and a picture window that has drawn nothing
        has no axis set at all -- each refusal names the window and the
        shape it holds, and the caller learns what to ask next.
        """
        pictures = getattr(frame, 'plotItems', None)
        if callable(pictures):
            items = list(pictures())
            if items:
                boxes = []
                for item in items:
                    view = getattr(item, 'getViewBox', None)
                    if view is None:
                        raise ValueError(
                            'The window "%s" holds pictures with no axis set '
                            'a span can be set on, so a range cannot be '
                            'pinned on them.' % (figure_key or 'this window'))
                    boxes.append(view())
                if boxes:
                    return boxes
            raise ValueError(
                'The window "%s" is a picture window that drew no picture, '
                'and a range needs the drawn picture to sit on: draw the '
                'quantity first, and the span is the one set_axis_range '
                'pins.' % (figure_key or 'this window'))
        pgPlot = getattr(frame, 'pgPlotWidget', None)
        if pgPlot is None or not hasattr(pgPlot, 'getViewBox'):
            raise ValueError(
                'The window "%s" is not a single figure whose span this '
                'gesture pins: a figure of curves holds one axis set, and '
                'a picture window takes the span of its pictures -- this '
                'one is neither, its panels each keeping their own answer '
                'on their own. Name the figure a curve was drawn in, or '
                'the one the pictures of one quantity are drawn in.'
                % (figure_key or 'this window'))
        return [pgPlot.getViewBox()]

    def _viewBoxOf(self, frame, figure_key=None):
        """The single axis set of a curve figure: `pgPlotWidget`'s ViewBox.

        The log and inversion gestures address curve figures: a table and a
        stacked window have one panel per picture and keep their own, the
        flux-surface figure draws inside a graphics layout, and a picture
        window is the span of its own pictures -- the one `set_axis_range`
        answers. Each refusal names the window the caller tried, and the
        gesture that answers it, so the refusal the caller reads says what
        to do next instead of repeating the call.
        """
        if callable(getattr(frame, 'plotItems', None)):
            raise ValueError(
                'The window "%s" is a picture window: the log and inversion '
                'gestures address the figure a single curve was drawn in, '
                'and this one holds pictures, whose span is the one '
                'set_axis_range pins. Name the figure the curve was drawn '
                'in.' % (figure_key or 'this window'))
        pgPlot = getattr(frame, 'pgPlotWidget', None)
        if pgPlot is None or not hasattr(pgPlot, 'getViewBox'):
            raise ValueError(
                'The window "%s" draws no single figure whose axes a log '
                'scale or an inversion can be set on: a curve figure '
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
        """The widget holding a named window: the app, a figure, a case URI.

        The one reading `screenshot` and `focus_window` share: "app" is the
        session's main window, a figure is the frame registered under its key
        -- or under the key the user names it by, "plot3" for `Plot3`, the
        newest for "la dernière figure" -- and a URI is that case's shot
        view. A name none of the three holds is refused from `list_windows`
        itself, the one the *Windows* menu draws. The refusal names what IS
        open, so the model can see the right key without inventing another
        guess. The figure reference resolves against what is held, the same
        `resolveFigureKey` the capture of a turn gives the PNG, so a show and
        the picture it asks for answer the same figure.
        """
        if window == 'app':
            if self.main_window is None:
                raise ValueError(
                    'No application window to capture: this session was '
                    'built without one -- name a figure key or a case URI.')
            return self.main_window
        if window in self.api.figureframes:
            return self.api.figureframes[window]
        # A loose reference to a held figure ("plot3", "3", "la dernière")
        # stands for the key it names, and is settled here rather than left
        # to the caller to spell exactly right. A name it does not settle --
        # and a case URI, which is not a figure -- falls through to the read
        # below, whose refusal names what IS open.
        if not (window or '').startswith('imas:') and '/' not in (window or ''):
            try:
                key = resolveFigureKey(window, self.api.figureframes,
                                       order=list(self.api.figureframes))
            except ValueError:
                key = None
            if key is not None:
                return self.api.figureframes[key]
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
