# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The tool declarations of one IMASViz session, on the official MCP SDK.

Each tool is a thin name over the core: the agent's words map one-to-one
onto a method of `McpGuiCore`, and the value that comes back is the value
the core answered -- a named `ValueError` included, which FastMCP hands
back as the error content of the call, so the refusal reads the same in
the transcript as it does in the log panel.

`dispatcher` is what runs the method on the GUI thread: the SDK answers
tool calls on its worker threads, and those may compute but must not
touch the widgets -- the rule the dispatcher exists for.
"""

import base64
from functools import partial
from typing import Literal, Optional, Union

from mcp.server.fastmcp import FastMCP
from mcp import types as mcp_types

# The tool vocabulary is one table, not two: the group name, the action
# inside it and the parameters that action takes are read from the same
# declaration the in-app agent is offered, so a merged group cannot end up
# spelled one way on the page and another on this endpoint.
from imasviz.VizAgent.tools import (
    argumentsForMember,
    gestureOf,
    missingParameterRefusal,
    missingParameters,
    unknownParameterRefusal,
    unknownParameters,
)

INSTRUCTIONS = """IMASViz, the ITER/CEA visualization front-end for IMAS plasma-fusion
cases, driven by name and answered by name.

How to work with it:
1. open_case(uri) -- the data dictionary is asked of the case when you do
   not name one;
2. list_idss(uri) tells which IDSs the case holds and which occurrences;
3. load_ids(uri, ids_name, occurrence) builds the tree branch;
4. search_nodes(uri, query) names the leaves in every spelling the tree
   holds -- the paths select_signals, plot and get_signal take are
   any of those spellings;
5. plot draws, and its `mode` says which drawing: 'single' one quantity
   into the figure its axes call for, 'slice' one value at an instant,
   'selection' what the case holds selected, 'table' one panel per
   quantity, 'stacked' the stacked view. get_screenshot answers a PNG of
   the window; the equilibrium has its
   own entry asked with an action -- equilibrium(action='surfaces') puts
   the flux surfaces of the instants you name side by side, and
   equilibrium(action='at_time') puts one instant's surface with its
   radial profiles in one window, the global quantities of the slice
   coming back in the answer;
6. state is read with list_selection (what the case holds selected),
   describe_node (what one node holds: documentation, units, size, the
   finite minimum and maximum, the nan and inf counts, a bounded
   preview), describe_ids (what the data dictionary says about an IDS:
   comment, homogeneous_time, units, time units, data dictionary
   version), and list_quantities (the filled tensors of one occurrence,
   grouped by array of structures) -- answers, not guesses, and empty is
   an answer too;
7. a report is self-contained HTML on disk, and it is one entry asked with
   `scope`: generate_report(scope='plot') names one window of curves (its
   image, one row per curve it drew, with the statistics of each),
   generate_report(scope='case_loaded') names the whole loaded tree of a
   case (one row per curve it holds, in tree order), and
   generate_report(scope='case_ids') names the case itself -- every IDS
   the case holds and the occurrences each
   holds, the ones the user loaded, a header of the `ids_properties`
   values per loaded occurrence, and the signals the tree holds for each
   (the ones it carries as available, a 0-D scalar held by the dynamic
   array among them).
8. manipulating a figure is work on what it holds, by name of the figure
   and of the curve: transform_curve does one thing to a drawn curve, and
   its `operation` says which -- 'scale' multiplies its value by a
   constant, 'shift' adds one, 'normalize' divides by its own peak/first/
   mean; read_figure reads the numbers as they stand -- action='stats' for
   the answer, action='export' for those same values in a file -- so a
   transform a hand put on is the value it returns, and operation='reset'
   takes that transform off, operation='remove' takes the curve off. The
   axes are moved by one tool of their own, configure_axes, whose
   `operation` says what moves: 'range' pins the window (xmin/xmax,
   ymin/ymax, or auto=True to re-fit), 'image_window' moves (start) or
   resizes (count) the window of a picture window, 'slice_index' poses a
   row of a slider band at an index, 'log' makes an axis log (True) or
   linear (False), 'invert' flips one. A curve is selected by a
   substring of its name, a 0-based index, or left out for every one; a
   log on values that cross zero is refused by name, and a figure that is
   not a single one (a table, or the flux-surface figure) is refused the
   same way -- name the figure the single curve was drawn in.

The state of a figure is what the calls of this session made, and a read
this session answered -- not what was said of it. A curve you say was
added, a transform you say was applied, an axis you say moved: each of
those stands only if the call that did it succeeded naming that figure,
or a read_figure of it answered that state. A refused call changed
nothing: it added no curve, applied no transform and moved no axis, so
the answer is the refusal it named, with the reason it gave -- not the
state it would have left. A call that did not run, or that had not
returned when you answered, is not a success: read the figure with
read_figure(action="stats") before saying what it holds, or say it
stands as you found it.

