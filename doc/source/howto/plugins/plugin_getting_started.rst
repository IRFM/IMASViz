.. _plugin_minimal_example:

Developing a simple plugin for IMASViz
======================================

This section will cover step by step instructions how to:

 - create a very simple introductory plugin example (~100 lines of code),
 - how to register it in IMASViz, and
 - how to run the plugin in IMASViz

The purpose of the simple plugin is not as an actual and useful plugin but only
to demonstrate the basic mechanism on how to create and use custom plugins in
IMASViz. This simple plugin can be considered as a starting template for more
complex plugins with advanced design and functionalities.

The main basic steps are as follows:

1. Plugin source files location
2. Setting mandatory file and class labels
3. Class inheritance
4. Mandatory functions

Plugin source files location
----------------------------

All plugin source files must be stored in a separate directory under
**$VIZ_HOME/imasviz/VizPlugins/<folder_name>**. The name of the directory
usually starts with **viz_**.

In this case we create a new directory with label **viz_minimal_example**. The
full path is then **$VIZ_HOME/imasviz/VizPlugins/viz_minimal_example**.

Mandatory Python file and class labels
--------------------------------------

The main .py file and the class name must be the same. In this case we create
a new Python file **minimalPluginExample.py** which contains
**class minimalPluginExample**.

.. code-block:: python

    class minimalPluginExample():

Inheritance
-----------

The class must inherit from VizPlugin class from the VizPlugin.py. This is
required for IMASViz to gather necessary information for running the plugin.

.. code-block:: python

    class minimalPluginExample(VizPlugin):

Mandatory functions
-------------------

The plugin class must contain 5 mandatory functions (besides constructor):

- execute(self, vizAPI, pluginEntry)
- getEntries(self)
- getPluginsConfiguration(self)
- getAllEntries(self)
- isEnabled(self)










