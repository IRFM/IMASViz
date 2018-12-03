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
#    def plotSelectedSignalVsTime
#    def plotSelectedSignalVsTimeAtIndex
#    def plotSelectedSignalVsCoordAtTimeIndex
#    def addSignalSelectionToTablePlotViewFrame
#    def showStackedPlotViewsManager
#    def # onClose
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#****************************************************

# from imasviz.VizDataAccess.QVizDataAccessFactory import QVizDataAccessFactory
from functools import partial

from PyQt5.QtCore import QObject, pyqtSlot
from PyQt5.QtWidgets import QAction, QMenu, QWidget, QApplication
from PyQt5.QtGui import QIcon, QStyle
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizUtils.QVizGlobalValues import GlobalIcons

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
        self.imas_viz_api = self.dataTreeView.imas_viz_api
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

    def showPopUpMenu(self, signalNodeName):
        """Display the popup menu for plotting data.

        Arguments:
            signalNodeName (str) : Name of the signal node (tree item).
                               (example: ids.magnetics.flux_loop[0].flux.data)
        """

        # TODO: popup menu gets build every time on right-click. Maybe create
        #       it once and then only enable/disable menu items on right-click

        # Name of the node selection
        self.signalNodeName = signalNodeName

        # Do not proceed with building the context menu if the selected node is
        # not signal node
        if (self.signalNodeName == None):
            return 0

        # Set new popup menu
        self.dataTreeView.popupmenu = self.buildContextMenu()

        # Map the menu (in order to show it)
        self.dataTreeView.popupmenu.exec_(
            self.dataTreeView.viewport().mapToGlobal(self.dataTreeView.pos))
        return 1

    def buildContextMenu(self):
        """Build context menu.
        """

        # Get total count of figures, tablePlotViews, stackedPlotViews etc.
        numFig = self.imas_viz_api.GetFigurePlotsCount()
        numTPV = self.imas_viz_api.GetTablePlotViewsCount()
        numSPV = self.imas_viz_api.GetStackedPlotViewsCount()

        # Set new popup menu
        self.contextMenu = QMenu()

        # SET TOP ACTIONS
        # - Add action for setting signal node select/unselect status
        self.contextMenu.addAction(self.actionSelectOrUnselectSignalNode())

        # - Add action for selection of all signals from the same array of
        #   structures
        self.contextMenu.addAction(self.actionSelectAllSignalNodesFromSameAOS())

        # SET TOP MENU ITEMS
        # - Add menu for handling plotting using the under-the-mouse selected
        #   signal node
        self.contextMenu.addMenu(self.menuPlotCurrentSignalNode())

        # - Add menu for handling unselection of signal nodes
        self.contextMenu.addMenu(self.menuUnselectSignalNodes())

        # - Add menu for handling plotting a selection of signal nodes
        self.contextMenu.addMenu(
            self.menuPlotSelectedSignalNodes(parentMenu=self.contextMenu))

        # - Add menu for handling show/hide if figures, TablePlotViews and
        #   StackedPlotViews.
        menu_showHide, menu_delete = self.menusShowHideAndDelete(numFig, numTPV, numSPV)
        self.contextMenu.addMenu(menu_showHide)
        self.contextMenu.addMenu(menu_delete)

        # TODO:
        """
        - 'Show/Hide subplots'
        - 'Add selection to TablePlotView'
        - 'Delete subplot'
        - 'Open subplots manager'
        - 'Plot ' + self.signalNodeName + ' as a function of time'
        """
        return self.contextMenu

    def actionSelectOrUnselectSignalNode(self):
        """Set action to select/unselect signal node.
        """
        s = ''
        if self.nodeData['isSelected'] == 1:
            # If the node is selected, show unselect menu
            s = 'Unselect '
            # Bitmap icon
            icon = GlobalIcons.getCustomQIcon(QApplication, 'unselect')

            # TODO
        else:
            # The node is unselected, show select menu
            s = 'Select '
            # Bitmap icon
            icon = GlobalIcons.getCustomQIcon(QApplication, 'select')

        # Set action for selection/unselection of the node
        action = QAction(icon, s + self.signalNodeName + '...', self)
        action.triggered.connect(self.selectOrUnselectSignal)

        return action

    def actionSelectAllSignalNodesFromSameAOS(self):
        # Set action for selection of all signals from the same array of
        # structures
        icon = GlobalIcons.getCustomQIcon(QApplication, 'selectAOS')
        action = QAction(icon, 'Select all nodes from the same AOS', self)
        action.triggered.connect(
            self.selectAllSignalsFromSameAOS)
        # TODO
        # Set bitmap to menu item

        return action

    def menuPlotCurrentSignalNode(self):
        """Set menu for plotting current (under the mouse selected) signal node.
        """

        menu = QMenu('Plot ' + self.signalNodeName + ' to', self.contextMenu)
        menu.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'plotSingle'))

        menu_figure = menu.addMenu('Figure')
        menu_figure.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'Figure'))

        # Add action to plot the signal data to a new figure
        icon_new = GlobalIcons.getCustomQIcon(QApplication, 'new')
        action_plotNewFigure = QAction(icon_new, 'New', self)
        action_plotNewFigure.triggered.connect(self.plotSignalCommand)
        menu_figure.addAction(action_plotNewFigure)

        for figureKey in self.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.FIGURETYPE):
            # Get figure number out from the figureKey string
            # (e.g. 'Figure:0' -> 0)
            # id_Fig = int(figureKey.split(':')[1])
            id_Fig = self.imas_viz_api.getFigureKeyNum(figureKey)

            # Add menu item to add plot to specific existing figure
            # Check for figures that share the same coordinates
            if self.shareSameCoordinatesFrom(figureKey):
                # Set action
                action_addSignalPlotToFig = QAction(figureKey, self)
                action_addSignalPlotToFig.triggered.connect(
                    partial(self.addSignalPlotToFig, id_Fig))
                # Add to submenu
                menu_figure.addAction(action_addSignalPlotToFig)

        return menu


    def menuUnselectSignalNodes(self):
        """Set menu for selected signal nodes unselection.
        """

        # Set menu
        menu = QMenu('Unselect Nodes', self.contextMenu)
        menu.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'unselectMultiple'))
        # Set disables as default
        menu.setDisabled(True)

        # If selected signals list exists, set actions for unselection of all
        # selected signals and enable the menu item
        if len(self.dataTreeView.selectedSignalsDict) > 0:
            menu.setDisabled(False)

            # Add menu item to unselect all signals - This/Current DTV
            icon_thisDTV = GlobalIcons.getCustomQIcon(QApplication, 'thisDTV')
            action_onUnselectSignals = QAction(icon_thisDTV, 'This IMAS Database',
                                               self)
            action_onUnselectSignals.triggered.connect(
                partial(self.onUnselectSignals, False))
            # Add to submenu
            menu.addAction(action_onUnselectSignals)

            # Add menu item to unselect all signals - All DTVs
            icon_allDTV = GlobalIcons.getCustomQIcon(QApplication, 'allDTV')
            action_onUnselectSignalsAll = QAction(icon_allDTV,
                                                  'All IMAS Databases', self)
            action_onUnselectSignalsAll.triggered.connect(
                partial(self.onUnselectSignals, True))
            # Add to submenu
            menu.addAction(action_onUnselectSignalsAll)
            # TODO
            # Set bitmap to menu item

        return menu

    def menuPlotSelectedSignalNodes(self, parentMenu):
        """Set menu for handling plotting a selection of signal nodes.
        """

        menu = QMenu('Plot selected nodes to', parentMenu)
        menu.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'plotMultiple'))
        menu.setDisabled(True)

        if len(self.dataTreeView.selectedSignalsDict) > 0:
            menu.setDisabled(False)

            subMenu_figure = menu.addMenu('Figure')
            subMenu_figure.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'Figure'))
            subMenu_figure_new = subMenu_figure.addMenu('New')
            subMenu_figure_new.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'new'))

            # --------------------------------------------------------------
            # Add menu item to plot selected signals to single
            # plot - This DTV
            icon_thisDTV = GlobalIcons.getCustomQIcon(QApplication, 'thisDTV')
            action_figure_thisDTV = QAction(icon_thisDTV, 'This IMAS Database', self)
            action_figure_thisDTV.triggered.connect(
                partial(self.plotSelectedSignals, False))
            # Add to submenu
            subMenu_figure_new.addAction(action_figure_thisDTV)

            # --------------------------------------------------------------
            # Add menu item to plot selected signals to single
            # plot - All DTVs

            icon_allDTV = GlobalIcons.getCustomQIcon(QApplication, 'allDTV')
            action_figure_allDTV = QAction(icon_allDTV, 'All IMAS Databases',
                                                 self)
            action_figure_allDTV.triggered.connect(
                partial(self.plotSelectedSignals, True))
            # Add to submenu
            subMenu_figure_new.addAction(action_figure_allDTV)

            # TODO: do same for TablePlotView and StackedPlotView
            for figureKey in self.imas_viz_api.GetFiguresKeys(
                    figureType=FigureTypes.FIGURETYPE):
                # Check for figures that share the same coordinates
                if self.shareSameCoordinatesFrom(figureKey):
                    # Get figure number id out from the figureKey string
                    # (e.g. 'Figure:0' -> 0)
                    # id_Fig = int(figureKey.split(':')[1])
                    id_Fig = self.imas_viz_api.getFigureKeyNum(figureKey)
                    # Add menu item to add plot to specific figure
                    subMenu_figure_existing = subMenu_figure.addMenu(figureKey)
                    # Add menu item to plot selected signals to existing
                    # plot - This DTV
                    action_figure_ex_thisDTV = \
                        QAction(icon_thisDTV, 'This IMAS Database', self)
                    action_figure_ex_thisDTV.triggered.connect(
                        partial(self.addSelectedSignalsPlotToFig, id_Fig, False))
                    # Add to submenu
                    subMenu_figure_existing.addAction(action_figure_ex_thisDTV)
                    # Add menu item to plot selected signals to existing
                    # plot - All DTV
                    action_figure_ex_allDTV = \
                        QAction(icon_thisDTV, 'All IMAS Databases', self)
                    action_figure_ex_allDTV.triggered.connect(
                        partial(self.addSelectedSignalsPlotToFig, id_Fig, True))
                    # Add to submenu
                    subMenu_figure_existing.addAction(action_figure_ex_allDTV)

            # ------------------------------------------------------------------
            # TablePlotView
            subMenu_TPV = menu.addMenu('TablePlotView')
            subMenu_TPV.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'TPV'))

            subMenu_TPV_new = subMenu_TPV.addMenu('New')
            subMenu_TPV_new.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'new'))

            # -----
            # Add menu item to plot selected signals to single
            # plot - This DTV
            icon_thisDTV = GlobalIcons.getCustomQIcon(QApplication, 'thisDTV')
            action_TPV_thisDTV = QAction(icon_thisDTV, 'This IMAS Database', self)
            action_TPV_thisDTV.triggered.connect(
                partial(self.onPlotToTablePlotView, False))
            # Add to submenu
            subMenu_TPV_new.addAction(action_TPV_thisDTV)

            # -----
            # Add menu item to plot selected signals to single
            # plot - All DTVs
            icon_allDTV = GlobalIcons.getCustomQIcon(QApplication, 'allDTV')
            action_TPV_allDTV = QAction(icon_allDTV, 'All IMAS Databases', self)
            action_TPV_allDTV.triggered.connect(
                partial(self.onPlotToTablePlotView, True))
            # Add to submenu
            subMenu_TPV_new.addAction(action_TPV_allDTV)

            # ------------------------------------------------------------------
            # StackedPlotView
            subMenu_SPV = menu.addMenu('StackedPlotView')
            subMenu_SPV.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'SPV'))

            subMenu_SPV_new = subMenu_SPV.addMenu('New')
            subMenu_SPV_new.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'new'))

            # -----
            # Add menu item to plot selected signals to single
            # plot - This DTV
            action_SPV_thisDTV = QAction(icon_thisDTV, 'This IMAS Database', self)
            action_SPV_thisDTV.triggered.connect(
                partial(self.onPlotToStackedPlotView, False))
            # Add to submenu
            subMenu_SPV_new.addAction(action_SPV_thisDTV)

            # -----
            # Add menu item to plot selected signals to single
            # plot - All DTVs
            action_SPV_allDTV = QAction(icon_allDTV, 'All IMAS Databases', self)
            action_SPV_allDTV.triggered.connect(
                partial(self.onPlotToStackedPlotView, True))
            # Add to submenu
            subMenu_SPV_new.addAction(action_SPV_allDTV)

        return menu

    def menusShowHideAndDelete(self, numFig, numTPV, numSPV):
        """Set two menus: first  for handling show/hide and second for deleting
        of existing figures, TablePlotViews and StackedPlotViews.
        """

        # Create and add empty menu to handle show/hide status of plot views and
        # figures
        menu_showHide = QMenu('Show/Hide', self.contextMenu)
        menu_showHide.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'showHide'))

        menu_showHide.setDisabled(True)
        # Create and add empty menu to handle deletion of plot views and
        # figures
        menu_delete = QMenu('Delete', self.contextMenu)
        menu_delete.setIcon(GlobalIcons.getStandardQIcon(QApplication, QStyle.SP_DialogDiscardButton))
        menu_delete.setDisabled(True)

        if numFig > 0 or numTPV > 0 or numSPV > 0:
            menu_showHide.setDisabled(False)
            menu_delete.setDisabled(False)

        # Set handling existing figures
        if numFig > 0:

            # Create and add empty submenu to handle figures show/hide
            submenu_showHideFigure = menu_showHide.addMenu('Figure')
            submenu_showHideFigure.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'Figure'))
            # Create and add empty submenu to handle figures deletion
            subMenu_deleteFigure = menu_delete.addMenu('Figure')
            subMenu_deleteFigure.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'Figure'))

            for figureKey in self.imas_viz_api.GetFiguresKeys(
                    figureType=FigureTypes.FIGURETYPE):
                # Get figure number out from the figureKey string
                # (e.g. 'Figure:0' -> 0)
                # id_Fig = int(figureKey.split(':')[1])
                id_Fig = self.imas_viz_api.getFigureKeyNum(figureKey)

                # --------------------------------------------------------------
                # Add menu item to show/hide existing figure
                # Set action
                action_showHide_figure = QAction(figureKey, self)
                action_showHide_figure.triggered.connect(
                    partial(self.showHideFigure, id_Fig, FigureTypes.FIGURETYPE))
                # Add to submenu
                submenu_showHideFigure.addAction(action_showHide_figure)

                # --------------------------------------------------------------
                # Add menu item to delete existing figure
                # Set action
                action_delete_figure = QAction(figureKey, self)
                action_delete_figure.triggered.connect(
                    partial(self.deleteFigure, id_Fig, FigureTypes.FIGURETYPE))
                # Add to submenu
                subMenu_deleteFigure.addAction(action_delete_figure)

            # ------------------------------------------------------------------
            # Add menu item to delete all existing figures
            # Set action
            action_deleteAll_figure = QAction('All', self)
            action_deleteAll_figure.triggered.connect(partial(
                self.deleteAllFigures, figureType=FigureTypes.FIGURETYPE))
            # Add to submenu
            subMenu_deleteFigure.addAction(action_deleteAll_figure)
            # Bitmap icon
            # TODO

        # Set handling existing TablePlotViews
        if numTPV > 0:
            # Create and add empty submenu to handle show/hide tablePlotViews
            subMenu_showHideTPV = menu_showHide.addMenu('TablePlotView')
            subMenu_showHideTPV.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'TPV'))
            # Create and add empty submenu to handle tablePlotViews deletion
            subMenu_deleteTPV = menu_delete.addMenu('TablePlotView')
            subMenu_deleteTPV.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'TPV'))

            for figureKey in self.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.TABLEPLOTTYPE):
                # Get figure id number out from the figureKey string
                # (e.g. 'Figure:0' -> 0)
                id_TPV = self.imas_viz_api.getFigureKeyNum(figureKey)

                # --------------------------------------------------------------
                # Add menu item to show/hide existing figure
                # Set action
                action_showHide_TPV = QAction(figureKey, self)
                action_showHide_TPV.triggered.connect(
                    partial(self.showHideFigure, id_TPV,
                            figureType=FigureTypes.TABLEPLOTTYPE))
                # Add to submenu
                subMenu_showHideTPV.addAction(action_showHide_TPV)

                # --------------------------------------------------------------
                # Add menu item to delete existing figure
                # Set action
                action_delete_TPV = QAction(figureKey, self)
                action_delete_TPV.triggered.connect(
                    partial(self.deleteFigure, id_TPV,
                            figureType=FigureTypes.TABLEPLOTTYPE))
                # Add to submenu
                subMenu_deleteTPV.addAction(action_delete_TPV)

            # ------------------------------------------------------------------
            # Add menu item to delete all existing figures
            # Set action
            action_deleteAll_TPV = QAction('All', self)
            action_deleteAll_TPV.triggered.connect(partial(
                self.deleteAllFigures, figureType=FigureTypes.TABLEPLOTTYPE))
            # Add to submenu
            subMenu_deleteTPV.addAction(action_deleteAll_TPV)

        # Set handling existing StackedPlotViews
        if numSPV > 0:
            # Create and add empty submenu to handle show/hide
            subMenu_showHideSPV = menu_showHide.addMenu('StackedPlotView')
            subMenu_showHideSPV.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'SPV'))
            # Create and add empty submenu to handle deletion
            subMenu_deleteSPV = menu_delete.addMenu('StackedPlotView')
            subMenu_deleteSPV.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'SPV'))

            for figureKey in self.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.STACKEDPLOTTYPE):
                # Get figure id number out from the figureKey string
                # (e.g. 'Figure:0' -> 0)
                id_SPV = self.imas_viz_api.getFigureKeyNum(figureKey)

                # --------------------------------------------------------------
                # Add menu item to show/hide existing figure
                # Set action
                action_showHide_SPV = QAction(figureKey, self)
                action_showHide_SPV.triggered.connect(
                    partial(self.showHideFigure, id_SPV,
                            figureType=FigureTypes.STACKEDPLOTTYPE))
                # Add to submenu
                subMenu_showHideSPV.addAction(action_showHide_SPV)

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

        return menu_showHide, menu_delete

    def updateNodeData(self):
        """ Update tree node/item data.
            TODO: use the global routine 'updateNodeData' defined in
                  QVizAbstractCommand instead.
        """
        self.nodeData = self.dataTreeView.selectedItem.getDataDict()
        self.treeNode = self.dataTreeView.selectedItem

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
            self.currentFigureKey = self.imas_viz_api.GetNextKeyForFigurePlots()
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
        figureKey = self.imas_viz_api.GetNextKeyForFigurePlots()
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
            figureKey = self.imas_viz_api. \
                GetFigureKey(str(numFig), figureType=FigureTypes.FIGURETYPE)
            QVizPlotSignal(dataTreeView=self.dataTreeView,
                           nodeData=self.nodeData,
                           figureKey=figureKey,
                           update=1).execute()
        except ValueError as e:
            self.dataTreeView.log.error(str(e))

    @pyqtSlot(int)
    def addSelectedSignalsPlotToFig(self, numFig, all_DTV=False):
        """Add/Plot selected signals to existing figure.

        Arguments:
            numFig (int) : Number identification of the existing figure.
        """
        # Get figure key (e.g. 'Figure:0' string)
        figureKey = self.imas_viz_api. \
            GetFigureKey(str(numFig), figureType=FigureTypes.FIGURETYPE)

        QVizPlotSelectedSignals(self.dataTreeView, figureKey, update=1,
                                all_DTV=all_DTV).execute()

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
        selectedDataList = self.imas_viz_api.figToNodes[figureKey]

        selectedSignalsList = []
        for k in selectedDataList:
            v = selectedDataList[k]
            selectedSignalsList.append(v[1])  # v[0] = shot number,
                                            # v[1] = node data
        s = self.nodeData

        if s['isSignal'] != 1:
            # For cases when running the QVizSignalHandling features from
            # DTV menubar and no selected signal is set
            # TODO: Code proper improvement necessary
            s = selectedSignalsList[0] # Set first selected signals as the
                                       # DTV selection (blue highlighted)
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
            self.imas_viz_api.GetFigureKey(str(numFig), figureType)
        self.imas_viz_api.ShowHideFigure(figureKey)

    @pyqtSlot(str)
    def deleteAllFigures(self, figureType=FigureTypes.FIGURETYPE):
        figureKeys = self.imas_viz_api.GetFiguresKeys(figureType)
        for figureKey in figureKeys:
            self.imas_viz_api.DeleteFigure(figureKey)

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
            figureKey = self.imas_viz_api. \
                GetFigureKey(str(numFig), figureType)
            self.imas_viz_api.DeleteFigure(figureKey)
        except ValueError as e:
            self.dataTreeView.log.error(str(e))
