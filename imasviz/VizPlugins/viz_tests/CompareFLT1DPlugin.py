from imasviz.VizPlugins.VizPlugin import VizPlugin
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal import QVizPlotSignal
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
import traceback, logging, os, sys
import numpy as np
from PyQt5.QtWidgets import QInputDialog, QLineEdit

class CompareFLT1DPlugin(VizPlugin):
    def __init__(self):
        VizPlugin.__init__(self)

    def execute(self, vizAPI, pluginEntry):

        try:
            print('CompareFLT1DPlugin to be executed...')
            logging.info('Comparing current node to sibling node from another shot...')
            logging.info('Data :' + self.selectedTreeNode.getDataName())

            ok, shotNumber, runNumber, userName, database = QVizGlobalOperations.askForShot()
            if not ok:
                return

            dataSource = self.dataTreeView.dataSource

            logging.info('Plotting data from current node...')
            figureKey, plotWidget = vizAPI.CreatePlotWidget(dataTreeView=self.dataTreeView)
            ps = QVizPlotSignal(dataTreeView=self.dataTreeView,
                           vizTreeNode=self.selectedTreeNode)

            #Plot data signal passing plotWidget which is a QWidget referencing a pg.PlotWidget(GraphicsView)
            ps.execute(plotWidget, update=0)

            # Set data source retriever/factory
            dataSourceFactory = QVizDataSourceFactory()

            # Load IMAS database
            dataSource = dataSourceFactory.create(
                dataSourceName=QVizGlobalValues.IMAS_NATIVE,
                shotNumber=shotNumber,
                runNumber=runNumber,
                userName=userName,
                imasDbName=database)

            logging.info('Creating datasource:' + dataSource.getLongLabel())

            # Build the data tree view frame
            f = vizAPI.CreateDataTree(dataSource)

            # Set the list of node paths that are to be selected
            paths = []
            paths.append(QVizGlobalOperations.makeIMASPath(self.selectedTreeNode.getDataName()))

            # Change it to dictionary with paths and occurrences (!)
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


    def getEntries(self):
        if self.selectedTreeNode.is1DAndDynamic():
            return [0]
        else:
            return []

    def getAllEntries(self):
        return [(0, 'Compare to shot...')]

    def isEnabled(self):
        return True
