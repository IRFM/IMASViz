import wx
import wx.lib.scrolledpanel

class ShowNodeDocumentation(wx.Frame):
    """Routine for displaying popup frame containing node description
    """
    def __init__(self, documentation, pos_x=500, pos_y=550, size_x=800,
                 size_y=100):
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

    def SetAndShow(parent_WxDataTreeView, documentation):

        """Get size and position of WxTreeView window/frame to be used
           for positioning the node documentation frame
        """

        """ - Get position"""
        px, py = parent_WxDataTreeView.GetPosition()
        """ - Get size"""
        sx, sy = parent_WxDataTreeView.GetSize()

        """ - Modify the position and size for more appealing look of the
              node documentation panel
        """
        px_ndoc = px
        py_ndoc = py+sy
        sx_ndoc = sx
        sy_ndoc = 175

        """New frame for displaying node documentation with the use of
           ShowNodeDocumentation.py.
        """
        """ - Set the frame and statictext IDs"""
        frame_node_doc_id = 10012
        """ - Note: The statictext IDs must must match to the ones in
              ShowNodeDocumentation.create function!
        """
        stext_node_label_id = 10002
        stext_node_doc_id = 10004

        """ - Find node documentation frame by ID"""
        frame_node_doc = wx.FindWindowById(frame_node_doc_id)

        """Updating node documentation """
        if (wx.FindWindowById(stext_node_doc_id) != None):
            """ - If the frame window (documentation static text ID)
                  already exists, then update only the required static text
                  (SetLabel), displaying the node label and documentation
            """
            """ - Find node label static text by ID"""
            stext_node_label = wx.FindWindowById(stext_node_label_id)
            """ - Update node label static text"""
            stext_node_label.SetLabel(documentation[1])
            """ - Find node documentation static text by ID"""
            stext_node_doc = wx.FindWindowById(stext_node_doc_id)
            """ - Update node documentation static text"""
            stext_node_doc.SetLabel(documentation[3])
            stext_node_doc.Wrap(sx_ndoc*0.90)

            """ - Update the node documentation frame position in
                  correlation to Browser_API position and size changes. Only
                  if the menu selection "Fix panel location" is disabled
            """
            fix_loc_checkitem_id = 10005
            fix_loc_checkitem_value = frame_node_doc.GetMenuBar(). \
                FindItemById(fix_loc_checkitem_id).IsChecked()
            if (fix_loc_checkitem_value != True):
                """ - Update position"""
                frame_node_doc.SetPosition((px_ndoc, py_ndoc))
                """ - Update size"""
                frame_node_doc.SetSize((sx_ndoc, sy_ndoc))
        else:
            """ - Else, if the frame window (static text ID) doesn't,
                  exists create new one"""
            frame_node_doc = \
                ShowNodeDocumentation(
                    documentation = documentation,
                    pos_x=px_ndoc, pos_y=py_ndoc,
                    size_x=sx_ndoc, size_y=sy_ndoc)
            frame_node_doc.SetId(frame_node_doc_id)
            frame_node_doc.Show()

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
