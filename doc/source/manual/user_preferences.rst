.. _user_preferences:

Setting user preferences
========================

Few user preferences options are available:

- parsing of GGD nodes structures can be ignored (default) or not
- plot of data with different units can be plotted on the same plot (not allowed by default)
- the color of selected nodes can be customized (default color is red)
- the color of nodes containing data (default color is blue) can be customized (not available currently for UDA; this is because UDA does not provide the information to know if a remote IMAS field contains data)


To change user preferences, you need to create a text file named 'preferences' in your ~/.imasviz folder with
the following content:

#Colour_of_data_nodes_containing_data=#0000ff

#Nodes_selection_colour=#ff0000

#Allow_data_to_be_plotted_with_different_units=0

#Ignore_GGD=1

These are the default values of the 4 currently available options.

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



