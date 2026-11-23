..
   Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
   and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
   CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
   The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

.. _user_preferences:

Setting user preferences
========================

Few user preferences options are available:

- parsing of GGD nodes structures can be ignored (default) or not
- plot of data with different units can be plotted on the same plot (not allowed by default)
- the color of selected nodes can be customized (default color is red)
- the color of nodes containing data (default color is blue) can be customized (not available currently for UDA; this is because UDA does not provide the information to know if a remote IMAS field contains data)
- the session a run is closed with can be kept automatically, and offered back at the next start (not kept by default)
- the theme the application is dressed with can be set to light (default) or dark
- the tree can be kept to the tensors of rank 1 and over, hiding the plain scalars (not filtered by default)
- the box in the corner of a window can take that window off the screen (default)
  or close it for good
- the MDI area can be laid out windowed (default), tabbed, tiled, or cascaded
- the list of cases of the start window can be sorted, filtered by backend and
  shown as URIs or as what they parse to (the five lines the boxes of that list
  write back)
- the endpoint, the model name and the key the agent's runs talk to
  (:ref:`agentics_llm`)
- how much of the agent's tool traffic the transcript shows
- the embeddings endpoint that ranks a journal search by meaning, and the model
  it names (:ref:`agentics_journal_llm`)
- the folder of the **shared** journal, and the folder of the agent's
  **documents corpus** (:ref:`agentics_journal_shared`, :ref:`agentics_documents`)
- the plugins the user has switched off (:ref:`plugins_active_state`)


To change user preferences, you need to create a text file named 'preferences' in your ~/.imasviz folder with
the following content:

#Colour_of_data_nodes_containing_data=#0000ff

#Nodes_selection_colour=#ff0000

#Allow_data_to_be_plotted_with_different_units=0

#Ignore_GGD=1

#Auto_save_session=0

#Theme=light

#Show_only_tensors_rank_ge_1=0

#Close_button_deletes=0

#Mdi_view_mode=windowed

#Uri_list_sort_key=database

#Uri_list_sort_direction=asc

#Uri_list_filter_HDF5=1

#Uri_list_filter_MDSplus=1

#Uri_list_view=uri

#AgentLLMEndpoint=http://127.0.0.1:11434/v1

#AgentLLMModel=qwen3.8:27b

#AgentLLMApiKey=

#AgentToolsMode=hide

#AgentEmbedEndpoint=

#AgentEmbedModel=

#SharedJournalDir=

#AgentDocsDir=

#Disabled_bricks=

#SharedPromptsDir=

These are the default values of the 24 options the file is read for.

To change an option, just remove the # character preceding the option name and change the value.

One line that cannot be read costs that line and nothing else. The value is named
in the log panel of the application -- ``Ignoring Theme in /home/you/.imasviz/preferences:
'Night' is not a theme: IMASViz wears 'light' or 'dark'`` -- and the option keeps its
default, so a typo in a colour leaves the windows of the run exactly where they were.
Before that, one unreadable value stopped the start-up before a window appeared.

Ignoring_GGD option
~~~~~~~~~~~~~~~~~~~
Parsing GGD structures increases significantly the time to load IDSs which contain large GGD structures.
Setting Ignore_GGD to 1 will ignore GGD structures when parsing IDSs containing GGD structures.
Setting Ignore_GGD to 0 will parse GGD structures.

Allow_data_to_be_plotted_with_different_units option
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Setting Allow_data_to_be_plotted_with_different_units to 0 will not allow data with different units to be plotted on the
same plot. Setting this option to 1 will disable this check.

Nodes_selection_colour option
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Change Nodes_selection_colour option value to change the color of selected nodes in the GUI.

A colour is written three ways, and all three are read:

- a hexadecimal code, with or without the leading # -- ``#ff0000`` and ``ff0000``
  are the same colour;
- a color name Qt knows -- ``red``, ``darkBlue``, ``gray``;
- the number of one of the six colours the interface ships with, from 1 to 6.
  This is the oldest spelling, and files written years ago use it.

The six colours, and the number each answers to:

