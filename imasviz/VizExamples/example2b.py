# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

#!/usr/bin/python
# A module providing a number of functions and variables that can be used to
# manipulate different parts of the Python runtime environment.
import sys
# PyQt library imports
from PySide6.QtWidgets import QApplication
# IMASViz source imports
from imasviz.Viz_API import Viz_API
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizUtils import QVizGlobalValues, QVizGlobalOperations

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

ok, uri = QVizGlobalOperations.askForShot()
if not ok:
    print("User input has failed on first shot. Example2b not executed.")
else:
    # Set first data source
    dataSource1 = dataSourceFactory.create(uri=uri)

    # Append data tree view frame to list
    f.append(api.CreateDataTree(dataSource1))

    # set second data source
    dataSource2 = dataSourceFactory.create(uri=uri)

    # Append data tree view frame to list
    f.append(api.CreateDataTree(dataSource2))

    ok, uri = QVizGlobalOperations.askForShot()

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
        app.exec_()
