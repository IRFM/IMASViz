# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The system instructions and the tool schemas for the in-app agent.

One source of truth: the docstrings of the tools in ``mcp_server/tools.py``
are the same text that the MCP surface reads; the schemas here are the
JSON the OpenAI-compatible client sends. The in-app agent and the MCP
surface share the same instructions so the LLM behaves the same way
regardless of which driver calls it.
"""

SYSTEM_INSTRUCTIONS = """You are the IMASViz assistant for ITER/CEA plasma-fusion data analysis.
You control the GUI strictly through the provided tools.

### MANDATORY WORKFLOW
1. `manage_case(action="open", uri)` -> Open the shot.
2. `list_case_idss(uri)` -> Check which IDSs and occurrences actually exist in the case.
3. `load_ids(uri, ids_name, occurrence)` -> Load the required IDS into the tree.
4. `inspect_tree(action="search")` or `inspect_tree(action="quantities")` -> Find exact leaf paths.
5. `plot(mode=...)` or `get_signal(...)` -> Draw curves or read numerical values.
   `mode` is the shape of the drawing: "single" one quantity, "slice" one
   profile at one instant, "selection" what was selected, "table" one panel
   per path, "stacked" the paths stacked in one window.

### STRICT RULES (NEVER VIOLATE)
- **NO HALLUCINATION:** Never invent IDS names, paths, numbers, figure keys, or file paths. Only state facts returned by a tool in this session.
- **NO FAKE ACTIONS:** Never say you plotted a curve, wrote a report, or saved a note unless the corresponding tool returned `error: null` in this turn. If a tool fails or refuses, report the exact refusal reason.
- **OCCURRENCE vs INDICES vs PATH:**
  - `occurrence`: Version of an IDS (passed to `load_ids`).
  - `indices`: 0-based index of a tensor dimension or nested array (e.g., `indices={"psi": 50}`).
  - `path`: Specific member of a structure array (e.g., `magnetics.flux_loop[2].flux.data`). To plot two members together, call `plot(mode="single")` twice using `into_figure_key` on the second call—never put `flux_loop` in `indices`.
- **MULTIPLE FAMILIES:** When asked to plot two different families (e.g., probes then flux loops), create two separate figures unless the user explicitly asks to overlay them ("sur la même figure" / "on the same figure").
- **WINDOWS & FOCUS:** Do NOT call `manage_window(action="focus")` or `manage_window(action="show")` automatically after plotting. Only call them if the user explicitly asks to bring a window to the front.
- **DESTRUCTIVE & SHARED ACTIONS:** Never call `manage_window(action="close")`, `manage_case(action="close")`, `manage_session(action="new")`, or write with `scope="shared"` (`manage_note`, the prompt tools) unless the user explicitly asks for it in their prompt.
- **AMBIGUITY:** If a user request is ambiguous (e.g., "sonde 2" when multiple probes exist), list the exact paths found by `inspect_tree(action="search")` and ask the user to choose.

### RESPONSE FORMAT
- Keep answers concise, factual, and grounded in tool outputs.
- Use `code` formatting for IMAS paths and figure keys (e.g., `Plot1`).
- Use LaTeX (`$...$` or `$$...$$`) for physics symbols and equations.
"""


# The one line the loop sends when the tools are switched off (`AgentToolsMode`
# is `off`): the model is offered no gesture at all, so the answer is a
# plain text shape and there is nothing it may be grounded on from the case.
# What it must not do is named, and is the whole of it: it has no case to
# read from this shape, no figure to point at and no count to recite, and the
# one it does not do is answer as if it had -- a "the case holds N IDS" it
# read from nowhere, or a value it never read. It says it may not, and hands
# the user the shape that would answer it, the tool that reads it. Everything
# the rest of ``SYSTEM_INSTRUCTIONS`` does here is a pointer to a gesture
# this shape does not run, so it is left out on purpose.
CHAT_INSTRUCTIONS = """IMASViz, the ITER/CEA visualization front-end for IMAS plasma-fusion
cases. You answer in plain words with a little markup the reader's panel
can render -- **bold** the idea, *italic* a node or unit name, `code`
around the paths, `$...$` a symbol, and a line of its own `$$...$$` a
formula.

In this shape you have no tools and no case is open for you to read: you
cannot open one, cannot list its IDSs, cannot load a quantity, cannot draw
a figure and cannot read back a value. So you do not say that you did. You
do not name a count of IDSs or occurrences you could have read from no
entry, a curve you could have drawn, an axis or an index you could have
pinned: none of it is grounded in this conversation, and an answer that
names any of it is an answer that is wrong.

