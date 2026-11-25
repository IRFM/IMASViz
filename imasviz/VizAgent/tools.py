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
1. `open_case(uri)` -> Open the shot.
2. `list_case_idss(uri)` -> Check which IDSs and occurrences actually exist in the case.
3. `load_ids(uri, ids_name, occurrence)` -> Load the required IDS into the tree.
4. `search_nodes(uri, query)` or `list_quantities(uri, ids_name)` -> Find exact leaf paths.
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
- **WINDOWS & FOCUS:** Do NOT call `focus_window` or `show_window` automatically after plotting. Only call them if the user explicitly asks to bring a window to the front.
- **DESTRUCTIVE & SHARED ACTIONS:** Never call `close_window`, `close_case`, `new_session`, or write to `scope="shared"` (journals/prompts) unless the user explicitly asks for it in their prompt.
- **AMBIGUITY:** If a user request is ambiguous (e.g., "sonde 2" when multiple probes exist), list the exact paths found by `search_nodes` and ask the user to choose.

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
    _tool(
        'open_case',
        'Open one IMAS case by URI (imas:hdf5?path=..., or an UDA URI). '
        '`dd_version` pins the data dictionary the case is read at; left '
        'out, the case is asked which one its own IDSs were written with.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string',
                    'description': 'The case URI, e.g. imas:hdf5?path=...'},
            'dd_version': {'type': ['string', 'null'],
                           'description': 'Data dictionary version pin'},
        }, 'required': ['uri'], 'additionalProperties': False},
    ),
    _tool(
        'list_cases',
        'The cases open in this session, with their loaded occurrences.',
        {'type': 'object', 'properties': {}, 'additionalProperties': False},
    ),
    _tool(
        'close_case',
        'Close one open case: its view, its windows, its bookkeeping.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
        }, 'required': ['uri'], 'additionalProperties': False},
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
    _tool(
        'search_nodes',
        'The leaves of the case, matched by a substring of their spellings. '
        '`query` is a case-insensitive substring; `ids_name` narrows to one '
        'IDS. The answer holds the three spellings of every match.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'query': {'type': 'string', 'default': ''},
            'ids_name': {'type': ['string', 'null']},
            'limit': {'type': 'integer', 'default': 200},
        }, 'required': ['uri'], 'additionalProperties': False},
    ),
    _tool(
        'select_signals',
        'Put the named paths into the case selection, as clicks would. '
        'A path the tree does not hold is refused by name. '
        '`additive=False` clears the selection first.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'paths': {'type': 'array', 'items': {}},
            'additive': {'type': 'boolean', 'default': True},
        }, 'required': ['uri', 'paths'], 'additionalProperties': False},
    ),
    _tool(
        'unselect_all',
        'Empty the case selection; the answer says how many were dropped.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
        }, 'required': ['uri'], 'additionalProperties': False},
    ),
    _tool(
        'list_selection',
        'The current selection of the case, in the order it was put in: '
        'the path, the data name, the IDS and the occurrence of each. '
        'Empty is an answer, count 0 -- not a refusal.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
        }, 'required': ['uri'], 'additionalProperties': False},
    ),
    _tool(
        'describe_node',
        'What this node holds, as the application documentation says it: '
        'dictionary documentation and units, and for an array the size, '
        'shape, the finite minimum and maximum, the counts of zeros, nan and '
        'inf entries, and a bounded preview of the values. A leaf the tree '
        'does not hold is refused by name.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'path': {'type': 'string'},
        }, 'required': ['uri', 'path'], 'additionalProperties': False},
    ),
    _tool(
        'describe_ids',
        'What the data dictionary says about an IDS: its comment '
        '(ids_properties.comment), whether it is written with homogeneous '
        'time (ids_properties.homogeneous_time), its units, time units, and '
        'the data dictionary version the case was written at. The answer '
        'holds only the fields the case fills; a property the case leaves '
        'empty is absent, not invented. An IDS the case does not declare is '
        'refused by name, naming the ones it does.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'ids_name': {'type': 'string'},
            'occurrence': {'type': 'integer', 'default': 0},
        }, 'required': ['uri', 'ids_name'], 'additionalProperties': False},
    ),
    _tool(
        'list_quantities',
        'The filled tensors (dimension >= 1) of one occurrence, grouped by '
        'the array of structures that drives them: one entry per quantity '
        '(its path, data name, parametrized path, units, data type, and how '
        'many elements of its array the case holds). A quantity that '
        'contains no data -- not blue in the tree -- is not listed, and '
        'scalar leaves (0D) are not tensors and are not listed either. This '
        'is the "what can be drawn" answer for one occurrence. An occurrence '
        'whose tree was never built is refused by name: load it with '
        'load_ids first.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'ids_name': {'type': 'string'},
            'occurrence': {'type': 'integer', 'default': 0},
        }, 'required': ['uri', 'ids_name'], 'additionalProperties': False},
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
        'selection holds (`select_signals` first). "table" lays one panel '
        'per `paths` in a Table Plot View. "stacked" stacks `paths`, one '
        'panel per quantity, in one window. The answer carries the figure '
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
    _tool(
        'equilibrium_surfaces',
        'The flux surfaces of the equilibrium, one frame per named instant, '
        'side by side in one window (the Equilibrium plugin\'s reading of '
        'the equilibrium IDS: the psi levels, the plasma boundary, the '
        'magnetic axis, the O-point, the limiter, at equal bounds). '
        '`times` is the list of instants in seconds, e.g. [40, 44, 48]; '
        'each answers the nearest slice the case holds, named back '
        '(time_requested vs time_slice_time). Use it when the user asks '
        'to compare the equilibrium at several instants, or to trace the '
        'flux surfaces (surfaces de flux). It is what the '
        '`equilibriumsurfaces` plugin entry 0 answers with: this tool opens '
        'a window of its own every time, so asking it AND that entry leaves '
        'two windows of the same row. Ask one.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'times': {'type': 'array', 'items': {'type': 'number'},
                      'description': 'instants in the case clock, seconds'},
            'occurrence': {'type': 'integer', 'default': 0},
        }, 'required': ['uri', 'times'], 'additionalProperties': False},
    ),
    _tool(
        'equilibrium_at_time',
        'One instant of the equilibrium, the way the Equilibrium plugin '
        'reads it: the flux surface at the instant with the radial '
        'profiles under it (q, elongation, triangularities, j_tor [MA/m^2], '
        'pressure [kPa], f_df_dpsi, dpressure_dpsi, on rho_tor_norm), and '
        'the global quantities of the slice (Ip [kA], q95, q_axis, li_3, '
        'W_mhd [kJ], axis position) in the answer. `time` is the instant '
        'in seconds; it answers the nearest slice the case holds, named '
        'back as time_slice_time. Use it when the user names one instant '
        'of the equilibrium ("l\'équilibre à 44 s", "q et pression à '
        'cet instant"). It is what the `equilibriumsurfaces` plugin entry '
        '1 answers with: asking that entry through `run_plugin` AND this '
        'tool opens two windows of the same instant, so ask one.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'time': {'type': 'number',
                     'description': 'the instant in seconds'},
            'occurrence': {'type': 'integer', 'default': 0},
        }, 'required': ['uri', 'time'], 'additionalProperties': False},
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
        'out for every curve. curve_stats and export_curve then read the '
        'transformed value; the quantity in the tree is unchanged. A table '
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
    _tool(
        'set_axis_range',
        'The window (the range) of a figure\'s axes, by name and number: '
        'pin `xmin`/`xmax` together, `ymin`/`ymax` together, or both; '
        '`auto=true` clears the pins and re-fits. A curve figure takes one '
        'axis set; a picture window takes the same span on each of its '
        'pictures, and a time zoom of a strip whose abscissa is its time '
        'is the `x` range, in the seconds the time axis holds. A partial '
        'pair is refused (a range is two bounds); a table or stacked '
        'window is refused by name.',
        {'type': 'object', 'properties': {
            'figure_key': {'type': 'string'},
            'xmin': {'type': ['number', 'null']},
            'xmax': {'type': ['number', 'null']},
            'ymin': {'type': ['number', 'null']},
            'ymax': {'type': ['number', 'null']},
            'auto': {'type': 'boolean', 'default': False},
        }, 'required': ['figure_key'], 'additionalProperties': False},
    ),
    _tool(
        'set_image_window',
        'The window a picture window\'s pictures sit on: moved with '
        '`start` (where it sits on the axis it reads across; the pictures '
        'are re-read in place, the scale and the band stay put) and resized '
        'with `count` (how many pictures it holds; the scale a hand settled '
        'is not moved off by the rebuild). Name at least one. The answer '
        'carries the axis, the start, the count, the extent the axis '
        'holds and the label of each picture the window shows, the time it '
        'is in seconds when the axis is the time. Refused by name: a window '
        'that is not a picture window (the shape it holds, named), a '
        'picture window that holds one picture, not a window of them (the '
        'span of that one is set_axis_range), and an ask that names '
        'neither bound.',
        {'type': 'object', 'properties': {
            'figure_key': {'type': 'string'},
            'start': {'type': ['integer', 'null'],
                      'description': 'where the window sits on the axis '
                                     'it reads across (0-based element)'},
            'count': {'type': ['integer', 'null'],
                      'description': 'how many pictures the window '
                                     'holds (1 up to the extent of '
                                     'the axis)'},
        }, 'required': ['figure_key'], 'additionalProperties': False},
    ),
    _tool(
        'set_slice_index',
        'A row of the slider band of a figure, posed at a named index: '
        '`axis` the row in the words the band spells it (an array of '
        'structures by its name -- `time_slice`, `profiles_2d` -- or the '
        'coordinate it carries), `index` the element it is posed at. The '
        'window re-reads the one the row is posed at, the other rows of '
        'the band stay where they are; the answer carries the rows of the '
        'band, the index the one moved is posed at and its extent. It '
        'addresses a curve figure that pins an axis and an image window '
        'that does; a table and a stacked window are refused by name, and '
        'so is a row the band does not hold (the rows it does, named), and '
        'an index past the extent the row holds (the bound it holds, '
        'named). A picture window whose pictures sit on the axis the '
        'gesture names holds no row for it, and the refusal names '
        'set_image_window (start and count of that window) as the '
        'gesture that answers the question the ask is asking.',
        {'type': 'object', 'properties': {
            'figure_key': {'type': 'string'},
            'axis': {'type': 'string'},
            'index': {'type': 'integer'},
        }, 'required': ['figure_key', 'axis', 'index'],
         'additionalProperties': False},
    ),
    _tool(
        'set_log_scale',
        'A log axis, by name: `x`/`y` each `true` for log, `false` for '
        'linear; name at least one. A log turned on where the values cross '
        'zero or below is refused by name (the picture would hide them); '
        'transform_curve(operation="shift") to clear them is the answer.',
        {'type': 'object', 'properties': {
            'figure_key': {'type': 'string'},
            'x': {'type': ['boolean', 'null']},
            'y': {'type': ['boolean', 'null']},
        }, 'required': ['figure_key'], 'additionalProperties': False},
    ),
    _tool(
        'invert_axis',
        'Invert (flip) an axis: `x=true`/`y=true` turn one around so the '
        'negative direction is the other way; `false` puts it back. Name at '
        'least one. Inversion and range are independent.',
        {'type': 'object', 'properties': {
            'figure_key': {'type': 'string'},
            'x': {'type': ['boolean', 'null']},
            'y': {'type': ['boolean', 'null']},
        }, 'required': ['figure_key'], 'additionalProperties': False},
    ),
    _tool(
        'curve_stats',
        'The numbers of a figure\'s drawn curve(s): sample count, finite '
        'min/max/mean/std of the values, the nan/inf counts, and the peak '
        'value with its abscissa. The read of a figure before or after a '
        'scale/shift/normalize; generate_report(scope="plot") is the same '
        'read with an HTML file on disk.',
        {'type': 'object', 'properties': {
            'figure_key': {'type': 'string'},
            'curve': {'type': ['string', 'integer', 'null']},
        }, 'required': ['figure_key'], 'additionalProperties': False},
    ),

    _tool(
        'detect_events',
        'The events of one kind, read off the leaf\'s signal: \'elm\' '
        '(an excursion up), \'sawtooth\' (a crash down), or \'lh\' (a '
        'threshold crossing). The signal is the one get_signal answers for '
        'the leaf, so what is detected and what a figure of the same leaf '
        'draws are the same read. ELM/sawtooth are gated by threshold '
        '(value floor), prominence, min_distance; lh by threshold, direction '
        '(up/down/both), hysteresis -- a kind refuses a parameter it does '
        'not take, by name. `figure_key` marks the events on that curve '
        'figure (capped at 40, refused when it would be a wall).',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'path': {'type': 'string'},
            'kind': {'type': 'string',
                     'enum': ['elm', 'sawtooth', 'lh']},
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
            'along': {'type': ['string', 'null']},
            'indices': {'type': ['object', 'null'],
                        'description': 'each other axis fixed by name, '
                                       'the way plot and get_signal do.'},
            'figure_key': {'type': ['string', 'null'],
                           'description': 'mark the events on this curve '
                                          'figure.'},
        }, 'required': ['uri', 'path', 'kind'],
           'additionalProperties': False},
    ),
    _tool(
        'clear_event_marks',
        'The event marks off a curve figure, one detect_events put there. '
        'Safe when the figure holds none: it answers the number it took '
        'off.',
        {'type': 'object', 'properties': {
            'figure_key': {'type': 'string'},
        }, 'required': ['figure_key'], 'additionalProperties': False},
    ),
    _tool(
        'events_report',
        'The events of one kind as a self-contained HTML report: the same '
        'read and detection as detect_events, the events in a table, the '
        'period of their times, and the figure when one is named. Lands in '
        '~/.imasviz/reports like the other reports; a name that names a '
        'place is refused by name.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'path': {'type': 'string'},
            'kind': {'type': 'string',
                     'enum': ['elm', 'sawtooth', 'lh']},
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
        }, 'required': ['uri', 'path', 'kind'],
           'additionalProperties': False},
    ),

    _tool(
        'spectrum',
        'What a leaf\'s time series oscillates at: the dominant frequency '
        'and its period, the leading peaks (most power first) with their '
        'power and share, and -- when a band is named -- the share of the '
        'power between its two bounds. The read is the one get_signal answers '
        'for the leaf, so the frequency read is the one a figure of the same '
        'leaf draws. A flat or too-short series is refused by name.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'path': {'type': 'string'},
            'n_peaks': {'type': ['integer', 'null'],
                        'description': 'how many leading peaks come back; '
                                       'five when left out.'},
            'band_low': {'type': ['number', 'null'],
                         'description': 'lower bound of the band, in Hz.'},
            'band_high': {'type': ['number', 'null'],
                          'description': 'upper bound of the band, in Hz.'},
            'along': {'type': ['string', 'null']},
            'indices': {'type': ['object', 'null'],
                        'description': 'each other axis fixed by name, '
                                       'the way plot and get_signal do.'},
        }, 'required': ['uri', 'path'],
           'additionalProperties': False},
    ),
    _tool(
        'cross_correlation',
        'How far one leaf\'s time series lags or leads another, and at what '
        'the two oscillate together. Both reads are the ones a figure draws '
        'for the two leaves, so a pair the case does not hold on one clock, '
        'or at one length, is refused by name. Answers the lag in samples '
        'and in time, the correlation of the peak, and the shared '
        'dominant frequency.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'path': {'type': 'string',
                     'description': 'the first series.'},
            'path_b': {'type': 'string',
                       'description': 'the second series, lagged against '
                                      'the first.'},
            'along': {'type': ['string', 'null']},
            'indices': {'type': ['object', 'null']},
            'indices_b': {'type': ['object', 'null'],
                          'description': 'the element of the second series '
                                         'fixed by name.'},
        }, 'required': ['uri', 'path', 'path_b'],
           'additionalProperties': False},
    ),
    _tool(
        'spectrum_report',
        'The spectral facts of a leaf\'s time series as a self-contained '
        'HTML report: the same read and spectrum as spectrum, the leading '
        'peaks in a table, the band when one is named, and the figure when a '
        'curve figure is named. Lands in ~/.imasviz/reports like the other '
        'reports; a name that names a place is refused by name.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'path': {'type': 'string'},
            'n_peaks': {'type': ['integer', 'null']},
            'band_low': {'type': ['number', 'null']},
            'band_high': {'type': ['number', 'null']},
            'along': {'type': ['string', 'null']},
            'indices': {'type': ['object', 'null']},
            'figure_key': {'type': ['string', 'null'],
                           'description': 'put the picture of this curve '
                                          'figure on the page.'},
            'name': {'type': ['string', 'null']},
        }, 'required': ['uri', 'path'],
           'additionalProperties': False},
    ),

    _tool(
        'greenwald',
        'The Greenwald fraction of a case, over the time the three read. '
        'f_G = n_e / n_G, with n_G = (I_pl / A) x 1e20 (I_pl in mega-Ampere, '
        'A in square metre). The three leaves -- n_e (m^-3), I_pl (A), A (m^2) '
        '-- are named by the caller, so the formula and the numbers come from '
        'the case, not from this method. A case that does not hold one, or '
        'holds the three at different lengths, is refused by name.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'n_e_path': {'type': 'string',
                         'description': 'the electron density, in m^-3, '
                                        'over time.'},
            'ip_path': {'type': 'string',
                        'description': 'the plasma current, in A, over time.'},
            'area_path': {'type': 'string',
                          'description': 'the cross-section, in m^2, over '
                                         'time.'},
            'along': {'type': ['string', 'null']},
            'indices': {'type': ['object', 'null'],
                        'description': 'the element of the density series '
                                       'fixed by name.'},
            'indices_ip': {'type': ['object', 'null'],
                           'description': 'the element of the current '
                                          'series fixed by name.'},
            'indices_area': {'type': ['object', 'null'],
                             'description': 'the element of the area series '
                                            'fixed by name.'},
        }, 'required': ['uri', 'n_e_path', 'ip_path', 'area_path'],
           'additionalProperties': False},
    ),

    _tool(
        'beta_normal',
        'The normalized beta beta_N = 2 mu_0 p / (B^2 a^2 / I_pl^-2) of a '
        'case, over the time the case holds it. The value is the case\'s own '
        'number read off its leaf (`beta_normal`), not one computed here. '
        'The answer carries the path that named it, the values, the points '
        'and the mean, max and min. `path`, `along` and `indices` are the '
        'seams the case keeps. A case that does not hold the leaf is '
        'refused by name, never a plausible-looking value.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'path': {'type': ['string', 'null'],
                     'description': 'the beta leaf. Defaults to the one the '
                                    'equilibrium case keeps '
                                    '(global_quantities.beta_normal).'},
            'along': {'type': ['string', 'null'],
                      'description': 'the axis of the node, for an array that '
                                     'has one; the clock (equilibrium.time) '
                                     'where it holds one.'},
            'indices': {'type': ['object', 'null'],
                        'description': 'the element of the node, for a node '
                                       'of one.'},
        }, 'required': ['uri'], 'additionalProperties': False},
    ),

    _tool(
        'total_pressure',
        'The total pressure p = n_e k_B T_e + n_i k_B T_i of a case, read off '
        'the leaf the case holds for it. The answer names the path that read '
        'it, the values, the points and the mean, max and min. `path`, '
        '`along` and `indices` are the seams the case keeps. A case that does '
        'not hold the leaf is refused by name, never a plausible-looking '
        'profile.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'path': {'type': ['string', 'null'],
                     'description': 'the pressure leaf. Defaults to the total '
                                    'the equilibrium case keeps '
                                    '(profiles_1d.pressure).'},
            'along': {'type': ['string', 'null']},
            'indices': {'type': ['object', 'null']},
        }, 'required': ['uri'], 'additionalProperties': False},
    ),

    _tool(
        'campaign',
        'The trend of one leaf across a series of shots, in campaign order. '
        'The same leaf is read from each shot (the read a figure of that leaf '
        'would draw), one value is taken per shot (at a named index of the '
        'curve, or mean/max/min over it), and the trend over the shots '
        'comes out: the per-shot values, the least-squares slope over the '
        'shot index, first-to-last change, min and max with the shots they '
        'came from, and the direction. A campaign of one shot, a shot the '
        'case does not hold the leaf in, or a campaign of all-equal values '
        'refuses in words -- each in the words that mean it.',
        {'type': 'object', 'properties': {
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
                                     'shot answers; name either this or `at`.'},
            'along': {'type': ['string', 'null']},
            'indices': {'type': ['object', 'null']},
        }, 'required': ['cases', 'path'], 'additionalProperties': False},
    ),

    _tool(
        'campaign_report',
        'The campaign answer as a self-contained HTML page: the per-shot '
        'table, the trend, and the line the shot values make across the '
        'shots. The same read and the same `campaign` the facts run on -- '
        'nothing is remembered from memory -- and the file lands under '
        '~/.imasviz/reports like the other reports.',
        {'type': 'object', 'properties': {
            'cases': {'type': 'array',
                      'items': {'type': 'string'},
                      'minItems': 2},
            'path': {'type': 'string'},
            'at': {'type': ['integer', 'string', 'null']},
            'which': {'type': ['string', 'null'],
                      'enum': ['mean', 'max', 'min']},
            'along': {'type': ['string', 'null']},
            'indices': {'type': ['object', 'null']},
            'name': {'type': ['string', 'null'],
                     'description': 'the report name, without the .html. '
                                    'Refused when it names a place.'},
        }, 'required': ['cases', 'path'], 'additionalProperties': False},
    ),

    _tool(
        'export_curve',
        'Take a figure\'s drawn curve(s) out to a file: the values as they '
        'stand (a scale/shift/normalize is in the file). `format` csv or '
        'json; `curve` a name, an index, or left out. The file lands in '
        '~/.imasviz/exports; a `name` that names a place is refused by '
        'name.',
        {'type': 'object', 'properties': {
            'figure_key': {'type': 'string'},
            'curve': {'type': ['string', 'integer', 'null']},
            'format': {'type': 'string', 'enum': ['csv', 'json'],
                      'default': 'csv'},
            'name': {'type': ['string', 'null']},
        }, 'required': ['figure_key'], 'additionalProperties': False},
    ),

    _tool(
        'list_windows',
        'Every window of the session, in the order the menus draw them. '
        'Each with its kind, label, key, and whether it is on screen.',
        {'type': 'object', 'properties': {}, 'additionalProperties': False},
    ),
    _tool(
        'show_window',
        'The user\'s "remets Plot1 à l\'écran" command: put a window '
        'back on the screen after a hide, at the size it holds; it '
        'keeps its key either way. A window that is on screen but not '
        'in front is a focus_window, and a draw is neither -- showing '
        'and raising are the gestures of the user\'s *Windows* menu.',
        {'type': 'object', 'properties': {
            'key': {'type': 'string'},
        }, 'required': ['key'], 'additionalProperties': False},
    ),
    _tool(
        'hide_window',
        'Take a window off the screen without deleting it: it keeps its '
        'key and `show_window` brings it back.',
        {'type': 'object', 'properties': {
            'key': {'type': 'string'},
        }, 'required': ['key'], 'additionalProperties': False},
    ),
    _tool(
        'close_window',
        'Close a window for good: it is deleted and forgets its key.',
        {'type': 'object', 'properties': {
            'key': {'type': 'string'},
        }, 'required': ['key'], 'additionalProperties': False},
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
        '`equilibriumsurfaces` entries ARE `equilibrium_surfaces` (entry 0) '
        'and `equilibrium_at_time` (entry 1), as the profiles entry is the '
        'table and curve draws. Ask one per window.',
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
    _tool(
        'save_session',
        'Write the session as the application writes it. '
        '`name` is a file under the configuration folder, `path` a full '
        'file name.',
        {'type': 'object', 'properties': {
            'name': {'type': ['string', 'null']},
            'path': {'type': ['string', 'null']},
        }, 'additionalProperties': False},
    ),
    _tool(
        'restore_session',
        'Put a session back: the cases open, the loads replayed, the '
        'figures and plugin windows drawn the way the file named them.',
        {'type': 'object', 'properties': {
            'name': {'type': ['string', 'null']},
            'path': {'type': ['string', 'null']},
        }, 'additionalProperties': False},
    ),
    _tool(
        'new_session',
        'One clean session, WITHOUT saving: every case view and every '
        'figure of this session is closed, and nothing is written -- '
        'the sessions the user saved on disk (`last_session` and the '
        'saved ones) are untouched, and the reports stay. Use it when '
        'the user asks for a "nouvelle session"/"clean slate": the '
        'figures they drew are the ones this gesture loses, and it '
        'answers by name how many it closed. It is the *New session* '
        'of the application\'s *File* menu, asked the way the page '
        'asks it.',
        {'type': 'object', 'properties': {},
         'required': [], 'additionalProperties': False},
    ),
    _tool(
        'list_sessions',
        'The sessions the configuration folder holds (the .vsess files '
        'next to the plot and selection configurations), as the '
        'application lists them.',
        {'type': 'object', 'properties': {}, 'additionalProperties': False},
    ),
    _tool(
        'list_configurations',
        'The plot configurations (.pcfg) and the selection configurations '
        '(.lsp) the configuration folder holds. `kind` narrows to one of '
        'the two kinds; a kind the application does not answer is '
        'refused by name.',
        {'type': 'object', 'properties': {
            'kind': {'type': ['string', 'null'],
                     'enum': ['plot', 'selection']},
        }, 'additionalProperties': False},
    ),
    _tool(
        'select_from_configuration',
        'Apply one saved configuration: select in the case the '
        'quantities it names (.lsp as .pcfg), loading first the IDSs the '
        'case would need and does not hold. Answers how many were '
        'selected; a name the folder does not hold is refused by name, '
        'naming the ones it does.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'name': {'type': 'string'},
        }, 'required': ['uri', 'name'], 'additionalProperties': False},
    ),
    _tool(
        'save_selection',
        'Write the current selection of the case out as a .lsp, one '
        'quantity per selected node. Nothing selected is refused by '
        'name; the name goes through the guard the application applies '
        'in its own dialog.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'name': {'type': 'string'},
        }, 'required': ['uri', 'name'], 'additionalProperties': False},
    ),
    _tool(
        'save_plot_configuration',
        'Write one Table Plot View out as a .pcfg: the quantities of its '
        'panels, and the place each panel held. A window that is not a '
        'Table Plot View is refused by name.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'figure_key': {'type': 'string'},
            'name': {'type': 'string'},
        }, 'required': ['uri', 'figure_key', 'name'],
         'additionalProperties': False},
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
        'the window answers small, size it with focus_window first, '
        'then take the picture. The LLM cannot parse this PNG on this '
        'stack; describe a figure by reading its underlying arrays with '
        'get_signal instead.',
        {'type': 'object', 'properties': {
            'window': {'type': 'string', 'default': 'app'},
        }, 'additionalProperties': False},
    ),
    _tool(
        'focus_window',
        'The user\'s "show me this" command: the window is brought to '
        'the front -- shown when it is off the screen, raised when it is '
        'not -- and keeps the size it holds, unless `width` and '
        '`height` name the pixels to put it at (a side left out keeps '
        'the size the window holds on that side). "app" for the '
        'application, a figure key for one figure, a case URI for its '
        'shot view. Call it when the user asks to see or bring forward '
        'a window -- "montre-moi Plot1", "ramène Plot1 devant", '
        '"je ne vois pas la figure" -- and to size one for a requested '
        'picture before the get_screenshot on it. A figure you drew or '
        'named in your answer is not a reason to call it: it is in the '
        'session\'s *Windows* menu, and a draw is not an ask to show '
        'it. The answer is the size the window now holds.',
        {'type': 'object', 'properties': {
            'window': {'type': 'string', 'default': 'app'},
            'width': {'type': ['integer', 'null'],
                      'description': 'Pixels, 1 and up; left out, the '
                                     'size the window holds'},
            'height': {'type': ['integer', 'null'],
                       'description': 'Pixels, 1 and up; left out, the '
                                      'size the window holds'},
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
    _tool(
        'search_journals',
        'The lab notebook, in its two journals (the personal under '
        '~/.imasviz/journals, the shared under the folder '
        'SharedJournalDir names), asked as a RAG: the structured '
        'filters (machine, campaign, shot, date, author) narrow to '
        'the notes that name each field you ask of, then your `query` '
        'is ranked over them -- by embeddings when the preferences '
        'name the embedding endpoint and it answers, else by keyword, '
        'and the answer names which it used. A note about a shot names '
        'machine, campaign, shot and date, and a note with none of '
        'them is a general one, the same journal. With no query, the '
        'notes come back in the order they are newest.',
        {'type': 'object', 'properties': {
            'scope': {'type': ['string', 'null'],
                      'enum': ['personal', 'shared'],
                      'description': 'the one journal to ask of; left '
                                     'out, both are asked'},
            'query': {'type': ['string', 'null'],
                      'description': 'the text to rank the filtered '
                                     'notes by; left out, the notes '
                                     'come back newest first'},
            'limit': {'type': 'integer', 'default': 20},
            'machine': {'type': ['string', 'null']},
            'campaign': {'type': ['string', 'null']},
            'shot': {'type': ['string', 'null']},
            'date_from': {'type': ['string', 'null'],
                          'description': 'ISO 8601 YYYY-MM-DD, inclusive'},
            'date_to': {'type': ['string', 'null'],
                        'description': 'ISO 8601 YYYY-MM-DD, inclusive'},
            'author': {'type': ['string', 'null']},
        }, 'additionalProperties': False},
    ),
    _tool(
        'read_note',
        'The full body of one note, by its `note_id` (the file name '
        'without .md) and its `scope`. The `snippet` of '
        'search_journals is the one it is a hand for -- not the full '
        'text this one gives. Not in the journal is refused by name, '
        'naming the ids it does hold.',
        {'type': 'object', 'properties': {
            'scope': {'type': 'string', 'enum': ['personal', 'shared']},
            'note_id': {'type': 'string'},
        }, 'required': ['scope', 'note_id'], 'additionalProperties': False},
    ),
    _tool(
        'list_notes',
        'The notes in the journal(s) the caller names, filtered '
        '(machine, campaign, shot, date_from, date_to, author) and '
        'newest first. date_from and date_to bound the shot date '
        '(YYYY-MM-DD); a note that names no date is excluded only '
        'when a window is named. A filter left out is no filter at '
        'all. Empty is an answer, the same shape a search_journals '
        'that answers nothing holds.',
        {'type': 'object', 'properties': {
            'scope': {'type': ['string', 'null'],
                      'enum': ['personal', 'shared']},
            'machine': {'type': ['string', 'null']},
            'campaign': {'type': ['string', 'null']},
            'shot': {'type': ['string', 'null']},
            'date_from': {'type': ['string', 'null']},
            'date_to': {'type': ['string', 'null']},
            'author': {'type': ['string', 'null']},
        }, 'additionalProperties': False},
    ),
    _tool(
        'journal_stats',
        'The state of the two journals: the folder each is under, '
        'the count of notes each holds, and the state of the '
        'embeddings (is the endpoint named, and which model it '
        'names). Ask of it before a search, and it tells the method '
        'a run will rank with -- and the shared one answers a '
        'refusal (not a folder named) when it is not set up.',
        {'type': 'object', 'properties': {}, 'additionalProperties': False},
    ),
    _tool(
        'add_note',
        'One new note in the journal you name. `text` is the body '
        '(required), `author` is the one who wrote it (defaults to '
        '$USER, and a write with no author at all is refused by '
        'name: the write is visible to whoever reads the journal), '
        'and `machine`/`campaign`/`shot`/`date`/`title` are the '
        'note\'s filters -- a note that names them is the one about '
        'a shot, and one that does not is the one that is general. '
        'A write to the shared journal is a visible line in a place '
        'everyone you share it with reads, and it is the loop that '
        'asks for it in the user\'s own words before it runs -- the '
        'word you would give for the shared one.',
        {'type': 'object', 'properties': {
            'scope': {'type': 'string', 'enum': ['personal', 'shared']},
            'text': {'type': 'string'},
            'author': {'type': ['string', 'null']},
            'machine': {'type': ['string', 'null']},
            'campaign': {'type': ['string', 'null']},
            'shot': {'type': ['string', 'null']},
            'date': {'type': ['string', 'null'],
                     'description': 'ISO 8601 YYYY-MM-DD'},
            'title': {'type': ['string', 'null']},
        }, 'required': ['scope', 'text'], 'additionalProperties': False},
    ),
    _tool(
        'edit_note',
        'One existing note, changed in place: `scope` and `note_id` '
        'name it, and it keeps the id the other writers read it under. '
        'A field you leave out keeps the one the note held, a field '
        'you name replaces it, and an empty one clears it -- except '
        'the author (a note keeps its author) and the body (your '
        '`text` left out keeps the one it held; an empty one is a '
        'refusal). Not in the journal is refused by name, naming the '
        'ids it does hold. A write to the shared journal is a visible '
        'line in a place everyone you share it with reads, and it is '
        'the loop that asks for it in the user\'s own words before it '
        'runs -- the word you would give for the shared one.',
        {'type': 'object', 'properties': {
            'scope': {'type': 'string', 'enum': ['personal', 'shared']},
            'note_id': {'type': 'string'},
            'text': {'type': ['string', 'null'],
                     'description': 'the new body; left out, the one '
                                    'the note held'},
            'author': {'type': ['string', 'null']},
            'machine': {'type': ['string', 'null']},
            'campaign': {'type': ['string', 'null']},
            'shot': {'type': ['string', 'null']},
            'date': {'type': ['string', 'null'],
                     'description': 'ISO 8601 YYYY-MM-DD'},
            'title': {'type': ['string', 'null']},
        }, 'required': ['scope', 'note_id'], 'additionalProperties': False},
    ),
    _tool(
        'delete_note',
        'One note gone: its file and the cache entry the run holds '
        'for it. `scope` and `note_id` name the one to take out, and '
        'not in the journal is refused by name, naming the ids it '
        'does hold. The next search of the journal you take one out '
        'of does not hold the note it did: its file is not there.',
        {'type': 'object', 'properties': {
            'scope': {'type': 'string', 'enum': ['personal', 'shared']},
            'note_id': {'type': 'string'},
        }, 'required': ['scope', 'note_id'], 'additionalProperties': False},
    ),
    _tool(
        'reindex_journals',
        'Put the journal(s) in step with their index: the run asks of '
        'this when the index is empty (a fresh journal), stale (a note '
        'written before it could be indexed), or guarded (the index was '
        'written under an embedding endpoint the run is no longer '
        'under — its vectors are in a different space than the query, '
        'and this re-embeds them). It walks the notes the journal '
        'holds, keeps the ones it already has, re-embeds the ones that '
        'moved, and drops the ones the journal no longer holds. '
        '`scope` names the one to run it on (or is left out for the '
        'two at once), and the answer names, per journal, how many it '
        'kept, how many it wrote, how many it dropped, and whether the '
        'run vectorized this pass or kept the text for the keyword. '
        'A write to the shared journal is a visible one in a place '
        'everyone you share it with reads, and it is the loop that '
        'asks for it in the user\'s own words before it runs.',
        {'type': 'object', 'properties': {
            'scope': {'type': ['string', 'null'],
                      'enum': ['personal', 'shared', None],
                      'description': 'the one journal to reindex; left '
                                     'out, both are asked'},
        }, 'additionalProperties': False},
    ),
    _tool(
        'list_documents',
        'The documents the in-app agent reads for its own RAG: the '
        'markdown, text, and PDF files the folder AgentDocsDir names '
        'holds (the name, the size, the date, the relative path a '
        'search answers by). An answer is the corpus as named (a '
        'folder with no document is an answer, and a folder not named '
        'is a refusal that names it -- the same shape a shared-journal '
        'without its folder answers).',
        {'type': 'object', 'properties': {},
         'additionalProperties': False},
    ),
    _tool(
        'read_document',
        'The full text of one document of the corpus, by its relative '
        'path (the one a search_documents hit names). Not in the corpus '
        'is a refusal by name, naming the ones it does read; a document '
        'it does not read is the same. The one to ask when a search hit '
        'is the one the reader wants to read in full.',
        {'type': 'object', 'properties': {
            'rel': {'type': 'string',
                    'description': 'the relative path of the document '
                                   'under the corpus folder'},
        }, 'required': ['rel'], 'additionalProperties': False},
    ),
    _tool(
        'reindex_documents',
        'Put the documents corpus in step with its index: the run asks '
        'of this when the user has added a document to the corpus '
        'folder, when the embedding endpoint has changed (a store '
        'written under another endpoint is guarded -- its vectors are '
        'in a different space than the query), or when the index is '
        'empty. It walks the documents the corpus reads, keeps the ones '
        'it already has, re-embeds the ones that moved, and drops the '
        'ones that left the folder. The answer names how many documents '
        'and chunks it kept, wrote, dropped, and whether the run '
        'vectorized this pass or kept the text for the keyword.',
        {'type': 'object', 'properties': {},
         'additionalProperties': False},
    ),
    _tool(
        'search_documents',
        'The in-app agent\'s RAG over the documents corpus: the ranked '
        'chunks of the user\'s own markdown, text, and PDF files '
        '(one hit per chunk, the document, the chunk, a snippet). The '
        'one to ask when the question is about the user\'s own '
        'writing, documents, or the corpus the AgentDocsDir folder '
        'holds. The answer names the method it ranked with '
        '(hybrid / embeddings / keyword / empty), and when a store was '
        'written under another embedding endpoint it is "guarded" and '
        'the keyword alone stands -- reindex_documents is the one that '
        'sets them in step.',
        {'type': 'object', 'properties': {
            'query': {'type': 'string'},
            'limit': {'type': 'integer',
                      'description': 'how many chunks to answer; '
                                     'left out, 8'},
        }, 'required': ['query'], 'additionalProperties': False},
    ),
    _tool(
        'documents_stats',
        'The state of the documents corpus: how many documents and '
        'chunks it holds, the embedding endpoint and model it was '
        'written under, and when it was built. The one to ask when the '
        'answer to "can the agent read my notes/documents" is "it is '
        'not indexed yet" or "it was indexed under another endpoint".',
        {'type': 'object', 'properties': {},
         'additionalProperties': False},
    ),
    _tool(
        'list_prompts',
        'The prompt catalogue: the prompts the user wrote once and '
        'keeps to ask again, each with its id, its name, its category, '
        'its one-line description and the holes it opens. The personal '
        'catalogue is under ~/.imasviz/prompts and the shared one under '
        'the folder SharedPromptsDir names (an unnamed shared folder '
        'costs its own half of the list, named in '
        'catalogues_unavailable -- the personal prompts still answer). '
        '`category` and `query` narrow it, and `categories` answers how '
        'many prompts each category holds. Ask of it when the user says '
        '"relance le prompt …" / "run my usual X" and you do not know '
        'the wording they filed.',
        {'type': 'object', 'properties': {
            'scope': {'type': ['string', 'null'],
                      'enum': ['personal', 'shared'],
                      'description': 'the one catalogue to ask of; left '
                                     'out, both are asked'},
            'category': {'type': ['string', 'null'],
                         'description': 'the prompts that name this '
                                        'category; compared without '
                                        'minding the case'},
            'query': {'type': ['string', 'null'],
                      'description': 'a word of the name, the '
                                     'description, the category or the '
                                     'id'},
            'limit': {'type': 'integer', 'default': 100},
        }, 'additionalProperties': False},
    ),
    _tool(
        'prompt_detail',
        'One prompt of the catalogue, whole: its body with its holes '
        'still open, and `values` -- what each hole would be answered '
        'from right now (what the user typed last time, what this '
        'session knows, what the file declares) and null for the ones '
        'that still need a value. `name` is the id or the display name; '
        'a name two prompts carry is refused naming their ids. Asking '
        'this remembers nothing: it is the look, not the typing.',
        {'type': 'object', 'properties': {
            'name': {'type': 'string',
                     'description': 'the id or the display name of the '
                                    'prompt'},
            'scope': {'type': ['string', 'null'],
                      'enum': ['personal', 'shared']},
        }, 'required': ['name'], 'additionalProperties': False},
    ),
    _tool(
        'fill_prompt',
        'The prompt as it will be asked, its holes filled -- and '
        'nothing run. A hole is filled from the first source that '
        'answers it: what you name in `values`, what was typed last '
        'time for that prompt, what this session knows (its open case: '
        'case, uri, shot, run, database; its one open window: figure), '
        'what the file declares -- and the answer says which one it '
        'was. A hole none of them answers is a refusal naming the '
        'holes: a prompt is never sent with {shot} in it and never '
        'sent with a guess. Take the `text` this answers and ask it as '
        'the user asked it -- filling is not running.',
        {'type': 'object', 'properties': {
            'name': {'type': 'string'},
            'values': {'type': ['object', 'null'],
                       'additionalProperties': {'type': 'string'},
                       'description': 'the hole -> the value to use '
                                      'this time, for the holes the '
                                      'session does not answer'},
            'scope': {'type': ['string', 'null'],
                      'enum': ['personal', 'shared']},
        }, 'required': ['name'], 'additionalProperties': False},
    ),
    _tool(
        'save_prompt',
        'One prompt into the catalogue, named and described, so the '
        'next run does not type it again. `text` is the prompt as it '
        'is asked, with its holes spelled {name}; `variables` left out '
        'is read off the text (every hole it opens, asked for on every '
        'run), and a hole declared and never opened is refused by name. '
        'The user asks for this in their own words ("garde ce prompt", '
        '"enregistre-le") -- a turn that merely drew a figure is not an '
        'ask to file its wording. scope=shared writes into the folder '
        'the team reads, which is a line others see: it is asked for in '
        'the user\'s own words too.',
        {'type': 'object', 'properties': {
            'name': {'type': 'string',
                     'description': 'the name the catalogue lists it by'},
            'text': {'type': 'string',
                     'description': 'the prompt, holes spelled {name}'},
            'category': {'type': ['string', 'null']},
            'description': {'type': ['string', 'null'],
                            'description': 'one line saying what it '
                                           'asks, for the reader of '
                                           'the list'},
            'variables': {'type': ['object', 'string', 'null'],
                          'description': 'hole -> default, as an '
                                         'object or as the "a=1; b=" '
                                         'line the file spells; left '
                                         'out, read off the text'},
            'scope': {'type': 'string', 'enum': ['personal', 'shared'],
                      'default': 'personal'},
            'prompt_id': {'type': ['string', 'null'],
                          'description': 'the file name to file it '
                                         'under; left out, the slug of '
                                         'the name'},
        }, 'required': ['name', 'text'], 'additionalProperties': False},
    ),
    _tool(
        'edit_prompt',
        'One prompt of the catalogue, changed in place: it keeps the id '
        'the pages, the sessions and the remembered values read it '
        'under. A field you leave out keeps the one the prompt held, a '
        'field you name replaces it, an empty one clears it -- the body '
        'excepted, which an edit cannot empty. A new prompt is '
        'save_prompt, not this one.',
        {'type': 'object', 'properties': {
            'name': {'type': 'string'},
            'text': {'type': ['string', 'null'],
                     'description': 'the new body; left out, the one '
                                    'the prompt held'},
            'category': {'type': ['string', 'null']},
            'description': {'type': ['string', 'null']},
            'variables': {'type': ['object', 'string', 'null']},
            'scope': {'type': ['string', 'null'],
                      'enum': ['personal', 'shared']},
        }, 'required': ['name'], 'additionalProperties': False},
    ),
    _tool(
        'delete_prompt',
        'One prompt out of the catalogue, and the values that were '
        'remembered for it. Not there is a refusal naming the ids the '
        'catalogue holds. This takes a file the user wrote off the disk: '
        'it is asked for in their own words, not decided for them.',
        {'type': 'object', 'properties': {
            'name': {'type': 'string'},
            'scope': {'type': ['string', 'null'],
                      'enum': ['personal', 'shared']},
        }, 'required': ['name'], 'additionalProperties': False},
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
            ('list', 'list_sessions'),
            ('configurations', 'list_configurations'),
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
