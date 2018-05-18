import wx
import os
from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.gui_commands.plot_commands.PlotSelectedSignalsWithWxmplot import PlotSelectedSignalsWithWxmplot
from imasviz.gui_commands.select_commands.SelectSignals import SelectSignals

class ConfigurationListsFrame(wx.Frame):
    """The configuration frame, containing tabs dealing with different
       configuration files.
    """
    def __init__(self, parent,  *args, **kwargs):
        wx.Frame.__init__(self, id=wx.NewId(), name='', parent=parent,
                          pos=wx.Point(358, 184), size=wx.Size(450, 530),
                          style=wx.DEFAULT_FRAME_STYLE|wx.LB_SINGLE,
                          title='Available configurations')
        self.parent = parent

        self.InitTabs()

    def showListBox(self):
        self.Show(True)

    def InitTabs(self):
        """Initialize tabs
        """
        # Set notebook that will contain the tabs
        nb = wx.Notebook(self)

        # Tab listing available plot configurations
        # - Set tab
        self.pconf_panel = PlotConfigurationListsTab(parent=nb, DTV=self.parent)
        # - Add to notebook
        nb.AddPage(self.pconf_panel, 'Available plot configurations')

        # Tab listing available lists of signal paths (IDS paths)
        # - Set tab
        self.lsp_panel = ListOfSignalPathsListsTab(parent=nb, DTV=self.parent)
        # - Add to notebook
        nb.AddPage(self.lsp_panel, 'Available lists of IDS paths')

    def update_pconf(self):
        self.pconf_panel.update()

    def update_lsp(self):
        self.lsp_panel.update()

class CommonConfigurationRoutines():
    """Common configuration routines.
    """
    def __init__(self, parent):
        """

        Parameters
        ----------

        parent: wx.Panel object
            wxPanel object, representing one of the tabs in the
            configuration frame

        """
        self.parent = parent    # wx.Panel object (tab panel)

    def Apply_Signal_Selection(self, event):
        """Apply signal selection from the config file - select signals only.
        """
        # Get in-list position of the selection (config file name)
        pos = self.parent.listBox1.GetSelection()
        # Get system path to the selected configuration file
        selectedFile = \
            GlobalOperations.getConfigurationFilesDirectory() + \
            "/" + self.parent.configurationFilesList[pos]
        # Extract signal paths from the config file and add them to a list of
        # paths
        pathsList = GlobalOperations.getSignalsPathsFromConfigurationFile(
                        configFile=selectedFile)
        # Select the signals, defined by a path in a list of paths, in the
        # given wxDataTreeView (DTV) window
        SelectSignals(self.parent.DTV.wxTreeView, pathsList).execute()

    def removeConfiguration(self, event):
        """Remove configuration file from the list.
        """
        # Get in-list position of the selection (config file name)
        pos = self.parent.listBox1.GetSelection()
        # Get system path to the selected configuration file
        selectedFile = \
            GlobalOperations.getConfigurationFilesDirectory() + \
            "/" + self.parent.configurationFilesList[pos]
        # Get Yes/No answer (returns True/False)
        answer = GlobalOperations.YesNo(question =
            "The configuation " + selectedFile + " will be deleted. Are you sure?")
        if answer:  # If True
            print ('Removing configuration: ' + selectedFile)
            try:
                # Remove the config file from the system directory, containing
                # containing all config files
                os.remove(selectedFile)
                # Remove the config file from the list
                self.parent.listBox1.Delete(pos)
                # Refresh the list
                self.parent.configurationFilesList = \
                    GlobalOperations.getConfFilesList(configType='pcfg')
            except OSError:
                print ("Unable to remove file: " + selectedFile)

