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
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp import types as mcp_types

INSTRUCTIONS = """IMASViz, the ITER/CEA visualization front-end for IMAS plasma-fusion
cases, driven by name and answered by name.

How to work with it:
1. open_case(uri) -- the data dictionary is asked of the case when you do
   not name one;
2. list_idss(uri) tells which IDSs the case holds and which occurrences;
3. load_ids(uri, ids_name, occurrence) builds the tree branch;
4. search_nodes(uri, query) names the leaves in every spelling the tree
   holds -- the paths select_signals, plot_one and get_signal take are
   any of those spellings;
5. plot_one / plot_selection / plot_table / plot_stacked draw, and
   get_screenshot answers a PNG of the window; the equilibrium has its
   own two entries -- equilibrium_surfaces puts the flux surfaces of the
   instants you name side by side, and equilibrium_at_time puts one
   instant's surface with its radial profiles in one window, the global
   quantities of the slice coming back in the answer;
6. state is read with list_selection (what the case holds selected),
   describe_node (what one node holds: documentation, units, size, the
   finite minimum and maximum, the nan and inf counts, a bounded
   preview), describe_ids (what the data dictionary says about an IDS:
   comment, homogeneous_time, units, time units, data dictionary
   version), and list_quantities (the filled tensors of one occurrence,
   grouped by array of structures) -- answers, not guesses, and empty is
   an answer too;
7. a report is self-contained HTML on disk: plot_report names one window
   of curves (its image, one row per curve it drew, with the statistics
   of each), case_report names the whole loaded tree of a case (one row
   per curve it holds, in tree order), and case_ids_report names the
   case itself -- every IDS the case holds and the occurrences each
   holds, the ones the user loaded, a header of the `ids_properties`
   values per loaded occurrence, and the signals the tree holds for each
   (the ones it carries as available, a 0-D scalar held by the dynamic
   array among them).
8. manipulating a figure is work on what it holds, by name of the figure
   and of the curve: scale_curve multiplies its value by a constant,
   shift_curve adds one, normalize_curve divides by its own peak/first/
   mean; curve_stats and export_curve read the numbers as they stand, so a
   transform a hand put on is the value it returns. reset_curve takes the
   transform off, remove_curve takes the curve off. The axes are set by
   name and number: set_axis_range pins the window (xmin/xmax, ymin/ymax,
   or auto=True to re-fit), set_log_scale makes an axis log (True) or
   linear (False), invert_axis flips one. A curve is selected by a
   substring of its name, a 0-based index, or left out for every one; a
   log on values that cross zero is refused by name, and a figure that is
   not a single one (a table, or the flux-surface figure) is refused the
   same way -- name the figure the single curve was drawn in.

The state of a figure is what the calls of this session made, and a read
this session answered -- not what was said of it. A curve you say was
added, a transform you say was applied, an axis you say moved: each of
those stands only if the call that did it succeeded naming that figure,
or a read of the figure (curve_stats, export_curve) answered that state.
A refused call changed nothing: it added no curve, applied no transform
and moved no axis, so the answer is the refusal it named, with the
reason it gave -- not the state it would have left. A call that did not
run, or that had not returned when you answered, is not a success: read
the figure with curve_stats before saying what it holds, or say it
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

    @server.tool(name='search_nodes')
    def search_nodes(uri: str, query: str = '',
                     ids_name: Optional[str] = None, limit: int = 200):
        """The leaves of the case, matched by a substring of their spellings.

        `query` is a case-insensitive substring matched against the
        display path, the data name and the parametrized path of every
        leaf; `ids_name` narrows to one IDS. The answer holds the three
        spellings of every match, and any of them is what
        `select_signals`, `plot_one` and `get_signal` take.
        """
        return {'matches': _run(partial(core.search_nodes, uri, query,
                                        ids_name=ids_name, limit=limit))}

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

    @server.tool(name='describe_node')
    def describe_node(uri: str, path: str):
        """What this node holds, as the application's documentation says it.

        Dictionary documentation and units, and for an array the size,
        shape, the finite minimum and maximum, the counts of zeros, nan
        and inf entries, and a bounded preview of the values. A leaf the
        tree does not hold is refused by name.
        """
        return _run(partial(core.describe_node, uri, path))

    @server.tool(name='describe_ids')
    def describe_ids(uri: str, ids_name: str, occurrence: int = 0):
        """What the data dictionary says about an IDS: its comment
        (ids_properties.comment), homogeneous_time, units, time units,
        and the data dictionary version the case was written at.

        A property the case leaves empty is absent, not invented; an IDS
        the case does not declare is refused by name.
        """
        return _run(partial(core.describe_ids, uri, ids_name,
                            occurrence=occurrence))

    @server.tool(name='list_quantities')
    def list_quantities(uri: str, ids_name: str, occurrence: int = 0):
        """The filled tensors (dimension >= 1) of one occurrence, grouped
        by the array of structures that drives them.

        One entry per quantity: its path, data name, parametrized path,
        units, data type, and how many elements of its array the case
        holds. A quantity that contains no data (not blue in the tree) is
        not listed, and scalar leaves (0D) are not tensors and are not
        listed either. An occurrence whose tree was never built is
        refused by name: load it with load_ids first.
        """
        return _run(partial(core.list_quantities, uri, ids_name,
                            occurrence=occurrence))

    # -------------------------------------------------------------- plotting

    @server.tool(name='plot_one')
    def plot_one(uri: str, path: str, along_time: Optional[bool] = None,
                 into_figure_key: Optional[str] = None,
                 along: Optional[str] = None,
                 indices: Optional[dict] = None,
                 time: Optional[float] = None,
                 time_interp: Optional[bool] = None):
        """Draw one quantity, into the figure its axes call for.

        A curve figure for one axis to draw, a picture window for two.
        The address is the one the agent and `get_signal` take, so the
        figure a reader sees and the numbers a read reports are the same
        element of the same array: `along` names the axis the quantity
        runs along (the clock, or one of its own axes, e.g. `psi`), and
        `indices` pins each OTHER axis at its 0-based index, one entry per
        nested array of structures (`time_slice`, `profiles_1d`, `ion`, ...)
        or the leaf's own coordinate. `equilibrium.time_slice[0]
        .profiles_1d.pressure` is a profile held by the dynamic array, so
        "le long du temps, un index `psi` de 50" is `along` left out (the
        clock) and `indices={"psi": 50}` -- not a legacy position.
        `along_time` and `indices` are the legacy ways of the same ask.
        `time` pins a profile to one slice of its dynamic time array (by
        default the nearest; `time_interp=true` the value between the two
        that bracket it); `time` and the unified schema are refused
        together, as opposite readings. `into_figure_key` adds it to an
        open curve figure (a superposition) instead of opening one. A
        quantity the read cannot answer, or an index past the extent the
        tree names, is refused with the reason the application names in
        its log, not a silent 0. The answer carries the figure key and
        `curves`, the exact list of the curves the figure holds after the
        call: a claim that a curve is on that figure stands on that list,
        not on memory of the call.
        """
        kwargs = {'along_time': along_time,
                  'into_figure_key': into_figure_key,
                  'along': along, 'indices': indices,
                  'time': time}
        if time_interp is not None:
            kwargs['time_interp'] = time_interp
        return _run(partial(core.plot_one, uri, path, **kwargs))

    @server.tool(name='plot_slice')
    def plot_slice(uri: str, leaf: str, time: float,
                   occurrence: int = 0,
                   interpolation: str = 'linear',
                   into_figure_key: Optional[str] = None):
        """Draw one 1D-profile leaf at a single time, the value the Access
        Layer answers at that instant (its own `DBEntry.get_slice`, not a
        GUI-side lerp).

        The coordinate is the leaf's own (independent of time); the curve
        is its value at `time`. `interpolation` is `linear` (default),
        `closest` (the case's nearest slice) or `previous` (the one at or
        before `time`); a time outside the case's range answers the nearest
        slice it holds, and the answer names `time_requested` and
        `time_slice_time` apart. `into_figure_key` adds the profile to an
        open figure (a superposition of slices) instead of opening one.
        Not a 2D-pictorial leaf, nor a 0D scalar.
        """
        return _run(partial(core.plot_slice, uri, leaf, time,
                            occurrence=occurrence,
                            interpolation=interpolation,
                            into_figure_key=into_figure_key))

    @server.tool(name='equilibrium_surfaces')
    def equilibrium_surfaces(uri: str, times: list, occurrence: int = 0):
        """The flux surfaces of the equilibrium, one frame per named instant.

        `times` is the list of instants in seconds (a single number is read
        as a list of one). The instants answer the case's own slices
        nearest to them -- a GGD grid is discrete, and the frame each
        instant answered is named back: `time_requested` vs
        `time_slice_time` and the slice index, per frame. Every frame
        shares the levels, the bounds and the marks (plasma boundary,
        magnetic axis, O-point, limiter), so the instants compare at
        equal measure. The window opens in the session like every other
        figure (`EquiSurfaces:` key); get_screenshot answers its PNG."""
        return _run(partial(core.equilibrium_surfaces, uri, times,
                            occurrence=occurrence))

    @server.tool(name='equilibrium_at_time')
    def equilibrium_at_time(uri: str, time: float, occurrence: int = 0):
        """One instant of the equilibrium, the way the Equilibrium plugin
        reads it: the flux surface at the instant, the radial profiles
        under it (q, elongation, triangularities, j_tor in MA/m^2,
        pressure in kPa, f_df_dpsi, dpressure_dpsi -- the plugin's
        quantities and its unit conversions, on rho_tor_norm), and the
        global quantities of the slice (Ip in kA, q95, q_axis, li_3,
        W_mhd in kJ, axis position) in the answer itself.

        `time` in seconds answers the nearest slice the case holds, named
        back as `time_slice_time`; a time outside the case's range says
        it was clamped. Not a leaf of the tree: the read is the one the
        plugin does on the IDS object, which the tree does not hold
        (the GGD branch, and the profiles read at one named slice)."""
        return _run(partial(core.equilibrium_at_time, uri, time,
                            occurrence=occurrence))

    @server.tool(name='plot_selection')
    def plot_selection(uri: str):
        """Draw the case selection: one curve figure, one window per picture.

        `select_signals` first. The selection of this case alone, not the
        other open cases -- the figure keys the windows carry come back.
        """
        return _run(partial(core.plot_selection, uri))

    @server.tool(name='plot_table')
    def plot_table(uri: str, paths: list, columns: Optional[int] = None,
                   plot_axis: Optional[str] = None):
        """One panel per named path, in a Table Plot View.

        `columns` sets the width of the row, `plot_axis` "TIME" reads
        every quantity along time; a quantity that reads nothing is
        refused with the reason it gave.
        """
        return _run(partial(core.plot_table, uri, paths, columns=columns,
                            plot_axis=plot_axis))

    @server.tool(name='plot_stacked')
    def plot_stacked(uri: str, paths: list, plot_axis: str = 'TIME'):
        """The named paths stacked one panel per quantity.

        Against the abscissa `plot_axis` names, the default being the
        clock.
        """
        return _run(partial(core.plot_stacked, uri, paths,
                            plot_axis=plot_axis))

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
        axis at its 0-based index (the shared schema of `plot_one`).
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

    @server.tool(name='scale_curve')
    def scale_curve(figure_key: str, factor: float,
                    curve: Optional[str] = None):
        """Multiply a figure's drawn curve(s) by a constant.

        In place and reversible (`reset_curve`), on the curves the figure
        named: `curve` is a name substring, an index, or left out for every
        curve the figure holds. `factor` must be a finite number. This turns
        the value of the curve as a reader of it reads it, not the quantity
        in the tree, so `curve_stats` and `export_curve` then answer the
        multiplied number.
        """
        return _run(partial(core.scale_curve, figure_key, factor, curve=curve))

    @server.tool(name='shift_curve')
    def shift_curve(figure_key: str, offset: float,
                    curve: Optional[str] = None):
        """Add a constant to a figure's drawn curve(s): a vertical offset.

        The inverse of a subtraction, on the same curve (by name, index, or
        all) as `scale_curve`. `offset` must be a finite number.
        """
        return _run(partial(core.shift_curve, figure_key, offset, curve=curve))

    @server.tool(name='normalize_curve')
    def normalize_curve(figure_key: str, mode: str = 'max',
                        curve: Optional[str] = None):
        """Divide a figure's drawn curve(s) by a reference of their own.

        `mode` is `max` (split by the largest sample), `first` (split by the
        first, index 0), or `mean` (split by the mean). A reference that is
        zero or not a number is refused by name; the division is then
        undefined and would read as a picture full of no-signal.
        """
        return _run(partial(core.normalize_curve, figure_key, mode, curve=curve))

    @server.tool(name='reset_curve')
    def reset_curve(figure_key: str, curve: Optional[str] = None):
        """Put a figure's curve(s) back to the data they were drawn with.

        The transform that scale, shift and normalize put on is taken off,
        and a curve nobody transformed is not in the answer. `curve` targets
        the one or the figure's.
        """
        return _run(partial(core.reset_curve, figure_key, curve=curve))

    @server.tool(name='remove_curve')
    def remove_curve(figure_key: str, curve: Optional[str] = None):
        """Take a curve off a figure, or every one when `curve` is left out.

        The trace leaves the plot and the figure forgets it; the answer is
        the count still held. The figure is the one a single curve was drawn
        in; a table or the flux-surface figure are not it, and are refused
        by name.
        """
        return _run(partial(core.remove_curve, figure_key, curve=curve))

    @server.tool(name='set_axis_range')
    def set_axis_range(figure_key: str, xmin: Optional[float] = None,
                       xmax: Optional[float] = None,
                       ymin: Optional[float] = None,
                       ymax: Optional[float] = None,
                       auto: bool = False):
        """The window (the range) of a figure's axes, by name and number.

        Pin `xmin`/`xmax` together (the abscissa) and/or `ymin`/`ymax`
        (the ordinate); a partial ask (one bound of a pair) is refused
        because a range is two. `auto=True` clears the pins and re-fits.
        A curve figure takes one axis set; a picture window takes the same
        span on the axis set of each of its pictures, so the time zoom of
        a strip whose abscissa is its time is the `x` range, in the
        seconds its time axis holds. A table and a stacked window keep
        one axis set per panel and are refused by name.
        """
        return _run(partial(core.set_axis_range, figure_key,
                            xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax,
                            auto=auto))

    @server.tool(name='set_image_window')
    def set_image_window(figure_key: str, start: Optional[int] = None,
                         count: Optional[int] = None):
        """The window a picture window's pictures sit on: moved with
        `start` (where it sits on the axis it reads across; the pictures
        are re-read in place, the scale and the band stay put), and
        resized with `count` (how many pictures it holds; the scale a hand
        settled is not moved off by the rebuild). Name at least one of
        the two.

        The answer carries the axis it reads across, its start and count,
        the extent the axis holds, and the label of each picture the
        window shows (the element it is, and the value the axis carries
        there when the axis is the time), so a window of three time slices
        answers the three slices it holds by their time, not by rank. A
        window that is not a picture window is refused by name (the shape
        it holds, and the gesture the question it was asked belongs to);
        so is one that holds a single picture, not a window of them (the
        span of that one is `set_axis_range`), and an ask that names
        neither the start nor the count of the window.
        """
        return _run(partial(core.set_image_window, figure_key,
                            start=start, count=count))

    @server.tool(name='set_slice_index')
    def set_slice_index(figure_key: str, axis: str, index: int):
        """A row of the slider band of a figure, posed at a named index:
        `axis` the row in the words the band spells it (an array of
        structures by its name -- `time_slice`, `profiles_2d` -- or the
        coordinate it holds), and `index` the element it is posed at (a
        0-based whole number, within the extent the row holds).

        The window re-reads the one the row is posed at -- the same read
        the slider drives, and the other rows of the band stay where they
        are -- and the answer carries the rows of the band it holds and
        the index each one is posed at, so one asks, reads, and confirms
        in the same call. It addresses a curve figure that pins an axis
        and an image window that pins one; a table and a stacked window
        are refused by name, and so is a row the band does not hold (the
        rows it does, named), and an index past the extent the row holds
        (the bound it holds, named). A picture window whose pictures hold
        the axis the gesture names holds no row for it: the axis is on
        screen, one picture per element, and the refusal names
        `set_image_window` (the start and count of that window) as the
        gesture the question it was asked belongs to.
        """
        return _run(partial(core.set_slice_index, figure_key,
                            axis=axis, index=index))

    @server.tool(name='set_log_scale')
    def set_log_scale(figure_key: str, x: Optional[bool] = None,
                      y: Optional[bool] = None):
        """A log axis, by name: `x`/`y` each `True` for log, `False` for
        linear. Name at least one. A log on a set of values that cross zero
        or below is refused by name, because the picture hides them and
        reads as empty where it holds a half-empty axis; `shift_curve` to
        clear the negatives is the answer.
        """
        return _run(partial(core.set_log_scale, figure_key, x=x, y=y))

    @server.tool(name='invert_axis')
    def invert_axis(figure_key: str, x: Optional[bool] = None,
                    y: Optional[bool] = None):
        """Invert (flip) an axis: `x=True`/`y=True` turn one around so the
        negative direction is the other way. `False` puts it back. Name at
        least one. Inversion and range are independent; a pinned range
        stays where the values sit, the picture reads reversed.
        """
        return _run(partial(core.invert_axis, figure_key, x=x, y=y))

    @server.tool(name='curve_stats')
    def curve_stats(figure_key: str, curve: Optional[str] = None):
        """The numbers of a figure's drawn curve(s): sample count, the
        finite min/max/mean/std of the values, the nan/inf counts, and the
        peak value with its abscissa. The read of a figure's curves in a
        place the reader can act on, before or after a scale/shift/
        normalize; a `plot_report` is the same read with an HTML file.
        """
        return _run(partial(core.curve_stats, figure_key, curve=curve))

    @server.tool(name='export_curve')
    def export_curve(figure_key: str, curve: Optional[str] = None,
                     format: str = 'csv', name: Optional[str] = None):
        """Take a figure's drawn curve(s) out to a file: the values as they
        stand (a scale/shift/normalize on them is in the file). `format`
        `csv` (default) or `json`; `curve` a name, an index, or left out.
        The file lands in `~/.imasviz/exports` under the guard of the
        configurations; a `name` that names a place, not a file, is refused
        by name.
        """
        return _run(partial(core.export_curve, figure_key, curve=curve,
                            format=format, name=name))

    # -------------------------------------------------------------- events

    @server.tool(name='detect_events')
    def detect_events(uri: str, path: str, kind: str,
                      threshold: Optional[float] = None,
                      prominence: Optional[float] = None,
                      min_distance: Optional[int] = None,
                      direction: Optional[str] = None,
                      hysteresis: Optional[float] = None,
                      along: Optional[str] = None,
                      indices: Optional[dict] = None,
                      figure_key: Optional[str] = None):
        """The events of one kind read off the leaf's signal: `elm`
        (an excursion up), `sawtooth` (a crash down), or `lh` (a threshold
        crossing). The signal is the one get_signal answers, so what is
        detected and what a figure of the same leaf draws are the same
        read. A kind refuses a parameter it does not take, by name. `figure_key`
        marks the events on that curve figure (capped), and clear_event_marks
        takes them off again.
        """
        return _run(partial(core.detect_events, uri, path, kind,
                            threshold=threshold,
                            prominence=prominence,
                            min_distance=min_distance,
                            direction=direction,
                            hysteresis=hysteresis,
                            along=along, indices=indices,
                            figure_key=figure_key))

    @server.tool(name='clear_event_marks')
    def clear_event_marks(figure_key: str):
        """The event marks off a curve figure, one detect_events put there.
        Safe when the figure holds none: it answers the number it took off.
        """
        return _run(partial(core.clear_event_marks, figure_key))

    @server.tool(name='events_report')
    def events_report(uri: str, path: str, kind: str,
                      threshold: Optional[float] = None,
                      prominence: Optional[float] = None,
                      min_distance: Optional[int] = None,
                      direction: Optional[str] = None,
                      hysteresis: Optional[float] = None,
                      along: Optional[str] = None,
                      indices: Optional[dict] = None,
                      figure_key: Optional[str] = None,
                      name: Optional[str] = None):
        """The events of one kind as a self-contained HTML report: the same
        read and detection as detect_events, the events in a table, the
        period of their times, and the figure when one is named. Lands in
        `~/.imasviz/reports` like the other reports.
        """
        return _run(partial(core.events_report, uri, path, kind,
                            threshold=threshold,
                            prominence=prominence,
                            min_distance=min_distance,
                            direction=direction,
                            hysteresis=hysteresis,
                            along=along, indices=indices,
                            figure_key=figure_key, name=name))

    @server.tool(name='spectrum')
    def spectrum(uri: str, path: str,
                 n_peaks: Optional[int] = None,
                 band_low: Optional[float] = None,
                 band_high: Optional[float] = None,
                 along: Optional[str] = None,
                 indices: Optional[dict] = None):
        """What a leaf's time series oscillates at: the dominant frequency and
        period, the leading peaks (most power first), and the band's share when
        a band is named. The read is the one get_signal answers for the leaf,
        so the frequency read is the one a figure of the same leaf draws. A band
        named with only one bound is refused by name.
        """
        return _run(partial(core.spectrum, uri, path,
                            n_peaks=n_peaks, band_low=band_low,
                            band_high=band_high,
                            along=along, indices=indices))

    @server.tool(name='cross_correlation')
    def cross_correlation(uri: str, path: str, path_b: str,
                          along: Optional[str] = None,
                          indices: Optional[dict] = None,
                          indices_b: Optional[dict] = None):
        """How far one leaf's time series lags or leads another, and at what
        the two ring together. Both reads are the ones a figure draws, so a
        pair the case does not hold on one clock, or at one length, is refused
        by name.
        """
        return _run(partial(core.cross_correlation, uri, path, path_b,
                            along=along, indices=indices, indices_b=indices_b))

    @server.tool(name='spectrum_report')
    def spectrum_report(uri: str, path: str,
                        n_peaks: Optional[int] = None,
                        band_low: Optional[float] = None,
                        band_high: Optional[float] = None,
                        along: Optional[str] = None,
                        indices: Optional[dict] = None,
                        figure_key: Optional[str] = None,
                        name: Optional[str] = None):
        """The spectral facts of a leaf's series as a self-contained HTML
        report: the peaks in a table, the band when named, and the figure when
        one is named. Lands in `~/.imasviz/reports`.
        """
        return _run(partial(core.spectrum_report, uri, path,
                            n_peaks=n_peaks, band_low=band_low,
                            band_high=band_high,
                            along=along, indices=indices,
                            figure_key=figure_key, name=name))

    # -------------------------------------------------------------- windows

    @server.tool(name='list_windows')
    def list_windows():
        """Every window of the session, in the order the menus draw them.

        The case views, the figures, the plugin windows: each with its
        kind, its label, its key and whether it is on screen.
        """
        return {'windows': _run(core.list_windows)}

    @server.tool(name='show_window')
    def show_window(key: str):
        """Put a window back on the screen; it keeps its key either way."""
        return _run(partial(core.show_window, key))

    @server.tool(name='hide_window')
    def hide_window(key: str):
        """Take a window off the screen without deleting it: it keeps its
        key and `show_window` brings it back."""
        return _run(partial(core.hide_window, key))

    @server.tool(name='close_window')
    def close_window(key: str):
        """Close a window for good: it is deleted and forgets its key."""
        return _run(partial(core.close_window, key))

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
                   ids_name: Optional[str] = None):
        """Run one entry of a plugin, with the answers the entry would
        have asked the user.

        `occurrence` is the one the entry plots, handed instead of being
        asked -- which is what keeps a modal question off the path of an
        agent. Refused by name when the case does not offer that entry.
        """
        return _run(partial(core.run_plugin, uri, plugin, entry,
                            occurrence=occurrence, ids_name=ids_name))

    # --------------------------------------------------------------- session

    @server.tool(name='save_session')
    def save_session(name: Optional[str] = None,
                     path: Optional[str] = None):
        """Write the session as the application writes it.

        The cases, the loads, the selection, the windows and their
        styling. `name` is a file under the configuration folder, `path`
        a full file name; the answer is the file that holds it.
        """
        return _run(partial(core.save_session, name=name, path=path))

    @server.tool(name='restore_session')
    def restore_session(name: Optional[str] = None,
                        path: Optional[str] = None):
        """Put a session back: the cases open, the loads replayed, the
        figures and plugin windows drawn the way the file named them."""
        return _run(partial(core.restore_session, name=name, path=path))

    @server.tool(name='list_sessions')
    def list_sessions():
        """The sessions the configuration folder holds, as the dialog lists them."""
        return {'sessions': _run(core.list_sessions)}

    @server.tool(name='list_configurations')
    def list_configurations(kind: Optional[str] = None):
        """The plot (.pcfg) and selection (.lsp) configurations the folder holds.

        `kind` narrows to one of the two kinds; a kind the application
        does not answer is refused by name, 'session' among them.
        """
        return _run(partial(core.list_configurations, kind))

    @server.tool(name='select_from_configuration')
    def select_from_configuration(uri: str, name: str):
        """Apply one saved configuration: select the quantities it names.

        A .lsp as a .pcfg; the IDSs the case would need and does not
        hold are loaded first, the way the menu does it. A name the
        folder does not hold is refused by name, naming the ones it does.
        """
        return _run(partial(core.select_from_configuration, uri, name))

    @server.tool(name='save_selection')
    def save_selection(uri: str, name: str):
        """Write the current selection of the case out as a .lsp.

        Nothing selected is refused by name; the name goes through the
        guard the application applies in its own dialog.
        """
        return _run(partial(core.save_selection, uri, name))

    @server.tool(name='save_plot_configuration')
    def save_plot_configuration(uri: str, figure_key: str, name: str):
        """Write one Table Plot View out as a .pcfg, the panels and their places.

        A window that is not a Table Plot View is refused by name.
        """
        return _run(partial(core.save_plot_configuration, uri,
                            figure_key, name))

    # --------------------------------------------------------------- reports

    @server.tool(name='plot_report')
    def plot_report(figure_key: str, name: Optional[str] = None):
        """A window of curves as a self-contained HTML report on disk.

        The image of the window, and one row per trace it drew -- the
        quantity, the number of samples, the finite minimum and maximum,
        and the nan/inf counts. The file lands in `~/.imasviz/reports`;
        `name` is the report name (a place, not a report, is refused).
        A window that draws no curve it could stat is refused by name.
        """
        return _run(partial(core.plot_report, figure_key, name=name))

    @server.tool(name='case_report')
    def case_report(uri: str, name: Optional[str] = None):
        """The loaded tree of a case as a self-contained HTML report on disk.

        One row per curve the tree holds -- the numeric arrays its leaves
        read, in tree order -- with the statistics of each. `name` is the
        report name (a place, not a report, is refused). A case whose
        loaded tree has no curve is refused by name.
        """
        return _run(partial(core.case_report, uri, name=name))

    @server.tool(name='case_ids_report')
    def case_ids_report(uri: str, name: Optional[str] = None):
        """The case itself as a self-contained HTML report on disk.

        The inventory of the case under one page: every IDS the case's
        data dictionary holds and the occurrences each one holds (read
        through DBEntry.list_all_occurrences, not listed from memory),
        which of those the session loaded, and for each loaded occurrence
        a header of the `ids_properties` values of that occurrence plus
        its available signals -- the signals the tree holds for it, kept
        to the ones the tree carries as available (the same test its own
        colouring applies), a 0-D scalar held by the dynamic array among
        them. A property the case leaves empty is named empty, an
        occurrence without an available signal is named as such, and a
        case that holds no data at all is refused by name. `name` is the
        report name (a place, not a report, is refused).
        """
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
        picture itself.
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

    @server.tool(name='focus_window')
    def focus_window(window: str = 'app',
                     width: Optional[int] = None,
                     height: Optional[int] = None):
        """Bring a window forward -- the caller's "show me this" command.

        Shown when it is off the screen, raised to the front, and kept
        at the size it holds unless `width` and `height` name the pixels
        to put it at (a side left out keeps the size the window holds
        on that side; both named refusals when they are not positive
        integers). "app" for the application, a figure key for one
        figure, a case URI for its shot view. A draw is not a reason to
        call it -- a figure is a window of the session, in the *Windows*
        menu -- and neither is a gesture that moved a figure's content
        (scale_curve, shift_curve, normalize_curve, reset_curve,
        remove_curve, the axes); the caller shows what it wants, when
        it wants it. Called to make a requested picture readable, size
        the window first and take the get_screenshot after. The answer
        is the size the window then holds.
        """
        return _run(partial(core.focus_window, window,
                            width=width, height=height))

    # ------------------------------------------------------------------- log

    @server.tool(name='get_logs')
    def get_logs(uri: Optional[str] = None, tail: int = 200):
        """The log panel of one case, or of every case when `uri` is left
        out: the last `tail` lines the gestures wrote there, the named
        refusals among them -- where an agent reads what a dialog would
        have told it."""
        return _run(partial(core.get_logs, uri, tail=tail))

    # ------------------------------------------------------------- journals

    @server.tool(name='search_journals')
    def search_journals(
            scope: Optional[str] = None,
            query: Optional[str] = None,
            limit: int = 20,
            machine: Optional[str] = None,
            campaign: Optional[str] = None,
            shot: Optional[str] = None,
            date_from: Optional[str] = None,
            date_to: Optional[str] = None,
            author: Optional[str] = None,
    ):
        """The notes that fit the filters you name, ranked for the query
        you ask in: `scope` is `personal` or `shared`, and left out it
        answers both (a journal not on this node is left out of the
        answer, named in it). `query` ranks by words first and by
        meaning when an embeddings endpoint is set -- the method it used
        is in the answer. The filters are `machine` (the tokamak),
        `campaign`, `shot` (the shot number), `date_from` / `date_to`
        (the shot date, `YYYY-MM-DD` range), and `author` (who wrote the
        note). A note may be a general observation that names no shot
        and no machine: a filter it does not carry is left out of the
        answer, and it is a match on the query you ran on the rest of
        its body."""
        return _run(partial(core.search_journals,
                            scope=scope, query=query, limit=limit,
                            machine=machine, campaign=campaign,
                            shot=shot, date_from=date_from, date_to=date_to,
                            author=author))

    @server.tool(name='read_note')
    def read_note(scope: str, note_id: str):
        """The whole note under `scope` (`personal` or `shared`) by its
        `note_id` -- the fields that name it (author, machine, campaign,
        shot, date, title) and the body of the note itself. The `note_id`
        comes from a search_journals or list_notes answer."""
        return _run(partial(core.read_note, scope, note_id))

    @server.tool(name='list_notes')
    def list_notes(
            scope: Optional[str] = None,
            machine: Optional[str] = None,
            campaign: Optional[str] = None,
            shot: Optional[str] = None,
            date_from: Optional[str] = None,
            date_to: Optional[str] = None,
            author: Optional[str] = None,
    ):
        """The notes under `scope` (`personal`, `shared`, or left out and
        both) that fit the filters you name, in date order: the short
        view of each (the fields that name it and a line of its body).
        `date_from` and `date_to` bound the shot date (`YYYY-MM-DD`).
        Where a `search_journals` ranks for a query, this lists for a
        filter -- the query is the ranking, and the filters are here."""
        return _run(partial(core.list_notes, scope=scope, machine=machine,
                            campaign=campaign, shot=shot,
                            date_from=date_from, date_to=date_to,
                            author=author))

    @server.tool(name='journal_stats')
    def journal_stats():
        """What the two journals hold on this node: the personal and shared
        directories, the count of notes each answers, and whether an
        embeddings endpoint is set (and on which model) -- the search on
        this node ranks by words until it is."""
        return _run(partial(core.journal_stats))

    @server.tool(name='add_note')
    def add_note(
            scope: str,
            text: str,
            author: Optional[str] = None,
            machine: Optional[str] = None,
            campaign: Optional[str] = None,
            shot: Optional[str] = None,
            date: Optional[str] = None,
            title: Optional[str] = None,
    ):
        """A line in one of the journals: `scope` is `personal` (the
        author's own notes) or `shared` (the shared cahier that a writer
        sees), the `text` is the body of the note, and the fields that
        name it are `author` (who wrote the note -- the user's name, left
        out for a note by the agent), `machine`, `campaign`, `shot`,
        `date` (all optional: a note may be a general observation that
        names no shot and no machine), and `title`. The `id` and `path`
        the file lands under come back in the answer."""
        return _run(partial(core.add_note, scope, text,
                            author=author, machine=machine,
                            campaign=campaign, shot=shot, date=date,
                            title=title))

    @server.tool(name='delete_note')
    def delete_note(scope: str, note_id: str):
        """Take a line out of one of the journals (the `scope` and
        `note_id` you named in a search_journals or list_notes answer).
        The note is gone, and the answer names the scope and the id that
        was removed -- the same line the agent sees in the transcript,
        not a silent `True`."""
        return _run(partial(core.delete_note, scope, note_id))

    @server.tool(name='reindex_journals')
    def reindex_journals(scope: Optional[str] = None):
        """Put the journal(s) in step with their index: the run asks of
        this when a search comes back `guarded` (the index was written
        under an embeddings endpoint the run is no longer under, its
        vectors are in a different space than the query) or before the
        first search of a journal that has not been indexed. It keeps
        the rows it already has, re-embeds the ones that moved, and drops
        the ones the journal no longer holds. `scope` is `personal` or
        `shared`, and left out it runs on the two; the answer names, per
        journal, how many it kept, wrote, and dropped, and whether the
        run vectorized this pass or kept the text for the keyword."""
        return _run(partial(core.reindex_journals, scope=scope))

    @server.tool(name='list_documents')
    def list_documents():
        """The documents the in-app agent reads for its own RAG over the
        user's own writing: the markdown, text, and PDF files the folder
        AgentDocsDir names holds (the name, the size, the date, and the
        relative path a search answers by). An empty corpus (a folder with
        no document) is an answer; a corpus with no folder named is a
        refusal that names it."""
        return _run(partial(core.list_documents))

    @server.tool(name='read_document')
    def read_document(rel: str):
        """The full text of one document of the corpus, by its relative
        path (the one a search_documents hit names). Not in the corpus is
        a refusal by name, naming the ones it does read. The one to ask
        when a search hit is the one the reader wants to read in full."""
        return _run(partial(core.read_document, rel))

    @server.tool(name='reindex_documents')
    def reindex_documents():
        """Put the documents corpus in step with its index: the run asks of
        this after the user has added a document to the corpus folder, or
        when a search comes back `guarded` (the index was written under an
        embeddings endpoint the run is no longer under, its vectors are in
        a different space than the query). It keeps the rows it already
        has, re-embeds the ones that moved, and drops the ones that left
        the folder; the answer names how many it kept, wrote, and dropped,
        and whether the run vectorized this pass or kept the text for the
        keyword."""
        return _run(partial(core.reindex_documents))

    @server.tool(name='search_documents')
    def search_documents(query: str, limit: Optional[int] = None):
        """The in-app agent's RAG over the documents corpus: the ranked
        chunks of the user's own markdown, text, and PDF files (one hit
        per chunk, the document, the chunk, a snippet). The one to ask
        when the question is about the user's own writing or the corpus
        the AgentDocsDir folder holds. The answer names the method it
        ranked with (hybrid / embeddings / keyword / empty), and when a
        store was written under another embeddings endpoint it is
        `guarded` and the keyword alone stands -- reindex_documents is
        the one that sets them in step."""
        kwargs = {'limit': limit} if limit is not None else {}
        return _run(partial(core.search_documents, query, **kwargs))

    @server.tool(name='documents_stats')
    def documents_stats():
        """The state of the documents corpus: how many documents and
        chunks it holds, the embeddings endpoint and model it was written
        under, and when it was built -- the one to ask when the answer to
        "can the agent read my notes/documents" is "it is not indexed "
        yet" or "it was indexed under another endpoint"."""
        return _run(partial(core.documents_stats))

    return server