A refused gesture is not a failure of the server: it is an answer, with
the reason the application names it. get_logs(uri) holds those reasons
as the user reads them in the log panel."""


def buildServer(core, dispatcher, name='imasviz'):
    """The FastMCP server of one session: the tools, their names, their words.

    FastMCP reads each tool's description off its docstring, so the
    docstrings say what the agent needs to know, in the order the words
    are asked.
    """
    server = FastMCP(name, instructions=INSTRUCTIONS)

    def _run(function):
        """Ask the GUI thread, and hand back what it answers -- value or
        named exception alike."""
        return dispatcher.call(function)

    # ------------------------------------------------------------------ cases

    @server.tool(name='open_case')
    def open_case(uri: str, dd_version: Optional[str] = None):
        """Open one IMAS case by URI (imas:hdf5?path=..., or an UDA URI).

        `dd_version` pins the data dictionary the case is read at; left
        out, the case is asked which one its own IDSs were written with,
        because a case stored under another major version is refused at
        every read otherwise.
        """
        return _run(partial(core.open_case, uri, dd_version=dd_version))

    @server.tool(name='list_cases')
    def list_cases():
        """The cases open in this session, with their loaded occurrences."""
        # The SDK answers a top-level list as one content block per
        # element; the list is a value under a name, not the answer.
        return {'cases': _run(core.list_cases)}

    @server.tool(name='close_case')
    def close_case(uri: str):
        """Close one open case: its view, its windows, its bookkeeping."""
        return _run(partial(core.close_case, uri))

    # -------------------------------------------------------------------- ids

    @server.tool(name='list_idss')
    def list_idss(uri: str):
        """Every IDS the case's data dictionary declares, and the occurrences
        each one holds -- including the roots that hold no data (an empty
        occurrence list). Asked of the case itself, never listed from a file.

        For the short list of the IDS the case actually holds, use
        list_case_idss instead: its names can be trusted as the case's own,
        because they are read from the case through
        DBEntry.list_all_occurrences, not recalled.
        """
        return {'idss': _run(partial(core.list_idss, uri))}

    @server.tool(name='list_case_idss')
    def list_case_idss(uri: str):
        """Only the IDS the case actually holds, and the occurrences each one
        names -- the roots the dictionary declares but the case does not fill
        are left out.

        The source of truth for "what is in this case". Do not present an IDS
        list you did not read from this call.
        """
        return {'idss': _run(partial(core.list_case_idss, uri))}

    @server.tool(name='load_ids')
    def load_ids(uri: str, ids_name: str, occurrence: int = 0,
                 slices: str = 'first'):
        """Load one occurrence of one IDS into the tree, synchronously.

        `slices` is "first" for the slice a plain load keeps, "all" for
        the whole dynamic array -- and an occurrence the case does not
        hold is refused by the load with its reason.
        """
        return _run(partial(core.load_ids, uri, ids_name, occurrence,
                            slices=slices))

    # ------------------------------------------------------- the tree itself

    # One name for the four ways the tree answers a question about itself,
    # the same offer the agent's loop makes (see `FAMILIES`, "the tree").
    # The checks are the loop's, in the loop's order, so a caller over this
    # socket and a caller in the panel hear the same words about the same
    # mistake.
    @server.tool(name='inspect_tree')
    def inspect_tree(
            action: Literal['search', 'node', 'ids', 'quantities'],
            uri: str,
            query: Optional[str] = None,
            ids_name: Optional[str] = None,
            occurrence: Optional[int] = None,
            limit: Optional[int] = None,
            path: Optional[str] = None):
        """What the tree of a case says about itself, and `action` picks.

        "search" matches the leaves whose spelling carries `query`
        (case-insensitive: the display path, the data name, the parametrized
        path), `ids_name` narrowing to one IDS and `limit` bounding the
        answer. The matches come back under `matches`, each with its three
        spellings -- any is what `select_signals`, `plot` and `get_signal`
        take -- and the `kind` a plot would make of it.

        "node" answers what one `path` holds, as the application's own
        documentation says it: units, size, shape, the finite minimum and
        maximum, the zero/nan/inf counts, a bounded preview. A leaf the tree
        does not hold is refused by name.

        "ids" answers what the data dictionary says of an `ids_name`: its
        comment, homogeneous_time, units, time units, and the version the
        case was written at. A property the case leaves empty is absent, not
        invented; an IDS the case does not declare is refused by name.

        "quantities" answers the filled tensors of one `occurrence`, grouped
        by the array of structures that drives them: path, data name,
        parametrized path, units, data type, how many elements the case
        holds. A scalar (0D) leaf is not a tensor and is not listed; an
        occurrence whose tree was never built is refused -- load it with
        load_ids first.
        """
        gesture = gestureOf('inspect_tree', {'action': action})
        args = {field: value for field, value in (
            ('uri', uri), ('query', query), ('ids_name', ids_name),
            ('occurrence', occurrence), ('limit', limit), ('path', path))
            if value is not None}
        unknown = unknownParameters(gesture, args)
        if unknown:
            raise ValueError(unknownParameterRefusal(gesture, unknown))
        missing = missingParameters(gesture, args)
        if missing:
            raise ValueError(missingParameterRefusal(gesture, missing))
        spelled = argumentsForMember(gesture, args)
        answer = _run(partial(getattr(core, gesture), **spelled))
        if gesture == 'search_nodes':
            # The search answer is a bare list of matches; the socket hands
            # it under a key, as this entry always did.
            return {'matches': answer}
        return answer

    @server.tool(name='select_signals')
    def select_signals(uri: str, paths: list, additive: bool = True):
        """Put the named paths into the case selection, as clicks would.

        A path the tree does not hold is refused by name, and the
        selection is left as it was; `additive=False` clears it first.
        """
        return _run(partial(core.select_signals, uri, paths,
                            additive=additive))

    @server.tool(name='unselect_all')
    def unselect_all(uri: str):
        """Empty the case selection; the answer says how many were dropped."""
        return _run(partial(core.unselect_all, uri))

    @server.tool(name='list_selection')
    def list_selection(uri: str):
        """The case's current selection, in the order it was put in.

        The path, the data name, the IDS and the occurrence of each;
        empty is an answer, count 0 -- not a refusal.
        """
        return _run(partial(core.list_selection, uri))

    # -------------------------------------------------------------- plotting

    # One name for the five ways a quantity is drawn, the same offer the
    # agent's loop makes (see `FAMILIES`, "the drawing"). The checks are the
    # loop's, in the loop's order -- the action's unknown parameters, then
    # its missing ones -- because a caller over this socket and a caller in
    # the panel must hear the same words about the same mistake, and the
    # parameters are checked in the spelling the caller typed (`path`, not
    # the `leaf` the slice gesture has always taken in Python).
    @server.tool(name='plot')
    def plot(mode: Literal['single', 'slice', 'selection', 'table',
                           'stacked'],
             uri: str, path: Optional[str] = None,
             paths: Optional[list] = None,
             along: Optional[str] = None,
             indices: Optional[dict] = None,
             along_time: Optional[bool] = None,
             into_figure_key: Optional[str] = None,
             time: Optional[float] = None,
             time_interp: Optional[bool] = None,
             occurrence: Optional[int] = None,
             interpolation: Optional[str] = None,
             columns: Optional[int] = None,
             plot_axis: Optional[str] = None):
        """Draw, in the shape the ask calls for: `mode` picks it.

        "single" draws one `path` into the figure its own axes call for -- a
        curve figure for one axis to draw, a picture window for two. The
        address is the one `get_signal` takes, so the figure a reader sees
        and the numbers a read reports are the same element of the same
        array: `along` names the axis the quantity runs along (the clock, or
        one of its own axes, e.g. `psi`), and `indices` pins each OTHER axis
        at its 0-based index, one entry per nested array of structures
        (`time_slice`, `profiles_1d`, `ion`, ...) or the leaf's own
        coordinate. `equilibrium.time_slice[0].profiles_1d.pressure` is a
        profile held by the dynamic array, so "le long du temps, un index
        `psi` de 50" is `along` left out (the clock) and `indices={"psi":
        50}`. `time` pins a profile to one slice of its dynamic time array
        (by default the nearest; `time_interp=true` the value between the
        two that bracket it) and is refused together with `along`/`indices`,
        as the opposite readings they are. `into_figure_key` adds it to an
        open curve figure (a superposition) instead of opening one.

        "slice" draws one `path` at one `time` through the Access Layer's
        own `DBEntry.get_slice` -- the value it answers at that instant, not
        a GUI-side lerp -- with `interpolation` `linear` (default),
        `closest` or `previous`; the coordinate is the leaf's own, a time
        outside the case's range answers the nearest slice it holds and says
        so, and it is not a 2D-pictorial leaf nor a 0D scalar.

        "selection" draws what `select_signals` selected for that case: one
        curve figure, one window per picture. "table" lays one panel per
        `paths` in a Table Plot View, `columns` wide, every quantity read
        along `plot_axis`. "stacked" stacks `paths`, one panel per quantity,
        in one window against the abscissa `plot_axis` names (the clock by
        default).

        A mode asked without a parameter it needs, or with one that belongs
        to another mode, is refused by naming the missing or stray name and
        the call that takes it. The answer carries the figure key and
        `curves`, the exact list of the curves the figure holds after the
        call.
        """
        gesture = gestureOf('plot', {'mode': mode})
        args = {name: value for name, value in (
            ('uri', uri), ('path', path), ('paths', paths),
            ('along', along), ('indices', indices),
            ('along_time', along_time),
            ('into_figure_key', into_figure_key), ('time', time),
            ('time_interp', time_interp), ('occurrence', occurrence),
            ('interpolation', interpolation), ('columns', columns),
            ('plot_axis', plot_axis)) if value is not None}
        unknown = unknownParameters(gesture, args)
        if unknown:
            raise ValueError(unknownParameterRefusal(gesture, unknown))
        missing = missingParameters(gesture, args)
        if missing:
            raise ValueError(missingParameterRefusal(gesture, missing))
        spelled = argumentsForMember(gesture, args)

        def draw():
            return getattr(core, gesture)(**spelled)

        return _run(draw)

    # The two reads of the equilibrium the plugin offers, under one name:
    # `action` says whether the caller wants the surfaces of several instants
    # side by side or one instant with its profiles under it.
    @server.tool(name='equilibrium')
    def equilibrium(action: Literal['surfaces', 'at_time'], uri: str,
                    times: Optional[list] = None,
                    time: Optional[float] = None,
                    occurrence: Optional[int] = None):
        """The equilibrium as the plugin reads it, and `action` picks.

        "surfaces": one frame per named instant, side by side in one window
        (an `EquiSurfaces:` key; get_screenshot answers its PNG). `times` in
        seconds -- a single number is read as a list of one. Each instant
        answers the case's nearest slice and says which: `time_requested`
        vs `time_slice_time` and the slice index, per frame. Every frame
        shares its levels, bounds and marks (plasma boundary, magnetic
        axis, O-point, limiter), so the instants compare at equal measure.

        "at_time": one instant's flux surface with the radial profiles under
        it (q, elongation, triangularities, j_tor in MA/m^2, pressure in
        kPa, f_df_dpsi, dpressure_dpsi -- the plugin's quantities and its
        unit conversions, on rho_tor_norm) and the slice's global
        quantities in the answer (Ip in kA, q95, q_axis, li_3, W_mhd in kJ,
        axis position). `time` in seconds answers the nearest slice the
        case holds, named back as `time_slice_time`; a time outside the
        case's range says it was clamped.

        Neither read is a leaf of the tree: it is the read the plugin does
        on the IDS object, the GGD branch the tree does not hold.
        """
        gesture = gestureOf('equilibrium', {'action': action})
        args = {field: value for field, value in (
            ('uri', uri), ('times', times), ('time', time),
            ('occurrence', occurrence)) if value is not None}
        unknown = unknownParameters(gesture, args)
        if unknown:
            raise ValueError(unknownParameterRefusal(gesture, unknown))
        missing = missingParameters(gesture, args)
        if missing:
            raise ValueError(missingParameterRefusal(gesture, missing))
        spelled = argumentsForMember(gesture, args)
        return _run(partial(getattr(core, gesture), **spelled))

    @server.tool(name='get_signal')
    def get_signal(uri: str, path: str,
                   as_function_of_time: Optional[bool] = None,
                   coordinate_index: int = 0,
                   time_index: Optional[int] = None,
                   along: Optional[str] = None,
                   indices: Optional[dict] = None):
        """The values the tree read gives for one leaf, as JSON.

        The same read the plots use, so what a figure of it draws and
        what this reports are the same element of the same array: `along`
        names the axis the quantity runs along (the clock by default, or
        one of its own axes, e.g. `psi`), and `indices` pins each other
        axis at its 0-based index (the shared schema of
        `plot(mode='single')`).
        `as_function_of_time`, `coordinate_index` and `time_index` are
        the legacy spellings of the same address. A word no axis answers,
        or an index past the extent the tree names, is refused with the
        reason the application names, not a silent 0.
        """
        return _run(partial(core.get_signal, uri, path,
                            as_function_of_time=as_function_of_time,
                            coordinate_index=coordinate_index,
                            time_index=time_index,
                            along=along, indices=indices))

    # ------------------------------------ the figures: the data and the axes

    @server.tool(name='transform_curve')
    def transform_curve(
            operation: Literal['scale', 'shift', 'normalize', 'reset',
                               'remove'],
            figure_key: str, factor: Optional[float] = None,
            offset: Optional[float] = None,
            reference: Optional[str] = None,
            curve: Optional[Union[str, int]] = None):
        """Do one thing to the curve(s) a figure already holds: `operation` picks it.

        "scale" multiplies their values by `factor`, "shift" adds `offset`
        to them, "normalize" divides them by a reference of their own --
        `reference` being `max` (the largest sample, the default), `first`
        (the sample at index 0) or `mean`; "reset" puts them back to the
        data they were drawn with, and "remove" takes the curve off the
        figure. Scale, shift and normalize are in place and reversible
        through "reset"; a reference that is zero or not a number is
        refused, as the division would then read as a picture full of
        no-signal. `read_figure` answers the transformed value afterwards;
        the quantity in the tree is unchanged.

        `curve` is a name substring, a 0-based index, or left out for every
        curve the figure holds. The figure is the one a single curve was
        drawn in -- a table or the flux-surface figure are refused by name.
        An operation asked without the number it needs, or with one that
        belongs to another, is refused by naming the parameter and the
        operation that takes it.
        """
        gesture = gestureOf('transform_curve', {'operation': operation})
        args = {name: value for name, value in (
            ('figure_key', figure_key), ('factor', factor),
            ('offset', offset), ('reference', reference),
            ('curve', curve)) if value is not None}
        unknown = unknownParameters(gesture, args)
        if unknown:
            raise ValueError(unknownParameterRefusal(gesture, unknown))
        missing = missingParameters(gesture, args)
        if missing:
            raise ValueError(missingParameterRefusal(gesture, missing))
        spelled = argumentsForMember(gesture, args)

        def change():
            return getattr(core, gesture)(**spelled)

        return _run(change)

    @server.tool(name='configure_axes')
    def configure_axes(
            operation: Literal['range', 'image_window', 'slice_index',
                               'log', 'invert'],
            figure_key: str, xmin: Optional[float] = None,
            xmax: Optional[float] = None,
            ymin: Optional[float] = None,
            ymax: Optional[float] = None,
            auto: Optional[bool] = None,
            start: Optional[int] = None,
            count: Optional[int] = None,
            axis: Optional[str] = None,
            index: Optional[int] = None,
            x: Optional[bool] = None,
            y: Optional[bool] = None):
        """Move one thing a window draws to: `operation` picks it.

        "range" pins the span of its axes -- `xmin`/`xmax` together (the
        abscissa) and/or `ymin`/`ymax` together (the ordinate); a partial
        ask (one bound of a pair) is refused because a range is two, and
        `auto=True` clears the pins and re-fits. A curve figure takes one
        axis set; a picture window takes the same span on each of its
        pictures, so the time zoom of a strip whose abscissa is its time
        is the `x` range, in the seconds its time axis holds.

        "image_window" moves (`start`: where it sits on the axis the
        pictures are read across) or resizes (`count`: how many pictures
        it holds) the window of a picture window. The pictures are re-read
        in place and the colour scale a hand settled stays put. The answer
        carries the axis, its start and count, the extent it holds, and the
        label of each picture shown -- the value the axis carries there
        when the axis is the time.

        "slice_index" poses one row of a slider band at `index`: `axis` is
        the row in the words the band spells it (an array of structures by
        its name -- `time_slice`, `profiles_2d` -- or the coordinate it
        holds) and `index` a 0-based whole number within the extent that
        row holds. The other rows of the band stay where they are.

        "log" makes an axis log (`x`/`y` `True`) or linear (`False`); a log
        where the values cross zero or below is refused, because the
        picture hides them -- `transform_curve(operation="shift")` to clear
        the negatives is the answer. "invert" turns one around (`False`
        puts it back); inversion and range are independent.

        A parameter of another operation is refused by naming the operation
        that takes it, and a table or a stacked window -- one axis set per
        panel -- is refused by name.
        """
        gesture = gestureOf('configure_axes', {'operation': operation})
        args = {name: value for name, value in (
            ('figure_key', figure_key), ('xmin', xmin), ('xmax', xmax),
            ('ymin', ymin), ('ymax', ymax), ('auto', auto),
            ('start', start), ('count', count), ('axis', axis),
            ('index', index), ('x', x), ('y', y)) if value is not None}
        unknown = unknownParameters(gesture, args)
        if unknown:
            raise ValueError(unknownParameterRefusal(gesture, unknown))
        missing = missingParameters(gesture, args)
        if missing:
            raise ValueError(missingParameterRefusal(gesture, missing))
        spelled = argumentsForMember(gesture, args)

        def move():
            return getattr(core, gesture)(**spelled)

        return _run(move)

    # The two reads of the curves a figure holds answer under one name, and
    # `action` says which: the numbers on the way back, or those same
    # numbers in a file. The checks are the loop's, in the loop's order.
    @server.tool(name='read_figure')
    def read_figure(
            action: Literal['stats', 'export'], figure_key: str,
            curve: Optional[Union[str, int]] = None,
            format: Optional[str] = None, name: Optional[str] = None):
        """What the curve(s) a figure holds answer, and `action` picks.

        "stats": the sample count, the finite min/max/mean/std of the
        values, the nan/inf counts, the peak with its abscissa -- the read
        of a figure's curves where the reader can act on it, before or
        after a scale/shift/normalize. "export": those same values, as they
        stand, written to `~/.imasviz/exports` under the guard of the
        configurations -- `format` `csv` (default) or `json`, a `name` that
        names a place being refused by name.

        `curve` is a name substring, a 0-based index, or left out for every
        curve the figure holds. The figure is a single curve figure -- a
        table or the flux-surface figure are refused by name.
        """
        gesture = gestureOf('read_figure', {'action': action})
        args = {field: value for field, value in (
            ('figure_key', figure_key), ('curve', curve),
            ('format', format), ('name', name)) if value is not None}
        unknown = unknownParameters(gesture, args)
        if unknown:
            raise ValueError(unknownParameterRefusal(gesture, unknown))
        missing = missingParameters(gesture, args)
        if missing:
            raise ValueError(missingParameterRefusal(gesture, missing))
        spelled = argumentsForMember(gesture, args)
        return _run(partial(getattr(core, gesture), **spelled))

    # ------------------------------------------------- physics of a signal

    @server.tool(name='analyze_signal')
    def analyze_signal(
            action: Literal['events', 'clear_events', 'events_report',
                            'spectrum', 'correlate', 'spectrum_report'],
            uri: Optional[str] = None,
            path: Optional[str] = None,
            path_b: Optional[str] = None,
            kind: Optional[str] = None,
            threshold: Optional[float] = None,
            prominence: Optional[float] = None,
            min_distance: Optional[int] = None,
            direction: Optional[str] = None,
            hysteresis: Optional[float] = None,
            n_peaks: Optional[int] = None,
            band_low: Optional[float] = None,
            band_high: Optional[float] = None,
            along: Optional[str] = None,
            indices: Optional[dict] = None,
            indices_b: Optional[dict] = None,
            figure_key: Optional[str] = None,
            name: Optional[str] = None,
    ):
        """What one leaf's signal does, and what to do with what it says:
        `action` picks the ask.

        "events": the events of one `kind` read off the leaf -- `elm` (an
        excursion up), `sawtooth` (a crash down), `lh` (a threshold
        crossing). The signal is the one get_signal answers, so what is
        detected and what a figure of the same leaf draws are the same read.
        `threshold` / `prominence` / `min_distance` gate an ELM or a
        sawtooth, `threshold` / `direction` / `hysteresis` an L-H crossing,
        and a kind refuses a parameter it does not take, by name. `figure_key`
        marks the events on that curve figure (capped, and refused when it
        would be a wall).

        "clear_events": those marks off a curve figure, safe when it holds
        none -- it answers the number it took off.

        "events_report": the same read and detection as a self-contained HTML
        page -- the events in a table, the period of their times, and the
        figure when one is named. Lands in `~/.imasviz/reports` like the
        other reports, and a `name` that names a place is refused by name.

        "spectrum": what the time series oscillates at -- the dominant
        frequency and its period, the leading `n_peaks` (most power first),
        and the band's share between `band_low` and `band_high` when a band
        is named. A band named with only one bound, or a flat or too-short
        series, is refused by name.

        "correlate": how far `path` lags or leads `path_b`, and at what the
        two oscillate together. Both reads are the ones a figure draws, so a
        pair the case does not hold on one clock, or at one length, is
        refused by name.

        "spectrum_report": the same spectral facts as a self-contained HTML
        page -- the peaks in a table, the band when named, and the figure
        when one is named.

        `uri` and `path` are the case and the leaf for the five reads;
        "clear_events" works on a figure, not on a case. `along` and
        `indices` pick one element out of a family, the way get_signal does.
        """
        gesture = gestureOf('analyze_signal', {'action': action})
        args = {name_: value for name_, value in (
            ('uri', uri), ('path', path), ('path_b', path_b),
            ('kind', kind), ('threshold', threshold),
            ('prominence', prominence), ('min_distance', min_distance),
            ('direction', direction), ('hysteresis', hysteresis),
            ('n_peaks', n_peaks), ('band_low', band_low),
            ('band_high', band_high), ('along', along),
            ('indices', indices), ('indices_b', indices_b),
            ('figure_key', figure_key), ('name', name))
            if value is not None}
        unknown = unknownParameters(gesture, args)
        if unknown:
            raise ValueError(unknownParameterRefusal(gesture, unknown))
        missing = missingParameters(gesture, args)
        if missing:
            raise ValueError(missingParameterRefusal(gesture, missing))
        spelled = argumentsForMember(gesture, args)
        return _run(partial(getattr(core, gesture), **spelled))

    # -------------------------------------------------- what a case says

    @server.tool(name='derived_quantity')
    def derived_quantity(
            quantity: Literal['greenwald', 'beta_normal', 'total_pressure'],
            uri: str,
            n_e_path: Optional[str] = None,
            ip_path: Optional[str] = None,
            area_path: Optional[str] = None,
            path: Optional[str] = None,
            along: Optional[str] = None,
            indices: Optional[dict] = None,
            indices_ip: Optional[dict] = None,
            indices_area: Optional[dict] = None):
        """A number a case is judged on, and `quantity` picks which one.

        "greenwald" divides the case's own density by the Greenwald limit,
        f_G = n_e / n_G with n_G = (I_pl/A) x 1e20 (I_pl in A, A in m^2). It
        manufactures nothing: the three leaves are named by the caller, and a
        case that does not hold one is refused by name.

        "beta_normal" and "total_pressure" are the case's own numbers, read
        off the leaf it keeps them in -- `global_quantities.beta_normal` and
        `profiles_1d.pressure` unless `path` names another -- never computed
        here. The answer carries the path that read it, the values, the
        points and the mean, max and min; a case that does not hold the leaf
        is refused by name.
        """
        gesture = gestureOf('derived_quantity', {'quantity': quantity})
        args = {field: value for field, value in (
            ('uri', uri), ('n_e_path', n_e_path), ('ip_path', ip_path),
            ('area_path', area_path), ('path', path), ('along', along),
            ('indices', indices), ('indices_ip', indices_ip),
            ('indices_area', indices_area))
            if value is not None}
        unknown = unknownParameters(gesture, args)
        if unknown:
            raise ValueError(unknownParameterRefusal(gesture, unknown))
        missing = missingParameters(gesture, args)
        if missing:
            raise ValueError(missingParameterRefusal(gesture, missing))
        spelled = argumentsForMember(gesture, args)
        return _run(partial(getattr(core, gesture), **spelled))

    # The trend of one leaf over a series of shots, and that same answer as
    # a page. The page runs the trend and dresses its answer, so the two
    # asks are one read and one word apart.
    @server.tool(name='trend_campaign')
    def trend_campaign(
            action: Literal['values', 'report'], cases: list, path: str,
            at: Optional[Union[int, str]] = None,
            which: Optional[str] = None, along: Optional[str] = None,
            indices: Optional[dict] = None, name: Optional[str] = None):
        """What one leaf does across a series of shots, and `action` picks.

        "values": the trend in campaign order -- the same leaf read from
        each shot (a figure's read of that leaf), one value per shot (a
        named index into the curve, or mean/max/min over it), then the
        per-shot values, the least-squares slope over the shot index, first
        to last, min/max and their shots, and the direction. A one-shot
        campaign, a shot without the leaf, or an all-equal campaign refuses
        in words.

        "report": that answer as a self-contained HTML page -- the per-shot
        table, the trend, the line the values make -- under
        `~/.imasviz/reports`.
        """
        gesture = gestureOf('trend_campaign', {'action': action})
        args = {field: value for field, value in (
            ('cases', cases), ('path', path), ('at', at), ('which', which),
            ('along', along), ('indices', indices), ('name', name),
        ) if value is not None}
        unknown = unknownParameters(gesture, args)
        if unknown:
            raise ValueError(unknownParameterRefusal(gesture, unknown))
        missing = missingParameters(gesture, args)
        if missing:
            raise ValueError(missingParameterRefusal(gesture, missing))
        spelled = argumentsForMember(gesture, args)
        return _run(partial(getattr(core, gesture), **spelled))

    # -------------------------------------------------------------- windows

    @server.tool(name='manage_window')
    def manage_window(
            action: Literal['list', 'show', 'hide', 'close', 'focus'],
            window: Optional[str] = None,
            width: Optional[int] = None,
            height: Optional[int] = None):
        """What one window of the session is asked to do: `action` picks it.

        "list" answers every window in the order the menus draw them -- the
        case views, the figures, the plugin windows, each with its kind, its
        label, its key and whether it is on screen. It asks for no window.

        "show" puts a window back on the screen after a hide, at the size it
        holds; it keeps its key either way. "hide" takes it off the screen
        without deleting it, and "show" brings it back. "close" deletes it
        and forgets its key.

        "focus" is the "show me this" gesture: the window comes forward
        (shown when off screen, raised when not) at the size it holds, and
        `width`/`height` are the pixels to put it at only when they are
        named -- a side left out keeps the size the window holds on that
        side, and a side that is named but is not a positive whole number
        is refused. Left without a `window`, it means the application. The
        answer is the size the window then holds.

        `window` is "app" for the application, a figure key for one figure,
        a case URI for its shot view. Showing is the user's command, not
        something the agent does after a draw: the figure is in the
        *Windows* menu, and that is where the raise lives. Neither a draw
        nor a gesture that moved a figure's content (transform_curve,
        configure_axes) is a reason to call it.
        """
        gesture = gestureOf('manage_window', {'action': action})
        args = {name: value for name, value in (
            ('window', window), ('width', width), ('height', height))
            if value is not None}
        unknown = unknownParameters(gesture, args)
        if unknown:
            raise ValueError(unknownParameterRefusal(gesture, unknown))
        missing = missingParameters(gesture, args)
        if missing:
            raise ValueError(missingParameterRefusal(gesture, missing))
        spelled = argumentsForMember(gesture, args)

        def move():
            return getattr(core, gesture)(**spelled)

        return _run(move)

    # -------------------------------------------------------------- plugins

    @server.tool(name='list_plugins')
    def list_plugins(uri: str, ids_name: str):
        """The entries an IDS root earns, in registration order.

        The feature number, its label, its description for each -- and
        with the answer, the refusals of the plugins the case cannot
        offer, named.
        """
        return _run(partial(core.list_plugins, uri, ids_name))

    @server.tool(name='run_plugin')
    def run_plugin(uri: str, plugin: str, entry: int, occurrence: int = 0,
                   ids_name: Optional[str] = None,
                   time: Optional[float] = None):
        """Run one entry of a plugin, with the answers the entry would
        have asked the user.

        `occurrence` and `time` are handed instead of being asked -- which
        is what keeps a modal question off the path of an agent: an entry
        that asks an instant (`equilibriumsurfaces` entry 1) and is handed
        none is refused by name, not left to open a dialog.

        `ids_name` says which IDS branch the line is asked on. Left out,
        the branch is resolved by searching the case for the branches that
        earn that entry: one is used, several or none is refused with them
        named. Refused by name when the case does not offer that entry.
        """
        return _run(partial(core.run_plugin, uri, plugin, entry,
                            occurrence=occurrence, ids_name=ids_name,
                            time=time))

    # --------------------------------------------------------------- session

    @server.tool(name='manage_session')
    def manage_session(
            action: Literal['save', 'restore', 'new', 'list_sessions',
                            'list_configurations', 'apply', 'save_selection',
                            'save_plot_configuration'],
            name: Optional[str] = None,
            path: Optional[str] = None,
            kind: Optional[str] = None,
            uri: Optional[str] = None,
            figure_key: Optional[str] = None,
    ):
        """The run kept and read back: `action` picks the ask.

        "save" writes the whole screen as the application writes it -- the
        cases, the loads, the selection, the windows and what a hand styled
        on them. `name` is a file under the configuration folder, `path` a
        full file name; left out both, it is written under a name of its
        own.

        "restore" puts one of those sessions back: the cases open, the
        loads replayed, the figures and plugin windows drawn the way the
        file named them.

        "new" is one clean session WITHOUT saving: every case view and
        every figure of this session is closed and nothing is written, so
        the sessions the user saved on disk and the reports stay where they
        are. It answers how many windows it closed, and it is the *New
        session* of the application's *File* menu: a client does not decide
        to clear a run it was not asked to clear.

        "list_sessions" answers the .vsess files the folder holds, and
        "list_configurations" the plot (.pcfg) and selection (.lsp) files;
        `kind` narrows the second to one kind, and a kind the application
        does not answer is refused by name.

        "apply" selects on a case the quantities one saved configuration
        names -- a .lsp as a .pcfg -- loading first the IDSs the case would
        need and does not hold, the way the menu does it. "save_selection"
        writes the case's current selection out as a .lsp (nothing selected
        is refused by name), and "save_plot_configuration" one Table Plot
        View out as a .pcfg, its panels and the places they held -- any
        other window is refused by name.
        """
        gesture = gestureOf('manage_session', {'action': action})
        args = {field: value for field, value in (
            ('name', name), ('path', path), ('kind', kind),
            ('uri', uri), ('figure_key', figure_key))
            if value is not None}
        unknown = unknownParameters(gesture, args)
        if unknown:
            raise ValueError(unknownParameterRefusal(gesture, unknown))
        missing = missingParameters(gesture, args)
        if missing:
            raise ValueError(missingParameterRefusal(gesture, missing))
        spelled = argumentsForMember(gesture, args)
        return _run(partial(getattr(core, gesture), **spelled))

    # --------------------------------------------------------------- reports

    @server.tool(name='generate_report')
    def generate_report(scope: Literal['plot', 'case_loaded', 'case_ids'],
                        figure_key: Optional[str] = None,
                        uri: Optional[str] = None,
                        name: Optional[str] = None):
        """A self-contained HTML report on disk; `scope` says which report.

        "plot" -- a window of curves: the image of the window, and one row
        per trace it drew (the quantity, the number of samples, the finite
        minimum and maximum, the nan/inf counts). The window is named by
        `figure_key`; a window that draws no curve it could stat is refused
        by name. "case_loaded" -- the loaded tree of a case, named by `uri`:
        one row per curve the tree holds, the numeric arrays its leaves
        read, in tree order, with the statistics of each. An IDS not yet
        loaded is not a curve, so the answer says how many curves it gave
        and list_idss names what the case still holds; a case whose loaded
        tree has no curve is refused by name. "case_ids" -- the case itself
        under one page: every IDS its data dictionary holds and the
        occurrences each one holds (read through
        DBEntry.list_all_occurrences, not listed from memory), which of
        those the session loaded, and for each loaded occurrence a header
        of its `ids_properties` values plus its available signals -- kept
        to the ones the tree carries as available, the same test its own
        colouring applies, a 0-D scalar held by the dynamic array among
        them. A property the case leaves empty is named empty, an
        occurrence without an available signal is named as such, and a case
        that holds no data at all is refused by name. The file lands in
        `~/.imasviz/reports`; `name` is the report name (a place, not a
        report, is refused).
        """
        # The parameters an action needs are the table's, not this
        # signature's: the signature has to hold every action's names, so
        # `scope="plot"` without a `figure_key` is legal to FastMCP and
        # would reach the core as a call missing its subject.
        gesture = gestureOf('generate_report', {'scope': scope})
        missing = missingParameters(gesture, {'figure_key': figure_key,
                                              'uri': uri})
        if missing:
            raise ValueError(missingParameterRefusal(gesture, missing))
        if gesture == 'plot_report':
            return _run(partial(core.plot_report, figure_key, name=name))
        if gesture == 'case_report':
            return _run(partial(core.case_report, uri, name=name))
        return _run(partial(core.case_ids_report, uri, name=name))

    # ---------------------------------------------------------------- export

    @server.tool(name='export_to_ids')
    def export_to_ids(uri: str, target_uri: str,
                      dd_version: Optional[str] = None):
        """Copy the opened IDSs of one case into the target case.

        `target_uri` is the case the Access Layer writes to
        (imas:hdf5?path=...); the write goes under the data dictionary
        the case was read at unless `dd_version` says otherwise.
        """
        return _run(partial(core.export_to_ids, uri, target_uri,
                            dd_version=dd_version))

    # ------------------------------------------------------------ screenshot

    @server.tool(name='get_screenshot')
    def get_screenshot(window: str = 'app'):
        """A window as it stands, in PNG.

        "app" for the application, a figure key for one figure, a case
        URI for its shot view -- the image content of the answer is the
        picture itself. The picture is the size the window is: when a
        requested picture should be readable and the window answers
        small, size it with manage_window(action='focus', width, height)
        first, then take the picture.
        """
        png = _run(partial(core.screenshot, window))
        return [
            mcp_types.TextContent(
                type='text',
                text='PNG of %s, %d bytes.' % (window, len(png))),
            mcp_types.ImageContent(
                type='image',
                data=base64.b64encode(png).decode('ascii'),
                mimeType='image/png'),
        ]

    # ------------------------------------------------------------------- log

    @server.tool(name='get_logs')
    def get_logs(uri: Optional[str] = None, tail: int = 200):
        """The log panel of one case, or of every case when `uri` is left
        out: the last `tail` lines the gestures wrote there, the named
        refusals among them -- where an agent reads what a dialog would
        have told it."""
        return _run(partial(core.get_logs, uri, tail=tail))

    # ------------------------------------------------------------- journals

    @server.tool(name='manage_note')
    def manage_note(
            action: Literal['search', 'list', 'read', 'add', 'delete',
                            'stats', 'reindex'],
            scope: Optional[str] = None,
            note_id: Optional[str] = None,
            query: Optional[str] = None,
            limit: Optional[int] = None,
            text: Optional[str] = None,
            machine: Optional[str] = None,
            campaign: Optional[str] = None,
            shot: Optional[str] = None,
            date: Optional[str] = None,
            date_from: Optional[str] = None,
            date_to: Optional[str] = None,
            author: Optional[str] = None,
            title: Optional[str] = None,
    ):
        """The lab notebook of the two journals: `action` picks the ask.

        "search" answers the notes that fit the filters you name, ranked for
        the `query` you ask in -- by words first and by meaning when an
        embeddings endpoint is set, and the method it used is in the answer.
        "list" is the same filters without a query, in date order, each note
        in its short view (the fields that name it and a line of its body).

        "read" answers the whole note under `note_id` (the fields that name
        it -- author, machine, campaign, shot, date, title -- and its body),
        the id coming from a "search" or "list" answer. "delete" takes that
        note out, naming in the answer the scope and the id it removed.
        "stats" answers what the two journals hold on this node: the two
        directories, the count of notes each answers, and whether an
        embeddings endpoint is set (and on which model) -- a search on this
        node ranks by words until it is. "reindex" puts the journal(s) in
        step with their index, the ask of a search that came back `guarded`
        (an index written under an embeddings endpoint this run is no longer
        under) or of a journal never indexed; it keeps the rows it has,
        re-embeds the ones that moved, drops the ones the journal no longer
        holds, and answers per journal how many of each.

        "add" writes a line: `text` is the body, and the fields that name
        the note are `author` (left out for a note by the agent), `machine`,
        `campaign`, `shot`, `date` and `title` -- all optional, a note may be
        a general observation that names no shot and no machine. The `id` and
        `path` the file lands under come back in the answer.

        `scope` is WHICH journal, not which action: `personal` (the author's
        own notes) or `shared` (the cahier a writer sees), and left out it
        asks the two -- a journal not on this node is left out of the answer,
        named in it. `date_from` / `date_to` bound the shot date
        (`YYYY-MM-DD`) on "search" and "list"; `date` is one note's date on
        "add". A note may carry no filter: a filter it does not carry leaves
        it out of the answer, not out of the query you ran on its body.

        Changing a note in place is not on this face -- it is the page's
        Edit button that asks that gesture, so a note keeps the id the other
        writers read it under.
        """
        gesture = gestureOf('manage_note', {'action': action})
        args = {name: value for name, value in (
            ('scope', scope), ('note_id', note_id), ('query', query),
            ('limit', limit), ('text', text), ('machine', machine),
            ('campaign', campaign), ('shot', shot), ('date', date),
            ('date_from', date_from), ('date_to', date_to),
            ('author', author), ('title', title))
            if value is not None}
        unknown = unknownParameters(gesture, args)
        if unknown:
            raise ValueError(unknownParameterRefusal(gesture, unknown))
        missing = missingParameters(gesture, args)
        if missing:
            raise ValueError(missingParameterRefusal(gesture, missing))
        spelled = argumentsForMember(gesture, args)
        return _run(partial(getattr(core, gesture), **spelled))

    # ------------------------------------------------------------- prompts

    @server.tool(name='manage_prompt')
    def manage_prompt(
            action: Literal['list', 'detail', 'fill', 'save', 'edit',
                            'delete'],
            name: Optional[str] = None,
            scope: Optional[str] = None,
            text: Optional[str] = None,
            category: Optional[str] = None,
            description: Optional[str] = None,
            variables: Optional[Union[dict, str]] = None,
            prompt_id: Optional[str] = None,
            values: Optional[dict] = None,
            query: Optional[str] = None,
            limit: Optional[int] = None,
    ):
        """The catalogue of prompts the user wrote once and asks again:
        `action` picks the ask.

        "list" answers the prompts -- id, name, category, one-line
        description, and the holes each opens. `category` and `query` narrow
        it and `categories` answers how many prompts each category holds. The
        personal catalogue is under ~/.imasviz/prompts and the shared one
        under the folder SharedPromptsDir names; an unnamed shared folder
        costs its own half of the list, named in `catalogues_unavailable`.
        Ask of it when the user says "relance le prompt ..." and you do not
        know the wording they filed.

        "detail" answers one prompt whole (its body with its holes open, and
        what each hole would be answered from right now) and remembers
        nothing. "fill" answers the prompt with its holes filled and runs
        nothing: a hole is filled from the first source that answers it --
        what you name in `values`, what was typed last time, what this
        session knows, what the file declares -- and a hole none of them
        answers is a refusal naming the holes. Take the `text` it answers and
        ask it as the user asked it: filling is not running.

        "save" files a new prompt (`text` with its holes spelled `{name}`,
        `variables` read off the text when left out). "edit" changes one in
        place, keeping the id its remembered values were written under -- a
        field left out keeps the value it held; a NEW prompt is "save".
        "delete" takes a prompt and its remembered values off the disk.

        `scope` is WHICH catalogue -- `personal`, or `shared` (a line the
        team reads, which the user has to ask for in their own words) -- and
        left out it asks both. Filing, changing and deleting are asked for in
        the user's own words: a turn that merely drew a figure is not an ask
        to file its wording.
        """
        gesture = gestureOf('manage_prompt', {'action': action})
        args = {field: value for field, value in (
            ('name', name), ('scope', scope), ('text', text),
            ('category', category), ('description', description),
            ('variables', variables), ('prompt_id', prompt_id),
            ('values', values), ('query', query), ('limit', limit))
            if value is not None}
        unknown = unknownParameters(gesture, args)
        if unknown:
            raise ValueError(unknownParameterRefusal(gesture, unknown))
        missing = missingParameters(gesture, args)
        if missing:
            raise ValueError(missingParameterRefusal(gesture, missing))
        spelled = argumentsForMember(gesture, args)
        return _run(partial(getattr(core, gesture), **spelled))

    # ----------------------------------------------------------- documents

    @server.tool(name='manage_documents')
    def manage_documents(
            action: Literal['list', 'search', 'read', 'reindex', 'stats'],
            query: Optional[str] = None,
            limit: Optional[int] = None,
            rel: Optional[str] = None):
        """The corpus of documents the agent reads for itself, and `action`
        picks the ask.

        "list" answers the markdown, text and PDF files the folder
        AgentDocsDir names (the name, the size, the date, and the `rel` a
        search answers by). An empty corpus -- a folder with no document --
        is an answer; a corpus with no folder named is a refusal that
        names it.

        "search" ranks the chunks of those files, one hit per chunk: the
        document `rel`, the chunk, a snippet. It is the ask when the
        question is about the user's own writing. The answer names the
        method it ranked with (hybrid / embeddings / keyword / empty); a
        store written under another embeddings endpoint is `guarded`, its
        vectors standing in a different space than the query, and the
        keyword alone ranks.

        "read" gives one document whole, by the `rel` a hit names -- the
        ask when a hit is worth reading entire. Not in the corpus is a
        refusal by name, naming the ones it does read.

        "reindex" puts the corpus in step with its store: after a document
        was added to the folder, or when a search comes back `guarded`. It
        keeps what it has, re-embeds what moved, drops what left the
        folder, and answers how many documents and chunks it kept, wrote
        and dropped.

        "stats" names how many documents and chunks the corpus holds, the
        embeddings endpoint and model it was written under, and when it was
        built -- the answer when "can the agent read my documents" is "it
        is not indexed yet".
        """
        gesture = gestureOf('manage_documents', {'action': action})
        args = {field: value for field, value in (
            ('query', query), ('limit', limit), ('rel', rel))
            if value is not None}
        unknown = unknownParameters(gesture, args)
        if unknown:
            raise ValueError(unknownParameterRefusal(gesture, unknown))
        missing = missingParameters(gesture, args)
        if missing:
            raise ValueError(missingParameterRefusal(gesture, missing))
        spelled = argumentsForMember(gesture, args)
        return _run(partial(getattr(core, gesture), **spelled))

    return server
