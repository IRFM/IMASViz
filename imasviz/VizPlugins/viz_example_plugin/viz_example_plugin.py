from imasviz.VizPlugins.VizPlugin import VizPlugin

from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSelectedSignals import QVizPlotSelectedSignals

import traceback
import logging
import os
import sys
import numpy as np
import pyqtgraph as pg


class viz_example_plugin(VizPlugin):  # The plugin should inherit from VizPlugin
    def __init__(self, *args, **kwargs):
        VizPlugin.__init__(self, *args, **kwargs)

    def execute(self, vizAPI, pluginEntry):

        try:
            if pluginEntry == 0:
                self.firstEntry(vizAPI)
            elif pluginEntry == 1:
                self.secondEntry(vizAPI)

        except :
            traceback.print_exc()
            logging.error(traceback.format_exc())

    def firstEntry(self, vizAPI):
        logging.info('viz_example_plugin to be executed...')
        logging.info('Documentation: ' + self.selectedTreeNode.getDocumentation())
        logging.info('Is IDS root? ' + str(self.selectedTreeNode.isIDSRoot()))
        logging.info('Data available? ' + str(self.selectedTreeNode.hasAvailableData()))
        logging.info('Data type: ' + self.selectedTreeNode.getDataType())
        logging.info('Is 1D and dynamic? ' + str(self.selectedTreeNode.is1DAndDynamic()))
        logging.info('Has homogeneous time? ' + str(self.selectedTreeNode.hasHomogeneousTime()))
        logging.info('Python data path: ' + self.selectedTreeNode.getDataName())
        logging.info('IMAS data path: ' + self.selectedTreeNode.getPath())
        logging.info('Parametrized path.: ' + self.selectedTreeNode.getParametrizedDataPath())
        logging.info('Parametrized coordinate1: ' + self.selectedTreeNode.getParametrizedCoordinate(coordinateNumber=1))
        logging.info('Coordinate1 (evaluated): ' + str(self.selectedTreeNode.
                                                       coordinateValues(coordinateNumber=1,
                                                                        dataTreeView=self.dataTreeView)))
        logging.info('Time dependent? ' + str(self.selectedTreeNode.
                                              isCoordinateTimeDependent(coordinateNumber=1)))
        logging.info('Embedded in a dynamic AOS? ' + str(self.selectedTreeNode.
                                                         embedded_in_time_dependent_aos()))
        label, xlabel, ylabel, title = self.selectedTreeNode.plotOptions(self.dataTreeView)
        logging.info('Some attributes used in plots: ')
        logging.info('label: ' + label)
        logging.info('xlabel: ' + xlabel)
        logging.info('ylabel: ' + ylabel)
        # logging.info('coordinate1 (IMAS syntax): ' + self.selectedTreeNode.getCoordinate(coordinateNumber=1))

        figureKey, plotWidget = vizAPI.CreatePlotWidget(dataTreeView=self.dataTreeView)
        QVizPlotSelectedSignals(self.dataTreeView, figureKey).execute(plotWidget)

    def secondEntry(self, vizAPI):
        ## Create random 3D data set with noisy signals
        img = pg.gaussianFilter(np.random.normal(size=(200, 200)), (5, 5)) * 20 + 100
        img = img[np.newaxis, :, :]
        decay = np.exp(-np.linspace(0, 0.3, 100))[:, np.newaxis, np.newaxis]
        data = np.random.normal(size=(100, 200, 200))
        data += img * decay
        data += 2

        ## Add time-varying signal
        sig = np.zeros(data.shape[0])
        sig[30:] += np.exp(-np.linspace(1, 10, 70))
        sig[40:] += np.exp(-np.linspace(1, 10, 60))
        sig[70:] += np.exp(-np.linspace(1, 10, 30))

        sig = sig[:, np.newaxis, np.newaxis] * 3
        data[:, 50:60, 30:40] += sig
        imv = pg.image(data)
        ## Display the data and assign each frame a time value from 1.0 to 3.0
        imv.setImage(data, xvals=np.linspace(1., 3., data.shape[0]))

        ## Set a custom color map
        colors = [
            (0, 0, 0),
            (45, 5, 61),
            (84, 42, 55),
            (150, 87, 60),
            (208, 171, 141),
            (255, 255, 255)
        ]
        cmap = pg.ColorMap(pos=np.linspace(0.0, 1.0, 6), color=colors)
        imv.setColorMap(cmap)

    def thirdEntry(self, vizAPI):
        def secondEntry(self, vizAPI):
            ## Create random 3D data set with noisy signals
            img = pg.gaussianFilter(np.random.normal(size=(200, 200)), (5, 5)) * 20 + 100
            img = img[np.newaxis, :, :]
            decay = np.exp(-np.linspace(0, 0.3, 100))[:, np.newaxis, np.newaxis]
            data = np.random.normal(size=(100, 200, 200))
            data += img * decay
            data += 2

            ## Add time-varying signal
            sig = np.zeros(data.shape[0])
            sig[30:] += np.exp(-np.linspace(1, 10, 70))
            sig[40:] += np.exp(-np.linspace(1, 10, 60))
            sig[70:] += np.exp(-np.linspace(1, 10, 30))

            sig = sig[:, np.newaxis, np.newaxis] * 3
            data[:, 50:60, 30:40] += sig
            imv = pg.image(data)
            ## Display the data and assign each frame a time value from 1.0 to 3.0
            imv.setImage(data, xvals=np.linspace(1., 3., data.shape[0]))

            ## Set a custom color map
            colors = [
                (0, 0, 0),
                (45, 5, 61),
                (84, 42, 55),
                (150, 87, 60),
                (208, 171, 141),
                (255, 255, 255)
            ]
            cmap = pg.ColorMap(pos=np.linspace(0.0, 1.0, 6), color=colors)
            imv.setColorMap(cmap)

    def getEntries(self):
        if self.selectedTreeNode.is1DAndDynamic():
            return [0]
        # elif self.selectedTreeNode.is2DAndDynamic():
        #     return [1]
        else:
            return []

    def getAllEntries(self):
        return [(0, 'Example plugin...'), (1, '2D plugin...')]

    def isEnabled(self):
        return True
