# Built-in
import traceback
import threading
import sys
from PyQt5.QtWidgets import QApplication

# Common
import matplotlib.pyplot as plt
#plt.switch_backend('Qt5Agg')

# IMAS
from imasviz.VizPlugins.VizPlugins import VizPlugins

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
            node_attributes = pluginsConfig.get('node_extra_attributes')
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
        #fr = wx.Frame(None, title='ToFu', size=(800,800))
        fr = None
        #panel = CanvasPanel(fr, figure)
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

class Frame():
    def __init__(self, out):
        #wx.Frame.__init__(self, None, title='tofu', pos=(150, 150), size=(800, 600))

        #self.panel = wx.Panel(self)

        #self.axes = self.figure.add_subplot(111)
        #self.canvas = FigureCanvas(self.panel, wx.ID_ANY, self.figure)

        self.KH = out.plot(fs=(10, 5))[1]
        self.figure = self.KH.dax['t'][0].figure
        self.axes = [[self.KH.dax[kk][ii] for ii in range(len(self.KH.dax[kk]))] for kk in self.KH.dax.keys()]
        #self.panel = CanvasPanel(self, self.figure)
        # rects = self.axes.bar(range(10), 20 * np.random.rand(10))
        # self.drs = []
        # for rect in rects:
        #     dr = DraggableRectangle(rect)
        #     dr.connect()
        #     self.drs.append(dr)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    #out = tfi.Bolo.load_geom(draw=False)
    #figure = out[1][0].get_figure()
    out = tfi.Bolo.load_data(52699, draw=False, plot=False)
    fr = Frame(out)
    #panel = CanvasPanel(fr, figure)
    fr.Show()

    app.MainLoop()
