#  Name   : QVizSignalHandling
#
#          Container to handle right-click events for signals - filled (blue)
#          tree items (PyQt5).
#          Note: The wxPython predecessor of this Python file is
#          SignalHandling.py
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#  TODO:
#
#    - Function definitions (from SignalHandling class)
#    def onPlotToTablePlotView
#    def plotSelectedSignalVsTime
#    def plotSelectedSignalVsTimeAtIndex
#    def plotSelectedSignalVsCoordAtTimeIndex
#    def deleteMultiplots
#    def addSignalSelectionToTablePlotViewFrame
#    def deleteSubplots
#    def showStackedPlotViewsManager
#    def # onClose
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#****************************************************

# from imasviz.VizDataAccess.QVizDataAccessFactory import QVizDataAccessFactory
from functools import partial

from PyQt5.QtCore import QObject, pyqtSlot
from PyQt5.QtWidgets import QAction, QMenu
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations

from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizTablePlotView import QVizTablePlotView
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizMultiPlotWindow import QVizMultiPlotWindow
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizStackedPlotView import QVizStackedPlotView
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSelectedSignals import QVizPlotSelectedSignals
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal import QVizPlotSignal
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPreviewPlotSignal import QVizPreviewPlotSignal
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectOrUnselectSignal import QVizSelectOrUnselectSignal
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignalsGroup import QVizSelectSignalsGroup
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizUnselectAllSignals import QVizUnselectAllSignals
from imasviz.VizUtils.QVizGlobalValues import FigureTypes


