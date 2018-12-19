#!/usr/bin/python

import os
# A module providing a number of functions and variables that can be used to
# manipulate different parts of the Python runtime environment.
import sys
# PyQt library imports
from PyQt5.QtWidgets import QApplication
# IMASViz source imports
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.Viz_API import Viz_API
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignals import QVizSelectSignals
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizUnselectAllSignals import QVizUnselectAllSignals
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

# Set user (get current user)
userName = os.environ['USER']

# Load IMAS database
dataSource = dataSourceFactory.create(
                                    dataSourceName=QVizGlobalValues.IMAS_NATIVE,
                                    shotNumber=52344,
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

# Set configuration file
configFilePath = os.environ['HOME'] + "/.imasviz/configuration_name.pcfg"

# Extract signal paths from the config file and add them to a list of
# paths
pathsList = QVizGlobalOperations.getSignalsPathsFromConfigurationFile(
    configFile=configFilePath)

# First unselect all signals (optional)
# QVizUnselectAllSignals(dataTreeView=f.dataTreeView).execute()

# Select the signals, defined by a path in a list of paths, in the
# given Data Tree View (DTV) window
QVizSelectSignals(dataTreeView=f.dataTreeView,
                  pathsList=pathsList).execute()

# Plot the set of the signal nodes selected using plot configuration file to
# a new Table Plot View and apply plot configurations (colors, line width etc.)
api.ApplyTablePlotViewConfiguration(f, configFilePath=configFilePath)

# Keep the application running
app.exec()
