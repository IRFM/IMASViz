..
   Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
   and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
   CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
   The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

.. |icon_arrowIDSroot| image:: images/DTV_IDS_root_arrow.png
   :scale: 75%

.. |button_undock| image:: images/button_undock.png

.. _loading_IDS:

Loading IDS from IMAS local data source
=======================================

This section describes and demonstrates how to load IDSs
within **IMASViz**

.. Note:: The procedure below is executed on the **GateWay HPC** and thus the
          shots in example are available on the GateWay.

Loading an IMAS IDS
-------------------

The procedure to load an IDS is as follows:

- In the main :guilabel:`IMASViz GUI`, select the first
  tab - :guilabel:`Local data source`.
- Enter the following parameters, listed below, to the appropriate text fields.

+-------------------------------+
| **IMAS IDS example**          |
+--------------------+----------+
| Parameters         | Values   |
+====================+==========+
| User name          | g2penkod |
+--------------------+----------+
| IMAS database name | viztest  |
+--------------------+----------+
| Shot number        | 52344    |
+--------------------+----------+
| Run number         | 0        |
+--------------------+----------+

The data source is a MDS+ pulse file located in
:file:`$HOME/public/imasdb/<IMAS database name>/3/0/` directory. In this
case, the :file:`~public/imasdb/viztest/3/0/` directory of user ``g2penkod``.

The filled GUI should then look as shown in the next figure:

.. image:: images/startup_window_filled.png
   :align: center
   :scale: 80%

Alternatively, the The :guilabel:`IMAS database browser` can be used to navigate
through available users databases and select it by double clicking. The
input parameters will then get filled automatically, as shown in figure below.

.. image:: images/startup_window_filled2.png
   :align: center
   :scale: 80%


By typing a different user name in the :guilabel:`User name` text window and
selecting 'Add databases from user ...' from the data browser popumenu 
(obtained by a right click)  will automatically load the available databases
to the :guilabel:`IMAS database browser`.

.. image:: images/adding_databases.png
   :align: center
   :scale: 80%


Open an IDS
-----------

The procedure to open any IDS is the same. In this manual,
the procedure will be shown on a **magnetics IDS**.


1. Click :guilabel:`Open` button to open the IDS.

   A navigation tree window will open inside the
   **Multiple Document Interface (MDI)**, as shown in the figure below.

   .. image:: images/DTVFrame_empty.png
      :align: center
      :width: 550px

2. Press the **arrow button** |icon_arrowIDSroot|  on the left side of the
   **IDS root node**.

   This will expand the navigation :guilabel:`tree window` and display a
   list of all IDSs. The **filled IDSs** are market with With **blue** color,
   other IDSs are empty.
   The tree will allow browsing data for the specific shot number which is
   displayed by the root node ( ``IDSs(52344)`` ).

   .. image:: images/DTV_IDS_root_open.png
      :align: center
      :width: 550px

   When IDS or node label is selected the :guilabel:`Node documentation`
   widget displays what the opened case holds for that node: its name and its
   documentation, the status the data dictionary gives it (*required*,
   *optional*, *experimental*, *alpha*, *obsolescent*) and its units. A scalar
   shows its value; an array shows its shape and its number of values, the
   smallest and the largest of its entries that are numbers, how many entries
   are zero, and how many are not numbers (``nan``, ``inf``), followed by the
   values themselves -- at most 200 at each end of a long array, with the number
   of values left out stated. A node that holds no values of its own, such as a
   structure, shows its name and its documentation only; a node whose values
   cannot be read says so, and says why. A row the node cannot answer is simply
   absent from the widget.

   .. image:: images/DTVFrame_node_doc.png
      :align: center
      :width: 550px

   The :guilabel:`Node Documentation` widget can be freely taken out from the
   main window by clicking the :guilabel:`undock` button |button_undock|
   and positioned anywhere on the screen. The same thing goes for
   the :guilabel:`Preview Plot` and :guilabel:`Log` widget.

   .. image:: images/DTVFrame_undock_example.png
      :align: center
      :width: 550px

3. Open the **magnetics IDS** by right-clicking on the **magnetics** node
   and selecting the command :guilabel:`Get magnetics data for occurrence`
   (occurrence 0) as shown in the figure below.

   .. image:: images/DTV_open_magnetics_IDS.png
      :align: center
      :width: 400px

   The submenu lists one entry per occurrence **this case holds data for** and
   this window does not display yet; an IDS with no such occurrence left states
   it instead of offering an empty menu. Which occurrences hold data is answered
   by the opened case, so the blue colour of an IDS name and that list always
   agree.

   .. Note:: Alternative: Double-clicking on the **IDS node label** -- or
             pressing :kbd:`Return` with that node selected -- loads the lowest
             occurrence of that IDS that is not displayed yet, with the default
             view described below. When every occurrence the case holds is
             already on screen, nothing is loaded and the :guilabel:`Log`
             widget says so.

   The magnetics IDS nodes are displayed as new nodes in the tree, as shown in
   the figure below. Nodes of an IDS are organized according to the
   **IMAS data dictionary**. Inside the **magnetics** tree, plottable
   **FLT_1D** nodes are colored blue (array length > 0).

    .. image:: images/DTV_magnetics_IDS_contents_FLT_1D.png
      :align: center
      :scale: 80%
      
Adding a new view for IDSs containing a dynamic Array Of Structure
------------------------------------------------------------------

By default, Viz opens a view displaying only one time slice, even if
more time slices have been loaded in memory during IDS loading described
above. This default view ('First time slice only') ensures to reduce the time
to build the IDS tree which is displayed to the user. The node that heads the
view says what it displays, next to the occurrence number:

.. code-block:: text

   equilibrium
      occurrence 0 [displaying first time slice]

Different views of the same occurrence can be added by right-clicking on that
node -- the entry :guilabel:`Add a new view for <IDS>` is offered whenever the
loaded occurrence holds at least one dynamic Array Of Structure, whatever the
view it was first built with -- as shown in the image below.

    .. image:: images/views_menu.png
      :align: center
      :scale: 80%

The different views are:

- 'All time slices': all time slices are displayed in the tree

- 'One over 10 time slices' : only 1 slice over 10 is displayed

- 'Specific time slice only': only 1 slice is displayed with a time index choosen by the user

- 'First time slice only': this is the default view.

The index asked for by 'Specific time slice only' is limited to the slices the
occurrence already in memory holds, and the question belongs to the window that
owns the view. An IDS can hold more than one dynamic Array Of Structure (the
reference *equilibrium* holds 49 ``time_slice`` and 1 ``grids_ggd``) and one
index applies to all of them: an index past the end of the narrower one is
refused, and the :guilabel:`Log` widget names that array and how many elements
it holds.

Below an example of 2 views of the same occurrence, the view
'One over 10 time slices' has been added by the user.

    .. image:: images/two_views.png
      :align: center
      :scale: 80%


