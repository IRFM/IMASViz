import wx
from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.gui_commands.plot_commands.PlotSignal import PlotSignal
from wxmplot import StackedPlotFrame
from imasviz.plotframes.IMASVIZ_StackedPlotFrame import StackedPlotFrame
import numpy

class SubPlotsManagerFrame(wx.Frame):
    def __init__(self, title, dataTree):
        wx.Frame.__init__(self, None, 1, title=title)

        """Set panel background colour"""
        self.SetBackgroundColour((204, 229, 255))

        self.dataTree = dataTree
        selectedSignals = self.dataTree.selectedSignals

        x = setNumberOfSubplots(message = 'Set number of required subplots:',
            default_value = str(len(selectedSignals)))
        self.subplotsCount = int(x)

        self.SetSize(400, (self.subplotsCount)*50 + 100)

        signalsCount = len(selectedSignals)
        button_open = wx.Button(self, 1, 'Open subplots', style = wx.BU_LEFT)
        signalNodeDataValueIterator = selectedSignals.values()
        self.signals_list = []

        iterSignalNodeDataValueIterator = iter(signalNodeDataValueIterator)

        for i in range(signalsCount):
            signalNodeDataValue = next(iterSignalNodeDataValueIterator)
            signalNodeData = signalNodeDataValue[1]
            # dataName = signalNodeData["dataName"]
            self.signals_list.append(signalNodeData)

        vbox = wx.BoxSizer(wx.VERTICAL)
        self.buildList(vbox)
        vbox.Add(button_open, 0, wx.LEFT | wx.TOP | wx.BOTTOM, 5)
        self.Bind(wx.EVT_BUTTON, self.showSubPlots)
        self.SetSizer(vbox)

    def buildList(self, vbox):
        self.label = []
        self.space = []
        self.combos = []
        self.indexList = []
        self.selectedIndex = {}
        i = 0

        indexList = []

        for i in range(self.subplotsCount):
            """Set text to be used within ComboBox widget (list of options to
            choose from)
            """
            indexList.append("subplot : " + str(i+1))
            i = i + 1

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
        for signal in self.signals_list:
            hbox = wx.BoxSizer(wx.HORIZONTAL)
            dataName = signal["Path"]

            print(dataName)

            """Add signal item label"""
            self.label.append(wx.StaticText(self, -1, str(j+1) + ". " + dataName))
            """Add space"""
            self.space.append(wx.StaticText(self, -1, " "))
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

            hbox.Add(self.label[j], 1, wx.EXPAND | wx.ALL, 4)
            hbox.Add(self.space[j], 1, wx.EXPAND | wx.ALL)
            hbox.Add(self.combos[j], 1, wx.EXPAND| wx.ALL,5)

            vbox.Add(hbox, 0, wx.TOP, 5)
            j = j + 1
        # print (self.selectedIndex)


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
                signals[key].append(self.signals_list[item])
        return signals

    def showSubPlots(self, evt):
        #api = self.dataTree.imas_viz_api
        signals = self.getSignals()
        print (self.selectedIndex)
        print (signals)
        from imasviz.subplots.SubPlot import SubPlot
        from imasviz.subplots.SubplotsShareXFrame import SubPlotsShareXFrame

        #signalHandling = SignalHandling(self.dataTree)
        subPlotsList = []

        """Set default x axis min and max values"""
        x_min = 0
        x_max = 0

        """Set array for x and y axis values"""
        xt = []
        yv = []

        for key in self.selectedIndex:
            for signalNodeData in signals[key]:
                # print 'dataName : ' + signalNodeData['dataName']
                s = PlotSignal.getSignal(self.dataTree, signalNodeData)
                t = PlotSignal.getTime(s)
                v = PlotSignal.get1DSignalValue(s)
                # label, xlabel, ylabel, title = \
                #     PlotSignal.plotOptions(self.dataTree, signalNodeData,
                #                            self.dataTree.dataSource.shotNumber)
                # sp = SubPlot(t, v, subplot_number = key, scatter = False,
                #              legend = label)
                # subPlotsList.append(sp)

                """Add the array of values to array list"""
                xt.append(t[0])
                yv.append(v[0])

                """Get/Update minimum and maximum x-axis value"""
                if min(t[0]) < x_min:
                    x_min = min(t[0])
                if max(t[0]) > x_max:
                    x_max = max(t[0])

        """Set the frame for multiple plots. Ratio= top vs bottom panel size
        ratio
        """
        pframe = StackedPlotFrame(title='SubPlotManager',
                                  numPlots = len(self.selectedIndex))

        for key in self.selectedIndex:
            for signalNodeData in signals[key]:
                label, xlabel, ylabel, title = \
                    PlotSignal.plotOptions(self.dataTree, signalNodeData,
                                           self.dataTree.dataSource.shotNumber)
                """Set panel name for IMASVIZ_StacketPlotFrame pframe function
                """
                if key == len(self.selectedIndex) - 1:
                    pname = 'panel_last'
                else:
                    pname = 'panel' + str(key)
                """Add plot to subplot manager"""
                pframe.plot(xt[key], yv[key], panel=pname, label=label,
                            xlabel=xlabel, ylabel=ylabel, title=title,
                            show_legend=True, xmin=x_min, xmax=x_max)

        # The previous subplotmanager.
        # TODO: Review the 'Keep this subplot' button event and 'Set plot style'
        #       menu option (ocated in SubPlotsShareXFrame)
        #       if they might be useful with the new SubPlotManager,
        #       done with the help of imasviz StackedPlotFrame feature
        # frame = SubPlotsShareXFrame(None, "SubPlots", subPlotsList,
        #                             self.subplotsCount, 0.1)
        # frame.imas_viz_api = self.dataTree.imas_viz_api
        # frame.Show()

        pframe.Show()
        pframe.Raise()


def setNumberOfSubplots(parent=None, message='', default_value=''):
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