What you do: say in direct words what you can answer from what you know
about plasma fusion and IMAS in general, and say out loud where an answer
needs the case, naming the gesture that would read it from the case --
``list_case_idss``, ``plot``, ``get_signal`` -- and inviting the user
to switch the agent back to a shape where it runs, the tools back on.
The user asks a question, you answer it in the shape you can answer in."""


def _tool(name, description, parameters):
    """One OpenAI-format tool schema."""
    return {
        'type': 'function',
        'function': {
            'name': name,
            'description': description,
            'parameters': parameters,
        },
    }


TOOLS = [
    # The three asks about the cases of the session. They share one thing
    # -- the case, named by its URI -- and "list" names none, so the group
    # requires only its discriminant and the rows of `ACTION_PARAMETERS`
    # say that "open" and "close" are nothing without the URI they mean.
    # The guard is asked about the gesture `close_case`, never about this
    # name: `manage_case(action="close")` is a call, not a permission.
    _tool(
        'manage_case',
        'The cases this session works on, and `action` says which ask. '
        '"open": open one IMAS case by URI (imas:hdf5?path=..., or an UDA '
        'URI) -- `dd_version` pins the data dictionary the case is read at, '
        'and left out the case is asked which one its own IDSs were '
        'written with. "list": the cases open, with their loaded '
        'occurrences. "close": one open case, its view, its windows and '
        'its bookkeeping, for good.',
        {'type': 'object', 'properties': {
            'action': {'type': 'string', 'enum': ['open', 'list',
                                                  'close']},
            'uri': {'type': ['string', 'null'],
                    'description': '"open" and "close": the case URI, e.g. '
                                   'imas:hdf5?path=...'},
            'dd_version': {'type': ['string', 'null'],
                           'description': '"open": data dictionary version '
                                          'pin'},
        }, 'required': ['action'], 'additionalProperties': False},
    ),
    _tool(
        'list_idss',
        'Every IDS the case\'s data dictionary declares, and the occurrences '
        'each one holds -- including the roots that hold no data (an empty '
        'occurrence list). Asked of the case itself, never listed from a '
        'file. For the short list of the IDS the case actually holds, use '
        'list_case_idss instead.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
        }, 'required': ['uri'], 'additionalProperties': False},
    ),
    _tool(
        'list_case_idss',
        'Only the IDS the case actually holds, and the occurrences each one '
        'names -- the roots the dictionary declares but the case does not '
        'fill are left out. Asked of the case through '
        'DBEntry.list_all_occurrences, so the names and counts are the case\'s '
        'own. This is the list to answer "what is in this case" with; '
        'recalling IDS names from memory is not. Do not summarise or rename '
        'the answer, and do not present an IDS list you did not read from '
        'this call.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
        }, 'required': ['uri'], 'additionalProperties': False},
    ),
    _tool(
        'load_ids',
        'Load one occurrence of one IDS into the tree, synchronously. '
        '`slices` is "first" for the slice a plain load keeps, "all" for '
        'the whole dynamic array.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'ids_name': {'type': 'string'},
            'occurrence': {'type': 'integer', 'default': 0},
            'slices': {'type': 'string', 'enum': ['first', 'all'],
                       'default': 'first'},
        }, 'required': ['uri', 'ids_name'], 'additionalProperties': False},
    ),
    # One name for the four ways the tree answers a question about itself:
    # which leaves the case holds, what one of them holds, what the data
    # dictionary says about an IDS, and what one occurrence can be drawn as.
    # The discriminant is `action`: no member of the group takes a word of
    # its own (test_175 refuses a discriminant a member already answers for
    # itself). `uri` is required of the offer because the four ask a case;
    # `path` and `ids_name` are not common, so each member names the one it
    # cannot do without, and the refusal of that member asks for it.
    _tool(
        'inspect_tree',
        'What the tree of a case says about itself, and `action` says which '
        'ask. "search": the leaves whose spelling carries `query` '
        '(case-insensitive), `ids_name` narrowing to one IDS; each match '
        'carries its three spellings -- any is what a plot takes -- and the '
        '`kind` a plot would make of it, `curve`, `image` or `scalar`. '
        '"node": what one `path` holds, as the application documentation '
        'says it -- units, size, finite minimum and maximum, the zero/nan/'
        'inf counts, a bounded preview; a leaf the tree does not hold is '
        'refused by name. "ids": what the data dictionary says of an '
        '`ids_name` -- its comment, homogeneous time, units, the version '
        'the case was written at; a property the case leaves empty is '
        'absent, not invented, and an IDS the case does not declare is '
        'refused naming the ones it does. "quantities": the filled tensors '
        'of one `occurrence`, grouped by the array of structures that '
        'drives them -- the "what can be drawn" answer. A scalar (0D) leaf '
        'is not a tensor and is not listed; an occurrence whose tree was '
        'never built is refused by name, load it with load_ids first.',
        {'type': 'object', 'properties': {
            'action': {'type': 'string',
                       'enum': ['search', 'node', 'ids', 'quantities']},
            'uri': {'type': 'string',
                    'description': 'the case whose tree is asked'},
            'query': {'type': ['string', 'null'],
                      'description': '"search": the substring a leaf '
                                     'spelling must carry; empty answers '
                                     'every leaf up to the limit'},
            'ids_name': {'type': ['string', 'null'],
                         'description': '"search": narrow to one IDS; '
                                        '"ids" and "quantities": the IDS to '
                                        'read, and it is asked of them'},
            'occurrence': {'type': ['integer', 'null'],
                           'description': '"ids" and "quantities": which '
                                          'occurrence; 0 when left out'},
            'limit': {'type': ['integer', 'null'],
                      'description': '"search": how many matches come back; '
                                     '200 when left out'},
            'path': {'type': ['string', 'null'],
                     'description': '"node": the leaf, spelled as a search '
                                    'hit names it'},
        }, 'required': ['action', 'uri'], 'additionalProperties': False},
    ),
    # The three asks about one object: what the case has selected. They
    # answer the same case and two of them take nothing but it, so the
    # question a turn answers is « what do I do with the selection », not
    # « which of these three functions ». What each action takes is written
    # per action (`ACTION_PARAMETERS`): the group schema cannot require
    # `paths` of "select" alone and refuse it of the other two.
    _tool(
        'manage_selection',
        'What the case selection holds and what to do with it, and '
        '`action` says which ask. "select": put the named `paths` in, as '
        'the tree clicks would -- one the tree does not hold is refused by '
        'name and nothing is put in. "clear": empty it, answering how many '
        'were dropped. "list": the selection in the order it was put in -- '
        'path, data name, IDS and occurrence of each; empty is an answer, '
        'count 0, not a refusal.',
        {'type': 'object', 'properties': {
            'action': {'type': 'string', 'enum': ['select', 'clear',
                                                  'list']},
            'uri': {'type': 'string'},
            'paths': {'type': 'array', 'items': {},
                      'description': '"select": the leaves, in any '
                                     'spelling a search hit answers'},
            'additive': {'type': 'boolean', 'default': True,
                         'description': '"select": false empties the '
                                        'selection before the paths go in'},
        }, 'required': ['action', 'uri'], 'additionalProperties': False},
    ),
    # One name for the five ways a quantity is drawn, because the question
    # the model is answering is « under what shape do I draw this », not
    # « which of these five functions is it ». `mode` answers it, and the
    # parameters each mode takes are checked per action
    # (`ACTION_PARAMETERS`): a `plot(mode="slice")` without a `time` is
    # refused by naming the missing parameter, never as a Python error.
    # The prose of the old five schemas is not recopied here five times --
    # what is per mode is written on the parameter that carries it.
    _tool(
        'plot',
        'Draw, in the shape the ask calls for: `mode` picks it. '
        '"single" draws one `path` into the figure its own axes call for '
        '-- a curve figure for one axis to draw, a picture window for two. '
        '"slice" draws one `path` at one `time`, the value the Access Layer '
        'answers at that instant. "selection" draws what the case '
        'selection holds (`manage_selection(action="select")` first). '
        '"table" lays one panel per `paths` in a Table Plot View. '
        '"stacked" stacks `paths`, one panel per quantity, in one window. '
        'The answer carries the figure '
        'key and `curves`, the exact list of the curves the figure holds '
        'after the call: a claim that a curve is on that figure stands on '
        'that list, not on memory of the call.',
        {'type': 'object', 'properties': {
            'mode': {'type': 'string',
                     'enum': ['single', 'slice', 'selection', 'table',
                              'stacked'],
                     'description': 'the shape to draw: "single" one '
                                    'quantity, "slice" one profile at one '
                                    'instant, "selection" the case '
                                    'selection, "table" one panel per '
                                    'path, "stacked" the paths stacked in '
                                    'one window'},
            'uri': {'type': 'string'},
            'path': {'type': 'string',
                     'description': '"single" and "slice": the leaf to '
                                    'draw, by its full data path, e.g. '
                                    'core_profiles.profiles_1d[0].electrons'
                                    '.temperature'},
            'paths': {'type': 'array', 'items': {},
                      'description': '"table" and "stacked": one panel per '
                                     'path'},
            'along_time': {'type': ['boolean', 'null'],
                           'description': 'legacy ("single"): one axis to '
                                          'draw. Prefer `along` + '
                                          '`indices`.'},
            'along': {'type': ['string', 'null'],
                      'description': '"single": the axis the quantity runs '
                                     'along: "time"/"temps"/"t" for the '
                                     'clock, or the name of one of its own '
                                     'axes (e.g. "psi"). None for the '
                                     'default (the clock when it holds '
                                     'one).'},
            'indices': {'type': ['object', 'null'],
                        'description': '"single": one entry per axis the '
                                       'figure does not draw, by that '
                                       'axis\'s name, at its 0-based index. '
                                       'An array of structures (time_slice, '
                                       'profiles_1d, ion, ...), or the '
                                       'leaf\'s own coordinate (psi, ...); '
                                       'each of several nested arrays on '
                                       'its own. e.g. {"psi": 50} for a '
                                       'profile held by the dynamic array, '
                                       '"ion": 4 for one structure in it.',
                        'additionalProperties': {'type': 'integer'}},
            'into_figure_key': {
                'type': ['string', 'null'],
                'description': 'The key of an existing figure to add this '
                               'quantity to (superposition). Use when the '
                               'user says "sur la même figure", "superposées", '
                               'or "on the same figure". Leave null to open a '
                               'NEW figure -- which is the default when the '
                               'user names different families in sequence '
                               '(e.g. "2 sondes, puis 2 boucles" is two '
                               'figures, not four in one).'},
            'time': {'type': ['number', 'null'],
                     'description': 'seconds. "single": pins the profile to '
                                    'one slice of its dynamic time array, '
                                    'the nearest by default (the answer '
                                    'names the index and that slice\'s own '
                                    'time, not the value asked at), or the '
                                    'linear interpolation between the two '
                                    'slices that bracket it with '
                                    'time_interp=true. Refused together '
                                    'with `along_time` / `along` / '
                                    '`indices` -- two opposite readings. '
                                    '"slice": required, the instant the '
                                    'profile is read at; a time outside '
                                    'the case\'s range answers the nearest '
                                    'slice the case holds, and the answer '
                                    'names time_requested and '
                                    'time_slice_time apart.'},
            'time_interp': {'type': ['boolean', 'null'],
                            'description': '"single": when true, '
                                           'interpolates linearly between '
                                           'the two slices that bracket the '
                                           'requested time, leaving the '
                                           'answer\'s time_slice_time equal '
                                           'to the exact value asked at, '
                                           'not the nearest slice. Defaults '
                                           'to false (nearest slice).'},
            'occurrence': {'type': 'integer', 'default': 0,
                           'description': '"slice": which occurrence of '
                                          'that IDS holds the leaf'},
            'interpolation': {'type': 'string',
                              'enum': ['linear', 'closest', 'previous'],
                              'default': 'linear',
                              'description': '"slice": how the instant is '
                                             'read -- the case\'s nearest '
                                             'slice, or the one at or '
                                             'before `time`'},
            'columns': {'type': ['integer', 'null'],
                        'description': '"table": the width of the row of '
                                       'panels'},
            'plot_axis': {'type': ['string', 'null'],
                          'description': '"table" and "stacked": the '
                                         'abscissa every quantity is read '
                                         'along, "TIME" the clock'},
        }, 'required': ['mode', 'uri'], 'additionalProperties': False},
    ),
    # One name for the two reads of the equilibrium the plugin offers: the
    # surfaces of the instants the caller names, and one instant with its
    # radial profiles under it. Both take the same `uri` and `occurrence`;
    # one takes a list of instants, the other a single one, and the group
    # schema cannot tell them apart -- the rows of the two actions can.
    _tool(
        'equilibrium',
        'The equilibrium as the Equilibrium plugin reads it, and `action` '
        'says which ask. "surfaces": one frame per named instant, side by '
        'side in one window -- the psi levels, the plasma boundary, the '
        'magnetic axis, the O-point, the limiter, at equal bounds; `times` '
        'is the list of instants in seconds, e.g. [40, 44, 48], each '
        'answering the nearest slice the case holds, named back '
        '(time_requested vs time_slice_time). "at_time": one instant with '
        'the radial profiles under it (q, elongation, triangularities, '
        'j_tor [MA/m^2], pressure [kPa], f_df_dpsi, dpressure_dpsi, on '
        'rho_tor_norm) and the slice\'s global quantities in the answer '
        '(Ip [kA], q95, q_axis, li_3, W_mhd [kJ], axis position). Both '
        'open a window of their own, and the `equilibriumsurfaces` plugin '
        'entries answer these same two asks -- ask one, not both.',
        {'type': 'object', 'properties': {
            'action': {'type': 'string', 'enum': ['surfaces', 'at_time']},
            'uri': {'type': 'string'},
            'times': {'type': ['array', 'null'],
                      'items': {'type': 'number'},
                      'description': '"surfaces": the instants in the case '
                                     'clock, seconds'},
            'time': {'type': ['number', 'null'],
                     'description': '"at_time": the instant in seconds'},
            'occurrence': {'type': 'integer', 'default': 0},
        }, 'required': ['action', 'uri'], 'additionalProperties': False},
    ),
    _tool(
        'get_signal',
        'The values the tree read gives for one leaf, as JSON. '
        '`along` names the axis it runs along (the clock, or one of its own '
        'axes); `indices` pins each OTHER axis at its index -- the same '
        'schema `plot(mode="single")` uses, so what the figures show and '
        'what this answers are the same element. Legacy '
        '`as_function_of_time` true reads along the clock, false along its '
        'own axis; `coordinate_index` '
        'pins one of the leaf\'s axes by position.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'path': {'type': 'string'},
            'as_function_of_time': {'type': ['boolean', 'null'],
                                    'description': 'legacy: one axis. '
                                                   'Prefer `along` + '
                                                   '`indices`.'},
            'along': {'type': ['string', 'null'],
                      'description': 'the axis the quantity runs along: '
                                     '"time"/"temps"/"t" for the clock, or '
                                     'the name of one of its own axes '
                                     '(e.g. "psi"). None for the default '
                                     '(the clock when it holds one).'},
            'indices': {'type': ['object', 'null'],
                        'description': 'one entry per axis the read does not '
                                       'draw, by that axis\'s name, at its '
                                       '0-based index. An array of '
                                       'structures (time_slice, profiles_1d, '
                                       'ion, ...), or the leaf\'s own '
                                       'coordinate (psi, ...); each of '
                                       'several nested arrays on its own. '
                                       'e.g. {"psi": 50}; "ion": 4 for one '
                                       'structure in it.',
                        'additionalProperties': {'type': 'integer'}},
            'coordinate_index': {'type': 'integer', 'default': 0,
                                 'description': 'legacy: pin one axis of the '
                                                'leaf by position. Prefer '
                                                '`indices`.'},
            'time_index': {'type': ['integer', 'null']},
        }, 'required': ['uri', 'path'], 'additionalProperties': False},
    ),

    # the figures: work on the data the figure holds, and the axes it draws to
    # One name for the five things done to a curve a figure already holds,
    # because what the model is answering is « what do I do to that curve »,
    # not « which of these five functions is it ». `operation` answers it,
    # and what each one takes is checked per action: a `factor` put on a
    # "reset" is refused by naming the parameter and the operation that
    # takes it, never as a Python error.
    _tool(
        'transform_curve',
        'Do one thing to the curve(s) a figure already holds: `operation` '
        'picks it. "scale" multiplies their values by `factor`, "shift" '
        'adds `offset`, "normalize" divides them by a reference of their '
        'own (`reference`: the largest sample, the first one, or the '
        'mean), "reset" puts them back to the data they were drawn with, '
        '"remove" takes the curve off the figure. scale, shift and '
        'normalize work in place, and "reset" answers what a hand put on '
        'was and takes it off; "remove" leaves the figure with one curve '
        'less. `curve` is a name substring, a 0-based index, or left '
        'out for every curve. read_figure then answers the transformed '
        'value; the quantity in the tree is unchanged. A table '
        'or a stacked window is not one figure and is refused by name.',
        {'type': 'object', 'properties': {
            'figure_key': {'type': 'string'},
            'operation': {
                'type': 'string',
                'enum': ['scale', 'shift', 'normalize', 'reset', 'remove'],
                'description': 'what to do to the curve: "scale" times a '
                               'constant, "shift" plus a constant, '
                               '"normalize" divided by its own reference, '
                               '"reset" back as drawn, "remove" off the '
                               'figure'},
            'factor': {'type': ['number', 'null'],
                       'description': '"scale": the constant, a finite '
                                      'number'},
            'offset': {'type': ['number', 'null'],
                       'description': '"shift": the constant to add, a '
                                      'finite number'},
            'reference': {'type': ['string', 'null'],
                          'enum': ['max', 'first', 'mean'],
                          'default': 'max',
                          'description': '"normalize": which reference of '
                                         'the curve it is divided by; a '
                                         'reference that is zero or not a '
                                         'number is refused by name'},
            'curve': {'type': ['string', 'integer', 'null'],
                      'description': 'a name substring, a 0-based index, '
                                     'or null for every curve'},
        }, 'required': ['figure_key', 'operation'],
           'additionalProperties': False},
    ),
    # One name for the five things moved on a window, because the ask is
    # « what of this window do I move »: its span, the band of pictures it
    # sits on, one row of its sliders, one of its axes on a log scale, one
    # of them turned around. `operation` answers which, and what each one
    # takes is still checked per action -- an `index` put on "log" is
    # refused by naming the operation that takes it.
    _tool(
        'configure_axes',
        'Move one thing a window draws to: `operation` picks it. "range" '
        'pins the span of its axes (`xmin`/`xmax` and/or `ymin`/`ymax`, a '
        'pair at a time -- a range is two bounds; `auto=true` clears the '
        'pins and re-fits). "image_window" moves (`start`) or resizes '
        '(`count`) the window a picture window sits on, its pictures '
        're-read in place and the colour scale a hand settled left where '
        'it is. "slice_index" poses one row of a slider band at `index`, '
        'the row named as the band spells it (`axis`). "log" makes an axis '
        'log (`x`/`y` true) or linear (false), refused where the values '
        'cross zero. "invert" turns one around. A parameter of another '
        'operation is refused by naming the one that takes it, and a table '
        'or a stacked window is refused by name.',
        {'type': 'object', 'properties': {
            'figure_key': {'type': 'string'},
            'operation': {
                'type': 'string',
                'enum': ['range', 'image_window', 'slice_index', 'log',
                         'invert'],
                'description': 'what is moved: the span of the axes, the '
                               'band of pictures, one slider row, a log '
                               'axis, an axis turned around'},
            'xmin': {'type': ['number', 'null'],
                     'description': '"range": the low bound of the '
                                    'abscissa, with `xmax`'},
            'xmax': {'type': ['number', 'null'],
                     'description': '"range": the high bound of the '
                                    'abscissa, with `xmin`'},
            'ymin': {'type': ['number', 'null'],
                     'description': '"range": the low bound of the '
                                    'ordinate, with `ymax`'},
            'ymax': {'type': ['number', 'null'],
                     'description': '"range": the high bound of the '
                                    'ordinate, with `ymin`'},
            'auto': {'type': ['boolean', 'null'],
                     'default': False,
                     'description': '"range": true clears the pins and '
                                    're-fits the window to what it holds'},
            'start': {'type': ['integer', 'null'],
                      'description': '"image_window": where the window '
                                     'sits on the axis it reads across '
                                     '(0-based element)'},
            'count': {'type': ['integer', 'null'],
                      'description': '"image_window": how many pictures '
                                     'the window holds (1 up to the '
                                     'extent of the axis)'},
            'axis': {'type': ['string', 'null'],
                     'description': '"slice_index": the row, in the words '
                                    'the band spells it -- an array of '
                                    'structures by its name (`time_slice`, '
                                    '`profiles_2d`) or the coordinate it '
                                    'carries'},
            'index': {'type': ['integer', 'null'],
                      'description': '"slice_index": the element that row '
                                     'is posed at'},
            'x': {'type': ['boolean', 'null'],
                  'description': '"log"/"invert": the abscissa -- true to '
                                 'turn it, false to put it back'},
            'y': {'type': ['boolean', 'null'],
                  'description': '"log"/"invert": the ordinate -- true to '
                                 'turn it, false to put it back'},
        }, 'required': ['figure_key', 'operation'],
           'additionalProperties': False},
    ),
    # One name for the two reads of the curve(s) a figure already holds:
    # what they answer as numbers, and those same numbers put in a file. The
    # discriminant is `action`: neither read takes an `action` of its own
    # (test_175 refuses a discriminant a member already answers for
    # itself), and what the two share is wider than what sets them apart --
    # one figure, one curve of it, and the values as they stand.
    _tool(
        'read_figure',
        'What the curve(s) a figure holds answer, and `action` says which '
        'ask. "stats": the sample count, the finite min/max/mean/std of the '
        'values, the nan/inf counts, the peak with its abscissa. "export": '
        'the same values in a file under ~/.imasviz/exports. Both read the '
        'values as they stand, so a transform a hand put on the figure is '
        'in the answer and in the file, while the leaf in the tree is '
        'unchanged.',
        {'type': 'object', 'properties': {
            'action': {'type': 'string', 'enum': ['stats', 'export']},
            'figure_key': {'type': 'string'},
            'curve': {'type': ['string', 'integer', 'null'],
                      'description': 'a name substring, a 0-based index, '
                                     'or null for every curve'},
            'format': {'type': ['string', 'null'], 'enum': ['csv', 'json'],
                       'description': '"export": csv (the default) or json'},
            'name': {'type': ['string', 'null'],
                     'description': '"export": the file name; refused when '
                                    'it names a place'},
        }, 'required': ['action', 'figure_key'],
           'additionalProperties': False},
    ),

    # One name for what a leaf's signal is doing, because the six asks are
    # one question about that signal -- « qu'est-ce que ce signal dit », and
    # then what to do with the answer. The discriminant is `action`: no
    # member of this group takes an `action` of its own (test_175 refuses a
    # discriminant a member already answers for itself), and what sets the
    # six apart is the read, not a window or a case. `figure_key` is the one
    # parameter four actions share for three different reasons, so its
    # description says which is which.
    _tool(
        'analyze_signal',
        'What one leaf\'s signal does, and what to do with what it says: '
        '`action` picks the ask. "events": the events of one `kind` read off '
        'the signal -- \'elm\' (an excursion up), \'sawtooth\' (a crash '
        'down), \'lh\' (a threshold crossing). The signal is the one '
        'get_signal answers for the leaf, so what is detected and what a '
        'figure of the same leaf draws are the same read; `threshold` / '
        '`prominence` / `min_distance` gate an ELM or a sawtooth, '
        '`threshold` / `direction` / `hysteresis` an L-H crossing, and a '
        'kind refuses a parameter it does not take, by name. `figure_key` '
        'marks the events on that curve figure (capped at 40, refused when '
        'it would be a wall). "clear_events": those marks off a curve '
        'figure, safe when it holds none -- it answers the number it took '
        'off. "events_report": the same read and detection as a '
        'self-contained HTML page -- the events in a table, the period of '
        'their times, and the picture of the figure when one is named; it '
        'lands in ~/.imasviz/reports like the other reports, and a `name` '
        'that names a place is refused by name. "spectrum": what the time '
        'series oscillates at -- the dominant frequency and its period, the '
        'leading `n_peaks` (most power first) with their power and share, '
        'and the share of the power between `band_low` and `band_high` when '
        'a band is named; a flat or too-short series is refused by name. '
        '"correlate": how far `path` lags or leads `path_b`, and at what the '
        'two oscillate together -- the lag in samples and in time, the '
        'correlation at the peak, and the shared dominant frequency; both '
        'reads are the ones a figure draws for the two leaves, so a pair the '
        'case does not hold on one clock, or at one length, is refused by '
        'name. "spectrum_report": the same spectral facts as a '
        'self-contained HTML page -- the leading peaks in a table, the band '
        'when one is named, and the picture of the figure when one is.',
        {'type': 'object', 'properties': {
            'action': {'type': 'string',
                       'enum': ['events', 'clear_events', 'events_report',
                                'spectrum', 'correlate', 'spectrum_report']},
            'uri': {'type': 'string',
                    'description': 'the case the leaf stands in; asked of '
                                   '"events", "events_report", "spectrum", '
                                   '"correlate" and "spectrum_report". '
                                   '"clear_events" works on a figure, not on '
                                   'a case.'},
            'path': {'type': 'string',
                     'description': 'the leaf; for "correlate", the first of '
                                    'the two series.'},
            'path_b': {'type': 'string',
                       'description': '"correlate": the second series, '
                                      'lagged against the first.'},
            'kind': {'type': 'string',
                     'enum': ['elm', 'sawtooth', 'lh'],
                     'description': '"events" and "events_report": which '
                                    'event is looked for.'},
            'threshold': {'type': ['number', 'null'],
                          'description': 'ELM/sawtooth: value floor. '
                                         'lh: the level crossed.'},
            'prominence': {'type': ['number', 'null'],
                           'description': 'ELM/sawtooth: how far the '
                                          'excursion must rise off the '
                                          'baseline.'},
            'min_distance': {'type': ['integer', 'number', 'null'],
                             'description': 'ELM/sawtooth: keep the most '
                                            'prominent of peaks nearer '
                                            'than this many samples.'},
            'direction': {'type': ['string', 'null'],
                          'enum': ['up', 'down', 'both'],
                          'description': 'lh: L-H (up), H-L (down), or '
                                         'both.'},
            'hysteresis': {'type': ['number', 'null'],
                           'description': 'lh: band the signal must clear '
                                          'off the level before it '
                                          're-triggers.'},
            'n_peaks': {'type': ['integer', 'null'],
                        'description': '"spectrum" and "spectrum_report": '
                                       'how many leading peaks come back; '
                                       'five when left out.'},
            'band_low': {'type': ['number', 'null'],
                         'description': '"spectrum" and "spectrum_report": '
                                        'lower bound of the band, in Hz.'},
            'band_high': {'type': ['number', 'null'],
                          'description': '"spectrum" and "spectrum_report": '
                                         'upper bound of the band, in Hz.'},
            'along': {'type': ['string', 'null'],
                      'description': 'the axis the read runs along, for the '
                                     'five reads of this tool.'},
            'indices': {'type': ['object', 'null'],
                        'description': 'each other axis fixed by name, '
                                       'the way plot and get_signal do.'},
            'indices_b': {'type': ['object', 'null'],
                          'description': '"correlate": the element of the '
                                         'second series fixed by name.'},
            'figure_key': {'type': ['string', 'null'],
                           'description': '"clear_events": the curve figure '
                                          'whose marks come off. "events": '
                                          'mark the events on it. '
                                          '"events_report" and '
                                          '"spectrum_report": put the picture '
                                          'of it on the page.'},
            'name': {'type': ['string', 'null'],
                     'description': '"events_report" and "spectrum_report": '
                                    'the name of the page; one that names a '
                                    'place, not a report, is refused.'},
        }, 'required': ['action'], 'additionalProperties': False},
    ),
    # One name for the three numbers a case is judged on: the three are
    # asked the same way -- a case, a leaf, an axis -- and answer the same
    # shape (the path that read it, the values, the points, the mean, the
    # peak and the floor). The discriminant is `quantity`: no member of the
    # group takes a word of its own (test_175 refuses a discriminant a
    # member already answers for itself). `uri` is required of the offer
    # because all three ask a case, the way `figure_key` is required of the
    # curve transforms; the leaves one member asks for belong to that
    # member's row, and a call that leaves one out is refused in that
    # member's own words.
    _tool(
        'derived_quantity',
        'A number a case is judged on, and `quantity` says which one. '
        '"greenwald": the Greenwald fraction over the time the three read, '
        'f_G = n_e / n_G with n_G = (I_pl / A) x 1e20 (I_pl in mega-Ampere, '
        'A in square metre) -- the three leaves are named by the caller '
        '(`n_e_path` in m^-3, `ip_path` in A, `area_path` in m^2), so the '
        'formula and the numbers both come from the case. "beta_normal" and '
        '"total_pressure" are the case\'s own numbers, read off the leaf the '
        'case keeps them in -- `global_quantities.beta_normal` and '
        '`profiles_1d.pressure` unless `path` names another -- never '
        'computed here (p = n_e k_B T_e + n_i k_B T_i). The two that read a '
        'leaf answer the path that read it, the values, the points and the '
        'mean, max and min; `along` and `indices` are the seams the case '
        'keeps. A case that does not hold a leaf, or holds the three at '
        'different lengths, is refused by name, never with a '
        'plausible-looking value.',
        {'type': 'object', 'properties': {
            'quantity': {'type': 'string',
                         'enum': ['greenwald', 'beta_normal',
                                  'total_pressure']},
            'uri': {'type': 'string',
                    'description': 'the case the number is read from'},
            'n_e_path': {'type': 'string',
                         'description': '"greenwald": the electron density, '
                                        'in m^-3, over time'},
            'ip_path': {'type': 'string',
                        'description': '"greenwald": the plasma current, in '
                                       'A, over time'},
            'area_path': {'type': 'string',
                          'description': '"greenwald": the cross-section, in '
                                         'm^2, over time'},
            'path': {'type': ['string', 'null'],
                     'description': '"beta_normal" and "total_pressure": the '
                                    'leaf to read; the one the case keeps '
                                    'for it when left out'},
            'along': {'type': ['string', 'null'],
                      'description': 'the axis of the leaf, for an array that '
                                     'has one; the clock where the case holds '
                                     'one'},
            'indices': {'type': ['object', 'null'],
                        'description': 'the element of the leaf, for an array '
                                       'of several'},
            'indices_ip': {'type': ['object', 'null'],
                           'description': '"greenwald": the element of the '
                                          'current series'},
            'indices_area': {'type': ['object', 'null'],
                             'description': '"greenwald": the element of the '
                                            'area series'},
        }, 'required': ['quantity', 'uri'], 'additionalProperties': False},
    ),

    # One name for the two asks about a series of shots: what one leaf does
    # across them, and that same answer as a page. The page runs the trend
    # and dresses its answer, so the two asks are one read and one word
    # apart. The group is NOT named `campaign`: it holds a tool of that
    # name, and one name answering two things is the confusion this table
    # exists to end.
    _tool(
        'trend_campaign',
        'What one leaf does across a series of shots, and `action` says '
        'which ask. "values": the trend in campaign order -- the same leaf '
        'read from each shot (the read a figure of that leaf would draw), '
        'one value per shot (at a named index of the curve, or mean/max/min '
        'over it), then the per-shot values, the least-squares slope over '
        'the shot index, first-to-last change, min and max with the shots '
        'they came from, and the direction. "report": that answer as a '
        'self-contained HTML page under ~/.imasviz/reports -- the per-shot '
        'table, the trend, the line the values make -- nothing taken from '
        'memory. A campaign of one shot, a shot the case does not hold the '
        'leaf in, or all-equal values refuses in words.',
        {'type': 'object', 'properties': {
            'action': {'type': 'string', 'enum': ['values', 'report']},
            'cases': {'type': 'array',
                      'items': {'type': 'string'},
                      'minItems': 2,
                      'description': 'the shot URIs, in campaign order.'},
            'path': {'type': 'string',
                     'description': 'the leaf to read from each shot.'},
            'at': {'type': ['integer', 'string', 'null'],
                   'description': 'a 0-based index into the curve each shot '
                                  'answers; name either this or `which`.'},
            'which': {'type': ['string', 'null'],
                      'enum': ['mean', 'max', 'min'],
                      'description': 'mean / max / min over the curve each '
                                     'shot answers; name either this or '
                                     '`at`.'},
            'along': {'type': ['string', 'null']},
            'indices': {'type': ['object', 'null']},
            'name': {'type': ['string', 'null'],
                     'description': '"report": the report name, without the '
                                    '.html; refused when it names a place'},
        }, 'required': ['action', 'cases', 'path'],
           'additionalProperties': False},
    ),

    # One name for everything a window of the session answers, because the
    # ask is « what do I do with that window », and the five answers differ
    # by one word. The window itself is named `window` here although three
    # of the gestures were written against `key`: one group, one word (the
    # rename is `ACTION_RENAMES`, applied once, after the checks).
    _tool(
        'manage_window',
        'What one window of the session is asked to do, and `action` says '
        'which. "list": every window of the session, in the order the menus '
        'draw them -- kind, label, key, and whether it is on screen. '
        '"show": the user\'s "remets Plot1 à l\'écran" command -- put a '
        'window back on the screen after a hide, at the size it holds; it '
        'keeps its key either way. "hide": take it off the screen without '
        'deleting it, and "show" brings it back. "close": delete it and '
        'forget its key -- asked for, never taken on a request that names '
        'no window. "focus": the user\'s "show me this" command -- the '
        'window is brought to the front, shown when it is off the screen '
        'and raised when it is not, and keeps the size it holds unless '
        '`width` and `height` name the pixels to put it at -- a side left '
        'out keeps the size the window holds on that side. A window that '
        'is on screen but not in front is "focus", and a draw is neither: '
        'showing and raising are the gestures of the user\'s *Windows* '
        'menu, so a figure you drew or named in your answer is not a '
        'reason to call it -- a draw is not an ask to show it. `window` is '
        '"app" for the application, a figure key for one figure, a case '
        'URI for its shot view; left out of "focus", the application. '
        'Call "focus" when the user asks to see or bring a window forward '
        '("montre-moi Plot1", "ramène Plot1 devant", "je ne vois pas la '
        'figure"), and to size one for a requested picture before the '
        'get_screenshot on it; it answers the size the window now holds.',
        {'type': 'object', 'properties': {
            'action': {'type': 'string',
                       'enum': ['list', 'show', 'hide', 'close', 'focus']},
            'window': {'type': 'string',
                       'description': 'The window the action is made on: '
                                      '"app" for the application, a figure '
                                      'key for one figure, a case URI for '
                                      'its shot view. Required of "show", '
                                      '"hide" and "close"; the application '
                                      'when "focus" leaves it out; not a '
                                      'parameter of "list".'},
            'width': {'type': ['integer', 'null'],
                      'description': '"focus": pixels, 1 and up; left out, '
                                     'the size the window holds'},
            'height': {'type': ['integer', 'null'],
                       'description': '"focus": pixels, 1 and up; left out, '
                                      'the size the window holds'},
        }, 'required': ['action'], 'additionalProperties': False},
    ),
    _tool(
        'list_plugins',
        'The entries an IDS root earns, in registration order. '
        'The feature number, its label, its description for each.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'ids_name': {'type': 'string'},
        }, 'required': ['uri', 'ids_name'], 'additionalProperties': False},
    ),
    _tool(
        'run_plugin',
        'Run one entry of a plugin, with the answers the entry would have '
        'asked the user. `occurrence` and `time` are handed instead of being '
        'asked: an entry that asks an instant and is handed none is refused by '
        'name, not left to open a dialog. `ids_name` says which IDS branch the '
        'line is asked on; left out, the branch is resolved from the case, and '
        'several branches earning that entry is refused with them named. '
        'Refused by name when the case does not offer that entry. '
        'The entry draws its own window: `drawn` names the ones it opened or '
        'redrew and `reused` the one it drew again. Asking the same entry '
        'again with the same answers draws into the window that already '
        'stands instead of opening another over it. What does double is '
        'asking the entry AND the tool that entry answers with: the two '
        '`equilibriumsurfaces` entries ARE '
        '`equilibrium(action="surfaces")` (entry 0) and '
        '`equilibrium(action="at_time")` (entry 1), as the profiles entry '
        'is the table and curve draws. Ask one per window.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'plugin': {'type': 'string'},
            'entry': {'type': 'integer'},
            'occurrence': {'type': 'integer', 'default': 0},
            'ids_name': {'type': ['string', 'null']},
            'time': {'type': ['number', 'null']},
        }, 'required': ['uri', 'plugin', 'entry'],
         'additionalProperties': False},
    ),
    # One name for the run as a thing kept: written, put back, cleared, and
    # the files beside it that a run is made of. The discriminant is
    # `action`: no member of the group takes a word of its own (test_175
    # refuses a discriminant a member already answers for itself), and
    # `name` could not be one -- it is a SESSION file for "save"/"restore"
    # and a CONFIGURATION file for the three asks that read or write one. So
    # the parameters are told apart in their own blocks, the same way the
    # rows of `ACTION_PARAMETERS` tell them apart when a call is checked.
    _tool(
        'manage_session',
        'The run kept and read back, and `action` says which ask. "save": '
        'the whole screen as the application writes it -- the cases, the '
        'loads, the selection, the windows and what a hand styled on them. '
        '"restore": one of those sessions put back: the cases open, the '
        'loads replayed, the figures and plugin windows drawn the way the '
        'file named them, and the answer names the cases that came back. '
        '"new": one clean session WITHOUT saving -- every case view and '
        'every figure of this session is closed and nothing is written, so '
        'the sessions the user saved on disk (`last_session` among them) '
        'and the reports stay where they are; it answers how many windows '
        'it closed. This is the *New session* of the *File* menu, asked the '
        'way the page asks it, and like that menu\'s close it is a gesture '
        'the user asks for out loud: a request that names no clean slate is '
        'a refusal, not a reset. "list_sessions": the .vsess files the '
        'configuration folder holds, as the application lists them. '
        '"list_configurations": the plot (.pcfg) and selection (.lsp) files '
        'in that folder, `kind` narrowing to one of the two -- a kind the '
        'application does not answer is refused by name, "session" among '
        'them, the sessions being "list_sessions". "apply": one saved '
        'configuration put on a case: its quantities selected, the IDSs the '
        'case would need and does not hold loaded first the way the menu '
        'does it, a .lsp read as a .pcfg; it answers how many were '
        'selected, and a name the folder does not hold is refused naming '
        'the ones it does. "save_selection": the case\'s current selection '
        'written out as a .lsp, one quantity per selected node -- nothing '
        'selected is refused by name. "save_plot_configuration": one Table '
        'Plot View written out as a .pcfg, the quantities of its panels and '
        'the place each held -- any other window is refused by name, and '
        'list_windows names the ones that hold panels.',
        {'type': 'object', 'properties': {
            'action': {'type': 'string',
                       'enum': ['save', 'restore', 'new', 'list_sessions',
                                'list_configurations', 'apply',
                                'save_selection',
                                'save_plot_configuration']},
            'name': {'type': ['string', 'null'],
                     'description': 'The file the ask is about. "save" and '
                                    '"restore": a session under the '
                                    'configuration folder ("save" settles '
                                    'on a name of its own when left out). '
                                    '"apply", "save_selection" and '
                                    '"save_plot_configuration": the '
                                    'configuration, .lsp as .pcfg, with no '
                                    'extension spelled. Required of those '
                                    'three.'},
            'path': {'type': ['string', 'null'],
                     'description': '"save" and "restore": a full file '
                                    'name, instead of a name in the '
                                    'configuration folder'},
            'kind': {'type': ['string', 'null'],
                     'enum': ['plot', 'selection'],
                     'description': '"list_configurations": one kind only; '
                                    'left out, both are answered'},
            'uri': {'type': ['string', 'null'],
                    'description': 'The case the ask is made on, for '
                                   '"apply", "save_selection" and '
                                   '"save_plot_configuration"; required of '
                                   'those three'},
            'figure_key': {'type': ['string', 'null'],
                           'description': '"save_plot_configuration": the '
                                          'Table Plot View to write out'},
        }, 'required': ['action'], 'additionalProperties': False},
    ),
    _tool(
        'generate_report',
        'A self-contained HTML report on disk under `~/.imasviz/reports`; '
        '`scope` says which report. "plot" -- a window of curves: the '
        'image of the window, and one row per trace it drew -- the '
        'quantity, the number of samples, the finite minimum and maximum, '
        'and the nan/inf counts. This is the "rapport"/"report" the user '
        'asks for. For a report of more than one plot, call it once per '
        'plot -- a report is one window, and the page lists the ones a '
        'request wrote together. A window that draws no curve it could '
        'stat is refused by name. "case_loaded" -- the loaded tree of a '
        'case: one row per curve the tree holds -- the numeric arrays its '
        'leaves read, in tree order -- with the statistics of each. An IDS '
        'not yet loaded is not a curve, so the answer says how many curves '
        'it gave and list_idss names what the case still holds. A case '
        'whose loaded tree has no curve is refused by name. "case_ids" -- '
        'the case itself: every IDS the case\'s data dictionary holds and '
        'the occurrences each one holds, which of those the session '
        'loaded, and for each loaded occurrence the header of its '
        '`ids_properties` values and available signals -- the signals the '
        'tree holds for it, kept to the ones the tree carries as available '
        '(the same test its own colouring applies), a 0-D scalar held by '
        'the dynamic array among them. The "inventaire du cas" / "what '
        'does this case hold" report. A property the case leaves empty is '
        'named empty, an occurrence without an available signal is named '
        'as such, and a case that holds no data at all is refused by name. '
        '`scope="plot"` takes the `figure_key` of the window, the other '
        'two the `uri` of the case; `name` is the report name (a place, '
        'not a report, is refused).',
        {'type': 'object', 'properties': {
            'scope': {'type': 'string',
                      'enum': ['plot', 'case_loaded', 'case_ids']},
            'figure_key': {'type': 'string'},
            'uri': {'type': 'string'},
            'name': {'type': ['string', 'null']},
        }, 'required': ['scope'], 'additionalProperties': False},
    ),
    _tool(
        'export_to_ids',
        'Copy the opened IDSs of one case into the target case. '
        '`target_uri` is the case the Access Layer writes to.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'target_uri': {'type': 'string'},
            'dd_version': {'type': ['string', 'null']},
        }, 'required': ['uri', 'target_uri'], 'additionalProperties': False},
    ),
    _tool(
        'get_screenshot',
        'The explicit picture ask: a window as it stands, in PNG. '
        '"app" for the application, a figure key for one figure, a case '
        'URI for its shot view. The picture is the size the window is, '
        'and no bigger: when a requested picture should be readable and '
        'the window answers small, size it with '
        'manage_window(action="focus") first, then take the picture. The '
        'LLM cannot parse this PNG on this stack; describe a figure by '
        'reading its underlying arrays with get_signal instead.',
        {'type': 'object', 'properties': {
            'window': {'type': 'string', 'default': 'app'},
        }, 'additionalProperties': False},
    ),
    _tool(
        'get_logs',
        'The log panel of one case, or of every case when `uri` is left '
        'out: the last `tail` lines the gestures wrote there, the named '
        'refusals among them.',
        {'type': 'object', 'properties': {
            'uri': {'type': ['string', 'null']},
            'tail': {'type': 'integer', 'default': 200},
        }, 'additionalProperties': False},
    ),
    # One name for the lab notebook, because the eight asks are one question
    # about it -- « qu'est-ce que je fais des notes » -- and the answers
    # differ by one word. The discriminant is `action` and NOT `scope`:
    # `add_note(scope, ...)` already answers `scope` for which of the two
    # journals it writes, and a group merged under a word its own members
    # take is one word answering two questions (test_175 refuses it).
    _tool(
        'manage_note',
        'The lab notebook of the two journals, and `action` says what is '
        'asked of it. "search": the notebook asked as a RAG -- the '
        'structured filters (machine, campaign, shot, date_from, date_to, '
        'author) narrow to the notes that name each field asked of, then '
        '`query` is ranked over them, by embeddings when the preferences '
        'name the embedding endpoint and it answers, else by keyword, and '
        'the answer names which it used; with no `query` the notes come '
        'back newest first. "list": the same filters without a query, '
        'newest first -- and an empty answer is an answer. "read": the '
        'full body of one `note_id`; the `snippet` of "search" is the hand '
        'that leads to it, not the text. "stats": what the two journals '
        'are on this node -- the folder each is under, how many notes each '
        'holds, whether the embedding endpoint is named and which model it '
        'names; ask it before a search and it names the method the run '
        'will rank with, and the shared one answers a refusal (not a '
        'folder named) when it is not set up. "reindex": put the '
        'journal(s) in step with their index -- the ask of a fresh, stale '
        'or guarded index (written under an embedding endpoint the run is '
        'no longer under: its vectors are in a different space than the '
        'query), answering per journal how many it kept, wrote and '
        'dropped. "add": one new note, `text` required and `author` '
        'defaulting to $USER -- a write with no author at all is refused '
        'by name, the write being visible to whoever reads the journal. '
        '"edit": one existing note changed in place, keeping the id the '
        'other writers read it under; a field left out keeps the one the '
        'note held, a field named replaces it and an empty one clears it, '
        'except the author (a note keeps its author) and the body (an '
        'empty `text` is a refusal). "delete": one note gone, its file and '
        'the cache entry the run holds for it. A note that names machine, '
        'campaign, shot and date is the one about a shot, and one that '
        'names none of them is a general one, in the same journal. '
        'A `note_id` the journal does not hold is refused by name, naming '
        'the ids it does hold. A write to the shared journal is a visible '
        'line in a place everyone you share it with reads, and it is the '
        'loop that asks for it in the user\'s own words before it runs.',
        {'type': 'object', 'properties': {
            'action': {'type': 'string',
                       'enum': ['search', 'list', 'read', 'add', 'edit',
                                'delete', 'stats', 'reindex']},
            'scope': {'type': ['string', 'null'],
                      'enum': ['personal', 'shared', None],
                      'description': 'Which journal the action is made on: '
                                     '"personal" under ~/.imasviz/journals, '
                                     '"shared" under the folder '
                                     'SharedJournalDir names. Required of '
                                     '"read", "add", "edit" and "delete"; '
                                     'left out of "search", "list" and '
                                     '"reindex" to ask the two at once; '
                                     'not a parameter of "stats".'},
            'note_id': {'type': 'string',
                        'description': '"read", "edit" and "delete": the '
                                       'note, under the id the journal '
                                       'names it (a file name without .md), '
                                       'the one "search" and "list" answer '
                                       'it by'},
            'query': {'type': ['string', 'null'],
                      'description': '"search": the text to rank the '
                                     'filtered notes by; left out, the '
                                     'notes come back newest first'},
            'limit': {'type': 'integer',
                      'description': '"search": how many notes to answer'},
            'text': {'type': ['string', 'null'],
                     'description': '"add": the body, required. "edit": '
                                    'the new body; left out, the one the '
                                    'note held, and an empty one is a '
                                    'refusal'},
            'machine': {'type': ['string', 'null'],
                        'description': 'a filter of "search" and "list", a '
                                       'field of "add" and "edit"'},
            'campaign': {'type': ['string', 'null'],
                         'description': 'a filter of "search" and "list", '
                                        'a field of "add" and "edit"'},
            'shot': {'type': ['string', 'null'],
                     'description': 'a filter of "search" and "list", a '
                                    'field of "add" and "edit"'},
            'date': {'type': ['string', 'null'],
                     'description': '"add" and "edit": the note\'s shot '
                                    'date, ISO 8601 YYYY-MM-DD'},
            'date_from': {'type': ['string', 'null'],
                          'description': '"search" and "list": ISO 8601 '
                                         'YYYY-MM-DD, inclusive'},
            'date_to': {'type': ['string', 'null'],
                        'description': '"search" and "list": ISO 8601 '
                                       'YYYY-MM-DD, inclusive'},
            'author': {'type': ['string', 'null'],
                       'description': 'a filter of "search" and "list"; on '
                                      '"add" and "edit" the writer, '
                                      'defaulting to $USER'},
            'title': {'type': ['string', 'null'],
                      'description': '"add" and "edit": the note\'s title'},
        }, 'required': ['action'], 'additionalProperties': False},
    ),
    # One name for the corpus of documents the agent reads for itself: what
    # it holds, what it answers to a question, one document of it whole, the
    # store put in step with the folder, and its state. The discriminant is
    # `action`: no member of the group takes a word of its own (test_175
    # refuses a discriminant a member already answers for itself). `rel`
    # keeps the spelling the answers already use: a search hit names the
    # document it came from by that word, so the read asks with it.
    _tool(
        'manage_documents',
        'The corpus of documents the in-app agent reads for its own RAG -- '
        'the markdown, text and PDF files the folder AgentDocsDir names -- '
        'and `action` says which ask. "list": the corpus as named (the '
        'name, the size, the date, the `rel` a search answers by); a folder '
        'with no document is an answer and a folder not named is a refusal '
        'that names it, the same shape a shared journal without its folder '
        'answers. "search": the ranked chunks of those files, one hit per '
        'chunk -- the document `rel`, the chunk, a snippet -- the ask when '
        'the question is about the user\'s own writing; `query` is what to '
        'look for and `limit` how many chunks come back, 8 left out. The '
        'answer names the `method` it ranked with (hybrid / embeddings / '
        'keyword / empty); a store written under another embedding endpoint '
        'is `guarded`, its vectors stand in a different space than the '
        'query, the keyword alone ranks, and "reindex" is what sets the two '
        'in step. "read": one document whole, by the `rel` a hit names -- '
        'the ask when a hit is worth reading entire; not in the corpus is a '
        'refusal naming the ones it does read, and so is a document it '
        'cannot read. "reindex": the corpus in step with its store, after a '
        'document was added to the folder or after the embedding endpoint '
        'changed; it keeps what it has, embeds what moved, drops what left '
        'the folder, and answers how many documents and chunks it kept, '
        'wrote and dropped and whether this pass vectorized. "stats": how '
        'many documents and chunks the corpus holds, the endpoint and model '
        'it was written under, and when it was built -- the answer to "can '
        'the agent read my documents" when it is "not indexed yet" or '
        '"indexed under another endpoint". A corpus the run cannot read '
        'is refused by name in every one of the five.',
        {'type': 'object', 'properties': {
            'action': {'type': 'string',
                       'enum': ['list', 'search', 'read', 'reindex',
                                'stats']},
            'query': {'type': 'string',
                      'description': '"search": what to look for; asked of '
                                     'no other action'},
            'limit': {'type': ['integer', 'null'],
                      'description': '"search": how many chunks come back; '
                                     '8 when left out'},
            'rel': {'type': 'string',
                    'description': '"read": the document under the corpus '
                                   'folder, spelled as a search hit names '
                                   'it'},
        }, 'required': ['action'], 'additionalProperties': False},
    ),
    # One name for the prompt catalogue, because the six asks are one
    # object looked at, filled, filed, changed and taken away. The
    # discriminant is `action`: no member takes one of its own (test_175
    # refuses a discriminant a member already answers for itself). `scope`
    # is not the discriminant here either -- it is WHICH catalogue, and
    # four of the six members answer it for themselves.
    _tool(
        'manage_prompt',
        'The catalogue of prompts the user wrote once and keeps to ask '
        'again -- `action` picks the ask. "list": the prompts, each with '
        'its id, its name, its category, its one-line description and '
        'the holes it opens; `category` and `query` narrow it and '
        '`categories` answers how many prompts each category holds. The '
        'personal catalogue is under ~/.imasviz/prompts and the shared '
        'one under the folder SharedPromptsDir names (an unnamed shared '
        'folder costs its own half of the list, named in '
        'catalogues_unavailable -- the personal prompts still answer). '
        'Ask of it when the user says "relance le prompt ..." or "run my '
        'usual X" and you do not know the wording they filed. "detail": '
        'one prompt whole -- its body with its holes still open, and '
        '`values`: what each hole would be answered from right now (what '
        'the user typed last time, what this session knows, what the '
        'file declares) and null for the ones that still need a value. '
        '`name` is the id or the display name; a name two prompts carry '
        'is refused naming their ids. Asking this remembers nothing: it '
        'is the look, not the typing. "fill": the prompt as it will be '
        'asked, its holes filled, and nothing run. A hole is filled from '
        'the first source that answers it -- what you name in `values`, '
        'what was typed last time for that prompt, what this session '
        'knows (its open case: case, uri, shot, run, database; its one '
        'open window: figure), what the file declares -- and the answer '
        'says which one it was. A hole none of them answers is a refusal '
        'naming the holes: a prompt is never sent with {shot} in it and '
        'never sent with a guess. Take the `text` this answers and ask '
        'it as the user asked it -- filling is not running. "save": one '
        'prompt into the catalogue, named and described, so the next run '
        'does not type it again; `text` is the prompt as it is asked, '
        'with its holes spelled {name}, and `variables` left out is read '
        'off the text (every hole it opens, asked for on every run), a '
        'hole declared and never opened being refused by name. The user '
        'asks for this in their own words ("garde ce prompt", '
        '"enregistre-le") -- a turn that merely drew a figure is not an '
        'ask to file its wording, and `scope="shared"` files it in the '
        'folder the team reads, which is a line others see. "edit": one '
        'prompt of the catalogue '
        'changed in place, keeping the id the pages, the sessions and the '
        'remembered values read it under. A field you leave out keeps the '
        'one the prompt held, a field you name replaces it, an empty one '
        'clears it -- the body excepted, which an edit cannot empty; a '
        'new prompt is "save". "delete": one prompt out of the '
        'catalogue, and the values that were remembered for it. Not '
        'there is a refusal naming the ids the catalogue holds. This '
        'takes a file the user wrote off the disk: it is asked for in '
        'their own words, not decided for them. `scope` is WHICH '
        'catalogue, not which ask -- left out, both are asked.',
        {'type': 'object', 'properties': {
            'action': {'type': 'string',
                       'enum': ['list', 'detail', 'fill', 'save', 'edit',
                                'delete']},
            'name': {'type': 'string',
                     'description': 'the id or the display name of the '
                                    'prompt; asked of the five asks but '
                                    '"list", which is what `query` '
                                    'narrows'},
            'scope': {'type': ['string', 'null'],
                      'enum': ['personal', 'shared'],
                      'description': 'the one catalogue to ask of; left '
                                     'out, both are asked'},
            'text': {'type': ['string', 'null'],
                     'description': '"save": the prompt, holes spelled '
                                    '{name}. "edit": its new body, the '
                                    'one it held when left out'},
            'category': {'type': ['string', 'null'],
                         'description': '"list": the prompts that name '
                                        'this category, compared without '
                                        'minding the case. "save" and '
                                        '"edit": the category to put'},
            'description': {'type': ['string', 'null'],
                            'description': '"save" and "edit": one line '
                                           'saying what it asks, for the '
                                           'reader of the list'},
            'variables': {'type': ['object', 'string', 'null'],
                          'description': '"save" and "edit": hole -> '
                                         'default, as an object or as the '
                                         '"a=1; b=" line the file spells; '
                                         'left out, read off the text'},
            'prompt_id': {'type': ['string', 'null'],
                          'description': '"save": the file name to file '
                                         'it under; left out, the slug of '
                                         'the name'},
            'values': {'type': ['object', 'null'],
                       'additionalProperties': {'type': 'string'},
                       'description': '"fill": the hole -> the value to '
                                      'use this time, for the holes the '
                                      'session does not answer'},
            'query': {'type': ['string', 'null'],
                      'description': '"list": a word of the name, the '
                                     'description, the category or the '
                                     'id'},
            'limit': {'type': ['integer', 'null'],
                      'description': '"list": how many prompts come back; '
                                     '100 when left out'},
        }, 'required': ['action'], 'additionalProperties': False},
    ),
]

TOOL_PARAMETERS = {
    tool['function']['name']: tool['function']['parameters']
    for tool in TOOLS
}


# The groups the manual's tool table draws (manual/agentics.rst, "The one
# core and the one tool set"), spelled next to the schemas so the two cannot
# drift without a word: test_174 refuses a group naming a tool that is not
# offered, a tool left out of every group, and a tool in two of them.
#
# A group answers a question the flat schemas cannot: the 84 schemas repeat
# the same parameter words (``along`` 12 times, ``scope`` 13, ``figure_key``
# 18), so a parameter the model put on the wrong tool of a group is a far
# likelier mistake than a parameter it invented, and a refusal that only
# lists what is *not* there leaves the model guessing -- ``siblingTaking``
# and ``unknownParameterRefusal`` are that answer.
#
# Each entry is ``(label, members, offers)``, and an offer is
# ``(offeredName, discriminator, ((action, member), ...))``:
#
#   * no offers -- the group is offered member by member, under its own name;
#   * one offer -- the group answers one name, and the ``discriminator``
#     parameter says which member the call means;
#   * two offers -- the group is kept together for the refusal (its tools
#     answer each other's parameters) but is not one tool: "the drawing" is
#     ``plot(mode=...)`` and ``get_signal``, "the curves already drawn" is
#     ``transform_curve(operation=...)`` and ``read_figure(action=...)``.
#
# The seam that makes this safe is one rule, and it is the whole reason the
# table lives beside the schemas instead of inside the loop:
#
#     a call reaches the core, the guards and the loop's own account as its
#     MEMBER, never as its group.
#
# ``manage_window(action='close')`` is the case that pays for the rule: the
# guard at ``DESTRUCTIVE_GESTURES`` is asked about ``close_window``, so a
# window is only taken away when the user asked for it -- a guard that read
# the call as ``manage_window`` would not recognise it and would close a
# figure nobody named. The same holds for what a turn keeps of itself: the
# set of reports that wrote a file, the figures a close took away, the notes
# a journal line stands on, the figures a turn worked on for a capture --
# all keyed by the member, because that is the vocabulary the guards and
# ``mcp_server.agent_mode.FIGURE_MUTATIONS`` were written in.
#
# What a MODEL reads is the other vocabulary, and it stays the OFFERED one:
# the transcript lines, ``last_action``, the ``name`` of the tool message
# handed back. A model that reads "plot_report: saved to ..." in its own
# transcript calls ``plot_report`` on the next turn and is refused for a name
# it was never offered, so the merge would leak into the very place that can
# not act on it. Prose that INSTRUCTS a call -- what a re-anchor asks the
# model to answer with -- is spelled from the offer for the same reason:
# ``callSpelling`` says it, and test_175 refuses any instruction naming a
# name that is not on offer.
#
# A group whose offer is in ``TOOLS`` no longer offers its members: the coup
# is clean, and ``resolveCall`` refuses a member name that was merged away
# while naming the offer that took its place.
FAMILIES = (
    ('cases', ('open_case', 'list_cases', 'close_case'), (
        ('manage_case', 'action', (
            ('open', 'open_case'),
            ('list', 'list_cases'),
            ('close', 'close_case'))),
    )),
    ('the IDSs', ('list_idss', 'list_case_idss', 'load_ids'), (
        ('manage_idss', 'action', (
            ('declared', 'list_idss'),
            ('filled', 'list_case_idss'),
            ('load', 'load_ids'))),
    )),
    ('the tree', ('search_nodes', 'describe_node', 'describe_ids',
                  'list_quantities'), (
        ('inspect_tree', 'action', (
            ('search', 'search_nodes'),
            ('node', 'describe_node'),
            ('ids', 'describe_ids'),
            ('quantities', 'list_quantities'))),
    )),
    ('the selection', ('select_signals', 'unselect_all', 'list_selection'), (
        ('manage_selection', 'action', (
            ('select', 'select_signals'),
            ('clear', 'unselect_all'),
            ('list', 'list_selection'))),
    )),
    ('the drawing', ('plot_one', 'plot_slice', 'plot_selection',
                     'plot_table', 'plot_stacked', 'get_signal'), (
        ('plot', 'mode', (
            ('single', 'plot_one'),
            ('slice', 'plot_slice'),
            ('selection', 'plot_selection'),
            ('table', 'plot_table'),
            ('stacked', 'plot_stacked'))),
        ('get_signal', None, ()),
    )),
    ('the equilibrium', ('equilibrium_surfaces', 'equilibrium_at_time'), (
        ('equilibrium', 'action', (
            ('surfaces', 'equilibrium_surfaces'),
            ('at_time', 'equilibrium_at_time'))),
    )),
    ('the curves already drawn', ('scale_curve', 'shift_curve',
                                  'normalize_curve', 'reset_curve',
                                  'remove_curve', 'curve_stats',
                                  'export_curve'), (
        ('transform_curve', 'operation', (
            ('scale', 'scale_curve'),
            ('shift', 'shift_curve'),
            ('normalize', 'normalize_curve'),
            ('reset', 'reset_curve'),
            ('remove', 'remove_curve'))),
        ('read_figure', 'action', (
            ('stats', 'curve_stats'),
            ('export', 'export_curve'))),
    )),
    ('the axes and the slices of a window',
     ('set_axis_range', 'set_image_window', 'set_slice_index',
      'set_log_scale', 'invert_axis'), (
        ('configure_axes', 'operation', (
            ('range', 'set_axis_range'),
            ('image_window', 'set_image_window'),
            ('slice_index', 'set_slice_index'),
            ('log', 'set_log_scale'),
            ('invert', 'invert_axis'))),
    )),
    ('the physics of a signal', ('detect_events', 'clear_event_marks',
                                 'events_report', 'spectrum',
                                 'cross_correlation', 'spectrum_report'), (
        ('analyze_signal', 'action', (
            ('events', 'detect_events'),
            ('clear_events', 'clear_event_marks'),
            ('events_report', 'events_report'),
            ('spectrum', 'spectrum'),
            ('correlate', 'cross_correlation'),
            ('spectrum_report', 'spectrum_report'))),
    )),
    ('what a case says', ('greenwald', 'beta_normal', 'total_pressure'), (
        ('derived_quantity', 'quantity', (
            ('greenwald', 'greenwald'),
            ('beta_normal', 'beta_normal'),
            ('total_pressure', 'total_pressure'))),
    )),
    ('a campaign of shots', ('campaign', 'campaign_report'), (
        # Not `campaign`: the group holds a tool of that name, and one name
        # answering two things is the confusion this table exists to end.
        ('trend_campaign', 'action', (
            ('values', 'campaign'),
            ('report', 'campaign_report'))),
    )),
    # `focus_window` stands with the windows it moves, not with the capture
    # it used to share a group with: one name for everything a window answers.
    ('the windows', ('list_windows', 'show_window', 'hide_window',
                     'close_window', 'focus_window'), (
        ('manage_window', 'action', (
            ('list', 'list_windows'),
            ('show', 'show_window'),
            ('hide', 'hide_window'),
            ('close', 'close_window'),
            ('focus', 'focus_window'))),
    )),
    ('the plugins', ('list_plugins', 'run_plugin'), (
        ('plugin', 'action', (
            ('list', 'list_plugins'),
            ('run', 'run_plugin'))),
    )),
    ('sessions and configurations', ('save_session', 'restore_session',
                                     'new_session', 'list_sessions',
                                     'list_configurations',
                                     'select_from_configuration',
                                     'save_selection',
                                     'save_plot_configuration'), (
        ('manage_session', 'action', (
            ('save', 'save_session'),
            ('restore', 'restore_session'),
            ('new', 'new_session'),
            ('list_sessions', 'list_sessions'),
            ('list_configurations', 'list_configurations'),
            ('apply', 'select_from_configuration'),
            ('save_selection', 'save_selection'),
            ('save_plot_configuration', 'save_plot_configuration'))),
    )),
    # Offered under one name since this pass: the three reports answer the
    # same question about three different things, and `scope` is that
    # question -- no member of the group takes a `scope` of its own, which
    # is what test_175 refuses for every group (the journals group cannot
    # use it: `add_note(scope, ...)` already does).
    ('the reports', ('plot_report', 'case_report', 'case_ids_report'), (
        ('generate_report', 'scope', (
            ('plot', 'plot_report'),
            ('case_loaded', 'case_report'),
            ('case_ids', 'case_ids_report'))),
    )),
    ('the export', ('export_to_ids',), (
        ('export_to_ids', None, ()),
    )),
    ('the screen', ('get_screenshot',), (
        ('get_screenshot', None, ()),
    )),
    ('the log', ('get_logs',), (
        ('get_logs', None, ()),
    )),
    ('the journals', ('search_journals', 'list_notes', 'read_note',
                      'add_note', 'edit_note', 'delete_note',
                      'journal_stats', 'reindex_journals'), (
        ('manage_note', 'action', (
            ('search', 'search_journals'),
            ('list', 'list_notes'),
            ('read', 'read_note'),
            ('add', 'add_note'),
            ('edit', 'edit_note'),
            ('delete', 'delete_note'),
            ('stats', 'journal_stats'),
            ('reindex', 'reindex_journals'))),
    )),
    ('the documents corpus', ('list_documents', 'search_documents',
                              'read_document', 'reindex_documents',
                              'documents_stats'), (
        ('manage_documents', 'action', (
            ('list', 'list_documents'),
            ('search', 'search_documents'),
            ('read', 'read_document'),
            ('reindex', 'reindex_documents'),
            ('stats', 'documents_stats'))),
    )),
    ('the prompts', ('list_prompts', 'prompt_detail', 'fill_prompt',
                     'save_prompt', 'edit_prompt', 'delete_prompt'), (
        ('manage_prompt', 'action', (
            ('list', 'list_prompts'),
            ('detail', 'prompt_detail'),
            ('fill', 'fill_prompt'),
            ('save', 'save_prompt'),
            ('edit', 'edit_prompt'),
            ('delete', 'delete_prompt'))),
    )),
)

# An offer whose discriminator is None is a member spelled under its own
# name: the group is not merged, and nothing is resolved.
_OFFERS = {}
for _label, _members, _offers in FAMILIES:
    for _offer in (_offers or [(name, None, ()) for name in _members]):
        _OFFERS[_offer[0]] = (_label, _offer[1], dict(_offer[2]),
                              tuple(action for action, _ in _offer[2]))

_OFFER_OF_MEMBER = {}
for _name, (_label, _discriminator, _actions, _order) in _OFFERS.items():
    for _action, _member in _actions.items():
        _OFFER_OF_MEMBER[_member] = (_name, _action, _label)

# The parameters each MERGED member takes -- the schema it had while it was
# offered on its own, kept because it is what a call of that action must be
# checked against. An offered schema can only declare what every action of
# the group needs (`generate_report` lists `scope`, `figure_key`, `uri` and
# `name`; only `scope` is required of every one of them), so without this,
# `generate_report(scope="plot")` would reach the core missing a `figure_key`
# and Python would answer with a TypeError about a positional argument.
#
# A member of a group that is not merged appears in no row: its own schema,
# spelled in its `_tool` definition, is both what is offered and what is
# checked. test_175 refuses the drift between a row here and the offered
# schema of its group: an action taking a parameter the group's schema does
# not declare is a call the model is never told it may make.
ACTION_PARAMETERS = {
    # The three asks about the cases. The group can require its
    # discriminant alone -- "list" names no case at all -- so these rows are
    # what says that "open" and "close" without a `uri` are incomplete, and
    # that a `dd_version` beside "list" is a word that went to the wrong ask.
    'open_case': ({
        'uri': {'type': 'string',
                'description': 'the case URI, e.g. imas:hdf5?path=...'},
        'dd_version': {'type': ['string', 'null'],
                       'description': 'the data dictionary version to pin '
                                      'the case at'},
    }, ('uri',)),
    'list_cases': ({}, ()),
    'close_case': ({
        'uri': {'type': 'string'},
    }, ('uri',)),
    # What the tree of a case says about itself. `query` belongs to the
    # rank alone, and `ids_name` is optional for that one only: it narrows a
    # search that stands without it, while "ids" and "quantities" are
    # nothing without the IDS they read. "node" is nothing without its leaf,
    # and the leaf it asks for is spelled as a search hit named it.
    'search_nodes': ({
        'uri': {'type': 'string'},
        'query': {'type': 'string', 'default': ''},
        'ids_name': {'type': ['string', 'null']},
        'limit': {'type': 'integer', 'default': 200},
    }, ('uri',)),
    'describe_node': ({
        'uri': {'type': 'string'},
        'path': {'type': 'string'},
    }, ('uri', 'path')),
    'describe_ids': ({
        'uri': {'type': 'string'},
        'ids_name': {'type': 'string'},
        'occurrence': {'type': 'integer', 'default': 0},
    }, ('uri', 'ids_name')),
    'list_quantities': ({
        'uri': {'type': 'string'},
        'ids_name': {'type': 'string'},
        'occurrence': {'type': 'integer', 'default': 0},
    }, ('uri', 'ids_name')),
    # The three asks about the selection. `uri` is the one thing they share
    # and the group requires it; `paths` and `additive` belong to "select"
    # alone, and a "list" that carries them is a call whose word went to the
    # wrong action -- which is what these rows answer, refusal by name.
    'select_signals': ({
        'uri': {'type': 'string'},
        'paths': {'type': 'array', 'items': {}},
        'additive': {'type': 'boolean', 'default': True},
    }, ('uri', 'paths')),
    'unselect_all': ({
        'uri': {'type': 'string'},
    }, ('uri',)),
    'list_selection': ({
        'uri': {'type': 'string'},
    }, ('uri',)),
    'plot_one': ({
        'uri': {'type': 'string'},
        'path': {'type': 'string'},
        'along_time': {'type': ['boolean', 'null']},
        'along': {'type': ['string', 'null']},
        'indices': {'type': ['object', 'null'],
                    'additionalProperties': {'type': 'integer'}},
        'into_figure_key': {'type': ['string', 'null']},
        'time': {'type': ['number', 'null']},
        'time_interp': {'type': ['boolean', 'null']},
    }, ('uri', 'path')),
    # `leaf` is the name `plot_slice` takes in Python. A model answering
    # `plot(mode="slice", leaf=...)` would be typing a second word for what
    # every other mode of the same tool calls `path` -- so the OFFER spells
    # `path` and this row is written in the offer's vocabulary, and
    # `ACTION_RENAMES` below is the one place the two spellings meet.
    'plot_slice': ({
        'uri': {'type': 'string'},
        'path': {'type': 'string'},
        'time': {'type': 'number'},
        'occurrence': {'type': 'integer', 'default': 0},
        'interpolation': {'type': 'string',
                          'enum': ['linear', 'closest', 'previous'],
                          'default': 'linear'},
        'into_figure_key': {'type': ['string', 'null']},
    }, ('uri', 'path', 'time')),
    'plot_selection': ({
        'uri': {'type': 'string'},
    }, ('uri',)),
    'plot_table': ({
        'uri': {'type': 'string'},
        'paths': {'type': 'array', 'items': {}},
        'columns': {'type': ['integer', 'null']},
        'plot_axis': {'type': ['string', 'null']},
    }, ('uri', 'paths')),
    'plot_stacked': ({
        'uri': {'type': 'string'},
        'paths': {'type': 'array', 'items': {}},
        'plot_axis': {'type': ['string', 'null']},
    }, ('uri', 'paths')),
    # The two reads of the equilibrium. `uri` and `occurrence` are common --
    # the group requires the first -- and the instant is not: a list of them
    # for the surfaces, one for the profiles under it. The group schema can
    # declare both and mean neither; these two rows say which takes which.
    'equilibrium_surfaces': ({
        'uri': {'type': 'string'},
        'times': {'type': ['array', 'null'], 'items': {'type': 'number'}},
        'occurrence': {'type': 'integer', 'default': 0},
    }, ('uri', 'times')),
    'equilibrium_at_time': ({
        'uri': {'type': 'string'},
        'time': {'type': ['number', 'null']},
        'occurrence': {'type': 'integer', 'default': 0},
    }, ('uri', 'time')),
    # The five operations of `transform_curve`. What they share is a figure
    # and the curve(s) of it; what sets them apart is the one number each
    # one asks for, which is why `factor` is required of "scale" and a
    # stranger on "reset".
    'scale_curve': ({
        'figure_key': {'type': 'string'},
        'factor': {'type': ['number', 'null']},
        'curve': {'type': ['string', 'integer', 'null']},
    }, ('figure_key', 'factor')),
    'shift_curve': ({
        'figure_key': {'type': 'string'},
        'offset': {'type': ['number', 'null']},
        'curve': {'type': ['string', 'integer', 'null']},
    }, ('figure_key', 'offset')),
    # `mode` is the name the gesture takes in Python for the reference it
    # divides by. Inside a group whose own word for the operation is
    # `operation`, a second word of that shape is the confusion the merge
    # was asked to end: the offer says `reference` and `ACTION_RENAMES`
    # below is where the two meet.
    'normalize_curve': ({
        'figure_key': {'type': 'string'},
        'reference': {'type': ['string', 'null'],
                      'enum': ['max', 'first', 'mean'],
                      'default': 'max'},
        'curve': {'type': ['string', 'integer', 'null']},
    }, ('figure_key',)),
    'reset_curve': ({
        'figure_key': {'type': 'string'},
        'curve': {'type': ['string', 'integer', 'null']},
    }, ('figure_key',)),
    'remove_curve': ({
        'figure_key': {'type': 'string'},
        'curve': {'type': ['string', 'integer', 'null']},
    }, ('figure_key',)),
    # The two reads of `read_figure`. They ask the same figure and the same
    # curve of it, and neither can do without the figure; what sets them
    # apart is what is done with the answer, so the two parameters the file
    # asks -- `format` and `name` -- are strangers on "stats", whose answer
    # is already on its way back.
    'curve_stats': ({
        'figure_key': {'type': 'string'},
        'curve': {'type': ['string', 'integer', 'null']},
    }, ('figure_key',)),
    'export_curve': ({
        'figure_key': {'type': 'string'},
        'curve': {'type': ['string', 'integer', 'null']},
        'format': {'type': 'string', 'enum': ['csv', 'json'],
                   'default': 'csv'},
        'name': {'type': ['string', 'null']},
    }, ('figure_key',)),
    # The five moves of `configure_axes`. Four of them ask the figure and
    # answer themselves; the fifth asks a row of a band, and that row is
    # the whole question -- hence an `axis` and an `index` required of
    # "slice_index" and strangers on every other operation. `x`/`y` are
    # spelled the same by "log" and "invert" because they answer the same
    # thing there: which of the two axes the move is made on.
    'set_axis_range': ({
        'figure_key': {'type': 'string'},
        'xmin': {'type': ['number', 'null']},
        'xmax': {'type': ['number', 'null']},
        'ymin': {'type': ['number', 'null']},
        'ymax': {'type': ['number', 'null']},
        'auto': {'type': ['boolean', 'null'], 'default': False},
    }, ('figure_key',)),
    'set_image_window': ({
        'figure_key': {'type': 'string'},
        'start': {'type': ['integer', 'null']},
        'count': {'type': ['integer', 'null']},
    }, ('figure_key',)),
    'set_slice_index': ({
        'figure_key': {'type': 'string'},
        'axis': {'type': ['string', 'null']},
        'index': {'type': ['integer', 'null']},
    }, ('figure_key', 'axis', 'index')),
    'set_log_scale': ({
        'figure_key': {'type': 'string'},
        'x': {'type': ['boolean', 'null']},
        'y': {'type': ['boolean', 'null']},
    }, ('figure_key',)),
    'invert_axis': ({
        'figure_key': {'type': 'string'},
        'x': {'type': ['boolean', 'null']},
        'y': {'type': ['boolean', 'null']},
    }, ('figure_key',)),
    # The five things one window of the session answers. Four of them are
    # made ON a window, and that window is the same word for all four even
    # though three of the gestures have always taken a `key` -- the rename
    # is `ACTION_RENAMES` below. "list" is the one that asks for nothing:
    # it answers every window the session holds. `width`/`height` belong to
    # "focus" alone, and "focus" is the one that can do without the window
    # itself: left out, it means the application.
    'list_windows': ({}, ()),
    'show_window': ({
        'window': {'type': 'string'},
    }, ('window',)),
    'hide_window': ({
        'window': {'type': 'string'},
    }, ('window',)),
    'close_window': ({
        'window': {'type': 'string'},
    }, ('window',)),
    'focus_window': ({
        'window': {'type': 'string'},
        'width': {'type': ['integer', 'null']},
        'height': {'type': ['integer', 'null']},
    }, ()),
    'plot_report': ({
        'figure_key': {'type': 'string'},
        'name': {'type': ['string', 'null']},
    }, ('figure_key',)),
    'case_report': ({
        'uri': {'type': 'string'},
        'name': {'type': ['string', 'null']},
    }, ('uri',)),
    'case_ids_report': ({
        'uri': {'type': 'string'},
        'name': {'type': ['string', 'null']},
    }, ('uri',)),
    # The notebook's eight asks. `scope` is WHICH JOURNAL the gesture runs
    # on, never which gesture is meant -- which is why this group answers
    # `action` and could not be merged under `scope` the reports are.
    'search_journals': ({
        'scope': {'type': ['string', 'null']},
        'query': {'type': ['string', 'null']},
        'limit': {'type': 'integer', 'default': 20},
        'machine': {'type': ['string', 'null']},
        'campaign': {'type': ['string', 'null']},
        'shot': {'type': ['string', 'null']},
        'date_from': {'type': ['string', 'null']},
        'date_to': {'type': ['string', 'null']},
        'author': {'type': ['string', 'null']},
    }, ()),
    'list_notes': ({
        'scope': {'type': ['string', 'null']},
        'machine': {'type': ['string', 'null']},
        'campaign': {'type': ['string', 'null']},
        'shot': {'type': ['string', 'null']},
        'date_from': {'type': ['string', 'null']},
        'date_to': {'type': ['string', 'null']},
        'author': {'type': ['string', 'null']},
    }, ()),
    'read_note': ({
        'scope': {'type': 'string'},
        'note_id': {'type': 'string'},
    }, ('scope', 'note_id')),
    'journal_stats': ({}, ()),
    'add_note': ({
        'scope': {'type': 'string'},
        'text': {'type': 'string'},
        'author': {'type': ['string', 'null']},
        'machine': {'type': ['string', 'null']},
        'campaign': {'type': ['string', 'null']},
        'shot': {'type': ['string', 'null']},
        'date': {'type': ['string', 'null']},
        'title': {'type': ['string', 'null']},
    }, ('scope', 'text')),
    'edit_note': ({
        'scope': {'type': 'string'},
        'note_id': {'type': 'string'},
        'text': {'type': ['string', 'null']},
        'author': {'type': ['string', 'null']},
        'machine': {'type': ['string', 'null']},
        'campaign': {'type': ['string', 'null']},
        'shot': {'type': ['string', 'null']},
        'date': {'type': ['string', 'null']},
        'title': {'type': ['string', 'null']},
    }, ('scope', 'note_id')),
    'delete_note': ({
        'scope': {'type': 'string'},
        'note_id': {'type': 'string'},
    }, ('scope', 'note_id')),
    'reindex_journals': ({
        'scope': {'type': ['string', 'null']},
    }, ()),
    # The six reads of one leaf's signal. `figure_key` is the parameter the
    # group is named for: four actions take it, for three different things
    # (mark them, take the marks off, put the picture on the page), which is
    # why its description on the offer spells which action means which.
    'detect_events': ({
        'uri': {'type': 'string'},
        'path': {'type': 'string'},
        'kind': {'type': 'string', 'enum': ['elm', 'sawtooth', 'lh']},
        'threshold': {'type': ['number', 'null']},
        'prominence': {'type': ['number', 'null']},
        'min_distance': {'type': ['integer', 'number', 'null']},
        'direction': {'type': ['string', 'null'],
                      'enum': ['up', 'down', 'both']},
        'hysteresis': {'type': ['number', 'null']},
        'along': {'type': ['string', 'null']},
        'indices': {'type': ['object', 'null']},
        'figure_key': {'type': ['string', 'null']},
    }, ('uri', 'path', 'kind')),
    'clear_event_marks': ({
        'figure_key': {'type': 'string'},
    }, ('figure_key',)),
    'events_report': ({
        'uri': {'type': 'string'},
        'path': {'type': 'string'},
        'kind': {'type': 'string', 'enum': ['elm', 'sawtooth', 'lh']},
        'threshold': {'type': ['number', 'null']},
        'prominence': {'type': ['number', 'null']},
        'min_distance': {'type': ['integer', 'number', 'null']},
        'direction': {'type': ['string', 'null'],
                      'enum': ['up', 'down', 'both']},
        'hysteresis': {'type': ['number', 'null']},
        'along': {'type': ['string', 'null']},
        'indices': {'type': ['object', 'null']},
        'figure_key': {'type': ['string', 'null']},
        'name': {'type': ['string', 'null']},
    }, ('uri', 'path', 'kind')),
    'spectrum': ({
        'uri': {'type': 'string'},
        'path': {'type': 'string'},
        'n_peaks': {'type': ['integer', 'null']},
        'band_low': {'type': ['number', 'null']},
        'band_high': {'type': ['number', 'null']},
        'along': {'type': ['string', 'null']},
        'indices': {'type': ['object', 'null']},
    }, ('uri', 'path')),
    'cross_correlation': ({
        'uri': {'type': 'string'},
        'path': {'type': 'string'},
        'path_b': {'type': 'string'},
        'along': {'type': ['string', 'null']},
        'indices': {'type': ['object', 'null']},
        'indices_b': {'type': ['object', 'null']},
    }, ('uri', 'path', 'path_b')),
    'spectrum_report': ({
        'uri': {'type': 'string'},
        'path': {'type': 'string'},
        'n_peaks': {'type': ['integer', 'null']},
        'band_low': {'type': ['number', 'null']},
        'band_high': {'type': ['number', 'null']},
        'along': {'type': ['string', 'null']},
        'indices': {'type': ['object', 'null']},
        'figure_key': {'type': ['string', 'null']},
        'name': {'type': ['string', 'null']},
    }, ('uri', 'path')),
    # The three numbers a case is judged on. `uri` is common to the three,
    # which is why the offer requires it; the leaves are not common, so each
    # member names the ones it cannot do without. Greenwald asks for all
    # three because it manufactures nothing and takes its numbers from the
    # case; the two that read a leaf settle on the one the case keeps for
    # them, which is why `path` is required of neither.
    'greenwald': ({
        'uri': {'type': 'string'},
        'n_e_path': {'type': 'string'},
        'ip_path': {'type': 'string'},
        'area_path': {'type': 'string'},
        'along': {'type': ['string', 'null']},
        'indices': {'type': ['object', 'null']},
        'indices_ip': {'type': ['object', 'null']},
        'indices_area': {'type': ['object', 'null']},
    }, ('uri', 'n_e_path', 'ip_path', 'area_path')),
    'beta_normal': ({
        'uri': {'type': 'string'},
        'path': {'type': ['string', 'null']},
        'along': {'type': ['string', 'null']},
        'indices': {'type': ['object', 'null']},
    }, ('uri',)),
    'total_pressure': ({
        'uri': {'type': 'string'},
        'path': {'type': ['string', 'null']},
        'along': {'type': ['string', 'null']},
        'indices': {'type': ['object', 'null']},
    }, ('uri',)),
    # A series of shots, one leaf at a time. Both asks take the shots and
    # the leaf -- the page runs the trend and dresses its answer -- so the
    # two rows differ by `name`, which only the page takes, and by nothing
    # they are asked to give.
    'campaign': ({
        'cases': {'type': 'array', 'items': {'type': 'string'},
                  'minItems': 2},
        'path': {'type': 'string'},
        'at': {'type': ['integer', 'string', 'null']},
        'which': {'type': ['string', 'null'],
                  'enum': ['mean', 'max', 'min']},
        'along': {'type': ['string', 'null']},
        'indices': {'type': ['object', 'null']},
    }, ('cases', 'path')),
    'campaign_report': ({
        'cases': {'type': 'array', 'items': {'type': 'string'},
                  'minItems': 2},
        'path': {'type': 'string'},
        'at': {'type': ['integer', 'string', 'null']},
        'which': {'type': ['string', 'null'],
                  'enum': ['mean', 'max', 'min']},
        'along': {'type': ['string', 'null']},
        'indices': {'type': ['object', 'null']},
        'name': {'type': ['string', 'null']},
    }, ('cases', 'path')),
    # The catalogue of prompts. `list` is the one ask that takes no `name`:
    # it is the ask that goes looking for one, so its row is the only one
    # with no required parameter, and `query` -- which no other action takes
    # -- is how it is narrowed.
    'list_prompts': ({
        'scope': {'type': ['string', 'null'], 'enum': ['personal',
                                                       'shared']},
        'category': {'type': ['string', 'null']},
        'query': {'type': ['string', 'null']},
        'limit': {'type': 'integer', 'default': 100},
    }, ()),
    'prompt_detail': ({
        'name': {'type': 'string'},
        'scope': {'type': ['string', 'null'], 'enum': ['personal',
                                                       'shared']},
    }, ('name',)),
    'fill_prompt': ({
        'name': {'type': 'string'},
        'values': {'type': ['object', 'null'],
                   'additionalProperties': {'type': 'string'}},
        'scope': {'type': ['string', 'null'], 'enum': ['personal',
                                                       'shared']},
    }, ('name',)),
    'save_prompt': ({
        'name': {'type': 'string'},
        'text': {'type': 'string'},
        'category': {'type': ['string', 'null']},
        'description': {'type': ['string', 'null']},
        'variables': {'type': ['object', 'string', 'null']},
        'scope': {'type': 'string', 'enum': ['personal', 'shared'],
                  'default': 'personal'},
        'prompt_id': {'type': ['string', 'null']},
    }, ('name', 'text')),
    'edit_prompt': ({
        'name': {'type': 'string'},
        'text': {'type': ['string', 'null']},
        'category': {'type': ['string', 'null']},
        'description': {'type': ['string', 'null']},
        'variables': {'type': ['object', 'string', 'null']},
        'scope': {'type': ['string', 'null'], 'enum': ['personal',
                                                       'shared']},
    }, ('name',)),
    'delete_prompt': ({
        'name': {'type': 'string'},
        'scope': {'type': ['string', 'null'], 'enum': ['personal',
                                                       'shared']},
    }, ('name',)),
    # The run kept and read back. Nothing here can be required of the group
    # itself: "save" needs no name (it settles on one of its own) and "new"
    # asks nothing, while "apply" and the two saves are nothing without
    # theirs. `name` is a SESSION file for the two session asks and a
    # CONFIGURATION file for the three that name one -- the one word the
    # offer keeps, since the action already says which of the two it is.
    'save_session': ({
        'name': {'type': ['string', 'null']},
        'path': {'type': ['string', 'null']},
    }, ()),
    'restore_session': ({
        'name': {'type': ['string', 'null']},
        'path': {'type': ['string', 'null']},
    }, ()),
    'new_session': ({}, ()),
    'list_sessions': ({}, ()),
    'list_configurations': ({
        'kind': {'type': ['string', 'null'], 'enum': ['plot', 'selection']},
    }, ()),
    'select_from_configuration': ({
        'uri': {'type': 'string'},
        'name': {'type': 'string'},
    }, ('uri', 'name')),
    'save_selection': ({
        'uri': {'type': 'string'},
        'name': {'type': 'string'},
    }, ('uri', 'name')),
    'save_plot_configuration': ({
        'uri': {'type': 'string'},
        'figure_key': {'type': 'string'},
        'name': {'type': 'string'},
    }, ('uri', 'figure_key', 'name')),
    # The documents corpus. Only "search" and "read" ask for a word of
    # their own: the corpus is one folder, so the three asks that walk it
    # need nothing, and `query` -- which no other action takes -- belongs
    # to the rank alone. `rel` is the spelling the answers already use for
    # a document, so the read asks a hit back with the word it came by.
    'list_documents': ({}, ()),
    'search_documents': ({
        'query': {'type': 'string'},
        'limit': {'type': ['integer', 'null']},
    }, ('query',)),
    'read_document': ({
        'rel': {'type': 'string'},
    }, ('rel',)),
    'reindex_documents': ({}, ()),
    'documents_stats': ({}, ()),
}

# The few names a merged group offers under a different spelling than the
# gesture's Python takes -- ``offered name -> spelled name``, per member.
# It exists for one reason: a group whose modes share an idea must name it
# with one word. ``plot`` asks for a ``path``, and the "slice" mode of that
# same tool was written against ``leaf``, a second word for the same leaf;
# leaving both in one schema is the confusion the merge was asked to remove.
#
# The rename happens once, on the way IN, after the call has been checked
# against the row above -- which is why that row is written in the offer's
# vocabulary: a refusal that named ``leaf`` would be naming a parameter the
# model was never told it may type.
ACTION_RENAMES = {
    'plot_slice': {'path': 'leaf'},
    'normalize_curve': {'reference': 'mode'},
    # The window one group names `window` while three of its gestures have
    # always taken `key`. It is the rename in the other direction from the
    # two above: there, the gesture was written before its group; here, the
    # group's word is the one the whole vocabulary already uses for a window
    # -- `get_screenshot` asks for a `window`, and a group that answered
    # `key` beside it would be one idea with two words again.
    'show_window': {'window': 'key'},
    'hide_window': {'window': 'key'},
    'close_window': {'window': 'key'},
}


def argumentsForMember(member, args):
    """The arguments of a call, spelled the way the gesture's Python takes
    them.

    A merged group is offered one vocabulary and the core was written in
    another; ``ACTION_RENAMES`` is the seam between the two, and this is the
    one place it is applied -- after the parameter checks, before the call.
    A member with no row there is handed its arguments unchanged.
    """
    renames = ACTION_RENAMES.get(member)
    out = dict(args or {})
    if not renames:
        return out
    for offered, spelled in renames.items():
        if offered in out:
            out[spelled] = out.pop(offered)
    return out


def parametersOf(name):
    """The parameters a gesture takes: its own row when its group is merged,
    its own schema while it is offered on its own. Empty for a name that is
    neither."""
    row = ACTION_PARAMETERS.get(name)
    if row is not None:
        return {'properties': row[0], 'required': list(row[1])}
    return TOOL_PARAMETERS.get(name, {})


_FAMILY_OF_TOOL = {name: label
                   for label, members, _offers in FAMILIES
                   for name in members}

_FAMILY_MEMBERS = {label: members
                   for label, members, _offers in FAMILIES}


def offeredNames():
    """Every name the groups answer: merged groups one, the rest member by
    member. ``TOOLS`` is still what the loop is offered; this is what it
    would be offered once every group is spelled under one name."""
    return tuple(name for name in _OFFERS)


def memberNames():
    """Every gesture, merged or not -- the vocabulary the guards and the
    loop's own account speak, and the one a journal line or a saved prompt
    may still quote after its group is merged."""
    return tuple(name for _label, members, _offers in FAMILIES
                 for name in members)


def isOfferName(name):
    """Whether ``name`` is a group answering one name, rather than a tool."""
    return name in _OFFERS and _OFFERS[name][1] is not None


def actionsOf(name):
    """The actions a group's name answers, in the order the table spells
    them. Empty for a tool and for a name that is not a group's."""
    offer = _OFFERS.get(name)
    return () if offer is None else offer[3]


