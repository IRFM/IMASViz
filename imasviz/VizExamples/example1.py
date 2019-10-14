#!/usr/bin/python
"""This example demonstrates the procedure of plotting multiple arrays to
a single plot, Table Plot View and Stacked Plot View, using IMAS IDS databases
located on the GateWay HPC.
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
                                 shotNumber=54178,
                                 runNumber=0,
                                 userName='fleuryl',
                                 imasDbName='test')

# Database on the GateWay HPC (comment the above dataSource code and uncomment
# the one below)
# dataSource = dataSourceFactory.create(shotNumber=52344,
#                                       runNumber=0,
#                                       userName='g2penkod',
#                                       imasDbName='viztest')


# Build the data tree view frame
f = api.CreateDataTree(dataSource)

# Set the list of node paths that are to be selected
paths = []
for i in range(0,6):
    paths.append('magnetics/flux_loop(' + str(i) + ')/flux/data')

# Change it to dictionary with paths an occurrences (!)
paths = {'paths' : paths,
         'occurrences' : [0]}

# Optional: Option with single path in dictionary
# paths = {'paths' : 'magnetics/flux_loop(1)/flux/data'}
# or
# paths = {'paths' : ['magnetics/flux_loop(1)/flux/data']}

# Select signal nodes corresponding to the paths in paths list
api.SelectSignals(f, paths)

# Plot signal nodes
# Note: Data tree view does not need to be shown in order for this routine to
#       work
api.PlotSelectedSignals(f)

# Keep the application running
app.exec()
