import wx
from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.gui_commands.plot_commands.PlotSignal import PlotSignal
# from wxmplot import StackedPlotFrame
from imasviz.plotframes.IMASVIZ_SubPlotManagerBaseFrame import SubPlotManagerBaseFrame
import numpy
from wxmplot.utils import MenuItem

class SubPlotsManagerFrame(wx.Frame):
    def __init__(self, title, WxDataTreeView):
        wx.Frame.__init__(self, None, 1, title=title)

        """Set panel background colour"""
        self.SetBackgroundColour((204, 229, 255))

        """WxDataTreeView"""
        self.WxDataTreeView = WxDataTreeView
        """Browser_API"""
        self.api = self.WxDataTreeView.imas_viz_api

        """Total number of existing WxDataTreeViews"""
        self.num_DTVs = len(self.api.wxDTVlist)

        """Total number of selected signals (all DTVs)"""
        self.num_selectedSignals_all_dtv = \
            len(self.api.GetSelectedSignals_AllDTVs())

        """Set list of signals and their 'source' DTV"""
        self.setSelectedSignalsList()

        """Get number of signals == number of subplots"""
        signalCount = len(self.selectedSignalsList_allDTVs)
        """Run dialog to set number of subplots"""
        x = self.setNumberOfSubplots(message = 'Set number of required subplots:',
            default_value = str(signalCount))
        self.subplotsCount = int(x)

        """Set and open SuvPlotManager signals list window"""
        self.setSubPlotManagerSignalsListWindow()

        # self.BuildMenu()

    def setSelectedSignalsList(self):
        """Set a list of signals and the DTV where each signal was selected"""
        """self.selectedSignalsList_allDTVs[i][0] ... i-th signal
           self.selectedSignalsList_allDTVs[i][1] ... source DTV of the i-th
                                                      signal
        """
        self.selectedSignalsList_allDTVs = []
        for dtv in self.api.wxDTVlist:
            """Get list of selected signals in DTV"""
            dtv_sortedSignals = GlobalOperations.getSortedSelectedSignals( \
                dtv.selectedSignals)
            for element in dtv_sortedSignals:
                """Get node data
                   element[0] = shot number,
                   element[1] = node data
                   element[2] = index,
                   element[3] = shot number,
                   element[3] = IDS database name,
                   element[4] = user name
                """
                """Add the signal node data and dtv to list"""
                self.selectedSignalsList_allDTVs.append((element[1], dtv))

    def setSubPlotManagerSignalsListWindow(self):
        """Set window size"""
        self.SetSize(400, (self.subplotsCount)*42 + 120)
        """Create BoxSizer"""
        vbox = wx.BoxSizer(wx.VERTICAL)
        """Add list of signals"""
        self.buildList(vbox)
        """Create and add 'Open' button"""
        button_open = wx.Button(self, 1, 'Open subplots', style = wx.BU_LEFT)
        vbox.Add(button_open, 0, wx.LEFT | wx.TOP | wx.BOTTOM, 5)
        self.Bind(wx.EVT_BUTTON, self.showSubPlots)
        self.SetSizer(vbox)

    def buildList(self, vbox):
        label = []
        space = []
        self.combos = []
        self.selectedIndex = {}

        indexList = []
        for i in range(self.subplotsCount):
            """Set text to be used within ComboBox widget (list of options to
            choose from)
            """
            indexList.append("subplot : " + str(i+1))

        """Set BoxSizer"""
        hbox_title = wx.BoxSizer(wx.HORIZONTAL)
        """Set the signal and subplot statictext"""
        stext_signal = wx.StaticText(self, -1, "Signal")
        stext_subplot = wx.StaticText(self, -1, "Subplot")
        """Set font of the statictexts"""
        font_label = wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD)
        stext_signal.SetFont(font_label)
        stext_subplot.SetFont(font_label)

        """Add all static text to BoxSizer (add space (static line) between both
        static texts
        """
        hbox_title.Add(stext_signal, 0, wx.LEFT, 4)
        hbox_title.Add(wx.StaticLine(self, -1, size=(220, 0)), 0, wx.ALL, 5)
        hbox_title.Add(stext_subplot, 0, wx.LEFT, 0)

        vbox.Add(hbox_title, 0, wx.TOP, 5)

        j = 0
        # for signal in self.signals_list:
        for signalInfo in self.selectedSignalsList_allDTVs:
            hbox = wx.BoxSizer(wx.HORIZONTAL)
            """Get signal path"""
            dataName = signalInfo[0]["Path"]
            """Get signal DTV source"""
            signal_dtv = signalInfo[1]

            """Add signal item label"""
            label.append(wx.StaticText(self, -1,
                '{}. Shot: {} Run: {} \n    Path: {}'.format(
                j+1, signalInfo[1].shotNumber, signalInfo[1].runNumber, dataName)))
            """Add space"""
            space.append(wx.StaticText(self, -1, " "))
            """Add ComboBox"""
            self.combos.append(wx.ComboBox(self, id = j, style = wx.CB_READONLY,
                                           choices = indexList))
            self.combos[j].SetSelection(j)

            self.combos[j].Bind(wx.EVT_COMBOBOX, self.OnCombo)
            list = []

            if j < self.subplotsCount:
                list.append(j)
                self.selectedIndex[j] = list # each subplot contains only one
                                             # signal at the beginning
            """Add to BoxSizer"""
            hbox.Add(label[j], 1, wx.EXPAND | wx.ALL, 4)
            hbox.Add(space[j], 1, wx.EXPAND | wx.ALL)
            hbox.Add(self.combos[j], 1, wx.EXPAND| wx.ALL,5)

            vbox.Add(hbox, 0, wx.TOP, 5)
            j = j + 1


    def OnCombo(self, event):
       index = event.GetId()
       selected_combo = self.combos[index]
       selection =  selected_combo.GetSelection()

       if (index not in self.selectedIndex[selection]):
           print ('OK')
           self.selectedIndex[selection].append(index)

       for key in self.selectedIndex:
           if key == selection:
               continue
           if index in self.selectedIndex[key]:
                self.selectedIndex[key].remove(index)
       print (self.selectedIndex)

    def getSignals(self):
        signals = {} # key = subplot number, value = list of signals in the
                     # subplot
        for key in self.selectedIndex:
            signals[key] = []
            for item in self.selectedIndex[key]:
                # signals[key].append(self.signals_list[item])
                signals[key].append(self.selectedSignalsList_allDTVs[item])
        return signals

    def showSubPlots(self, evt):
        from imasviz.subplots.SubPlot import SubPlot
        from imasviz.subplots.SubplotsShareXFrame import SubPlotsShareXFrame
        signals = self.getSignals()

        """Set default x axis min and max values for subplots"""
        x_min = 0
        x_max = 0

        """Set empty array for x and y axis values"""
        xt = []
        yv = []

        for key in self.selectedIndex:
            for signalInfo in signals[key]:
                s = PlotSignal.getSignal(signalInfo[1], signalInfo[0])
                """signalInfo[0] ... node data
                   signalInfo[1] ... WxDataTreeView (DTV where the signal
                                     (node data) was selected)
                """
                """Get x-axis values (time)"""
                t = PlotSignal.getTime(s)
                """Get y-axis values"""
                v = PlotSignal.get1DSignalValue(s)

                """Add the obtained array of values to array list"""
                xt.append(t[0])
                yv.append(v[0])

                """Get/Update minimum and maximum x-axis value"""
                if min(t[0]) < x_min:
                    x_min = min(t[0])
                if max(t[0]) > x_max:
                    x_max = max(t[0])

        figurekey = self.api.GetNextKeyForSubPlots()

        """Set the frame for holding n number of subplots."""
        pframe = SubPlotManagerBaseFrame(title=figurekey,
                                  numPlots = len(self.selectedIndex))

        """Set the pframe (SubPlot window) to figurekey list.
           This enables the SubPlot to be reopened in the same session after
           it was closed (if it was not destroyed).
        """
        self.api.figureframes[figurekey] = pframe

        """Set all selected subplots to SubPlot window"""
        for key in self.selectedIndex:
            for signalInfo in signals[key]:
                """signalInfo[0] ... node data
                   signalInfo[1] ... WxDataTreeView (DTV where the signal
                                     (node data) was selected)
                """
                """Get subplot labels and title"""
                label, xlabel, ylabel, title = \
                    PlotSignal.plotOptions(signalInfo[1], signalInfo[0],
                                           signalInfo[1].dataSource.shotNumber)
                """Set panel name for IMASVIZ_StacketPlotFrame plot function
                """
                if key == len(self.selectedIndex) - 1:
                    pname = 'panel_last'
                else:
                    pname = 'panel' + str(key)
                """Add subplot to SubPlot manager"""
                pframe.plot(xt[key], yv[key], panel=pname, label=label,
                            xlabel=xlabel, ylabel=ylabel, title=title,
                            show_legend=True, xmin=x_min, xmax=x_max)

        """Show the SubPlot window"""
        pframe.Show()
        pframe.Raise()

    def BuildMenu(self):
        """Set menu bar for SubPlot Manager plot signals list window"""
        mbar = wx.MenuBar()

        """Set first menu"""
        menu_1 = wx.Menu()

        """Set menu item for saving subplot configuration"""
        MenuItem(self, menu_1, "Save configuration",
                 "Save SubPlot manager configuration",
                 self.SaveSubPlotConfiguration)

        """Append the menu to menu bar"""
        mbar.Append(menu_1, "Options")

        """Activate the menu bar"""
        self.SetMenuBar(mbar)

    # def SaveSubPlotConfiguration(self, event=None):
    #     """Save SubPlot configuration """

    #     """Save plot signals"""
    #     self.conf_signals = self.getSignals()

    def setNumberOfSubplots(self, parent=None, message='', default_value=''):
        dlg = wx.TextEntryDialog(parent, message,
                                 caption = "SubPlots Manager - Input",
                                 value = default_value, style = wx.OK)
        dlg.ShowModal()
        result = dlg.GetValue()
        dlg.Destroy()
        return result

