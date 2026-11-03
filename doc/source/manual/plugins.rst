..
   Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
   and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
   CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
   The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

.. _IMASViz_plugins:

Plugins
=======

IMASViz allows the use of custom-made plugins which further extend the IMASViz
functionality. The plugins currently available are listed here together with a
manual section on how to use them.

.. _your_own_plugins:

The plugins IMASViz ships, and the ones you wrote
-------------------------------------------------

Every plugin is offered the same way -- a line in the :guilabel:`Plugins`
sub-menu of a node -- and every plugin answers that menu for the nodes it
claims. What differs is **whose file it is**, and that decides one thing: a
plugin IMASViz ships is read here and not changed; a plugin of your own is
changed in place.

Two entries on the :menuselection:`File` menu of the application window reach
both:

- :menuselection:`File --> New plugin...` writes a plugin of your own from a
  name and the :guilabel:`IDS` it is for. It lands in
  :file:`$HOME/.imasviz/plugins`, next to the preferences and the plot
  configuration files, and nothing has to be registered anywhere: what is in
  that folder is looked for each time the menu is built.
- :menuselection:`File --> Plugins...` opens the table of every plugin this
  session can offer -- the ones IMASViz ships and the ones you wrote -- with
  four columns: which plugin, whose it is, what the opened cases said about it,
  and where the file lives.

.. note::
   The *State* column says ``ok``, ``refused: <why>`` or ``not asked yet``. The
   third is an answer and not a gap: a case view nobody has right-clicked has
   asked its plugins nothing yet.

Reading a shipped plugin, and changing one
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Select a row and the button says what it will do: :menuselection:`Read...` for a
plugin IMASViz ships, :menuselection:`Edit...` for one of your own. A shipped
plugin opens in a text area you cannot type in, and the box says what to do
instead: :menuselection:`Copy into my plugins...` takes its whole folder --
sub-packages and all -- into :file:`$HOME/.imasviz/plugins` under a name of your
choosing, rewriting the class name wherever it appears. The copy is yours to
change; the one it came from is not touched.

The same boundary is in the :guilabel:`Plugins` sub-menu of a node: a plugin of
your own gets a second line there, :menuselection:`Edit <plugin>...`, and a
shipped plugin does not get one at all.

A saved plugin is a running plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Saving a plugin of your own puts it back into the session that is already
running: the file is watched, and a save -- of IMASViz's editor or of any other
-- is picked up a moment later, so the next right click answers with what is on
disk now. :menuselection:`Reload now` in the *Plugins* window asks for the same
thing without waiting, which is what to press when the folder is on a file system
that announces nothing.

Three things a reload does **not** do, said so that they are not mistaken for a
failure:

- a window a plugin already opened stays as it was drawn. It is not re-drawn
  with the new code -- close it and open it again;
- a plugin IMASViz ships is never re-imported during a run;
- a file that no longer parses is refused, and **the plugin that worked keeps
  working**: the reason, with the line the interpreter stopped at, is written in
  the log panel of every opened case, and the *State* column of the *Plugins*
  window repeats it.

What a plugin you have just written does
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A plugin written by :menuselection:`File --> New plugin...` is not a stub: its
first click draws a real figure in the :guilabel:`Plot Figure` machinery of
IMASViz, through the same command the tree's own *Plot* gesture uses. Click it on
a node of the :guilabel:`IDS` it was written for, and a window appears -- before
a single line of the plugin has been changed.

.. note::
   A plugin is Python, and it runs at the same trust level as IMASViz itself.
   What is in your own plugin folder is imported without being checked over; it
   is your folder, and it is your responsibility. To write one, see
   :ref:`plugin_simple_plot_example`.

Equilibrium overview plugin
---------------------------

This subsection describes and demonstrates the use of IMASViz
**equilibrium overview plugin**, a simple utility for loading and displaying
multiple data from **equilibrium IDS** at once.

Executing the equilibrium overview plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The procedure of executing the IMASViz
**Equilibrium overview plugin** is as follows:

1. In opened IMAS database navigate to the **equilibrium** IDS.

2. **Right-click** on the **equilibrium** node. In a pop up menu a list of available plugins for the
   equilibrium IDS will be displayed.

