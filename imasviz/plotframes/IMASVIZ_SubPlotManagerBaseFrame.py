#!/usr/bin/python
"""A modified wxmplot.StackedPlotFrame file intended for configuration
of the IMASViz SubPlotManager. Originally it was working with max two
plots - top and bottom, and it was modified to allow plotting 'n' number of
plots (any number of selected plot signals).

First plot panel is labeled as 'panel0', second 'panel1' etc. with the
'panel_last' reffering to the n-th panel.
"""

import wx
import numpy as np
import matplotlib
from matplotlib.ticker import NullFormatter, NullLocator
from functools import partial
from wxmplot.utils import pack, MenuItem
from wxmplot.plotpanel import PlotPanel
from wxmplot.baseframe import BaseFrame
# import tkinter as tk


class SubPlotManagerBaseFrame(BaseFrame):
    """
    Top/Bottom MatPlotlib panels in a single frame
    """
    def __init__(self, parent=None, title ='Stacked Plot Frame',
                 numPlots = 1, **kws):

        """Get screen resolution"""
        # root = tk.Tk()
        # screen_width = root.winfo_screenwidth()
        # screen_height = root.winfo_screenheight()

        """Set BaseFrame size"""
        self.frame_width = 750
        self.frame_height = 710

        """Set BaseFrame size"""
        framesize=(self.frame_width, self.frame_height)

        """Create BaseFrame"""
        BaseFrame.__init__(self, parent=parent, title=title,
                           size=framesize, **kws)

        """Set size of the subplots"""
        nplots_size = ((self.frame_height-120)/numPlots)
        """ - Set default panel size in relation to frame size"""
        self.panelsize = (self.frame_width, nplots_size)
        """ - Set first panel size in relation to default panel size"""
        self.panel0size = (self.frame_width, nplots_size+50)
        """ - Set last panel size in relation to default panel size"""
        self.panel_lastsize = (self.frame_width, nplots_size+70)

        self.xlabel = None

        """Set number of plots"""
        self.numPlots = numPlots

        """Set empty list of panels for plots (to be populated later)"""
        self.panelList = []
        """Set empty list of panel names"""
        self.panelLabelList = []

        for plot_id in range(self.numPlots):
            if plot_id == self.numPlots - 1:    # For bottom plot
                """Set current plot name"""
                panelLabel = 'panel_last'
            else:
                """Set current plot name"""
                panelLabel = 'panel' + str(plot_id)

            """Add plot name to list of plot names"""
            self.panelLabelList.append(panelLabel)
            """Generate code for declaring n panel objects
               (e.g. self.panel0 etc.)
            """
            panelObjectGenCode = 'self.' + panelLabel + '= None'
            """Execute generated command (e.g. 'self.panel0 = None' to declare
               current panel object
            """
            exec(panelObjectGenCode)

            # """Append the created panel object to self.panelList"""
            # addPanel2ListGenCode = 'self.panelList.append( self.' + panelLabel + ')'
            # """Execute generated command (e.g.
            # 'self.panelList.append(self.panel0') to add the panel object to the
            # panelList
            # """
            # exec(addPanel2ListGenCode)

        self.BuildFrame()

    def get_panel(self, panelname):
        if panelname.lower().startswith('bot'):
            return self.panel_last
        else:
            return eval('self.' + panelname)

    def get_panel_by_ID(self, panelID):
        """Get panel by ID. 'panelname' must be the same as object label
           (e.g. labelID = 0 for self.panel0)
        """
        return eval('self.panel' + str(panelID))

    def plot(self, x, y, xmin=0, xmax=1, panel='panel0', xlabel=None, **kws):
        """plot after clearing current plot """
        panel = self.get_panel(panel)
        """Add plot to panel.
           Note: xmin and xmax are multipled my 1.01 do add some space to left and
                 right side
        """
        panel.plot(x, y, xmin=xmin*1.01, xmax=xmax*1.01, **kws)

        if xlabel is not None:
            self.xlabel = xlabel
        if self.xlabel is not None:
            self.panel_last.set_xlabel(self.xlabel)

    def oplot(self, x, y, xmin=0, xmax=1, panel='panel0', xlabel=None, **kws):
        """plot method, overplotting any existing plot """
        panel = self.get_panel(panel)
        """Add plot to existing plot within panel.
           Note: xmin and xmax are multipled my 1.01 do add some space to left and
                 right side
        """
        panel.oplot(x, y, xmin=xmin*1.01, xmax=xmax*1.01, **kws)
        if xlabel is not None:
            self.xlabel = xlabel
        if self.xlabel is not None:
            self.panel_last.set_xlabel(self.xlabel)

    def add_text(self, panel, text, x, y):
        panel =self.get_panel(panel)
        panel.add_text(text, x, y)

    def unzoom_all(self, event=None):
        """ zoom out full data range """
        # for p in (self.panel0, self.panel_last):
        for i in range(len(self.panelLabelList)):
            p = eval('self.' + self.panelLabelList[i])
            p.conf.zoom_lims = []
            p.conf.unzoom(full=True)
        # self.panel.set_viewlimits()

    def unzoom(self, event=None, panel='panel0'):
        """zoom out 1 level, or to full data range """
        panel = self.get_panel(panel)
        panel.conf.unzoom(event=event)
        self.panel.set_viewlimits()

    def update_line(self, t, x, y, panel='panel0', **kws):
        """overwrite data for trace t """
        panel = self.get_panel(panel)
        panel.update_line(t, x, y, **kws)

    def set_xylims(self, lims, axes=None, panel='panel0', **kws):
        """set xy limits"""
        panel = self.get_panel(panel)
        # print("Stacked set_xylims ", panel, self.panel)
        panel.set_xylims(lims, axes=axes, **kws)

    def clear(self, panel='panel0'):
        """clear plot """
        panel = self.get_panel(panel)
        panel.clear()

    def set_title(self,s, panel='panel0'):
        "set plot title"
        panel = self.get_panel(panel)
        panel.set_title(s)

    def set_xlabel(self,s, panel='panel0'):
        "set plot xlabel"
        self.panel_last.set_xlabel(s)

    def set_ylabel(self,s, panel='panel0'):
        "set plot xlabel"
        panel = self.get_panel(panel)
        panel.set_ylabel(s)

    def save_figure(self, event=None, panel='panel0'):
        """ save figure image to file"""
        panel = self.get_panel(panel)
        panel.save_figure(event=event)

    def configure(self, event=None, panel='panel0'):
        panel = self.get_panel(panel)
        panel.configure(event=event)

    ####
    ## create GUI
    ####
    def BuildFrame(self):
        sbar = self.CreateStatusBar(2, wx.CAPTION)
        sfont = sbar.GetFont()
        sfont.SetWeight(wx.BOLD)
        sfont.SetPointSize(10)
        sbar.SetFont(sfont)

        self.SetStatusWidths([-3,-1])
        self.SetStatusText('',0)

        """Create sizer"""
        sizer = wx.BoxSizer(wx.VERTICAL)

        """Set margins for first and last subplot panel"""
        margins = {'panel0': dict(left=0.15, bottom=0.00, top=0.20, right=0.05),
                   'panel_last': dict(left=0.15, bottom=0.30, top=0.00, right=0.05)}

        setPlotEval = []
        for plot_id in range(self.numPlots):

            setPlotEval.append(str('self.' + self.panelLabelList[plot_id]) )

            if plot_id  == 0:   # First panel
                """Set first panel"""
                self.panel0 = PlotPanel(self, size=self.panel0size)
                lsize = self.panel0.conf.labelfont.get_size()
                self.panel0.conf.margin_callback = self.onMargins

            elif plot_id == self.numPlots - 1:   # Last panel
                panelLabel = self.panelLabelList[plot_id]  # panelLabel == 'panel_last'
                """Set bottom panel"""
                self.panel_last = PlotPanel(self, size=self.panel_lastsize)
                self.panel_last.conf.labelfont.set_size(lsize)
                self.panel_last.yformatter = self.bot_yformatter

            else:   # Panels in the middle - between top and bottom panel
                panelLabel = self.panelLabelList[plot_id]

                """Set margins (dictionary) for the additional subplot
                   panels in the middle (between the first and last subplot)
                """
                margins.update({panelLabel: dict(left=0.15, bottom=0.00,
                                                 top=0.00, right=0.05)})

                """Set middle panel"""
                exec('self.' + panelLabel + '= PlotPanel(self, size=self.panelsize)')

                exec('self.' + panelLabel + '.xformatter = ' + \
                    'self.null_formatter')
                lsize = eval('self.' + panelLabel + '.conf.labelfont.get_size()')
                exec('self.' + panelLabel + '.conf.labelfont.set_size(lsize)')
                exec('self.' + panelLabel + '.conf.margin_callback = self.onMargins')

        for pname in self.panelLabelList:
            pan = self.get_panel(pname)
            pan.messenger = self.write_message
            pan.conf.auto_margins = False
            pan.conf.set_margins(**margins[pname])
            pan.axes.update_params()
            pan.axes.set_position(pan.axes.figbox)
            pan.set_viewlimits = partial(self.set_viewlimits, panel=pname)
            pan.unzoom_all = self.unzoom_all
            pan.unzoom = self.unzoom
            pan.canvas.figure.set_facecolor('#F4F4EC')

            if pname == 'panel_last':
                # # suppress mouse events on the bottom panel
                # null_events = {'leftdown': None, 'leftup': None, 'rightdown': None,
                #                'rightup': None, 'motion': None, 'keyevent': None}
                # self.panel_last.cursor_modes = {'zoom': null_events}
                """Add subplot panel to sizer"""
                sizer.Add(self.panel_last, 1, wx.GROW | wx.EXPAND, 2)
            else:
                """Add subplot panel to sizer"""
                exec('sizer.Add(self.' + pname + ', 1, wx.GROW | wx.EXPAND, 2)')

        pack(self, sizer)
        sizer.RecalcSizes()

        self.SetAutoLayout(True)
        # self.SetSizerAndFit(sizer)
        self.SetSizer(sizer)
        self.BuildMenu()

    def BuildMenu(self):
        """Set SubPlot Manager display window menu bar"""
        mfile = self.Build_FileMenu()

        """Set 'Options' menu"""
        mopts = wx.Menu()
        # MenuItem(self, mopts, "Configure Plot\tCtrl+K",
        #          "Configure Plot styles, colors, labels, etc",
        #          self.panel0.configure)
        # MenuItem(self, mopts, "Configure Lower Plot",
        #          "Configure Plot styles, colors, labels, etc",
        #          self.panel_last.configure)
        # MenuItem(self, mopts, "Toggle Legend\tCtrl+L",
        #          "Toggle Legend Display",
        #          self.panel0.toggle_legend)
        # MenuItem(self, mopts, "Toggle Grid\tCtrl+G",
        #          "Toggle Grid Display",
        #          self.toggle_grid)

        # mopts.AppendSeparator()

        """Add 'Zoom all plots out' option menu item"""
        MenuItem(self, mopts, "Zoom Out\tCtrl+Z",
                 "Zoom out to full data range",
                 self.unzoom_all)
        """Add 'Apply top theme to all' option menu item"""
        MenuItem(self, mopts, "Top theme to all",
                 "Apply top panel theme to all other plots",
                 self.onThemeColorAll)

        """Set 'Help' menu"""
        mhelp = wx.Menu()
        """Add 'Quick reference' menu item"""
        MenuItem(self, mhelp, "Quick Reference",  "Quick Reference for WXMPlot",
                 self.onHelp)
        """Add 'About' menu item"""
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

    def toggle_grid(self, event=None, show=None):
        "toggle grid on top/bottom panels"
        if show is None:
            show = not self.panel0.conf.show_grid
        for p in (self.panel0, self.panel_last):
            p.conf.enable_grid(show)

    def onThemeColor(self, color, item):
        """pass theme colors to bottom panel"""
        bconf = self.panel_last.conf
        if item == 'grid':
            bconf.set_gridcolor(color)
        elif item == 'bg':
            bconf.set_bgcolor(color)
        elif item == 'frame':
            bconf.set_framecolor(color)
        elif item == 'text':
            bconf.set_textcolor(color)
        bconf.canvas.draw()

    def onThemeColorAll(self, event=None):
        "Pass first panel theme to all other panels"
        for plot_id in range(1, self.numPlots):
            """Traverse through all other plots and set the .conf object of the
            plot
            """
            bconf = eval('self.' + self.panelLabelList[plot_id] + '.conf')
            """Set plot grid color the same as of the first plot"""
            bconf.set_gridcolor(self.panel0.conf.gridcolor)
            """Set plot bg color the same as of the first plot"""
            bconf.set_bgcolor(self.panel0.conf.bgcolor)
            """Set plot frame color the same as of the first plot"""
            bconf.set_framecolor(self.panel0.conf.framecolor)
            """Set plot text color the same as of the first plot"""
            bconf.set_textcolor(self.panel0.conf.textcolor)

    def onMargins(self, left=0.1, top=0.1, right=0.1, bottom=0.1):
        """ pass left/right margins on to bottom panel"""
        bconf = self.panel_last.conf
        l, t, r, b = bconf.margins
        bconf.set_margins(left=left, top=t, right=right, bottom=b)
        bconf.canvas.draw()

    def set_viewlimits(self, panel='panel0'):
        """update xy limits of a plot, as used with .update_line() """
        this_panel = self.get_panel(panel)
        other = self.get_panel(panel)   # Dummy object

        xmin, xmax, ymin, ymax = this_panel.conf.set_viewlimits()[0]
        # print("Set ViewLimits ", xmin, xmax, ymin, ymax)
        # make all panels below the top panel follow the top panel xlimits
        if this_panel == self.panel0:  # If this_panel == top panel
            for i in range(1, len(self.panelLabelList)): # Traverse through all
                                                    # panels below the top panel
                other = eval('self.' + self.panelLabelList[i])
                for _ax in other.fig.get_axes():
                    _ax.set_xlim((xmin, xmax), emit=True)
                other.draw()

    def null_formatter(self, x, pos, type='x'):
        return ''

    def bot_yformatter(self, val, type=''):
        """custom formatter for FuncFormatter() and bottom panel"""
        fmt = '%1.5g'

        ax = self.panel_last.axes.yaxis

        ticks = ax.get_major_locator()()
        dtick = ticks[1] - ticks[0]

        if   dtick > 29999:
            fmt = '%1.5g'
        elif dtick > 1.99:
            fmt = '%1.0f'
        elif dtick > 0.099:
            fmt = '%1.1f'
        elif dtick > 0.0099:
            fmt = '%1.2f'
        elif dtick > 0.00099:
            fmt = '%1.3f'
        elif dtick > 0.000099:
            fmt = '%1.4f'
        elif dtick > 0.0000099:
            fmt = '%1.5f'

        s =  fmt % val
        s.strip()
        s = s.replace('+', '')
        while s.find('e0')>0:
            s = s.replace('e0','e')
        while s.find('-0')>0:
            s = s.replace('-0','-')
        return s

    def onExit(self, event=None):
        """Override the onExit function to hide the window instead to destroy it
           (this is required to enable for the SubPlot Manager
           window to be reopened in the same session after it was closed)
        """
        try:
            """Hide window"""
            self.Hide()
        except:
            pass


