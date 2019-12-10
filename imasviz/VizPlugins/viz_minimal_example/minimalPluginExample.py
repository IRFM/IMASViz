#  Name   : minimalPluginExample
#
#           A minimal plugin example for running it inside IMASViz that
#           can serve as a basic template for new plugins.
#           This plugin demonstrates also how to plot basic data/signals found
#           in the IDSs using matplotlib Python library.
#
#           Important: Every plugin must be registered in IMASViz. This is done
#           by adding the plugin in the "RegisteredPlugins" in top part of the
#           "imasviz.VizPlugins.VizPlugin.py" file. The entry format is is
#           "<Plugin main class name>: <plugin_dir/plugin_py_file>".
#
#           The <Plugin main class name> and <plugin_py_file> must be the same!
#
#           In this case would be:
#           'minimalPluginExample' : 'viz_minimal_example.minimalPluginExample'
#
#           Use of Python version 3.7 is recommended, as IMASViz does not
#           support Python2 anymore.
#
#  Author :
#         Dejan Penko
#  E-mail :
#         dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2019- D. Penko

import logging, os
from imasviz.VizPlugins.VizPlugin import VizPlugin
import matplotlib.pyplot as plt

class minimalPluginExample(VizPlugin):
    """A minimal working plugin example for IMASViz.
    There are 5 mandatory functions that every plugin must include (!):
    - execute
    - getEntriesPerSubject
    - getPluginsConfiguration
    - getAllEntries
    - isEnabled

    The functions in this example can be used as a template.

    Note: Inheriting from VizPlugin provides us with the objects
    "selectedTreeNode" and "dataTreeView".
    """

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