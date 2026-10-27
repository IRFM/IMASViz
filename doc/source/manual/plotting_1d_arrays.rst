..
   Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
   and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
   CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
   The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

.. include:: ../icons.inc


.. _plotting_1d_arrays:

Plotting 1D arrays
==================

Plotting 1D arrays and plot handling are the main features and
purposes of the :guilabel:`IMASViz`.

This section describes the basics of plotting a 1D array stored in
an IDS and how to handle the existing plots.

.. _plotting_single_1d_array:

Plotting a single 1D array to a figure
-----------------------------------------

The procedure to plot 1D array is as follows:

1. Navigate through the **magnetics IDS** and search for the node containing
   **FLT_1D** data, for example **magnetics.flux_loop[0].flux.data**.
   Plottable FLT_1D nodes are colored **blue** (array length > 0).

   .. figure:: images/DTV_magnetics_IDS_contents_FLT_1D.png
     :align: center
     :scale: 80%
     :alt: FLT_1D plot

     Example of plottable FLT_1D node.

   By clicking on the node, the preview plot will be displayed in the
   :guilabel:`Preview Plot`, located in the main window. This
   feature helps to quickly check how the data, stored in the FLT_1D, looks
   when plotted on other figures.

   .. figure:: images/DTV_preview_plot.png
     :align: center
     :width: 550px
     :alt:   Preview Plot

     Preview Plot

2. Right-click on the **magnetics.flux_loop[0].flux.data (FLT_1D)** node.

3. From the pop-up menu, select the command
   :guilabel:`Plot ids.magnetics.flux_loop[0].flux.data to` |icon_plotSingle| ->
   :guilabel:`figure` |icon_Figure| -> :guilabel:`New` |icon_new|.

   .. figure:: images/DTV_popupmenu_plotting_single_plot.png
     :align: center
     :scale: 80%

     Navigating through right-click menu to plot data on a figure.

   The plot should display in a figure as shown in the image below.

   .. figure:: images/plotWidget_basic.png
     :align: center
     :width: 550px

     Basic plot figure display.


Basic plot display features
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The features described below are available for any :guilabel:`plot display`. Most of them
are available in the right-click menu.

.. Note::
   Term :guilabel:`Plot Display` is used for any base subwindow for displaying
   plots. Following that the :guilabel:`Plot Figure` contains a single
   :guilabel:`Plot Display`, while :guilabel:`Table Plot View`
   and :guilabel:`Stacked Plot View` consist of multiple
   :guilabel:`Plot Displays`.

.. note::
   What a right click answers depends on which window it was asked of. On a
   :guilabel:`Plot Figure` or :guilabel:`Image` drawn by the entries described
   here, the menu starts with pyqtgraph's own -- :guilabel:`View All`,
   :guilabel:`X axis` and :guilabel:`Y axis` (whose sub-window holds the range,
   the Auto/Manual choice, :guilabel:`Invert Axis`, :guilabel:`Mouse Enabled`
   and the axis link) and :guilabel:`Mouse Mode` -- and the scene adds one line,
   :guilabel:`Export...`. A :guilabel:`Plot Figure` adds the three IMASViz lines
   named below -- :guilabel:`Show/Hide error bars`,
   :guilabel:`Show error bars (with slicing)` and
   :guilabel:`Show/Hide confidence bands` -- because the figure that drew the
   curve is the one holding it; an :guilabel:`Image` figure answers pyqtgraph's
   lines only, and no figure offers :guilabel:`Configure Plot`: that dialog
   belongs to the plots of the :ref:`Profiles plugin <plugins>`. The menu that
   carried these entries on the old figure window was deleted with that window,
   and the frames drawn today answer the error-bar lines themselves. Two of the
   sections below describe lines that menu carried: :guilabel:`Auto Range` is
   not a line of its own on these frames -- it is the Auto/Manual pair in the
   axis sub-window, and :guilabel:`View All` applies it -- and no frame offers
   grid or log-scale choices from a right click.

.. figure:: images/plotDisplay_popupmenu.png
  :align: center
  :width: 450px

  Window right-click menu of a plot.

.. Disable/Enable Mouse
.. ^^^^^^^^^^^^^^^^^^^^

.. Allows enabling or disabling mouse.
.. This feature can ticked on/off on bottom left corner

View All
^^^^^^^^

Zoom to view whole plot area.

   .. figure:: images/plotDisplay_popupmenu_viewAll.png
     :align: center
     :scale: 75%

     :guilabel:`View All` feature in the right-click menu.

Auto Range
^^^^^^^^^^