import os

if __name__ == "__main__":

    app = wx.App()

    GlobalOperations.checkEnvSettings()

    from imasviz.data_source.DataSourceFactory import DataSourceFactory

    dataSourceFactory = DataSourceFactory()
    dataSource = dataSourceFactory.create(name = GlobalValues.TORE_SUPRA,
        shotNumber = 47979)
    from imasviz.Browser_API import Browser_API
    api = Browser_API()
    frame = api.CreateDataTree(dataSource)

    selectedSignals = {}
    nodeData1 = {}
    nodeData1['dataName'] = "SIPMES"
    nodeData2 = {}
    nodeData2['dataName'] = "SFDIAM"
    nodeData3 = {}
    nodeData3['dataName'] = "SIPMES"
    nodeData4 = {}
    nodeData4['dataName'] = "SIPMES"
    selectedNodeData1 = (47979, nodeData1)
    selectedNodeData2 = (47978, nodeData2)
    selectedNodeData3 = (47977, nodeData3)
    selectedNodeData4 = (47976, nodeData4)
    selectedSignals["47979:SIPMES"] = selectedNodeData1
    nodeData1['Path'] = "47979:SIPMES"
    selectedSignals["47978:SFDIAM"] = selectedNodeData2
    nodeData2['Path'] = "47978:SFDIAM"
    #selectedSignals["47977:SIPMES"] = selectedNodeData3
    nodeData3['Path'] = "47977:SIPMES"
    #selectedSignals["47976:SIPMES"] = selectedNodeData4
    nodeData4['Path'] = "47976:SIPMES"
    frame.wxTreeView.selectedSignals = selectedSignals


    spm = SubPlotsManagerFrame("Subplots manager", frame.wxTreeView)
    spm.Show()
    app.MainLoop()
