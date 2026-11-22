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

Where a plugin is offered
-------------------------

A plugin says **where it sits** and that is where it appears -- no plugin is
offered everywhere. There are five places, and they are the five the framework
knows:

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - the place
     - where the line lands
   * - an IDS root
     - the :guilabel:`Plugins` sub-menu of the right click on that root
   * - a quantity
     - the :guilabel:`Plugins` sub-menu of the right click on that node
   * - a case
     - the :guilabel:`Plugins` line of that shot view's own menu bar
   * - the app
     - the :guilabel:`Plugins` line of the application window's menu bar
   * - a figure
     - a sub-menu of the right click on a **window of curves**

What each place is asked is different, and so is the answer. An IDS root knows
which IDS it is; a quantity knows which node the mouse is on; a case knows its
URI and no node; the application knows every case the session holds and no case
in particular -- which is why a trend over a campaign of shots sits on the
application's bar and not on one shot's; and a figure knows the window it drew,
which is the only place a question about *the curve on screen* can be answered.

The lines are read again every time a menu opens, so a plugin just edited is on
the next menu without restarting anything. The exception is a figure: its
sub-menus are built when the window is, so a change reaches the next window of
curves.

.. _your_own_plugins:

The plugins IMASViz ships, and the ones you wrote
-------------------------------------------------

Every plugin answers its own menu for the places it claims. What differs is
**whose file it is**, and that decides one thing: a plugin IMASViz ships is read
here and not changed; a plugin of your own is changed in place.

Two entries on the :menuselection:`File` menu of the application window reach
both:

- :menuselection:`File --> New plugin...` writes a plugin of your own from a
  name and the :guilabel:`IDS` it is for. It lands in
  :file:`$HOME/.imasviz/plugins`, next to the preferences and the plot
  configuration files, and nothing has to be registered anywhere: what is in
  that folder is looked for each time the menu is built.
- :menuselection:`File --> Plugins...` opens the table of every plugin this
  session can offer -- the ones IMASViz ships and the ones you wrote -- with
  five columns: which plugin, whose it is, whether it is active, what the
  opened cases said about it, and where the file lives.

.. note::
   The *State* column says ``ok``, ``refused: <why>`` or ``not asked yet``. The
   third is an answer and not a gap: a case view nobody has right-clicked has
   asked its plugins nothing yet.

.. _plugins_active_state:

Switching a plugin off
~~~~~~~~~~~~~~~~~~~~~~

The *Active?* column is a tick box. Un-ticking a row takes that plugin out of
every menu of the run, and the choice is written to the preferences file, so the
next session opens with the plugin still off:

::

    Disabled_bricks=VizEventDetection,VizSpectral

Ticking it back puts the line and its plugin where they were. A plugin refused
because it is switched off is refused **with the same voice as any other
refusal**: it is named in the log panel of the case -- ``Plugin VizSpectral is
not offered: disabled by the user in the preferences`` -- and the *State* column
repeats it, rather than leaving a silent gap in a menu.

Two things this switch does **not** do:

- it does not touch the physics. The two bricks that live on a window of curves
  keep their objects on that window: switch *Événements* off and the sub-menu is
  gone from the right click, while the figure, its curves and the tools of
  :ref:`agentics` that read them are untouched. The switch is about the menu.
- it does not make a name up. A name IMASViz does not ship is refused by name in
  the log, listing the names it does ship, and the line is ignored -- no plugin
  is switched off by a line that cannot be read.

What IMASViz ships, and what each one is offered on:

