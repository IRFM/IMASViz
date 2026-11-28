# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The three tables the schemas of the tools answer from: the groups, the
parameters each merged member takes, and the renames between the offered
spelling and the gesture's own.

They live beside the schemas — ``tools.py`` — but out of its flow: the three
are data, not logic, and a file that carries every gesture's vocabulary is a
file that cannot be re-read. ``tools.py`` imports them back, so the
``from imasviz.VizAgent.tools import FAMILIES`` spelling keeps its meaning.
Nothing here imports from ``tools``: pure data, no seam to cross.
"""


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
    ('the drawing', ('plot_one', 'plot_slice', 'plot_slices',
                     'plot_selection', 'plot_table', 'plot_stacked',
                     'get_signal'), (
        ('plot', 'mode', (
            ('single', 'plot_one'),
            ('slice', 'plot_slice'),
            ('slices', 'plot_slices'),
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
    # The three asks about the IDSs of a case. The group requires `uri`
    # because all three ask a case, but only "load" takes the IDS it loads:
    # these rows are what say that a "load" without `ids_name` is an
    # incomplete call and that an `ids_name` beside "filled" or "declared"
    # belongs to the third ask.
    'list_idss': ({
        'uri': {'type': 'string'},
    }, ('uri',)),
    'list_case_idss': ({
        'uri': {'type': 'string'},
    }, ('uri',)),
    'load_ids': ({
        'uri': {'type': 'string'},
        'ids_name': {'type': 'string'},
        'occurrence': {'type': 'integer', 'default': 0},
        'slices': {'type': 'string', 'enum': ['first', 'all'],
                   'default': 'first'},
    }, ('uri', 'ids_name')),
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
    # The multi-instant read of one profile: `times` is required and is
    # the list of instants the model asks for -- one trace per instant on
    # one figure. `occurrence` and `interpolation` are the same two words
    # `slice` takes, because `slices` is the same read with a list instead
    # of one instant. `plot_slices` takes `path` in Python, so no rename
    # is needed.
    'plot_slices': ({
        'uri': {'type': 'string'},
        'path': {'type': 'string'},
        'times': {'type': 'array', 'items': {'type': 'number'}},
        'occurrence': {'type': 'integer', 'default': 0},
        'interpolation': {'type': 'string',
                          'enum': ['linear', 'closest', 'previous'],
                          'default': 'linear'},
        'into_figure_key': {'type': ['string', 'null']},
    }, ('uri', 'path', 'times')),
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
    # The two asks about the plugins of a case. The group requires `uri`
    # because both ask a case, but "list" asks the IDS root whose entries it
    # wants and "run" asks the entry itself: these rows are what say that a
    # "run" that names no `entry` is an incomplete call, and that an
    # `ids_name` alone is not an answer for either of them.
    'list_plugins': ({
        'uri': {'type': 'string'},
        'ids_name': {'type': 'string'},
    }, ('uri', 'ids_name')),
    'run_plugin': ({
        'uri': {'type': 'string'},
        'plugin': {'type': 'string'},
        'entry': {'type': 'integer'},
        'occurrence': {'type': 'integer', 'default': 0},
        'ids_name': {'type': ['string', 'null']},
        'time': {'type': ['number', 'null']},
    }, ('uri', 'plugin', 'entry')),
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
