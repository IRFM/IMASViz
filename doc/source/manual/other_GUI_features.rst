..
   Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
   and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
   CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
   The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

.. include:: ../icons.inc

.. _other_GUI_features:

Other GUI features
==================

Other :guilabel:`IMASViz` GUI features are listed here.

Hide/Show Plot Window
---------------------

To **hide** or **show** any of the plot windows (:guilabel:`Figure`,
:guilabel:`Table Plot View` etc.), first right-click on any
signal node. From the shown pop-up menu, select the command
:guilabel:`Show/Hide` |icon_showHide| and select the plot window you wish to
show or hide.

.. note::
   Shown plot windows will be hidden while hidden windows will be shown.

.. figure:: images/DTV_popupmenu_show_hide.png
   :align: center
   :scale: 75%

   Show/Hide plot window.

Delete Plot Window
------------------

To delete any of the plot windows, first right-click on any signal node.
From the shown pop-up menu, select the command
:guilabel:`Delete` and select the plot window you wish to delete or delete
all plot windows of certain type (:guilabel:`Figure`,
:guilabel:`Table Plot View` etc.).

.. warning::
   The plot window will be deleted permanently.

.. figure:: images/DTV_popupmenu_delete.png
   :align: center
   :scale: 75%

   Delete plot window.

Export IDS
----------

This feature allows the user to export the opened IDSs to a separate IDS with
custom parameters.

.. Note::
   Only IDSs that are currently opened and populated in the tree view window are
   exported using this feature.

.. Note::
   IMAS database (e.g. device or machine) must exist before trying to export IDS
   to it.

To export the IDSs, first navigate to the menu :guilabel:`Actions` ->
:guilabel:`Export to IDS`.

.. figure:: images/DTV_menu_export_to_IDS.png
   :align: center
   :scale: 75%

   :guilabel:`Export to IDS` feature in the menu bar.

A popup dialog will be shown where the IDS case parameters are set.

.. figure:: images/dialog_ExportToIDS.png
   :align: center
   :scale: 75%

   Empty dialog of the :guilabel:`Export to IDS` feature.

The IDS case parameters are described below:

+--------------------+-----------------------------------------------------------+
| **GUI Fields**     | **Description**                                           |
+====================+===========================================================+
| User name          | Creator/owner of the IMAS IDSs database                   |
+--------------------+-----------------------------------------------------------+
| IMAS database name | IMAS database label, usually device/machine name of the   |
|                    | IMAS IDS database (i. e. iter, aug, west...)              |
+--------------------+-----------------------------------------------------------+
| Shot number        | Pulse shot number                                         |
+--------------------+-----------------------------------------------------------+
| Run number         | Pulse run number                                          |
+--------------------+-----------------------------------------------------------+
| Backend            | Where the pulse is written: HDF5 or MDSplus               |
+--------------------+-----------------------------------------------------------+

The four fields start from the case this tree view has open, and each is checked
as it is entered: the two number fields only take digits, and a field left empty
is answered with its own name rather than sent to the Access Layer.

When the case parameters are set, press the :guilabel:`OK` button to export to
the specified new IDS.

.. figure:: images/dialog_ExportToIDS_filled.png
   :align: center
   :scale: 75%

   :guilabel:`Export to IDS` feature dialog with set parameters.

The four fields name one case: the pulse is written under
``<database>/<data dictionary major version>/<shot>/<run>``, at the data
dictionary the exported IDSs were read with. That version comes from the data,
not from the Access Layer running the application: an IDS read at version 3.35.0
is written as a version 3 case, and an export asked for under another major
version is refused before anything is written.

The export status gets displayed in the tree view log widget: the number of IDSs
written out of the number opened, each IDS the target refused named with the
reason it was refused, and the URI that was written to.

.. figure:: images/ExportToIDS_log_success.png
   :align: center
   :scale: 75%

   :guilabel:`Export to IDS` finish message.

Export plot
-----------

This feature allows the user to export:

- plot to image,
- plot to .SVG format,
- plot to matplotlib window, and
- plot data to CSV or HDF5 format.

This feature is accessible by right-clicking anywhere inside the plot window
and by selecting :guilabel:`Export...` option in the shown popup menu.

.. figure:: images/ExportFeature_1.png
   :align: center
   :width: 25%

   Selections of the :guilabel:`Export` feature in the popup menu.

A dialog window will be shown, displaying the possible export options.
Some the export options allow also setting basic parameters such as image
size etc.

.. figure:: images/ExportFeature_2.png
   :align: center
   :width: 35%

   :guilabel:`Export` feature dialog window.

