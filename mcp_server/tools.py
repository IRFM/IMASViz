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

The tools are not written here: they are **declared from the table** this
file imports, one entry of `TOOLS` (the list the in-app agent is offered)
becoming one tool of the server -- name, description, parameters, the type
and the note of each, and the actions its discriminant offers. What stays
in this file is what a schema cannot say: `dispatcher`, `INSTRUCTIONS`,
the three answers that are this server's own shape (`LIST_ANSWER`,
`PICTURE_OF`) and the type reading (`JSON_TYPE`).

`dispatcher` is what runs the method on the GUI thread: the SDK answers
tool calls on its worker threads, and those may compute but must not
touch the widgets -- the rule the dispatcher exists for.
"""

import base64
import inspect
from functools import partial
from typing import Annotated, Literal, Optional, Union

from mcp.server.fastmcp import FastMCP
from mcp import types as mcp_types
from pydantic import Field

# The tool vocabulary is one table, not two: the name, the action inside it
# and the parameters that action takes are read from the same declaration
# the in-app agent is offered, so a merged group cannot end up spelled one
# way on the page and another on this endpoint -- and neither can a
# parameter's own sentence, which goes on this wire as the note the table
# carries.
from imasviz.VizAgent.tools import (
    TOOLS,
    argumentsForMember,
    missingParameterRefusal,
    missingParameters,
    resolveCall,
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
   'slices' one profile at several instants -- one trace per instant on
   one figure -- 'selection' what the case holds selected, 'table' one
   panel per quantity, 'stacked' the stacked view. get_screenshot answers a PNG of
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
10. the calls that set the field up are never an ask --
    manage_case(action='open'), manage_idss(action='filled'),
    manage_idss(action='load'), plugin(action='list') -- run one whenever
    the work needs it. A plugin window is: never call plugin(action='run')
    unless the user's own request asks for a plugin or names that plugin;
    loading an IDS never asks for a window.

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

    The tools are **declared from the table**, not written here. One entry
    of ``imasviz.VizAgent.tools.TOOLS`` -- the list the in-app loop is
    offered -- becomes one tool of this server: its name, its description,
    its parameters, the type and the note of each, which of them a call is
    refused without, and the action its discriminant offers. Before T6 this
    file spelled all of that a second time, 1 037 lines of it, and the two
    spellings were kept in step by a guard and by somebody remembering.

    What that buys is on the wire, not only in the line count. A parameter's
    own sentence lives in its schema block on the loop face and had no place
    here, because the signature was written by hand and its prose would have
    been a third wording; ``Annotated[type, Field(description=...)]`` puts
    the loop's own sentence in this face's schema (measured on this node's
    ``mcp`` and ``pydantic`` 2.14.2). A caller over this socket reads what
    ``uri``, ``along`` or ``indices`` means in the same words the panel's
    model reads them.

    What cannot be read off a schema is declared below, in the clear:
    ``LIST_ANSWER`` (the SDK answers a top-level list as one content block
    per element), ``PICTURE_OF`` (one tool answers bytes) and ``JSON_TYPE``
    (the types the table uses). Nothing else is this server's own, and
    test_177 refuses a name, a word or a description this file invents.
    """
    server = FastMCP(name, instructions=INSTRUCTIONS)

    def _run(function):
        """Ask the GUI thread, and hand back what it answers -- value or
        named exception alike."""
        return dispatcher.call(function)

    for tool in TOOLS:
        _declare(server, tool, core, _run)
    return server


# What the generated entry cannot read off the table ------------------------

# The SDK answers a top-level list as one content block per element, so a
# gesture whose whole answer IS a list goes back under the name the in-app
# answer gives it. Keyed by the GESTURE, not by the offered name: a merged
# group answers one name and only one of its actions lists.
LIST_ANSWER = {'list_cases': 'cases',
               'list_idss': 'idss',
               'list_case_idss': 'idss',
               'search_nodes': 'matches'}

# One tool answers bytes, and the SDK's image content is what puts the
# picture in the transcript beside the line saying how big it is. The value
# is the parameter that names what was captured, for the words of that line.
PICTURE_OF = {'get_screenshot': 'window'}

# The types the table spells, and what stands for them in a signature.
# ``array`` stays a bare list: the table types its items nowhere
# (``{'items': {}}``), and inventing an item type here would be this face
# saying something the table does not say.
JSON_TYPE = {'string': str, 'integer': int, 'number': float,
             'boolean': bool, 'object': dict, 'array': list}

# Stands for "a call cannot leave this word out", so that ``None`` can mean
# what a call that leaves a word out answers with. A default of ``None`` is
# a value, so it cannot double as the absence of one.
_REQUIRED = object()


