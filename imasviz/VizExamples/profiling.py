#!/usr/bin/python
"""This example demonstrates the procedure of plotting multiple arrays to
a single plot, Table Plot View and Stacked Plot View, using IMAS IDS databases
located on the GateWay HPC.
"""

# A module providing a number of functions and variables that can be used to
# manipulate different parts of the Python runtime environment.
import sys,os

# PyQt library imports
from PyQt5.QtWidgets import QApplication
sys.path.append((os.environ['VIZ_HOME']))
# IMASViz source imports
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.Viz_API import Viz_API
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadSelectedData import QVizLoadSelectedData
from imasviz.VizGUI.QtVIZ_GUI import VizMainWindow



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
                                 userName='imas_public',
                                 imasDbName='west')

# Build the data tree view frame
f = api.CreateDataTree(dataSource)
#f.show()
api.LoadIDSData(f, 'equilibrium', 0, 0)

#QVizLoadSelectedData(f.dataTreeView, 'magnetics', 0, 0).execute()
f.show()

# Keep the application running
app.exec()
