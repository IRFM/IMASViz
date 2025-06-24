# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

from imasviz.VizPlugins.VizPlugin import VizPlugin
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal import QVizPlotSignal
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizUtils import QVizGlobalValues, QVizGlobalOperations
import traceback, logging, os, sys


class CompareFLT1DPlugin(VizPlugin):
    def __init__(self):
        VizPlugin.__init__(self)

    def execute(self, vizAPI, pluginEntry):

        try:
            print('CompareFLT1DPlugin to be executed...')
            logging.getLogger(self.dataTreeView.uri).info('Comparing current node to sibling node from another shot...')
            logging.getLogger(self.dataTreeView.uri).info('Data :' + self.selectedTreeNode.getDataName())

            ok, uri = QVizGlobalOperations.askForShot()
            if not ok:
                return

            dataSource = self.dataTreeView.dataSource

            logging.getLogger(self.dataTreeView.uri).info('Plotting data from current node...')
            figureKey, plotWidget = vizAPI.CreatePlotWidget(dataTreeView=self.dataTreeView, plotAxis="DEFAULT")
            ps = QVizPlotSignal(dataTreeView=self.dataTreeView,
                                vizTreeNode=self.selectedTreeNode,
                                plotWidget=plotWidget)

            # Plot data signal passing plotWidget which is a QWidget referencing a pg.PlotWidget(GraphicsView)
            ps.execute(update=0)

            # Set data source retriever/factory
            dataSourceFactory = QVizDataSourceFactory()

            # Load IMAS database
            dataSource = dataSourceFactory.create(
                uri=uri)

            logging.getLogger(self.dataTreeView.uri).info('Creating datasource:' + dataSource.getLongLabel())

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

        except:
            traceback.print_exc()
            logging.getLogger(self.dataTreeView.dataSource.uri).error(traceback.format_exc())

    def getEntries(self):
        if self.selectedTreeNode.is1DAndDynamic():
            return [0]
        else:
            return []

    def getAllEntries(self):
        return [(0, 'Compare to shot...')]

    def getDescription(self):
        """ Return plugin description.
        """

        return "Test plugin to compare two FLT_1D signals."

    def isEnabled(self):
        return True