3. Click the :guilabel:`Equilibrium overview` option.

   .. figure:: images/equilibrium_plugin_popupmenu.png
     :align: center
     :scale: 80%
     :alt: Equilibrium overview plugin popup menu option.

     Equilibrium overview plugin popup menu option.

The plugin will then first grab the data from the Equilibrium IDS which
takes a few seconds. After that the plugin window will appear.

   .. figure:: images/equilibrium_plugin_window_start.png
     :align: center
     :scale: 60%
     :alt: Equilibrium overview plugin main window.

     Equilibrium overview plugin main window.

.. note::
   The plugin reads **occurrence 0** of the :guilabel:`equilibrium` IDS and of the
   :guilabel:`wall` IDS. It does not ask which occurrence, and it has no occurrence
   control: if that occurrence is not in memory, nothing is opened and the reason is
   written in the log panel of the shot view the menu was built on. The *Profiles*
   panel, which offers every occurrence the case holds, carries that choice as a
   combo on its own window instead.

.. note::
   The window is managed like a plot window: it is a line of the
   :guilabel:`Windows` menu, in the :guilabel:`Equilibrium` group, under the line
   ``EquiPlotView:1`` (a second opening gets ``EquiPlotView:2``). Its own close
   box hides it -- see :ref:`other_GUI_features` -- and it belongs to the shot
   view it was opened from, so it is taken down with that view.

Equilibrium overview plugin GUI features
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Equilibrium plugin allows some interactions with the plots that are described
below.

Plot at time slice using slider
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The plotting time value can be easily set by **holding** and **moving** the
slider. By doing that the **red dashed line** on the left plot will move at the
same time, indicating the selected time value (position).

On **slider release** all plots are updated for the selected time.

Plot at time slide using time value
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The time can be specified directly by typing the value to the **time value box**.

   .. figure:: images/equilibrium_plugin_window_time_value_textbox.png
     :align: center
     :scale: 80%
     :alt: Time value box.

     Time value box.

By pressing :guilabel:`enter` keyboard button, all plots are be updated for the
specified time.

.. note::
   Check the left plot for the time values range.

Run through time slices
^^^^^^^^^^^^^^^^^^^^^^^

This feature allows the plugin to go through all time values and at the same
time update all plots, giving a good overall overview.

This is done by pressing the :guilabel:`Run` button.

Enable plot grid
^^^^^^^^^^^^^^^^

To enable grid on all plots check the :guilabel:`Enable Grid` option.

'Profiles' plugin overview
--------------------------

This plugin answers one question for the node you are on: **what does this IDS hold
that can be drawn, and how would it be drawn?** It is offered on every IDS root of
the opened case -- there is no list of supported IDSs in the plugin, and there used
to be one. What the window holds is read off the tree that loading that occurrence
built, so the tabs are the arrays of structures *this* IDS has, and the quantities
in them are the ones the application knows how to plot.

On the case this manual was written against (WEST 54924, run 0, data dictionary
3.35.0), the same entry answers four different IDSs:

+---------------+-----------+-------------+----------------+---------------------+
| IDS           | tabs      | quantities  | error fields   | occurrences         |
+===============+===========+=============+================+=====================+
| equilibrium   | 10        | 191         | 536            | 0, 1, 2, 3          |
+---------------+-----------+-------------+----------------+---------------------+
| core_profiles | 9         | 220         | 558            | 0, 1, 2, 3          |
+---------------+-----------+-------------+----------------+---------------------+
| magnetics     | 4         | 21          | 16             | 0, 1                |
+---------------+-----------+-------------+----------------+---------------------+
| wall          | 4         | 52          | 96             | 0                   |
+---------------+-----------+-------------+----------------+---------------------+

``magnetics`` and ``wall`` are the two that used to answer nothing at all: they are
written with ``homogeneous_time = 1``, and the read the plugin used kept only what
it called dynamic.

Executing the 'Profiles' plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Navigate to the IDS you want -- any IDS of the opened case.

2. **right-click** on its root node. The :menuselection:`Plugins` sub-menu lists
   :guilabel:`Plot what the <ids> IDS holds...`.

3. Choose it. The window opens on the first occurrence the case holds, with one tab
   per array of structures of that IDS and one tab for the quantities outside any of
   them.

Nothing is asked in a dialog: the choices are combos on the window.

