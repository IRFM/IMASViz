from imasviz.VizPlugins.VizPlugins import VizPlugins
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal import QVizPlotSignal
import traceback, logging, os

class CompareFLT1DPlugin(VizPlugins):
    def __init__(self):
        VizPlugins.__init__(self)

    def execute(self, vizAPI):

        try:
            print('CompareFLT1DPlugin to be executed...')
            figureKey, plotWidget = vizAPI.CreatePlotWidget()
            node = self.selectedTreeNode
            QVizPlotSignal(dataTreeView=self.dataTreeView,
                           label=None,
                           title=None,
                           nodeData=node.getNodeData(),
                           figureKey=figureKey,
                           update=0).execute(plotWidget)
            plotWidget.show()
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
