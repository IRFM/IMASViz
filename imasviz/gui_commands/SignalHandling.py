import wx

from imasviz.signals_data_access.SignalDataAccessFactory import SignalDataAccessFactory
from imasviz.gui_commands.select_commands.SelectOrUnselectSignal import SelectOrUnselectSignal
from imasviz.gui_commands.select_commands.UnselectAllSignals import UnselectAllSignals
from imasviz.gui_commands.select_commands.SelectSignalsGroup import SelectSignalsGroup
from imasviz.gui_commands.plot_commands.PlotSignal import PlotSignal
from imasviz.gui_commands.plot_commands.PreviewPlotSignal import PreviewPlotSignal
from imasviz.gui_commands.plot_commands.PlotSelectedSignals import PlotSelectedSignals
from imasviz.gui_commands.plot_commands.PlotSelectedSignalsWithWxmplot import (PlotSelectedSignalsWithWxmplot,
                                                                              modifyMultiPlot)
from imasviz.util.GlobalValues import GlobalIDs
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.view.Coord1Slider import Coord1Slider
from imasviz.util.GlobalValues import FigureTypes

class SignalHandling:

    def __init__(self, view):
        self.view = view
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
        """Display the popup menu for plotting data.
        """

        if (signalName == None): return 0

        # Set new main menu
        self.view.popupmenu = wx.Menu()
        s = ''

        # The popup menu behaviour in relation on the selection/unselection
        # status of the node
        if self.nodeData['isSelected'] == 1:
            # If the node is selected, show unselect menu
            s = 'Unselect '
            # Bitmap icon
            bitmap1 = wx.Bitmap(wx.ArtProvider.GetBitmap(wx.ART_DEL_BOOKMARK))
        else:
            # The node is unselected, show select menu
            s = 'Select '
            # Bitmap icon
            bitmap1 = wx.Bitmap(wx.ArtProvider.GetBitmap(wx.ART_ADD_BOOKMARK))

        # Set second-level popup menu for selection/deselection of the node
        item1 = wx.MenuItem(self.view.popupmenu,
                            GlobalIDs.ID_SELECT_OR_UNSELECT_SIGNAL,
                            text= s + signalName + '...',
                            kind=wx.ITEM_NORMAL)
        # Set bitmap to menu item
        item1.SetBitmap(bitmap1)

        #item2 = wx.MenuItem(self.view.popupmenu, wx.ID_MORE, item='Show '+signalName+' size', kind=wx.ITEM_NORMAL)

        # Set second-level popup menu for creating new plot out of the
        # selected IDS node
        item3 = None
        # The popup menu behaviour in relation to the presence of pre-existing
        # plots
        if len(self.view.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.FIGURETYPE))==0:
            # If there is no pre-existing plot
            item3 = wx.MenuItem(self.view.popupmenu,
                                GlobalIDs.ID_ADD_PLOT_TO_FIGURE,
                                text='Plot ' + signalName,
                                kind=wx.ITEM_NORMAL)
        else:
            # If some plot already exists

            # Add menu for creation of a new figure
            item3 = wx.MenuItem(self.view.popupmenu,
                                GlobalIDs.ID_ADD_PLOT_TO_FIGURE,
                                text='Plot ' + signalName + ' to new figure',
                                kind=wx.ITEM_NORMAL)
            i = 0
            j= 0
            for figureKey in self.view.imas_viz_api.GetFiguresKeys(\
                figureType=FigureTypes.FIGURETYPE):
                # Check for figures that share the same coordinates
                if self.shareSameCoordinatesFrom(figureKey):
                    if j == 0:
                        subMenu = wx.Menu()
                        self.view.popupmenu.Append(wx.ID_ANY,
                                                   'Add plot to existing figure',
                                                   subMenu)

                    subMenu.Append(GlobalIDs.ID_ADD_PLOT_TO_EXISTING_FIGURE + i,
                                   item= figureKey,
                                   kind=wx.ITEM_NORMAL)
                    j = j + 1
                i = i + 1
        # Bitmap icon
        bitmap3 = wx.Bitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_FORWARD))
        # Set bitmap to menu item
        item3.SetBitmap(bitmap3)

        i = 0
        for figureKey in self.view.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.FIGURETYPE):
            if i == 0:
                showMenu = wx.Menu()
                self.view.popupmenu.Append(wx.ID_ANY,
                                           'Show/Hide figure',
                                           showMenu)
            showMenu.Append(GlobalIDs.ID_SHOW_HIDE_FIGURES + i,
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
            showMenu.Append(GlobalIDs.ID_SHOW_HIDE_MULTIPLOTS + i,
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
            showMenu.Append(GlobalIDs.ID_SHOW_HIDE_SUBPLOTS + i,
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
                showMenu.Append(GlobalIDs.ID_DELETE_FIGURES + i,
                                item="All",
                                kind=wx.ITEM_NORMAL)
            showMenu.Append(GlobalIDs.ID_DELETE_FIGURES + i + 1,
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
            showMenu.Append(GlobalIDs.ID_DELETE_MULTIPLOTS + i,
                            item=figureKey,
                            kind=wx.ITEM_NORMAL)
            i = i + 1

        i = 0

        # Set menu items for adding selection to existing MultiPlots
        for figureKey in self.view.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.MULTIPLOTTYPE):
            if i == 0:
                showMenu = wx.Menu()
                self.view.popupmenu.Append(wx.ID_ANY,
                                           'Add selection to MultiPlot',
                                           showMenu)
            showMenu.Append(GlobalIDs.ID_ADD_SELECTION_TO_MULTIPLOT + i,
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
            showMenu.Append(GlobalIDs.ID_DELETE_SUBPLOTS + i,
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
                    GlobalIDs.ID_PLOT_ALL_SELECTED_SIGNALS_TO_FIGURE + i,
                    item=figureKey,
                    kind=wx.ITEM_NORMAL)
                i = i + 1


        item4 = wx.MenuItem(self.view.popupmenu,
                            GlobalIDs.ID_PLOT_SELECTED_SIGNALS_TO_NEW_FIGURE,
                            text='Plot all selected signals to a new figure',
                            kind=wx.ITEM_NORMAL)
        # Bitmap icon
        bitmap4 = wx.Bitmap(wx.ArtProvider.GetBitmap(wx.ART_NEW))
        # Set bitmap to menu item
        item4.SetBitmap(bitmap4)

        # Set submenu for handling signal unselection feature
        menu_signals_unselect = wx.Menu()

        item5 = wx.MenuItem(menu_signals_unselect,
                            GlobalIDs.ID_POPUP_MENU_SIGNALS_UNSELECT_SINGLE_DTV,
                            text='This IMAS Database',
                            kind=wx.ITEM_NORMAL)

        menu_signals_unselect.Append(item5)

        item5_2 = wx.MenuItem(menu_signals_unselect,
                            GlobalIDs.ID_POPUP_MENU_SIGNALS_UNSELECT_ALL_DTV,
                            text='All IMAS Databases',
                            kind=wx.ITEM_NORMAL)

        menu_signals_unselect.Append(item5_2)

        item6 = wx.MenuItem(self.view.popupmenu,
                            GlobalIDs.ID_OPEN_SUBPLOTS_MANAGER,
                            text='Open subplots manager',
                            kind=wx.ITEM_NORMAL)
        # Bitmap icon
        bitmap6 = wx.Bitmap(wx.ArtProvider.GetBitmap(wx.ART_LIST_VIEW))
        # Set bitmap to menu item
        item6.SetBitmap(bitmap6)

        item7 = wx.MenuItem(self.view.popupmenu,
                            GlobalIDs.ID_PLOT_AS_ITIME,
                            text='Plot ' + signalName + ' as a function of time',
                            kind=wx.ITEM_NORMAL)
        # Bitmap icon
        bitmap7 = wx.Bitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_FORWARD))
        # Set bitmap to menu item
        item7.SetBitmap(bitmap7)

        item8 = wx.MenuItem(self.view.popupmenu,
                            GlobalIDs.ID_PLOT_SELECTED_SIGNALS_ALL_DTV_TO_MULTIPLOTFRAME,
                            text='Plot selected signals to a multiplots frame (all opened IMAS databases)',
                            kind=wx.ITEM_NORMAL)
        # Bitmap icon
        bitmap8 = wx.Bitmap(wx.ArtProvider.GetBitmap(wx.ART_REPORT_VIEW))
        # Set bitmap to menu item
        item8.SetBitmap(bitmap8)

        item9 = wx.MenuItem(self.view.popupmenu,
                            GlobalIDs.ID_PLOT_SELECTED_SIGNALS_SINGLE_DTV_TO_MULTIPLOTFRAME,
                            text='Plot selected signals to a multiplots frame (this opened IMAS database',
                            kind=wx.ITEM_NORMAL)
        # Bitmap icon
        bitmap9 = wx.Bitmap(wx.ArtProvider.GetBitmap(wx.ART_REPORT_VIEW))
        # Set bitmap to menu item
        item9.SetBitmap(bitmap9)

        item10 = wx.MenuItem(self.view.popupmenu,
                            GlobalIDs.ID_SELECT_ALL_SIGNALS_FROM_SAME_AOS,
                            text='Select all signals from the same AOS',
                            kind=wx.ITEM_NORMAL)
        # Bitmap icon
        bitmap10 = wx.Bitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_UP))
        # Set bitmap to menu item
        item10.SetBitmap(bitmap10)

        self.view.popupmenu.Append(item1)
        #self.view.popupmenu.Append(item2)
        if item3 != None:
            self.view.popupmenu.Append(item3)

        if item10 != None:
            self.view.popupmenu.Append(item10)

        if len(self.view.selectedSignals) > 0:
            if self.shareSameCoordinates(self.view.selectedSignals):
                self.view.popupmenu.Append(item4)

            self.view.popupmenu.Append(wx.ID_CANCEL,
                "Unselect signals", menu_signals_unselect)

            self.view.popupmenu.Append(item8)
            self.view.popupmenu.Append(item9)

        if len(self.view.selectedSignals) > 1:
            self.view.popupmenu.Append(item6)

        treeNode = self.view.getNodeAttributes(self.nodeData['dataName'])
        if treeNode != None and treeNode.time_dependent(treeNode.aos):
            self.view.popupmenu.Append(item7)

        self.view.Bind(wx.EVT_MENU, self.popUpMenuHandler)
        return 1

    def popUpMenuHandler(self, event):
        """Link the events (defined by event ID) with corresponding routines.
        """
        if event.GetId() == wx.ID_MORE:
            self.signalSizeRequest(event)
        elif event.GetId() == GlobalIDs.ID_ADD_PLOT_TO_FIGURE:
            self.plotSignalCommand(event)
        elif event.GetId() == GlobalIDs.ID_SELECT_OR_UNSELECT_SIGNAL:
            self.selectOrUnselectSignal(event)  # selection
        elif event.GetId() == GlobalIDs.ID_PLOT_SELECTED_SIGNALS_TO_NEW_FIGURE:
            self.plotSelectedSignals()
        elif event.GetId() == GlobalIDs.ID_PLOT_SELECTED_SIGNALS_ALL_DTV_TO_MULTIPLOTFRAME:
            self.plotSelectedSignalsToMultiPlotsFrame(all_DTV=True)
        elif event.GetId() == GlobalIDs.ID_PLOT_SELECTED_SIGNALS_SINGLE_DTV_TO_MULTIPLOTFRAME:
            self.plotSelectedSignalsToMultiPlotsFrame(all_DTV=False)
        elif event.GetId() == GlobalIDs.ID_SELECT_ALL_SIGNALS_FROM_SAME_AOS:
            self.selectAllSignalsFromSameAOS()
        elif event.GetId() == GlobalIDs.ID_POPUP_MENU_SIGNALS_UNSELECT_ALL_DTV:
            self.unselectAllSignals(all_DTV=True)
        elif event.GetId() == GlobalIDs.ID_POPUP_MENU_SIGNALS_UNSELECT_SINGLE_DTV:
            self.unselectAllSignals(all_DTV=False)
        elif event.GetId() == GlobalIDs.ID_OPEN_SUBPLOTS_MANAGER:
            self.showSubPlotsManager()
        elif event.GetId() == GlobalIDs.ID_PLOT_AS_ITIME:
            self.plotSelectedSignalVsTime()
        else:
            for i in range(0, len(self.view.imas_viz_api.figureframes)):
                if event.GetId() == i + GlobalIDs.ID_ADD_PLOT_TO_EXISTING_FIGURE:
                    self.addSignalPlotToFig(i)
                elif event.GetId() == i + GlobalIDs.ID_SHOW_HIDE_FIGURES:
                    self.hideShowfigure(i, figureType=FigureTypes.FIGURETYPE)
                elif event.GetId() == i + GlobalIDs.ID_SHOW_HIDE_MULTIPLOTS:
                    self.hideShowfigure(i,figureType=FigureTypes.MULTIPLOTTYPE)
                elif event.GetId() == GlobalIDs.ID_DELETE_FIGURES:
                    self.deleteAllFigures()
                elif event.GetId() == i + 1 + GlobalIDs.ID_DELETE_FIGURES:
                    self.deleteFigure(i)
                elif event.GetId() == i + GlobalIDs.ID_DELETE_MULTIPLOTS:
                    self.deleteMultiplots(i)
                elif event.GetId() == i + GlobalIDs.ID_DELETE_SUBPLOTS:
                    self.deleteSubplots(i)
                elif event.GetId() == i + GlobalIDs.ID_PLOT_ALL_SELECTED_SIGNALS_TO_FIGURE:
                    self.plotSelectedSignalsToFig(i)
                elif event.GetId() == i + GlobalIDs.ID_SHOW_HIDE_SUBPLOTS:
                    self.hideShowfigure(i, figureType=FigureTypes.SUBPLOTTYPE)
                elif event.GetId() == i + GlobalIDs.ID_ADD_SELECTION_TO_MULTIPLOT:
                    self.addSignalSelectionToMultiPlotFrame(i)

    def selectSignal(self):
        SelectOrUnselectSignal(self.view, self.nodeData).execute()

    def selectOrUnselectSignal(self, event):
        SelectOrUnselectSignal(self.view, self.nodeData).execute()

    def unselectAllSignals(self, all_DTV=False):
        """Unselect signals in single (current) or all DTVs

        Arguments:
                all_DTV (bool) : Indicator to read selected signals from the
                                 current or all DTVs.
        """
        if all_DTV != True:
            UnselectAllSignals(self.view, self.nodeData).execute()
        else:
            for dtv in self.view.imas_viz_api.wxDTVlist:
                UnselectAllSignals(dtv, self.nodeData).execute()

    def plotSignalCommand(self, event):
        try:
            self.currentFigureKey = \
                self.view.imas_viz_api.GetNextKeyForFigurePlots()
            treeNode = self.view.getNodeAttributes(self.nodeData['dataName'])
            label = None
            xlabel = None
            if treeNode != None and treeNode.time_dependent_aos():
                aos_vs_itime = treeNode.getDataPathVsTime(treeNode.aos)
                label = treeNode.getDataPath(aos_vs_itime, 0)
                label = label.replace("ids.", "")
                label = GlobalOperations.replaceBrackets(label)
                label = GlobalOperations.replaceDotsBySlashes(label)
                xlabel = \
                    GlobalOperations.replaceBrackets(treeNode.evaluateCoordinate1At(0))
                self.timeSlider = True
            else:
                self.timeSlider = None
            p = PlotSignal(self.view, self.nodeData, signal=None,
                figureKey=self.currentFigureKey, label=label,xlabel=xlabel,
                signalHandling=self)
            p.execute()

        except ValueError as e:
            self.view.log.error(str(e))

    def plotPreviewSignalCommand(self, event):
        """Show preview plot.
        """
        try:
            label = None
            xlabel = None
            p = PreviewPlotSignal(self.view, self.nodeData, signal=None,
                                  label=label,xlabel=xlabel,
                                  signalHandling=self)
            p.execute()

        except ValueError as e:
            self.view.log.error(str(e))

    def plotSelectedSignals(self):
        """Plot selected signals.
        """
        # Get label for the next figure (e.c. if 'Figure 2' already exists,
        # value 'Figure 3' will be returned)
        figureKey = self.view.imas_viz_api.GetNextKeyForFigurePlots()
        # Plot the selected signals
        PlotSelectedSignals(self.view, figureKey).execute()

    def plotSelectedSignalsToFig(self, numFig):
        figureKeys = \
            self.view.imas_viz_api.GetFiguresKeys(figureType=FigureTypes.FIGURETYPE)
        figureKey = figureKeys[numFig]
        PlotSelectedSignals(self.view, figureKey, 1).execute()

    def plotSelectedSignalsToMultiPlotsFrame(self, all_DTV=False):
        """Create a MultiPlot using signals selected in single/all opened DTV
           windows

           Parameters:
                all_DTV : bool
                Indicator to read selected signals from the current or all DTVs.
        """
        # Get next figure key/label
        figureKey = self.view.imas_viz_api.GetNextKeyForMultiplePlots()
        if all_DTV != True:
            # Note: '.execute' rutine is from the PlotSelectedSignals.py
            PlotSelectedSignalsWithWxmplot(self.view, figureKey, 1,
                                           all_DTV = False).execute()
        else:
            PlotSelectedSignalsWithWxmplot(self.view, figureKey, 1,
                                           all_DTV = True).execute()

    def selectAllSignalsFromSameAOS(self):
        SelectSignalsGroup(self.view, self.nodeData).execute()

    def plotSelectedSignalVsTime(self):
        self.updateNodeData()
        treeNode = self.view.getNodeAttributes(self.nodeData['dataName'])
        index = 0
        data_path_list = treeNode.getDataVsTime() #aos[0], aos[1], ... , aos[itime], ...
        signalDataAccess = SignalDataAccessFactory(self.view.dataSource).create()
        signal = signalDataAccess.GetSignalVsTime(data_path_list,
                                                  self.nodeData, treeNode, index)
        label, title = \
            treeNode.coordinate1LabelAndTitleForTimeSlices(self.nodeData, index,
                                                           self.view.dataSource.ids)
        self.treeNode = treeNode
        self.timeSlider = False
        p = PlotSignal(view=self.view, nodeData=self.nodeData, signal=signal,
                       figureKey=self.currentFigureKey, title=title, label=label,
                       xlabel="Time[s]", update=0, signalHandling=self)
        p.execute()

    def plotSelectedSignalVsTimeAtIndex(self, index, currentFigureKey):
        self.updateNodeData()
        treeNode = self.view.getNodeAttributes(self.nodeData['dataName'])
        data_path_list = treeNode.getDataVsTime()
        signalDataAccess = SignalDataAccessFactory(self.view.dataSource).create()
        signal = signalDataAccess.GetSignalVsTime(data_path_list, self.nodeData, treeNode, index)
        label, title = \
            treeNode.coordinate1LabelAndTitleForTimeSlices(self.nodeData, index,
                                                           self.view.dataSource.ids)
        if label != None:
            label = label.replace("ids.", "")
        PlotSignal(view=self.view, nodeData=self.nodeData, signal=signal,
                   figureKey=currentFigureKey, title=title, label=label,
                   xlabel="Time[s]", update=0, signalHandling=self).execute()

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
            selectedSignalsList.append(v[1]) # v[0] = shot number,
                                             # v[1] = node data
                                             # v[2] = index,
                                             # v[3] = shot number,
                                             # v[3] = IDS database name,
                                             # v[4] = user name
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
        """ Hide/Show figure frame or MultiPlot frame.

        Parameters
        ----------
        numFig : integer
            Figure number.
        figureType : string
            Type of figure e.c. "Figure:", "Multiplot:", "Subplot"... see
            GlobalValues.py FigureTypes class for a full list of figure types.
        """
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

    def addSignalSelectionToMultiPlotFrame(self, numFig):
        """Add signal selection to existing MultiPlot.

        Parameters
        ----------

        numFig : integer
            MultiPlot frame number.
        """
        try:
            # Get MultiPlot frame, selected from the popup menu
            # - Get all existing MultiPlot (figure) frame keys
            figureKeys = self.view.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.MULTIPLOTTYPE)
            # - Get the required (numFig) label of the wanted MultiPlot frame
            figureKey = figureKeys[numFig]  # Label of the MultiPlot frame that
                                            # is to be updated (new signal
                                            # selection added).
            # - Set MultiPlot frame
            multiPlotFrame = self.view.imas_viz_api.getFigureFrame(figureKey)
            # Add signal selection to MultiPlot frame
            mmp = modifyMultiPlot(multiPlotFrame=multiPlotFrame,
                               WxDataTreeView=self.view)
            mmp.addSignalSelection()
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
        frame = SubPlotsManagerFrame("SubPlots Manager", self.view, all_DTVs = False)
        frame.Show(True)


    # def onClose(self, api, numfig):
    #     frame = api.figureframes[numfig]
    #     del api.figures[numfig]
    #     del api.figureframes[numfig]
    #     frame.Close()