def _annotation(block, toolName, parameter, omittedAt=_REQUIRED):
    """The annotation one schema block stands for.

    The block is the reference, which is the point of the whole pass: a
    parameter that becomes optional, narrower, or takes a new type on the
    loop face is here on this socket the next time the server is built,
    with nothing to remember. A block that spells an ``enum`` becomes a
    ``Literal``, so the values are checked before the GUI thread is asked
    -- and the refusal names them, which is what an enum in a schema is for.

    ``omittedAt`` is what a call that leaves the word out answers with, and
    it makes a word nullable the block does not spell nullable. ``plot``'s
    ``path`` is the case: the block types it ``string`` and the schema does
    not require it, so the signature has to carry a default, and a default
    of ``None`` beside a ``type: string`` is a schema that contradicts
    itself -- pydantic prints exactly that, without a word. The null branch
    is what leaving it out already means, so it goes in the type.

    The block's own sentence comes along as ``Field(description=...)``, so
    the note the panel's model reads is the note the caller over this socket
    reads. It is not written twice: it is read off the same block.
    """
    spelled = block.get('type')
    if spelled is None:
        raise ValueError('the %s tool spells no type for %s: the generator '
                         'takes a type, it does not guess one'
                         % (toolName, parameter))
    names = spelled if isinstance(spelled, list) else [spelled]
    unknown = sorted(name for name in names if name not in JSON_TYPE
                     and name != 'null')
    if unknown:
        raise ValueError('the %s tool spells %s as a type this face has no '
                         'reading for: %s' % (toolName, parameter, unknown))
    choices = block.get('enum')
    if choices is not None:
        values = tuple(value for value in choices if value is not None)
        if not values:
            raise ValueError('the %s tool spells %s as an enum with nothing '
                             'in it: a call could not answer it'
                             % (toolName, parameter))
        base = Literal[values]
        nullable = None in choices or 'null' in names or omittedAt is None
    else:
        known = [JSON_TYPE[name] for name in names if name != 'null']
        base = known[0] if len(known) == 1 else Union[tuple(known)]
        nullable = 'null' in names or omittedAt is None
    annotation = Optional[base] if nullable else base
    note = block.get('description')
    return Annotated[annotation, Field(description=note)] if note \
        else annotation


def _declare(server, tool, core, run):
    """Declare one entry of the table as a tool of this server."""
    function = tool['function']
    name = function['name']
    schema = function['parameters']
    properties = schema.get('properties', {})
    required = set(schema.get('required', ()))

    annotations = {}
    defaults = {}
    for parameter, block in properties.items():
        omitted = parameter not in required
        if omitted:
            # The default the table declares is the default the gesture's
            # Python already answers with -- the two were measured against
            # each other, and a schema that says `occurrence: 0` while the
            # call sends nothing is a schema nobody can trust.
            defaults[parameter] = block.get('default')
        annotations[parameter] = _annotation(
            block, name, parameter,
            defaults[parameter] if omitted else _REQUIRED)

    def call(**arguments):
        """Ask the gesture this entry answers, in the core's own spelling.

        ``resolveCall`` is the loop's own seam, so a call made over this
        socket resolves exactly as one made in the panel: the discriminant
        picks the MEMBER and leaves the arguments, and the parameter checks
        are asked about that member -- a merged schema lists what every
        action takes and requires only its discriminant, so
        ``generate_report(scope="plot")`` without a ``figure_key`` looks
        legal against the schema and is not a call.

        What this face does NOT ask is the destructive and shared-journal
        gate: on the loop face a model decides and a user has to have asked
        for it, and over this socket the ask is the caller's own (test_135
        is that asymmetry's guard).
        """
        given = {field: value for field, value in arguments.items()
                 if value is not None}
        gesture, args = resolveCall(name, given)
        if not hasattr(core, gesture):
            raise ValueError('the tool "%s" is not a gesture of this session'
                             % gesture)
        unknown = unknownParameters(gesture, args)
        if unknown:
            raise ValueError(unknownParameterRefusal(gesture, unknown))
        missing = missingParameters(gesture, args)
        if missing:
            raise ValueError(missingParameterRefusal(gesture, missing))
        spelled = argumentsForMember(gesture, args)
        answer = run(partial(getattr(core, gesture), **spelled))
        if name in PICTURE_OF:
            return [
                mcp_types.TextContent(
                    type='text',
                    text='PNG of %s, %d bytes.'
                         % (given.get(PICTURE_OF[name], ''), len(answer))),
                mcp_types.ImageContent(
                    type='image',
                    data=base64.b64encode(answer).decode('ascii'),
                    mimeType='image/png'),
            ]
        under = LIST_ANSWER.get(gesture)
        return {under: answer} if under is not None else answer

    call.__name__ = call.__qualname__ = name
    call.__doc__ = function['description']
    call.__annotations__ = annotations
    # FastMCP builds its schema by introspection, and a function assembled
    # here has no signature of its own until it is handed one. Keyword-only,
    # because the call is made by name on both faces.
    call.__signature__ = inspect.Signature([
        inspect.Parameter(
            parameter,
            inspect.Parameter.KEYWORD_ONLY,
            default=defaults.get(parameter, inspect.Parameter.empty),
            annotation=annotations[parameter])
        for parameter in properties])
    server.tool(name=name)(call)
