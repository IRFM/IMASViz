from imasviz.plugins.VIZPlugins import VIZPlugins
import traceback

class ArraySizePlugin(VIZPlugins):
    def __init__(self):
        VIZPlugins.__init__(self)

    def execute(self, app, pluginsConfig):
        try:
            print ('ArraySizePlugin to be executed...')
            size_request = pluginsConfig.get('size_request')
            if size_request != None and size_request == 1:
                view = pluginsConfig.get('imasviz_view')
                node_attributes = pluginsConfig.get('node_attributes')
                ids = view.dataSource.ids
                size = len(eval(node_attributes.get('dataName')))
                view.log.info('Size of ' + str(node_attributes.get('dataName')) + " = " + str(size) )

            app.MainLoop()
        except :
            traceback.print_exc()
            view.log.error(traceback.format_exc())


    # def getSubjects(self):
    #     subjects = {'overview':'ArraySize overview...', 'arraysize':'ArraySize overview...'}
    #     return subjects

    def getEntriesPerSubject(self):
        return {'overview':[0,1], 'tf_overview':[2], 'signal':[3]}

    def getAllEntries(self):
        return [(0, 'ArraySize overview...'), #(config number, description)
                   (0, 'ArraySize overview2...'),
                   (0, 'ArraySize specific...'),
                (1, 'Array size...')]

    #def execute(self, app, pluginsConfig):
    #    print ('ArraySize overview to be executed...')
    #   app.MainLoop()