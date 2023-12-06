#  Name   : viz_example_plugin
#
#           A plugin example that demonstrates how to provide multiple features
#           from the same plugin code.
#
#           Important: Every plugin must be registered in IMASViz. This is done
#           by adding the plugin in the "RegisteredPlugins" in top part of the
#           "imasviz.VizPlugins.VizPlugin.py" file. The entry format is is
#           "<Plugin main class name>: <plugin_dir/plugin_py_file>".
#
#           The <Plugin main class name> and <plugin_py_file> must be the same!
#
#           In this case would be:
#           'viz_example_plugin' : 'viz_example_plugin.viz_example_plugin'
#
#           Use of Python version 3.7 is recommended, as IMASViz does not
#           support Python2 anymore.
#
#  Author :
#         Ludovic Fleury
#  E-mail :
#         ludovic.fleury@cea.fr
#
# ****************************************************
#     Copyright(c) 2019- L. Fleury

from imasviz.VizPlugins.VizPlugin import VizPlugin
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSelectedSignals import QVizPlotSelectedSignals
#from imasviz.VizPlugins.viz_example_plugin.real_time import Graph

import traceback
import logging
import numpy as np
import pyqtgraph as pg


class viz_example_plugin(VizPlugin):  # The plugin has to inherit from VizPlugin
    def __init__(self, *args, **kwargs):
        VizPlugin.__init__(self, *args, **kwargs)

    #this function is caught by IMASViz when the user selects an entry provided by the plugin
    def execute(self, vizAPI, pluginEntry):  #Note that all exceptions not caught by this function are caught by IMASViz

        try:
            ####
            # pluginEntry is an integer which has been set by the user when selecting an item from the IMASViz plugins menu
            #pluginEntry = 0 if the user has selected the first entry provided by the plugin
            #pluginEntry = 1 if the user has selected the second entry provided by the plugin
            # and so on...
            #All possible entries of a plugin are returned by the getAllEntries() function below which is implemented
            #by all plugins.
            ###
            if pluginEntry == 0:  #user has selected the first entry, so we call the first feature provided
                # by the plugin
                self.firstEntry(vizAPI)
            elif pluginEntry == 1:  #user has selected the second entry, so we call the second feature provided
                # by the plugin
                self.secondEntry(vizAPI)
            elif pluginEntry == 2:
                self.thirdEntry()

        except :
            traceback.print_exc()
            logging.getLogger(self.dataTreeView.dataSource.uri).error(traceback.format_exc())

    #Implementation of the first feature provided by this plugin
    #This feature prints some informations in the log window using the IMASViz API.
    def firstEntry(self, vizAPI):
        logging.info('First entry of the viz_example_plugin to be executed...')
        logging.info('Documentation: ' + self.selectedTreeNode.getDocumentation())
        logging.info('Is IDS root? ' + str(self.selectedTreeNode.isIDSRoot()))
        logging.info('Data available? ' + str(self.selectedTreeNode.hasAvailableData()))
        logging.info('Data type: ' + self.selectedTreeNode.getDataType())
        logging.info('Is 1D and dynamic? ' + str(self.selectedTreeNode.is1DAndDynamic()))
        logging.info('Has homogeneous time? ' + str(self.selectedTreeNode.hasHomogeneousTime()))
        logging.info('Python data path: ' + self.selectedTreeNode.getDataName())
        logging.info('IMAS data path: ' + self.selectedTreeNode.getPath())
        logging.info('Parametrized path.: ' + self.selectedTreeNode.getParametrizedDataPath())
        logging.info('Parametrized coordinate1: ' + self.selectedTreeNode.getParametrizedCoordinate(coordinateNumber=1))
        logging.info('Coordinate1 (evaluated): ' + str(self.selectedTreeNode.
                                                       coordinateValues(coordinateNumber=1,
                                                                        dataTreeView=self.dataTreeView)))
        logging.info('Time dependent? ' + str(self.selectedTreeNode.
                                              isCoordinateTimeDependent(coordinateNumber=1)))
        logging.info('Embedded in a dynamic AOS? ' + str(self.selectedTreeNode.
                                                         embedded_in_time_dependent_aos()))

    # Implementation of the second feature provided by this plugin
    # This feature draws a 2D plot using pyqtgraph.
    def secondEntry(self, vizAPI):
        ## Create random 3D data set with noisy signals
        img = pg.gaussianFilter(np.random.normal(size=(200, 200)), (5, 5)) * 20 + 100
        img = img[np.newaxis, :, :]
        decay = np.exp(-np.linspace(0, 0.3, 100))[:, np.newaxis, np.newaxis]
        data = np.random.normal(size=(100, 200, 200))
        data += img * decay
        data += 2

        ## Add time-varying signal
        sig = np.zeros(data.shape[0])
        sig[30:] += np.exp(-np.linspace(1, 10, 70))
        sig[40:] += np.exp(-np.linspace(1, 10, 60))
        sig[70:] += np.exp(-np.linspace(1, 10, 30))

        sig = sig[:, np.newaxis, np.newaxis] * 3
        data[:, 50:60, 30:40] += sig
        imv = pg.image(data)
        ## Display the data and assign each frame a time value from 1.0 to 3.0
        imv.setImage(data, xvals=np.linspace(1., 3., data.shape[0]))

        ## Set a custom color map
        colors = [
            (0, 0, 0),
            (45, 5, 61),
            (84, 42, 55),
            (150, 87, 60),
            (208, 171, 141),
            (255, 255, 255)
        ]
        cmap = pg.ColorMap(pos=np.linspace(0.0, 1.0, 6), color=colors)
        imv.setColorMap(cmap)

    def thirdEntry(self):
        g = Graph()
        g.setup()
        #g.run()

    def getEntries(self):
        #The first feature is displayed only if a 1D array is selected by the user
        if self.selectedTreeNode.is1DAndDynamic():
            return [0]
        #The second feature is displayed only if the user selects the root of an IDS
        elif self.selectedTreeNode.isIDSRoot():
            return [1]
        else:
            return []

    #The first entry (0) is diplayed with the menu item 'Prints node info to log using IMASViz API...'
    #The second entry (1) is displayed with the menu item 'Shows a 2D plot...'
    def getAllEntries(self):
        return [(0, 'Prints some node attributes to log using IMASViz API...'), (1, 'Shows a 2D plot...')]

    def getDescription(self):
        """ Return plugin description.
        """

        return "A plugin example that demonstrates how to provide  \n" \
               "multiple features from the same plugin code. \n"       \
               "Authors: Ludovic Fleury (ludovic.fleury@cea.fr)."

    def isEnabled(self):
        return True
