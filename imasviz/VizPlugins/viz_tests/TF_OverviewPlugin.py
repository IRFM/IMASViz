from imasviz.VizPlugins.VizPlugins import VizPlugins
import traceback, logging, os

class TFOverviewPlugin(VizPlugins):
    def __init__(self):
        VizPlugins.__init__(self)

    def execute(self, vizAPI):

        #view = pluginsConfiguration.get('imasviz_view')
        #node_attributes = pluginsConfiguration.get('node_attributes')

        try:
            print ('TF plugin to be executed...')
            print(self.selectedTreeNode)

            #figure.show()
        except :
            traceback.print_exc()
            logging.error(traceback.format_exc())


    def getEntriesPerSubject(self):
        return {'FLT_1D':[0], 'FLT_2D':[1]}

    def getAllEntries(self):
        return [(0, 'FLT_1D plugin...'), #(config number, description)
                   (1, 'FLT_2D plugin...')]

    def getPluginsConfiguration(self):
        return [{}, {}]

    def isEnabled(self):
        return True
