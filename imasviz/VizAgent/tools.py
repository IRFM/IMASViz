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

# The ADDRESSING block is what lets a tool description stay short: the
# shared words are defined here, once, at the top of every turn, so a
# parameter note no longer has to re-say what `uri`, `path`, `indices` or
# `along` mean. Said once here rather than seventeen times out there --
# measured 10 712 characters of parameter notes, and `uri` alone answered
# in 7 different sentences across 14 tools.
SYSTEM_INSTRUCTIONS = """You are the IMASViz assistant for ITER/CEA plasma-fusion data analysis.
You control the GUI strictly through the provided tools.

### MANDATORY WORKFLOW
1. `manage_case(action="open", uri)` -> Open the shot.
2. `manage_idss(action="filled", uri)` -> Check which IDSs and occurrences
   actually exist in the case.
3. `manage_idss(action="load", uri, ids_name, occurrence)` -> Load the
   required IDS into the tree.
4. `inspect_tree(action="search")` or `inspect_tree(action="quantities")` -> Find exact leaf paths.
5. `plot(mode=...)` or `get_signal(...)` -> Draw curves or read numerical values.
   `mode` is the shape of the drawing: "single" one quantity, "slice" one
   profile at one instant, "selection" what was selected, "table" one panel
   per path, "stacked" the paths stacked in one window.

### ADDRESSING -- one word, one question, said here and not by a tool
- `uri`: the case, spelled as `manage_case(action="list")` named it.
- `ids_name`: an IDS of that case. `occurrence`: Version of an IDS
  (passed to `manage_idss(action="load")`). The two go together and
  `manage_idss(action="filled")` names both for the case.
- `path`: Specific member of a structure array (e.g.,
  `magnetics.flux_loop[2].flux.data`), in any spelling
  `inspect_tree(action="search")` answered. Which member of a family it
  is sits IN the path: to plot two members together, call
  `plot(mode="single")` twice using `into_figure_key` on the second
  call--never put `flux_loop` in `indices`.
- `indices`: 0-based index of a tensor dimension or nested array (e.g.,
  `indices={"psi": 50}`), one entry per array of structures. It pins an
  axis the curve does NOT run along.
- `along`: the axis a curve runs along. `time`: one instant -- the value
  the user asked AT, not the value the case holds there.
- `figure_key`: a window of curves; `window`: any window on the screen.
  Both spelled as an answer or `manage_window(action="list")` named
  them, and a window the close box took down keeps its key.
- A group of asks says which one is meant with `action`, `mode`,
  `operation` or `scope`; a call that leaves it out is refused, never
  run on a guess.
- A refusal is an answer: report its reason, then answer again in the
  spelling that refusal names.

### STRICT RULES (NEVER VIOLATE)
- **NO HALLUCINATION:** Never invent IDS names, paths, numbers, figure keys, or file paths. Only state facts returned by a tool in this session.
- **NO FAKE ACTIONS:** Never say you plotted a curve, wrote a report, or saved a note unless the corresponding tool returned `error: null` in this turn. If a tool fails or refuses, report the exact refusal reason.
- **MULTIPLE FAMILIES:** When asked to plot two different families (e.g., probes then flux loops), create two separate figures unless the user explicitly asks to overlay them ("sur la même figure" / "on the same figure").
- **WINDOWS & FOCUS:** Do NOT call `manage_window(action="focus")` or `manage_window(action="show")` automatically after plotting. Only call them if the user explicitly asks to bring a window to the front.
- **ONE WINDOW PER ASK:** A plugin entry and the tool that entry answers draw the same window. Ask one, not both.
- **PLUGIN WINDOWS ARE ASKED FOR:** The calls that set the field up are never an ask -- `manage_case(action="open")`, `manage_idss(action="filled")`, `manage_idss(action="load")`, `plugin(action="list")` -- run one whenever the work needs it. A plugin window is: never call `plugin(action="run")` unless the user's own request asks for a plugin or names that plugin; loading an IDS never asks for a window.
- **PICTURES:** A screenshot is a picture you cannot read. Say what a figure shows from the arrays `get_signal` answers, never from the PNG.
- **DESTRUCTIVE & SHARED ACTIONS:** Never call `manage_window(action="close")`, `manage_case(action="close")`, `manage_session(action="new")`, or write with `scope="shared"` (`manage_note`, the prompt tools) unless the user explicitly asks for it in their prompt. Nor write anything they did not ask for: a note, a prompt filed, a report, a session saved. A turn that only drew a figure is not an ask to file its wording.
- **AMBIGUITY:** If a user request is ambiguous (e.g., "sonde 2" when multiple probes exist), list the exact paths found by `inspect_tree(action="search")` and ask the user to choose.

### RESPONSE FORMAT
- Keep answers concise, factual, and grounded in tool outputs.
- Use `code` formatting for IMAS paths and figure keys (e.g., `Plot1`).
- Use **bold** for the key idea and *italic* for a node or unit name.
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
``manage_idss(action="filled")``, ``plot``, ``get_signal`` -- and
inviting the user to switch the agent back to a shape where it runs, the
tools back on.
The user asks a question, you answer it in the shape you can answer in."""


