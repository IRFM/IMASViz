#  Name   : example1.py
#
#           An example of IMASViz script demonstrating how to plot multiple
#           signals (defined by paths) to a regular plot.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
# ****************************************************
#     Copyright(c) 2016- L. Fleury,X. Li, D. Penko
# ****************************************************

# !/usr/bin/python
"""This example demonstrates the procedure of plotting multiple arrays to
a single plot, Table Plot View and Stacked Plot View, using IMAS IDS databases
located on the GateWay HPC.
"""

# A module providing a number of functions and variables that can be used to
# manipulate different parts of the Python runtime environment.
import sys
# PyQt library imports
from PySide6.QtWidgets import QApplication
# IMASViz source imports
from imasviz.VizUtils import QVizGlobalOperations, QVizGlobalValues
from imasviz.Viz_API import Viz_API
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory

# Set object managing the PyQt GUI application's control flow and main
# settings
app = QApplication(sys.argv)

# Check if necessary system variables are set
QVizGlobalOperations.checkEnvSettings()

# Set Application Program Interface
api = Viz_API()

# Set data source retriever/factory
dataSourceFactory = QVizDataSourceFactory()

ok, uri = QVizGlobalOperations.askForShot()

if not ok:
    print("User input has failed. Example1 not executed.")
else:
    # Load IMAS database
    dataSource = dataSourceFactory.create(
                                     uri=uri,
                                     dataSourceName=QVizGlobalValues.IMAS_NATIVE)


    # Build the data tree view frame
    f = api.CreateDataTree(dataSource)

    # Set the list of node paths that are to be selected
    paths = []
    for i in range(0,6):
        paths.append('magnetics/flux_loop(' + str(i) + ')/flux/data')

    # Change it to dictionary with paths an occurrences (!)
    pathsDict = {'paths' : paths,
             'occurrences' : [0]}

    # Optional: Option with single path in dictionary
    # paths = {'paths' : 'magnetics/flux_loop(1)/flux/data'}
    # or
    # paths = {'paths' : ['magnetics/flux_loop(1)/flux/data']}

    # Select signal nodes corresponding to the paths in paths list
    api.SelectSignals(f, pathsDict)

    # Plot signal nodes
    # Note: Data tree view does not need to be shown in order for this routine to
    #       work
    api.PlotSelectedSignals(f)

# Keep the application running
app.exec_()
