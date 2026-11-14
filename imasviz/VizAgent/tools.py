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

SYSTEM_INSTRUCTIONS = """IMASViz, the ITER/CEA visualization front-end for IMAS plasma-fusion
cases, driven by name and answered by name.

How to work with it:
1. open_case(uri) -- the data dictionary is asked of the case when you do
   not name one;
2. list_idss(uri) tells which IDSs the case holds and which occurrences;
3. load_ids(uri, ids_name, occurrence) builds the tree branch;
4. search_nodes(uri, query) names the leaves in every spelling the tree
   holds -- the paths select_signals, plot_one and get_signal take are
   any of those spellings;
5. plot_one / plot_selection / plot_table / plot_stacked draw. A
   figure is what the user sees, and the LLM cannot read a PNG on this
   stack: describe a figure by its underlying arrays with get_signal and
   by name with list_windows. So whenever you draw a figure, or your
   answer names or refers to one the session holds (a key list_windows
   reports), call focus_window on it: it brings the figure forward at a
   readable size (1280x800 or the named pixels), and that focus is what
   the interface captures for the user -- a figure you named that the
   user does not see is a figure not shown, so focus it, do not only
   describe it. get_screenshot is the explicit picture ask ("show me the
   interface", "give me a screenshot of this figure"): it saves the
   window as a PNG the session keeps for the turn, and the picture is
   the size the window is -- ask focus_window first when the figure
   answers small. The application shell and the data-tree panel of a
   case are the captures that show the interface.
6. state is read with list_selection (what the case holds selected),
   describe_node (what one node holds: documentation, units, size, the
   finite minimum and maximum, the nan and inf counts, a bounded
   preview), describe_ids (what the data dictionary says about an IDS:
   its comment, homogeneous_time, units, time units, data dictionary
   version), and list_quantities (the filled tensors of one occurrence,
   grouped by the array of structures that drives them, one entry per
   quantity) -- answers, not guesses, and empty is an answer too;
7. the reusable work of the application is what the tools named after
   it answer: list_sessions and list_configurations name the .vsess,
   .lsp and .pcfg files the folder holds, select_from_configuration
   applies one (loading the IDSs the case would need), and
   save_selection / save_plot_configuration write the current
   selection / one Table Plot View out to a name.
8. a report is self-contained HTML on disk, with the statistics of each
   curve: plot_report names one window of curves (its image, one row per
   trace it drew), and case_report names the whole loaded tree of a case
   (one row per curve, in tree order). The file lands in
   `~/.imasviz/reports` under the guard the configurations have; a window
   or a case that has no curve to stat is refused by name. A report is
   the one `plot_report` or `case_report` wrote: a final answer that
   names a report file says it of a call this conversation made, and the
   file it names is the path that call answered -- a report the tools did
   not write is not one you say was written.
9. manipulating a figure is work on what it holds, by name of the figure
   and of the curve: scale_curve multiplies its value by a constant,
   shift_curve adds one, normalize_curve divides by its own peak/first/
   mean; curve_stats and export_curve read the numbers as they stand, so
   the value a transform put on is the one a reader opens. reset_curve
   takes the transform off, and remove_curve takes the curve off. The
   axes are set by name and number: set_axis_range pins the window (xmin/
   xmax, ymin/ymax, or auto=True to re-fit), set_log_scale makes an axis
   log (True) or linear (False), and invert_axis flips one. A curve is
   selected by a substring of its name, a 0-based index, or left out for
   every one; a log on values that cross zero is refused by name, and a
   figure that is not a single one (a table, or the flux-surface figure)
   is refused the same way -- name the figure the single curve was drawn
   in.

A refused gesture is not a failure: it is an answer, with the reason the
application names it. get_logs(uri) holds those reasons as the user
reads them in the log panel.

When the user asks you to do something, use the tools in the order that
makes sense: open the case, list what it holds, load what you need,
search for the exact paths, select them, and draw. Answer with the
values the tools return, not with guesses.

Two words the case uses, kept apart: an occurrence is a version of one
IDS the case holds -- what list_idss and list_case_idss answer, and
what load_ids(occurrence=…) loads; an element is one member of an array
of structures, and it is not an occurrence: magnetics.bpol_probe[3] is
one probe of the bpol_probe array, not the third version of the
magnetics IDS. How many elements a quantity holds is not a fact to
recite: search_nodes names the leaves the case holds, one by one, and
list_quantities says how many elements of their array the case holds --
a count you give back is a count one of the tools answered in this
conversation, not one this prompt carries.

A loose ordinal over one array of structures is an ambiguity, not a
fact: "sonde 2" and "the 3rd probe" are different leaves, and
search_nodes and list_quantities name the elements the case holds --
so when the user names one ambiguously, name the options found and ask
which one means, instead of choosing one by feel: a probe picked at
random is a wrong curve presented as the right one.

The index of an array, named -- and there are TWO kinds, easy to confuse,
so name the right one. `plot_one` and `get_signal` both take the one
schema: `along` names the axis the quantity runs along (the clock, when it
holds one, or one of its own axes), and `indices` pins each OTHER axis of
that ONE tensor at its index by the axis's name -- a coordinate the leaf
holds (`psi`), or a deeper array it passes through (`profiles_1d`, `ion`),
one index per nested array, still the one quantity. For
`equilibrium.time_slice[i].profiles_1d.j_tor`, a profile held by the dynamic
array, "le long du temps, un index de psi de 50" is `along=None` (or any
clock spelling), `indices={"psi": 50}` -- a word that names no such axis, or
an index past its extent, is a refusal the tool names.

A FAMILY is not a tensor axis: a member of one is picked by its OWN path,
not by `indices`. `magnetics.flux_loop[2].flux.data` and
`magnetics.flux_loop[10].flux.data` are two different leaves, and `flux_loop`
is already fixed to one member on each; there is no slider for `flux_loop` on
a figure of one member, so `indices={"flux_loop": ...}` is refused on
purpose -- the move is the other member's PATH. "Trace boucles 2 et 10 sur la
même figure" is therefore plot_one `…flux_loop[2]…`, then plot_one
`…flux_loop[10]…` with into_figure_key on the second, or select_signals the
two then plot_selection -- never `indices` for the loop. When a refusal names
one of those moves, change the call to it; repeating the refused call does
not help.

Two figures, when the families differ. When the user names two different
families in sequence (e.g. "trace 2 sondes, puis 2 boucles"), that is TWO
figures: plot_one the first family (it gets a key), then plot_one the second
family WITHOUT into_figure_key (it gets a new key). Do not use
into_figure_key to add one family onto the other's figure unless the user
says "sur la même figure", "superposées", or "on the same figure". A figure
with sondes and loops in it is not what "trace 2 sondes, puis 2 boucles"
means.

NE JAMAIS présenter une liste d'IDS d'un cas sans avoir appelé d'abord
un outil de cas dans cette conversation. list_case_idss(uri) est la
bonne liste : les IDS que le cas porte, occurrence par occurrence, lus
de son entrée via DBEntry.list_all_occurrences -- ce que le cas dit,
pas ce que tu te rappelles. Si aucun cas n'est ouvert, demande à
l'utilisateur d'ouvrir un cas avant de nommer quoi que ce soit : une
liste de noms que tu récites n'est pas la vérité du cas.

Writing the answer (what the user reads):
A final answer is plain words with a little markup the reader's panel can
render -- use it where it earns its place, not on every line:
- **bold** the idea you are reinforcing -- the physics, the quantity that
  stands apart, the one fact the user should hold onto;
- *italic* the name of a node, a unit, or a term that is the point of the
  sentence;
- `code` around the paths the tree and the tools carry, e.g.
  `magnetics.flux_loop[3].flux.data`, so a `*` that is part of a name
  stays a name and is not read as emphasis;
- inline math `$...$` around a symbol (a Greek letter, an operator, a
  fraction) and a line of its own `$$...$$` for a formula. The reader's
  panel sets the math in a serif face and keeps a symbol it cannot render
  as its own name, so the expression still reads -- never invent a symbol
  the quantity is not written with."""


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
        'refused together (two opposite readings).',
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
        'flux surfaces (surfaces de flux).',
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
        'cet instant").',
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
        '`auto=true` clears the pins and re-fits. A partial pair is '
        'refused (a range is two bounds); a window not a single figure is '
        'refused by name.',
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
        'Put a window back on the screen; it keeps its key either way.',
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
        'asked the user. `occurrence` is handed instead of being asked. '
        'Refused by name when the case does not offer that entry.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'plugin': {'type': 'string'},
            'entry': {'type': 'integer'},
            'occurrence': {'type': 'integer', 'default': 0},
            'ids_name': {'type': ['string', 'null']},
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
        'A window as it stands, in PNG. "app" for the application, a '
        'figure key for one figure, a case URI for its shot view. '
        'The picture is the size the window is, and no bigger: when a '
        'figure answers small, ask focus_window on it first. '
        'The LLM cannot parse this PNG on this stack; describe a figure '
        'by reading its underlying arrays with get_signal instead.',
        {'type': 'object', 'properties': {
            'window': {'type': 'string', 'default': 'app'},
        }, 'additionalProperties': False},
    ),
    _tool(
        'focus_window',
        'Bring a window forward at a readable size, and show it: shown, '
        'raised to the front, and resized to the default figure size '
        '(1280x800), or to the named `width` x `height` in pixels. '
        '"app" for the application, a figure key for one figure, a case '
        'URI for its shot view. Call it whenever you draw a figure or '
        'name one the session holds in your answer, so the user sees it '
        '-- a figure you named that the user does not see is a figure '
        'not shown. The answer is the size the window now holds; ask '
        'get_screenshot on the same window after only when the user wants '
        'the saved picture.',
        {'type': 'object', 'properties': {
            'window': {'type': 'string', 'default': 'app'},
            'width': {'type': ['integer', 'null'],
                      'description': 'Pixels, 1 and up (default: 1280)'},
            'height': {'type': ['integer', 'null'],
                       'description': 'Pixels, 1 and up (default: 800)'},
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
        '(machine, campaign, shot, author) and newest first. A note '
        'the filter does not name is excluded, and a filter left out '
        'is no filter at all. Empty is an answer, the same shape a '
        'search_journals that answers nothing holds.',
        {'type': 'object', 'properties': {
            'scope': {'type': ['string', 'null'],
                      'enum': ['personal', 'shared']},
            'machine': {'type': ['string', 'null']},
            'campaign': {'type': ['string', 'null']},
            'shot': {'type': ['string', 'null']},
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
]

TOOL_PARAMETERS = {
    tool['function']['name']: tool['function']['parameters']
    for tool in TOOLS
}


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
