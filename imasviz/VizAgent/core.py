# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The shared layer of the agent's gestures: the addressing, the reports, the helpers.

The gestures themselves live in the mixin modules beside this one —
`core_cases`, `core_plots`, `core_curves`, `core_analysis`, `core_windows`,
`core_journals_prompts` and `core_export`. `McpGuiCore` assembles them, and
keeps the small set of private helpers the clusters share. The module-level
helpers (`axesAddressing`, `resolveFigureKey`, the report style, the clock
constants) stay here: every cluster imports what it needs from this module.

Every method of the core runs **where a click would have run**: it builds the
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
                'manage_selection(action="select") then '
                'plot(mode="selection") for a selection).'
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

from imasviz.VizAgent.core_cases import CaseOps
from imasviz.VizAgent.core_plots import PlotOps
from imasviz.VizAgent.core_curves import CurveOps
from imasviz.VizAgent.core_analysis import AnalysisOps
from imasviz.VizAgent.core_windows import WindowOps
from imasviz.VizAgent.core_journals_prompts import JournalOps
from imasviz.VizAgent.core_export import ExportOps


class McpGuiCore(CaseOps, PlotOps, CurveOps, AnalysisOps, WindowOps, JournalOps, ExportOps):
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
            '"%s" is not a leaf of the case %s -- inspect_tree('
            'action="search") names what this tree can give, in every '
            'spelling it holds.'
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

    def _windowForKey(self, key):
        for record in self.api.openWindows():
            if record.figureKey == key:
                frame = record.frame()
                if frame is not None:
                    return record, frame
        raise ValueError(
            'No window holds the key "%s" any more -- list_windows names '
            'what is open.' % key)

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

    @staticmethod
    def _num(value):
        if value is None:
            return '—'
        return ('%g' % float(value)) if isinstance(value, float) else str(value)

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

    def _viewForUri(self, uri):
        for view in self.api.DTVlist:
            if view.dataSource.uri == uri:
                return view
        openUris = [getattr(view.dataSource, 'uri', None)
                    for view in self.api.DTVlist]
        raise ValueError(
            'The case %r is not open in this session (it holds: %s). '
            'Open it with manage_case(action="open") first.'
            % (uri, ', '.join('"%s"' % u for u in openUris) or 'nothing'))
