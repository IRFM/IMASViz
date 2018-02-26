import wx
from imasviz.plotframes.IMASVIZPlotPanel import IMASVIZPlotPanel

class ShowNodeDocumentation(wx.Frame):
    """Routine for displaying popup frame containing node description
    """
    """TODO: Delete previousl created frames"""
    # def __init__(self, parent, ID, title, pos, size, name, documentation):
    def __init__(self, documentation):
        wx.Frame.__init__(self, None, 1001,
                          title = "Documentation",
                          pos=(500, 550),
                          size=(800, 100),
                          name = "Frame-Documentation")
        self.create(documentation)

    def create(self, documentation):
        self.panel = wx.Panel(self, -1)
        self.panel.SetBackgroundColour("white")
        self.t = wx.StaticText(self.panel, 10001, documentation)


