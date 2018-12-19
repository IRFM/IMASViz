#!/usr/bin/python
"""This example demonstrates the procedure of plotting multiple arrays from
two IMAS IDS databases to a single plot.
"""

# A module providing a number of functions and variables that can be used to
# manipulate different parts of the Python runtime environment.
import sys
# PyQt library imports
from PyQt5.QtWidgets import QApplication
# IMASViz source imports
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.Viz_API import Viz_API
from imasviz.VizDataSource import DataSourceFactory
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues

# Set object managing the PyQt GUI application's control flow and main
# settings
app = QApplication(sys.argv)

# Check if necessary system variables are set
GlobalOperations.checkEnvSettings()

# Set Application Program Interface
api = Viz_API()

# Set data source retriever/factory
dataSourceFactory = DataSourceFactory()

# Set and empty list for listing data tree view frames
f = []
# Set list of shots
n_shot = [52702, 52703]

for i in range(0, 2):
    # Load IMAS databases
    dataSource = dataSourceFactory.create(dataSourceName=QVizGlobalValues.IMAS_NATIVE,
                                          shotNumber=n_shot[i],
                                          runNumber=0,
                                          userName='imas_public',
                                          imasDbName='west')
    # Append data tree view frame to list
    f.append(api.CreateDataTree(dataSource))

# Set the list of node paths (for both databases) that are to be selected
paths1 = []
for i in range(1, 3):
    paths1.append('magnetics/flux_loop(' + str(i) + ')/flux/data')
paths2 = []
for i in range(1, 3):
    paths2.append('magnetics/bpol_probe(' + str(i) + ')/field/data')

# Select signal nodes corresponding to the paths in paths list
api.SelectSignals(f[0], paths1)
api.SelectSignals(f[1], paths2)
# Plot signal nodes
# Note: Data tree view does not need to be shown in order for this routine to
#       work
api.PlotSelectedSignalsFrom(f)

# Show the data tree view window
f[0].show()
f[1].show()

# Keep the application running
app.exec()