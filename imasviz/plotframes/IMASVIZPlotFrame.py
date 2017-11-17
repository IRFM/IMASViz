from wxmplot import PlotFrame
import wx
from imasviz.plotframes.IMASVIZPlotPanel import IMASVIZPlotPanel
import matplotlib.pyplot as plt

class IMASVIZPlotFrame(PlotFrame):
    def __init__(self, parent=None, size=None, axisbg=None, title=None, signalHandling=None, **kws):
        if title is None:
            title = '2D Plot Frame'
        self.axisbg = axisbg
        self.signalHandling = signalHandling

        PlotFrame.__init__(self, parent=parent, title=title, size=size,
                           axisbg=axisbg, **kws)

    def BuildFrame(self):
        # Python3 note: wxPython has no THICK_FRAME
        sbar = self.CreateStatusBar(2, wx.CAPTION)
        sfont = sbar.GetFont()
        sfont.SetWeight(wx.BOLD)
        sfont.SetPointSize(10)
        sbar.SetFont(sfont)

        self.SetStatusWidths([-3,-1])
        self.SetStatusText('',0)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.panel = IMASVIZPlotPanel(self, size=self.size,
                               axisbg=self.axisbg,
                               output_title=self.output_title,
                               signalHandling=self.signalHandling)
        self.panel.messenger = self.write_message
        sizer.Add(self.panel, 1, wx.EXPAND)
        self.BuildMenu()

        self.SetAutoLayout(True)
        self.SetSizer(sizer)
        self.Fit()
