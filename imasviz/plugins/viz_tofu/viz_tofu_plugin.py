# Built-in
import traceback
import threading
import wx
from imasviz.plugins.viz_tofu.WxFrame import CanvasPanel

# Common
import matplotlib.pyplot as plt
#plt.switch_backend('Qt5Agg')

# IMAS
from imasviz.plugins.VIZPlugins import VIZPlugins

# tofu
import tofu_irfm as tfi


class ToFuPlugin(VIZPlugins):
    def __init__(self):
        VIZPlugins.__init__(self)

    def execute(self, app, pluginsConfig):
        try:
            print ('ToFuPlugin to be executed...')
            plt.ioff()
            view = pluginsConfig.get('imasviz_view')
            node_attributes = pluginsConfig.get('node_attributes')
            figure = None
            if node_attributes.get('IDSName')=='bolometer':
                if pluginsConfig.get('geom'):
                    out = tfi.Bolo.load_geom(draw=False)
                    figure = out[1][0].get_figure()
                elif pluginsConfig.get('data'):
                    tfi.Bolo.load_data(view.dataSource.shotNumber, draw=False, fs=(8,4))
                    figure = plt.gcf()
            elif node_attributes.get('IDSName')=='interferometer':
                if pluginsConfig.get('geom'):
                    out = tfi.Interfero.load_geom(draw=False)
                    figure = out[1][0].get_figure()
                elif pluginsConfig.get('data'):
                    tfi.Interfero.load_data(view.dataSource.shotNumber, draw=False, fs=(8,4))
                    figure = plt.gcf()
            elif node_attributes.get('IDSName')=='soft_x_rays':
                if pluginsConfig.get('geom'):
                    out = tfi.SXR.load_geom(draw=False)
                    figure = out[1][0].get_figure()
                elif pluginsConfig.get('data'):
                    tfi.SXR.load_data(view.dataSource.shotNumber, draw=False, fs=(8,4))
                    figure = plt.gcf()
            self.OpenWxFrame(figure)
            app.MainLoop()
        except :
            traceback.print_exc()
            view.log.error(traceback.format_exc())

    def OpenWxFrame(self, figure):
        fr = wx.Frame(None, title='ToFu', size=(1200,1200))
        panel = CanvasPanel(fr, figure)
        #panel.draw()
        fr.Show()


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

if __name__ == "__main__":
    app = wx.App()
    #out=tfi.Bolo.load_data(52682)
    #print (out[1])
    #figure = out[1][0].get_figure()
    out = tfi.Bolo.load_geom(draw=False)
    #figure = plt.gcf()
    figure = out[1][0].get_figure()
    fr = wx.Frame(None, title='test', size=(1200,1200))
    panel = CanvasPanel(fr, figure)
    #panel.draw()
    fr.Show()
    #plt.show()

    app.MainLoop()
