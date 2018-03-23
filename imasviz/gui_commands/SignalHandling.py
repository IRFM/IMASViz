import wx

from imasviz.signals_data_access.SignalDataAccessFactory import SignalDataAccessFactory
from imasviz.gui_commands.select_commands.SelectOrUnselectSignal import SelectOrUnselectSignal
from imasviz.gui_commands.select_commands.UnselectAllSignals import UnselectAllSignals
from imasviz.gui_commands.plot_commands.PlotSignal import PlotSignal
from imasviz.gui_commands.plot_commands.PlotSelectedSignals import PlotSelectedSignals
from imasviz.gui_commands.plot_commands.PlotSelectedSignalsWithWxmplot import PlotSelectedSignalsWithWxmplot
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.view.Coord1Slider import Coord1Slider
from imasviz.util.GlobalValues import FigureTypes


class MenuIDS:
    def __init__(self):
        self.ID_ADD_PLOT_TO_FIGURE = 1000
        self.ID_ADD_PLOT_TO_EXISTING_FIGURE = 1500 #wx.NewId()
        self.ID_SELECT_OR_UNSELECT_SIGNAL = 2000
        self.ID_SHOW_HIDE_FIGURES  = 3000
        self.ID_SHOW_HIDE_MULTIPLOTS = 3500
        self.ID_SHOW_HIDE_SUBPLOTS = 4000
        self.ID_PLOT_ALL_SELECTED_SIGNALS_TO_FIGURE = 5000
        self.ID_PLOT_AS_ITIME = 6000
        self.ID_PLOT_SELECTED_SIGNALS_TO_NEW_FIGURE = 7000
        self.ID_PLOT_SELECTED_SIGNALS_TO_MULTIPLOTFRAME = 7500
        self.ID_OPEN_SUBPLOTS_MANAGER = 8000
        self.ID_CHANGE_COORD1 = 9000
        self.ID_DELETE_FIGURES = 10000
        self.ID_DELETE_MULTIPLOTS = 15000
        self.ID_DELETE_SUBPLOTS = 20000

