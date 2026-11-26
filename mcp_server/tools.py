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

The words a call is answered with, said once here and not by each tool:
- uri: the case, spelled as manage_case(action='list') named it.
- ids_name: which IDS of that case. occurrence: which version of it. The
  two go together, and manage_idss(action='filled') names both for the
  case.
- path: a leaf of the tree, in any spelling inspect_tree(action='search')
  answered. Which member of an array of structures it is sits IN the path,
  never in indices.
- indices: the 0-based index of a tensor dimension or of a nested array,
  one entry per array of structures; it pins an axis the curve does not
  run along.
- along: the axis a curve runs along. time: one instant -- the value the
  user asked AT, not the value the case holds there.
- figure_key: a window of curves; window: any window on the screen. Both
  spelled as an answer or manage_window(action='list') named them, and a
  window the close box took down keeps its key.
- A group of asks says which one is meant with action, mode, operation or
  scope; a call that leaves it out is refused, never run on a guess.
- A refusal is an answer: report its reason, then answer again in the
  spelling that refusal names.

How to work with it:
1. manage_case(action='open', uri) -- the data dictionary is asked of the
   case when you do not name one;
2. manage_idss(action='filled', uri) tells which IDSs the case actually
   holds and which occurrences; manage_idss(action='declared') adds the
   roots the dictionary declares but the case leaves empty;
3. manage_idss(action='load', uri, ids_name, occurrence) builds the tree
   branch;
