# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

#!/usr/bin/python
"""This test file executes the plugin 'viz_example_plugin' for testing
"""
import sys, logging, os
# PyQt library imports
from PySide6.QtWidgets import QApplication
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

ok, uri = QVizGlobalOperations.askForShot()  # Asking for a shot

if not ok:
    logging.error("User input has failed. Test not executed.")
    exit()

# Creating IMASViz data source for this shot
dataSource = QVizDataSourceFactory().create(dataSourceName=QVizGlobalValues.IMAS_NATIVE, uri=uri)

f = api.CreateDataTree(dataSource)  # Build the data tree view frame
# paths = ['equilibrium.time_slice[0].profiles_1d.j_tor'] # Set the list of node paths that are to be selected
# paths = {'paths' : paths, 'occurrences' : [0]} # Change paths to specify occurrence of each path
#
# # Select signal nodes corresponding to the paths in paths list
# api.SelectSignals(f, paths)

# Execution of the 'viz_example_plugin' plugin
plugin_instance = viz_example_plugin(f.dataTreeView.selectedItem, f.dataTreeView)
plugin_instance.execute(api, pluginEntry=2)

app.exec_()  # Keep the application running
