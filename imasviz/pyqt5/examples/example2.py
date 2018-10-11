#!/usr/bin/python
"""This example demonstrates the procedure of plotting multiple data to one
plot.
"""
from imasviz.Browser_API import Browser_API
from imasviz.data_source.DataSourceFactory import DataSourceFactory
from imasviz.util.GlobalOperations import GlobalOperations
from PyQt5.QtWidgets import QApplication
import sys
from imasviz.pyqt5.src.VizGUI.VizGUICommands.VizSignalSelectionCommands.QVizSelectSignals \
    import QVizSelectSignals

from imasviz.gui_commands.select_commands.LoadSelectedData import LoadSelectedData

app = QApplication(sys.argv)

GlobalOperations.checkEnvSettings()

api = Browser_API()

dataSourceFactory = DataSourceFactory()

f1 = api.CreateDataTree(dataSourceFactory.create(shotNumber = 52344,
                                                 runNumber = 0,
                                                 userName = 'g2penkod',
                                                 imasDbName = 'test'))
f2 = api.CreateDataTree(dataSourceFactory.create(shotNumber = 52682,
                                                 runNumber = 0,
                                                 userName = 'g2penkod',
                                                 imasDbName = 'test'))

# Set the list of paths
pathsList1 = []
for i in range(0,2):
    pathsList1.append('magnetics/flux_loop(' + str(i) + ')/flux/data')

pathsList2 = []
for i in range(0,3):
    pathsList2.append('magnetics/bpol_probe(' + str(i) + ')/field/data')

# Select signals corresponding to the paths in pathsList
api.SelectSignals(f1, pathsList1)
api.SelectSignals(f2, pathsList2)
# Can use also
# QVizSelectSignals(f1.dataTreeView, pathsList1).execute()
# QVizSelectSignals(f2.dataTreeView, pathsList2).execute()

f = [f1,f2]
#api.PlotSelectedSignalsFrom(f)

# Show the data tree window
f1.show()
f2.show()

sys.exit(app.exec_())