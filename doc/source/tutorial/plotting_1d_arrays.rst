.. _plotting_1d_arrays:

Plotting 1D arrays
==================

The plotting of 1D arrays option and plot handling is one of the main features
of the IMASViz.

This tutorial subsection presents the basics of plotting a 1D array, stored in
the IDS, and how to handle the created plots.

Plotting a single 1D array to plot widget
-----------------------------------------

The procedure to plot 1D array is as follows:

1. Navigate through the **magnetics IDS** and search for the node containing
   **FLT_1D** data, for example **ids.magnetics.flux_loop[0].flux.data**.
   Plottable FLT_1D nodes are colored blue (array length > 0)

   .. figure:: images/DTV_magnetics_IDS_contents_FLT_1D.png
     :align: center
     :scale: 80%
     :alt: FLT_1D plot

     Example of plottable FLT_1D node.

   By clicking on the node the preview plot will be displayed in the
   :guilabel:`Preview Plot Widget`, located in the main browsing window. This
   feature helps to quickly check how the data, stored in the FLT_1D, looks
   when plotted.

   .. figure:: images/DTV_preview_plot.png
     :align: center
     :scale: 80%

     Preview Plot Widget

2. Right-click on the **ids.magnetics.flux_loop[0].flux.data (FLT_1D)** node

3. From the pop-up menu, select the command
   :guilabel:`Plot ids.magnetics.flux_loop[0].flux.data to` ->
   :guilabel:`figure` -> :guilabel:`New`.

   .. figure:: images/DTV_popupmenu_plotting_single_plot.png
     :align: center
     :scale: 80%

     Navigating through right-click menu to plot data to plot widget.

   The plot should display in plot widget as shown in the image below.

   .. figure:: images/plotWidget_basic.png
     :align: center
     :scale: 80%

     Basic plot widget display.


Basic plot display features
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The below features are available for any :guilabel:`plot display`. Most of them
are available in the right-click menu.

.. Note::
   Term :guilabel:`Plot Display` is used for any base window for displaying
   plots. Following that the :guilabel:`Plot Widget` contains a single
   :guilabel:`Plot Display`, while :guilabel:`Table Plot View`
   and :guilabel:`Stacked Plot View` consist of multiple
   :guilabel:`Plot Displays`.


plotDisplay_popupmenu.png


.. Disable/Enable Mouse
.. ^^^^^^^^^^^^^^^^^^^^

.. Allows enabling or disabling mouse.
.. This feature can ticked on/off on bottom left corner

View All
^^^^^^^^

View whole plot area.

   .. figure:: images/plotDisplay_popupmenu_viewAll.png
     :align: center
     :scale: 75%

     :guilabel:`View All` feature in the right-click menu.

Auto Range
^^^^^^^^^^

Similar to :guilabel:`View All` feature with the difference that it shows
plot area between values ``X_min`` -> ``X_max`` and ``Y_min`` -> ``Y_max``,
without 'plot margins'.

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

Axis options
^^^^^^^^^^^^

X and Y axis range, inverse, mouse enable/disable options and more.

   .. figure:: images/plotDisplay_popupmenu_axisOptions.png
     :align: center
     :scale: 75%

     :guilabel:`Axis Options` feature in the right-click menu.

Plot Configuration and Customization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Setting color and line properties of plots shown in the Plot Display.

   .. figure:: images/plotDisplay_popupmenu_configurePlot.png
     :align: center
     :scale: 75%

     :guilabel:`Configure Plot` feature in the right-click menu.

   .. figure:: images/plotDisplay_configurePlot_window.png
     :align: center

     :guilabel:`Configure Plot` GUI.

Plot options
^^^^^^^^^^^^

Enable/Disable grid, log scale and more.

   .. figure:: images/plotDisplay_popupmenu_plotOptions.png
     :align: center
     :scale: 75%

     :guilabel:`Plot Options` feature in the right-click menu.

Export feature
^^^^^^^^^^^^^^

The Plot Display scene can be exported to:
- image file (PNG, JPG, ...). A total of 16 image formats are supported.
- scalable vector graphics (SVG)
- matplotlib window
- CSV
- HDF5

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
     :scale: 75%

     Comparison of IMASViz :guilabel:`Plot Widget` and
     :guilabel:`matplotlib window`