.. list-table::
   :header-rows: 1
   :widths: 25 17 58

   * - plugin
     - offered on
     - what the line does
   * - ``equilibriumcharts``
     - an IDS root (``equilibrium``)
     - the matplotlib overview of :guilabel:`equilibrium`
   * - ``equilibriumsurfaces``
     - an IDS root (``equilibrium``)
     - the same reading, in IMASViz's own figures
   * - ``VizProfiles_plugin``
     - any IDS root
     - what that IDS holds that can be drawn
   * - ``VizSlicePlugin``
     - any IDS root
     - every filled 1D-profile of that IDS at one slice, in one figure
   * - ``VizEventDetection``
     - a figure
     - *Événements*: ELM, sawtooth and L-H events marked on the curve on screen
   * - ``VizSpectral``
     - a figure
     - *Spectre*: the peaks of the live curve's spectrum
   * - ``VizDerivedQuantities``
     - a case
     - *Quantités dérivées*: the Greenwald fraction, beta normalised and the
       total pressure of that case
   * - ``VizCampaignTrend``
     - the application
     - *Campagne*: the trend of one leaf across the shots this session holds

A plugin of your own is offered on any of the four first places; the figure's
menu box is built from what IMASViz ships and does not scan your folder. See
:ref:`plugin_figure_scope`.

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

Equilibrium surfaces plugin
---------------------------

This plugin draws the same quantities the **Equilibrium overview** plots -- the
magnetic flux surfaces and the radial profiles -- but through IMASViz's *own*
figures: black ground, the one trace palette every curve window wears, one
:guilabel:`EquiSurfaces` key in the figure bookkeeping. The window it opens is
therefore a line of the :guilabel:`Windows` menu, reachable by the case
gestures, and put back by a session -- unlike the overview's matplotlib
window, it has no slider to keep and no grid checkbox to toggle.

It is offered on the **equilibrium** IDS only, as two entries:

- :guilabel:`Surfaces de flux (début, milieu, fin)...`
- :guilabel:`Équilibre à un instant (surface + profils)...`

Executing the equilibrium surfaces plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. In the opened IMAS database navigate to the **equilibrium** IDS.

2. **Right-click** the **equilibrium** node and choose one of the two lines in
   the :guilabel:`Plugins` sub-menu.

The first line draws the flux surfaces of three instants -- the first, middle
and last slice the case holds -- side by side, one frame each, all on the same
scale: the same psi levels, the same bounds, the same marks (plasma boundary,
magnetic axis, O-point, limiter) at each named instant. That is the comparison a
side-by-side row exists for, and a window the case answers cannot answer costs
no figure: the refusal is named in the log panel of the shot view.

The second line asks, through a dialog bounded to the case's own clock, for the
instant to draw. It then holds the flux surface of that instant, and, stacked
under it, the eight radial profiles the overview draws (``q``, ``elongation``,
``triangularity_upper``, ``triangularity_lower``, ``j_tor`` in MA/m²,
``pressure`` in kPa, ``f_df_dpsi``, ``dpressure_dpsi``) on the common radius,
with the slice's global quantities (``ip`` in kA, ``q_95``, ``q_axis``,
``li_3``, ``w_mhd`` in kJ, axis position) said in the window title.

.. note::
   Both entries read **occurrence 0** of the :guilabel:`equilibrium` and
   :guilabel:`wall` IDSs, like the overview. An instant far outside the case's
   clock is not drawn: it is clamped into the case's range and the slice that
   answered is named back.

.. note::
   A session replaying the second entry puts it back **at the instant the file
   held**, not the one it opens on: the instant the entry answered is written
   with the window and handed back instead of re-asked, so a restore does not
   open that dialog a second time.

.. note::
   A tool call is not a click. The ``run_plugin`` tool hands the instant as its
   ``time`` rather than asking for it, and an entry that asks one and is handed
   none is **refused by name** -- naming the parameter and the
   ``equilibrium_at_time`` tool that draws the same window -- because a dialog
   opened where nobody is there to answer it is a session that stops. The
   question above is what a hand on the menu line earns.

Also available as tools, not just the menu
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The same two surfaces are the two gestures the in-app agent and the MCP server
drive (``equilibrium_surfaces`` and ``equilibrium_at_time``), so the agent can
open them from a conversation and an external client over MCP can draw them
without a GUI. What they draw and how they refuse is the code this menu line
runs -- and a refusal is the named reason rather than an empty window.

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

'Slice' plugin
--------------

One line on **any IDS root** -- :guilabel:`Draw the slice of the <ids> IDS…`, so
the same line reads *the equilibrium IDS* under one root and *the wall IDS* under
another -- and one window: every 1D-profile that IDS holds a value for at the
slice the tree is standing on, one curve each, in a single figure of curves.

