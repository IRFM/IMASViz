import wx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
import numpy as np
from imasviz.subplots.SubPlot import SubPlot
from imasviz.subplots.SubplotsCustomization import SubPlotsCustomization
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from imasviz.util.GlobalValues import FigureTypes

class SubPlotsShareXFrame(wx.Frame):
    def __init__(self, parent, title, subPlotsList, subplotsCount, hspace = 0):
        wx.Frame.__init__(self,parent,title=title,size=(800,800))
        self.imas_viz_api = None
        #self.keep = False
        self.fig = plt.figure()
        self.subPlotsList = subPlotsList
        self.subplotsCount = subplotsCount
        self.hspace = hspace
        self.f, self.axarr = plt.subplots(subplotsCount, sharex=True, squeeze=False)

        plt.subplots_adjust(left=0.1, bottom=0.1, right=0.7, top=0.9, wspace=0, hspace=0)

        self.canvas = FigureCanvas(self, -1, self.f)
        self.updateSubPlots(self.subPlotsList, self.hspace)

        self.button_keep_subplots = wx.Button(self, 1, 'Keep this subplots')
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.canvas, 1, wx.EXPAND | wx.ALL)
        vbox.Add(self.button_keep_subplots, 0, wx.ALIGN_LEFT | wx.TOP | wx.BOTTOM, 20)
        self.Bind(wx.EVT_BUTTON, self.keepSubPlots)


        menubar = wx.MenuBar()
        styleMenu = wx.Menu()
        fitem = styleMenu.Append(wx.ID_PROPERTIES, 'Set plot style', '')
        menubar.Append(styleMenu, "Customize")
        self.SetMenuBar(menubar)
        self.Bind(wx.EVT_MENU, self.OnSetPlotStyle, fitem)
        #self.add_toolbar()

        self.toolbar = NavigationToolbar2Wx(self.canvas)
        self.toolbar.Realize()
        vbox.Add(self.toolbar, 0, wx.LEFT | wx.EXPAND)
        # update the axes menu on the toolbar
        self.toolbar.update()

        self.SetSizer(vbox)

        self.Bind(wx.EVT_CLOSE, self.onClose)

    def onClose(self, event):
        self.Hide()

    def ShowFrame(self):
        self.button_keep_subplots.Disable()
        self.Show()

    def updateSubPlots(self, subPlotsList, hspace, update=False):

        #setting x limitation range, taking xlim from first plot as default
        sp = subPlotsList[0]
        plt.xlim(sp.xmin, sp.xmax)

        legends_map = {}
        legends_handles_map = {}

        for i in range(0, len(subPlotsList)):

            sp = subPlotsList[i]

            ax = self.axarr[sp.subplot_number, 0]

            if (sp.subplot_number not in legends_handles_map):
                legends_handles_map[sp.subplot_number] = []
                legends_map[sp.subplot_number] = []

            plt.ylim(sp.ymin, sp.ymax)
            ax.set_ylabel(sp.labelY)

            if sp.subplot_number == self.subplotsCount - 1:
                self.axarr[sp.subplot_number, 0].set_xlabel(sp.labelX)
            if (update == False):
                if sp.scatter == True:
                    legend_handle, = ax.scatter(sp.x[0], sp.y[0])
                    sp.setLegendHandle(legend_handle)
                else:
                    legend_handle, = ax.plot(sp.x[0], sp.y[0])
                    sp.setLegendHandle(legend_handle)
            if hspace == 0:
                if i == 0 and sp.title is not None:
                    ax.set_title(sp.title)
            else:
                if sp.title is not None:
                    ax.set_title(sp.title)

            legends_handles_map[sp.subplot_number].append(sp.legend_handle)
            legends_map[sp.subplot_number].append(sp.legend)

        self.f.subplots_adjust(hspace=0)
        ax.legend(loc=2)
        for i in range(0, self.subplotsCount):
            #ax.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.,frameon=False)
            leg = self.axarr[i, 0].legend(legends_handles_map[i], legends_map[i])
            leg.get_frame().set_linewidth(0.0)
            leg.set_bbox_to_anchor((1.,1))
        self.canvas.draw()


    def OnSetPlotStyle(self, evt):
        spf = SubPlotsSetStyleFrame(self, "Set subplots style", self.subPlotsList, self.hspace)
        spf.Show()

    def keepSubPlots(self, evt):
        #api = self.GetParent().dataTree.imas_viz_api
        loop = True
        subplotName = self.imas_viz_api.GetNextKeyForSubPlots()
        while loop:
            subplotName = self.ask(message='Name of the subplots:', default_value=subplotName)
            if (subplotName not in self.imas_viz_api.GetFiguresKeys(figureType=FigureTypes.SUBPLOTTYPE)) :
                loop = False
                #self.keep = True
                figureKey = self.imas_viz_api.GetFigureKey(subplotName, FigureTypes.SUBPLOTTYPE)
                self.SetTitle(figureKey)
                self.imas_viz_api.figureframes[figureKey] = self
                self.button_keep_subplots.Disable()
            else:
                dlg = wx.MessageDialog(None, "The name " + subplotName + " already exists.", caption="Duplicate name", style=wx.OK)
                dlg.ShowModal()

    def onHide(self, api, key):
        if key in api.GetFiguresKeys(figureType=FigureTypes.SUBPLOTTYPE):
            api.figureframes[key].Hide()

    def ask(self, parent=None, message='', default_value=''):
        dlg = wx.TextEntryDialog(parent, message, value=default_value, style=wx.OK)
        dlg.ShowModal()
        result = dlg.GetValue()
        dlg.Destroy()
        return result


class SubPlotsSetStyleFrame(wx.Frame):
    def __init__(self, parent, title, subPlotsList, hspace):
        wx.Frame.__init__(self,parent,title=title,size=(800,800))
        self.subPlotsList = subPlotsList
        self.hspace = hspace
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.sc = SubPlotsCustomization(self, self.subPlotsList)
        update_subplots = wx.Button(self, 1, 'Update subplots')
        vbox.Add(update_subplots, 0, wx.ALIGN_LEFT | wx.TOP | wx.BOTTOM, 20)
        vbox.Add(self.sc, 1, wx.EXPAND | wx.ALL)
        self.SetSizer(vbox)
        self.Bind(wx.EVT_BUTTON, self.OnUpdateSubplots)

    def OnUpdateSubplots(self, evt):
        labelX = self.sc.txtCtrl[0].GetValue()
        for i in range(0,len(self.subPlotsList)):
            self.subPlotsList[i].labelX = labelX
            subplotnumber = self.subPlotsList[i].subplot_number
            labelY = self.sc.txtCtrl[subplotnumber + 1].GetValue()
            if labelY is not None:
                self.subPlotsList[i].labelY = labelY

            legend = self.sc.txtCtrl_legends[i].GetValue()
            if legend is not None:
                self.subPlotsList[i].legend = legend

        self.GetParent().updateSubPlots(self.subPlotsList, self.hspace, True)


if __name__ == "__main__":
    app=wx.PySimpleApp()
    subPlotsList = []
    x = np.arange(0.0, 2.0, 0.02)
    y = np.sin(2 * np.pi * x)
    sp = SubPlot(x, y, False)
    subPlotsList.append(sp)
    y1 = np.cos(np.pi*x)
    sp2 = SubPlot(x, y1, True, 'Titre2')
    subPlotsList.append(sp2)
    frame=SubPlotsShareXFrame(None, "SubPlotsTest", subPlotsList, 0.0)
    frame.Show()
    app.MainLoop()
