from imasviz.VizPlugins.VizPlugins import VizPlugins
import traceback

class TFOverviewPlugin(VizPlugins):
    def __init__(self):
        VizPlugins.__init__(self)

    def execute(self, app, pluginsConfig):
        try:
            print ('TFOverviewPlugin to be executed...')
            app.MainLoop()

        except :
            traceback.print_exc()
            self.view.log.error(traceback.format_exc())

    # def getSubjects(self):
    #     subjects = {'overview':'TF overview...', 'tf':'TF overview...'}
    #     return subjects

    def getEntriesPerSubject(self):
        return {'overview':[0,1], 'tf_overview':[2]}

    def getAllEntries(self):
        return [(0, 'TF overview...'), #(config number, description)
                   (0, 'TF overview2...'),
                   (0, 'TF specific...')]
