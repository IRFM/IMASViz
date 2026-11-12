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
- the box in the corner of a window can take that window off the screen (default)
  or close it for good
- the MDI area can be laid out windowed (default), tabbed, tiled, or cascaded
- the endpoint, the model name and the key the agent's runs talk to
  (:ref:`agentics_llm`)


To change user preferences, you need to create a text file named 'preferences' in your ~/.imasviz folder with
the following content:

#Colour_of_data_nodes_containing_data=#0000ff

#Nodes_selection_colour=#ff0000

#Allow_data_to_be_plotted_with_different_units=0

#Ignore_GGD=1

#Auto_save_session=0

#Theme=light

#Close_button_deletes=0

#Mdi_view_mode=windowed

#AgentLLMEndpoint=http://127.0.0.1:11434/v1

#AgentLLMModel=qwen3.8:27b

#AgentLLMApiKey=

These are the default values of the 11 currently available options.

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
