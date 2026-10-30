..
   Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
   and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
   CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
   The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

.. _user_preferences:

Setting user preferences
========================

Few user preferences options are available:

- parsing of GGD nodes structures can be ignored (default) or not
- plot of data with different units can be plotted on the same plot (not allowed by default)
- the color of selected nodes can be customized (default color is red)
- the color of nodes containing data (default color is blue) can be customized (not available currently for UDA; this is because UDA does not provide the information to know if a remote IMAS field contains data)
- the session a run is closed with can be kept automatically, and offered back at the next start (not kept by default)


To change user preferences, you need to create a text file named 'preferences' in your ~/.imasviz folder with
the following content:

#Colour_of_data_nodes_containing_data=#0000ff

#Nodes_selection_colour=#ff0000

#Allow_data_to_be_plotted_with_different_units=0

#Ignore_GGD=1

#Auto_save_session=0

These are the default values of the 5 currently available options.

To change an option, just remove the # character preceding the option name and change the value.

Ignoring_GGD option
~~~~~~~~~~~~~~~~~~~
Parsing GGD structures increases significantly the time to load IDSs which contain large GGD structures.
Setting Ignore_GGD to 1 will ignore GGD structures when parsing IDSs containing GGD structures.
Setting Ignore_GGD to 0 will parse GGD structures.

Allow_data_to_be_plotted_with_different_units option
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Setting Allow_data_to_be_plotted_with_different_units to 0 will not allow data with different units to be plotted on the
same plot. Setting this option to 1 will disable this check.

Nodes_selection_colour option
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Change Nodes_selection_colour option value to change the color of selected nodes in the GUI.

Few color code are given here (more can be found on QT documentation):

BLUE = QBrush(QColor('#0000ff'))   --> set option value to #0000ff

RED = QBrush(QColor('#ff0000')) --> set option value to #ff0000

CYAN = QBrush(QColor('#00ffff')) --> set option value to #00ffff

LIGHT_CYAN = QBrush(QColor('#cce5ff')) --> set option value to #cce5ff

LIGHT_GREY = QBrush(QColor('#d3d3d3')) --> set option value to #d3d3d3

Colour_of_data_nodes_containing_data option
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Change Colour_of_data_nodes_containing_data option value to change the color of nodes which contain data. Some available
colors are listed above.

Auto_save_session option
~~~~~~~~~~~~~~~~~~~~~~~~

Setting Auto_save_session to 1 makes IMASViz keep the session of a run on its own:
when the application window closes, what is on the screen -- the case views, the
occurrences they have loaded, the selected quantities, the plot windows and what
had been set on them -- is written to ~/.imasviz/last_session.vsess, and the next
start asks once whether to put it back.

Setting it to 0 (the default) writes nothing at the close and asks nothing at the
start. The option answers both ends of it together, so a file left behind by an
earlier release does not bring the question back.

This is only about doing it *without being asked*. The *File* menu of the
application window offers Save session and Load session whatever this option says:
a session you name yourself is always written, and always listed. See
:ref:`save_load_session`.
