#!/usr/bin/python
"""This file uses the QVizPlotImageWidget for testing purpose
"""
import logging
import sys

import numpy as np
from PySide2.QtWidgets import QApplication

from imasviz.VizEntities.QVizDataArrayHandle import QVizDataArrayHandle, ArrayCoordinates
from imasviz.VizGUI.VizPlot.VizPlotFrames.QvizPlotImageWidget import QvizPlotImageWidget
# IMASViz source imports
from imasviz.VizUtils import QVizGlobalOperations
from imasviz.Viz_API import Viz_API
from imasviz.Viz_DataSelection_API import Viz_DataSelection_API

# PyQt library imports

# Set object managing the PyQt GUI application's control flow
app = QApplication(sys.argv)

# Check if necessary system variables are set
QVizGlobalOperations.checkEnvSettings()

# Setting the logger
root = logging.getLogger()
root.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)

api = Viz_API()  # Creating IMASViz Application Programming Interface
selection_api = Viz_DataSelection_API()
ok, shotNumber, runNumber, userName, database = QVizGlobalOperations.askForShot()  #  Asking for a shot

if not ok:
    logging.error("User input has failed. Test not executed.")
    exit()

#shotNumber = 54178
#runNumber = 0
#userName= 'imas_public'
#database = 'west'

# Creating IMASViz data source for this shot
#dataSource = QVizDataSourceFactory().create(dataSourceName=QVizGlobalValues.IMAS_NATIVE,
#                                      shotNumber=shotNumber,
#                                      runNumber=runNumber,
#                                      userName=userName,
#                                      imasDbName=database)

#f = api.CreateDataTree(dataSource) # Build the data tree view frame

# Set the list of node paths that are to be selected
paths = []
paths.append('spectrometer_visible/channel(101)/grating_spectrometer/intensity_spectrum/data')

# Change it to dictionary with paths an occurrences (!)
pathsDict = {'paths' : paths, 'occurrences' : [0]}

# Select signal nodes corresponding to the paths in paths list
#api.SelectSignals(f, pathsDict)
#dtv = f.dataTreeView
#dataArrayHandles = selection_api.GetSelectedDataFeatures(dataTreeView=dtv)
coordinatesPath = ['path.x', 'path.y']
coordinatesValues = []
coordinatesValues.append(np.linspace(0, 100., num=100))
coordinatesValues.append(np.linspace(10., 33., num=200))
coordinates_labels = ['x_label', 'y_label']
timeCoordinateDim = 2

arrayCoordinates=ArrayCoordinates(coordinatesPath, coordinatesValues, timeCoordinateDim, coordinates_labels)

sinx = np.sin(coordinatesValues[0]/50)
cosy = np.cos(coordinatesValues[1]/20)
arrayValues = np.zeros((100, 200))
for i in range(0, 100):
  arrayValues[i, :] = sinx[i]*cosy
print(np.shape(arrayValues))
name='test'
label='label of the test'
dataArrayHandle = QVizDataArrayHandle(arrayCoordinates, arrayValues, name, label)

plotWidget = QvizPlotImageWidget(dataTreeView=None, plotSliceFromROI=True, showImageTitle=False)
plotWidget.plot(dataArrayHandle)
plotWidget.show()

app.exec_() # Keep the application running
