from imasviz.plugins.VIZPlugins import VIZPlugins
import traceback

class ECEOverviewPlugin(VIZPlugins):
    def __init__(self):
        VIZPlugins.__init__(self)

    def execute(self, app, pluginsConfig):
        print 'ECE overview to be executed with config -->'
        print pluginsConfig
        print pluginsConfig['imasviz_view']
        app.MainLoop()

    def getEntriesPerSubject(self):
        return {'overview':[0], 'ece_overview':[0]}

    def getAllEntries(self):
        # return [(0, 'ECE overview...'), #(config number, description)
        #            (1, 'ECE overview2...'),
        #            (0, 'ECE specific...')]
        return [(0, 'ECE overview...')]
