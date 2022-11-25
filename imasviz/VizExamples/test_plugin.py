#!/usr/bin/python
"""This test file executes the plugin 'viz_example_plugin' for testing
"""
import sys, logging, os
# PyQt library imports
from PySide2.QtWidgets import QApplication
# IMASViz source imports
from imasviz.VizUtils import QVizGlobalOperations, QVizGlobalValues
from imasviz.Viz_API import Viz_API
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizPlugins.viz_example_plugin.viz_example_plugin import viz_example_plugin

# Set object managing the PyQt GUI application's control flow
app = QApplication(sys.argv)

# Check if necessary system variables are set
QVizGlobalOperations.checkEnvSettings()

# Setting the logger
root = logging.getLogger()
root.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)

api = Viz_API()  # Creating IMASViz Application Programming Interface

ok, shotNumber, runNumber, userName, database = QVizGlobalOperations.askForShot()  #  Asking for a shot

if not ok:
    logging.error("User input has failed. Test not executed.")
    exit()

# Creating IMASViz data source for this shot
dataSource = QVizDataSourceFactory().create(dataSourceName=QVizGlobalValues.IMAS_NATIVE,
                                      shotNumber=shotNumber,
                                      runNumber=runNumber,
                                      userName=userName,
                                      imasDbName=database)

f = api.CreateDataTree(dataSource) # Build the data tree view frame
# paths = ['equilibrium.time_slice[0].profiles_1d.j_tor'] # Set the list of node paths that are to be selected
# paths = {'paths' : paths, 'occurrences' : [0]} # Change paths to specify occurrence of each path
#
# # Select signal nodes corresponding to the paths in paths list
# api.SelectSignals(f, paths)

# Execution of the 'viz_example_plugin' plugin
plugin_instance = viz_example_plugin(f.dataTreeView.selectedItem, f.dataTreeView)
plugin_instance.execute(api, pluginEntry=2)

app.exec() # Keep the application running