def discriminatorOf(name):
    """The parameter that says which gesture a group's name is asked for
    (``mode`` for ``plot``, ``scope`` for ``generate_report``), and None for
    a name that answers itself.

    Two things hinge on it. A model told "``scope`` is missing" has to be
    told the name of the thing missing, and a group whose discriminant
    shares a name with a parameter one of its own members takes is a group
    where one word answers two questions -- which is why the journals group
    is merged under ``action`` and never under ``scope``, that group's
    ``add_note`` already taking a ``scope`` of its own."""
    offer = _OFFERS.get(name)
    return None if offer is None else offer[1]


def familyOf(name):
    """The group a tool belongs to, and None for a name that is not one."""
    return _FAMILY_OF_TOOL.get(name)


def membersOf(label):
    """The gestures of the group spelled ``label``, in the order the table
    holds them."""
    return _FAMILY_MEMBERS[label]


def callSpellings(label):
    """The spelled calls of a whole group, in its order -- the shape the
    loop's re-anchor text wears when it tells the model what to answer with
    (``plot_report(figure_key) / case_report(uri)`` before the merge,
    ``generate_report(scope="plot", figure_key) / ...`` after it). Spelled
    from the table so a merge cannot leave an instruction naming a name the
    model is no longer offered."""
    return ' / '.join(callSpelling(member) for member in membersOf(label))