Hide/Show/Delete DTV
--------------------

This feature allows the user to either hide, show or delete existing
**Data Tree Views** (DTVs).

This feature is available from the starting dialog window (the one where the
database parameters **user**/**database**/**shot**/**run** are being set) by
right clicking anywhere inside the window. A popup menu will be shown displaying
those available options.

.. figure:: images/ShowHideDeleteDTV_1.png
   :align: center

   :guilabel:`Show/Hide/Delete DTV` popup menu.

.. _save_load_session:

Save/Load Session
-----------------

A **session** is what is on the screen when :guilabel:`IMASViz` is closed: the
case views that are open, the IDS occurrences they have loaded, the quantities
that are selected, the plot windows that were drawn, and what had been set on
each of those windows. The two commands :menuselection:`File --> Save session`
and :menuselection:`File --> Load session` write that down and put it back.

.. note::
   Those two lines are on the **File** menu of the application window, the bar
   along the top of :guilabel:`IMASViz` -- not on a case view's
   :guilabel:`Actions` menu. A session is the whole screen, every case view and
   every figure together, so the gesture belongs to the window that holds them
   and is on screen whatever you are looking at. That bar also holds
   :menuselection:`File --> Quit` (:kbd:`Ctrl+Q`), which closes the application
   the way the window's own button does -- asking first, and keeping the session
   if you asked for that (:ref:`below <last_session>`).

To save a session, select :guilabel:`Save session` and type a name in the dialog.
The session is written to :file:`$HOME/.imasviz/<name>.vsess`, beside the plot and
selection configuration files.

To put a session back, select :guilabel:`Load session` and choose one of the
sessions that folder holds -- the sub-menu is only on the menu once at least one
session has been saved, and the list is drawn again every time the menu opens, so
a session saved a minute ago is there without restarting. Nothing else is asked:
the file names the cases, so a session comes back without retyping the database
parameters.

+-------------------------------------+-----------------------------------------+
| **What the file keeps**             | **How it comes back**                   |
+=====================================+=========================================+
| The cases (their URIs)              | Each one is opened as the *Open* entry  |
|                                     | opens it, and shown as a case view      |
+-------------------------------------+-----------------------------------------+
| The IDS occurrences that were       | Each one is loaded again, with the same |
| loaded and the time slices each     | time-slice choice: *all*, *one over 10*,|
| was asked for                       | *first*, or the index that was asked    |
+-------------------------------------+-----------------------------------------+
| Which branches of the tree were     | The IDS branch and the occurrence       |
| unfolded                            | branch are unfolded again; deeper       |
|                                     | branches stay as the load leaves them   |
+-------------------------------------+-----------------------------------------+
| The selected quantities, in the     | Selected on the case view, as a node    |
| order they were picked              | selection file is applied               |
+-------------------------------------+-----------------------------------------+
| The plot windows: kind, quantities, | Each window is drawn again by the same  |
| axis, table cells, and the **key**  | command that drew it the first time,    |
| of each                             | under the key it had -- see below       |
+-------------------------------------+-----------------------------------------+
| What had been set on each window:   | Put back after the window is drawn, in  |
| where its time sliders stood, which | that order: the sliders (which reload   |
| of the **error lines** were on and  | the curves they stand on), then the     |
| at what step, the range a           | lines at the step they were at, then    |
| :guilabel:`Plot Figure` was zoomed  | the range, then the place. A window of  |
| onto, whether the window was        | the area is moved, maximized or hidden  |
| maximized or hidden, and where it   | as it was left: hidden is not closed,   |
| sat                                 | and its key stays in the menus          |
+-------------------------------------+-----------------------------------------+
| A window a plugin drew: which       | Its menu line is asked again of that    |
| plugin, which entry of it, on which | case view, with the occurrence it was   |
| IDS of which case, and the answers  | given and the key it had handed over,   |
| that entry was given                | so nothing is asked of the user again   |
+-------------------------------------+-----------------------------------------+

The key of a window is not a label: it is the name the :guilabel:`Show/Hide` and
:guilabel:`Delete` menus address it by, and the name the *Plot X to -> Figure*
menu offers when a quantity is added to a window that is already open. A saved
session keeps it, so a window that was :guilabel:`SlicesPlot1` comes back as
:guilabel:`SlicesPlot1`, and the menus still name one line for it.

.. note::
   A restored window is drawn from the data again, not taken out of the file. So
   it owns its time sliders, its axis, its legend and its log, and it answers the
   same gestures as a window drawn by hand. A Stacked Plot View is filled from the
   selection, so the selection of its case is set to its quantities while it is
   drawn, and the selection the session was left on is applied afterwards.

.. note::
   Reading a session is fast because its IDSs are read lazily: only the structure
   each tree needs is walked, and the values are taken from the file when a
   quantity is drawn. Measured on the reference case (WEST 54924 run 0): the tree
   of one ``equilibrium`` occurrence costs 0,10 s this way, against 3,99 s when
   the same IDS is read whole -- and the tree is the same either way.

.. warning::
   A session names quantities of a **data dictionary**. A case that comes back at
   another version than the one the session was written with can hold fewer nodes
   than the file names: the difference is said in the log when the case is opened,
   and each quantity that is gone is named when its window is drawn. A case that
   cannot be opened at all costs its own windows and nothing else, so the other
   cases of the file still come back.

.. warning::
   What a session does not keep: the state that belongs to a **panel** rather than
   to a window -- the time sliders of a :guilabel:`Table Plot View` or a
   :guilabel:`Stacked Plot View` are per panel, and the zoom of an
   :guilabel:`Image` figure is per picture. Those windows come back as the drawing
   leaves them.

   What a hand styled **is** kept, and only that. The pen of a trace (colour, line
   style and thickness, symbol, symbol size and the two symbol colours) and the
   text of a title or an axis label are written under the quantity that drew them,
   for the traces the hand actually touched -- which is why the colour a figure
   chose for itself is chosen again the next time the case is drawn, and two traces
   of a new figure stay legible side by side. A style whose quantity the reopened
   case no longer draws is named in the log of the case and costs its own style and
   nothing else.

   The colours of an :guilabel:`Image` figure are kept the same way, and for the
   same reason: one **map** and one **level range** for the window -- never one per
   picture, since the pictures of a window share a scale -- written only for the
   half a hand actually moved. A window nobody dressed writes neither, so it opens
   with the map this installation holds and the span its own pictures settle on,
   rather than the colours and the numbers of the case the file was saved from. A
   map this installation cannot draw -- a name written on another node, where the
   library's own menu reaches the maps of matplotlib -- is named in the log of the
   case, and the window keeps the colours it opens with while **the level range of
   the file still stands**: losing the number because the colour is missing would
   hide the half that still means something. See :ref:`2d_colour_scale`.

.. warning::
   A plugin window comes back **as its entry draws it**, not as the user left it.
   The file keeps the gesture -- which entry, on which IDS, at which occurrence --
   and replays it, so the :guilabel:`Profiles` panel returns with its tabs and its
   time slider at the index the entry starts on, and any tab added by hand is
   gone. What the entry itself refuses is named in the log of the case: an
   occurrence the plugin does not read (the :guilabel:`Equilibrium overview` reads
   occurrence 0 of :guilabel:`equilibrium` and :guilabel:`wall`, and says so rather
   than drawing curves from an occurrence the file did not name), a plugin that
   offers no such entry on that node, or an entry whose code cannot be handed the
   answers -- which leaves that one window out and puts the rest of the screen
   back.

.. _last_session:

The session of the run that ended
`````````````````````````````````

**This is a preference, and it is off by default.** Nothing is written when you
close :guilabel:`IMASViz`, and the next start asks you nothing. To have the session
of a run kept without asking for it every time, set the option in
:file:`$HOME/.imasviz/preferences` -- see :ref:`user_preferences`:

  Auto_save_session=1

With it on, closing writes the session that was on screen to
:file:`$HOME/.imasviz/last_session.vsess`, under one name nobody chose, and the
next start asks once:

   Restore the session IMASViz was closed with?

Answering no opens nothing and leaves the file where :guilabel:`Load session`
lists it; answering yes puts that session back. The question is only asked when
such a file is there, so the first run -- and every run that followed one closed
with nothing open -- asks nothing. The option answers **both** ends of it at once:
with it off there is no write and no question, even when a file an earlier release
left behind is still in the folder.

The file is a session like the ones you name yourself, so it can be opened by hand
from :menuselection:`File --> Load session`, copied, or read over: it is a file,
not a hidden state. And with the preference off, saving by hand changes nothing
about it -- a session you name is always available, kept or not.

The look of the application
---------------------------

The chrome of the application -- the menu bar and the menus, the tree and its
selection, the docks, the log panel, the input fields, the title of a window and
the canvas all the windows float on -- is dressed with one of two themes,
``light`` (the default) or ``dark``. It is a line in the preferences file, read at
start-up; see :ref:`user_preferences`.

What a theme does not dress is the inside of a plot: a figure keeps its black
ground either way. The trace colours, the colour maps and the slice lines were all
picked against that black, on either theme.



