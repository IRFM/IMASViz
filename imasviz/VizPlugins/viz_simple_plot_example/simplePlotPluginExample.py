
# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

# modules for event logging system and for operating system dependent
# functionality
import logging
# IMASViz plugin sources
from imasviz.VizPlugins.VizPlugin import VizPlugin
# Matplotlib library
import matplotlib.pyplot as plt


class simplePlotPluginExample(VizPlugin):
    """A minimal working plugin example for IMASViz.
    There are 5 mandatory functions that every plugin must include (!):
    - execute
    - getEntries
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

        # Get dataSource from the VizAPI (IMASViz Application Program Interface)
        # Note: instance of "self.datatreeView" is provided by the VizPlugins
        # through inheritance
        dataSource = vizAPI.GetDataSource(self.dataTreeView)
        # Get uri from the dataSource
        uri = dataSource.uri
        occurrence = 0

        # Check if the IDS data is already loaded in IMASviz. If it is not,
        # load it
        if not vizAPI.IDSDataAlreadyFetched(self.dataTreeView, 'magnetics', occurrence):
            logging.getLogger(dataSource.uri).info('Loading magnetics IDS...')
            vizAPI.LoadIDSData(self.dataTreeView, 'magnetics', occurrence)

        # Get IDS object
        self.ids = dataSource.getImasEntry(occurrence)

        # Displaying basic case information
        print('Reading data...')
        print('URI    =', uri)
        
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
        return []

    def getPluginsConfiguration(self):
        return None

    def getAllEntries(self):
        # Set a text which will be displayed in the pop-up menu
        return [(0, 'Magnetics overview (simple plot plugin example)...')]

    def getDescription(self):
        """ Return plugin description.
        """

        return "A minimal plugin example for IMASViz. \n"                  \
               "This plugin demonstrates also how to plot basic \n"        \
               "data/signals found in the IDSs using matplotlib Python \n" \
               "library. \n"     \
               "Authors: Dejan Penko (dejan.penko@lecad.fs.uni-lj.si)."

    def isEnabled(self):
        return True