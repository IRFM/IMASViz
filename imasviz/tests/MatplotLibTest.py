import wx

import numpy
import matplotlib

from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
import numpy as np
import matplotlib.pyplot as plt

class MplFrame(wx.Frame):
    def __init__(self,parent,title):
        wx.Frame.__init__(self,parent,title=title,size=(800,800))

        self.fig = plt.figure()
        # ax1 = self.fig.add_axes([0.1, 0.1, 0.4, 0.7])
        # ax2 = self.fig.add_axes([0.55, 0.1, 0.4, 0.7])
        #
        x = np.arange(0.0, 2.0, 0.02)
        y = np.sin(2 * np.pi * x)
        # y2 = np.exp(-x)
        # # l1, l2 = ax1.plot(x, y1, 'rs-', x, y2, 'go')
        # l1 = ax1.plot(x, y, 'rs-')
        #
        # y3 = np.sin(4 * np.pi * x)
        # y4 = np.exp(-2 * x)
        # # l3, l4 = ax2.plot(x, y3, 'yd-', x, y4, 'k^')
        # l3 = ax2.plot(x, y3, 'yd-')
        #
        # self.fig.legend((l1), ('Line 1'), 'upper left')
        # self.fig.legend((l3), ('Line 3'), 'upper right')

        f, axarr = plt.subplots(2, sharex=True)
        axarr[0].plot(x, y)
        axarr[0].set_title('Sharing X axis')
        axarr[1].scatter(x, y)
        f.subplots_adjust(hspace=0.1)
        self.canvas = FigureCanvas(self, -1, f)

if __name__ == "__main__":
    app=wx.PySimpleApp()
    frame=MplFrame(None,"Hello Matplotlib !")
    frame.Show()
    app.MainLoop()