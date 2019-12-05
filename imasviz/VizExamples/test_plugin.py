#!/usr/bin/python
"""This example demonstrates the procedure of plotting multiple arrays to
a single plot, Table Plot View and Stacked Plot View, using IMAS IDS databases
located on the GateWay HPC.
"""

# A module providing a number of functions and variables that can be used to
# manipulate different parts of the Python runtime environment.
import sys, logging, os
# PyQt library imports
from PyQt5.QtWidgets import QApplication
# IMASViz source imports
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.Viz_API import Viz_API
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues
from imasviz.VizPlugins.viz_1D_overtime.viz_1D_overtime_plugin import viz_1D_overtime_plugin
from PyQt5.QtWidgets import QMessageBox, QInputDialog, QLineEdit

# Set object managing the PyQt GUI application's control flow and main
# settings
app = QApplication(sys.argv)

# Check if necessary system variables are set
QVizGlobalOperations.checkEnvSettings()

root = logging.getLogger()
root.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)

# Set Application Program Interface
api = Viz_API()

# Set data source retriever/factory
dataSourceFactory = QVizDataSourceFactory()

ok, shotNumber, runNumber, userName, tokamak = QVizGlobalOperations.askForShot()

if not ok:
    print("User input has failed. Test not executed.")
else:

    # Load IMAS database
    dataSource = dataSourceFactory.create(dataSourceName=QVizGlobalValues.IMAS_NATIVE,
                                          shotNumber=shotNumber,
                                          runNumber=runNumber,
                                          userName=userName,
                                          imasDbName=tokamak)

    # Build the data tree view frame
    f = api.CreateDataTree(dataSource)

    # Set the list of node paths that are to be selected
    paths = []
    paths.append('equilibrium.time_slice[0].profiles_1d.j_tor')
    # paths = []
    # for i in range(0,1):
    #     paths.append('magnetics/flux_loop(' + str(i) + ')/flux/data')

    # Change it to dictionary with paths an occurrences (!)
    paths = {'paths' : paths,
             'occurrences' : [0]}

    # Select signal nodes corresponding to the paths in paths list
    api.SelectSignals(f, paths)

    plugin_instance = viz_1D_overtime_plugin(f.dataTreeView.selectedItem, f.dataTreeView)
    plugin_instance.execute(api)

    #f.show()
    # Keep the application running
    app.exec()
