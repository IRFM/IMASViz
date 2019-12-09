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

            logging.info('Data: ' + self.selectedTreeNode.getDataName())
            logging.info('Data param.: ' + self.selectedTreeNode.getParametrizedDataPath())
            logging.info('coordinate1 (python syntax): ' + self.selectedTreeNode.getParametrizedCoordinate(coordinateNumber=1))
            logging.info('coordinate1 (IMAS syntax): ' + self.selectedTreeNode.getCoordinate(coordinateNumber=1))

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