1. BLUE = QBrush(QColor('#0000ff')) -- write ``1`` or ``#0000ff``
2. RED = QBrush(QColor('#ff0000')) -- write ``2`` or ``#ff0000``
3. BLACK = QBrush(QColor('#000000')) -- write ``3`` or ``#000000``
4. CYAN = QBrush(QColor('#00ffff')) -- write ``4`` or ``#00ffff``
5. LIGHT_CYAN = QBrush(QColor('#cce5ff')) -- write ``5`` or ``#cce5ff``
6. LIGHT_GREY = QBrush(QColor('#d3d3d3')) -- write ``6`` or ``#d3d3d3``

A number outside 1 to 6, or a word that names no colour, is named in the log panel
and leaves the default in place.

Colour_of_data_nodes_containing_data option
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Change Colour_of_data_nodes_containing_data option value to change the color of nodes which contain data. It takes the
same three spellings as the option above.

Auto_save_session option
~~~~~~~~~~~~~~~~~~~~~~~~

Setting Auto_save_session to 1 makes IMASViz keep the session of a run on its own:
when the application window closes, what is on the screen -- the case views, the
occurrences they have loaded, the selected quantities, the plot windows and what
had been set on them -- is written to ~/.imasviz/last_session.vsess, and the next
start asks once whether to put it back.

Setting it to 0 (the default) writes nothing at the close and asks nothing at the
start. The option answers both ends of it together, so a file left behind by an
earlier release does not bring the question back.

This is only about doing it *without being asked*. The *File* menu of the
application window offers Save session and Load session whatever this option says:
a session you name yourself is always written, and always listed. See
:ref:`save_load_session`.

Theme option
~~~~~~~~~~~~

IMASViz wears two themes, ``light`` (the default) and ``dark``. The choice is made
at start-up: change the line, restart, and every window of the run is dressed with
it. There is no switch in a menu, on purpose -- a theme touches the ground every
colour is read against, and a window that changed ground under a figure already
drawn would leave that figure dressed for a colour that is no longer there.

What it dresses is the chrome: the menu bar and the menus, the tree and its
selection, the input fields and the buttons, the tabs, the docks, the log panel,
the title of a window and the canvas all the windows float on. The colours are the
same ones this manual is written with -- the palette of the tool and the palette of
the book about it are one table, and a test refuses the two drifting apart.

What it deliberately does **not** dress is the inside of a plot. A figure keeps its
black ground in both themes. That is not an oversight: every trace colour, every
colour map and every slice line was picked against that black, and a theme that
reached it would quietly make those choices wrong -- a curve that reads well on
black does not read well on white, and the same palette would be worn on both.

The name is matched without regard to case, so ``Theme=Dark`` works. A name that
is neither of the two is named in the log panel and leaves the default standing.

Close_button_deletes option
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The box in the corner of a window title bar takes that window off the screen and
keeps it: the *Windows* menu still names it, unchecked, clicking that line puts it
back, and a saved session writes it hidden. See :ref:`other_GUI_features`.

Setting Close_button_deletes to 1 makes that box close the window for good -- out
of the menu, out of the session, and, for a case view, out of the case: the IDSs
that were loaded for it go with the last view that was showing it. It is the same
thing the *Delete* line of the *Windows* menu does.

Hiding is the default because a plot window costs a read of the case to redraw,
and the box is what most users reach for when they want a window out of the way
rather than one thrown away.

The switch answers 0 or 1. Anything else is named in the log panel and leaves the
default standing -- ``Close_button_deletes`` will not read ``2`` as a third state,
and will not guess what ``purple`` was meant to say. The band along the edge of a window that
resizes it, the arrows of the data tree, the scroll bars and the separators
between panels answer the same numbers in both themes, set for a hand holding a
stylus; see :ref:`other_GUI_features`. The title bar of a window is drawn by the
widget style and tinted by the theme, which is what keeps its minimise, maximise
and close buttons on it.

Mdi_view_mode option
~~~~~~~~~~~~~~~~~~~~

The MDI area is laid out in one of four ways, and this option names which one a
case is opened into: ``windowed`` (the default, the titled pile), ``tabbed``
(every window as a tab in one strip), ``tiled`` (a grid, all visible at once),
or ``cascaded`` (stacked diagonally, every title bar reachable). See
:ref:`layout_modes`.

It is set the same way either from the file or from the :guilabel:`Disposition`
sub-menu of the Windows menu: the value is written into this file, so a run in
the next session is opened laid out the way you left it. A name that is none of
the four is named in the log panel and leaves the mode the application had
standing.

