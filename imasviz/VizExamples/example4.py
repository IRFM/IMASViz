#  Name   : example4.py
#
#           An example of IMASViz script demonstrating how to select signals
#           from the selected configuration file and plots it to the TablePlot.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- L. Fleury,X. Li, D. Penko
#****************************************************

#!/usr/bin/python

import os
# A module providing a number of functions and variables that can be used to
# manipulate different parts of the Python runtime environment.
import sys
# PyQt library imports
from PySide6.QtWidgets import QApplication
# IMASViz source imports
from imasviz.VizUtils import QVizGlobalOperations, QVizGlobalValues
from imasviz.Viz_API import Viz_API
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignals import QVizSelectSignals
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizUnselectAllSignals import QVizUnselectAllSignals
from PySide6.QtWidgets import QFileDialog

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

ok, uri = QVizGlobalOperations.askForShot()

if not ok:
    print("User input has failed. Example3 not executed.")
else:

    # Load IMAS database
    dataSource = dataSourceFactory.create(
        uri=uri)

    # Build the data tree view frame
    f = api.CreateDataTree(dataSource)

    # Set configuration file using file dialog
    # Note: configuration files are located in $HOME/.imasviz by default
    options = QFileDialog.Options()
    options |= QFileDialog.DontUseNativeDialog
    configFilePath, ok = QFileDialog.getOpenFileName(None,
                         "Select plot config. file",
                         os.environ["HOME"]+"/.imasviz/",
                         "LSP Files (*.lsp*)",
                         options=options)

    if not ok:
        print("User input has failed. Example4 not executed.")
    else:
        # Extract signal paths from the config file and add them to a list of
        # paths
        pathsMap = QVizGlobalOperations.getSignalsPathsFromConfigurationFile(
            configFile=configFilePath)

        # First unselect all signals (optional)
        # QVizUnselectAllSignals(dataTreeView=f.dataTreeView).execute()

        # Select the signals, defined by a path in a list of paths, in the
        # given Data Tree View (DTV) window
        QVizSelectSignals(dataTreeView=f.dataTreeView,
                          pathsMap=pathsMap).execute()

        # Plot the set of the signal nodes selected using plot configuration file to
        # a new Table Plot View and apply plot configurations (colors, line width etc.)
        api.PlotSelectedSignalsInTablePlotViewFrame(f)

        # Show the DTV window
        # f.show()
        # Keep the application running
        app.exec_()
