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
pathsList = []
for i in range(0,2):
    pathsList.append('magnetics/flux_loop(' + str(i) + ')/flux/data')

# Select signals corresponding to the paths in pathsList
api.SelectSignals(f1, pathsList)
api.SelectSignals(f2, pathsList)
# Can use also
# QVizSelectSignals(f1.dataTreeView, pathsList).execute()
# QVizSelectSignals(f2.dataTreeView, pathsList).execute()

f = [f1,f2]
#api.PlotSelectedSignalsFrom(f)

# Show the data tree window
f1.show()
f2.show()

sys.exit(app.exec_())