import wx

from imasviz.signals_data_access.SignalDataAccessFactory import SignalDataAccessFactory
from imasviz.gui_commands.select_commands.SelectOrUnselectSignal import SelectOrUnselectSignal
from imasviz.gui_commands.select_commands.UnselectAllSignals import UnselectAllSignals
from imasviz.gui_commands.plot_commands.PlotSignal import PlotSignal
from imasviz.gui_commands.plot_commands.PlotSelectedSignals import PlotSelectedSignals
from imasviz.gui_commands.plot_commands.PlotSelectedSignalsWithWxmplot import PlotSelectedSignalsWithWxmplot
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.view.Coord1Slider import Coord1Slider


class MenuIDS:
    def __init__(self):
        self.ID_ADD_PLOT_TO_FIGURE = 100
        self.ID_ADD_PLOT_TO_EXISTING_FIGURE = 150 #wx.NewId()
        self.ID_SELECT_OR_UNSELECT_SIGNAL = 200
        self.ID_SHOW_HIDE_FIGURES  = 300
        self.ID_SHOW_HIDE_SUBPLOTS = 400
        self.ID_PLOT_ALL_SELECTED_SIGNALS_TO_FIGURE = 500
        self.ID_PLOT_AS_ITIME = 600
        self.ID_PLOT_SELECTED_SIGNALS_TO_NEW_FIGURE = 700
        self.ID_PLOT_SELECTED_SIGNALS_TO_MULTIPLOTFRAME = 750
        self.ID_OPEN_SUBPLOTS_MANAGER = 800
        self.ID_CHANGE_COORD1 = 900

