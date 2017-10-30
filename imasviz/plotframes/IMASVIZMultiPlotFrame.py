from wxmplot import PlotFrame
from wxmplot import MultiPlotFrame
import wx
from wxmplot.utils import MenuItem, Closure
from wxmplot.plotpanel import PlotPanel
from imasviz.gui_commands.plots_configuration.SavePlotsConfiguration import SavePlotsConfiguration

class IMASVIZMultiPlotFrame(MultiPlotFrame):
    def __init__(self, view, parent=None, rows=1, cols=1, framesize=None,
                 panelsize=(400, 320), panelopts=None, **kws):
        self.view = view
        self.help_msg = """Quick help:

         Left-Click:   to display X,Y coordinates
         Left-Drag:    to zoom in on plot region
         Right-Click:  display popup menu with choices:
                        Zoom out 1 level
                        Zoom all the way out
                        --------------------
                        Configure
                        Save Image

        Also, these key bindings can be used
        (For Mac OSX, replace 'Ctrl' with 'Apple'):

          Ctrl-S:     save plot image to file
          Ctrl-C:     copy plot image to clipboard
          Ctrl-K:     Configure Plot

        """
        MultiPlotFrame.__init__(self, parent, rows, cols, framesize,
                 panelsize, panelopts, **kws)


    def BuildFrame(self):

        sbar = self.CreateStatusBar(2, wx.CAPTION)
        sfont = sbar.GetFont()
        sfont.SetWeight(wx.BOLD)
        sfont.SetPointSize(10)
        sbar.SetFont(sfont)


        sizer = wx.GridBagSizer(3, 3)

        for i in range(self.rows):
            for j in range(self.cols):
                self.panels[(i,j)] = PlotPanel(self, size=self.panelsize)
                # **self.panelopts)
                self.panels[(i,j)].messenger = self.write_message
                panel = self.panels[(i,j)]

                sizer.Add(panel,(i,j),(1,1),flag=wx.EXPAND|wx.ALIGN_CENTER)
                panel.report_leftdown = Closure(self.report_leftdown,
                                               panelkey=(i,j))

        self.panel = self.panels[(0,0)]
        for i in range(self.rows):
            sizer.AddGrowableRow(i)
        for i in range(self.cols):
            sizer.AddGrowableCol(i)


        self.BuildMenu()
        self.SetStatusWidths([-3, -1])
        self.SetStatusText('',0)
        self.SetSize(self.framesize)
        self.SetAutoLayout(True)
        self.SetSizerAndFit(sizer)

    def BuildMenu(self):
        mfile = self.Build_FileMenu()
        mopts = wx.Menu()
        MenuItem(self, mopts, "Configure Plot\tCtrl+K",
                 "Configure Plot styles, colors, labels, etc",
                 self.on_configure)
        MenuItem(self, mopts, "Toggle Legend\tCtrl+L",
                 "Toggle Legend Display",
                 self.on_toggle_legend)
        MenuItem(self, mopts, "Toggle Grid\tCtrl+G",
                 "Toggle Grid Display",
                 self.on_toggle_grid)

        mopts.AppendSeparator()
        MenuItem(self, mopts, "Zoom Out\tCtrl+Z",
                 "Zoom out to full data range",
                 self.on_unzoom)

        mscripts = wx.Menu()
        MenuItem(self, mopts, "Save plots configuration\tCtrl+S",
                 "Save this plots configuration for applying on other shots",
                 self.save_configuration)

        mhelp = wx.Menu()
        MenuItem(self, mhelp, "Quick Reference",
                 "Quick Reference for WXMPlot", self.onHelp)
        MenuItem(self, mhelp, "About", "About WXMPlot", self.onAbout)

        mbar = wx.MenuBar()
        mbar.Append(mfile, 'File')
        mbar.Append(mopts, '&Options')
        if self.user_menus is not None:
            for title, menu in self.user_menus:
                mbar.Append(menu, title)

        mbar.Append(mhelp, '&Help')

        self.SetMenuBar(mbar)
        self.Bind(wx.EVT_CLOSE,self.onExit)

    def Build_FileMenu(self, extras=None):
        mfile = wx.Menu()
        MenuItem(self, mfile, "&Save Image\tCtrl+S",
                 "Save Image of Plot (PNG, SVG, JPG)",
                 action=self.save_figure)
        MenuItem(self, mfile, "&Copy\tCtrl+C",
                 "Copy Plot Image to Clipboard",
                 self.Copy_to_Clipboard)

        MenuItem(self, mfile, "Export Data",
                "Export Data to ASCII Column file",
                self.onExport)

        if extras is not None:
            for text, helptext, callback in extras:
                MenuItem(self, mfile, text, helptext, callback)


        mfile.AppendSeparator()
        MenuItem(self, mfile, 'Page Setup...', 'Printer Setup',
                 self.PrintSetup)

        MenuItem(self, mfile, 'Print Preview...', 'Print Preview',
                 self.PrintPreview)

        MenuItem(self, mfile, "&Print\tCtrl+P", "Print Plot",
                 self.Print)

        # mfile.AppendSeparator()
        # MenuItem(self, mfile, "E&xit\tCtrl+Q", "Exit", self.onExit)
        return mfile

    def save_configuration(self, event=None, **kws):
        print "Saving plots configuration..."
        SavePlotsConfiguration(view=self.view).execute()