def siblingTaking(name, parameter):
    """The other tools of ``name``'s group that do take ``parameter``.

    Empty when the group has none -- the parameter is then one the model
    invented, and the refusal must not send it off to a tool that does not
    take it either. Empty for a name that is not a tool, and for a parameter
    the tool itself takes: asking why ``get_signal`` takes ``time_index``
    would be answering nothing.
    """
    label = _FAMILY_OF_TOOL.get(name)
    if label is None:
        return []
    if parameter in parametersOf(name).get('properties', {}):
        return []
    return [other for other in _FAMILY_MEMBERS[label]
            if other != name
            and parameter in parametersOf(other).get('properties', {})]


def unknownParameterRefusal(name, unknown):
    """The loop's words for an argument the tool does not take.

    ``unknown`` is what ``unknownParameters`` answered; the first name is
    the one put on trial. The refusal names the stray and the parameters
    that are -- a Python ``TypeError`` says "unexpected keyword argument",
    which does not tell the model what to answer with -- and then, when a
    neighbour in the same group takes the stray, names that neighbour:
    ``columns`` put on a single quantity's call is a table asked that way,
    and the short way back is the call that takes it.

    Both sides of that sentence are spelled as the model may type them
    (``offerHead``): a refusal that names ``plot_table`` names a name that
    is not on the menu, and a model told to ask it will be refused for
    asking it.
    """
    schema = parametersOf(name)
    allowed = sorted(schema.get('properties', {}))
    if allowed:
        text = ('"%s" is not a parameter of the %s call: it takes %s. '
                'Answer with the parameters the call names.'
                % (unknown[0], offerHead(name), ', '.join(allowed)))
    else:
        text = ('"%s" is not a parameter of the %s call, which takes no '
                'parameter at all. Answer with no arguments.'
                % (unknown[0], offerHead(name)))
    siblings = siblingTaking(name, unknown[0])
    if siblings:
        spelled = [offerHead(sibling) for sibling in siblings]
        if len(spelled) == 1:
            text += (' "%s" is a parameter of %s: ask that call if that is '
                     'the gesture you mean.' % (unknown[0], spelled[0]))
        else:
            text += (' "%s" is a parameter of %s: ask one of those if that '
                     'is the gesture you mean.'
                     % (unknown[0], ', '.join(spelled)))
    return text