# What a parameter note is for, and what it is not for.
#
# A note says what a value IS and how it is spelled -- the half of the
# question a call cannot settle for itself. What a call REQUIRES, and which
# of its actions takes a word at all, is answered by the call's own
# validation: the rows of ``ACTION_PARAMETERS`` below drive
# ``missingParameters`` and ``unknownParameters``, and both refusals name
# the action, the word, and the call to answer with. Prose that recites an
# enforced rule is paid at every turn and answers nothing the model did not
# already get back in the refusal.
#
# So a note has a length, as a description has one (test_176 refuses the
# drift in both): 15 words for a parameter word several tools take, 25 for
# one a single tool takes. The ratio is the wire, not style: the format has
# no reference, so a word fourteen tools take is paid fourteen times, and
# a word one tool takes may afford its example.
#
# A shared word has one wording, spelled once here and referenced by every
# schema that takes it: a model that meets ``uri`` phrased three ways has
# three things to learn, and a call refused on a wording the schema did not
# use is a refusal it cannot answer. Silence stays legal -- a word the
# ADDRESSING block above already answers needs no note beside it -- and
# this table is exactly that block's vocabulary: test_176 asks that every
# word of it is answered up there, so the block and the notes cannot drift
# apart. What is not legal is a second wording.
#
# A word the block does not answer is not shared, and a word whose meaning
# changes with the tool that takes it is not shared either; both stay
# spelled where they are used, under the same cap: ``path`` is a leaf in
# six tools and a file in manage_session; ``name`` is a written page in
# five and a prompt's identity in manage_prompt; ``paths`` and ``curve``
# are too local for the block to carry; ``dd_version`` pins a case at open
# in one tool and states the dictionary a copy is written in in another;
# ``scope``, ``kind``, ``mode`` and ``operation`` are each tool's own
# discriminant.
SHARED_NOTES = {
    'uri': 'the case, as manage_case(action="list") named it: '
           'imas:hdf5?path=... or an UDA one',
    'ids_name': 'the IDS the ask is about, by its root name '
                '(equilibrium, magnetics)',
    'occurrence': 'which occurrence of that IDS, counting from 0; 0 left '
                  'out',
    'figure_key': 'the window of curves the ask is made on, by its key',
    'window': '"app" for the application, a figure key, or a case URI for '
              'its shot view',
    'along': 'the axis to run along: "time", or one of the leaf\'s own axis '
             'names ("psi")',
    'indices': 'axis name -> 0-based index, for each axis not run along: '
               '{"psi": 50}',
    'time': 'one instant, in seconds, on the clock of the case',
}


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
    #
    # A URI is spelled as `manage_case(action="list")` answered it, in either
    # shape the Access Layer takes (an `imas:hdf5?path=...` file or an UDA
    # one). "close" takes the shot view and the windows that serve this case
    # alone out of the bookkeeping for good; a window that serves another
    # case too is hidden and keeps its key, because that other case still
    # reads a live curve out of it. One window that refuses in the middle of
    # the list is named and the rest of the case is still taken care of.
    _tool(
        'manage_case',
        'The cases this session works on, and `action` says which ask. '
        '"open": one IMAS case by URI; `dd_version` pins the data '
        'dictionary, left out the case is asked which one its own IDSs '
        'were written with. "list": the cases open, with their loaded '
        'occurrences. "close": one open case, its view, its windows and '
        'its bookkeeping, for good.',
        {'type': 'object', 'properties': {
            'action': {'type': 'string', 'enum': ['open', 'list',
                                                  'close']},
            'uri': {'type': ['string', 'null'],
                    'description': SHARED_NOTES['uri']},
            'dd_version': {'type': ['string', 'null'],
                           'description': '"open": the data dictionary to '
                                          'pin the case at'},
        }, 'required': ['action'], 'additionalProperties': False},
    ),
    # The three asks about the IDSs of a case: what its data dictionary
    # declares, which of those the case actually fills, and the load of one
    # occurrence into the tree. All three ask the same case by URI, so the
    # group can require `uri` beside its discriminant -- and the rows of
    # `ACTION_PARAMETERS` are what say that "load" is nothing without the
    # IDS it loads, and that an `ids_name` beside "filled" is a word that
    # went to the wrong ask.
    #
    # "filled" is read through the entry's own occurrence listing, so the
    # names and counts come off the case and not out of a recall. "load" is
    # synchronous -- an occurrence whose tree is still being built is an
    # empty window -- and `slices` decides how much of the dynamic array the
    # walk keeps: "first" is the slice a plain load keeps, "all" walks the
    # whole array, which on a big IDS is the difference between thousands of
    # signals and hundreds of thousands.
    _tool(
        'manage_idss',
        'The IDSs of a case, and `action` says which ask. "declared": '
        'every IDS its dictionary declares, the roots that hold no data '
        'included. "filled": only the IDS the case holds -- the answer to '
        '"what is in this case", never a recalled one. "load": one '
        'occurrence of one IDS into the tree, keeping "first" slice or the '
        'whole dynamic array per `slices`.',
        {'type': 'object', 'properties': {
            'action': {'type': 'string', 'enum': ['declared', 'filled',
                                                  'load']},
            'uri': {'type': 'string',
                    'description': SHARED_NOTES['uri']},
            'ids_name': {'type': ['string', 'null'],
                         'description': SHARED_NOTES['ids_name']},
            'occurrence': {'type': ['integer', 'null'],
                           'description': SHARED_NOTES['occurrence']},
            'slices': {'type': ['string', 'null'],
                       'enum': ['first', 'all'],
                       'description': '"load": how much of the dynamic '
                                      'array the load keeps; "first" when '
                                      'left out'},
        }, 'required': ['action', 'uri'], 'additionalProperties': False},
    ),
    # One name for the four ways the tree answers a question about itself:
    # which leaves the case holds, what one of them holds, what the data
    # dictionary says about an IDS, and what one occurrence can be drawn as.
    # The discriminant is `action`: no member of the group takes a word of
    # its own (test_175 refuses a discriminant a member already answers for
    # itself). `uri` is required of the offer because the four ask a case;
    # `path` and `ids_name` are not common, so each member names the one it
    # cannot do without, and the refusal of that member asks for it.
    #
    # What the sentence no longer has room for, and what the answer says
    # anyway: a search query is matched case-insensitively and each hit
    # carries its three spellings -- any is what a plot takes -- beside the
    # `kind` a plot would make of it, `curve`, `image` or `scalar`. The node
    # answer is what the application documentation says, so it counts the
    # zero/nan/inf values beside the finite minimum and maximum, and a leaf
    # the tree does not hold is refused by name. The ids answer carries the
    # IDS comment, homogeneous time, units and the version the case was
    # written at, a property the case leaves empty is absent rather than
    # invented, and an IDS the case does not declare is refused naming the
    # ones it does. A scalar (0D) leaf is not a tensor and is not listed; an
    # occurrence whose tree was never built is refused by name, load it with
    # manage_idss(action="load") first.
    _tool(
        'inspect_tree',
        'What the tree of a case says, and `action` says which ask. '
        '"search": the leaves whose spelling carries `query`; each match '
        'answers the spellings a plot takes. "node": what one `path` holds '
        '-- units, size, min/max, a bounded preview. "ids": what the data '
        'dictionary says of an `ids_name`. "quantities": the filled tensors '
        'of one `occurrence`, grouped by the array of structures that '
        'drives them -- the "what can be drawn" answer.',
        {'type': 'object', 'properties': {
            'action': {'type': 'string',
                       'enum': ['search', 'node', 'ids', 'quantities']},
            'uri': {'type': 'string',
                    'description': SHARED_NOTES['uri']},
            'query': {'type': ['string', 'null'],
                      'description': '"search": the substring a leaf '
                                     'spelling must carry, matched '
                                     'case-insensitively; empty answers '
                                     'every leaf'},
            'ids_name': {'type': ['string', 'null'],
                         'description': SHARED_NOTES['ids_name']},
            'occurrence': {'type': ['integer', 'null'],
                           'description': SHARED_NOTES['occurrence']},
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
    #
    # "select" puts the paths in as the tree clicks would and answers the
    # paths it took beside the new size; "list" is the one that spells each
    # leaf -- data name, IDS, occurrence -- in the order the leaves were
    # put in. One path the tree does not hold stops the whole call: nothing
    # goes in, so a selection is never half-applied.
    _tool(
        'manage_selection',
        'What the case selection holds and what to do with it, and '
        '`action` says which ask. "select": the named `paths` go in -- one '
        'the tree does not hold is refused by name and nothing goes in. '
        '"clear": empty it, answering how many were dropped. "list": the '
        'selection in the order it was put in; empty answers count 0, not '
        'a refusal.',
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
    #
    # What the sentence no longer has room for: the answer's `curves` is
    # read off the window itself after the draw, so a claim that a curve
    # stands on a figure stands on that list and not on a memory of the
    # call (test_137 reads the joined figure back the same way); a mode
    # asked without what it takes is refused by naming the parameter, and
    # `time` beside `along` is refused as the two opposite readings they
    # are. "slice" outside the case's range answers the nearest slice.
    #
    # What the parameter notes no longer say, and what the code answers
    # anyway: `mode` carries no note, because the sentence above and the
    # ADDRESSING block of the instruction spell the five shapes. The clock
    # is answered by "time", "temps" and "t" alike, and an `along` left out
    # is the clock when the leaf holds one. `indices` takes one entry per
    # array of structures (`time_slice`, `profiles_1d`, `ion`) as well as
    # the leaf's own coordinate, several nested arrays each on its own. A
    # `time` beside "single" pins the profile on one slice of its dynamic
    # array, and the answer names `time_requested` and `time_slice_time`
    # apart -- the value asked at and the slice that answered it. An
    # `into_figure_key` left out opens a window of its own, which is what
    # an ask naming two families wants: two windows, not one of four.
    _tool(
        'plot',
        'What shape to draw in, and `mode` picks it. "single": one '
        '`path` into the figure its own axes call for -- a curve for one '
        'axis to draw, a picture window for two. "slice": one `path` read '
        'at one `time`. "selection": what the case selection holds. '
        '"table": one panel per `paths` in a Table Plot View. "stacked": '
        '`paths` stacked, one panel each, in one window. The answer names '
        'the figure key and `curves`, the curves on it after the call.',
        {'type': 'object', 'properties': {
            'mode': {'type': 'string',
                     'enum': ['single', 'slice', 'selection', 'table',
                              'stacked']},
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
                      'description': SHARED_NOTES['along']},
            'indices': {'type': ['object', 'null'],
                        'description': SHARED_NOTES['indices'],
                        'additionalProperties': {'type': 'integer'}},
            'into_figure_key': {
                'type': ['string', 'null'],
                'description': 'The key of an open window to add this to; '
                               'left out, a new window. "sur la même '
                               'figure", "superposées" ask for it.'},
            'time': {'type': ['number', 'null'],
                     'description': SHARED_NOTES['time']},
            'time_interp': {'type': ['boolean', 'null'],
                            'description': '"single": true interpolates '
                                           'between the two slices that '
                                           'bracket `time`, and the answer '
                                           'names the value asked at; '
                                           'false takes the nearest '
                                           'slice.'},
            'occurrence': {'type': 'integer', 'default': 0,
                           'description': SHARED_NOTES['occurrence']},
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
    #
    # What the sentence no longer has room for, and what the window and the
    # answer carry anyway: each of the two asks opens a window of its own,
    # so neither one joins a figure that stands. A surface frame draws the
    # psi levels, the plasma boundary, the magnetic axis, the O-point and
    # the limiter, and the frames of one window stand at equal bounds so
    # they can be compared.
    # The profiles under `at_time` are q, elongation, the triangularities,
    # j_tor [MA/m^2], pressure [kPa], f_df_dpsi and dpressure_dpsi, against
    # rho_tor_norm; its answer adds the slice's global quantities -- Ip
    # [kA], q95, q_axis, li_3, W_mhd [kJ] and the axis position. An instant
    # is settled on the nearest slice the case holds and named back
    # (`time_requested` beside `time_slice_time`). The `equilibriumsurfaces`
    # plugin entries answer these same two asks, which is what the shared
    # ONE WINDOW PER ASK rule is for: ask one, not both.
    _tool(
        'equilibrium',
        'The equilibrium as the Equilibrium plugin draws it, and `action` '
        'says which ask. "surfaces": one frame per instant of `times`, '
        'side by side in one window. "at_time": one `time` with its radial '
        'profiles under it and the slice global quantities in the answer. '
        'An instant outside the case answers its nearest slice, named '
        'back.',
        {'type': 'object', 'properties': {
            'action': {'type': 'string', 'enum': ['surfaces', 'at_time']},
            'uri': {'type': 'string'},
            'times': {'type': ['array', 'null'],
                      'items': {'type': 'number'},
                      'description': '"surfaces": the instants in the case '
                                     'clock, seconds, e.g. [40, 44, 48]'},
            'time': {'type': ['number', 'null'],
                     'description': SHARED_NOTES['time']},
            'occurrence': {'type': 'integer', 'default': 0},
        }, 'required': ['action', 'uri'], 'additionalProperties': False},
    ),
    # The read of one leaf, offered as a name the model may type. What the
    # two halves of this tool are for is said here and not in the sentence:
    # the answer is the SAME element a figure of that leaf draws, because
    # both go through the one resolver and take the one `along` + `indices`
    # schema (test_125 pins that both DECLARE the pair). The legacy spelling
    # of that pair is kept because the surfaces were written against it; it
    # answers one axis and pins one position, which is all the pair is.
    _tool(
        'get_signal',
        'The values the tree read gives for one leaf, as JSON, on the same '
        '`along` + `indices` schema `plot(mode="single")` uses: the same '
        'element a figure of that leaf draws. `as_function_of_time` and '
        '`coordinate_index` are the legacy spelling of that pair.',
        {'type': 'object', 'properties': {
            'uri': {'type': 'string'},
            'path': {'type': 'string'},
            'as_function_of_time': {'type': ['boolean', 'null'],
                                    'description': 'legacy: one axis. '
                                                   'Prefer `along` + '
                                                   '`indices`.'},
            'along': {'type': ['string', 'null'],
                      'description': SHARED_NOTES['along']},
            'indices': {'type': ['object', 'null'],
                        'description': SHARED_NOTES['indices'],
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
    #
    # What the sentence no longer has room for: scale, shift and normalize
    # are put on the drawn values in place, so asking the figure again
    # answers what the hand made of them, and `reset` -- which answers what
    # was put on -- takes the lot off and leaves the data the curve was
    # drawn with. "remove" leaves the figure with one curve less. A table
    # or a stacked window is not one figure and is refused by name, since
    # its panels are drawn from quantities, not from curves a hand holds.
    _tool(
        'transform_curve',
        'Do one thing to the curve(s) a figure already holds, and '
        '`operation` picks it. "scale" times `factor`, "shift" plus '
        '`offset`, "normalize" divided by a reference of their own '
        '(`reference`), "reset" back to the data they were drawn with, '
        '"remove" off the figure. scale, shift and normalize work in '
        'place, so read_figure answers the transformed value while the '
        'leaf in the tree is unchanged.',
        {'type': 'object', 'properties': {
            'figure_key': {'type': 'string'},
            'operation': {
                'type': 'string',
                'enum': ['scale', 'shift', 'normalize', 'reset',
                         'remove']},
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
    #
    # What the sentence no longer has room for, and what the answers say:
    # a range is two bounds, so one of a pair alone is refused rather than
    # guessed at the other end; moving or resizing a picture band re-reads
    # its pictures in place and leaves where it is the colour scale a hand
    # settled; a slider row is named as the band spells it; and a table or
    # a stacked window is refused by name, its panels having no span, band
    # or axis of their own to move.
    _tool(
        'configure_axes',
        'Move one thing a window draws to, and `operation` picks it. '
        '"range" pins the span of its axes (`xmin`/`xmax` and/or '
        '`ymin`/`ymax`, a pair at a time; `auto=true` clears the pins). '
        '"image_window" moves (`start`) or resizes (`count`) the band of '
        'pictures a picture window sits on. "slice_index" poses one slider '
        'row (`axis`) at `index`. "log" makes an axis log or linear '
        '(`x`/`y`), refused where the values cross zero, and carries a '
        'pinned span across the scale. "invert" turns one around.',
        {'type': 'object', 'properties': {
            'figure_key': {'type': 'string'},
            'operation': {
                'type': 'string',
                'enum': ['range', 'image_window', 'slice_index', 'log',
                         'invert']},
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
    #
    # What the sentence no longer has room for: both reads take the curve
    # as it stands on the figure, so a transform a hand put on it (a log
    # axis, an inversion, a scale) is in the answer and in the file, while
    # the leaf in the tree is left as it is -- nothing here writes back.
    _tool(
        'read_figure',
        'What the curve(s) a figure holds answer, and `action` says which '
        'ask. "stats": the sample count, the finite min/max/mean/std, the '
        'nan/inf counts, the peak with its abscissa. "export": the same '
        'values in a file under ~/.imasviz/exports. Both read the values '
        'as they stand: a transform a hand put on the figure is in the '
        'answer.',
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
    # parameter four actions share for three different reasons, so the
    # sentence says which is which; the note on the word is the group's,
    # shared with every other tool that takes it.
    #
    # What the sentence no longer has room for, and what the answers say
    # anyway: an `elm` is an excursion up, a `sawtooth` a crash down, an
    # `lh` a threshold crossing, and each kind gates itself -- `threshold` /
    # `prominence` / `min_distance` for the first two, `threshold` /
    # `direction` / `hysteresis` for the crossing -- a kind refusing a gate
    # it does not take, by name. The signal detected is the one
    # ``get_signal`` answers for that leaf, so a detection and a figure of
    # the same leaf are one read; the marks it puts on a `figure_key` are
    # capped at 40 and refused when they would be a wall, and "clear_events"
    # answers how many it took off, being safe when the figure holds none.
    # A flat or too-short series is refused, and so is a pair of leaves the
    # case does not hold on one clock or at one length; the lag "correlate"
    # answers comes in samples and in time, with the correlation at the peak
    # and the frequency the two share. A report is self-contained HTML in
    # ``~/.imasviz/reports``, taking the figure's picture only when one is
    # named.
    _tool(
        'analyze_signal',
        'What one leaf\'s signal says, and `action` says which ask. '
        '"events": the events of one `kind`, gated by the parameters that '
        'kind takes. "clear_events": those marks off a curve figure. '
        '"spectrum": the dominant frequency, the leading `n_peaks` by '
        'power, the power between `band_low` and `band_high`. '
        '"correlate": how far `path_b` lags or leads `path`, and at what '
        'the two oscillate together. "events_report" and "spectrum_report": '
        'the same two answers as an HTML page in ~/.imasviz/reports. '
        '`figure_key` is the figure the marks or the picture go on.',
        {'type': 'object', 'properties': {
            'action': {'type': 'string',
                       'enum': ['events', 'clear_events', 'events_report',
                                'spectrum', 'correlate', 'spectrum_report']},
            'uri': {'type': 'string',
                    'description': SHARED_NOTES['uri']},
            'path': {'type': 'string',
                     'description': 'the leaf; for "correlate", the first of '
                                    'the two series.'},
            'path_b': {'type': 'string',
                       'description': '"correlate": the second series, '
                                      'lagged against the first.'},
            'kind': {'type': 'string',
                     'enum': ['elm', 'sawtooth', 'lh'],
                     'description': '"events" and "events_report": which '
                                    'event; a kind refuses a gate it does '
                                    'not take'},
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
                                       'how many peaks; five left out'},
            'band_low': {'type': ['number', 'null'],
                         'description': '"spectrum" and "spectrum_report": '
                                        'lower band bound, in Hz'},
            'band_high': {'type': ['number', 'null'],
                          'description': '"spectrum" and "spectrum_report": '
                                         'upper band bound, in Hz'},
            'along': {'type': ['string', 'null'],
                      'description': SHARED_NOTES['along']},
            'indices': {'type': ['object', 'null'],
                        'description': SHARED_NOTES['indices']},
            'indices_b': {'type': ['object', 'null'],
                          'description': '"correlate": the element of the '
                                         'second series fixed by name.'},
            'figure_key': {'type': ['string', 'null'],
                           'description': SHARED_NOTES['figure_key']},
            'name': {'type': ['string', 'null'],
                     'description': '"events_report" and "spectrum_report": '
                                    'the page name; a place, not a name, is '
                                    'refused.'},
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
    #
    # What the sentence no longer holds, and what the answers say: n_G is
    # (I_pl / A) x 1e20, I_pl in mega-Ampere and A in square metre, and the
    # three reads go into that formula as they came out of the case --
    # nothing is converted. So the units are the caller's business, said on
    # the three parameters that take them (m^-3, mega-Ampere, m^2); the
    # IMAS standard triple, `n_e` / `ip` / `area` under
    # `equilibrium.time_slice[i].global_quantities`, is already in those
    # three. The two case numbers are read off
    # `global_quantities.beta_normal` and `profiles_1d.pressure`
    # unless `path` names another leaf, and their formula is deliberately
    # not computed here (p = n_e k_B T_e + n_i k_B T_i): a case that keeps
    # the number is asked for it, and one that does not is refused by name
    # rather than answered with a plausible-looking value. The two that read
    # a leaf answer the path that read it, the values, the points, and the
    # mean, max and min.
    _tool(
        'derived_quantity',
        'A number a case is judged on; `quantity` says which. '
        '"greenwald": f_G = n_e / n_G, over three leaves the caller names '
        '(`n_e_path`, `ip_path`, `area_path`) -- formula and numbers from '
        'the case. "beta_normal" and "total_pressure": the case\'s own '
        'numbers, off the leaf it keeps them in, never computed here. A '
        'leaf the case lacks, or three at different lengths, is refused '
        'by name.',
        {'type': 'object', 'properties': {
            'quantity': {'type': 'string',
                         'enum': ['greenwald', 'beta_normal',
                                  'total_pressure']},
            'uri': {'type': 'string',
                    'description': SHARED_NOTES['uri']},
            'n_e_path': {'type': 'string',
                         'description': '"greenwald": the electron density, '
                                        'in m^-3, over time'},
            'ip_path': {'type': 'string',
                        'description': '"greenwald": the plasma current, in '
                                       'mega-Ampere -- the formula converts '
                                       'nothing'},
            'area_path': {'type': 'string',
                          'description': '"greenwald": the cross-section, in '
                                         'm^2, over time'},
            'path': {'type': ['string', 'null'],
                     'description': '"beta_normal" and "total_pressure": the '
                                    'leaf to read, or the one this case '
                                    'keeps it in'},
            'along': {'type': ['string', 'null'],
                      'description': SHARED_NOTES['along']},
            'indices': {'type': ['object', 'null'],
                        'description': SHARED_NOTES['indices']},
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
    #
    # What the sentence no longer has room for: the read of each shot is
    # the one a figure of that leaf would draw, "values" answers the
    # per-shot values, the least-squares slope over the shot index, the
    # first-to-last change, the direction, and the min and max with the
    # shots they came from, and "report" dresses exactly that -- the
    # per-shot table, the trend, the line the values make -- as a
    # self-contained page, nothing taken from memory. Three answers come in
    # words rather than numbers: a campaign of one shot (the schema already
    # asks for two), a shot the case does not hold the leaf in, and a
    # series whose values are all equal.
    _tool(
        'trend_campaign',
        'What one leaf does across a series of shots, and `action` picks '
        'the ask. "values": one value per shot -- `at` an index of its '
        'curve or `which` over it -- then the slope over the shot index, '
        'the first-to-last change, min and max. "report": that answer as '
        'an HTML page under ~/.imasviz/reports.',
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
    #
    # What the sentence no longer has room for, and where it stands: the
    # size keep is on the two parameters that take pixels -- a side left out
    # keeps the size the window holds on that side, and the gesture test
    # (test_122) reads the size back off the answer. "close" deleting a
    # window and forgetting its key is refused on a call that names no
    # window; the destructive half of that is the instruction's. A window
    # that is on screen but not in front is "focus", and a window named
    # `app` is the application, raised with no figure touched; a side that
    # is not a pixel count and a name the session does not hold are both
    # refused, the second from the open ones.
    _tool(
        'manage_window',
        'What one window of the session is asked to do, and `action` says '
        'which. "list": every window -- kind, label, key, on screen or not. '
        '"show": put a hidden window back on the screen; "hide": take it '
        'off without deleting it. "close": delete it and forget its key. '
        '"focus": the user\'s "show me this" command -- raised to the '
        'front, resized only when `width` and `height` name the pixels. A '
        'draw is not an ask to show it.',
        {'type': 'object', 'properties': {
            'action': {'type': 'string',
                       'enum': ['list', 'show', 'hide', 'close', 'focus']},
            'window': {'type': 'string',
                       'description': SHARED_NOTES['window']},
            'width': {'type': ['integer', 'null'],
                      'description': '"focus": pixels, 1 and up; left out, '
                                     'the size the window holds'},
            'height': {'type': ['integer', 'null'],
                       'description': '"focus": pixels, 1 and up; left out, '
                                      'the size the window holds'},
        }, 'required': ['action'], 'additionalProperties': False},
    ),
    # Two asks about the plugins of a case, and they answer each other: "list"
    # names the plugin and numbers the entry that "run" then takes back. Both
    # ask a case, so the group requires `uri` beside its discriminant. What the
    # rows of `ACTION_PARAMETERS` answer is the other half: a "run" without its
    # `entry` is an incomplete call, and a `plugin` beside "list" is a word
    # that went to the wrong ask.
    #
    # What the sentence no longer has room for: "list" answers the entries
    # in registration order, the feature number, its label and its
    # description for each, and beside them the refusals of the plugins the
    # case cannot offer. "run" hands `occurrence` and `time` instead of
    # letting the entry ask them, because a modal window asked on a surface
    # that answers in the user's place holds the whole session; an entry
    # that asks an instant and is handed none is therefore refused by name,
    # and so is an entry the case does not offer. `ids_name` left out of
    # "run" is resolved from the case, several branches earning that entry
    # being refused with them named. The entry draws its own window: `drawn`
    # names the ones it opened or redrew, `reused` the one it drew again --
    # the same entry with the same answers draws into the window that
    # already stands rather than another over it.
    _tool(
        'plugin',
        'The plugins a case offers, and `action` says which ask. "list": '
        'the entries an IDS root earns, beside the refusals of the plugins '
        'that case cannot offer. "run": one entry, with `occurrence` and '
        '`time` handed instead of asked; the same entry asked again draws '
        'into the window that stands, and `drawn` names what came back.',
        {'type': 'object', 'properties': {
            'action': {'type': 'string', 'enum': ['list', 'run']},
            'uri': {'type': 'string',
                    'description': SHARED_NOTES['uri']},
            'ids_name': {'type': ['string', 'null'],
                         'description': SHARED_NOTES['ids_name']},
            'plugin': {'type': ['string', 'null'],
                       'description': '"run": the plugin, as "list" named it'},
            'entry': {'type': ['integer', 'null'],
                      'description': '"run": the entry number, as "list" '
                                     'numbered it'},
            'occurrence': {'type': ['integer', 'null'],
                           'description': SHARED_NOTES['occurrence']},
            'time': {'type': ['number', 'null'],
                     'description': SHARED_NOTES['time']},
        }, 'required': ['action', 'uri'], 'additionalProperties': False},
    ),
    # One name for the run as a thing kept: written, put back, cleared, and
    # the files beside it that a run is made of. The discriminant is
    # `action`: no member of the group takes a word of its own (test_175
    # refuses a discriminant a member already answers for itself), and
    # `name` could not be one -- it is a SESSION file for "save"/"restore"
    # and a CONFIGURATION file for the three asks that read or write one. So
    # the parameters are told apart in their own blocks, the same way the
    # rows of `ACTION_PARAMETERS` tell them apart when a call is checked.
    #
    # What the sentence no longer has room for, and what the answers say:
    # "save" writes the cases, the loads, the selection, the windows and
    # what a hand styled on them. "restore" replays the gestures rather
    # than rebuilding widgets, so a put-back window owns its sliders, and
    # a case that cannot be opened costs its own windows and names the file
    # and the URI. "new" answers how many windows it closed, leaves the
    # sessions the user saved on disk -- `last_session` among them -- and
    # the reports where they are, and is the *New session* of the *File*
    # menu asked the way the page asks it: like that menu's close it is a
    # gesture the user asks for out loud, and a request that names no clean
    # slate is a refusal, not a reset. "list_sessions" answers the .vsess
    # files as the application lists them and "list_configurations" the
    # .pcfg and .lsp ones; a kind the application does not answer is
    # refused by name, "session" among them, the sessions being
    # "list_sessions". "apply" loads first the IDSs the case would need and
    # does not hold, the way the menu does it, reads a .lsp as a .pcfg,
    # answers how many were selected, and refuses a name the folder does not
    # hold naming the ones it does. "save_selection" writes one quantity per
    # selected node and refuses nothing selected by name.
    # "save_plot_configuration" writes the quantities of a Table Plot View's
    # panels and the place each held; any other window is refused by name
    # and manage_window(action="list") names the ones that hold panels.
    #
    # What the two file words no longer spell, and who answers it: `name` is
    # asked of "apply", "save_selection" and "save_plot_configuration" -- the
    # rows above refuse a call that leaves it out --, a "save" without one
    # settles on a name of its own under the configuration folder, and both
    # a session and a configuration are named without their extension.
    _tool(
        'manage_session',
        'The run kept and read back, and `action` says which ask. "save": '
        'the whole screen as the application writes it. "restore": one of '
        'those sessions put back, naming the cases that came back. "new": '
        'a clean session WITHOUT saving -- every case view and figure '
        'closed, nothing written; the user asks for it out loud. '
        '"list_sessions": the .vsess files. "list_configurations": the '
        '.pcfg and .lsp files, `kind` narrowing to one. "apply": one saved '
        'configuration put on a case, its quantities selected and the IDSs '
        'it needs loaded first. "save_selection": the case selection as a '
        '.lsp. "save_plot_configuration": one Table Plot View as a .pcfg.',
        {'type': 'object', 'properties': {
            'action': {'type': 'string',
                       'enum': ['save', 'restore', 'new', 'list_sessions',
                                'list_configurations', 'apply',
                                'save_selection',
                                'save_plot_configuration']},
            'name': {'type': ['string', 'null'],
                     'description': 'the session or configuration the ask '
                                    'is about, with no extension spelled'},
            'path': {'type': ['string', 'null'],
                     'description': '"save" and "restore": a full file '
                                    'name, instead of a name in the '
                                    'configuration folder'},
            'kind': {'type': ['string', 'null'],
                     'enum': ['plot', 'selection'],
                     'description': '"list_configurations": one kind only; '
                                    'left out, both are answered'},
            'uri': {'type': ['string', 'null'],
                    'description': SHARED_NOTES['uri']},
            'figure_key': {'type': ['string', 'null'],
                           'description': SHARED_NOTES['figure_key']},
        }, 'required': ['action'], 'additionalProperties': False},
    ),
    # One name for the three pages a request can ask for, because the three
    # are the same ask -- put what the session knows where the user can open
    # it -- and `scope` answers which page. The discriminant is `scope` and
    # not `action`: `action` is the word the other groups answer with, and a
    # group naming a discriminant its own members already take is the
    # confusion this table exists to end (test_175).
    #
    # What the sentence no longer holds: this is the "rapport" / "report"
    # the user asks for, and "case_ids" is the "inventaire du cas". A report
    # is one window, so a report of more than one plot is one call per plot,
    # and the page lists the ones a request wrote together. "plot" refuses a
    # window that draws no curve it could stat; "case_loaded" is one row per
    # curve the loaded tree holds -- an IDS not yet loaded is not a curve,
    # so the answer says how many curves it gave and
    # ``manage_idss(action="declared")`` names what the case still holds --
    # and a loaded tree with no curve is refused. "case_ids" adds, per
    # loaded occurrence, the header of its ``ids_properties`` and the
    # signals the tree carries as available for it (the same test its own
    # colouring applies, a 0-D scalar held by the dynamic array among them);
    # a property left empty is named empty, an occurrence without an
    # available signal is named as such, and a case holding no data at all
    # is refused. A `name` that names a place is refused by every scope.
    _tool(
        'generate_report',
        'A self-contained HTML page in ~/.imasviz/reports; `scope` says '
        'which. "plot": one window of curves -- its image and one row per '
        'trace it drew, saying the quantity, the samples and the counts. '
        '"case_loaded": one row per curve the loaded tree of a case holds. '
        '"case_ids": every IDS the case\'s dictionary holds, the '
        'occurrences each holds, and which the session loaded.',
        {'type': 'object', 'properties': {
            'scope': {'type': 'string',
                      'enum': ['plot', 'case_loaded', 'case_ids']},
            'figure_key': {'type': 'string',
                           'description': SHARED_NOTES['figure_key']},
            'uri': {'type': 'string',
                    'description': SHARED_NOTES['uri']},
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
    # The explicit picture ask, and the one answer the model cannot read: on
    # this stack the PNG is handed to the transcript as a file, not as pixels
    # the endpoint parses, so an answer that describes what a picture shows
    # describes what it never read. The way to say what a figure shows is to
    # read the arrays under it, with get_signal; the way to make a picture
    # readable is to size its window first, with manage_window(action=
    # "focus"), which answers the size the window then holds.
    _tool(
        'get_screenshot',
        'The explicit picture ask: a window as it stands, in PNG. The '
        'picture is the size the window holds, so size it first with '
        'manage_window(action="focus") when the picture has to be '
        'readable.',
        {'type': 'object', 'properties': {
            'window': {'type': 'string', 'default': 'app',
                       'description': SHARED_NOTES['window']},
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
    #
    # The sentence is short on purpose, and so are the notes: the word
    # budget says what a tool may hold, and what every one of these eight
    # asks shares -- where the two journals live, that a write to the
    # shared one is a line others read and stands only on the user's own
    # ask -- is said once in the instruction, not eight times here. What the
    # `scope` note no longer spells is answered the same way: required of
    # "read", "add", "edit" and "delete", left out of the three that ask
    # both journals; "personal" under ~/.imasviz/journals, "shared" under
    # the folder SharedJournalDir names.
    _tool(
        'manage_note',
        'The lab notebook of the two journals, and `action` says which '
        'ask. "search": the filters narrow to the notes that name them, '
        '`query` ranks them, and the answer names the `method` it ranked '
        'by. "list": the same filters without a query, newest first. '
        '"read": one `note_id` whole. "add": one new note, `text` '
        'required. "edit": one note changed in place; a field left out '
        'keeps what it held. "delete": one note, gone. "stats": what the '
        'two journals are on this node, and the endpoint a search ranks '
        'with. "reindex": the journals in step with their index. A '
        '`note_id` a journal lacks is refused by name.',
        {'type': 'object', 'properties': {
            'action': {'type': 'string',
                       'enum': ['search', 'list', 'read', 'add', 'edit',
                                'delete', 'stats', 'reindex']},
            'scope': {'type': ['string', 'null'],
                      'enum': ['personal', 'shared', None],
                      'description': 'which journal: "personal", or '
                                     '"shared" under the folder '
                                     'SharedJournalDir names; left out, '
                                     'both'},
            'note_id': {'type': 'string',
                        'description': '"read", "edit" and "delete": the '
                                       'id "search" and "list" answer by '
                                       '(a file name without .md)'},
            'query': {'type': ['string', 'null'],
                      'description': '"search": the text to rank by; '
                                     'left out, newest first'},
            'limit': {'type': 'integer',
                      'description': '"search": how many notes'},
            'text': {'type': ['string', 'null'],
                     'description': '"add": the body, required. "edit": '
                                    'the new body; left out, the one the '
                                    'note held'},
            'machine': {'type': ['string', 'null'],
                        'description': 'a filter of "search" and "list", '
                                       'a field of "add" and "edit"'},
            'campaign': {'type': ['string', 'null'],
                         'description': 'a filter of "search" and "list", '
                                        'a field of "add" and "edit"'},
            'shot': {'type': ['string', 'null'],
                     'description': 'a filter of "search" and "list", a '
                                    'field of "add" and "edit"'},
            'date': {'type': ['string', 'null'],
                     'description': '"add" and "edit": the shot date, '
                                    'ISO 8601 YYYY-MM-DD'},
            'date_from': {'type': ['string', 'null'],
                          'description': '"search" and "list": ISO 8601 '
                                         'YYYY-MM-DD, inclusive'},
            'date_to': {'type': ['string', 'null'],
                        'description': '"search" and "list": ISO 8601 '
                                       'YYYY-MM-DD, inclusive'},
            'author': {'type': ['string', 'null'],
                       'description': 'a filter of "search" and "list"; '
                                      'the writer on "add", $USER left '
                                      'out'},
            'title': {'type': ['string', 'null'],
                      'description': '"add" and "edit": the note\'s '
                                     'title'},
        }, 'required': ['action'], 'additionalProperties': False},
    ),
    # One name for the corpus of documents the agent reads for itself: what
    # it holds, what it answers to a question, one document of it whole, the
    # store put in step with the folder, and its state. The discriminant is
    # `action`: no member of the group takes a word of its own (test_175
    # refuses a discriminant a member already answers for itself). `rel`
    # keeps the spelling the answers already use: a search hit names the
    # document it came from by that word, so the read asks with it.
    #
    # What the short sentence leaves out stands in the answers themselves:
    # a store written under another embedding endpoint holds vectors in a
    # different space than the query, so the keyword alone ranks and
    # `guarded` says so; "reindex" keeps what it has, embeds what moved
    # and drops what left the folder; an unnamed AgentDocsDir is a
    # refusal that names it, as an unnamed shared journal folder is.
    _tool(
        'manage_documents',
        'The corpus the agent reads for its own RAG, in the AgentDocsDir '
        'folder; `action` says which ask. "list": the corpus as named, '
        'with the `rel` a search answers by. "search": the ranked chunks, '
        'naming the `method` it ranked with. "read": one document whole, '
        'by its `rel`. "reindex": the corpus in step with its store. '
        '"stats": how many documents and chunks, under which endpoint. A '
        'store under another embedding endpoint answers `guarded` and '
        'ranks by keyword alone.',
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
    #
    # What the short sentence leaves out is what the answers say anyway:
    # a hole is filled from the first source that answers it -- what the
    # call names in `values`, what was typed last time for that prompt,
    # what the session knows (its open case, its one open window), what
    # the file declares -- and the answer names which one it was, never
    # a guess. An unnamed SharedPromptsDir costs its own half of a list
    # and is named in `catalogues_unavailable`; an edit keeps the id the
    # pages, the sessions and the remembered values read a prompt under;
    # "detail" remembers nothing, it is the look and not the typing. That
    # a prompt is filed or taken away only on the user's own words is
    # said once, in the instruction, for every write of that kind.
    _tool(
        'manage_prompt',
        'The prompts the user filed to ask again; `action` picks which. '
        '"list": the prompts with their ids and the holes each opens; '
        '`category` and `query` narrow it. "detail": one prompt whole, '
        'with `values`: what each hole would take now. "fill": the '
        'filled prompt, and nothing run; a hole no source answers is '
        'refused naming it. "save": a new prompt, `text` with its holes '
        'spelled {name}. "edit": one prompt changed in place, keeping '
        'its id. "delete": one prompt out of the catalogue. `scope` is '
        'WHICH catalogue, not which ask.',
        {'type': 'object', 'properties': {
            'action': {'type': 'string',
                       'enum': ['list', 'detail', 'fill', 'save', 'edit',
                                'delete']},
            'name': {'type': 'string',
                     'description': 'the prompt, by id or display name; '
                                    'asked by every action but "list"'},
            'scope': {'type': ['string', 'null'],
                      'enum': ['personal', 'shared'],
                      'description': 'which catalogue; left out, both'},
            'text': {'type': ['string', 'null'],
                     'description': '"save": the body, holes spelled '
                                    '{name}. "edit": its new body'},
            'category': {'type': ['string', 'null'],
                         'description': '"list": a filter. "save" and '
                                        '"edit": where to file it'},
            'description': {'type': ['string', 'null'],
                            'description': '"save" and "edit": one line '
                                           'for the reader of the list'},
            'variables': {'type': ['object', 'string', 'null'],
                          'description': '"save" and "edit": hole -> '
                                         'default; left out, read off the '
                                         'text'},
            'prompt_id': {'type': ['string', 'null'],
                          'description': '"save": the file name; left '
                                         'out, the slug of the name'},
            'values': {'type': ['object', 'null'],
                       'additionalProperties': {'type': 'string'},
                       'description': '"fill": hole -> value, for the '
                                      'holes the session does not answer'},
            'query': {'type': ['string', 'null'],
                      'description': '"list": a word of the name, the '
                                     'description, the category or the id'},
            'limit': {'type': ['integer', 'null'],
                      'description': '"list": how many come back; 100 '
                                     'left out'},
        }, 'required': ['action'], 'additionalProperties': False},
    ),
]

TOOL_PARAMETERS = {
    tool['function']['name']: tool['function']['parameters']
    for tool in TOOLS
}


# The three tables live in ``imasviz/VizAgent/tools_tables.py``: the
# groups, the per-member parameters and the renames between the offered
# spelling and the gesture's own. They are data, not logic, and they are
# imported back here so ``from imasviz.VizAgent.tools import FAMILIES``
# keeps its meaning.
from imasviz.VizAgent.tools_tables import (
    ACTION_PARAMETERS,
    ACTION_RENAMES,
    FAMILIES,
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
    """Why a call did not say which gesture it means, in words that read.

    The discriminant is a word of the schema, not an English one, so no
    sentence here puts an article in front of it: `a action` is what the
    first cut of this answer said for every `action` group, and a refusal
    the model has to re-read is a refusal it answers wrong.
    """
    choices = ', '.join('"%s"' % action for action in order)
    if value is None:
        return ('the %s tool answers no gesture before it says its %s: '
                'answer with %s among %s.'
                % (name, discriminator, discriminator, choices))
    spelled = {member: action
               for action, member in _OFFERS[name][2].items()}
    if value in spelled:
        return ('"%s" is a gesture the %s tool answers, not a value of its '
                '%s: answer with %s="%s".'
                % (value, name, discriminator, discriminator, spelled[value]))
    return ('the %s tool answers no %s "%s": it answers %s. Answer with one '
            'of those.' % (name, discriminator, value, choices))


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
