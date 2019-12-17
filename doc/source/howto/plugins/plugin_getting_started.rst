.. _plugin_minimal_example:

Developing a simple plugin for IMASViz
======================================

This section will cover step by step instructions how to:

 - create a very simple introductory plugin example (~80 lines of code),
 - how to register plugin in IMASViz, and
 - how to run the plugin in IMASViz

This simple plugin can be considered also as a starting template for more
complex plugins with advanced design and functionalities.

The main basic steps which will be covered in this tutorial are as follows:

1. Setting plugin source files directory
2. Add IMASViz to $PYTHONPATH
3. Code:

   a) Required import statements.
   b) Setting mandatory file and class labels
   c) Class inheritance
   d) Mandatory functions

4. Registering plugin in IMASViz

Complete code of the simple plugin (named as **minimalPluginExample**) is
available in IMASViz code source in
**$VIZ_HOME/imasviz/VizPlugins/viz_minimal_example**.

Setting Plugin source files location
------------------------------------

All plugin source files must be stored in a separate directory under
**$VIZ_HOME/imasviz/VizPlugins/<folder_name>**. The name of the directory
usually starts with **viz_**.

For the purposes of this tutorial create a new directory with label
**viz_my_example** to distinguish it from other plugins. The full path is then
**$VIZ_HOME/imasviz/VizPlugins/viz_my_plugin**.

Add IMASViz sources to $PYTHONPATH
----------------------------------

In order to have IMASViz sources at our disposal the $VIZ_HOME must be added
to $PYTHONPATH:

.. code-block::

    # bash
    export PYTHONPATH=${VIZ_HOME}:${PYTHONPATH}
    # tcsh
    setenv PYTHONPATH ${VIZ_HOME}:${PYTHONPATH}

Code
----

Required import statements
^^^^^^^^^^^^^^^^^^^^^^^^^^

The next import statements are required:

.. code-block:: python

    import logging, os
    # IMASViz plugin sources
    from imasviz.VizPlugins.VizPlugin import VizPlugin
    # Matplotlib library
    import matplotlib.pyplot as plt

Mandatory Python file and class labels
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The main .py file and the class name must be the same. In this case we create
a new Python file **myPlugin.py** which contains **class myPlugin**.

.. code-block:: python

    class myPlugin():

Inheritance
^^^^^^^^^^^

The class must inherit from VizPlugin class from the VizPlugin.py. This is
required for IMASViz to gather necessary information for running the plugin.

.. code-block:: python

    class myPlugin(VizPlugin):

Mandatory functions
^^^^^^^^^^^^^^^^^^^

The plugin class must contain 5 mandatory functions (besides constructor):

- execute(self, vizAPI, pluginEntry)
- getEntries(self)
- getPluginsConfiguration(self)
- getAllEntries(self)
- isEnabled(self)

Constructor (__init__())
""""""""""""""""""""""""

In this case leave constructor empty.

.. code-block:: python

    def __init__(self):
        pass

execute()
"""""""""

The :guilabel:`execute()` function consists of three parts:

- obtaining data source from IMASViz
- checking if the IDS data was already fetched
- extracting and plotting the data from the IDS

Obtaining data source from IMASViz:

.. code-block:: python

    # Get dataSource from the VizAPI (Application Program Interface)
    # Note: instance of "self.datatreeView" is provided by the VizPlugins
    # through inheritance
    dataSource = vizAPI.GetDataSource(self.dataTreeView)
    shot = dataSource.shotNumber
    run = dataSource.runNumber
    machine = dataSource.imasDbName
    user = dataSource.userName
    occurrence = 0

    # Displaying basic information
    print('Reading data...')
    print('Shot    =', shot)
    print('Run     =', run)
    print('User    =', user)
    print('Machine =', machine)

Checking if the IDS data was already fetched

.. code-block:: python

    # Check if the IDS data is already loaded in IMASviz. If it is not,
    # load it
    if not vizAPI.IDSDataAlreadyFetched(self.dataTreeView, 'magnetics', occurrence):
        logging.info('Loading magnetics IDS...')
        vizAPI.LoadIDSData(self.dataTreeView, 'magnetics', occurrence)

    # Get IDS
    self.ids = dataSource.getImasEntry(occurrence)

Extracting and plotting the data from the IDS

.. code-block:: python

    # Get some data from the IDS and pass it to plot (using matplotlib)
    # - Set subplot
    fig, ax = plt.subplots()
    # - Extract X-axis values (time)
    time_values = self.ids.magnetics.time
    x = time_values
    # - Get the size of AoS (number of arrays)
    num_bpol_probe_AoS = len(self.ids.magnetics.bpol_probe)
    # - For each array extract array values and create a plot
    for i in range(num_bpol_probe_AoS):
        # - Extract array values
        y = self.ids.magnetics.bpol_probe[i].field.data
        # - Set plot (line) defined by X and Y values +
        # - set line as full line (-) and add legend label.
        ax.plot(x, y, '-', label='bpol_probe[' + str(i) + ']')
    # - Enable grid
    ax.grid()
    # - Set axis labels and plot title
    ax.set(xlabel='time [s]', ylabel='Poloidal field probe values',
           title='Poloidal field probe')
    # - Enable legend
    ax.legend()
    # - Draw/Show plots
    plt.show()

getEntries()
""""""""""""

The :guilabel:`getEntries()` function provides IMASViz the information to which
IDS the plugin is associated to.

.. code-block::

    def getEntries(self):
        if self.selectedTreeNode.getIDSName() == "magnetics":
            return [0]

getPluginsConfiguration()
"""""""""""""""""""""""""

The :guilabel:`getPluginsConfiguration()` function provides additional
configurations to IMASViz. In this case no additional configurations are
required -> the function returns value **None**.

.. code-block::

    def getPluginsConfiguration(self):
        return None

getAllEntries()
"""""""""""""""

