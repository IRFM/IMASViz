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

   .. image:: images/DTV_magnetics_IDS_contents_FLT_1D.png
     :align: center
     :scale: 80%

   By clicking on the node the preview plot will be displayed in the
   :guilabel:`Preview Plot Widget`, located in the main browsing window. This
   feature helps to quickly check how the data, stored in the FLT_1D, looks
   when plotted.

   .. image:: images/DTV_preview_plot.png
     :align: center
     :scale: 80%

2. Right-click on the **ids.magnetics.flux_loop[0].flux.data (FLT_1D)** node

3. From the pop-up menu, select the command
   :guilabel:`Plot ids.magnetics.flux_loop[0].flux.data to` ->
   :guilabel:`figure` -> :guilabel:`New`.

   .. image:: images/DTV_popupmenu_plotting_single_plot.png
     :align: center
     :scale: 80%
