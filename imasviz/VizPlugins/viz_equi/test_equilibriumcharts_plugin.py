# -*- coding: utf-8 -*-
"""This example demonstrates the procedure of directly running equilibrium
plugin for specified database using script.
Note: Script is adjusted to use IMAS database found on the GateWay.
"""

# A module providing a number of functions and variables that can be used to
# manipulate different parts of the Python runtime environment.
import sys
# PyQt library imports
from PyQt5.QtWidgets import QApplication
# IMASViz source imports
from imasviz.Viz_API import Viz_API
from imasviz.VizDataSource.QVizDataSourceFactory import \
    QVizDataSourceFactory
from imasviz.VizUtils import QVizGlobalOperations
from imasviz.VizPlugins.viz_equi import equilibriumcharts

# Set object managing the PyQt GUI application's control flow and main
# settings
app = QApplication(sys.argv)

# Check if necessary system variables are set
QVizGlobalOperations.checkEnvSettings()

# Set Application Program Interface
api = Viz_API()

# Set data source retriever/factory
dataSourceFactory = QVizDataSourceFactory()

# Load IMAS database and build the data tree view frame
f1 = api.CreateDataTree(dataSourceFactory.create(shotNumber=52344,
                                                 runNumber=0,
                                                 userName='g2penkod',
                                                 imasDbName='viztest'))

# Get equilibrium treeWidget item (QVizTreeNode)
eq_item = f1.dataTreeView.IDSRoots['equilibrium']

# Get selected item/subject data dict
infoDict = eq_item.getInfoDict()

# Show the data tree view window
# f1.show()

# Get equilibrium data and set plugin frame
app.frame = equilibriumcharts.PlotFrame(infoDict, parent=f1.dataTreeView)

# Show frame
app.frame.show()

# Keep the application running
sys.exit(app.exec_())
