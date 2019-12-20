.. _plugin_minimal_example:

Developing a simple plugin for IMASViz
======================================

This section will cover step by step instructions on how to:

 - create a very simple introductory plugin example (~80 lines of code),
 - how to register the plugin in IMASViz, and
 - how to run the plugin from IMASViz

This simple plugin can be considered also as a starting template for more
complex plugins with advanced design and functionalities.

The main basic steps which will be covered in this tutorial are as follows:

1. Adding IMASViz home directory to :envvar:`$PYTHONPATH`
2. Setting plugin source files
3. The code:

   a) Required import statements
   b) Properly setting file and class labels
   c) Class inheritance
   d) Mandatory functions

4. Registering plugin in IMASViz

Complete code of the simple plugin (named as **minimalPluginExample**) is
available in IMASViz code source in
:file:`$VIZ_HOME/imasviz/VizPlugins/viz_minimal_example.py`.

Add IMASViz sources to $PYTHONPATH
-----------------------------------

In order to have IMASViz sources at our disposal the ``$VIZ_HOME`` must be added
to :envvar:`$PYTHONPATH` environment variable. This can be achieved by running
the next command in the terminal:

.. code-block::

    # bash
    export PYTHONPATH=${VIZ_HOME}:${PYTHONPATH}
    # tcsh
    setenv PYTHONPATH ${VIZ_HOME}:${PYTHONPATH}

.. _plugin_minimal_example_setting_dir:

Setting directory for plugin source files
-----------------------------------------

All plugin source files must be stored in a separate directory under
:file:`$VIZ_HOME/imasviz/VizPlugins/<folder_name>`. The name of the directory
usually starts with **viz_**.

For the purposes of this tutorial create a new directory with label
**viz_my_example** to distinguish it from other plugins. The full path is then
:file:`$VIZ_HOME/imasviz/VizPlugins/viz_my_plugin`.

Inside the newly created directory create a new Python script file. In this case
name it as :file:`myPlugin.py`. The script can be left empty for now.

The code (Python file contents)
-------------------------------

This subsection will cover the contents of the plugin main Python script file
:file:`$VIZ_HOME/imasviz/VizPlugins/viz_my_plugin/myPlugin.py` (previously
created in :ref:`plugin_minimal_example_setting_dir`).

Required import statements
^^^^^^^^^^^^^^^^^^^^^^^^^^

As the first entry in the Python script, the next modules need to be imported
with the use of the import statements.

In your :file:`myPlugin.py` file add:

.. code-block:: python

    # modules for event logging system and for operating system dependent
    # functionality
    import logging, os
    # IMASViz plugin sources
    from imasviz.VizPlugins.VizPlugin import VizPlugin
    # Matplotlib library
    import matplotlib.pyplot as plt

Mandatory Python file and class labels
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The plugins main Python file must contain a class with the same name as the
name of the Python file. In this case, a class **myPlugin**.

In your :file:`myPlugin.py` file add:

.. code-block:: python

    class myPlugin():

Inheritance
^^^^^^^^^^^

The class must inherit from **VizPlugin class** from the :file:`VizPlugin.py`.
This is required for IMASViz to be able to gather necessary information
required for properly running the plugin.

In your :file:`myPlugin.py` file add:

.. code-block:: python

    class myPlugin(VizPlugin):

Mandatory functions
^^^^^^^^^^^^^^^^^^^

The plugin class must contain 5 mandatory functions (besides constructor):

- **execute(self, vizAPI, pluginEntry)**
- **getEntries(self)**
- **getPluginsConfiguration(self)**
- **getAllEntries(self)**
- **isEnabled(self)**

Constructor (__init__())
""""""""""""""""""""""""

In this case, leave the constructor empty.

In your :file:`myPlugin.py` file add:

.. code-block:: python

    def __init__(self):
        pass

