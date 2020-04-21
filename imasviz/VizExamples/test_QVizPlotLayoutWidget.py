#!/usr/bin/python
"""This test file executes the plugin 'viz_example_plugin' for testing
"""
import sys, logging, os
import numpy as np
import pyqtgraph as pg
# PyQt library imports
from PyQt5.QtWidgets import QApplication
# IMASViz source imports
from imasviz.VizUtils import QVizGlobalOperations, QVizGlobalValues
from imasviz.Viz_API import Viz_API
from imasviz.Viz_DataSelection_API import Viz_DataSelection_API
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizPlugins.viz_example_plugin.viz_example_plugin import viz_example_plugin
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal import QVizPlotSignal

from imasviz.VizGUI.VizPlot.VizPlotFrames.QvizPlotLayoutWidget import QvizPlotLayoutWidget
from imasviz.VizGUI.VizPlot.QVizCustomPlotContextMenu \
    import QVizCustomPlotContextMenu



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
userName= 'fleuryl'
database = 'west'

# Creating IMASViz data source for this shot
dataSource = QVizDataSourceFactory().create(dataSourceName=QVizGlobalValues.IMAS_NATIVE,
                                      shotNumber=shotNumber,
                                      runNumber=runNumber,
                                      userName=userName,
                                      imasDbName=database)

f = api.CreateDataTree(dataSource) # Build the data tree view frame

# Set the list of node paths that are to be selected
# paths = []
# for i in range(0,8):
#     paths.append('magnetics/flux_loop(' + str(i) + ')/flux/data')
paths = []
paths.append('spectrometer_visible/channel(101)/grating_spectrometer/intensity_spectrum/data')

# Change it to dictionary with paths an occurrences (!)
pathsDict = {'paths' : paths, 'occurrences' : [0]}

# Optional: Option with single path in dictionary
# paths = {'paths' : 'magnetics/flux_loop(1)/flux/data'}
# or
# paths = {'paths' : ['magnetics/flux_loop(1)/flux/data']}
#spectrometer_visible.channel[101].grating_spectrometer.intensity_spectrum.data

# Select signal nodes corresponding to the paths in paths list
api.SelectSignals(f, pathsDict)
dtv = f.dataTreeView
plotWidget = QvizPlotLayoutWidget(rows=100, columns=3, size=(1000, 600), dataTreeView=f)
data_features = selection_api.GetSelectedDataFeatures(dataTreeView=dtv)

data_feature = data_features[0]
y = data_feature[3]

coordinates = data_feature[2]
time = coordinates[1]
print(len(time[0]))
print('test')
print(np.shape(y[1,:]))

for i in range(0, 1024):
    df = (None, None, time[0], y[i,:], '', '', '', '')
    plotWidget.addPlot(df)


#dtv = (None, None, time, y[0], '', '', '', '')
#
# imv = pg.image(y)
# ## Display the data and assign each frame a time value from 1.0 to 3.0
# imv.setImage(y)
#
# ## Set a custom color map
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

# for data_feature in data_features:
#     df = data_feature
#
#     y = data_feature[3]
#     print(np.shape(y))
#     coordinate_of_time = data_feature[8]
#     print(coordinate_of_time)
    #plotWidget.addPlot(data_feature)
    #plotWidget.addPlotAt(0, 0, data_feature)

plotWidget.show()

app.exec() # Keep the application running