- :guilabel:`Occurrence`, bounded by the occurrences this case holds. Choosing
  another one loads it and asks the tree again, so the tabs change with it.
- :guilabel:`Plot along`: either the clock of the IDS, or *its own axis*, which
  leaves the read to answer per quantity. Those are the same two strategies as
  :guilabel:`New ('TIME' axis)` and :guilabel:`New (default axis)` in the tree's own
  menu (section :ref:`plotting_a_selection_to_figure`). An IDS with no clock of its
  own answers only the second.
- :guilabel:`Plots per row`: how many panels a row of the page it opens holds.
  Left on *auto (from the page size)* -- its default -- the answer is the one a
  table of that page size has always given; choose a number to keep that width on
  the windows this panel opens. The window the tree's own gesture opens is not
  told anything, so that choice stays with the window that owns it.

The line under them states the whole answer: how many tabs, how many quantities, and
-- named as a refusal rather than hidden -- how many of those quantities are error
fields.

What a tab holds, and what a click draws
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A tab lists one page of its group and says which page that is -- this is the line
the ``time_slice/constraints`` tab of ``equilibrium`` occurrence **2** answers, on a
group longer than a page: ``111 quantities along time (the clock of the IDS), page 1
of 2 (100 on this page, 100 per page)``. Three buttons:

- :guilabel:`Draw this page` puts one panel per quantity into a
  :ref:`Table Plot View <TPV>`;
- :guilabel:`Add the next page` puts the page after this one into a window **of its
  own**, because a table asks the width of its grid once for the whole table and
  panels arriving afterwards would be laid out twice;
- :guilabel:`Draw the selected quantities` honours the rows the list over it
  stands on, and the list takes one or several. One chosen alone runs the tree's
  own *Plot this node* gesture -- a curve figure, or an image window for a
  quantity with two axes of its own. Several are a :ref:`Table Plot View
  <TPV>` of exactly those, in the order they stand in the list. A list with no
  row under the pointer is a refusal in the log panel, and no window.

The window a click opens belongs to the application, not to the plugin. It is a
line of the :guilabel:`Windows` menu, which is also where it is closed for good, a
saved session puts it back (section :ref:`save_load_session`), each panel answers
:guilabel:`Configure Plot` on its own right click, and the export dialogue offers
its formats.

A tab that lists fewer quantities than its array holds names the ones it leaves out
and why: a quantity with two axes of its own has no panel to sit in on the page,
and :guilabel:`Draw the selected quantities`, with that one alone selected, opens
it as a picture.

A quantity whose read is refused keeps its panel on the page, and the panel says
why under the name of the quantity -- a page of fifty is not a window of thirty
seven with an explained hole. A page for which **no** quantity gives a curve is
refused out loud in the log panel of the shot view and not opened at all --
``wall`` occurrence 0 of this case answers 22 such quantities.

The time cursors
^^^^^^^^^^^^^^^^

A window drawn along the clock needs no cursor: its abscissa *is* the time array. A
window drawn along each quantity's own axis pins one element of that array per
panel, and the band at the bottom of the plugin window moves those panels together.
It is folded into one line -- :guilabel:`More` puts the sliders back -- and it offers
a base only when a window this panel opened actually answers a row for it. That is
why the band is empty over a window drawn along time, and absent altogether for an
IDS with no time base.

.. note::
   The 536 error fields of ``equilibrium`` occurrence 0 are counted and refused
   here, not drawn. An error field is a bar on the curve it belongs to, and the bars
   live in a figure of curves (section
   :ref:`plotting_error_bars_and_confidence_bands`): a panel of a table answers
   :guilabel:`Configure Plot` and no error-bar line. :guilabel:`Draw the selected
   quantities`, with one of them alone selected, opens the curve those bars belong
   to.

.. note::
   With the shot view's :guilabel:`Show only tensors (rank >= 1)` filter on, the tabs
   hold what survived that filter, and the window says so rather than inventing a
   count for what was pruned while the tree was built.

.. note::
   The plugin's window is registered like a figure (``PlotView:1``) and is a line of
   the *Windows* menu, but it is not inside the MDI area: it travels with the
   shot view it was opened from, and a session puts it back by asking the plugin's
   menu line again -- see :ref:`plugin_answers_and_sessions`.

