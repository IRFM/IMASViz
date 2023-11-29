#!/usr/bin/python
"""This example demonstrates the procedure of plotting multiple arrays to
a single plot, Table Plot View and Stacked Plot View, using IMAS IDS databases
located on the GateWay HPC.
"""

# A module providing a number of functions and variables that can be used to
# manipulate different parts of the Python runtime environment.
import sys, os
# PyQt library imports
from PySide6.QtWidgets import QApplication
# IMASViz source imports
from imasviz.VizUtils import QVizGlobalOperations, QVizGlobalValues
from imasviz.Viz_API import Viz_API
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from PySide6.QtWidgets import QInputDialog

# Set object managing the PyQt GUI application's control flow and main
# settings
app = QApplication(sys.argv)

# Check if necessary system variables are set
QVizGlobalOperations.checkEnvSettings()

# Set Application Program Interface
api = Viz_API()

# Set data source retriever/factory
dataSourceFactory = QVizDataSourceFactory()


URI, ok = QInputDialog.getText(None, "Shot number", "enter an URI")

if not ok:
    print("User input has failed. Test not executed.")
else:

    # Load IMAS database
    dataSource = dataSourceFactory.create(uri=uri)

    # Build the data tree view frame
    f = api.CreateDataTree(dataSource)

    # Set the list of node paths that are to be selected
    paths = []
    for i in range(0,6):
        paths.append('magnetics/flux_loop(' + str(i) + ')/flux/data')

    # Change it to dictionary with paths an occurrences (!)
    paths = {'paths' : paths,
             'occurrences' : [0]}

    # Select signal nodes corresponding to the paths in paths list
    api.SelectSignals(f, paths)

    f.show()
    # Keep the application running
    app.exec_()