def unknownParameters(name, args):
    """The names in ``args`` that the tool ``name`` does not take.

    Every tool in ``TOOLS`` declares ``additionalProperties: false`` and
    lists the names it does take in ``parameters.properties``. An
    argument whose name is not in that list is one the model invented --
    ``time_index`` on ``plot(mode="single")`` is the one measured -- the loop
    must refuse it by naming the parameter that is not there and the ones
    that are, instead of letting Python's ``TypeError`` (``unexpected
    keyword argument``) speak for it. An unknown tool name, or a tool that
    admits extra parameters, answers an empty list.

    Asked with a MERGED member, it is that member's row that decides, not
    the group's offered schema: the group has to declare every action's
    names, so ``uri`` is a legal name for ``generate_report`` and a stray
    for ``scope="plot"``.
    """
    if name not in TOOL_PARAMETERS and name not in ACTION_PARAMETERS:
        return []
    schema = parametersOf(name)
    if schema.get('additionalProperties', False):
        return []
    allowed = set(schema.get('properties', {}))
    return sorted(set(args or {}) - allowed)


_OFFERED_NAMES = frozenset(tool['function']['name'] for tool in TOOLS)


def offerHead(member):
    """The name a model may TYPE to ask for ``member``, with no parameters.

    The half of ``callSpelling`` a refusal needs when it is naming the call
    rather than telling the model what to answer with: a refusal that names
    ``plot_table`` is naming a name that is not on the menu, and the model
    cannot act on it -- it has to be told the name it does have,
    ``plot(mode="table")``. A gesture whose group is not merged is answered
    by its own name, which IS the offer.
    """
    offer = _OFFER_OF_MEMBER.get(member)
    if (offer is not None and offer[0] in _OFFERED_NAMES
            and _OFFERS[offer[0]][1] is not None):
        name, action, _label = offer
        return '%s(%s="%s")' % (name, _OFFERS[name][1], action)
    return member


