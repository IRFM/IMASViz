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

SOLPS overview plugin
---------------------

This subsection describes and demonstrates the use of IMASViz
**SOLPS overview plugin**, a simple utility for loading and displaying
grid geometry (including grid subsets), and physics quantities (such as
electron density, ion temperature etc.) stored within
**edge_profiles IDS GGD (General Grid Description)**.

.. note::
   The **SOLPS overview plugin** can be run also in a standalone mode
   (outside IMASViz) either from widget source code or from plugin .ui source.
   The necessary sources can be found in directory
   ``$VIZ_HOME/imasviz/VizPlugin/viz_solps``. There, to run standalone widget
   run command ``python3 SOLPSwidget.py`` in terminal. To run standalone plugin
   (the same one as used in IMASViz) run command
   ``python3 run_plugin_ui_standalone.py``.

.. Note::
   The development procedure of the **SOLPS overview plugin** can be seen in a
   short movie found in section :ref:`plugins_qtdesigner`.


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

Executing the SOLPS overview plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The procedure of executing the IMASViz **SOLPS overview plugin** is as follows:

1. In opened IMAS database navigate to the **edge_profiles** IDS.

2. While holding the **shift keyboard button**, **right-click** on the
   **edge_profiles** node. In a pop up menu a list of available plugins for the
   edge_profiles IDS will be displayed.

3. Click the :guilabel:`SOLPS overview` option.

   .. figure:: images/SOLPS_plugin_popupmenu.png
     :align: center
     :scale: 80%
     :alt: SOLPS overview plugin popup menu option

     SOLPS overview plugin popup menu option

   After that the main plugin window will appear, containing an empty plot
   widget and a few buttons.

   .. figure:: images/SOLPS_plugin_window_start.png
     :align: center
     :scale: 60%
     :alt: SOLPS overview plugin main window.

     SOLPS overview plugin main window.

4. Click the :guilabel:`Set IDS` button. The plugin will then first read the
   available data from the Edge Profiles IDS (provided by IMASViz) and build
   the tree view which takes a few seconds.

5. Click the :guilabel:`Set Data` button. After that a dialog window will
   appear, requesting:

   - :guilabel:`GGD Grid (Slice)`, specifying a grid geometry time slice.
     In most cases the grid geometry does not change with time so in such cases
     is obsolete to 're-write' it (that is also the reason why the
     **GGD Grid (grid_ggd)** and **GGD Quantities (ggd)** structures are
     separated).
   - :guilabel:`GGD Quantities (Slice)`, specifying the time slice for physics
     quantities,
   - :guilabel:`Grid Subset`, listing all available 2D grid subsets for specified
     **GGD Grid** and **GGD Quantities** slice.
   - :guilabel:`Grid Subset Quantity`, listing all available quantities for
     grid subset specified by :guilabel:`Grid Subset` drop down list.

   .. figure:: images/SOLPS_plugin_dialog_set_data.png
     :align: center
     :scale: 80%
     :alt: SOLPS overview plugin dialog for setting data (basic example values
           are set).

     SOLPS overview plugin dialog for setting data (basic example values
     are set).

   .. figure:: images/SOLPS_plugin_dialog_list_grid_subset.png
     :align: center
     :scale: 80%
     :alt: List of available (2D) grid subsets for current IDS.

     List of available (2D) grid subsets for current IDS.

   .. figure:: images/SOLPS_plugin_dialog_list_quantities.png
     :align: center
     :scale: 80%
     :alt: List of available physics quantities for current IDS.

     List of available physics quantities for current IDS.

   After the requested parameters are set, press the :guilabel:`OK` button.

6. Click the :guilabel:`Plot Data` button. After pressing the button the plot
   widget will be populated with plot created using the specified data.

   .. figure:: images/SOLPS_plugin_plot_te.png
     :align: center
     :scale: 80%
     :alt: SOLPS overview plugin plot - **Cells** grid subset (all 2D quad
           elements in the domain) + electron temperature quantity values.

     SOLPS overview plugin plot - **Cells** grid subset (all 2D quad
     elements in the domain) + electron temperature quantity values.
