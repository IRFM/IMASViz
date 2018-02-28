import wx
from imasviz.plotframes.IMASVIZPlotPanel import IMASVIZPlotPanel

class ShowNodeDocumentation(wx.Frame):
    """Routine for displaying popup frame containing node description
    """
    """TODO: Delete previousl created frames"""
    # def __init__(self, parent, ID, title, pos, size, name, documentation):
    def __init__(self, documentation, pos_x=500, pos_y=550, size_x=800, size_y=100):
        """Set node documentation frame preferences
        """
        wx.Frame.__init__(self, None, 1001,
                          title="Selected node documentation",
                          pos=(pos_x, pos_y),
                          size=(size_x, size_y),
                          name = "Frame-Documentation")

        """Set wrap width later to be used for documentation static text"""
        stext_wrap_width = size_x*0.95
        """Create panel"""
        self.create(documentation, stext_wrap_width)

    def create(self, documentation, stext_wrap_width):
        """Routine for creation of the panel from existing frame
        """
        self.panel = wx.Panel(self, -1)
        """Set panel background colour"""
        self.panel.SetBackgroundColour((204, 229, 255))

        """Set documentation as static text"""
        t = 18
        self.stext_1 = wx.StaticText(self.panel, 10001, documentation[0], pos=(4,0))
        self.stext_2 = wx.StaticText(self.panel, 10002, documentation[1], pos=(10,t*1))
        self.stext_3 = wx.StaticText(self.panel, 10003, documentation[2], pos=(4,t*2))
        self.stext_4 = wx.StaticText(self.panel, 10004, documentation[3], pos=(10,t*3))
        """Set documentation font"""
        font_label = wx.Font(t*0.7, wx.SWISS, wx.NORMAL, wx.BOLD)
        font_text  = wx.Font(t*0.65, wx.SWISS, wx.NORMAL, wx.NORMAL)
        self.stext_1.SetFont(font_label)
        self.stext_2.SetFont(font_text)
        self.stext_3.SetFont(font_label)
        self.stext_4.SetFont(font_text)

        """Set documentation wrapping"""
        # self.stext_1.Wrap(stext_wrap_width)
        # self.stext_2.Wrap(stext_wrap_width)
        # self.stext_3.Wrap(stext_wrap_width)
        self.stext_4.Wrap(stext_wrap_width)