class SignalHandling:

    def __init__(self, view):
        self.view = view
        self.menuIDS = MenuIDS()
        self.CHANGE_COORD1 = wx.NewId()
        self.CHANGE_TIME1  = wx.NewId()
        self.plotFrame = None
        self.currentFigureKey = None
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

    def showPopUpMenu(self, signalName):
        """Display the popup menu for plotting data
        """

        if (signalName == None): return 0

        """Set new main menu"""
        self.view.popupmenu = wx.Menu()
        s = ''

        """The popup menu behaviour in relation on the selection/unselection
        status of the node
        """
        if self.nodeData['isSelected'] == 1:
            """If the node is selected, show unselect menu"""
            s = 'Unselect '
        else:
            """The node is unselected, show select menu"""
            s = 'Select '

        """Set second-level popup menu for selection/deselection of the node """
        item1 = wx.MenuItem(self.view.popupmenu,
                            self.menuIDS.ID_SELECT_OR_UNSELECT_SIGNAL,
                            text= s + signalName + '...',
                            kind=wx.ITEM_NORMAL)

        #item2 = wx.MenuItem(self.view.popupmenu, wx.ID_MORE, item='Show '+signalName+' size', kind=wx.ITEM_NORMAL)

        """Set second-level popup menu for creating new plot out of the
        selected IDS node
        """
        item3 = None
        """The popup menu behaviour in relation to the presence of pre-existing
        plots"""
        if len(self.view.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.FIGURETYPE))==0:
            """If there is no pre-existing plot """
            item3 = wx.MenuItem(self.view.popupmenu,
                                self.menuIDS.ID_ADD_PLOT_TO_FIGURE,
                                text='Plot ' + signalName,
                                kind=wx.ITEM_NORMAL)
        else:
            """If some plot already exists"""

            """Add menu for creation of a new figure"""
            item3 = wx.MenuItem(self.view.popupmenu,
                                self.menuIDS.ID_ADD_PLOT_TO_FIGURE,
                                text='Plot ' + signalName + ' to new figure',
                                kind=wx.ITEM_NORMAL)
            i = 0
            j= 0
            for figureKey in self.view.imas_viz_api.GetFiguresKeys(\
                figureType=FigureTypes.FIGURETYPE):
                """Check for figures that share the same coordinates"""
                if self.shareSameCoordinatesFrom(figureKey):
                    if j == 0:
                        subMenu = wx.Menu()
                        self.view.popupmenu.Append(wx.ID_ANY,
                                                   'Add plot to existing figure',
                                                   subMenu)
                    subMenu.Append(
                        self.menuIDS.ID_ADD_PLOT_TO_EXISTING_FIGURE + i,
                        item= figureKey,
                        kind=wx.ITEM_NORMAL)
                    j = j + 1
                i = i + 1

        i = 0
        for figureKey in self.view.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.FIGURETYPE):
            if i == 0:
                showMenu = wx.Menu()
                self.view.popupmenu.Append(wx.ID_ANY,
                                           'Show/Hide figure',
                                           showMenu)
            showMenu.Append(self.menuIDS.ID_SHOW_HIDE_FIGURES + i,
                            item=figureKey,
                            kind=wx.ITEM_NORMAL)
            i = i + 1

        i = 0
        for figureKey in self.view.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.MULTIPLOTTYPE):
            if i == 0:
                showMenu = wx.Menu()
                self.view.popupmenu.Append(wx.ID_ANY,
                                           'Show/Hide multiplots',
                                           showMenu)
            showMenu.Append(self.menuIDS.ID_SHOW_HIDE_MULTIPLOTS + i,
                            item=figureKey,
                            kind=wx.ITEM_NORMAL)
            i = i + 1

        i = 0
        for figureKey in self.view.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.SUBPLOTTYPE):
            if i == 0:
                showMenu = wx.Menu()
                self.view.popupmenu.Append(wx.ID_ANY,
                                           'Show/Hide subplots',
                                           showMenu)
            showMenu.Append(self.menuIDS.ID_SHOW_HIDE_SUBPLOTS + i,
                            item=figureKey,
                            kind=wx.ITEM_NORMAL)
            i = i + 1

        i = 0
        for figureKey in self.view.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.FIGURETYPE):
            if i == 0:
                showMenu = wx.Menu()
                self.view.popupmenu.Append(wx.ID_ANY,
                                           'Delete figure',
                                           showMenu)
                showMenu.Append(self.menuIDS.ID_DELETE_FIGURES + i,
                                item="All",
                                kind=wx.ITEM_NORMAL)
            showMenu.Append(self.menuIDS.ID_DELETE_FIGURES + i + 1,
                            item=figureKey,
                            kind=wx.ITEM_NORMAL)
            i = i + 1

        i = 0
        for figureKey in self.view.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.MULTIPLOTTYPE):
            if i == 0:
                showMenu = wx.Menu()
                self.view.popupmenu.Append(wx.ID_ANY,
                                           'Delete multiplot',
                                           showMenu)
            showMenu.Append(self.menuIDS.ID_DELETE_MULTIPLOTS + i,
                            item=figureKey,
                            kind=wx.ITEM_NORMAL)
            i = i + 1

        i = 0
        for figureKey in self.view.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.SUBPLOTTYPE):
            if i == 0:
                showMenu = wx.Menu()
                self.view.popupmenu.Append(wx.ID_ANY,
                                           'Delete subplot',
                                           showMenu)
            showMenu.Append(self.menuIDS.ID_DELETE_SUBPLOTS + i,
                            item=figureKey,
                            kind=wx.ITEM_NORMAL)
            i = i + 1

        if self.view.imas_viz_api.GetFigurePlotsCount() > 0 \
                and len(self.view.selectedSignals) > 0 \
                and self.shareSameCoordinates(self.view.selectedSignals):

            i = 0
            for figureKey in self.view.imas_viz_api.GetFiguresKeys(
                    figureType=FigureTypes.FIGURETYPE):
                if i == 0:
                    showMenu = wx.Menu()
                    self.view.popupmenu.Append(wx.ID_ANY,
                                               'Plot all selected signals to',
                                               showMenu)
                showMenu.Append(
                    self.menuIDS.ID_PLOT_ALL_SELECTED_SIGNALS_TO_FIGURE + i,
                    item=figureKey,
                    kind=wx.ITEM_NORMAL)
                i = i + 1


        item4 = wx.MenuItem(self.view.popupmenu,
                            self.menuIDS.ID_PLOT_SELECTED_SIGNALS_TO_NEW_FIGURE,
                            text='Plot all selected signals to a new figure',
                            kind=wx.ITEM_NORMAL)

        item5 = wx.MenuItem(self.view.popupmenu,
                            wx.ID_CANCEL,
                            text='Unselect all signals',
                            kind=wx.ITEM_NORMAL)

        item6 = wx.MenuItem(self.view.popupmenu,
                            self.menuIDS.ID_OPEN_SUBPLOTS_MANAGER,
                            text='Open subplots manager',
                            kind=wx.ITEM_NORMAL)

        item7 = wx.MenuItem(self.view.popupmenu,
                            self.menuIDS.ID_PLOT_AS_ITIME,
                            text='Plot ' + signalName + ' as a function of time',
                            kind=wx.ITEM_NORMAL)

        item8 = wx.MenuItem(self.view.popupmenu,
                            self.menuIDS.ID_PLOT_SELECTED_SIGNALS_TO_MULTIPLOTFRAME,
                            text='Plot all selected signals to a multiplots frame',
                            kind=wx.ITEM_NORMAL)

        self.view.popupmenu.Append(item1)
        #self.view.popupmenu.Append(item2)
        if item3 != None:
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
            for i in range(0, len(self.view.imas_viz_api.figureframes)):
                if event.GetId() == i + self.menuIDS.ID_ADD_PLOT_TO_EXISTING_FIGURE:
                    self.addSignalPlotToFig(i)
                elif event.GetId() == i + self.menuIDS.ID_SHOW_HIDE_FIGURES:
                    self.hideShowfigure(i, figureType=FigureTypes.FIGURETYPE)
                elif event.GetId() == i + self.menuIDS.ID_SHOW_HIDE_MULTIPLOTS:
                    self.hideShowfigure(i,figureType=FigureTypes.MULTIPLOTTYPE)
                elif event.GetId() == self.menuIDS.ID_DELETE_FIGURES:
                    self.deleteAllFigures()
                elif event.GetId() == i + 1 + self.menuIDS.ID_DELETE_FIGURES:
                    self.deleteFigure(i)
                elif event.GetId() == i + self.menuIDS.ID_DELETE_MULTIPLOTS:
                    self.deleteMultiplots(i)
                elif event.GetId() == i + self.menuIDS.ID_DELETE_SUBPLOTS:
                    self.deleteSubplots(i)
                elif event.GetId() == i + self.menuIDS.ID_PLOT_ALL_SELECTED_SIGNALS_TO_FIGURE:
                    self.plotSelectedSignalsToFig(i)
                elif event.GetId() == i + self.menuIDS.ID_SHOW_HIDE_SUBPLOTS:
                    self.hideShowfigure(i, figureType=FigureTypes.SUBPLOTTYPE)


    def selectSignal(self):
        SelectOrUnselectSignal(self.view, self.nodeData).execute()

    def selectOrUnselectSignal(self, event):
        SelectOrUnselectSignal(self.view, self.nodeData).execute()

    def unselectAllSignals(self):
        UnselectAllSignals(self.view, self.nodeData).execute()

    def plotSignalCommand(self, event):
        try:
            self.currentFigureKey = self.view.imas_viz_api.GetNextKeyForFigurePlots()
            treeNode = self.view.getNodeAttributes(self.nodeData['dataName'])
            label = None
            xlabel = None
            if treeNode != None and treeNode.time_dependent_aos():
                aos_vs_itime = treeNode.getDataPathVsTime(treeNode.aos)
                label = treeNode.getDataPath(aos_vs_itime, 0)
                label = label.replace("ids.", "")
                label = GlobalOperations.replaceBrackets(label)
                label = GlobalOperations.replaceDotsBySlashes(label)
                xlabel = GlobalOperations.replaceBrackets(treeNode.evaluateCoordinate1At(0))
                self.timeSlider = True
            else:
                self.timeSlider = None
            p = PlotSignal(self.view, self.nodeData, signal=None, figureKey=self.currentFigureKey, label=label,xlabel=xlabel, signalHandling=self)
            p.execute()

        except ValueError as e:
            self.view.log.error(str(e))

    def plotSelectedSignals(self):
        figureKey = self.view.imas_viz_api.GetNextKeyForFigurePlots()
        PlotSelectedSignals(self.view, figureKey).execute()

    def plotSelectedSignalsToFig(self, numFig):
        figureKeys = self.view.imas_viz_api.GetFiguresKeys(figureType=FigureTypes.FIGURETYPE)
        figureKey = figureKeys[numFig]
        PlotSelectedSignals(self.view, figureKey, 1).execute()

    def plotSelectedSignalsToMultiPlotsFrame(self):
        figureKey = self.view.imas_viz_api.GetNextKeyForMultiplePlots()
        PlotSelectedSignalsWithWxmplot(self.view, figureKey, 1).execute()

    def plotSelectedSignalVsTime(self):
        self.updateNodeData()
        treeNode = self.view.getNodeAttributes(self.nodeData['dataName'])
        index = 0
        data_path_list = treeNode.getDataVsTime() #aos[0], aos[1], ... , aos[itime], ...
        signalDataAccess = SignalDataAccessFactory(self.view.dataSource).create()
        signal = signalDataAccess.GetSignalVsTime(data_path_list, self.nodeData, treeNode, index)
        label, title = treeNode.coordinate1LabelAndTitleForTimeSlices(self.nodeData, index, self.view.dataSource.ids)
        self.treeNode = treeNode
        self.timeSlider = False
        p = PlotSignal(view=self.view, nodeData=self.nodeData, signal=signal, figureKey=self.currentFigureKey,
                       title=title, label=label, xlabel="Time[s]", update=0, signalHandling=self)
        p.execute()

    def plotSelectedSignalVsTimeAtIndex(self, index, currentFigureKey):
        self.updateNodeData()
        treeNode = self.view.getNodeAttributes(self.nodeData['dataName'])
        data_path_list = treeNode.getDataVsTime()
        signalDataAccess = SignalDataAccessFactory(self.view.dataSource).create()
        signal = signalDataAccess.GetSignalVsTime(data_path_list, self.nodeData, treeNode, index)
        label, title = treeNode.coordinate1LabelAndTitleForTimeSlices(self.nodeData, index, self.view.dataSource.ids)
        if label != None:
            label = label.replace("ids.", "")
        PlotSignal(view=self.view, nodeData=self.nodeData, signal=signal, figureKey=currentFigureKey, title=title,
                   label=label, xlabel="Time[s]", update=0, signalHandling=self).execute()

    def plotSelectedSignalVsCoordAtTimeIndex(self, time_index, currentFigureKey):
        self.updateNodeData()
        treeNode = self.view.getNodeAttributes(self.nodeData['dataName'])
        signalDataAccess = SignalDataAccessFactory(self.view.dataSource).create()
        signal = signalDataAccess.GetSignalAt(self.nodeData,
                                              self.view.dataSource.shotNumber,
                                              treeNode,
                                              time_index)
        aos_vs_itime = treeNode.getDataPathVsTime(treeNode.aos)
        print (aos_vs_itime)
        label = treeNode.getDataPath(aos_vs_itime, time_index)
        label = label.replace("ids.", "")
        label = GlobalOperations.replaceBrackets(label)
        label = GlobalOperations.replaceDotsBySlashes(label)
        xlabel = GlobalOperations.replaceBrackets(
            treeNode.evaluateCoordinate1At(time_index))
        PlotSignal(view=self.view,
                   nodeData=self.nodeData,
                   signal=signal,
                   figureKey=currentFigureKey,
                   label=label,
                   xlabel=xlabel,
                   update=0,
                   signalHandling=self).execute()


    def addSignalPlotToFig(self, numFig):
        try:
            figureKeys = self.view.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.FIGURETYPE)
            figureKey = figureKeys[numFig]
            PlotSignal(view=self.view,
                       nodeData=self.nodeData,
                       figureKey=figureKey,
                       update=1).execute()
        except ValueError as e:
            self.view.log.error(str(e))

    def shareSameCoordinates(self, selectedDataList):
        """Check if data in selectedDataList share the same coordinates
        """
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

    def shareSameCoordinatesFrom(self, figureKey):
        selectedDataList = self.view.imas_viz_api.figToNodes[figureKey]
        return self.shareSameCoordinates(selectedDataList)

    def hideShowfigure(self, numFig, figureType):
        figureKeys = self.view.imas_viz_api.GetFiguresKeys(figureType=figureType)
        figureKey = figureKeys[numFig]
        self.view.imas_viz_api.HideShowFigure(figureKey)

    def deleteAllFigures(self):
        figureKeys = self.view.imas_viz_api.GetFiguresKeys(
            figureType=FigureTypes.FIGURETYPE)
        for figureKey in figureKeys:
            self.view.imas_viz_api.DeleteFigure(figureKey)

    def deleteFigure(self, numFig):
        try:
            figureKeys = self.view.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.FIGURETYPE)
            figureKey = figureKeys[numFig]
            self.view.imas_viz_api.DeleteFigure(figureKey)
        except ValueError as e:
            self.view.log.error(str(e))

    def deleteMultiplots(self, numFig):
        try:
            figureKeys = self.view.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.MULTIPLOTTYPE)
            figureKey = figureKeys[numFig]
            self.view.imas_viz_api.DeleteFigure(figureKey)
        except ValueError as e:
            self.view.log.error(str(e))

    def deleteSubplots(self, numFig):
        try:
            figureKeys = self.view.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.SUBPLOTTYPE)
            figureKey = figureKeys[numFig]
            self.view.imas_viz_api.DeleteFigure(figureKey)
        except ValueError as e:
            self.view.log.error(str(e))

    def showSubPlotsManager(self):
        from imasviz.gui_commands.plot_commands.SubPlotsManagerView import SubPlotsManagerFrame
        frame = SubPlotsManagerFrame("SubPlots Manager", self.view)
        frame.Show(True)


    # def onClose(self, api, numfig):
    #     frame = api.figureframes[numfig]
    #     del api.figures[numfig]
    #     del api.figureframes[numfig]
    #     frame.Close()


