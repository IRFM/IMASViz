import wx
import os
from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.gui_commands.plot_commands.PlotSelectedSignalsWithWxmplot import PlotSelectedSignalsWithWxmplot
from imasviz.gui_commands.select_commands.SelectSignals import SelectSignals

class ConfigurationListsFrame(wx.Frame):
    """The configuration panel, listing the available save configuration files,
       and its features.
    """
    def __init__(self, parent,  *args, **kwargs):
        wx.Frame.__init__(self, id=wx.NewId(), name='', parent=parent,
                          pos=wx.Point(358, 184), size=wx.Size(350, 500),
                          style=wx.DEFAULT_FRAME_STYLE|wx.LB_SINGLE,
                          title='Available configurations')
        self.parent = parent
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.configurationFilesList = None
        self.createList()

        # Set buttons
        # - 'Apply configuration to MultiPlot' button
        #   - Next button ID
        buttonId = wx.NewId()
        #   - Create button
        apply_MultiPlot_button = \
            wx.Button(self, buttonId, 'Apply configuration to MultiPlot')
        #   - Add the 'Apply configuration to MultiPlot' button to BoxSizer
        self.vbox.Add(apply_MultiPlot_button, 0, wx.ALL|wx.EXPAND, 5)
        #   - Bind 'apply_MultiPlot_button' feature to the 'Apply configuration
        #     to MultiPlot' button
        self.Bind(wx.EVT_BUTTON, self.apply_MultiPlot, id=buttonId)

        # - 'Remove configuration' button
        #   - Next button ID
        removeButtonId = wx.NewId()
        #   - Create button
        remove_button = wx.Button(self, removeButtonId, 'Remove configuration')
        #   - Add the 'Remove configuration' button to BoxSizer
        self.vbox.Add(remove_button, 0, wx.ALL | wx.EXPAND, 5)
        #   - Bind 'removeConfiguration' feature to the 'Remove configuration'
        #     button
        self.Bind(wx.EVT_BUTTON, self.removeConfiguration, id=removeButtonId)

        # - 'Apply signal selection' button
        #   - Next button ID
        signalSelectButtonId = wx.NewId()
        #   - Create button
        signalSelect_button = wx.Button(self, signalSelectButtonId,
            'Apply signal selection')
        #   - Add the 'Apply signal selection' button to BoxSizer
        self.vbox.Add(signalSelect_button, 0, wx.ALL | wx.EXPAND, 5)
        #   - Bind 'removeConfiguration' feature to the 'Apply signal selection'
        #     button
        self.Bind(wx.EVT_BUTTON, self.Apply_Signal_Selection,
                  id=signalSelectButtonId)

        # buttonTestId = wx.NewId()
        # test_button = wx.Button(self, buttonTestId, 'Apply configuration TEST')
        # self.vbox.Add(test_button, 0, wx.ALL|wx.EXPAND, 5)
        # self.Bind(wx.EVT_BUTTON, self.Apply_Signal_Selection, id=buttonTestId)

        # Set note
        # - Set fonts
        font_size = 10
        font_bold = wx.Font(font_size, wx.SWISS, wx.NORMAL, wx.BOLD)
        font_normal = wx.Font(font_size, wx.SWISS, wx.NORMAL, wx.NORMAL)
        # - Set wrap width
        noteText_wrapWidth = 325
        # - Set note texts
        note_1 = "Note:"
        note_2 = "The configuration will be applied ONLY to the " \
                 "single currently opened IMAS database source:"
        note_3 = self.parent.GetTitle()
        # - Next ID
        staticTextId = wx.NewId()
        # - Set first wx.StaticText
        noteText_1 = wx.StaticText(self, staticTextId, note_1)
        noteText_1.SetFont(font_bold)
        # - Next ID
        staticTextId = wx.NewId()
        # - Set second wx.StaticText
        noteText_2 = wx.StaticText(self, staticTextId, note_2)
        noteText_2.SetFont(font_normal)
        noteText_2.Wrap(noteText_wrapWidth)
        # - Next ID
        staticTextId = wx.NewId()
        # - Set third wx.StaticText
        noteText_3 = wx.StaticText(self, staticTextId, note_3)
        noteText_3.SetFont(font_bold)
        noteText_3.Wrap(noteText_wrapWidth)

        # - Add static text to BoxSizer
        self.vbox.Add(noteText_1, 0, wx.LEFT, 4)
        self.vbox.Add(noteText_2, 0, wx.LEFT, 4)
        self.vbox.Add(noteText_3, 0, wx.LEFT, 4)

        # Set sizer
        self.SetSizer(self.vbox)

    def createList(self):

        self.listBox1 = wx.ListBox(choices=[], id=wx.NewId(),
                                   name='Available configurations',
                                   parent=self, pos=wx.Point(8, 48),
                                   size=wx.Size(184, 256), style=0)

        # self.configurationFilesList = \
        #    GlobalOperations.getConfigurationFilesList()
        # for f in self.configurationFilesList:
        #     self.listBox1.Append(f)
        self.update()

        self.vbox.Add(self.listBox1 , 0, wx.ALL|wx.EXPAND, 5)

    def showListBox(self):
        self.Show(True)

    def update(self):
        self.listBox1.Clear()
        self.configurationFilesList = \
            GlobalOperations.getConfigurationFilesList()
        for f in self.configurationFilesList:
            self.listBox1.Append(f)

    def Apply_Signal_Selection(self, event):
        pos = self.listBox1.GetSelection()
        selectedFile = \
            GlobalOperations.getConfigurationFilesDirectory() + \
            "/" + self.configurationFilesList[pos]
        pathsList = GlobalOperations.getSignalsPathsFromConfigurationFile(
                        configFileName=selectedFile)
        SelectSignals(self.parent.wxTreeView, pathsList).execute()

    def apply_MultiPlot(self, event):
        pos = self.listBox1.GetSelection()
        selectedFile = \
            GlobalOperations.getConfigurationFilesDirectory() + \
            "/" + self.configurationFilesList[pos]
        figurekey = \
            self.parent.wxTreeView.imas_viz_api.GetNextKeyForMultiplePlots()
        PlotSelectedSignalsWithWxmplot(self.parent.wxTreeView,
                                       figurekey=figurekey,
                                       update=0,
                                       configFileName=selectedFile).execute()


    def removeConfiguration(self, event):
        pos = self.listBox1.GetSelection()
        selectedFile = \
            GlobalOperations.getConfigurationFilesDirectory() + \
            "/" + self.configurationFilesList[pos]
        #print selectedFile
        answer = GlobalOperations.YesNo(question =
            "The configuation " + selectedFile + " will be deleted. Are you sure?")
        if answer:
            print ('Removing configuration: ' + selectedFile)
            try:
                os.remove(selectedFile)
                self.listBox1.Delete(pos)
                self.configurationFilesList = \
                    GlobalOperations.getConfigurationFilesList()
            except OSError:
                print ("Unable to remove file: " + selectedFile)