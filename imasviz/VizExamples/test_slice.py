#!/usr/bin/python
"""This test file executes the plugin 'viz_example_plugin' for testing
"""
from PyQt5.QtWidgets import QApplication
import sys, logging, os
import numpy as np
import pyqtgraph as pg
# PyQt library imports

# IMASViz source imports
from imasviz.VizUtils import QVizGlobalOperations, QVizGlobalValues
from imasviz.Viz_API import Viz_API
from imasviz.Viz_DataSelection_API import Viz_DataSelection_API
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizPlugins.viz_example_plugin.viz_example_plugin import viz_example_plugin
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal import QVizPlotSignal
from imasviz.VizGUI.VizPlot.VizPlotFrames.QvizPlotImageWidget import QvizPlotImageWidget


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
#ok, shotNumber, runNumber, userName, database = QVizGlobalOperations.askForShot()  #  Asking for a shot

#if not ok:
#    logging.error("User input has failed. Test not executed.")
#    exit()

shotNumber = 54178
runNumber = 0
userName= 'g2lfleur'
database = 'west'

# Creating IMASViz data source for this shot
dataSource = QVizDataSourceFactory().create(dataSourceName=QVizGlobalValues.IMAS_NATIVE,
                                      shotNumber=shotNumber,
                                      runNumber=runNumber,
                                      userName=userName,
                                      imasDbName=database)

f = api.CreateDataTree(dataSource) # Build the data tree view frame

# Set the list of node paths that are to be selected
paths = []
paths.append('spectrometer_visible/channel(101)/grating_spectrometer/intensity_spectrum/data')

# Change it to dictionary with paths an occurrences (!)
pathsDict = {'paths' : paths, 'occurrences' : [0]}

# Select signal nodes corresponding to the paths in paths list
api.SelectSignals(f, pathsDict)
dtv = f.dataTreeView
dataArrayHandles = selection_api.GetSelectedDataFeatures(dataTreeView=dtv)

dataArrayHandle = dataArrayHandles[0]

plotWidget = QvizPlotImageWidget(dataTreeView=dtv, plotSliceFromROI=True)
plotWidget.addPlot(dataArrayHandle)
plotWidget.show()

#pg.ImageWindow

# imv = pg.image(y)
# imv.setImage(y)
# #
# # ## Set a custom color map
# colors = [
#     (0, 0, 0),
#     (45, 5, 61),
#     (84, 42, 55),
#     (150, 87, 60),
#     (208, 171, 141),
#     (255, 255, 255)
# ]
# cmap = pg.ColorMap(pos=np.linspace(0.0, 1.0, 6), color=colors)
# imv.setColorMap(cmap)

app.exec() # Keep the application running