import matplotlib
matplotlib.use('WXAgg')

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx, wxc
from matplotlib.figure import Figure

import wx

class CanvasPanel(wx.Panel):
    def __init__(self, parent, figure):
        wx.Panel.__init__(self, parent)
        #self.figure = Figure()
        #self.axes = figure.add_subplot(111)
        self.canvas = FigureCanvas(self, -1, figure)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.sizer)
        self.Fit()
        self.add_toolbar()

    def add_toolbar(self):
        self.toolbar = NavigationToolbar2Wx(self.canvas)
        self.toolbar.Realize()
        # By adding toolbar in sizer, we are able to put it at the bottom
        # of the frame - so appearance is closer to GTK version.
        self.sizer.Add(self.toolbar, 0, wx.LEFT | wx.EXPAND)
        # update the axes menu on the toolbar
        self.toolbar.update()


#
# if __name__ == "__main__":
#     app = wx.PySimpleApp()
#     fr = wx.Frame(None, title='test')
#     panel = CanvasPanel(fr)
#     panel.draw()
#     fr.Show()
#     app.MainLoop()
