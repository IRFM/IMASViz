# Built-in
import traceback
import threading

# Common
import matplotlib.pyplot as plt
plt.switch_backend('Qt5Agg')

# IMAS
from imasviz.plugins.VIZPlugins import VIZPlugins

# tofu
import tofu_irfm as tfi


class ToFuPlugin(VIZPlugins):
    def __init__(self):
        VIZPlugins.__init__(self)
        
        class thread(threading.Thread):

            def set(self, view, nattr):
                self.view = view
                self.nattr = nattr

            def run(self):
                if self.nattr.get('IDSName')=='bolometer':
                    if self.view.get('geom'):
                        tfi.Bolo.load_geom()
                    elif self.view.get('data'):
                        tfi.Bolo.load_data(view.dataSource.shotNumber)
                elif self.nattr.get('IDSName')=='interferometer':
                    if self.view.get('geom'):
                        tfi.Interfero.load_geom()
                    elif self.view.get('data'):
                        tfi.Interfero.load_data(view.dataSource.shotNumber)
                elif self.nattr.get('IDSName')=='soft_x_rays':
                    if self.view.get('geom'):
                        tfi.SXR.load_geom()
                    elif self.view.get('data'):
                        tfi.SXR.load_data(view.dataSource.shotNumber)
        self.thread = thread()    

    def execute(self, app, pluginsConfig):
        try:
            print ('ToFuPlugin to be executed...')
            size_request = pluginsConfig.get('size_request')
            #if size_request != None and size_request == 1:
            view = pluginsConfig.get('imasviz_view')
            node_attributes = pluginsConfig.get('node_attributes')
            #ids = view.dataSource.ids
            #size = len(eval(node_attributes.get('dataName')))
            #view.log.info('Size of ' + str(node_attributes.get('dataName')) + " = " + str(size) )
            #self.thread.set(pluginsConfig, node_attributes)
            #self.thread.start()
            if node_attributes.get('IDSName')=='bolometer':
                if pluginsConfig.get('geom'):
                    tfi.Bolo.load_geom()
                elif pluginsConfig.get('data'):
                    tfi.Bolo.load_data(view.dataSource.shotNumber)
            elif node_attributes.get('IDSName')=='interferometer':
                if pluginsConfig.get('geom'):
                    tfi.Interfero.load_geom()
                elif pluginsConfig.get('data'):
                    tfi.Interfero.load_data(view.dataSource.shotNumber)
            elif node_attributes.get('IDSName')=='soft_x_rays':
                if pluginsConfig.get('geom'):
                    tfi.SXR.load_geom()
                elif pluginsConfig.get('data'):
                    tfi.SXR.load_data(view.dataSource.shotNumber)
            app.MainLoop()
        except :
            traceback.print_exc()
            view.log.error(traceback.format_exc())

    def getEntriesPerSubject(self):
        a = {'interferometer_overview':[0,1],
             'bolometer_overview':[2,3],
             'soft_x_rays_overview':[4,5]}
        return a

    def getAllEntries(self):
        #(config number, description)
        return [(0, 'tofu - geom...'), (1, 'tofu - data'), 
                (2, 'tofu - geom...'), (3, 'tofu - data'),
                (4, 'tofu - geom...'), (5, 'tofu - data')]