def callSpelling(member):
    """How a call that answers ``member`` is spelled to a model.

    Two vocabularies live in this application now, and only one of them is
    in front of the model: a guard decides on the member's name, a model can
    only act on a name it was offered. So the prose that INSTRUCTS -- what a
    re-anchor asks the model to answer with -- is spelled from the table:
    the member's own name while its group is offered member by member
    (``plot_report(figure_key)``, exactly what this file's refusals said by
    hand before the table existed), and the group's name with the action
    that means this member once it is merged
    (``generate_report(scope="plot", figure_key)``). Required parameters
    follow, in the order the schema spells them.
    """
    schema = parametersOf(member)
    params = list(schema.get('required', ()))
    offer = _OFFER_OF_MEMBER.get(member)
    if (offer is not None and offer[0] in _OFFERED_NAMES
            and _OFFERS[offer[0]][1] is not None):
        name, action, _label = offer
        params.insert(0, '%s="%s"' % (_OFFERS[name][1], action))
        return '%s(%s)' % (name, ', '.join(params))
    return '%s(%s)' % (member, ', '.join(params))


def _actionRefusal(name, discriminator, order, value):
    choices = ', '.join('"%s"' % action for action in order)
    if value is None:
        return ('the %s tool answers no gesture without a %s: answer with %s '
                'among %s.' % (name, discriminator, discriminator, choices))
    spelled = {member: action
               for action, member in _OFFERS[name][2].items()}
    if value in spelled:
        return ('"%s" is the gesture the %s tool answers, not a %s it takes: '
                'answer with %s="%s".'
                % (value, name, discriminator, discriminator, spelled[value]))
    return ('"%s" is not a %s the %s tool answers: it answers %s. Answer with '
            'one of those.' % (value, discriminator, name, choices))