Similar to :guilabel:`View All` feature with the difference that it shows
plot area between values ``X_min`` -> ``X_max`` and ``Y_min`` -> ``Y_max``,
without additional "plot margins" on the sides.

   .. figure:: images/plotDisplay_popupmenu_autoRange.png
     :align: center
     :scale: 75%

     :guilabel:`Auto Range` feature in the right-click menu.

Left Mouse Button Mode Change
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Change between :guilabel:`Pan Mode` (move plot around) and
:guilabel:`Area Zoom Mode` (choose selectable area to zoom into).

   .. figure:: images/plotDisplay_popupmenu_mouseMode.png
     :align: center
     :scale: 75%

     :guilabel:`Mouse Mode` feature in the right-click menu.

   .. figure:: images/plotDisplay_area_zoom.png
     :align: center
     :width: 300px

     :guilabel:`Area Zoom` example: Marking zoom area using.


   .. figure:: images/plotDisplay_area_zoom_result.png
     :align: center
     :width: 300px

     :guilabel:`Area Zoom` example: Result.

Axis options
^^^^^^^^^^^^

X and Y axis range, inverse, mouse enable/disable options and more.

   .. figure:: images/plotDisplay_popupmenu_axisOptions.png
     :align: center
     :scale: 75%

     :guilabel:`Axis Options` feature in the right-click menu.

Curve colours
^^^^^^^^^^^^^

Every trace a :guilabel:`Plot Figure` draws is given a colour of its own, taken
in the order the traces were laid down: the first quantity plotted takes the
first colour, the quantity added to that figure next takes the second, and so
on. This is what makes the comparison the window exists for possible, whichever
entry drew the trace -- :ref:`a plot added to an existing figure
<add_plot_to_existing_figure>`, or :ref:`a selection plotted to one figure
<plotting_a_selection_to_figure>`, where every selected quantity shares the
same figure. A figure holding more traces than the palette holds colours
(**8**) starts over from its first colour.

   .. note::
      When one quantity is drawn as several traces, each takes its colour and
      its own legend label, spelled ``path[row index]`` -- the path alone would
      name two different traces identically. And the ``path`` of a trace taken
      from an array of structures names the **element** it came from,
      ``magnetics.flux_loop[3].flux.data`` and not ``flux_loop[i]`` -- see
      :ref:`element_or_tensor`.

Two things are left out of that palette, on purpose. The confidence bands of
section :ref:`Displaying error bars and/or confidence bands
<plotting_error_bars_and_confidence_bands>` keep their own red hatched fill and
grey borders: a band belongs to a curve, it is not one. And an :guilabel:`Image`
figure draws pictures, not traces -- one colour scale already answers for all of
them, and there is no trace there to tell apart.

Plot Configuration and Customization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Setting color and line properties of plots shown in the Plot Display.

   .. figure:: images/plotDisplay_popupmenu_configurePlot.png
     :align: center
     :scale: 75%

     :guilabel:`Configure Plot` feature in the right-click menu.

Each plot can be customized. By selecting this feature a separate GUI window
will open, listing the curves of the plot whose menu was used and the properties
that can be changed on each of them by hand.

   .. figure:: images/plotDisplay_configurePlot_window.png
     :align: center

     :guilabel:`Configure Plot` GUI.

   .. figure:: images/plot_configuration_example.png
     :align: center

     Plot configuration example for single plot.

The window answers three questions, in three sections: the properties of each
drawn curve -- colour, line style and thickness, symbol, symbol size and the two
symbol colours; the text of the plot and of the axes it draws a label for, with
bold, italic and size; and, for a window that lays several plots out, the
margins around them. Each change is applied to the plot as it is made.
:guilabel:`Cancel` puts back what the window found when it opened, and
:guilabel:`OK` leaves the changes in place.

A curve drawn without a symbol offers :guilabel:`None` in its symbol list, which
is how a symbol already drawn is taken back off. The error bars and confidence
bands of section :ref:`plotting_error_bars_and_confidence_bands` are not listed
as curves to style: they belong to a curve, and are turned on and off from the
right-click menu.

Plot options
^^^^^^^^^^^^

Enable/Disable grid, log scale and more.

   .. figure:: images/plotDisplay_popupmenu_plotOptions.png
     :align: center
     :scale: 75%

     :guilabel:`Plot Options` feature in the right-click menu.

Export feature
^^^^^^^^^^^^^^

