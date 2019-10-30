from imasviz.VizPlugins.VizPlugins import VizPlugins
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal import QVizPlotSignal
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
import traceback, logging, os, sys
import numpy as np
from PyQt5.QtWidgets import QInputDialog, QLineEdit

class CompareFLT1DPlugin(VizPlugins):
    def __init__(self):
        VizPlugins.__init__(self)

    def execute(self, vizAPI):

        try:
            print('CompareFLT1DPlugin to be executed...')
            logging.info('Comparing current node to sibling node from another shot...')
            logging.info('Data :' + self.selectedTreeNode.getDataName())

            ok, shotNumber, runNumber, userName, tokamak = QVizGlobalOperations.askForShot()
            if not ok:
                return

            dataSource = self.dataTreeView.dataSource

            logging.info('Plotting data from current node...')
            figureKey, plotWidget = vizAPI.CreatePlotWidget()
            node = self.selectedTreeNode
            ps = QVizPlotSignal(dataTreeView=self.dataTreeView,
                           label=None,
                           title=None,
                           nodeData=node.getNodeData(),
                           update=0)

            ps.execute(plotWidget)

            # Set data source retriever/factory
            dataSourceFactory = QVizDataSourceFactory()


            # Load IMAS database
            dataSource = dataSourceFactory.create(
                dataSourceName=QVizGlobalValues.IMAS_NATIVE,
                shotNumber=shotNumber,
                runNumber=runNumber,
                userName=userName,
                imasDbName=tokamak)

            logging.info('Creating datasource:' + dataSource.getLongLabel())

            # Build the data tree view frame
            f = vizAPI.CreateDataTree(dataSource)

            # Set the list of node paths that are to be selected
            paths = []
            paths.append(QVizGlobalOperations.makeIMASPath(self.selectedTreeNode.getDataName()))

            # Change it to dictionary with paths an occurrences (!)
            paths = {'paths': paths,
                     'occurrences': [self.selectedTreeNode.getOccurrence()]}

            # Select signal nodes corresponding to the paths in paths list
            vizAPI.SelectSignals(f, paths)

            # Plot signal nodes on the same figure
            # Note: Data tree view does not need to be shown in order for this routine to
            #       work
            vizAPI.PlotSelectedSignals(f, figureKey=figureKey, update=1)

        except :
            traceback.print_exc()
            logging.error(traceback.format_exc())


    def getEntriesPerSubject(self):
        return {'FLT_1D':[0]}

    def getAllEntries(self):
        return [(0, 'Compare to shot...')]

    def getPluginsConfiguration(self):
        return [{}]

    def isEnabled(self):
        return True
