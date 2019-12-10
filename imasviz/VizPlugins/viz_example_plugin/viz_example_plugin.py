from imasviz.VizPlugins.VizPlugin import VizPlugin

from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSelectedSignals import QVizPlotSelectedSignals

import traceback
import logging
import os
import sys


class viz_example_plugin(VizPlugin):  # The plugin should inherit from VizPlugin
    def __init__(self, *args, **kwargs):
        VizPlugin.__init__(self, *args, **kwargs)

    def execute(self, vizAPI, pluginEntry):

        try:
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
                         coordinateValues(coordinateNumber=1, dataTreeView=self.dataTreeView)))
            logging.info('Time dependent? ' + str(self.selectedTreeNode.
                                                  isCoordinateTimeDependent(coordinateNumber=1)))
            logging.info('Embedded in a dynamic AOS? ' + str(self.selectedTreeNode.
                                                           embedded_in_time_dependent_aos()))
            label, xlabel, ylabel, title = self.selectedTreeNode.plotOptions(self.dataTreeView)
            logging.info('Some attributes used in plots: ')
            logging.info('label: ' + label)
            logging.info('xlabel: ' + xlabel)
            logging.info('ylabel: ' + ylabel)
            #logging.info('coordinate1 (IMAS syntax): ' + self.selectedTreeNode.getCoordinate(coordinateNumber=1))

            figureKey, plotWidget = vizAPI.CreatePlotWidget(dataTreeView=self.dataTreeView)
            QVizPlotSelectedSignals(self.dataTreeView, figureKey).execute(plotWidget)

        except :
            traceback.print_exc()
            logging.error(traceback.format_exc())


    def getEntries(self):
        if self.selectedTreeNode.is1DAndDynamic():
            return [0]
        else:
            return []

    def getAllEntries(self):
        return [(0, 'Example plugin...')]

    def isEnabled(self):
        return QVizGlobalValues.TESTING
