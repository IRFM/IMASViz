.. _plugin_providing_several_functionalities:

Example of a plugin providing several functionalities
=====================================================

The execute() plugin method has the following signature:

execute(vizAPI, pluginEntry)

Each time the user select a plugin menu item in the 'plugins' menu, the pluginEntry
will be set to the value of the entry declared in the getAllEntries().

For example, the viz_example_plugin provides 2 functionalities declared in the
getAllEntries() as:

def getAllEntries(self):
    return [(0, 'Prints some node attributes to log using IMASViz API...'), (1, 'Shows a 2D plot...')]

The first entry (0) is diplayed with the menu item 'Prints node info to log using IMASViz API...',
the second entry (1) is displayed with the menu item 'Shows a 2D plot...'

When the user selects 'Show a 2D plot', pluginEntry is set to 1 and the plugin execute()
method is executed, so the plugin can execute the right functionality using pluginEntry
as a switch in the code of the plugin.

Please refers to the documented viz_example_plugin which is present in the
VizPlugins folder for a detailed example.