class QVizSignalHandling(QObject):
    def __init__(self, dataTreeView):
        """
        Arguments:
            dataTreeView (QTreeWidget) : DataTreeView object of the QTreeWidget.
        """
        super(QVizSignalHandling, self).__init__()
        self.dataTreeView = dataTreeView
        self.api = self.dataTreeView.imas_viz_api
        # self.CHANGE_COORD1 = GlobalIDs.ID_CHANGE_COORD1
        # self.CHANGE_TIME1  = GlobalIDs.ID_CHANGE_TIME1
        self.plotFrame = None
        self.currentFigureKey = None
        # Get signal node (tree item) data
        self.nodeData = None
        if self.dataTreeView.selectedItem != None:
            self.nodeData = self.dataTreeView.selectedItem.getDataDict()
        # Get signal node dataName
        self.treeNode = self.dataTreeView.selectedItem

        self.timeSlider = None

    def updateNodeData(self):
        """ Update tree node/item data.
            TODO: use the global routine 'updateNodeData' defined in
                  QVizAbstractCommand instead.
        """
        self.nodeData = self.dataTreeView.selectedItem.getDataDict()
        self.treeNode = self.dataTreeView.selectedItem

    def showPopUpMenu(self, signalName):
        """Display the popup menu for plotting data.

        Arguments:
            signalName (str) : Name of the signal node (tree item).
                               (example: ids.magnetics.flux_loop[0].flux.data)
        """

        # TODO: popup menu gets build every time on right-click. Maybe create
        #       it once and then only enable/disable menu items on right-click

        if (signalName == None):
            return 0

        # Get total count of figures, tablePlotViews, stackedPlotViews etc.
        numFig = self.api.GetFigurePlotsCount()
        numTPV = self.api.GetTablePlotViewsCount()
        numSPV = self.api.GetStackedPlotViewsCount()

        # Set new popup menu
        self.dataTreeView.popupmenu = QMenu()

        # SET TOP ACTIONS
        # ----------------------------------------------------------------------
        # The popup menu behavior in relation on the selection/unselection
        # status of the node
        s = ''
        if self.nodeData['isSelected'] == 1:
            # If the node is selected, show unselect menu
            s = 'Unselect '
            # Bitmap icon
            # TODO
        else:
            # The node is unselected, show select menu
            s = 'Select '
            # Bitmap icon
            # TODO

        # Set action for selection/unselection of the node
        action_selectOrUnselectSignal = QAction(s + signalName + '...', self)
        action_selectOrUnselectSignal.triggered.connect(self.selectOrUnselectSignal)
        self.dataTreeView.popupmenu.addAction(action_selectOrUnselectSignal)
        # Set bitmap to menu item
        # TODO

        # Add action for selection of all signals from the same array of
        # structures
        action_selectAllSignalsFromSameAOS = \
            QAction('Select all nodes from the same AOS', self)
        action_selectAllSignalsFromSameAOS.triggered.connect(
            self.selectAllSignalsFromSameAOS)
        self.dataTreeView.popupmenu.addAction(action_selectAllSignalsFromSameAOS)
        # TODO
        # Set bitmap to menu item

        # SET BASIC TEMPLATE FOR TOP MENU ITEMS
        # ----------------------------------------------------------------------
        menu_plotSelection = self.dataTreeView.popupmenu.addMenu('Plot ' + signalName + ' to')

        menu_unselect = self.dataTreeView.popupmenu.addMenu('Unselect Nodes')
        menu_unselect.setDisabled(True)

        menu_plotSelectedNodes = self.dataTreeView.popupmenu.addMenu('Plot selected nodes to')
        menu_plotSelectedNodes.setDisabled(True)

        if len(self.dataTreeView.selectedSignalsDict) > 0:
            menu_unselect.setDisabled(False)
            menu_plotSelectedNodes.setDisabled(False)

        menu_showHide = self.dataTreeView.popupmenu.addMenu('Show/Hide')
        menu_showHide.setDisabled(True)

        # Create and add empty submenu to handle deletion of plot views and
        # figures
        menu_delete = self.dataTreeView.popupmenu.addMenu('Delete')
        menu_delete.setDisabled(True)
        if numFig > 0 or numTPV > 0 or numSPV > 0:
            menu_delete.setDisabled(False)
            menu_showHide.setDisabled(False)

        # ----------------------------------------------------------------------
        # SET MENU FOR UNSELECT HANDLING
        # Set actions for unselection of all selected signals if menu is enabled
        if len(self.dataTreeView.selectedSignalsDict) > 0:
            # Add menu item to unselect all signals - This/Current DTV
            action_onUnselectSignals = QAction('This IMAS Database', self)
            action_onUnselectSignals.triggered.connect(
                partial(self.onUnselectSignals, False))
            # Add to submenu
            menu_unselect.addAction(action_onUnselectSignals)

            # Add menu item to unselect all signals - All DTVs
            action_onUnselectSignalsAll = QAction('All IMAS Databases',
                                                  self)
            action_onUnselectSignalsAll.triggered.connect(
                partial(self.onUnselectSignals, True))
            # Add to submenu
            menu_unselect.addAction(action_onUnselectSignalsAll)
            # TODO
            # Set bitmap to menu item

        # ----------------------------------------------------------------------
        # SET MENU FOR NEW PLOT HANDLING
        menu_plotSelection_figure = menu_plotSelection.addMenu('Figure')

        # Add action to plot the signal data to a new figure
        action_plotNewFigure = QAction('New', self)
        action_plotNewFigure.triggered.connect(self.plotSignalCommand)
        menu_plotSelection_figure.addAction(action_plotNewFigure)

        # Create and add empty submenu to handle figures deletion
        subMenu_deleteFigure = menu_delete.addMenu('Figure')

        submenu_showHideFigure = menu_showHide.addMenu('Figure')

        for figureKey in self.api.GetFiguresKeys(
                figureType=FigureTypes.FIGURETYPE):
            # Get figure number out from the figureKey string
            # (e.g. 'Figure:0' -> 0)
            # id_Fig = int(figureKey.split(':')[1])
            id_Fig = self.api.getFigureKeyNum(figureKey)

            # --------------------------------------------------------------
            # Add menu item to add plot to specific existing figure
            # Check for figures that share the same coordinates
            if self.shareSameCoordinatesFrom(figureKey):
                # Set action
                action_addSignalPlotToFig = QAction(figureKey, self)
                action_addSignalPlotToFig.triggered.connect(
                    partial(self.addSignalPlotToFig, id_Fig))
                # Add to submenu
                menu_plotSelection_figure.addAction(action_addSignalPlotToFig)

            # --------------------------------------------------------------
            # Add menu item to show/hide existing figure
            # Set action
            action_showHideFigure = QAction(figureKey, self)
            action_showHideFigure.triggered.connect(
                partial(self.showHideFigure, id_Fig, FigureTypes.FIGURETYPE))
            # Add to submenu
            submenu_showHideFigure.addAction(action_showHideFigure)

            # --------------------------------------------------------------
            # Add menu item to delete existing figure
            # Set action
            action_deleteFigure = QAction(figureKey, self)
            action_deleteFigure.triggered.connect(
                partial(self.deleteFigure, id_Fig))
            # Add to submenu
            subMenu_deleteFigure.addAction(action_deleteFigure)

        # ------------------------------------------------------------------
        # Add menu item to delete all existing figures
        # Set action
        action_deleteAllFigures = QAction('All', self)
        action_deleteAllFigures.triggered.connect(partial(
            self.deleteAllFigures, figureType=FigureTypes.FIGURETYPE))
        # Add to submenu
        subMenu_deleteFigure.addAction(action_deleteAllFigures)
        # Bitmap icon
        # TODO

        # ------------------------------------------------------------------
        # Add submenu to add plot selected signals to specific existing
        # figure, if selected signals are present
        if len(self.dataTreeView.selectedSignalsDict) > 0 \
            and self.shareSameCoordinates(self.dataTreeView.selectedSignalsDict):
            # Create and add empty submenu to main menu

            submenu_plotSelectedNodes_figure = menu_plotSelectedNodes.addMenu('Figure')

            submenu_plotSelectedNodes_figure_new = submenu_plotSelectedNodes_figure.addMenu('New')

            # --------------------------------------------------------------
            # Add menu item to plot selected signals to single
            # plot - This DTV
            action_plotSelectedSignals = QAction('This IMAS Database',
                                                 self)
            action_plotSelectedSignals.triggered.connect(
                partial(self.plotSelectedSignals, False))
            # Add to submenu
            submenu_plotSelectedNodes_figure_new.addAction(action_plotSelectedSignals)

            # --------------------------------------------------------------
            # Add menu item to plot selected signals to single
            # plot - All DTVs
            action_plotSelectedSignals = QAction('All IMAS Databases',
                                                 self)
            action_plotSelectedSignals.triggered.connect(
                partial(self.plotSelectedSignals, True))
            # Add to submenu
            submenu_plotSelectedNodes_figure_new.addAction(action_plotSelectedSignals)

            for figureKey in self.api.GetFiguresKeys(
                    figureType=FigureTypes.FIGURETYPE):
                # Check for figures that share the same coordinates
                if self.shareSameCoordinatesFrom(figureKey):
                    # Get figure number id out from the figureKey string
                    # (e.g. 'Figure:0' -> 0)
                    # id_Fig = int(figureKey.split(':')[1])
                    id_Fig = self.api.getFigureKeyNum(figureKey)
                    # Add menu item to add plot to specific figure
                    action_addSelectedSignalsPlotToFig = \
                        QAction(figureKey, self)
                    action_addSelectedSignalsPlotToFig.triggered.connect(
                        partial(self.addSelectedSignalsPlotToFig, id_Fig))
                    # Add to submenu
                    submenu_plotSelectedNodes_figure.addAction(action_addSelectedSignalsPlotToFig)
        # Bitmap icon
        # TODO

        # ----------------------------------------------------------------------
        # Set submenu for handling features for plotting selected signals to new
        # TablePlotView and StackedPlotView
        if len(self.dataTreeView.selectedSignalsDict) > 0:
            # ------------------------------------------------------------------
            # TablePlotView
            submenu_plotSelectedNodes_TPV = menu_plotSelectedNodes.addMenu('TablePlotView')

            submenu_plotSelectedNodes_TPV_new = submenu_plotSelectedNodes_TPV.addMenu('New')

            # -----
            # Add menu item to plot selected signals to single
            # plot - This DTV
            action_multiPlotSelectedSignals = QAction('This IMAS Database',
                                                      self)
            action_multiPlotSelectedSignals.triggered.connect(
                partial(self.onPlotToTablePlotView, False))
            # Add to submenu
            submenu_plotSelectedNodes_TPV_new.addAction(action_multiPlotSelectedSignals)

            # -----
            # Add menu item to plot selected signals to single
            # plot - All DTVs
            action_multiPlotSelectedSignals = QAction('All IMAS Databases',
                                                      self)
            action_multiPlotSelectedSignals.triggered.connect(
                partial(self.onPlotToTablePlotView, True))
            # Add to submenu
            submenu_plotSelectedNodes_TPV_new.addAction(action_multiPlotSelectedSignals)

            # ------------------------------------------------------------------
            # StackedPlotView
            submenu_plotSelectedNodes_SPV = menu_plotSelectedNodes.addMenu('StackedPlotView')

            submenu_plotSelectedNodes_SPV_new = submenu_plotSelectedNodes_SPV.addMenu('New')

            # -----
            # Add menu item to plot selected signals to single
            # plot - This DTV
            action_subPlotSelectedSignals = QAction('This IMAS Database',
                                                    self)
            action_subPlotSelectedSignals.triggered.connect(
                partial(self.onPlotToStackedPlotView, False))
            # Add to submenu
            submenu_plotSelectedNodes_SPV_new.addAction(action_subPlotSelectedSignals)

            # -----
            # Add menu item to plot selected signals to single
            # plot - All DTVs
            action_subPlotSelectedSignals = QAction('All IMAS Databases',
                                                    self)
            action_subPlotSelectedSignals.triggered.connect(
                partial(self.onPlotToStackedPlotView, True))
            # Add to submenu
            submenu_plotSelectedNodes_SPV_new.addAction(action_subPlotSelectedSignals)

        # Set handling existing TablePlotViews
        if numTPV > 0:
            # Create and add empty submenu to handle show/hide figures
            subMenu_showHideTPV = menu_showHide.addMenu('TablePlotView')

            # Create and add empty submenu to handle figures deletion
            subMenu_deleteTPV = QMenu('TablePlotView')
            menu_delete.addMenu(subMenu_deleteTPV)

            for figureKey in self.api.GetFiguresKeys(
                figureType=FigureTypes.TABLEPLOTTYPE):
                # Get figure id number out from the figureKey string
                # (e.g. 'Figure:0' -> 0)
                id_TPV = self.api.getFigureKeyNum(figureKey)

                # --------------------------------------------------------------
                # Add menu item to add plot to specific existing figure
                # Check for figures that share the same coordinates
                # TODO
                # if self.shareSameCoordinatesFrom(figureKey):
                #     # Set action
                #     action_addSignalPlotToFig = QAction(figureKey, self)
                #     action_addSignalPlotToFig.triggered.connect(
                #         partial(self.addSignalPlotToFig, numTPV))
                #     # Add to submenu
                #     menu_plotSelectedNodes.addAction(action_addSignalPlotToFig)

                # --------------------------------------------------------------
                # Add menu item to show/hide existing figure
                # Set action
                action_showHideTPV = QAction(figureKey, self)
                action_showHideTPV.triggered.connect(
                    partial(self.showHideFigure, id_TPV,
                            figureType=FigureTypes.TABLEPLOTTYPE))
                # Add to submenu
                subMenu_showHideTPV.addAction(action_showHideTPV)

                # --------------------------------------------------------------
                # Add menu item to delete existing figure
                # Set action
                action_deleteTPV = QAction(figureKey, self)
                action_deleteTPV.triggered.connect(
                    partial(self.deleteFigure, id_TPV,
                            figureType=FigureTypes.TABLEPLOTTYPE))
                # Add to submenu
                subMenu_deleteTPV.addAction(action_deleteTPV)

            # ------------------------------------------------------------------
            # Add menu item to delete all existing figures
            # Set action
            action_deleteAllTPV = QAction('All', self)
            action_deleteAllTPV.triggered.connect(partial(
                self.deleteAllFigures, figureType=FigureTypes.TABLEPLOTTYPE))
            # Add to submenu
            subMenu_deleteTPV.addAction(action_deleteAllTPV)

        # Set handling existing StackedPlotViews
        if numSPV > 0:
            # Create and add empty submenu to handle show/hide
            subMenu_showHideSPV = menu_showHide.addMenu('StackedPlotView')

            # Create and add empty submenu to handle figures deletion
            subMenu_deleteSPV = QMenu('StackedPlotView')
            menu_delete.addMenu(subMenu_deleteSPV)

            for figureKey in self.api.GetFiguresKeys(
                figureType=FigureTypes.STACKEDPLOTTYPE):
                # Get figure id number out from the figureKey string
                # (e.g. 'Figure:0' -> 0)
                id_SPV = self.api.getFigureKeyNum(figureKey)

                # --------------------------------------------------------------
                # Add menu item to add plot to specific existing figure
                # Check for figures that share the same coordinates
                # TODO
                # if self.shareSameCoordinatesFrom(figureKey):
                #     # Set action
                #     action_addSignalPlotToFig = QAction(figureKey, self)
                #     action_addSignalPlotToFig.triggered.connect(
                #         partial(self.addSignalPlotToFig, numSPV))
                #     # Add to submenu
                #     menu_plotSelectedNodes.addAction(action_addSignalPlotToFig)

                # --------------------------------------------------------------
                # Add menu item to show/hide existing figure
                # Set action
                action_showHideSPV = QAction(figureKey, self)
                action_showHideSPV.triggered.connect(
                    partial(self.showHideFigure, id_SPV,
                            figureType=FigureTypes.STACKEDPLOTTYPE))
                # Add to submenu
                subMenu_showHideSPV.addAction(action_showHideSPV)

                # --------------------------------------------------------------
                # Add menu item to delete existing figure
                # Set action
                action_deleteSPV = QAction(figureKey, self)
                action_deleteSPV.triggered.connect(
                    partial(self.deleteFigure, id_SPV,
                            figureType=FigureTypes.STACKEDPLOTTYPE))
                # Add to submenu
                subMenu_deleteSPV.addAction(action_deleteSPV)

            # ------------------------------------------------------------------
            # Add menu item to delete all existing figures
            # Set action
            action_deleteAllSPV = QAction('All', self)
            action_deleteAllSPV.triggered.connect(partial(
                self.deleteAllFigures, figureType=FigureTypes.TABLEPLOTTYPE))
            # Add to submenu
            subMenu_deleteSPV.addAction(action_deleteAllSPV)

            # TODO:
            """
            - 'Show/Hide subplots'
            - 'Add selection to TablePlotView'
            - 'Delete subplot'
            - 'Open subplots manager'
            - 'Plot ' + signalName + ' as a function of time'
            """

        # Map the menu (in order to show it)
        self.dataTreeView.popupmenu.exec_(
            self.dataTreeView.viewport().mapToGlobal(self.dataTreeView.pos))
        return 1

    def selectSignal(self):
        QVizSelectOrUnselectSignal(self.dataTreeView, self.nodeData).execute()

    @pyqtSlot()
    def selectOrUnselectSignal(self):
        QVizSelectOrUnselectSignal(self.dataTreeView, self.nodeData).execute()

    @pyqtSlot(bool)
    def onUnselectSignals(self, all_DTV=False):
        """Unselect all signals (single or all DTVs)."""
        QVizUnselectAllSignals(self.dataTreeView, all_DTV).execute()

    @pyqtSlot()
    def selectAllSignalsFromSameAOS(self):
        QVizSelectSignalsGroup(self.dataTreeView, self.nodeData).execute()

    @pyqtSlot()
    def plotSignalCommand(self):
        try:
            self.currentFigureKey = self.api.GetNextKeyForFigurePlots()
            label = None
            xlabel = None
            # if self.treeNode is not None and self.treeNode.time_dependent_aos():
            #     aos_vs_itime = self.treeNode.getDataPathVsTime(self.treeNode.aos)
            #     label = self.treeNode.getDataPath(aos_vs_itime, 0)
            #     label = label.replace("ids.", "")
            #     label = QVizGlobalOperations.replaceBrackets(label)
            #     label = QVizGlobalOperations.replaceDotsBySlashes(label)
            #     xlabel = \
            #         QVizGlobalOperations.replaceBrackets(self.treeNode.evaluateCoordinate1At(0))
            #     self.timeSlider = True
            # else:
            #     self.timeSlider = None
            # Get the signal data for plot widget
            p = QVizPlotSignal(self.dataTreeView, self.nodeData, signal=None,
                               figureKey=self.currentFigureKey, label=label,
                               xlabel=xlabel, signalHandling=self)
            # Plot signal data to plot widget
            p.execute()

        except ValueError as e:
            self.dataTreeView.log.error(str(e))

    def plotPreviewSignalCommand(self):
        """Show preview plot.
        """
        try:
            label = None
            xlabel = None

            # Get the signal data for preview plot update
            p = QVizPreviewPlotSignal(dataTreeView= self.dataTreeView,
                                      nodeData= self.nodeData,
                                      signal= None, label = label,
                                      xlabel= xlabel, signalHandling = self)
            # Plot signal data to preview plot widget
            p.execute()

        except ValueError as e:
            self.dataTreeView.log.error(str(e))

    # @pyqtSlot(bool)
    def plotSelectedSignals(self, all_DTV=True):
        """Plot selected signals from current or all DTV instances.

        Arguments:
            all_DTV (bool) : Boolean operator specifying if current or all DTVs
                             should be considered.
        """
        # Get label for the next figure (e.c. if 'Figure 2' already exists,
        # value 'Figure 3' will be returned)
        figureKey = self.api.GetNextKeyForFigurePlots()
        # Plot the selected signals
        if all_DTV == False:
            QVizPlotSelectedSignals(self.dataTreeView, figureKey,
                                    all_DTV=False).execute()
        else:
            QVizPlotSelectedSignals(self.dataTreeView, figureKey,
                                    all_DTV=True).execute()

    @pyqtSlot(bool)
    def onPlotToTablePlotView(self, all_DTV=False):
        """Plot selected nodes from single/all opened DTVs to MultiPlot
        TablePlotView.

        Arguments:
            all_DTV (bool) : Operator to read selected signals from the
                             current or all DTVs.
        """
        # Get next figure key/label
        figureKey = self.dataTreeView.imas_viz_api.getNextKeyForTablePlotView()
        # Note: figureKey that includes 'TablePlotView' is expected
        if all_DTV != True:
            QVizMultiPlotWindow(dataTreeView=self.dataTreeView, figureKey=figureKey,
                                update=1, all_DTV=False)
        else:
            QVizMultiPlotWindow(dataTreeView=self.dataTreeView, figureKey=figureKey,
                                update=1, all_DTV=True)

    @pyqtSlot(bool)
    def onPlotToStackedPlotView(self, all_DTV=False):
        """Plot selected nodes from single/all opened DTVs to MultiPlot
        StackedPlotView.

        Arguments:
            all_DTV (bool) : Operator to read selected signals from the
                             current or all DTVs.
        """
        # Get next figure key/label
        figureKey = self.dataTreeView.imas_viz_api.getNextKeyForStackedPlotView()
        # Note: figureKey that includes 'StackedPlotView' is expected
        if all_DTV != True:
            QVizMultiPlotWindow(dataTreeView=self.dataTreeView, figureKey=figureKey,
                                update=1, all_DTV=False)
        else:
            QVizMultiPlotWindow(dataTreeView=self.dataTreeView, figureKey=figureKey,
                                update=1, all_DTV=True)

    @pyqtSlot(int)
    def addSignalPlotToFig(self, numFig):
        """Add signal plot to existing figure.

        Arguments:
            numFig (int) : Number identification of the existing figure.
        """
        try:
            # Get figure key (e.g. 'Figure:0' string)
            figureKey = self.api. \
                GetFigureKey(str(numFig), figureType=FigureTypes.FIGURETYPE)
            QVizPlotSignal(dataTreeView=self.dataTreeView,
                           nodeData=self.nodeData,
                           figureKey=figureKey,
                           update=1).execute()
        except ValueError as e:
            self.dataTreeView.log.error(str(e))

    @pyqtSlot(int)
    def addSelectedSignalsPlotToFig(self, numFig):
        """Add/Plot selected signals to existing figure.

        Arguments:
            numFig (int) : Number identification of the existing figure.
        """
        # Get figure key (e.g. 'Figure:0' string)
        figureKey = self.api. \
            GetFigureKey(str(numFig), figureType=FigureTypes.FIGURETYPE)

        QVizPlotSelectedSignals(self.dataTreeView, figureKey, update=1,
                                all_DTV=False).execute()

    def shareSameCoordinates(self, selectedDataList):
        """Check if data in selectedDataList (dict) share the same coordinates
        """

        selectedSignalsList = []
        for key in selectedDataList:
            v = selectedDataList[key]  # v is a map
            selectedSignalsList.append(v['QTreeWidgetItem'].getDataDict())

        s = self.nodeData
        for si in selectedSignalsList:
            if s['coordinate1'] != si['coordinate1']:
                return False
            s = si
        return True

    def shareSameCoordinatesFrom(self, figureKey):
        """Check if data already in figure and next to be added signal plot
        share the same coordinates.
        """
        selectedDataList = self.api.figToNodes[figureKey]

        selectedSignalsList = []
        for k in selectedDataList:
            v = selectedDataList[k]
            selectedSignalsList.append(v[1])  # v[0] = shot number,
                                            # v[1] = node data
        s = self.nodeData
        for si in selectedSignalsList:
            if s['coordinate1'] != si['coordinate1']:
                return False
            s = si
        return True

    @pyqtSlot(int, str)
    def showHideFigure(self, numFig, figureType=FigureTypes.FIGURETYPE):
        """Show/Hide figure plot widget window or TablePlotView frame.

        Arguments:
            numFig     (int) : Figure number identificator.
            figureType (str) : Type of figure e.c. "Figure:", "Multiplot:",
                               "Subplot"... see QVizGlobalValues.py FigureTypes
                               class for a full list of figure types.
        """
        # Get figure key (e.g. 'Figure:0' string)
        figureKey = \
            self.api.GetFigureKey(str(numFig), figureType)
        self.api.ShowHideFigure(figureKey)

    @pyqtSlot(str)
    def deleteAllFigures(self, figureType=FigureTypes.FIGURETYPE):
        figureKeys = self.api.GetFiguresKeys(figureType)
        for figureKey in figureKeys:
            self.api.DeleteFigure(figureKey)

    @pyqtSlot(int, str)
    def deleteFigure(self, numFig, figureType=FigureTypes.FIGURETYPE):
        """Delete figure plot widget window.

        Arguments:
            numFig     (int) : Figure number identificator.
            figureType (str) : Type of figure e.c. "Figure:", "Multiplot:",
                               "Subplot"... see QVizGlobalValues.py FigureTypes
                               class for a full list of figure types.
        """
        try:
            # Get figure key (e.g. 'Figure:0' string)
            figureKey = self.api. \
                GetFigureKey(str(numFig), figureType)
            self.api.DeleteFigure(figureKey)
        except ValueError as e:
            self.dataTreeView.log.error(str(e))