What that window answers is **which leaves carry a value**. The application
already knows the structure of the IDS, so the entry asks the case which of its
profiles are filled and draws those; the empty ones are counted and said, not
handed to the screen as flat lines. An IDS occurrence that holds no filled
1D-profile at all is refused by name and costs no window.

The line draws the first occurrence the case holds. A session replaying the
window puts back the occurrence the file recorded, and an occurrence the case
does not hold is refused by name, with the ones it does answer spelled out.

.. note::
   This is the slice **the tree stands on**, not an instant you name. A value
   interpolated at an arbitrary time is the ``plot_slice`` gesture of
   :ref:`agentics`, and a quantity of two axes of its own is no 1D-profile: it
   belongs to a picture window, and the tree's own entries are the way to it.

.. _physical_bricks:

Four questions about the plasma
-------------------------------

Four of the shipped plugins answer the questions a physicist asks **about the
signal itself**, rather than about the tree it came from: what events does this
curve carry, what does it oscillate at, what does this case say about the
Greenwald fraction or the beta, and how has this quantity moved across the shots
of a campaign. Each is offered where its question lives:

- the two questions about **the curve on screen** sit on that curve's window --
  the right-click menu box of a window of curves;
- the question about **one case** sits on that shot view's own menu bar;
- the question about **a campaign** sits on the application window's menu bar,
  because a campaign is by definition more than one case, and the session is the
  place where they are all open at once.

All four read the numbers the figures already read. The physics is one layer of
this package with no Qt and no case in it -- it takes a time axis, a value axis
and the parameters of the question -- and both a menu line and a tool of
:ref:`agentics` ask that layer the same question on the same read. So a mark
drawn from the right-click menu and a count answered to the agent are the same
events, found in the same samples. And none of the four invents a number a case
does not hold: a flat signal, a signal too short, a leaf the case does not carry,
or a session holding one shot is a refusal in words, naming what was tried.

Events on a window of curves
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Right-click a window of curves and the sub-menu :guilabel:`Événements` carries
four lines: :guilabel:`ELM`, :guilabel:`sawtooth`, :guilabel:`transition L-H`
and :guilabel:`Retirer les marques`.

An ELM is an excursion **up**, a sawtooth a crash **down**, an L-H transition a
**threshold crossing**. The first two are peaks, gated by their **prominence** --
how far a peak rises above the nearest lower contour on either side of it -- so
the ripple under an ELM is not mistaken for a wall of events; the third is a
crossing, with a hysteresis band so a signal wobbling on the threshold does not
re-trigger.

The series it runs on is the figure's **live curve** -- the first curve that
follows the sliders -- read back off what is on the screen. Nothing is re-read
from the case: what is marked is the curve you are looking at. Each event earns
one vertical line across the plot, and the window answers how many were posed. A
window carries **one set of marks**: asking the next kind replaces them, so a
window shows the ELMs or the sawteeth, not both at once.

Two refusals are worth knowing, because both answer a real state of a curve:

- the figure holds no curve following the sliders (every trace is a kept one), so
  there is no series to run on;
- the signal is flat, or too short to carry an event.

And a cap: when a detection answers **more than forty** events the line is
refused -- more than forty verticals on one window is a wall and not a marking --
and the answer says so, pointing at the report, which is one row per event
instead of one line per event. :guilabel:`Retirer les marques` takes the marks
back off, and says how many it took.

The same three reads are tools, so the agent can mark a figure it drew, or answer
the count without opening one: ``detect_events`` (with ``figure_key`` to mark, or
without it to count), ``clear_event_marks`` and ``events_report``.

The spectrum of the live curve
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The sub-menu :guilabel:`Spectre` has one line, :guilabel:`Sommets du spectre
(top 5)`, and it answers on the same live curve as the events::

    Dominant : f = 3.333  ·  période 0.3  ·  61.7 % de la puissance
    Puissance totale : 1.204e+06
    1024 échantillon(s)

    Pics :
      1.  f = 3.333  ·  période 0.3  ·  61.7 %
      2.  f = 6.667  ·  période 0.15  ·  22.1 %

