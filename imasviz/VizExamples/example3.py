#!/usr/bin/python
"""This example demonstrates the procedure of plotting multiple arrays to a
single Table Plot View.
"""

# A module providing a number of functions and variables that can be used to
# manipulate different parts of the Python runtime environment.
import sys
# PyQt library imports
from PyQt5.QtWidgets import QApplication
# IMASViz source imports
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.Viz_API import Viz_API
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues

# Set object managing the PyQt GUI application's control flow and main
# settings
app = QApplication(sys.argv)

# Check if necessary system variables are set
QVizGlobalOperations.checkEnvSettings()

# Set Application Program Interface
api = Viz_API()

# Set data source retriever/factory
dataSourceFactory = QVizDataSourceFactory()

# Load IMAS database
dataSource = dataSourceFactory.create(
                                    dataSourceName=QVizGlobalValues.IMAS_NATIVE,
                                    shotNumber=52682,
                                    runNumber=0,
                                    userName='imas_public',
                                    imasDbName='west')

# Database on the GateWay HPC (comment the above dataSource code and uncomment
# the one below)
# dataSource = dataSourceFactory.create(shotNumber=52344,
#                                       runNumber=0,
#                                       userName='g2penkod',
#                                       imasDbName='viztest')

# Build the data tree view frame
f = api.CreateDataTree(dataSource)

# Set the list of node paths that are to be selected
pathsList = []
for i in range(0, 5):
    pathsList.append('magnetics/flux_loop(' + str(i) + ')/flux/data')

# Select signal nodes corresponding to the paths in paths list
api.SelectSignals(f, pathsList)

# Plot the set of signal nodes selected by the user to a new Table Plot View.
api.PlotSelectedSignalsInTablePlotViewFrame(f)

# Show the data tree view window
api.ShowDataTree(f)

# Keep the application running
app.exec()
