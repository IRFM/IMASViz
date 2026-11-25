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
5. `plot_one(...)` or `get_signal(...)` -> Draw curves or read numerical values.

### STRICT RULES (NEVER VIOLATE)
- **NO HALLUCINATION:** Never invent IDS names, paths, numbers, figure keys, or file paths. Only state facts returned by a tool in this session.
- **NO FAKE ACTIONS:** Never say you plotted a curve, wrote a report, or saved a note unless the corresponding tool returned `error: null` in this turn. If a tool fails or refuses, report the exact refusal reason.
- **OCCURRENCE vs INDICES vs PATH:**
  - `occurrence`: Version of an IDS (passed to `load_ids`).
  - `indices`: 0-based index of a tensor dimension or nested array (e.g., `indices={"psi": 50}`).
  - `path`: Specific member of a structure array (e.g., `magnetics.flux_loop[2].flux.data`). To plot two members together, call `plot_one` twice using `into_figure_key` on the second call—never put `flux_loop` in `indices`.
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
``list_case_idss``, ``plot_one``, ``get_signal`` -- and inviting the user
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
    _tool(
        'plot_one',
        'Draw one quantity, into the figure its axes call for. '
        'A curve figure for one axis to draw, a picture window for two. '
        '`along` names the axis the quantity runs along (the clock, or one '
        'of its own axes); `indices` pins each OTHER axis at its index -- '
        'the same schema `get_signal` uses, so the figure the user sees and '
        'the numbers get_signal reports are the same element. '
        '`time` pins a profile to one slice of its dynamic time array: by '
        'default the nearest slice (the answer names the index and that '
        'slice\'s own time, not the value asked at), or, with '
        'time_interp=true, the linear interpolation between the two slices '
        'that bracket the value (the answer then carries the exact value '
        'requested). `along_time` / `along` / `indices` and `time` are '
        'refused together (two opposite readings). The answer carries the '
        'figure key and `curves`, the exact list of the curves the figure '
        'holds after the call: a claim that a curve is on that figure '
        'stands on that list, not on memory of the call.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'path': {'type': 'string'},
            'along_time': {'type': ['boolean', 'null'],
                           'description': 'legacy: one axis to draw. '
                                          'Prefer `along` + `indices`.'},
            'along': {'type': ['string', 'null'],
                      'description': 'the axis the quantity runs along: '
                                     '"time"/"temps"/"t" for the clock, or '
                                     'the name of one of its own axes '
                                     '(e.g. "psi"). None for the default '
                                     '(the clock when it holds one).'},
            'indices': {'type': ['object', 'null'],
                        'description': 'one entry per axis the figure does '
                                       'not draw, by that axis\'s name, at '
                                       'its 0-based index. An array of '
                                       'structures (time_slice, profiles_1d, '
                                       'ion, ...), or the leaf\'s own '
                                       'coordinate (psi, ...); each of '
                                       'several nested arrays on its own. '
                                       'e.g. {"psi": 50} for a profile held '
                                       'by the dynamic array, "ion": 4 '
                                       'for one structure in it.',
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
                     'description': 'seconds; the time at which to pin the '
                                    'profile. Nearest slice by default; '
                                    'interpolated with time_interp=true.'},
            'time_interp': {'type': ['boolean', 'null'],
                            'description': 'when true, interpolates '
                                           'linearly between the two slices '
                                           'that bracket the requested time, '
                                           'leaving the answer\'s '
                                           'time_slice_time equal to the '
                                           'exact value asked at, not the '
                                           'nearest slice. Defaults to '
                                           'false (nearest slice).'},
        }, 'required': ['uri', 'path'], 'additionalProperties': False},
    ),
    _tool(
        'plot_slice',
        'Draw one 1D-profile leaf at a single time, through the Access '
        'Layer\'s own DBEntry.get_slice (the value the Access Layer answers '
        'at that instant, not a GUI-side lerp). The coordinate is the leaf\'s '
        'own (independent of time); the curve is its value at `time`. '
        'interpolation: "linear" (default), "closest" (the case\'s nearest '
        'slice), or "previous" (the one at or before `time`). A time outside '
        'the case\'s range answers the nearest slice the case holds, and the '
        'answer names time_requested and time_slice_time apart. Not a '
        '2D-pictorial leaf, nor a 0D scalar.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'leaf': {'type': 'string',
                     'description': 'the full data path of the leaf, e.g. '
                                    'core_profiles.profiles_1d[0].'
                                    'electrons.temperature'},
            'time': {'type': 'number',
                     'description': 'the instant the profile is read at'},
            'occurrence': {'type': 'integer', 'default': 0},
            'interpolation': {'type': 'string',
                              'enum': ['linear', 'closest', 'previous'],
                              'default': 'linear'},
            'into_figure_key': {'type': ['string', 'null'],
                                'description': 'an open Plot: figure to add '
                                               'to; by default a new '
                                               'figure is opened'},
        }, 'required': ['uri', 'leaf', 'time'],
           'additionalProperties': False},
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
        'plot_selection',
        'Draw the case selection: one curve figure, one window per picture. '
        '`select_signals` first.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
        }, 'required': ['uri'], 'additionalProperties': False},
    ),
    _tool(
        'plot_table',
        'One panel per named path, in a Table Plot View. '
        '`columns` sets the width of the row; `plot_axis` "TIME" reads '
        'every quantity along time.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'paths': {'type': 'array', 'items': {}},
            'columns': {'type': ['integer', 'null']},
            'plot_axis': {'type': ['string', 'null']},
        }, 'required': ['uri', 'paths'], 'additionalProperties': False},
    ),
    _tool(
        'plot_stacked',
        'The named paths stacked one panel per quantity. '
        'Against the abscissa `plot_axis` names, the default being the clock.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'paths': {'type': 'array', 'items': {}},
            'plot_axis': {'type': 'string', 'default': 'TIME'},
        }, 'required': ['uri', 'paths'], 'additionalProperties': False},
    ),
    _tool(
        'get_signal',
        'The values the tree read gives for one leaf, as JSON. '
        '`along` names the axis it runs along (the clock, or one of its own '
        'axes); `indices` pins each OTHER axis at its index -- the same '
        'schema `plot_one` uses, so what the figures show and what this '
        'answers are the same element. Legacy `as_function_of_time` true '
        'reads along the clock, false along its own axis; `coordinate_index` '
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
    _tool(
        'scale_curve',
        'Multiply a figure\'s drawn curve(s) by a constant. In place and '
        'reversible (reset_curve); `curve` is a name substring, a 0-based '
        'index, or left out for every curve. `factor` must be a finite '
        'number. curve_stats and export_curve then read the multiplied '
        'value, the quantity in the tree unchanged.',
        {'type': 'object', 'properties': {
            'figure_key': {'type': 'string'},
            'factor': {'type': 'number'},
            'curve': {'type': ['string', 'integer', 'null'],
                      'description': 'a name substring, a 0-based index, '
                                     'or null for every curve'},
        }, 'required': ['figure_key', 'factor'], 'additionalProperties': False},
    ),
    _tool(
        'shift_curve',
        'Add a constant to a figure\'s drawn curve(s): a vertical offset. '
        'The inverse of a subtraction, on the same `curve` as scale_curve. '
        '`offset` must be a finite number.',
        {'type': 'object', 'properties': {
            'figure_key': {'type': 'string'},
            'offset': {'type': 'number'},
            'curve': {'type': ['string', 'integer', 'null']},
        }, 'required': ['figure_key', 'offset'], 'additionalProperties': False},
    ),
    _tool(
        'normalize_curve',
        'Divide a figure\'s drawn curve(s) by a reference of their own: '
        '`max` (the largest sample), `first` (index 0), or `mean`. A '
        'reference that is zero or not a number is refused by name.',
        {'type': 'object', 'properties': {
            'figure_key': {'type': 'string'},
            'mode': {'type': 'string', 'enum': ['max', 'first', 'mean'],
                     'default': 'max'},
            'curve': {'type': ['string', 'integer', 'null']},
        }, 'required': ['figure_key'], 'additionalProperties': False},
    ),
    _tool(
        'reset_curve',
        'Put a figure\'s curve(s) back to the data they were drawn with: '
        'the scale/shift/normalize put on is taken off. A curve nobody '
        'transformed is not in the answer.',
        {'type': 'object', 'properties': {
            'figure_key': {'type': 'string'},
            'curve': {'type': ['string', 'integer', 'null']},
        }, 'required': ['figure_key'], 'additionalProperties': False},
    ),
    _tool(
        'remove_curve',
        'Take a curve off a figure, or every one when `curve` is left '
        'out. The curve leaves the plot and the figure forgets it; the '
        'answer is the count still held. A table or the flux-surface '
        'figure is not a single figure and is refused by name.',
        {'type': 'object', 'properties': {
            'figure_key': {'type': 'string'},
            'curve': {'type': ['string', 'integer', 'null']},
        }, 'required': ['figure_key'], 'additionalProperties': False},
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
        'shift_curve to clear them is the answer.',
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
        'scale/shift/normalize; plot_report is the same read with an HTML '
        'file on disk.',
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
                                       'the way plot_one does.'},
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
                                       'the way plot_one does.'},
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
        'plot_report',
        'A window of curves as a self-contained HTML report on disk: the '
        'image of the window, and one row per trace it drew -- the '
        'quantity, the number of samples, the finite minimum and maximum, '
        'and the nan/inf counts. This is the "rapport"/"report" the user '
        'asks for. For a report of more than one plot, call it once per '
        'plot -- a report is one window, and the page lists the ones a '
        'request wrote together. The file lands in `~/.imasviz/reports`; '
        '`name` is the report name (a place, not a report, is refused). '
        'A window that draws no curve it could stat is refused by name.',
        {'type': 'object', 'properties': {
            'figure_key': {'type': 'string'},
            'name': {'type': ['string', 'null']},
        }, 'required': ['figure_key'], 'additionalProperties': False},
    ),
    _tool(
        'case_report',
        'The loaded tree of a case as a self-contained HTML report on '
        'disk: one row per curve the tree holds -- the numeric arrays its '
        'leaves read, in tree order -- with the statistics of each. An IDS '
        'not yet loaded is not a curve, so the answer says how many curves '
        'it gave and list_idss names what the case still holds. A case '
        'whose loaded tree has no curve is refused by name.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'name': {'type': ['string', 'null']},
        }, 'required': ['uri'], 'additionalProperties': False},
    ),
    _tool(
        'case_ids_report',
        'The case itself as a self-contained HTML report on disk: every '
        'IDS the case\'s data dictionary holds and the occurrences each '
        'one holds, which of those the session loaded, and for each loaded '
        'occurrence the header of its `ids_properties` values and '
        'available signals -- the signals the tree holds for it, kept to '
        'the ones the tree carries as available (the same test its own '
        'colouring applies), a 0-D scalar held by the dynamic array '
        'among them. The "inventaire du cas" / "what does this case '
        'hold" report. A property the case leaves empty is named empty, '
        'an occurrence without an available signal is named as such, and '
        'a case that holds no data at all is refused by name. `name` is '
        'the report name under '
        '`~/.imasviz/reports` (a place, not a report, is refused).',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'name': {'type': ['string', 'null']},
        }, 'required': ['uri'], 'additionalProperties': False},
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
# A group is NOT a name the loop is offered: every tool is still offered by
# its own name, and a group answers one question the flat schemas cannot --
# which of the neighbouring tools a stray parameter belongs to. The 84
# schemas repeat the same parameter words (``along`` 12 times, ``scope``
# 13, ``figure_key`` 18), so a parameter the model put on the wrong tool of
# a group is a far likelier mistake than a parameter it invented, and the
# refusal that only lists what is *not* there leaves the model guessing.
#
# The day a group is offered under one name instead of its members, this is
# the table that says which member answers which call, and the loop's guards
# (``DESTRUCTIVE_GESTURES``, ``SHARED_JOURNAL_GESTURES``, ``_WORK_GESTURES``)
# must keep being asked about the member's name, not the group's: a
# ``manage_window(action='close')`` that reaches the guard as
# ``manage_window`` is a closed window nobody asked for.
FAMILIES = (
    ('cases', ('open_case', 'list_cases', 'close_case')),
    ('the IDSs', ('list_idss', 'list_case_idss', 'load_ids')),
    ('the tree', ('search_nodes', 'describe_node', 'describe_ids',
                  'list_quantities')),
    ('the selection', ('select_signals', 'unselect_all', 'list_selection')),
    ('the drawing', ('plot_one', 'plot_slice', 'plot_selection',
                     'plot_table', 'plot_stacked', 'get_signal')),
    ('the equilibrium', ('equilibrium_surfaces', 'equilibrium_at_time')),
    ('the curves already drawn', ('scale_curve', 'shift_curve',
                                  'normalize_curve', 'reset_curve',
                                  'remove_curve', 'curve_stats',
                                  'export_curve')),
    ('the axes and the slices of a window',
     ('set_axis_range', 'set_image_window', 'set_slice_index',
      'set_log_scale', 'invert_axis')),
    ('the physics of a signal', ('detect_events', 'clear_event_marks',
                                 'events_report', 'spectrum',
                                 'cross_correlation', 'spectrum_report')),
    ('what a case says', ('greenwald', 'beta_normal', 'total_pressure')),
    ('a campaign of shots', ('campaign', 'campaign_report')),
    ('the windows', ('list_windows', 'show_window', 'hide_window',
                     'close_window')),
    ('the plugins', ('list_plugins', 'run_plugin')),
    ('sessions and configurations', ('save_session', 'restore_session',
                                     'new_session', 'list_sessions',
                                     'list_configurations',
                                     'select_from_configuration',
                                     'save_selection',
                                     'save_plot_configuration')),
    ('the reports', ('plot_report', 'case_report', 'case_ids_report')),
    ('the export', ('export_to_ids',)),
    ('the screen', ('get_screenshot', 'focus_window')),
    ('the log', ('get_logs',)),
    ('the journals', ('search_journals', 'list_notes', 'read_note',
                      'add_note', 'edit_note', 'delete_note',
                      'journal_stats', 'reindex_journals')),
    ('the documents corpus', ('list_documents', 'search_documents',
                              'read_document', 'reindex_documents',
                              'documents_stats')),
    ('the prompts', ('list_prompts', 'prompt_detail', 'fill_prompt',
                     'save_prompt', 'edit_prompt', 'delete_prompt')),
)

