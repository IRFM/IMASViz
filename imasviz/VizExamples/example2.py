# !/usr/bin/python
"""This example demonstrates the procedure of plotting multiple arrays to a
single plot, Table Plot View and Stacked Plot View, using IMAS IDS databases
located on the GateWay HPC.
"""

# A module providing a number of functions and variables that can be used to
# manipulate different parts of the Python runtime environment.
import sys
# PyQt library imports
from PyQt5.QtWidgets import QApplication
# IMASViz source imports
from imasviz.Viz_API import Viz_API
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling

# Set object managing the PyQt GUI application's control flow and main
# settings
app = QApplication(sys.argv)

# Check if necessary system variables are set
QVizGlobalOperations.checkEnvSettings()

# Set Application Program Interface
api = Viz_API()

# Set data source retriever/factory
dataSourceFactory = QVizDataSourceFactory()

ok, shotNumber, runNumber, userName, tokamak = QVizGlobalOperations.askForShot()

if not ok:
    print("User input has failed on first shot. Example2 not executed.")

else:
    f1 = api.CreateDataTree(dataSourceFactory.create(shotNumber=shotNumber,
                                                     runNumber=runNumber,
                                                     userName=userName,
                                                     imasDbName=tokamak))

    ok, shotNumber, runNumber, userName, tokamak = QVizGlobalOperations.askForShot()

    if not ok:
        print("User input has failed on second shot. Example2 not executed.")
    else:

        f2 = api.CreateDataTree(dataSourceFactory.create(shotNumber=shotNumber,
                                                         runNumber=runNumber,
                                                         userName=userName,
                                                         imasDbName=tokamak))


        # Add data tree view frames to list (!)
        f = [f1, f2]
        # Set the list of node paths that are to be selected
        pathsList1 = []
        for i in range(0, 5):
            pathsList1.append('magnetics/flux_loop(' + str(i) + ')/flux/data')
        pathsList2 = []
        for i in range(0, 6):
            pathsList2.append('magnetics/bpol_probe(' + str(i) + ')/field/data')

        # Select signal nodes corresponding to the paths in paths list
        api.SelectSignals(f1, pathsList1)
        api.SelectSignals(f2, pathsList2)
        # Might use also
        # QVizSelectSignals(f1.dataTreeView, pathsList1).execute()
        # QVizSelectSignals(f2.dataTreeView, pathsList2).execute()

        # Show the data tree view window
        f1.show()
        f2.show()

        # Plot signal nodes
        # Note: Data tree view does not need to be shown in order for this routine to
        #       work
        api.PlotSelectedSignalsFrom(f)


        # Plot data from the first data source (f1) to Table Plot View
        QVizSignalHandling(f1.dataTreeView).onPlotToTablePlotView(all_DTV=False)

        # Plot data from the first data source (f1) to Stacked Plot View
        QVizSignalHandling(f1.dataTreeView).onPlotToStackedPlotView(all_DTV=False)

    # Keep the application running
    sys.exit(app.exec_())