Show_only_tensors_rank_ge_1 option
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Setting this to 1 builds the tree of a case with the **tensors of rank 1 and
over** and leaves the plain scalars out: fewer rows, and a walk of the tree that
asks nothing of a leaf it will not show. The default, 0, keeps every node the
dictionary describes.

This line is the **starting** state: it is read once, when the case is opened.
The checkable line :guilabel:`Show only tensors (rank >= 1)` of the shot view's
:menuselection:`Actions` menu is what answers for a tree already on screen -- it
rebuilds every view of that tree the way it was asked, and moves the preference
for the rest of the run without rewriting this file. Measured on the reference
case, a plain load of :guilabel:`equilibrium` occurrence 0 keeps 3 368 signals;
the tensor view of the same load keeps 48, all of them leaves, with no folder
left. What the filter prunes is said rather than silently missing, and the
:ref:`Profiles plugin <IMASViz_plugins>` tabs hold what survived it.

The shot list of the start window
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Five lines, and all five are what the boxes over that list write back -- the file
and the boxes are two ways of setting one state, and a run that has never touched
either sees the list as it has always been laid out.

- **Uri_list_sort_key** -- the field the list is ordered by: ``uri``,
  ``database`` (the default), ``backend``, ``shot`` or ``run``. Whatever the
  choice, the cases are already read in the order database, backend, shot, run,
  so a field that was not chosen is not an absence but that order. Shot and run
  are read as **numbers**, so 12 comes before 999 -- not as words.
- **Uri_list_sort_direction** -- ``asc`` (the default) or ``desc``.
- **Uri_list_filter_HDF5** / **Uri_list_filter_MDSplus** -- 1 shows that kind of
  case, 0 hides it. Both are on by default, and they cannot both be off: the list
  is *which kind of case to open*, and an empty one is a place to look at that
  shows nothing. Note the spelling in the file -- ``MDSplus``, where the box says
  ``MDS+``.
- **Uri_list_view** -- ``uri`` (the default) shows each case as the URI it is
  opened with; ``parsed`` shows the backend, the database, the shot and the run
  the scanner read out of it.

A word none of the boxes offers is named in the log panel and leaves the shape
the list was holding.

The agent's model
~~~~~~~~~~~~~~~~~

The three lines of the agent's runs -- the faces of :ref:`agentics` read them,
the panel of :guilabel:`File --> Agent` among them, and the REPL of
``python3 -m viz_cli`` writes them back when it is asked to, one field at a
time (``/llm endpoint``, ``/llm model``, ``/llm key``). None of them reaches
anything but the model: a line that cannot be read is named where the run
reads it and leaves the default standing, and the runs before the line does
not change.

- **AgentLLMEndpoint** -- the endpoint of a chat that speaks the OpenAI shape,
  the last word of it being ``/v1``. The default is
  ``http://127.0.0.1:11434/v1``, the one a local server answers on port 11434.
  A face is never left hanging on it: the first run against an endpoint that
  does not answer is a named refusal, the endpoint it asked for in the words.

- **AgentLLMModel** -- the name of the model, sent with every call. An empty
  name is **not** a refusal and not a guess: the endpoint is asked, and the
  first entry of its ``/v1/models`` is the one sent, on the first connect. A
  name the endpoint does not hold costs one round trip and a named refusal; it
  is not silently replaced by the one it does hold.

- **AgentLLMApiKey** -- the token, for an endpoint that asks for one. Sent as
  an ``Authorization`` header **only when it is non-empty**; the default is
  empty, and a local server does not ask for one, so the default line never
  sends a header. The word is not logged, not in the log panel and not in a
  transcript: it is the one word of the file that is not repeated where it is
  named.

What the transcript shows
~~~~~~~~~~~~~~~~~~~~~~~~~

**AgentToolsMode** -- three shapes, and they are what the loop asks of the model:

- ``hide`` (the default) -- the agent still runs its gestures; the transcript
  shows the prompt, the final answer and the refusals, and nothing between. It
  is the verbosity cut, not a cut of the work: the figures still appear, and a
  refusal is still named.