def resolveCall(name, args):
    """The gesture a call answers, and the arguments that gesture takes.

    The one seam between what the model is offered and what the session
    runs. A tool name answers itself; a merged group's name answers the
    member its discriminator names, and the discriminator is taken out of
    the arguments on the way -- so everything that DECIDES is asked about
    the MEMBER: the core lookup, the parameter check, the destructive and
    journal guards, the sets a turn keeps of what it did. What the model
    READS back (the transcript, ``last_action``, the tool message) is left
    at the offered spelling by the caller, which is the other half of the
    same rule: see the header of ``FAMILIES``.

    A member whose group is offered under one name is refused rather than
    run: the coup is clean, and the refusal names the call that took its
    place. A name that is neither a tool nor a group answers itself, so the
    loop's own "not a gesture of this session" keeps speaking for it.

    The action is refused by naming the actions and, when the model put a
    member's name where the action belongs, by naming the action that means
    it: ``generate_report(scope="plot_report")`` is one word from standing.
    """
    args = dict(args or {})
    offer = _OFFERS.get(name)
    if (offer is not None and offer[1] is not None
            and name in _OFFERED_NAMES):
        _label, discriminator, actions, order = offer
        value = args.get(discriminator)
        if value not in actions:
            raise ValueError(_actionRefusal(name, discriminator, order, value))
        args.pop(discriminator)
        return actions[value], args
    if name in _OFFERED_NAMES:
        return name, args
    merged = _OFFER_OF_MEMBER.get(name)
    if merged is not None and merged[0] in _OFFERED_NAMES:
        raise ValueError('the %s tool is no longer offered on its own: ask '
                         '%s.' % (name, callSpelling(name)))
    return name, args


