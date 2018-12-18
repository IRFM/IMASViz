#!/usr/bin/python
"""This example demonstrates the procedure of plotting multiple data to one
plot.
"""
import sys

from PyQt5.QtWidgets import QApplication

from imasviz.Viz_API import Viz_API
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling

app = QApplication(sys.argv)

QVizGlobalOperations.checkEnvSettings()

api = Viz_API()

dataSourceFactory = QVizDataSourceFactory()

f1 = api.CreateDataTree(dataSourceFactory.create(shotNumber=52344,
                                                 runNumber=0,
                                                 userName='g2penkod',
                                                 imasDbName='viztest'))
f2 = api.CreateDataTree(dataSourceFactory.create(shotNumber=52682,
                                                 runNumber=0,
                                                 userName='g2penkod',
                                                 imasDbName='viztest'))

# Set the list of paths
pathsList1 = []
for i in range(0, 5):
    pathsList1.append('magnetics/flux_loop(' + str(i) + ')/flux/data')

pathsList2 = []
for i in range(0, 6):
    pathsList2.append('magnetics/bpol_probe(' + str(i) + ')/field/data')

# Select signals corresponding to the paths in pathsList
api.SelectSignals(f1, pathsList1)
api.SelectSignals(f2, pathsList2)
# Might use also
# QVizSelectSignals(f1.dataTreeView, pathsList1).execute()
# QVizSelectSignals(f2.dataTreeView, pathsList2).execute()

f = [f1, f2]
api.PlotSelectedSignalsFrom(f)

# Show the data tree window
f1.show()
f2.show()

# Plot data from the first data source (f1) to Table Plot View
QVizSignalHandling(f1.dataTreeView).onPlotToTablePlotView(all_DTV=False)

# Plot data from the first data source (f1) to Stacked Plot View
QVizSignalHandling(f1.dataTreeView).onPlotToStackedPlotView(all_DTV=False)

sys.exit(app.exec_())