class PlotConfigurationListsTab(wx.Panel):
    """The configuration tab panel, listing the available plot configuration
       files and its features.
    """
    def __init__(self, parent, DTV):
        wx.Panel.__init__(self, name='', parent=parent,
                          pos=wx.DefaultPosition, size=wx.DefaultSize,
                          style=wx.DEFAULT_FRAME_STYLE|wx.LB_SINGLE)
        self.parent = parent
        self.DTV = DTV
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.configurationFilesList = None
        self.createList()
        commonConf = CommonConfigurationRoutines(self)

        # Set buttons
        # - 'Apply configuration to current shot' button
        #   - Next button ID
        MultiPlotButtonId = wx.NewId()
        #   - Create button
        apply_MultiPlot_button = wx.Button(self, MultiPlotButtonId,
                                 'Apply configuration to current shot')
        #   - Add the button to BoxSizer
        self.vbox.Add(apply_MultiPlot_button, 0, wx.ALL|wx.EXPAND, 5)
        #   - Bind the 'apply_MultiPlot' feature to the button
        self.Bind(wx.EVT_BUTTON, self.apply_MultiPlot, id=MultiPlotButtonId)

        # - 'Apply data selection only from selected configuration to current
        #    shot' button
        #   - Next button ID
        signalSelectButtonId = wx.NewId()
        #   - Create button
        signalSelect_button = wx.Button(self, signalSelectButtonId,
            'Apply only data selection from selected\n '
            '       configuration to current shot',
            size=(100,40))
        #   - Add the button to BoxSizer
        self.vbox.Add(signalSelect_button, 0, wx.ALL | wx.EXPAND, 5)
        #   - Bind the 'Apply_Signal_Selection' feature to the button
        self.Bind(wx.EVT_BUTTON, commonConf.Apply_Signal_Selection,
                  id=signalSelectButtonId)

        # - 'Remove configuration' button
        #   - Next button ID
        removeButtonId = wx.NewId()
        #   - Create button
        remove_button = wx.Button(self, removeButtonId, 'Remove configuration')
        #   - Add the button to BoxSizer
        self.vbox.Add(remove_button, 0, wx.ALL | wx.EXPAND, 5)
        #   - Bind 'removeConfiguration' feature to the button
        self.Bind(wx.EVT_BUTTON, commonConf.removeConfiguration, id=removeButtonId)

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
        note_3 = self.DTV.GetTitle()
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
        #    GlobalOperations.getConfFilesList(configType='pcfg')
        # for f in self.configurationFilesList:
        #     self.listBox1.Append(f)
        self.vbox.Add(self.listBox1 , 0, wx.ALL|wx.EXPAND, 5)

        self.update()

    def showListBox(self):
        self.Show(True)

    def update(self):
        self.listBox1.Clear()
        self.configurationFilesList = \
            GlobalOperations.getConfFilesList(configType='pcfg')
        for f in self.configurationFilesList:
            self.listBox1.Append(f)

    def apply_MultiPlot(self, event):
        """Apply signal selection from the config file - apply it directly
           to MultiPlot feature.
        """
        # Get in-list position of the selection (config file name)
        pos = self.listBox1.GetSelection()
        # Get system path to the selected configuration file
        selectedFile = \
            GlobalOperations.getConfigurationFilesDirectory() + \
            "/" + self.configurationFilesList[pos]
        # Get next figurekey (label) for the MultiPlot
        figurekey = \
            self.DTV.wxTreeView.imas_viz_api.GetNextKeyForMultiplePlots()
        # Set up and show the MultiPlot using the config file
        PlotSelectedSignalsWithWxmplot(self.DTV.wxTreeView,
                                       figurekey=figurekey,
                                       update=0,
                                       configFile=selectedFile).execute()

class ListOfSignalPathsListsTab(wx.Panel):
    """The configuration tab panel, listing the available lists of signal paths
       files and its features.
    """
    def __init__(self, parent, DTV):
        wx.Panel.__init__(self, name='', parent=parent,
                          pos=wx.DefaultPosition, size=wx.DefaultSize,
                          style=wx.DEFAULT_FRAME_STYLE|wx.LB_SINGLE)
        self.parent = parent
        self.DTV = DTV
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.configurationFilesList = None
        self.createList()
        commonConf = CommonConfigurationRoutines(self)

        # Set buttons
        # - 'Apply list of IDS paths selection to current shot' button
        #   - Next button ID
        signalSelectButtonId = wx.NewId()
        #   - Create button
        signalSelect_button = wx.Button(self, signalSelectButtonId,
            'Apply list of IDS paths from selected\n '
            '       file to current shot',
            size=(100,40))
        #   - Add the button to BoxSizer
        self.vbox.Add(signalSelect_button, 0, wx.ALL | wx.EXPAND, 5)
        #   - Bind the 'Apply_Signal_Selection' feature to the button
        self.Bind(wx.EVT_BUTTON, commonConf.Apply_Signal_Selection,
                  id=signalSelectButtonId)

        # - 'Remove configuration' button
        #   - Next button ID
        removeButtonId = wx.NewId()
        #   - Create button
        remove_button = wx.Button(self, removeButtonId, 'Remove configuration')
        #   - Add the button to BoxSizer
        self.vbox.Add(remove_button, 0, wx.ALL | wx.EXPAND, 5)
        #   - Bind 'removeConfiguration' feature to the button
        self.Bind(wx.EVT_BUTTON, commonConf.removeConfiguration, id=removeButtonId)

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
        note_3 = self.DTV.GetTitle()
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
        #    GlobalOperations.getConfFilesList(configType='lsp')
        # for f in self.configurationFilesList:
        #     self.listBox1.Append(f)
        self.vbox.Add(self.listBox1 , 0, wx.ALL|wx.EXPAND, 5)

        self.update()

    def showListBox(self):
        self.Show(True)

    def update(self):
        self.listBox1.Clear()
        self.configurationFilesList = \
            GlobalOperations.getConfFilesList(configType='lsp')
        for f in self.configurationFilesList:
            self.listBox1.Append(f)
