import wx
from imasviz.plotframes.IMASVIZPlotPanel import IMASVIZPlotPanel

class ShowNodeDocumentation:
    """Routine for displaying popup frame containing node description
    """
    """TODO: Delete previousl created frames"""
    def __init__(self, parent, ID, title, pos, size, name, documentation):

        f = wx.Frame(None, 1001, title = 'Documentation',
                             pos = (500,550), size = (800, 100),
                             name = 'Frame - Documentation ')

        p = wx.Panel(f, -1)
        t = wx.StaticText(p, -1, documentation)
        f.Show()