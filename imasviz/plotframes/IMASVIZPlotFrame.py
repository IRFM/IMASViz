from wxmplot import PlotFrame
import wx
from imasviz.plotframes.IMASVIZPlotPanel import IMASVIZPlotPanel, \
                                                IMASVIZ_PreviewPlotPanel
from imasviz.util.GlobalValues import GlobalIDs
import matplotlib.pyplot as plt

class IMASVIZPlotFrame(PlotFrame):
    def __init__(self, parent=None, size=None, facecolor=None, title=None,
                 signalHandling=None, **kws):
        if title is None:
            title = '2D Plot Frame'
        self.facecolor = facecolor
        self.signalHandling = signalHandling

        PlotFrame.__init__(self, parent=parent, title=title, size=size,
                           axisbg=facecolor, **kws)

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
                               facecolor=self.facecolor,
                               output_title=self.output_title,
                               signalHandling=self.signalHandling)
        self.panel.messenger = self.write_message
        sizer.Add(self.panel, 1, wx.EXPAND)
        self.BuildMenu()

        self.SetAutoLayout(True)
        self.SetSizer(sizer)
        self.Fit()

class IMASVIZ_PreviewPlotFrame(PlotFrame):
    """Light version of IMASVIZPlotFrame class, used for simple plots
       (for plot preview etc.)
    """
    def __init__(self, parent=None, size=None, facecolor=None, title=None,
                 signalHandling=None, **kws):
        if title is None:
            title = 'Plot Frame'
        self.facecolor = facecolor
        self.signalHandling = signalHandling

        PlotFrame.__init__(self, parent=parent, title=title, size=size,
                           axisbg=facecolor, **kws)

    def BuildFrame(self):
        # Python3 note: wxPython has no THICK_FRAME
        sbar = self.CreateStatusBar(2, wx.CAPTION)
        sfont = sbar.GetFont()
        sfont.SetWeight(wx.BOLD)
        sfont.SetPointSize(6)
        sbar.SetFont(sfont)

        self.SetStatusWidths([-3,-1])
        self.SetStatusText('',0)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.panel = IMASVIZ_PreviewPlotPanel(self, size=self.size,
                               facecolor=self.facecolor,
                               output_title=self.output_title,
                               signalHandling=self.signalHandling)
        self.panel.messenger = self.write_message

        self.createMenu()

        sizer.Add(self.panel, 1, wx.EXPAND)

        self.SetAutoLayout(True)
        self.SetSizer(sizer)
        self.Fit()

    def createMenu(self):
        """Configure the menu bar.
        """
        menubar = wx.MenuBar()

        """Set new menubar item to be added to 'Options' menu"""
        menu = wx.Menu()

        """Add option to fix the position of the preview plot"""
        """ - Set checkout item"""
        item_pp_2 = menu.AppendCheckItem(
                    id=GlobalIDs.ID_MENU_ITEM_PREVIEW_PLOT_FIX_POSITION,
                    item='Fix position', help="Fix position of the preview plot")

        """Add and set 'Options' menu """
        menubar.Append(menu, 'Options')

        self.SetMenuBar(menubar)
