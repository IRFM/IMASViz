#  Name   : example2b.py
#
#           An example of IMASViz script demonstrating how to plot multiple
#           signals (defined by paths) from two different IMAS IDS databases.
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
# A module providing a number of functions and variables that can be used to
# manipulate different parts of the Python runtime environment.
import sys
# PyQt library imports
from PyQt5.QtWidgets import QApplication
# IMASViz source imports
from imasviz.Viz_API import Viz_API
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations

# Set object managing the PyQt GUI application's control flow and main
# settings
app = QApplication(sys.argv)

# Check if necessary system variables are set
QVizGlobalOperations.checkEnvSettings()

# Set Application Program Interface
api = Viz_API()

# Set data source retriever/factory
dataSourceFactory = QVizDataSourceFactory()

# Set and empty list for listing data tree view frames
f = []
# Set list of shots
#n_shot = [52702, 52703]

ok, shotNumber, runNumber, userName, tokamak = QVizGlobalOperations.askForShot()
if not ok:
    print("User input has failed on first shot. Example2b not executed.")
else:
    # Set first data source
    dataSource1 = dataSourceFactory.create(dataSourceName=QVizGlobalValues.IMAS_NATIVE,
                                          shotNumber=shotNumber,
                                          runNumber=runNumber,
                                          userName=userName,
                                          imasDbName=tokamak)

    # Append data tree view frame to list
    f.append(api.CreateDataTree(dataSource1))

    # set second data source
    dataSource2 = dataSourceFactory.create(dataSourceName=QVizGlobalValues.IMAS_NATIVE,
                                          shotNumber=shotNumber,
                                          runNumber=runNumber,
                                          userName=userName,
                                          imasDbName=tokamak)

    # Append data tree view frame to list
    f.append(api.CreateDataTree(dataSource2))

    ok, shotNumber, runNumber, userName, tokamak = QVizGlobalOperations.askForShot()

    if not ok:
        print("User input has failed on second shot. Example2b not executed.")
    else:
        # Set the list of node paths (for both databases) that are to be selected
        pathsList1 = []
        for i in range(0, 3):
            pathsList1.append('magnetics/flux_loop(' + str(i) + ')/flux/data')
        pathsList2 = []
        for i in range(0, 3):
            pathsList2.append('magnetics/bpol_probe(' + str(i) + ')/field/data')

        # Define the dictionary holding the list of paths and occurrence value
        pathsDict1 = {'paths' : pathsList1,
                      'occurrences' : [0]}

        pathsDict2 = {'paths' : pathsList2,
                      'occurrences' : [0]}

        # Select signal nodes corresponding to the paths in paths list
        api.SelectSignals(f[0], pathsDict1)
        api.SelectSignals(f[1], pathsDict2)
        # Plot signals (e.g. data from nodes)
        # Note: Data tree view does not need to be shown in order for this
        #       routine to work
        api.PlotSelectedSignalsFrom([f[0]]) # Plot signals from first source to
                                            # first figure
        api.PlotSelectedSignalsFrom([f[1]]) # Plot signals from first source to
                                            # second figure
        api.PlotSelectedSignalsFrom(f) # Plots selected signals from both sources
                                       # to the same figure

        # Show the data tree view window
        f[0].show()
        f[1].show()

        # Keep the application running
        app.exec()