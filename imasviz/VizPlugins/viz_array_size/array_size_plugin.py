from imasviz.VizPlugins.VizPlugins import VizPlugins
import traceback

class ArraySizePlugin(VizPlugins):
    def __init__(self):
        VizPlugins.__init__(self)

    def execute(self, dictDataSource, dataTreeView):
        try:
            print ('ArraySizePlugin to be executed...')
            #pluginsConfig = self.getPluginsConfiguration('ArraySizePlugin')
            size_request = dictDataSource['size_request']
            if size_request != None and size_request == 1:
                view = dictDataSource['imasviz_view']
                node_attributes = dictDataSource['node_attributes']
                ids = view.dataSource.ids[0]
                size = len(eval('ids.' + node_attributes.get('dataName')))
                view.log.info('Size of ' + str(node_attributes.get('dataName')) + " = " + str(size) )

            #app.MainLoop()
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