The :guilabel:`Plot Display` scene can be exported to:
   - image file (PNG, JPG, ...). A total of **16** image formats are supported.
   - scalable vector graphics (SVG) file
   - matplotlib window
   - CSV file
   - HDF5 file

   .. figure:: images/plotDisplay_popupmenu_export.png
     :align: center
     :scale: 75%

     :guilabel:`Export` feature in the right-click menu.

   .. figure:: images/plotDisplay_export_window.png
     :align: center
     :scale: 75%

     Export GUI window.

   .. figure:: images/plotDisplay_export_matplotlib.png
     :align: center
     :width: 550px

     Comparison of IMASViz :guilabel:`Plot Figure` and
     :guilabel:`matplotlib window`

.. _add_plot_to_existing_figure:

Adding a plot to existing figure
--------------------------------

The procedure of adding a plot to an already existing figure is as follows:

1. From the previous navigation tree, navigate to the wanted node, for example
   **ids.magnetics.flux_loop[16].flux.data**

2. Right-click on the node.

3. From the pop-up menu, navigate and select
   :guilabel:`Plot <node name> to` |icon_plotSingle| ->
   :guilabel:`Figure` |icon_Figure| -> :guilabel:`SlicesPlot1`

   .. figure:: images/DTV_popupmenu_plot_to_existing_figure.png
     :align: center
     :scale: 75%

     Plotting to existing figure.

The plot will be added to the selected existing plot as shown in the image
below.

   .. figure:: images/DTV_popupmenu_plot_to_existing_figure_result.png
     :align: center
     :width: 550px

     Plotting to existing figure - result.

.. Note:: A plot figure has **one** abscissa: the axis its first curve was read
          along, and the label under it says which. Every quantity added to that
          figure is read along the same axis, so its curves are comparable point by
          point — and the quantities offered in that submenu are the ones that can
          be read along it. A quantity that cannot be read along it is not offered;
          asked for by another route, it is refused in the log panel of that shot,
          naming both the axis of the figure and the axis that quantity runs along.
          The same clock counts as one axis whichever way the IDS writes it: an IDS
          with a homogeneous time base keeps it in the IDS **time** node, an
          inhomogeneous one spells it under the array that carries the quantity
          (``time_slice(itime).time``); the two are one abscissa, and a history of
          one can be joined by a history of the other.


Comparing plots between two IDS databases
-----------------------------------------

:guilabel:`IMASViz` allows comparing of FLT_1D arrays between two different
IDS URIs. The procedure is very similar to the one
presented in the section :ref:`add_plot_to_existing_figure`:

1. Open another IMAS database, same as shown in section :ref:`loading_IDS`.
   In this manual this will be demonstrated using IDS with :guilabel:`shot`
   **52682** and :guilabel:`run` **0** parameters.

   +-------------------------+-----+
   | **Manual IDS case**           |
   +--------------------+----------+
   | parameters         | values   |
   +--------------------+----------+
   | User name          | g2penkod |
   +--------------------+----------+
   | IMAS database name | viztest  |
   +--------------------+----------+
   | Shot number        | 52682    |
   +--------------------+----------+
   | Run number         | 0        |
   +--------------------+----------+


2. Load **occurrence 0** of **magnetics** IDS

3. Navigate through the IDS search for the wanted node, for example
   **ids.magnetics.flux_loop[0].flux.data**.

4. Right-click on the node.

5. From the pop-up menu, navigate and select
   :guilabel:`Plot <node name> to` |icon_plotSingle| ->
   :guilabel:`Figure` |icon_Figure| -> :guilabel:`SlicesPlot1`

The plot will be added to the existing plot as shown in the image below.

   .. figure:: images/DTV2_popupmenu_plot_to_existing_figure_result.png
     :align: center
     :width: 550px

     Plotting from other IDS to existing figure - result.

.. _plotting_a_selection_to_figure:

Plotting a selection of 1D arrays to figure
-------------------------------------------

The procedure of 1D arrays selection and plotting to a figure is as
follows:

1. In main tree view window set a selection of nodes holding 1D arrays.

   .. note::
      How to create a selection of arrays is described in section
      :ref:`signal_node_selection`.

2. When finished with node selection, either:
   - right-click on any FLT_1D node, or
   - click :guilabel:`Node Selection` menu on menubar of the main tree view
   window.

3. From the pop-up menu, navigate and select
   :guilabel:`Plot selected nodes to` |icon_plotMultiple| ->
   :guilabel:`Figure` |icon_Figure| -> :guilabel:`New` |icon_new|->
   :guilabel:`This IMAS database` |icon_thisDTV|.

   .. Note::
      The same procedure applies plotting the selection to an existing figure.

   .. figure:: images/DTV_popupmenu_plot_selected_nodes_to_figure_thisDTV.png
     :align: center
     :scale: 75%

     Plotting selection to a new figure using selection from the currently
     opened IDS database.

   .. figure:: images/DTV_plot_selected_nodes_to_figure_thisDTV_result.png
     :align: center
     :width: 550px

     Example of plot figure, created by plotting data from node selection.