4. inspect_tree(action='search', uri, query) names the leaves in every
   spelling the tree holds -- the paths manage_selection(action='select'),
   plot and get_signal take are any of those spellings;
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
6. state is read with manage_selection(action='list') (what the case
   holds selected),
   inspect_tree(action='node') for what one node holds: documentation,
   units, size, the finite minimum and maximum, the nan and inf counts, a
   bounded preview; inspect_tree(action='ids') for what the data
   dictionary says about an IDS: comment, homogeneous_time, units, time
   units, data dictionary version; and inspect_tree(action='quantities')
   for the filled tensors of one occurrence, grouped by array of
   structures -- answers, not guesses, and empty is an answer too;
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
9. two asks that draw one window: a plugin entry and the tool that entry
   answers are the same window -- plugin(action='run') on an
   equilibriumsurfaces entry IS equilibrium(action='surfaces') -- so ask
   one, not both. And a screenshot is a picture you cannot read: say what
   a figure shows from the arrays get_signal answers, never from the PNG.

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
    are asked. They say it in the same words the agent's loop is offered
    (``imasviz.VizAgent.tools``'s ``TOOLS``), under the same prose budget:
    a caller over this socket and a caller in the panel read one account
    of one gesture, and a tool that pays 400 words here while its twin
    there pays 60 is a face nobody keeps in step (test_176 measures both).

    One asymmetry to know before comparing the two faces. On the loop face
    a parameter's own sentence lives in its schema block; on this face the
    signature IS the schema, so what a parameter takes is said by its type
    and the per-parameter prose is not sent -- it is in the comment above
    the entry, and the loop's block is the reference for the wording. It
    can come back on the wire: measured on this node's ``mcp`` 1.30.0 with
    ``pydantic`` 2.14.2, a parameter annotated
    ``Annotated[Optional[str], Field(description=...)]`` is declared with
    that description in the tool's JSON schema.
    """
    server = FastMCP(name, instructions=INSTRUCTIONS)

    def _run(function):
        """Ask the GUI thread, and hand back what it answers -- value or
        named exception alike."""
        return dispatcher.call(function)

    # ------------------------------------------------------------------ cases

    # The words are the loop's, verbatim: a caller over this socket and a
    # caller in the panel are told the same thing about the same gesture,
    # and the same holds for the refusals below. What the sentence no
    # longer has room for is here: a `dd_version` left out asks the case
    # which dictionary its own IDSs were written with, which is what a
    # case stored under another major version needs -- read at the wrong
    # one, every read is refused. "close" is for good: the shot view and
    # the windows that serve this case alone leave the bookkeeping, a
    # window another case reads is hidden and keeps its key.
    # `uri` is Optional because "list" names no case.
    @server.tool(name='manage_case')
    def manage_case(action: Literal['open', 'list', 'close'],
                    uri: Optional[str] = None,
                    dd_version: Optional[str] = None):
        """The cases this session works on, and `action` says which ask.
        "open": one IMAS case by URI; `dd_version` pins the data
        dictionary, left out the case is asked which one its own IDSs
        were written with. "list": the cases open, with their loaded
        occurrences. "close": one open case, its view, its windows and
        its bookkeeping, for good."""
        gesture = gestureOf('manage_case', {'action': action})
        args = {field: value for field, value in (
            ('uri', uri), ('dd_version', dd_version)) if value is not None}
        unknown = unknownParameters(gesture, args)
        if unknown:
            raise ValueError(unknownParameterRefusal(gesture, unknown))
        missing = missingParameters(gesture, args)
        if missing:
            raise ValueError(missingParameterRefusal(gesture, missing))
        spelled = argumentsForMember(gesture, args)
        answer = _run(partial(getattr(core, gesture), **spelled))
        if gesture == 'list_cases':
            # The SDK answers a top-level list as one content block per
            # element; the list is a value under a name, not the answer.
            return {'cases': answer}
        return answer

    # -------------------------------------------------------------------- ids

    # "filled" is read through the entry's own occurrence listing, so its
    # names and counts come off the case; "load" is synchronous, and
    # `slices` decides how much of the dynamic array the walk keeps -- on a
    # big IDS the difference between thousands of signals and hundreds of
    # thousands. An occurrence the case does not hold is refused by the
    # load with its reason. `ids_name`, `occurrence` and `slices` are
    # Optional because the two lists name no IDS.
    @server.tool(name='manage_idss')
    def manage_idss(action: Literal['declared', 'filled', 'load'],
                    uri: str,
                    ids_name: Optional[str] = None,
                    occurrence: Optional[int] = None,
                    slices: Optional[str] = None):
        """The IDSs of a case, and `action` says which ask. "declared":
        every IDS its dictionary declares, the roots that hold no data
        included. "filled": only the IDS the case holds -- the answer to
        "what is in this case", never a recalled one. "load": one
        occurrence of one IDS into the tree, keeping "first" slice or the
        whole dynamic array per `slices`."""
        gesture = gestureOf('manage_idss', {'action': action})
        args = {field: value for field, value in (
            ('uri', uri), ('ids_name', ids_name),
            ('occurrence', occurrence), ('slices', slices))
            if value is not None}
        unknown = unknownParameters(gesture, args)
        if unknown:
            raise ValueError(unknownParameterRefusal(gesture, unknown))
        missing = missingParameters(gesture, args)
        if missing:
            raise ValueError(missingParameterRefusal(gesture, missing))
        spelled = argumentsForMember(gesture, args)
        answer = _run(partial(getattr(core, gesture), **spelled))
        if gesture in ('list_idss', 'list_case_idss'):
            # The SDK answers a top-level list as one content block per
            # element; the list is a value under a name, not the answer.
            return {'idss': answer}
        return answer

    # ------------------------------------------------------- the tree itself

    # One name for the four ways the tree answers a question about itself,
    # the same offer the agent's loop makes (see `FAMILIES`, "the tree").
    # The checks are the loop's, in the loop's order, so a caller over this
    # socket and a caller in the panel hear the same words about the same
    # mistake.
    #
    # What the sentence no longer has room for, and what the answer says
    # anyway: a `query` is matched case-insensitively over the display path,
    # the data name and the parametrized path, and each match comes back
    # under `matches` with those three spellings -- any is what
    # manage_selection(action='select'), `plot` and `get_signal` take --
    # beside the `kind` a plot would make of it. "node" answers what the
    # application's own documentation says of the leaf: units, size, shape,
    # the finite minimum and maximum, the zero/nan/inf counts, a bounded
    # preview, and a leaf the tree does not hold is refused by name. "ids"
    # leaves a property the case leaves empty absent rather than invented.
    # A scalar (0D) leaf is not a tensor and is not listed, and an
    # occurrence whose tree was never built is refused -- load it with
    # manage_idss(action='load') first.
    @server.tool(name='inspect_tree')
    def inspect_tree(
            action: Literal['search', 'node', 'ids', 'quantities'],
            uri: str,
            query: Optional[str] = None,
            ids_name: Optional[str] = None,
            occurrence: Optional[int] = None,
            limit: Optional[int] = None,
            path: Optional[str] = None):
        """What the tree of a case says, and `action` says which ask.
        "search": the leaves whose spelling carries `query`; each match
        answers the spellings a plot takes. "node": what one `path` holds
        -- units, size, min/max, a bounded preview. "ids": what the data
        dictionary says of an `ids_name`. "quantities": the filled tensors
        of one `occurrence`, grouped by the array of structures that drives
        them -- the "what can be drawn" answer."""
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

    # The three asks about the selection, under one name: what is selected,
    # what to put in, and to empty it. `additive` is Optional and not True
    # here because a parameter the action does not take is a refusal, and a
    # default would answer "clear" and "list" with a stray word.
    #
    # "select" takes any spelling a search hit answers and answers the
    # paths it took beside the new size; "list" is the one that spells each
    # leaf -- path, data name, IDS, occurrence -- in the order they were put
    # in. The selection is what `plot(mode="selection")` draws.
    @server.tool(name='manage_selection')
    def manage_selection(action: Literal['select', 'clear', 'list'],
                         uri: str, paths: Optional[list] = None,
                         additive: Optional[bool] = None):
        """What the case selection holds and what to do with it, and
        `action` says which ask. "select": the named `paths` go in -- one
        the tree does not hold is refused by name and nothing goes in.
        "clear": empty it, answering how many were dropped. "list": the
        selection in the order it was put in; empty answers count 0, not a
        refusal."""
        gesture = gestureOf('manage_selection', {'action': action})
        args = {field: value for field, value in (
            ('uri', uri), ('paths', paths), ('additive', additive))
            if value is not None}
        unknown = unknownParameters(gesture, args)
        if unknown:
            raise ValueError(unknownParameterRefusal(gesture, unknown))
        missing = missingParameters(gesture, args)
        if missing:
            raise ValueError(missingParameterRefusal(gesture, missing))
        spelled = argumentsForMember(gesture, args)
        return _run(partial(getattr(core, gesture), **spelled))

    # -------------------------------------------------------------- plotting

    # One name for the five ways a quantity is drawn, the same offer the
    # agent's loop makes (see `FAMILIES`, "the drawing"). The checks are the
    # loop's, in the loop's order -- the action's unknown parameters, then
    # its missing ones -- because a caller over this socket and a caller in
    # the panel must hear the same words about the same mistake, and the
    # parameters are checked in the spelling the caller typed (`path`, not
    # the `leaf` the slice gesture has always taken in Python).
    #
    # What the sentence no longer has room for, and where it is said: the
    # address "single" takes is the one `get_signal` takes -- `along` names
    # the axis the quantity runs along (the clock, or one of its own axes
    # such as `psi`) and `indices` pins each OTHER axis at its 0-based
    # index, one entry per nested array of structures (`time_slice`,
    # `profiles_1d`, `ion`, ...) or the leaf's own coordinate, so the
    # figure a reader sees and the numbers a read reports are one element
    # of one array -- `equilibrium.time_slice[0].profiles_1d.pressure` is
    # held by the dynamic array, so "along the clock at psi index 50" is
    # `along` left out (the clock) and `indices={"psi": 50}`.
    # `time` pins a profile to one slice of its dynamic array
    # (`time_interp=true` for the value between the two that bracket it)
    # and is refused beside `along`/`indices`, being the opposite reading;
    # "slice" goes through the Access Layer's own `DBEntry.get_slice` at
    # `interpolation` `linear` (default), `closest` or `previous`, a time
    # outside the case answering its nearest slice and saying so, and it is
    # neither a 2D-pictorial leaf nor a 0D scalar; "table" lays its panels
    # `columns` wide and "stacked" reads along `plot_axis`;
    # `into_figure_key` adds to an open curve figure instead of opening
    # one. The wording of each of those parameters is the loop's schema
    # block for `plot`.
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
        """What shape to draw in, and `mode` picks it. "single": one `path`
        into the figure its own axes call for -- a curve for one axis to
        draw, a picture window for two. "slice": one `path` read at one
        `time`. "selection": what the case selection holds. "table": one
        panel per `paths` in a Table Plot View. "stacked": `paths` stacked,
        one panel each, in one window. The answer names the figure key and
        `curves`, the curves on it after the call."""
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
    #
    # Two things that are this entry's own: a single number in `times` is
    # read as a list of one, and the window that comes back is an
    # `EquiSurfaces:` key whose PNG get_screenshot answers. And neither read
    # is a leaf of the tree -- it is the read the plugin does on the IDS
    # object, the GGD branch the tree walk does not hold -- so a quantity
    # of it is never a path to search for. What each frame draws and what
    # the answer carries is the loop's comment for `equilibrium`.
    @server.tool(name='equilibrium')
    def equilibrium(action: Literal['surfaces', 'at_time'], uri: str,
                    times: Optional[list] = None,
                    time: Optional[float] = None,
                    occurrence: Optional[int] = None):
        """The equilibrium as the Equilibrium plugin draws it, and `action`
        says which ask. "surfaces": one frame per instant of `times`, side
        by side in one window. "at_time": one `time` with its radial
        profiles under it and the slice global quantities in the answer. An
        instant outside the case answers its nearest slice, named back."""
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

    # The read of one leaf, on the same `along` + `indices` address as
    # `plot(mode='single')`, so what a figure of it draws and what this
    # reports are one element of one array. A word no axis answers, or an
    # index past the extent the tree names, is refused with the reason the
    # application names, not a silent 0.
    @server.tool(name='get_signal')
    def get_signal(uri: str, path: str,
                   as_function_of_time: Optional[bool] = None,
                   coordinate_index: int = 0,
                   time_index: Optional[int] = None,
                   along: Optional[str] = None,
                   indices: Optional[dict] = None):
        """The values the tree read gives for one leaf, as JSON, on the same
        `along` + `indices` schema `plot(mode="single")` uses: the same
        element a figure of that leaf draws. `as_function_of_time` and
        `coordinate_index` are the legacy spelling of that pair."""
        return _run(partial(core.get_signal, uri, path,
                            as_function_of_time=as_function_of_time,
                            coordinate_index=coordinate_index,
                            time_index=time_index,
                            along=along, indices=indices))

    # ------------------------------------ the figures: the data and the axes

    # Scale, shift and normalize are in place and reversible through
    # "reset"; `reference` is `max` (the largest sample, the default),
    # `first` (the sample at index 0) or `mean`, and a reference that is
    # zero or not a number is refused, as the division would otherwise read
    # as a picture full of no-signal. `curve` is a name substring, a 0-based
    # index, or left out for every curve the figure holds. The figure is
    # one a single curve was drawn in -- a table or the flux-surface figure
    # are refused by name, and so is an operation asked without the number
    # it needs or with one that belongs to another.
    @server.tool(name='transform_curve')
    def transform_curve(
            operation: Literal['scale', 'shift', 'normalize', 'reset',
                               'remove'],
            figure_key: str, factor: Optional[float] = None,
            offset: Optional[float] = None,
            reference: Optional[str] = None,
            curve: Optional[Union[str, int]] = None):
        """Do one thing to the curve(s) a figure already holds, and
        `operation` picks it. "scale" times `factor`, "shift" plus `offset`,
        "normalize" divided by a reference of their own (`reference`),
        "reset" back to the data they were drawn with, "remove" off the
        figure. scale, shift and normalize work in place, so read_figure
        answers the transformed value while the leaf in the tree is
        unchanged."""
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

    # A range is two bounds: `xmin` with `xmax` (the abscissa) and/or
    # `ymin` with `ymax` (the ordinate), and a partial ask is refused
    # because a half-range is not a question -- `auto=True` clears the pins
    # and re-fits. A curve figure takes one axis set; a picture window
    # takes the same span on each of its pictures, so the time zoom of a
    # strip whose abscissa is its time is the `x` range, in the seconds its
    # time axis holds. For "image_window", `start` is where the band sits
    # on the axis the pictures are read across and `count` how many pictures
    # it holds; the pictures are re-read in place and a colour scale a hand
    # settled stays put, and the answer carries the axis, its start and
    # count, the extent it holds and the label of each picture shown. For
    # "slice_index", `axis` is the row in the words the band spells it (an
    # array of structures by its name -- `time_slice`, `profiles_2d` -- or
    # the coordinate it holds) and `index` a 0-based whole number within
    # that row's extent; the other rows stay where they are. A log where
    # the values cross zero or below is refused, because the picture hides
    # them -- `transform_curve(operation="shift")` to clear the negatives is
    # the answer; inversion and range are independent. A parameter of
    # another operation is refused by naming the operation that takes it,
    # and a table or a stacked window -- one axis set per panel -- is
    # refused by name.
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
        """Move one thing a window draws to, and `operation` picks it.
        "range" pins the span of its axes (`xmin`/`xmax` and/or
        `ymin`/`ymax`, a pair at a time; `auto=true` clears the pins).
        "image_window" moves (`start`) or resizes (`count`) the band of
        pictures a picture window sits on. "slice_index" poses one slider
        row (`axis`) at `index`. "log" makes an axis log or linear (`x`/`y`),
        refused where the values cross zero. "invert" turns one around."""
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
    #
    # "stats" is the read of a figure's curves where the reader can act on
    # it, before or after a scale/shift/normalize; "export" writes those
    # same values as they stand to `~/.imasviz/exports` under the guard of
    # the configurations -- `format` `csv` (default) or `json`, and a `name`
    # that names a place rather than a file is refused by name. `curve` is a
    # name substring, a 0-based index, or left out for every curve the
    # figure holds; the figure is a single curve figure, a table or the
    # flux-surface figure being refused by name.
    @server.tool(name='read_figure')
    def read_figure(
            action: Literal['stats', 'export'], figure_key: str,
            curve: Optional[Union[str, int]] = None,
            format: Optional[str] = None, name: Optional[str] = None):
        """What the curve(s) a figure holds answer, and `action` says which
        ask. "stats": the sample count, the finite min/max/mean/std, the
        nan/inf counts, the peak with its abscissa. "export": the same
        values in a file under ~/.imasviz/exports. Both read the values as
        they stand: a transform a hand put on the figure is in the
        answer."""
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

    # Six asks about one leaf, and one name for them; what each of the six
    # is, what gates each kind and what a report holds is the loop's comment
    # for `analyze_signal`. Two things this entry adds for a caller over the
    # socket: `uri` and `path` are the case and the leaf of the five reads,
    # "clear_events" working on a figure and not on a case; and `along`,
    # `indices` and -- for the second series of "correlate" -- `indices_b`
    # pick one element out of a family, exactly the way `get_signal` does,
    # so what is detected and what a figure of the same leaf draws are one
    # read. The two reports are self-contained HTML: the events or the peaks
    # in a table, the period of their times, the band when named, and the
    # figure's picture only when a `figure_key` is named. A band named with
    # only one bound is refused by name, and so is a `name` that names a
    # place rather than a report.
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
        """What one leaf's signal says, and `action` says which ask.
        "events": the events of one `kind`, gated by the parameters that
        kind takes. "clear_events": those marks off a curve figure.
        "spectrum": the dominant frequency, the leading `n_peaks` by power,
        the power between `band_low` and `band_high`. "correlate": how far
        `path_b` lags or leads `path`, and at what the two oscillate
        together. "events_report" and "spectrum_report": the same two
        answers as an HTML page in ~/.imasviz/reports. `figure_key` is the
        figure the marks or the picture go on."""
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

    # One name for the three numbers a case is judged on, and the physics of
    # each -- the Greenwald ratio's n_G = (I_pl / A) x 1e20 with `I_pl` in
    # mega-Ampere and `A` in square metre, and the two case numbers read off
    # `global_quantities.beta_normal` and `profiles_1d.pressure` unless
    # `path` names another leaf -- is the loop's comment for
    # `derived_quantity`, which also says why neither of the two is computed
    # here. Nothing is manufactured: a leaf the case lacks is refused by
    # name, and so are three leaves of three different lengths, f_G being a
    # ratio of three read at the same time.
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
        """A number a case is judged on; `quantity` says which.
        "greenwald": f_G = n_e / n_G, over three leaves the caller names
        (`n_e_path`, `ip_path`, `area_path`) -- formula and numbers from the
        case. "beta_normal" and "total_pressure": the case's own numbers,
        off the leaf it keeps them in, never computed here. A leaf the case
        lacks, or three at different lengths, is refused by name."""
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
    #
    # "values" reads the same leaf from each shot the way a figure of it is
    # read, one value per shot -- `at` a named index into that curve, or
    # `which` over it (mean, max, min) -- and answers the per-shot values,
    # the least-squares slope over the shot index, the first-to-last change,
    # min and max with the shots they came from, and the direction. A
    # one-shot campaign, a shot without the leaf, or an all-equal campaign
    # refuses in words. "report" lays that answer out as a page: the per-shot
    # table, the trend, the line the values make.
    @server.tool(name='trend_campaign')
    def trend_campaign(
            action: Literal['values', 'report'], cases: list, path: str,
            at: Optional[Union[int, str]] = None,
            which: Optional[str] = None, along: Optional[str] = None,
            indices: Optional[dict] = None, name: Optional[str] = None):
        """What one leaf does across a series of shots, and `action` picks
        the ask. "values": one value per shot -- `at` an index of its curve
        or `which` over it -- then the slope over the shot index, the
        first-to-last change, min and max. "report": that answer as an HTML
        page under ~/.imasviz/reports."""
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

    # "list" answers every window in the order the menus draw them -- the
    # case views, the figures, the plugin windows, each with its kind, its
    # label, its key and whether it is on screen -- and asks for no window.
    # A hide keeps the key, so the *Windows* menu still names the window
    # (unchecked) and a session writes it hidden; "close" is the menu's
    # Delete line: hide, delete, forget the key.
    #
    # "focus" is shown when off screen and raised when not, at the size it
    # holds; a `width`/`height` side left out keeps the size the window
    # holds on that side, and a side named but not a positive whole number
    # is refused. Left without a `window`, "focus" means the application.
    # The answer is the size the window then holds, which is what a picture
    # ask reads before taking the shot.
    #
    # `window` is "app" for the application, a figure key for one figure, a
    # case URI for its shot view. Showing is the user's command: neither a
    # draw nor a gesture that moved a figure's content (transform_curve,
    # configure_axes) is a reason to call it.
    @server.tool(name='manage_window')
    def manage_window(
            action: Literal['list', 'show', 'hide', 'close', 'focus'],
            window: Optional[str] = None,
            width: Optional[int] = None,
            height: Optional[int] = None):
        """What one window of the session is asked to do, and `action` says
        which. "list": every window -- kind, label, key, on screen or not.
        "show": put a hidden window back on the screen; "hide": take it off
        without deleting it. "close": delete it and forget its key.
        "focus": the user's "show me this" command -- raised to the front,
        resized only when `width` and `height` name the pixels. A draw is
        not an ask to show it."""
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

    # "list" answers the entries in registration order -- the feature
    # number, its label, its description for each. "run" answers with the
    # answers the entry would have asked the user, which is what keeps a
    # modal question off the path of an agent: an entry that asks an instant
    # (`equilibriumsurfaces` entry 1) and is handed none is refused by name,
    # not left to open a dialog.
    #
    # `ids_name`, `plugin` and `entry` are Optional because "list" names no
    # plugin and no entry; a word the asked action does not take is refused
    # by name instead of travelling to the core. The defaults of the run --
    # occurrence 0, the branch resolved from the case -- stay the core's.
    @server.tool(name='plugin')
    def plugin(action: Literal['list', 'run'],
               uri: str,
               ids_name: Optional[str] = None,
               plugin: Optional[str] = None,
               entry: Optional[int] = None,
               occurrence: Optional[int] = None,
               time: Optional[float] = None):
        """The plugins a case offers, and `action` says which ask. "list":
        the entries an IDS root earns, beside the refusals of the plugins
        that case cannot offer. "run": one entry, with `occurrence` and
        `time` handed instead of asked; the same entry asked again draws
        into the window that stands, and `drawn` names what came back."""
        gesture = gestureOf('plugin', {'action': action})
        args = {field: value for field, value in (
            ('uri', uri), ('ids_name', ids_name), ('plugin', plugin),
            ('entry', entry), ('occurrence', occurrence), ('time', time))
            if value is not None}
        unknown = unknownParameters(gesture, args)
        if unknown:
            raise ValueError(unknownParameterRefusal(gesture, unknown))
        missing = missingParameters(gesture, args)
        if missing:
            raise ValueError(missingParameterRefusal(gesture, missing))
        spelled = argumentsForMember(gesture, args)
        return _run(partial(getattr(core, gesture), **spelled))

    # --------------------------------------------------------------- session

    # "save" writes the cases, the loads, the selection, the windows and
    # what a hand styled on them; `name` is a file under the configuration
    # folder, `path` a full file name, and left out both the file is written
    # under a name of its own. "restore" opens the cases again, replays the
    # loads and draws the figures and plugin windows the way the file named
    # them.
    #
    # "new" answers how many windows it closed. It is the *New session* of
    # the application's *File* menu: a client does not decide to clear a run
    # it was not asked to clear, and the sessions the user saved on disk and
    # the reports stay where they are.
    #
    # A `kind` the application does not answer is refused by name. "apply"
    # takes a .lsp as a .pcfg, loading first the IDSs the case would need
    # and does not hold, the way the menu does it. "save_selection" refuses
    # a case with nothing selected; "save_plot_configuration" writes one
    # Table Plot View, its panels and the places they held, and refuses any
    # other window by name.
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
        """The run kept and read back, and `action` says which ask. "save":
        the whole screen as the application writes it. "restore": one of
        those sessions put back, naming the cases that came back. "new": a
        clean session WITHOUT saving -- every case view and figure closed,
        nothing written; the user asks for it out loud. "list_sessions":
        the .vsess files. "list_configurations": the .pcfg and .lsp files,
        `kind` narrowing to one. "apply": one saved configuration put on a
        case, its quantities selected and the IDSs it needs loaded first.
        "save_selection": the case selection as a .lsp.
        "save_plot_configuration": one Table Plot View as a .pcfg."""
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

    # The parameter that names the subject depends on the scope: `figure_key`
    # is the window for "plot", `uri` the case for the other two.
    #
    # A "plot" page stats its traces: the finite minimum and maximum and the
    # nan/inf counts beside the samples; a window that draws no curve it
    # could stat is refused by name. A "case_loaded" page takes the curves
    # in tree order; an IDS not yet loaded is not a curve, so the answer
    # says how many curves it gave and manage_idss(action='declared') names
    # what the case still holds. A "case_ids" page reads the occurrences
    # through DBEntry.list_all_occurrences rather than listing them from
    # memory, and gives each loaded occurrence a header of its `ids_properties`
    # values plus its available signals -- kept to the ones the tree carries
    # as available, the same test its own colouring applies, a 0-D scalar
    # held by the dynamic array among them. A property the case leaves empty
    # is named empty, an occurrence without an available signal is named as
    # such, and a case that holds no data at all is refused by name; `name`
    # naming a place rather than a report is refused at the disk.
    @server.tool(name='generate_report')
    def generate_report(scope: Literal['plot', 'case_loaded', 'case_ids'],
                        figure_key: Optional[str] = None,
                        uri: Optional[str] = None,
                        name: Optional[str] = None):
        """A self-contained HTML page in ~/.imasviz/reports; `scope` says
        which. "plot": one window of curves -- its image and one row per
        trace it drew, saying the quantity, the samples and the counts.
        "case_loaded": one row per curve the loaded tree of a case holds.
        "case_ids": every IDS the case's dictionary holds, the occurrences
        each holds, and which the session loaded."""
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

    # `window` is "app" for the application, a figure key for one figure, a
    # case URI for its shot view. The picture goes back as image content
    # beside the text line saying how many bytes it is.
    @server.tool(name='get_screenshot')
    def get_screenshot(window: str = 'app'):
        """The explicit picture ask: a window as it stands, in PNG. The
        picture is the size the window holds, so size it first with
        manage_window(action="focus") when the picture has to be readable."""
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

    # The place an agent reads what a dialog would have told it: a refusal a
    # gesture raised is a line of this log, named, on the case that raised it.
    @server.tool(name='get_logs')
    def get_logs(uri: Optional[str] = None, tail: int = 200):
        """The log panel of one case, or of every case when `uri` is left
        out: the last `tail` lines the gestures wrote there, the named
        refusals among them."""
        return _run(partial(core.get_logs, uri, tail=tail))

    # ------------------------------------------------------------- journals

    # The two journals are the author's own notebook and the cahier the
    # writers share; `scope` says WHICH one, not which ask, and left out the
    # ask goes to both -- a journal not on this node is left out of the
    # answer, named in it.
    #
    # "search" ranks by words first and by meaning when an embeddings
    # endpoint is set; "list" is the same filters without a query, in date
    # order, each note in its short view (the fields that name it and a line
    # of its body). "read" answers the whole note -- author, machine,
    # campaign, shot, date, title and its body -- the id coming from a
    # "search" or "list" answer; "delete" names in its answer the scope and
    # the id it removed. "stats" answers the two directories, the count of
    # notes each answers, and whether an embeddings endpoint is set (and on
    # which model): a search on this node ranks by words until it is.
    # "reindex" is the ask of a search that came back `guarded` (an index
    # written under an endpoint this run is no longer under) or of a journal
    # never indexed; it keeps the rows it has, re-embeds the ones that
    # moved, drops the ones the journal no longer holds, and answers per
    # journal how many of each.
    #
    # "add" takes `text` as the body and the naming fields as optional --
    # `author` (left out for a note by the agent), `machine`, `campaign`,
    # `shot`, `date`, `title`: a note may be a general observation naming no
    # shot and no machine. The `id` and `path` the file lands under come back
    # in the answer. `date_from` / `date_to` bound the shot date
    # (`YYYY-MM-DD`) on "search" and "list"; `date` is one note's date on
    # "add". A note may carry no filter: a filter it does not carry leaves it
    # out of the answer, not out of the query run on its body.
    #
    # "edit" is deliberately not on this face -- it is the page's Edit button
    # that asks that gesture, so a note keeps the id the other writers read
    # it under. The table knows the action; this Literal offers seven.
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
        """The lab notebook of the two journals, and `action` says which
        ask. "search": the filters narrow to the notes that name them,
        `query` ranks them, and the answer names the `method` it ranked by.
        "list": the same filters without a query, newest first. "read": one
        `note_id` whole. "add": one new note, `text` required. "delete": one
        note, gone. "stats": what the two journals are on this node, and the
        endpoint a search ranks with. "reindex": the journals in step with
        their index. A `note_id` a journal lacks is refused by name."""
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

    # The personal catalogue is under ~/.imasviz/prompts and the shared one
    # under the folder SharedPromptsDir names; an unnamed shared folder costs
    # its own half of the list, named in `catalogues_unavailable`. `scope` is
    # WHICH catalogue -- `personal`, or `shared`, which the user has to ask
    # for in their own words -- and left out the ask goes to both.
    #
    # "list" answers id, name, category, a one-line description and the holes
    # each opens; `categories` answers how many prompts each category holds.
    # It is the ask when the user says "relance le prompt ..." and the
    # wording they filed is not known. "detail" answers the body with its
    # holes open and what each hole would be answered from right now, and
    # remembers nothing. "fill" fills a hole from the first source that
    # answers it -- what is named in `values`, what was typed last time, what
    # this session knows, what the file declares -- and takes the `text` it
    # answers back: filling is not running, so the caller asks that text as
    # the user asked it. "save" reads `variables` off the text when left out;
    # "edit" keeps the id the remembered values were written under and a
    # field left out keeps the value it held -- a NEW prompt is "save".
    # "delete" takes a prompt and its remembered values off the disk.
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
        """The prompts the user filed to ask again; `action` picks which.
        "list": the prompts with their ids and the holes each opens;
        `category` and `query` narrow it. "detail": one prompt whole, with
        `values`: what each hole would take now. "fill": the filled prompt,
        and nothing run; a hole no source answers is refused naming it.
        "save": a new prompt, `text` with its holes spelled {name}. "edit":
        one prompt changed in place, keeping its id. "delete": one prompt
        out of the catalogue. `scope` is WHICH catalogue, not which ask."""
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

    # The corpus is the markdown, text and PDF files of the AgentDocsDir
    # folder. An empty corpus -- a folder with no document -- is an answer;
    # a corpus with no folder named is a refusal that names it.
    #
    # "list" gives the name, the size, the date and the `rel` a search
    # answers by. "search" is one hit per chunk -- the document `rel`, the
    # chunk, a snippet -- and is the ask when the question is about the
    # user's own writing; the answer names the method it ranked with (hybrid
    # / embeddings / keyword / empty), a `guarded` store having its vectors
    # in a different space than the query, so the keyword alone ranks. "read"
    # is the ask when a hit is worth reading entire: not in the corpus is a
    # refusal by name, naming the ones it does read. "reindex" is the ask
    # after a document was added to the folder or when a search comes back
    # `guarded`; it keeps what it has, re-embeds what moved, drops what left
    # the folder, and answers how many documents and chunks it kept, wrote
    # and dropped. "stats" names the endpoint and model the store was written
    # under and when it was built -- the answer when "can the agent read my
    # documents" is "it is not indexed yet".
    @server.tool(name='manage_documents')
    def manage_documents(
            action: Literal['list', 'search', 'read', 'reindex', 'stats'],
            query: Optional[str] = None,
            limit: Optional[int] = None,
            rel: Optional[str] = None):
        """The corpus the agent reads for its own RAG, in the AgentDocsDir
        folder; `action` says which ask. "list": the corpus as named, with
        the `rel` a search answers by. "search": the ranked chunks, naming
        the `method` it ranked with. "read": one document whole, by its
        `rel`. "reindex": the corpus in step with its store. "stats": how
        many documents and chunks, under which endpoint. A store under
        another embedding endpoint answers `guarded` and ranks by keyword
        alone."""
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