- ``off`` -- the agent is offered **no tools at all**: a text answer, no gesture
  run. This is not ``hide`` with the lines hidden; there is nothing to call, so
  a request that needs a case, a figure or a read is answered from what the model
  recalls, which is exactly what the rest of this application refuses to do.
- ``verbose`` -- the whole tool traffic, one line per call and one per result.
  The shape the loop wore before the default moved, and the one to reach for
  when a refusal has to be traced back through the calls that produced it.

A word that is none of the three is named in the log panel and leaves the mode
that was standing.

The agent's journals
~~~~~~~~~~~~~~~~~~~~

The two journals the agent reads and writes on the runs of :ref:`agentics` --
the :ref:`agentics_journal` that holds the notes -- are steered here. None of
them reaches anything but the journals: a line that cannot be read is named
where the run reads it and leaves the default standing.

.. _agentics_journal_llm:

The embeddings endpoint
-----------------------

The journal search ranks by **meaning** when one of these is set and the
endpoint answers, and by **words** while it is not, or while the endpoint
does not answer.

- **AgentEmbedEndpoint** -- the endpoint of a server that answers
  ``POST /v1/embeddings`` in the OpenAI shape. A **chat** endpoint (the one
  ``AgentLLMEndpoint`` names) is not one: the model that answers
  ``/embeddings`` has to carry an embedding table, so the two are apart.
  While this line is empty, or an endpoint it names does not answer, the
  journal search ranks by **words** (a light rank, no dependency) and names
  the fallback in the answer (``fallback_from: 'embeddings'`` and the reason).
- **AgentEmbedModel** -- the name of the embedding model, sent with every call
  to the endpoint named by ``AgentEmbedEndpoint``. An empty name is not a
  refusal: the server answers with the model it holds, and the search reads
  the vector it gives. The same word is not logged.

.. _agentics_journal_shared:

The shared journal
------------------

- **SharedJournalDir** -- the directory the **shared** journal lives in, the
  one the writers of the node reach (an AFS path). Empty by default: on a node
  with no shared one, an explicit ask for the shared journal is refused by
  name (naming the reason and the other journal) and a search that spans the
  two degrades to the personal one the node does hold, with the reason in the
  log. The author of a note written to the shared journal is the ``$USER`` of
  the writer: it is a visible line the writers read, and the writer is named.

.. _agentics_documents_folder:

The documents corpus
--------------------

- **AgentDocsDir** -- the folder of the agent's **documents corpus**: the
  markdown, text and PDF files it is allowed to read for its own
  :ref:`agentics_documents`. Empty by default, and an empty line is not a
  corpus of nothing -- a search over the corpus is refused by name, naming the
  line that is missing, while the two journals keep answering. The folder is
  the user's: its layout, its language and what is in it are nobody's business
  but the reader's, and what is in it is read without being checked over.

.. _agentics_prompts_shared:

The shared prompt catalogue
---------------------------

- **SharedPromptsDir** -- the directory the **shared** prompt catalogue lives
  in (see :ref:`agentics_prompts`), the one the writers of the node reach (an
  AFS path), so that a prompt one of them filed is on the menu of the others.
  Empty by default: a listing that spans the two catalogues answers the
  personal ones and names the missing half in its answer, and a write that
  explicitly asks for the shared catalogue on a node that names no folder is
  refused by name -- never filed in the personal folder instead, which is how
  a prompt would end up believed shared by the one who wrote it. The values
  last typed for a prompt are kept in the user's own folder whatever
  catalogue the prompt sits in.

.. _plugins_active_state_option:

The plugins the user switched off
---------------------------------

- **Disabled_bricks** -- a comma-separated list of plugin **names**, and those
  names are the ones of the table of :ref:`IMASViz_plugins`, not the words the
  menu says::

      Disabled_bricks=VizEventDetection,VizSpectral

  A plugin named here is refused like any other refusal: it is named in the log
  panel of every case -- ``Plugin VizSpectral is not offered: disabled by the
  user in the preferences`` -- and the *State* column of the *Plugins* window
  repeats it. Empty (the default) is nothing switched off.

  The same list is a tick box in :menuselection:`File --> Plugins...`, which
  writes this line and puts the menus back without a restart.

  A name IMASViz does not ship is refused **by name**, listing the names it does
  ship -- and it costs the whole line, so the rest of that line does not take
  effect either. No plugin is switched off by a line that cannot be read.