.. _element_or_tensor:

One element of an array, or the array itself
--------------------------------------------

The shot view shows the **elements** of an array: right-clicking
**magnetics.flux_loop[3].flux.data** asks for one of the **17** things that array
holds, not for the array. IMASViz answers that in two ways, and they are not the
same picture:

* an **element** — every plot entry of the tree. The arrays the node stands on are
  fixed at the element the node names, and that element is written where the user
  can read it: the legend says **flux_loop[3]**, not **flux_loop[i]**. Nothing on
  the figure offers to move those indices, because moving one would answer a
  different quantity than the one asked for. What the tree does *not* fix is the
  leaf's own coordinate -- the index inside **flux.data** -- and that keeps a
  control of its own.
* the **tensor** — :guilabel:`Plot <node> to` |icon_plotSingle| ->
  :guilabel:`Figure` |icon_Figure| -> :guilabel:`Explore this tensor`. One figure
  where every axis the curve leaves out gets a slider, so the elements of that
  array can be walked one after the other. The figure opens on the element the
  tree was standing on, not on the first one.

:guilabel:`Keep this curve`, under the sliders, freezes the curve that is live at
the indices it stands on; the sliders then carry on with a new curve, and the
frozen one stays. Unchecking it takes the frozen curve back out. That is how a
family of elements -- **flux_loop[0]**, **flux_loop[5]**, **flux_loop[12]** -- is
laid on one figure to be compared.

A slider costs a line of the window, so the sliders of a figure of curves are
folded behind one summary line, **flux_loop 5 / 16**, with a
:guilabel:`More` / :guilabel:`Fewer` button to open them. A folded band still
answers: it is hidden, not dismantled. An :guilabel:`Image` figure and a
:guilabel:`Table Plot View` panel keep theirs open -- there, the rows are the only
place saying which slice the colours and the numbers stand for (see
:ref:`plotting_2d_arrays`).

A quantity of two axes to draw at once belongs on an :guilabel:`Image` figure, and
an image window does not explore its tensor: the axis an exploration would move is
the one the pictures are already spread over. Such a request is named in the log
panel of the shot view and costs no window.

Plotting 1D array as a function of coordinate1 along the time axis
------------------------------------------------------------------

One of the IMASViz features is to plot data along coordinate1 specified
in the IMAS Data Dictionary.
This is allowed for IDS nodes, located within **time_slice[:]** structure, and
it is already set as a default plotting feature for such arrays.

The curve answers the time slice the node names: right-clicking
**equilibrium.time_slice[0].profiles_1d.phi** draws slice **0**, and the legend
says so. The other slices are reached through :guilabel:`Explore this tensor`,
which puts a slider on **time_slice** (:ref:`element_or_tensor` above).

The procedure to plot such 1D array is quite identical as in section
:ref:`plotting_single_1d_array`. The procedure is described and demonstrated
on **equilibrium.time_slice[0].profiles_1d.phi** (Torodial Flux) array.

1. Navigate through the **equilibrium IDS** and search for the time slice node
   containing
   **FLT_1D** data, for example **equilibrium.time_slice[0].profiles_1d.phi**.

   .. figure:: images/DTV_plot_as_a_function_of_coordinate1.png
     :align: center
     :scale: 80%

     Example of plottable FLT_1D time slice node.

2. Right-click on the **equilibrium.time_slice[0].profiles_1d.phi (FLT_1D)**
   node.

3. From the pop-up menu, select the command
   :guilabel:`Plot equilibrium.time_slice[0].profiles_1d.phi to`
   |icon_plotSingle| -> :guilabel:`figure` |icon_Figure| ->
   :guilabel:`New` |icon_new|.

   .. figure:: images/DTV_popupmenu_plotting_as_a_function_of_coordinate1.png
     :align: center
     :scale: 80%

     Navigating through right-click menu to plot data to plot figure.

   The plot should display in plot figure as shown in the image below.
   Note that **coordinate1 = ids.equilibrium.time_slice[0].profiles_1d.psi**
   for this FLT_1D data array.

   .. figure:: images/plotWidget_function_of_coordinate1.png
     :align: center
     :width: 550px

     Time slice plot figure display. The data are represented as a function of
     coordinate1 (**ids.equilibrium.time_slice[0].profiles_1d.psi**) for the
     first **phi** time slice
     (**ids.equilibrium.time_slice[0].profiles_1d.phi**).

   The slice drawn is the one the node names. To walk the time axis, ask
   :guilabel:`Explore this tensor`: it puts a slider on **time_slice**, starting
   at the slice that was clicked, and the plot changes with it
   (:ref:`element_or_tensor`).

   .. figure:: images/plotWidget_function_of_coordinate1_2.png
     :align: center
     :width: 550px

     Time slice plot figure display for
     **ids.equilibrium.time_slice[48].profiles_1d.phi**. The data are
     represented as a function of coordinate1
     (**ids.equilibrium.time_slice[48].profiles_1d.psi**).

