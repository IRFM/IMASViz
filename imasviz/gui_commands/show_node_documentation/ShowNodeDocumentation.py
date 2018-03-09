import wx
import wx.lib.scrolledpanel

class ShowNodeDocumentation(wx.Frame):
    """Routine for displaying popup frame containing node description
    """
    def __init__(self, documentation, pos_x=500, pos_y=550, size_x=800, size_y=100):
        """Set node documentation frame preferences
        """
        wx.Frame.__init__(self, None, 1001,
                          title="Selected node documentation",
                          pos=(pos_x, pos_y),
                          size=(size_x, size_y),
                          name = "Frame-Documentation")
        """Bind to mouse event handler"""
        # self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouseEvent)
        """Set menu bar"""
        self.SetMenuBar(SetNodeDocMenuBar(parent=self))

        """Set wrap width later to be used for documentation static text"""
        stext_wrap_width = size_x*0.90
        """Create panel"""
        SetNodeDocScrolledPanel(self, documentation, stext_wrap_width)

    # def OnMouseEvent(self, event):
    #     """Mouse event handlers."""
    #     if event.LeftDown():
    #         print(event.Id)

    def OnExit(self, event):
        """Close the panel
        """
        self.Close()

class SetNodeDocScrolledPanel(wx.lib.scrolledpanel.ScrolledPanel):
    """Class for setting node doc panel scroll bar
    """
    def __init__(self, parent, documentation, stext_wrap_width):

        """Set scrolled panel used within node documentation frame"""
        wx.lib.scrolledpanel.ScrolledPanel.__init__(self, parent, -1)

        """Set panel background colour"""
        self.SetBackgroundColour((204, 229, 255))

        """Set new BoxSizer"""
        vbox = wx.BoxSizer(wx.VERTICAL)

        """Set node documentation panel text"""
        t = 18  # Default text size parameter
        """ - String "Node" """
        stext_1 = wx.StaticText(self, 10001, documentation[0])
        """ - Node label"""
        stext_2 = wx.StaticText(self, 10002, documentation[1])
        """ - String "Documentation" """
        stext_3 = wx.StaticText(self, 10003, documentation[2])
        """ - Node documentation"""
        stext_4 = wx.StaticText(self, 10004, documentation[3])
        """ - Set documentation font"""
        font_label = wx.Font(t*0.7, wx.SWISS, wx.NORMAL, wx.BOLD)
        font_text  = wx.Font(t*0.65, wx.SWISS, wx.NORMAL, wx.NORMAL)
        stext_1.SetFont(font_label)
        stext_2.SetFont(font_text)
        stext_3.SetFont(font_label)
        stext_4.SetFont(font_text)
        """ - Set documentation wrapping"""
        # stext_1.Wrap(stext_wrap_width)
        stext_2.Wrap(stext_wrap_width)  # Set node label wrap width
        # stext_3.Wrap(stext_wrap_width)
        stext_4.Wrap(stext_wrap_width)  # Set documentation wrap width

        """Add all static text to BoxSizer"""
        vbox.Add(stext_1, 0, wx.LEFT, 4)
        vbox.Add(stext_2, 0, wx.LEFT, 10)
        vbox.Add(stext_3, 0, wx.LEFT, 4)
        vbox.Add(stext_4, 0, wx.LEFT, 10)
        """Add 'invisible' line to activate scroll bar"""
        """TODO: Set the panel to recognize the required height itself"""
        vbox.Add(wx.StaticLine(self, -1, size=(-1, 256)), 0, wx.ALL, 5)
        """Set sizer"""
        self.SetSizer(vbox)
        """Set scrolling"""
        self.SetupScrolling()

class SetNodeDocMenuBar(wx.MenuBar):
    """Class for setting node doc panel menu bar
    """
    def __init__(self, parent):
        """Set full menu bar
        """

        """Set default menu bar"""
        wx.MenuBar.__init__(self)

        """Set first menu"""
        first_menu = self.SetFirstMenu(parent=parent)
        """Add the first menu to menubar tab 'Menu'"""
        self.Append(first_menu, "Menu")

    def SetFirstMenu(self, parent):
        """Set first menu"""
        menu = wx.Menu()
        """ - Add check item to menu"""
        self.MenuAddCheckItem(menu=menu, parent=parent, id=10005,
                              title="Fix panel location")

        return menu

    def MenuAddCheckItem(self, menu, parent, id, title):
        """Add Check Item to menu
        """
        menu.AppendCheckItem(id, title)
