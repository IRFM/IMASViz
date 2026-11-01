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
   :guilabel:`wall` IDS. It does not ask which occurrence: unlike the *Profiles*
   plugin, it has no occurrence question to answer. If that occurrence is not in
   memory, nothing is opened and the reason is written in the log panel of the
   shot view the menu was built on.

.. note::
   The window is managed like a plot window: it appears in the
   :guilabel:`Show/Hide` and :guilabel:`Delete` menus under :guilabel:`Plot
   windows`, under the name :guilabel:`Equilibrium` and the line
   ``EquiPlotView:1`` (a second opening gets ``EquiPlotView:2``). It belongs to
   the shot view it was opened from, so it is taken down with that view.

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

This plugin allows to plot 0D/1D data embedded in dynamic AOS. It currently supports the following IDSs:

- core_profiles
- core_transport
- core_sources
- equilibrium
- edge_profiles

Executing the 'Profiles' plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here is a scenario example on executing the IMASViz **Profiles plugin**:

1. Navigate to the **core_sources**, **core_profiles**, **core_transport**, **edge_profiles** or **equilibrium**  IDS.

2. **right-click** on the **core_profiles** node for example. The available plugin actions appear in the popup menu.

    .. figure:: images/Profiles_plugin_profiles_plugin_menu.png
     :align: center
     :scale: 80%
     :alt: Profiles plugin popup menu

     Profiles plugin popup menu

3. Select **Visualization of 1D nodes from profiles_1d(itime) along coordinate1 axis**. All 1D data contained contained in profiles_1d(itime) are plotted along the coordinate1 axis.

    .. figure:: images/Profiles_plugin_plots_along_coordinate1_example.png
     :align: center
     :scale: 80%
     :alt: Plots example along the 'coordinate1' axis using the 'Profiles' plugin

     Plots example along the coordinate1 axis using the 'Profiles' plugin

.. note::
   Every panel of that window draws its curve in the same colour, and on white.
   This is not an oversight: the window holds one quantity **per panel**, so a
   colour would have nothing there to tell apart, and the ground is the window's
   own — unlike a :guilabel:`Plot Figure`, which paints black and gives each of
   its traces a colour of its own (section :ref:`plotting_1d_arrays`). The
   colours of that palette are chosen so that they stay legible on white.

4. Move the time slider. Each plot is updated accordingly.

5. **right-click** on a particular plot. A popup menu displays.

    .. figure:: images/Profiles_plugin_plots_menu.png
     :align: center
     :scale: 80%
     :alt: Plot menu

     Plot menu

6. Select 'Plot this in a new separate figure'

.. Note::
   For the 'core_sources' and 'core_transport' IDS, you will be asked for the index i1 of the 'source(i1) AOS' (index i1 of the model(i1) AOS respectively), 
   in order to select all data contained in 'source(i1)/profiles_1d' and 'source(i1)/global_quantities' ('model(i1)/profile_1d' respectively).

   The time slider appears only for plots along the 'coordinate1' axis.

Each table of plots can be managed (hide/show and delete) from the menu 'Plot windows' as shown below:

    .. figure:: images/Profiles_plugin_plots_windows_menu.png
     :align: center
     :scale: 80%
     :alt: Plots windows menu

     Plots windows menu

Time value can be converted in time slice index using the field 'Time value':

1. Enter the time value in the field 'Time value'. The time value is automatically converted in time index in the field 'Time slice index'
2. Click the button 'Plot' in order to update the plots accordingly

.. Note::
   The plots are automatically updated if the checkbox 'Refresh plot(s) automatically on time index change' is enabled.