.. Note:: Adding a plot (presented in :ref:`add_plot_to_existing_figure`) to such
          an existing figure adds a curve of its own, read at the element the tree
          was standing on and labelled with it. The slices of one quantity are
          shared by the curves that sample on them; the element an array of
          structures stands on is not shared, and a curve added later does not
          move an earlier one.

Plotting 1D arrays at given coordinate1 index as a function of the time
-----------------------------------------------------------------------

One of the IMASViz features is to plot data as a function of time for a given
coordinate1 index which can be set using a slider. This is allowed for IDS nodes,
located within **time_slice[:]** structure, and it is already set as a
default plotting feature for such arrays.

The procedure is described and demonstrated
on **equilibrium.time_slice[0].profiles_1d.f** (Torodial Flux) array.

1. Navigate through the **equilibrium IDS** and search for the time slice node
   containing
   **FLT_1D** data, for example **equilibrium.time_slice[0].profiles_1d.f**.

   .. figure:: images/DTV_plot_as_a_function_of_coordinate1.png
     :align: center
     :scale: 80%

     Example of plottable FLT_1D time slice node.

2. Right-click on the **equilibrium.time_slice[0].profiles_1d.f (FLT_1D)**
   node.

3. From the pop-up menu, select the command
   :guilabel:`Plot equilibrium.time_slice[0].profiles_1d.f to`
   |icon_plotSingle| -> :guilabel:`figure` |icon_Figure| ->
   :guilabel:`New` |icon_new|.

   .. figure:: images/DTV_popupmenu_plotting_as_a_function_of_time.png
     :align: center
     :scale: 80%

     Navigating through right-click menu to plot data to plot figure.

   The plot should display in plot figure as shown in the image below.
   Note that Y-axis values are an array of
   **equilibrium.time_slice[:].profiles_1d.f[0]** values through all time slices
   (marked by **[:]**) and X-axis values are time values found in
   **equilibrium.time**.

   .. figure:: images/plotWidget_function_of_time_1.png
     :align: center
     :width: 550px

     Plot as a function of time. Y-axis values are an array of
     **equilibrium.time_slice[:].profiles_1d.f[0]** values through all time
     slices (marked by **[:]**) and X-axis values are time values found in
     **equilibrium.time**.

   The coordinate1 slider allows you to move along the array index and the plot
   will change accordingly. That slider belongs to the quantity itself: the tree
   does not fix an index inside **profiles_1d.f**, and the curve follows it. The
   time slice of the node is fixed and written in the legend; to walk it, ask
   :guilabel:`Explore this tensor` (:ref:`element_or_tensor`).

   .. figure:: images/plotWidget_function_of_time_2.png
     :align: center
     :width: 550px

     Plot as a function of time. Y-axis values are an array of
     **equilibrium.time_slice[:].profiles_1d.f[23]** values through all time
     slices (marked by **[:]**) and X-axis values are time values found in
     **equilibrium.time** node (array of FLT_1D values).

.. Note:: Adding a plot (presented in :ref:`add_plot_to_existing_figure`) to such
          an existing figure adds a curve of its own, and the coordinate1 slider
          moves the curves that sample on that coordinate. On a figure built by
          :guilabel:`Explore this tensor`, :guilabel:`Keep this curve` freezes the
          live curve at the indices it stands on before the sliders go on to
          another element, so the elements of one array can be compared at once.

.. _multiplot_features:

Plotting 1D arrays as a function of the '1..N' coordinate
---------------------------------------------------------
Any 1D array can be plotted against the values of its indices (the so-called '1..N' coordinate).

As an example, the procedure is described below for the **magnetics.flux_loop[0].flux.data (FLT_1D)** node:

1. Load the 'magnetics' IDS from an existing URI.

2. Right-click on the **magnetics.flux_loop[0].flux.data (FLT_1D)** node.