The :guilabel:`getAllEntries()` function provides IMASViz 'cosmetic' information
(e.g. label which should be shown in the popup menu etc.)

.. code-block::

    def getAllEntries(self):
        # Set a text which will be displayed in the pop-up menu
        return [(0, 'My plugin...')]

isEnabled()
"""""""""""

Through the :guilabel:`isEnabled()` function the custom plugin can be either
**enabled** (returns ``True``) or **disabled** (returns ``False``)

.. code-block::

    def isEnabled(self):
        return True

Full code:

.. code-block::
    :linenos:

    import logging, os
    from imasviz.VizPlugins.VizPlugin import VizPlugin
    import matplotlib.pyplot as plt

    class minimalPluginExample(VizPlugin):

        def __init__(self):
            pass

        def execute(self, vizAPI, pluginEntry):
            """Main plugin function.
            """

            # Get dataSource from the VizAPI (Application Program Interface)
            # Note: instance of "self.datatreeView" is provided by the VizPlugins
            # through inheritance
            dataSource = vizAPI.GetDataSource(self.dataTreeView)
            shot = dataSource.shotNumber
            run = dataSource.runNumber
            machine = dataSource.imasDbName
            user = dataSource.userName
            occurrence = 0

            # Check if the IDS data is already loaded in IMASviz. If it is not,
            # load it
            if not vizAPI.IDSDataAlreadyFetched(self.dataTreeView, 'magnetics', occurrence):
                logging.info('Loading magnetics IDS...')
                vizAPI.LoadIDSData(self.dataTreeView, 'magnetics', occurrence)

            # Get IDS
            self.ids = dataSource.getImasEntry(occurrence)

            # Displaying basic information
            print('Reading data...')
            print('Shot    =', shot)
            print('Run     =', run)
            print('User    =', user)
            print('Machine =', machine)

            # Get some data from the IDS and pass it to plot (using matplotlib)
            # - Set subplot
            fig, ax = plt.subplots()
            # - Extract X-axis values (time)
            time_values = self.ids.magnetics.time
            x = time_values
            # - Get the size of AoS (number of arrays)
            num_bpol_probe_AoS = len(self.ids.magnetics.bpol_probe)
            # - For each array extract array values and create a plot
            for i in range(num_bpol_probe_AoS):
                # - Extract array values
                y = self.ids.magnetics.bpol_probe[i].field.data
                # - Set plot (line) defined by X and Y values +
                # - set line as full line (-) and add legend label.
                ax.plot(x, y, '-', label='bpol_probe[' + str(i) + ']')
            # - Enable grid
            ax.grid()
            # - Set axis labels and plot title
            ax.set(xlabel='time [s]', ylabel='Poloidal field probe values',
                   title='Poloidal field probe')
            # - Enable legend
            ax.legend()
            # - Draw/Show plots
            plt.show()

        def getEntries(self):
            if self.selectedTreeNode.getIDSName() == "magnetics":
                return [0]

        def getPluginsConfiguration(self):
            return None

        def getAllEntries(self):
            # Set a text which will be displayed in the pop-up menu
            return [(0, 'magnetics overview (minimal plugin example)...')]

        def isEnabled(self):
            return True

Registering plugin in IMASViz
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order to register plugin in IMASViz a single entry is required in top part
of the **$VIZ_HOME/imasviz/VizPlugins/VizPlugin.py** file.

In the :guilabel:`RegisteredPlugins` dictionary add key and corresponding value
relevant for your plugin, e.g. ``'myPlugin' : 'viz_my_plugin.myPlugin'``.

Here the key must match the **py. file** and **class name** while the
corresponding value must match ``<plugin_source_path>.<py. file name>``.

In this case it should look something like this:

.. code-block::
    :emphasize-lines: 9

    RegisteredPlugins = {'equilibriumcharts':'viz_equi.equilibriumcharts',
                         'ToFuPlugin':'viz_tofu.viz_tofu_plugin',
                         'SOLPS_UiPlugin': '',
                         'CompareFLT1DPlugin':'viz_tests.CompareFLT1DPlugin',
                         'viz_example_plugin':'viz_example_plugin.viz_example_plugin',
                         'example_UiPlugin': '',
                         'minimalPluginExample' : 'viz_minimal_example.minimalPluginExample',
                         'ETSpluginIMASViz' : 'viz_ETS.ETSpluginIMASViz',
                         'myPlugin' : 'viz_my_plugin.myPlugin'
                         }

Running the custom plugin in IMASViz
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To run the plugin in IMASViz while in IMASViz session with opened IDS database,
in :guilabel:`tree view browser`:

- right-click on the IDS previously specified in :guilabel:`getEntries()` function. A popup menu including the menu action (with label previously specified in :guilabel:`getAllEntries()`) will be shown.
- Click on the menu action