That is the leading peak with its period and its share of the power, the total,
the sample count, and the leading peaks down to five. The units are the case's:
the abscissa is in seconds and the frequency is in hertz, and no conversion is
done -- a signal kept in milliseconds on the axis keeps the frequencies that
spelling implies.

It refuses, in words, a series that is flat (it answers no power off its mean), a
series too short to spread a power over (fewer than eight samples left), and an
abscissa that is not a strictly increasing clock -- two equal or out-of-order
points would make every frequency ambiguous. Two things the menu does not offer
are offered by the tools: ``spectrum`` with a **band** named answers how much of
the power lives between its two bounds, and ``cross_correlation`` answers how far
one leaf **lags or leads** another, at what the two oscillate together, and what
their shared dominant frequency is. ``spectrum_report`` writes the same facts to
a self-contained HTML page under :file:`~/.imasviz/reports`.

The derived quantities of a case
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :guilabel:`Plugins` line of a shot view's own menu bar carries
:guilabel:`Quantités dérivées`, with three lines. Each reads the case's own
leaves and answers a window; the leaf it read is named in that window, so the
number can be checked against the tree.

.. list-table::
   :header-rows: 1
   :widths: 24 38 38

   * - the line
     - what it answers
     - the leaves it reads by default
   * - :guilabel:`Fraction de Greenwald`
     - ``f_G = n_e / n_G``, with the limit the standard gives,
       ``n_G = (I_p / A) x 1e20`` -- ``I_p`` in mega-Ampère, ``A`` in square
       metre, so the ratio is a metre-cubed density
     - ``equilibrium.time_slice[0].global_quantities.n_e``, ``.ip``, ``.area``
   * - :guilabel:`Beta_N`
     - the case's **normalised beta**, read off the leaf that holds it
     - ``equilibrium.time_slice[0].global_quantities.beta_normal``
   * - :guilabel:`Pression totale`
     - the case's **total pressure**, ``p = n_e k_B T_e + n_i k_B T_i``
     - ``equilibrium.time_slice[0].profiles_1d.pressure``

The last two are read, not computed: the case is what summed electrons and ions,
and the application reports the number the case keeps, under the name of the leaf
it came from. A case that does not hold that leaf is refused by name -- never
handed back as a plausible-looking value.

The window answers the **mean, the peak and the floor** of the series over the
time it is held, with how many points were read and the path they came from. For
the Greenwald fraction it answers the fraction and the limit at the first instant
the three leaves read, and names the three paths so a different ``n_e`` or a
different area can be asked for through the ``greenwald`` tool, which takes the
three leaves as arguments and answers the whole series.

The trend across the shots of a session
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :guilabel:`Plugins` line of the **application window's** menu bar carries
:guilabel:`Campagne`, with :guilabel:`Tendance (ip)` and
:guilabel:`Exporter le rapport`.

The campaign is the session: the shot views that are open, in the order they were
opened. Nothing is named and nothing is typed; the shots a physicist has opened
*are* the campaign, and the answer says so, one row per shot URI. It reads the
same leaf from every one -- ``equilibrium.time_slice[0].global_quantities.ip`` by
default -- takes one value per shot (the mean of the curve the shot answers), and
answers the **direction**, the **first-to-last variation** and the
**least-squares slope over the shot index**.

A trend needs two shots: a session holding one is refused with that count in the
words, as is a campaign whose values are all equal -- a flat campaign says
neither rising nor falling. ``Exporter le rapport`` writes the same answer, with
the per-shot table, to a self-contained HTML page under :file:`~/.imasviz/reports`.

The tools go further than the menu on one point: ``campaign`` takes the **leaf**
and how the per-shot value is taken -- ``at`` an index of the curve, or ``which``
of ``mean`` / ``max`` / ``min`` -- and the shots themselves, in campaign order,
which is what lets the agent run a trend over a list the user dictated rather
than over the windows that happen to be open.