3. Select 'Set coordinate1 of magnetics flux_loop[0].flux.data to' from the popup menu.

   .. figure:: images/set_coordinate1.png
     :align: center
     :width: 550px

4. Select the '1..N' coordinate. The preview should be updated, plotting now the node against the '1..N' coordinate.

.. Note:: After this change, all subsequent plots will be performed along the '1..N' coordinate. To restore the
          defaut value of coordinate1, step 3 should be repeated by selecting 'flux_loop(i1).flux.time'. 



.. _plotting_error_bars_and_confidence_bands:

Displaying error bars and/or confidence bands
---------------------------------------------
If data for fields error_upper and/or error_lower are available, errors bars and
confidence bars can be displayed.
Right clicking on a plot figure will display a popup menu as shown in
the image below.

.. note::
   The three lines below are answered by a :guilabel:`Plot Figure` -- the window
   that drew the curve is the one asked -- and by the plots of the
   :ref:`Profiles plugin <plugins>`, whose menu carries them too. They are not
   offered on an :guilabel:`Image` figure or on a MultiPlot display: an error bar
   or a band belongs to a curve, and those windows draw none. The image below is
   a :ref:`Profiles plugin <plugins>` menu, whose two extra lines
   :guilabel:`Auto Range` and :guilabel:`Configure Plot` a :guilabel:`Plot
   Figure` does not offer.

  .. figure:: images/plot_menu_error_bars.png
     :align: center
     :width: 550px

'Show/Hide error bars' displays error bars for each data point while
'Show error bars (with slicing)' diplays error bars every N data points
where N is a value asked to the user.

'Show/Hide confidence bands' displays confidence bands as shown in 
the image below.

  .. figure:: images/confidence_bands.png
     :align: center
     :width: 550px
 

MultiPlot features
------------------

IMASViz provides few features that allow plotting a selection of 1D data
to different plot figure templates (view).

Currently there are two views available:
   - :guilabel:`Table Plot View` and
   - :guilabel:`Stacked Plot View`.

Each of those Plot Views displays interactive menu for interaction features.

.. Note::
   In the old IMASViz, the :guilabel:`Table Plot View` is known as
   :guilabel:`MultiPlot` and the :guilabel:`Stacked Plot View` is known as
   :guilabel:`SubPlot`. The decision to rename those features was made due to
   the previous names not properly describing the feature itself and both of
   those features being a form of 'MultiPlot' - a window consisting of multiple
   plot displays.

.. _TPV:

Table Plot View
~~~~~~~~~~~~~~~

:guilabel:`Table Plot View` allows the user to create a multiplot window by
plotting every array from selection to its own plot display.
The plots are arranged to resemble a table layout as shown in the figure
below. The number of columns follows the number of panels: one panel gets a
row of its own, up to four panels share two columns, and more than four are
laid out in three columns.

.. figure:: images/TablePlotView_example.png
    :align: center
    :scale: 50%

    MultiPlot - :guilabel:`Table Plot View` Example.

Each panel holds one quantity of the selection. A panel is read on the axes
that quantity sits on and is labelled from that reading, so a selection mixing
quantities on different coordinates gives one labelled panel each rather than
one abscissa label for the whole window. Every panel carries a named control for
each axis its reading had to fix: the control says which element of that axis the
panel answers for, and moving it re-reads that panel alone.

Creating New View
^^^^^^^^^^^^^^^^^

To create a new :guilabel:`Table Plot View`, follow the following steps:

1. Create a selection of data nodes, as described in section
   :ref:`plotting_a_selection_to_figure`.

2. When finished with node selection, either:
      - right-click on any **FLT_1D** node or
      - click :guilabel:`Node Selection` menu on menubar of the main tree view
        window.

3. From the pop-up menu, navigate and select
   :guilabel:`Plot selected nodes to` |icon_plotMultiple| ->
   :guilabel:`TablePlotView` |icon_TablePlotView| -> :guilabel:`New (default axis)` |icon_new|->
   :guilabel:`This IMAS Database` |icon_thisDTV| or
   :guilabel:`All IMAS Databases` |icon_allDTV|.

   or

   :guilabel:`Plot selected nodes to` |icon_plotMultiple| ->
   :guilabel:`TablePlotView` |icon_TablePlotView| -> :guilabel:`New ('TIME' axis)` |icon_new|->
   :guilabel:`This IMAS Database` |icon_thisDTV| or
   :guilabel:`All IMAS Databases` |icon_allDTV|.

   When the selection contains 1D nodes located in dynamic AOS, 'TIME' plots
   these nodes along the time axis and fixes their coordinate -- which element is
   fixed is named on the panel and can be moved there. The default strategy plots
   1D data in dynamic AOS along the coordinate axis and fixes the time slice,
   again named and movable on the panel. A node with no time base is read the
   same way by both entries.

   .. figure:: images/DTV_plot_selected_nodes_to_TPV_thisDTV2.png
     :align: center
     :scale: 75%

     Plotting selection to a new figure using selection from the currently
     opened IDS database.

   The :guilabel:`Table Plot View` window will then be created and shown.

