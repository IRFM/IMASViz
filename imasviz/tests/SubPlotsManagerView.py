import wx
from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.gui_commands.plot_commands.PlotSignal import PlotSignal

class SubPlotsManagerFrame(wx.Frame):
    def __init__(self, title, dataTree):
        wx.Frame.__init__(self, None, 1, title=title)
        self.dataTree = dataTree
        selectedSignals = self.dataTree.selectedSignals

        x = ask(message='Number of desired subplots?', default_value=str(len(selectedSignals)))
        self.subplotsCount = int(x)

        signalsCount = len(selectedSignals)
        button_open = wx.Button(self, 1, 'Open subplots')
        signalNodeDataValueIterator = selectedSignals.itervalues()
        self.signals_list = []

        for i in range(signalsCount):
            signalNodeDataValue = signalNodeDataValueIterator.next()
            signalNodeData = signalNodeDataValue[1]
            # dataName = signalNodeData["dataName"]
            self.signals_list.append(signalNodeData)

        vbox = wx.BoxSizer(wx.VERTICAL)
        self.buildList(vbox)
        vbox.Add(button_open, 0, wx.ALIGN_LEFT | wx.TOP | wx.BOTTOM, 20)
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
            indexList.append("subplot : " + str(i))
            i = i + 1

        hbox_title = wx.BoxSizer(wx.HORIZONTAL)
        hbox_title.Add(wx.StaticText(self, -1, "Signal"))
        hbox_title.Add(wx.StaticText(self, -1, "                        "))
        hbox_title.Add(wx.StaticText(self, -1, "Subplot"))

        vbox.Add(hbox_title, 0, wx.TOP, 5)

        j = 0
        for signal in self.signals_list:
            hbox = wx.BoxSizer(wx.HORIZONTAL)
            dataName = signal["Path"]
            self.label.append(wx.StaticText(self, -1, dataName))
            self.space.append(wx.StaticText(self, -1, " "))
            self.combos.append(wx.ComboBox(self, id = j, style=wx.CB_READONLY, choices=indexList))
            self.combos[j].SetSelection(j)

            self.combos[j].Bind(wx.EVT_COMBOBOX, self.OnCombo)
            list = []

            if j < self.subplotsCount:
                list.append(j)
                self.selectedIndex[j] = list #each subplot contains only one signal at the beginning

            hbox.Add(self.label[j], 1, wx.EXPAND | wx.ALL)
            hbox.Add(self.space[j], 1, wx.EXPAND | wx.ALL)
            hbox.Add(self.combos[j], 1, wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL|wx.ALL,5)

            vbox.Add(hbox, 0, wx.TOP, 5)
            j = j + 1
        print self.selectedIndex


    def OnCombo(self, event):
       index = event.GetId()
       selected_combo = self.combos[index]
       selection =  selected_combo.GetSelection()

       if (index not in self.selectedIndex[selection]):
           print 'OK'
           self.selectedIndex[selection].append(index)

       for key in self.selectedIndex:
           if key == selection:
               continue
           if index in self.selectedIndex[key]:
                self.selectedIndex[key].remove(index)
       print self.selectedIndex

    def getSignals(self):
        signals = {} #key = subplot number, value = list of signals in the subplot
        for key in self.selectedIndex:
            signals[key] = []
            for item in self.selectedIndex[key]:
                signals[key].append(self.signals_list[item])
        return signals

    def showSubPlots(self, evt):
        #api = self.dataTree.imas_viz_api
        signals = self.getSignals()
        print self.selectedIndex
        print signals
        from imasviz.subplots.SubPlot import SubPlot
        from imasviz.subplots.SubplotsShareXFrame import SubPlotsShareXFrame

        #signalHandling = SignalHandling(self.dataTree)
        subPlotsList = []

        for key in self.selectedIndex:
            for signalNodeData in signals[key]:
                # print 'dataName : ' + signalNodeData['dataName']
                s = PlotSignal.getSignal(self.dataTree, signalNodeData)
                t = PlotSignal.getTime(s)
                v = PlotSignal.get1DSignalValue(s)
                label, xlabel, ylabel, title = PlotSignal.plotOptions(self.dataTree, signalNodeData, self.dataTree.dataSource.shotNumber)
                sp = SubPlot(t, v, subplot_number=key, scatter=False, legend=label)
                subPlotsList.append(sp)

        frame = SubPlotsShareXFrame(None, "SubPlots", subPlotsList, self.subplotsCount, 0.1)
        #frame.subplots_manager = self
        frame.imas_viz_api = self.dataTree.imas_viz_api
        frame.Show()


def ask(parent=None, message='', default_value=''):
    dlg = wx.TextEntryDialog(parent, message, value=default_value,  style=wx.OK)
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
    dataSource = dataSourceFactory.create(name=GlobalValues.TORE_SUPRA, shotNumber=47979)
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
