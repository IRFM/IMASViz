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
   screenshot is a capture the user asks for, not one you take
   yourself: the LLM cannot read a PNG on this stack (describe a figure
   by its underlying arrays with get_signal, and by name with
   list_windows), so get_screenshot exists to save a picture for the
   user, and it is yours to call only when the user asks for a capture
   ("show me the interface", "give me a screenshot of this figure").
   The pictures it saves are the figures the session has drawn in this
   turn -- the captures of the turn. A figure an earlier turn drew is
   captured in the files that turn left, and this turn reaches it again
   only when the ask names it. The application shell and the data-tree
   panel of a case are the captures that show the interface instead,
   and those are saved only when the user names that interface in the
   ask. A
   screenshot is the size the window is: when the figure is one the user
   must see, focus_window puts it forward at a readable size (1280x800
   or the named pixels) before the get_screenshot.
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

The index of the arrays a quantity sits in, named. `plot_one` and
`get_signal` both take the one schema: `along` names the axis the
quantity runs along (the clock, when it holds one, or one of its own
axes), and `indices` pins each OTHER axis at its index by that axis's
name. Each of several nested arrays of structures is on its own, so a
quantity in two arrays is addressed by one index per array. For
`equilibrium.time_slice[i].profiles_1d.j_tor`, a profile held by the
dynamic array, "tracer le long du temps pour un index de psi de 50" is
`along=None` (or any clock spelling), `indices={"psi": 50}` -- and
"tracer pour un ion de 4, un profil de 2" is `indices={"ion": 4, "f":
2}`. The `numbers` get_signal answers and the `figure` plot_one opens
are the same element of the same array, because both halves route
through the same shared resolver; a word that names no axis the
quantity holds, or an index past its extent, is a refusal the tool
names -- answer with the refusal, do not retry with a different number.

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
            'into_figure_key': {'type': ['string', 'null']},
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
        'and the nan/inf counts. The file lands in `~/.imasviz/reports`; '
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
        'Bring a window forward at a readable size before a screenshot: '
        'shown, raised to the front, and resized to the default figure '
        'size (1280x800), or to the named `width` x `height` in pixels. '
        '"app" for the application, a figure key for one figure, a case '
        'URI for its shot view. The answer is the size the window now '
        'holds -- ask get_screenshot on the same window after.',
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