.. note::
   A quantity that needs two axes to be drawn at once -- a 2D array read along
   its two coordinates -- is not drawn in a :guilabel:`Table Plot View`: a panel
   holds one curve, and a picture needs a colour scale and controls of its own.
   Such a quantity is named in the log panel of the shot view, saying what was
   refused and why, and the rest of the selection is drawn. To see it as a
   picture, select only that node and use :guilabel:`Figure` (see
   :ref:`plotting_2d_arrays`).

.. note::
   Each panel is drawn from the data and is not customized by hand: the
   :guilabel:`Configure Plot` dialog that the plots of the
   :ref:`Profiles plugin <plugins>` offer on right-click is not offered on a
   :guilabel:`Table Plot View` panel. What can be changed is
   what the panel answers for, through the controls it carries.

.. note::
   Scrolling down the :guilabel:`Table Plot View` window using the middle mouse
   button is disabled as the same button is used to interact with the plot
   display (zoom in and out). Scrolling can be done by clicking the scroll bar
   on the right and dragging it up and down.

.. _save_multiplot_configuration:

Save MultiPlot Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

MultiPlot configuration (currently available only for
:guilabel:`Table Plot View` feature) allows the user to save the MultiPlot
session and load it later.

To create MultiPlot configuration, follow the next steps:

1. Create a selection of nodes, as described in section
   :ref:`plotting_a_selection_to_figure`.

2. Create a :guilabel:`Table Plot View`, as described in :ref:`TPV`.

3. Press the **Save Plot Configuration** button at the top of the
   :guilabel:`Table Plot View` window.

   .. figure:: images/SavePlotConfiguration_dialog.png
     :align: center
     :scale: 75%

     Save Plot Configuration Dialog Window.

4. Type configuration name in the text area.

5. Press **OK**.

.. Note::
   The configurations files are saved to :file:`$HOME/.imasviz` folder.

.. _apply_multiplot_configuration:

Applying MultiPlot configuration to other IMAS database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To apply MultiPlot configuration to any IMAS database, follow the next steps:

1. Open IMAS database.

   .. See also::
      How to open IMAS database is described in :ref:`loading_IDS`.

2. In Main Tree View Window menu navigate to **Actions** ->
   **Apply Configuration**. In the shown window switch to
   :guilabel:`Apply Plot Configuration` tab.

   .. figure:: images/ApplyPlotConfiguration_window.png
     :align: center
     :scale: 75%

     Apply Plot Configuration GUI Window.

3. Select the configuration from the list.

4. Press **Apply selection and plot selected data**.

   The :guilabel:`Table Plot View` will be created using the data stored in the
   configuration file.

.. Note::
   A configuration file holds three things: which quantities were plotted, where
   each panel sat in the table, and along which abscissa the window was drawn.
   All three are put back: the quantities are selected again in the database that
   is open and their panels are laid where they were. How the panels *looked*
   (pen, symbols, axis ranges) is not in a file written by this release, because
   the panels are drawn from the data. A configuration written by an older
   release does hold that styling; the log panel of the shot view then says so and
   how many panels it leaves out, so the difference between the saved window and
   the new one is stated rather than left to be discovered.

.. Note::
   The abscissa saved with the window is the one the configuration is applied
   with. Applying one through the menu of a shot view therefore gives back the
   window that was saved; the scripted entries that name an abscissa themselves
   (:ref:`scripting`) keep what they name.

.. Note::
   A quantity named by the file that this tree does not hold is named in the log
   panel and skipped: load the IDS it belongs to first. The rest of the
   configuration is drawn.

.. Note::
   Currently this feature will take all plot data from single (currently)
   opened IMAS database, event though MultiPlot configuration was made using
   plots from multiple IMAS databases at once. This feature is to be improved
   in the future.

.. warning::
   The plots order depends on the order in which the data selection has
   been performed. First selected data will be the first plots in the
   :guilabel:`Table Plot View` window.

Stacked Plot View
~~~~~~~~~~~~~~~~~