class SignalHandling:
    
    def __init__(self, view):
        self.view = view
        self.menuIDS = MenuIDS()
        self.CHANGE_COORD1 = wx.NewId()
        self.CHANGE_TIME1  = wx.NewId()
        self.plotFrame = None
        self.currentNumFig = None
        self.nodeData = None
        if self.view.selectedItem != None:
            self.nodeData = self.view.GetItemData(self.view.selectedItem)
        self.treeNode = None    
        if self.nodeData != None:
            self.treeNode = self.view.getNodeAttributes(self.nodeData['dataName'])

        self.timeSlider = None

    def updateNodeData(self):
        self.nodeData = self.view.GetItemData(self.view.selectedItem)
        self.treeNode = self.view.getNodeAttributes(self.nodeData['dataName'])
        
    # Display the menu for plotting data
    def showPopUpMenu(self, signalName, numfig=0):

        if (signalName == None): return 0

        self.view.popupmenu = wx.Menu()
        s = ''
        
        # If the node is unselected, show unselect menu
        if self.nodeData['isSelected'] == 1:
            s = 'Unselect '

        # If the node is selected, show select menu
        else:
            s = 'Select '

        item1 = wx.MenuItem(self.view.popupmenu, self.menuIDS.ID_SELECT_OR_UNSELECT_SIGNAL, text= s + signalName + '...', kind=wx.ITEM_NORMAL)
        #item2 = wx.MenuItem(self.view.popupmenu, wx.ID_MORE, item='Show '+signalName+' size', kind=wx.ITEM_NORMAL)
        item3 = None
        if len(self.view.imas_viz_api.figures)==0: #if there is no figure
            item3 = wx.MenuItem(self.view.popupmenu, self.menuIDS.ID_ADD_PLOT_TO_FIGURE, text='Plot ' + signalName, kind=wx.ITEM_NORMAL)
        else:
            item3 = wx.MenuItem(self.view.popupmenu, self.menuIDS.ID_ADD_PLOT_TO_FIGURE, text='Plot ' + signalName + ' to new figure', kind=wx.ITEM_NORMAL)

            subMenu = wx.Menu()
            self.view.popupmenu.Append(wx.ID_ANY, 'Add plot to existing figure', subMenu)
            for i in range(0, len(self.view.imas_viz_api.figures)):
                if self.shareSameCoordinatesFrom(i):
                    subMenu.Append(self.menuIDS.ID_ADD_PLOT_TO_EXISTING_FIGURE + i, item= 'Figure '+str(i+1), kind=wx.ITEM_NORMAL)

        if len (self.view.imas_viz_api.figures) > 0:

            showMenu = wx.Menu()
            self.view.popupmenu.Append(wx.ID_ANY, 'Show/Hide figure', showMenu)
            for i in range(0, len(self.view.imas_viz_api.figures)):
                showMenu.Append(self.menuIDS.ID_SHOW_HIDE_FIGURES + i, item='Figure ' + str(i + 1), kind=wx.ITEM_NORMAL)

        if len(self.view.imas_viz_api.subplots) > 0:

            showMenu = wx.Menu()
            self.view.popupmenu.Append(wx.ID_ANY, 'Show/Hide subplots', showMenu)
            i = 0
            for key in self.view.imas_viz_api.subplots:
                showMenu.Append(self.menuIDS.ID_SHOW_HIDE_SUBPLOTS + i, item=key, kind=wx.ITEM_NORMAL)
                i = i + 1

        if len (self.view.imas_viz_api.figures) > 0 \
                and len(self.view.selectedSignals) > 0\
                and self.shareSameCoordinates(self.view.selectedSignals):

            showMenu = wx.Menu()
            self.view.popupmenu.Append(wx.ID_ANY, 'Plot all selected signals to', showMenu)
            for i in range(0, len(self.view.imas_viz_api.figures)):
                showMenu.Append(self.menuIDS.ID_PLOT_ALL_SELECTED_SIGNALS_TO_FIGURE + i, item='Figure ' + str(i + 1), kind=wx.ITEM_NORMAL)


        item4 = wx.MenuItem(self.view.popupmenu, self.menuIDS.ID_PLOT_SELECTED_SIGNALS_TO_NEW_FIGURE, text='Plot all selected signals to a new figure',
                                kind=wx.ITEM_NORMAL)

        item5 = wx.MenuItem(self.view.popupmenu, wx.ID_CANCEL, text='Unselect all signals',
                            kind=wx.ITEM_NORMAL)

        item6 = wx.MenuItem(self.view.popupmenu, self.menuIDS.ID_OPEN_SUBPLOTS_MANAGER, text='Open subplots manager',
                            kind=wx.ITEM_NORMAL)

        item7 = wx.MenuItem(self.view.popupmenu, self.menuIDS.ID_PLOT_AS_ITIME, text='Plot ' + signalName + ' as a function of time',
                            kind=wx.ITEM_NORMAL)

        item8 = wx.MenuItem(self.view.popupmenu, self.menuIDS.ID_PLOT_SELECTED_SIGNALS_TO_MULTIPLOTFRAME,
                            text='Plot all selected signals to a multiplots frame',
                            kind=wx.ITEM_NORMAL)

        self.view.popupmenu.Append(item1)
        #self.view.popupmenu.Append(item2)
        self.view.popupmenu.Append(item3)

        if len(self.view.selectedSignals) > 0:
            if self.shareSameCoordinates(self.view.selectedSignals):
                self.view.popupmenu.Append(item4)
            self.view.popupmenu.Append(item5)
            self.view.popupmenu.Append(item8)

        if len(self.view.selectedSignals) > 1:
            self.view.popupmenu.Append(item6)

        treeNode = self.view.getNodeAttributes(self.nodeData['dataName'])
        if treeNode != None and treeNode.time_dependent(treeNode.aos):
            self.view.popupmenu.Append(item7)

        self.view.Bind(wx.EVT_MENU, self.popUpMenuHandler)
        return 1

    

    def popUpMenuHandler(self, event):
        if event.GetId() == wx.ID_MORE:
            self.signalSizeRequest(event)
        elif event.GetId() == self.menuIDS.ID_ADD_PLOT_TO_FIGURE:
            self.plotSignalCommand(event)
        elif event.GetId() == self.menuIDS.ID_SELECT_OR_UNSELECT_SIGNAL:
            self.selectOrUnselectSignal(event)  # selection
        elif event.GetId() == self.menuIDS.ID_PLOT_SELECTED_SIGNALS_TO_NEW_FIGURE:
            self.plotSelectedSignals()
        elif event.GetId() == self.menuIDS.ID_PLOT_SELECTED_SIGNALS_TO_MULTIPLOTFRAME:
            self.plotSelectedSignalsToMultiPlotsFrame()
        elif event.GetId() == wx.ID_CANCEL:
            self.unselectAllSignals()
        elif event.GetId() == self.menuIDS.ID_OPEN_SUBPLOTS_MANAGER:
            self.showSubPlotsManager()
        elif event.GetId() == self.menuIDS.ID_PLOT_AS_ITIME:
            self.plotSelectedSignalVsTime()
        else:
            for i in range(0, len(self.view.imas_viz_api.figures)):
                if event.GetId() == i + self.menuIDS.ID_ADD_PLOT_TO_EXISTING_FIGURE:
                    self.addSignalPlotToFig(i)
                elif event.GetId() == i + self.menuIDS.ID_SHOW_HIDE_FIGURES:
                    self.hideShowfigure(i)
                elif event.GetId() == i + self.menuIDS.ID_PLOT_ALL_SELECTED_SIGNALS_TO_FIGURE:
                    self.plotSelectedSignalsToFig(i)

            for i in range(0, len(self.view.imas_viz_api.subplots)):
                if event.GetId() == i + self.menuIDS.ID_SHOW_HIDE_SUBPLOTS:
                    key = self.view.imas_viz_api.subplots.keys()[i]
                    self.view.imas_viz_api.HideShowSubplots(key)


    def selectSignal(self):
        SelectOrUnselectSignal(self.view, self.nodeData).execute()

    def selectOrUnselectSignal(self, event):
        SelectOrUnselectSignal(self.view, self.nodeData).execute()

    def unselectAllSignals(self):
        UnselectAllSignals(self.view, self.nodeData).execute()

    def plotSignalCommand(self, event):
        try:
            self.currentNumFig = self.view.imas_viz_api.GetNextNumFigForNewPlot()
            treeNode = self.view.getNodeAttributes(self.nodeData['dataName'])
            if treeNode.time_dependent_aos():
                self.timeSlider = True
            else:
                self.timeSlider = None
            p = PlotSignal(self.view, self.nodeData, signal=None, numfig=self.currentNumFig, signalHandling=self)
            p.execute()

        except ValueError as e:
            self.view.log.error(str(e))
        
    def plotSelectedSignals(self):
        selectedsignals = self.view.selectedSignals
        numFig = self.view.imas_viz_api.GetNextNumFigForNewPlot()
        PlotSelectedSignals(self.view, selectedsignals, numFig).execute()

    def plotSelectedSignalsToFig(self, numFig):
        selectedsignals = self.view.selectedSignals
        PlotSelectedSignals(self.view, selectedsignals, numFig, 1).execute()

    def plotSelectedSignalsToMultiPlotsFrame(self):
        selectedsignals = self.view.selectedSignals
        numFig = self.view.imas_viz_api.GetNextNumFigForNewPlot()
        PlotSelectedSignalsWithWxmplot(self.view, selectedsignals, numFig, 1).execute()

    def plotSelectedSignalVsTime(self):
        self.updateNodeData();
        treeNode = self.view.getNodeAttributes(self.nodeData['dataName'])
        index = 0
        data_path_list = treeNode.getDataVsTime()
        signalDataAccess = SignalDataAccessFactory(self.view.dataSource).create()
        signal = signalDataAccess.GetSignalVsTime(data_path_list, self.nodeData, treeNode, index)
        label = treeNode.coordinate1Label(self.nodeData['IDSName'], index, self.view.dataSource.ids)
        self.currentNumFig = self.view.imas_viz_api.GetNextNumFigForNewPlot()
        self.treeNode = treeNode
        self.timeSlider = False
        p = PlotSignal(self.view, self.nodeData, signal, self.currentNumFig, label, "Time[s]", 0, self)
        p.execute()

    def plotSelectedSignalVsTimeAtIndex(self, index):
        self.updateNodeData();
        treeNode = self.view.getNodeAttributes(self.nodeData['dataName'])
        data_path_list = treeNode.getDataVsTime()
        signalDataAccess = SignalDataAccessFactory(self.view.dataSource).create()
        signal = signalDataAccess.GetSignalVsTime(data_path_list, self.nodeData, treeNode, index)
        label = treeNode.coordinate1Label(self.nodeData['IDSName'], index, self.view.dataSource.ids)
        label = label.replace("ids.", "")
        PlotSignal(view=self.view, nodeData=self.nodeData, signal=signal, numfig=self.currentNumFig, label=label, xlabel="Time[s]", update=1, signalHandling=self).execute()
        
    def plotSelectedSignalVsCoordAtTimeIndex(self, time_index):
        self.updateNodeData();
        treeNode = self.view.getNodeAttributes(self.nodeData['dataName'])
        signalDataAccess = SignalDataAccessFactory(self.view.dataSource).create()
        signal = signalDataAccess.GetSignalAt(self.nodeData, self.view.dataSource.shotNumber, treeNode, time_index)
        aos_vs_itime = treeNode.getDataPathVsTime(treeNode.aos)
        label = treeNode.getDataPath(aos_vs_itime, time_index)
        label = label.replace("ids.", "")
        label = GlobalOperations.replaceBrackets(label)
        label = GlobalOperations.replaceDotsBySlashes(label)
        xlabel = GlobalOperations.replaceBrackets(treeNode.evaluateCoordinate1At(time_index))
        PlotSignal(view=self.view,  nodeData=self.nodeData, signal=signal, numfig=self.currentNumFig, label=label, xlabel=xlabel, update=1, signalHandling=self).execute()


    def addSignalPlotToFig(self, numFig):
        try:
            PlotSignal(view=self.view, nodeData=self.nodeData, numfig=numFig, update=1).execute()
        except ValueError as e:
            self.view.log.error(str(e))

    def shareSameCoordinates(self, selectedDataList):
            selectedSignalsList = []
            for k in selectedDataList:
                v = selectedDataList[k]
                selectedSignalsList.append(v[1]) #v[0] = shot number, v[1] = node data
            s = self.nodeData
            for si in selectedSignalsList:
                if s['coordinate1'] != si['coordinate1']:
                    return False
                s = si
            return True

    def shareSameCoordinatesFrom(self, fig):
        selectedDataList = self.view.imas_viz_api.figToNodes[fig]
        return self.shareSameCoordinates(selectedDataList)

    def hideShowfigure(self, numFig):
        self.view.imas_viz_api.HideShowFigure(numFig)

    def closefigure(self, numFig):
        api = self.view.wxTreeView.imas_viz_api
        self.onClose(api, numFig)

    def showSubPlotsManager(self):
        from imasviz.tests.SubPlotsManagerView import SubPlotsManagerFrame
        frame = SubPlotsManagerFrame("SubPlots Manager", self.view)
        frame.Show(True)


    def onClose(self, api, numfig):
        frame = api.figureframes[numfig]
        del api.figures[numfig]
        del api.figureframes[numfig]
        frame.Close()


