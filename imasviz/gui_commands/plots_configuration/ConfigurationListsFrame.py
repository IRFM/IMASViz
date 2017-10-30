import wx
import os
from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.gui_commands.plot_commands.PlotSelectedSignalsWithWxmplot import PlotSelectedSignalsWithWxmplot


class ConfigurationListsFrame(wx.Frame):
    def __init__(self, parent,  *args, **kwargs):
        wx.Frame.__init__(self, id=wx.NewId(), name='', parent=parent,
                          pos=wx.Point(358, 184), size=wx.Size(299, 387),
                          style=wx.DEFAULT_FRAME_STYLE|wx.LB_SINGLE, title='Available configurations')
        self.parent = parent
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.configurationFilesList = None
        self.createList()
        buttonId = wx.NewId()
        apply_button = wx.Button(self, buttonId, 'Apply configuration')
        removeButtonId = wx.NewId()
        remove_button = wx.Button(self, removeButtonId, 'Remove configuration')
        self.vbox.Add(apply_button, 0, wx.ALL|wx.EXPAND, 5)
        self.vbox.Add(remove_button, 0, wx.ALL | wx.EXPAND, 5)
        self.Bind(wx.EVT_BUTTON, self.apply, id=buttonId)
        self.Bind(wx.EVT_BUTTON, self.removeConfiguration, id=removeButtonId)
        self.SetSizer(self.vbox)

    def createList(self):

        self.listBox1 = wx.ListBox(choices=[], id=wx.NewId(),
                                   name='Available configurations', parent=self, pos=wx.Point(8, 48),
                                   size=wx.Size(184, 256), style=0)

        # self.configurationFilesList = GlobalOperations.getMultiplePlotsConfigurationFilesList()
        # for f in self.configurationFilesList:
        #     self.listBox1.Append(f)
        self.update()

        self.vbox.Add(self.listBox1 , 0, wx.ALL|wx.EXPAND, 5)

    def showListBox(self):
        self.Show(True)

    def update(self):
        self.listBox1.Clear()
        self.configurationFilesList = GlobalOperations.getMultiplePlotsConfigurationFilesList()
        for f in self.configurationFilesList:
            self.listBox1.Append(f)

    def apply(self, event):
        pos = self.listBox1.GetSelection()
        selectedFile = GlobalOperations.getMultiplePlotsConfigurationFilesDirectory() + "/" + self.configurationFilesList[pos]
        numFig = self.parent.wxTreeView.imas_viz_api.GetNextNumFigForNewMultiplePlots()
        #print numFig
        PlotSelectedSignalsWithWxmplot(self.parent.wxTreeView, numfig=numFig, update=0, configFileName=selectedFile).execute()


    def removeConfiguration(self, event):
        pos = self.listBox1.GetSelection()
        selectedFile = GlobalOperations.getMultiplePlotsConfigurationFilesDirectory() + "/" + \
                       self.configurationFilesList[pos]
        #print selectedFile
        answer = GlobalOperations.YesNo(question = "The configuation " + selectedFile + " will be deleted. Are you sure ?")
        if answer:
            print 'Removing configuration: ' + selectedFile
            try:
                os.remove(selectedFile)
                self.listBox1.Delete(pos)
                self.configurationFilesList = GlobalOperations.getMultiplePlotsConfigurationFilesList()
            except OSError:
                print "Unable to remove file: " + selectedFile