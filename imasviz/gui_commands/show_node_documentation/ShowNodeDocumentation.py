import wx
from imasviz.plotframes.IMASVIZPlotPanel import IMASVIZPlotPanel

class ShowNodeDocumentation(wx.Frame):
    """Routine for displaying popup frame containing node description
    """
    """TODO: Delete previousl created frames"""
    # def __init__(self, parent, ID, title, pos, size, name, documentation):
    def __init__(self, documentation, pos_x=500, pos_y=550, size_x=800, size_y=100):
        wx.Frame.__init__(self, None, 1001,
                          title = "Documentation",
                          pos=(pos_x, pos_y),
                          size=(size_x, size_y),
                          name = "Frame-Documentation")
        self.create(documentation)

    def create(self, documentation):
        self.panel = wx.Panel(self, -1)
        # self.panel.SetBackgroundColour("white")
        self.panel.SetBackgroundColour((204, 229, 255))
        self.t = wx.StaticText(self.panel, 10001, documentation)