:guilabel:`Stacked Plot View` allows the user to create a multiplot window by
plotting every array from selection to its own plot display.
The plot displays are arranged to resemble a stack layout, as shown in figure
below. All plots displays always share the same X and Y range, even when
using plot interaction features such as :guilabel:`Zoom in/out`,
:guilabel:`Pan Mode`, :guilabel:`Area Zoom Mode` etc.: the ranges of the first
display are the ranges of the window, and interacting with any display moves all
of them.

.. figure:: images/StackedPlotView_example.png
    :align: center
    :scale: 50%

    MultiPlot - :guilabel:`Stacked Plot View` Example.

What a display holds, and how it is read
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Each display holds one quantity of the selection, with the controls for the axes
its reading had to fix -- the same display as in a :guilabel:`Table Plot View`
(see :ref:`TPV`). What differs is that the displays of a
:guilabel:`Stacked Plot View` are drawn against one abscissa, because the point
of the window is to compare several quantities over one span. The quantity read
first fixes that abscissa, and every other quantity is read along it.

Two checkboxes at the top of the window control what the displays share:

* :guilabel:`Group pan mode`, on by default, keeps the X and Y ranges of every
  display linked to the first one. Turned off, each display pans and zooms on its
  own; the quantities still come from the same abscissa.
* :guilabel:`Display X axis of all plots`, off by default, shows the abscissa
  graduations under every display. Off, they are drawn under the bottom display
  only, since all displays are scaled the same way.

Creating New View
^^^^^^^^^^^^^^^^^

To create a new :guilabel:`Stacked Plot View`, follow the next steps:

1. Create a selection of nodes, as described in section
   :ref:`plotting_a_selection_to_figure`.

2. When finished with node selection, either:
      - right-click on any FLT_1D node or
      - click :guilabel:`Node Selection` menu on menubar of the main tree view
        window.

3. From the pop-up menu, navigate and select
   :guilabel:`Plot selected nodes to` |icon_plotMultiple| ->
   :guilabel:`StackedPlotView` |icon_StackedPlotView| ->
   :guilabel:`New (default axis)` |icon_new|->
   :guilabel:`This IMAS Database` |icon_thisDTV| or
   :guilabel:`All IMAS Databases` |icon_allDTV|.

   or

   :guilabel:`Plot selected nodes to` |icon_plotMultiple| ->
   :guilabel:`StackedPlotView` |icon_StackedPlotView| ->
   :guilabel:`New ('TIME' axis)` |icon_new|->
   :guilabel:`This IMAS Database` |icon_thisDTV| or
   :guilabel:`All IMAS Databases` |icon_allDTV|.

   The two entries answer the same question as in a :guilabel:`Table Plot View`:
   :guilabel:`New ('TIME' axis)` reads every quantity along time, which is what
   puts a scalar and a 1D array of a dynamic AOS on one abscissa;
   :guilabel:`New (default axis)` leaves the answer to the reading of each
   quantity, so a 1D array of a dynamic AOS is read along its own coordinate.

   .. figure:: images/DTV_plot_selected_nodes_to_SPV_thisDTV.png
     :align: center
     :scale: 75%

     Plotting selection to a new figure using selection from the currently
     opened IDS database.

   The :guilabel:`Stacked Plot View` window will then be shown.

.. note::
   Because the window has one abscissa, a quantity the reading would take along
   another one is not drawn: the log panel of the shot view names the quantity,
   says which axis it is read along and which one the window draws everything
   against, and points at :guilabel:`Table Plot View` -- the window for
   quantities that do not agree, where each display carries its own abscissa. The
   rest of the selection is drawn. Selecting the two quantities under
   :guilabel:`New ('TIME' axis)`, or in a :guilabel:`Table Plot View`, is what
   shows them both.

.. note::
   A quantity that needs two axes to be drawn at once -- a 2D array read along
   its two coordinates -- is not drawn in a :guilabel:`Stacked Plot View` either:
   a display holds one curve. It is named in the log panel, and the rest of the
   selection is drawn (see :ref:`plotting_2d_arrays` to see it as a picture).

.. note::
   Each display is drawn from the data and is not customized by hand: the
   :guilabel:`Configure Plot` dialog that the plots of the
   :ref:`Profiles plugin <plugins>` offer on right-click is not offered on a
   :guilabel:`Stacked Plot View` display. What can be changed is
   what the display answers for, through the controls it carries, and what it
   shares with its neighbours, through the two checkboxes.

.. note::
   Scrolling down the :guilabel:`Stacked Plot View` window using the middle mouse
   button is disabled as the same button is used to interact with the plot
   display (zoom in and out). Scrolling can be done by clicking the scroll bar
   on the right and dragging it up and down.