_FAMILY_OF_TOOL = {name: label
                   for label, members in FAMILIES
                   for name in members}

_FAMILY_MEMBERS = dict(FAMILIES)


def familyOf(name):
    """The group a tool belongs to, and None for a name that is not one."""
    return _FAMILY_OF_TOOL.get(name)


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
    if parameter in TOOL_PARAMETERS[name].get('properties', {}):
        return []
    return [other for other in _FAMILY_MEMBERS[label]
            if other != name
            and parameter in TOOL_PARAMETERS[other].get('properties', {})]


def unknownParameterRefusal(name, unknown):
    """The loop's words for an argument the tool does not take.

    ``unknown`` is what ``unknownParameters`` answered; the first name is
    the one put on trial. The refusal names the stray and the parameters
    that are -- a Python ``TypeError`` says "unexpected keyword argument",
    which does not tell the model what to answer with -- and then, when a
    neighbour in the same group takes the stray, names that neighbour:
    ``columns`` on ``plot_one`` is a table asked with a single quantity's
    call, and the short way back is the tool that takes it.
    """
    schema = TOOL_PARAMETERS.get(name, {})
    allowed = sorted(schema.get('properties', {}))
    if allowed:
        text = ('"%s" is not a parameter of the %s tool: it takes %s. '
                'Answer with the parameters the tool names.'
                % (unknown[0], name, ', '.join(allowed)))
    else:
        text = ('"%s" is not a parameter of the %s tool, which takes no '
                'parameter at all. Answer with no arguments.'
                % (unknown[0], name))
    siblings = siblingTaking(name, unknown[0])
    if siblings:
        if len(siblings) == 1:
            text += (' "%s" is a parameter of %s: ask that tool if that is '
                     'the gesture you mean.' % (unknown[0], siblings[0]))
        else:
            text += (' "%s" is a parameter of %s: ask one of those if that '
                     'is the gesture you mean.'
                     % (unknown[0], ', '.join(siblings)))
    return text


def unknownParameters(name, args):
    """The names in ``args`` that the tool ``name`` does not take.

    Every tool in ``TOOLS`` declares ``additionalProperties: false`` and
    lists the names it does take in ``parameters.properties``. An
    argument whose name is not in that list is one the model invented --
    ``time_index`` on ``plot_one`` is the one measured -- and the loop
    must refuse it by naming the parameter that is not there and the ones
    that are, instead of letting Python's ``TypeError`` (``unexpected
    keyword argument``) speak for it. An unknown tool name, or a tool that
    admits extra parameters, answers an empty list.
    """
    schema = TOOL_PARAMETERS.get(name)
    if schema is None:
        return []
    if schema.get('additionalProperties', False):
        return []
    allowed = set(schema.get('properties', {}))
    return sorted(set(args or {}) - allowed)
