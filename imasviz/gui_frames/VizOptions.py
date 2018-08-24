import wx.py
import os
from imasviz.util.GlobalValues import GlobalValues, Imas_Viz_Options

class VizOptions(wx.Frame):

    def __init__(self, parent, id):
        wx.Frame.__init__(self, parent, id, 'IMAS_VIZ options', size=(400, 300))
        self.panel = wx.Panel(self)
        self.myCheckBox01 = wx.CheckBox(self.panel, 101, "Hide empty signals", (20, 20), (160, -1))
        self.myCheckBox01.SetValue(Imas_Viz_Options.HIDE_EMPTY_SIGNALS)
        self.myCheckBox02 = wx.CheckBox(self.panel, 102, "Hide obsolescent nodes", (20, 40), (160, -1))
        self.myCheckBox02.SetValue(Imas_Viz_Options.HIDE_OBSOLESCENT_NODES)
        self.Bind(wx.EVT_CLOSE, self.onClose)

    def onClose(self, event):
        Imas_Viz_Options.HIDE_EMPTY_SIGNALS = self.myCheckBox01.IsChecked()
        Imas_Viz_Options.HIDE_OBSOLESCENT_NODES = self.myCheckBox02.IsChecked()
        self.Hide()

if __name__ == '__main__':
    app = wx.App()
    frame = VizOptions(parent=None, id=-1)
    frame.Center()
    frame.Show()
    app.MainLoop()




