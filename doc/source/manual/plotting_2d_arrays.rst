..
   Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
   and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
   CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
   The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

.. include:: ../icons.inc


.. _plotting_2d_arrays:

Plotting 2D arrays
==================

A picture draws two axes. Everything else the quantity has -- a time base, an
array of structures holding the leaf -- is either spread over several pictures or
pinned at a stated element, and the window says which it did. This section
describes what the image window shows and how to read it.

.. note::

   The screenshots below were taken with the previous image window. Its layout has
   changed since: the window is now titled :guilabel:`SlicesImage1`, the axis the
   pictures leave out is spread over them instead of pinned, and the slice commands
   are buttons under the pictures instead of entries in a right-click menu. They
   have not been regenerated in this branch.

.. _plotting_single_2d_array:

Plotting a single 2D array
--------------------------

1. Navigate through an IDS and search for a node containing
   **FLT_2D** data. Below is an example based on a WEST shot (54178, run=0).
   The node **spectrometer_visible.channel[101].grating_spectrometer.intensity_spectrum.data** has been
   selected.
   Plottable FLT_2D nodes are colored **blue** (2D data array shapes > 0).

   By clicking on the node a preview plot will be displayed as a black and white 2D image:

   .. figure:: images/2D_image_preview.png
     :align: center
     :scale: 80%
     :alt: FLT_2D plot

2. Right-click on the node.

3. From the pop-up menu, select the command
   :guilabel:`Plot spectrometer_visible.channel[101].grating_spectrometer.intensity_spectrum.data to` |icon_plotSingle| ->
   :guilabel:`Image` |icon_Figure| -> :guilabel:`New` |icon_new|.

   The submenu is named after the window the command is about to open: a quantity
   with two axes to draw opens an image window, a quantity with one opens a figure
   whose submenu is called :guilabel:`Figure` (see :ref:`plotting_1d_arrays`).
   Which of the two is offered is decided by the axes the read walks along the
   quantity, enclosing arrays of structures included -- not by the dimension the
   data dictionary spells on the leaf.

   .. figure:: images/2D_DTV_popupmenu_plotting_image.png
     :align: center
     :width: 550px

4. The image window opens, titled :guilabel:`SlicesImage1`, and is listed in the
   :guilabel:`Show/Hide` and :guilabel:`Delete` menus under
   :guilabel:`SlicesImage`.

   .. figure:: images/2D_image_plotwidget.png
     :align: center
     :scale: 80%

What the window shows
~~~~~~~~~~~~~~~~~~~~~

Pictures
^^^^^^^^

When the quantity is held by a dynamic array, its elements are drawn **side by
side** instead of pinned at one of them: three pictures at a time, starting at the
element the tree was sitting on when the command was triggered. The control under
the pictures names the axis and the elements it holds -- for instance
:guilabel:`time_slice: 1-3 / 4` -- and slides the window along that axis. It stops
where the axis does, and a case holding fewer elements than the window takes draws
only what exists. A quantity with nothing to spread over pictures shows a single
picture and no window control.

Each picture is titled with the quantity and the element it stands for, for example
:guilabel:`psi[Pa] - time_slice 1 (t = 1)`. When the axis carries values they are
spelled out: three pictures saying when they were taken can be read in order, three
saying only 1, 2, 3 cannot.

One colour scale answers for every picture on the window, spanning all of them, and
it does not move when the window does. Comparing two pictures means comparing
colours, and a scale that re-fitted itself to each picture would make every picture
look the same whatever it held.

The axes of a picture are labelled with the coordinates they draw, units included,
and the picture is laid over the extents those coordinates take. The cells
themselves stay element ranks, because a dictionary grid need not be regular; what
is exact is the extent, the labels, and the slice the colours stand for. When one of
the two axes drawn is a time axis, it is laid horizontal.

Pinned axes
^^^^^^^^^^^

Every axis the pictures leave out gets a control of its own, named after the array
or the coordinate the dictionary uses -- for instance a **profiles_2d:** slider with
its :guilabel:`2 / 2` index. The axis spread across the pictures gets none: its
elements are already on screen. Moving a control re-reads and moves every picture at
once.

Slices
^^^^^^

One movable line stands on each axis of the picture. A line is placed in the
coordinates the picture is laid over rather than in element ranks, and cannot leave
their extents; it says where it stands, for instance :guilabel:`rho_tor[m]=2`. The
element it reads is the nearest one, since a slice is an element of the array and on
an irregular grid the nearest one is not the one below.

The slice under each line is drawn as a 1D curve under the pictures, against the
values of the other axis of the picture -- the abscissa the picture already carries.
That curve answers the picture that is up now: moving the window of pictures, or a
pinned axis, moves the slice with it.

Keep this slice
^^^^^^^^^^^^^^^

:guilabel:`Keep this slice` copies the curve under a line onto its plot, labelled
with where the line stood. Kept slices do not move when the window or a control
does, which is what makes two of them comparable. Each line has its own button,
named after the axis it stands on.

Delete the kept slices
^^^^^^^^^^^^^^^^^^^^^^

:guilabel:`Delete the kept slices` removes everything kept, and leaves the lines and
their slices where they are.

Markers
^^^^^^^

Each slice carries a movable cursor of its own, so a position can be read off the
curve without moving the line that produced it. The cursor says which axis it reads
and its units -- for instance :guilabel:`theta_poloidal[rad]=0.5` -- so a slice
running along a time axis reads seconds. :guilabel:`Add a new marker` puts another
cursor on a slice, to compare two positions at once, and :guilabel:`Delete the
markers` takes them all away; the slice itself stays.

Refusals
~~~~~~~~

A quantity is refused with a reason in the log panel rather than drawn wrong, and no
empty window is left behind:

- one axis to draw: it belongs on a figure, where its fixed axes get controls too;
- more than two axes to draw: no picture shows more than two, and the axis read
  between the pictures is already taken;
- no values: nothing to plot, naming the path of the node;
- a second quantity on a window that already holds pictures: one quantity per image
  window, because a second one would need its own colour scale and its own controls.

Drawing a selection
~~~~~~~~~~~~~~~~~~~

A selection of nodes is drawn through :guilabel:`Plot selected nodes to`
|icon_plotMultiple| -> :guilabel:`Figure` |icon_Figure| -> :guilabel:`New` |icon_new|
-> :guilabel:`This IMAS Database` |icon_thisDTV| (or :guilabel:`All IMAS Databases`
|icon_allDTV|). One entry takes curves and pictures: the command gives each quantity
the window its axes need, so a quantity of one axis joins a curve figure and a
quantity of two axes gets a window of its own, with the same pictures, controls and
slices as above. A quantity the window cannot show is refused with a reason in the
log panel and costs no window; the other quantities of the same selection are drawn
all the same.

The menu lists the curve figures already open under the key they carry
(:guilabel:`SlicesPlot1`) to add the selection to one of them instead of opening a
new one. An image window is not listed: it holds one quantity, with its colour scale
and its controls, so a second quantity would need a window of its own.

Other features
~~~~~~~~~~~~~~

Zooming, panning and the right-click menu of a picture are pyqtgraph's own: **View
All**, **Auto Range**, **Mouse Mode** and **Export** work as described for 1D plots
in :ref:`plotting_1d_arrays`. The IMASViz :guilabel:`Configure Plot` dialog is not
offered on an image window: it configures curve properties, and a picture has no
curve to configure -- what it has instead is the colour scale and the slice
controls above.