if  __name__ == "__main__":
    """Modified StackedPlotFrame test (independent from IMASViz)
    """

    """Set main app"""
    app = wx.App()

    """Set example arrays"""
    x = np.arange(0.0, 30.0, 0.1)
    y = np.sin(2*x)/(x+2)

    """Print the arrays"""
    # print("x: ", x)
    # print("y: ", y)

    """Set the frame for multiple plots."""
    pframe = SubPlotManagerBaseFrame(title='SubPlotManager', numPlots = 4)

    xmin = -1
    xmax = max(x+100)+1
    """Set first plot example"""
    pframe.plot(x, y, panel='panel0', label="First plot", xlabel="First xlabel",
            ylabel="First ylabel", title="First plot title", show_legend=True,
            xmin = xmin, xmax = xmax)

    """Add another plot to the first plot"""
    pframe.oplot((x*1.3), (y*1.3), panel='panel0', label='Add to top plot',
                 show_legend=True, xmin = xmin, xmax = xmax)

    """Set second plot example"""
    pframe.plot(x, y, panel='panel1', label="Second plot", xlabel="Second xlabel",
            ylabel="Second ylabel", title="Second plot title", show_legend=True,
            xmin = xmin, xmax = xmax)

    pframe.add_text( panel='panel1', text=".test_text", x=60, y=0)

    """Set third plot example"""
    pframe.plot(x+100, y+100, panel='panel2', label="Third plot", xlabel="Third xlabel",
            ylabel="Third ylabel", title="Third plot title", show_legend=True,
            xmin = xmin, xmax = xmax)

    """Set last plot example"""
    pframe.plot((x*0.9), (y*0.9), panel='panel_last', label="Last plot", xlabel="Last xlabel",
            ylabel="Last ylabel", title="Last plot title", show_legend=True,
            xmin = xmin, xmax = xmax)

    """Show multiplot frame"""
    pframe.Show()
    pframe.Raise()

    """Run app"""
    app.MainLoop()