execute()
"""""""""

The :guilabel:`execute()` function consists of three parts:

1. Obtaining data source from IMASViz
2. Checking if the IDS data was already fetched
3. Extracting and plotting the data from the IDS

**1. Obtaining data source (IDS object) from IMASViz:**

This is done through **vizAPI** - **the IMASViz Application Program Interface
(API)** and its **GetDataSource** function.

In your :file:`myPlugin.py` file add:

.. code-block:: python

    # Get dataSource from the VizAPI (IMASViz Application Program Interface)
    # Note: instance of "self.datatreeView" is provided by the VizPlugins
    # through inheritance
    dataSource = vizAPI.GetDataSource(self.dataTreeView)
    # Get case parameters (shot, run, machine user) from the dataSource
    shot = dataSource.shotNumber
    run = dataSource.runNumber
    machine = dataSource.imasDbName
    user = dataSource.userName
    occurrence = 0

    # Displaying basic case information
    print('Reading data...')
    print('Shot    =', shot)
    print('Run     =', run)
    print('User    =', user)
    print('Machine =', machine)

**2. Checking if the IDS data was already fetched**

With the use of functions provided by **vizAPI** it can be checked if the
case (IDS) data was already fetched (loaded in memory) in IMASViz. In case the
data was not yet fetched it can be done with the use of the **LoadIDSData**
function (with the use of this function also the IMASViz data tree view browser
gets updated automatically).

The IDS object is then obtained with the use of **getImasEntry()** function
for given occurrence (default occurrence value is 0).

In your :file:`myPlugin.py` file add:

.. code-block:: python

    # Check if the IDS data is already loaded in IMASviz. If it is not,
    # load it
    if not vizAPI.IDSDataAlreadyFetched(self.dataTreeView, 'magnetics', occurrence):
        logging.info('Loading magnetics IDS...')
        vizAPI.LoadIDSData(self.dataTreeView, 'magnetics', occurrence)

    # Get IDS object
    self.ids = dataSource.getImasEntry(occurrence)

**3. Extracting and plotting the data from the IDS**

With the IDS object available its contents can be easily accessed (following the
structure defined by the :guilabel:`Data Dictionary`). The data can be then
plotted with the use of the :guilabel:`Matplotlib` Python library
(`link <https://matplotlib.org/>`_).

This plugin example will read some simple data from the **Magnetics IDS**
and plot it using **Matplotlib** plitting utilities:

- **time values** (stored in ``magnetics.time`` node) -> **X axis**
- **poloidal field probe values** (stored in ``magnetics.bpol_probe`` array of
  structures (AOS). The values are stored in
  ``magnetics.bpol_probe[i].field.data`` where :math:`i` is the array index)
  -> **Y axis**

In your :file:`myPlugin.py` file add:

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
IDS the plugin is associated. While in the IMASViz tree view browser, the plugin
will be then accessible by right-clicking on here defined IDS (the option
for running this plugin gets shown in the popup menu).

In this case, as the plugin deals with the data stored in **Magnetics IDS**,
this option should be set to ``"magnetics"`` as shown in the code part below.

In your :file:`myPlugin.py` file add:

.. code-block::

    def getEntries(self):
        if self.selectedTreeNode.getIDSName() == "magnetics":
            return [0]

getPluginsConfiguration()
"""""""""""""""""""""""""


The :guilabel:`getPluginsConfiguration()` function provides additional
configurations to IMASViz. In this case no additional configurations are
required -> the function returns value **None**.

In your :file:`myPlugin.py` file add:

.. code-block::

    def getPluginsConfiguration(self):
        return None

getAllEntries()
"""""""""""""""

The :guilabel:`getAllEntries()` function provides IMASViz 'cosmetic' information
(e.g. label which should be shown in the popup menu etc.).

In your :file:`myPlugin.py` file add:

.. code-block::

    def getAllEntries(self):
        # Set a text which will be displayed in the pop-up menu
        return [(0, 'My plugin...')]


isEnabled()
"""""""""""

Through the :guilabel:`isEnabled()` function the custom plugin can be either
**enabled** (returns ``True``) or **disabled** (returns ``False``).

In your :file:`myPlugin.py` file add:

.. code-block::

    def isEnabled(self):
        return True

Full code
^^^^^^^^^

Below is a full code which is done by following the steps in the previous
subsections.

.. code-block::
    :linenos:

    # modules for event logging system and for operating system dependent
    # functionality
    import logging, os
    # IMASViz plugin sources
    from imasviz.VizPlugins.VizPlugin import VizPlugin
    # Matplotlib library
    import matplotlib.pyplot as plt

    class minimalPluginExample(VizPlugin):

        def __init__(self):
            pass

        def execute(self, vizAPI, pluginEntry):
            """Main plugin function.
            """

            # Get dataSource from the VizAPI (IMASViz Application Program Interface)
            # Note: instance of "self.datatreeView" is provided by the VizPlugins
            # through inheritance
            dataSource = vizAPI.GetDataSource(self.dataTreeView)
            # Get case parameters (shot, run, machine user) from the dataSource
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

In order to register the plugin in IMASViz, a single entry is required in the
top part of the :file:`$VIZ_HOME/imasviz/VizPlugins/VizPlugin.py` file.

In the :guilabel:`RegisteredPlugins` dictionary add key and corresponding value
relevant for your plugin, e.g. :kbd:`'myPlugin' : 'viz_my_plugin.myPlugin'`.

Here the key must match the **py. file** and **class name** while the
corresponding value must match :kbd:`'<plugin_source_path>.<py_file_name.py>'`.

In this case, it should look something like this:

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

- right-click on the IDS previously specified in :guilabel:`getEntries()`
  function. A popup menu including the menu action (with label previously
  specified in :guilabel:`getAllEntries()`) will be shown.
- click on the menu action