def gestureOf(name, args):
    """Which gesture a call answers, without checking anything.

    The pure sibling of ``resolveCall``, for the bookkeeping a turn keeps
    *after* the call ran -- which report wrote a file, which figure a close
    took away, which note a journal line stands on, which figure a turn
    worked on. Those are asked about gestures, and a merged group's name is
    not a gesture: ``generate_report(scope="plot")`` grounded a
    ``plot_report``, and a guard that read the call as ``generate_report``
    would refuse an honest answer about a file that stands on disk.

    Nothing is refused here, and no argument is touched: a bad action
    answers its own name, because ``resolveCall`` already refused the call
    before this could be asked of it.
    """
    offer = _OFFERS.get(name)
    if offer is None or offer[1] is None:
        return name
    member = offer[2].get((args or {}).get(offer[1]))
    return member or name


def missingParameters(name, args):
    """The parameters the tool requires and the call left out.

    The mirror of ``unknownParameters``, and the one the merge makes
    necessary: a merged schema can only list what every action needs, so
    ``generate_report(uri)`` is a legal-looking call that would reach
    Python as a ``TypeError`` about a missing positional argument. It is
    refused naming the call that is missing what.

    A MERGED member is measured against its own row for the same reason:
    the group's schema requires only what every action needs, so the
    group's ``required`` list can never say that ``scope="plot"`` without
    a ``figure_key`` is an incomplete call.
    """
    if name not in TOOL_PARAMETERS and name not in ACTION_PARAMETERS:
        return []
    schema = parametersOf(name)
    return sorted(set(schema.get('required', ())) - set(args or {}))


def missingParameterRefusal(name, missing):
    """The words for an incomplete call, spelled as the model may type it.

    ``name`` is the gesture that would have run; ``offerHead`` is what the
    model has to answer with, because a merged gesture's own name is not
    something it can call.
    """
    return ('%s needs %s, and the call left it out: answer with %s.'
            % (offerHead(name), ' and '.join(missing), callSpelling(name)))
