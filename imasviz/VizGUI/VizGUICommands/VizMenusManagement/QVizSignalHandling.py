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
#    def addSignalSelectionToTablePlotViewFrame
#    def showStackedPlotViewsManager
#    def # onClose
#
#****************************************************
#     Copyright(c) 2016- L. Fleury, L. Xinyi, D. Penko
#****************************************************

from functools import partial
import re, logging
from PyQt5.QtCore import QObject, pyqtSlot
from PyQt5.QtWidgets import QAction, QMenu, QWidget, QApplication, QStyle
from PyQt5.QtGui import QIcon
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizUtils.QVizGlobalValues import GlobalIcons

from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPlotWidget import QVizPlotWidget
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizTablePlotView import QVizTablePlotView
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizMultiPlotWindow import QVizMultiPlotWindow
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizStackedPlotView import QVizStackedPlotView
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSelectedSignals import QVizPlotSelectedSignals
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal import QVizPlotSignal
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPreviewPlotSignal import QVizPreviewPlotSignal
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectOrUnselectSignal import QVizSelectOrUnselectSignal
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignalsGroup import QVizSelectSignalsGroup
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizUnselectAllSignals import QVizUnselectAllSignals
from imasviz.VizDataAccess.QVizDataAccessFactory import QVizDataAccessFactory
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizPluginsPopUpMenu import QVizPluginsPopUpMenu
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
        self.plotFrame = None
        self.currentFigureKey = None
        # Get signal node (tree item) data
        self.nodeData = None
        if self.dataTreeView.selectedItem != None:
            self.nodeData = self.dataTreeView.selectedItem.getInfoDict()
        self.treeNode = self.dataTreeView.selectedItem

    def buildContextMenu(self, signalNode):
        """Build context menu.
        """

        self.signalNodeName = signalNode.getDataName()

        # Get total count of figures, tablePlotViews, stackedPlotViews etc.
        numFig = self.imas_viz_api.GetFigurePlotsCount()
        numTPV = self.imas_viz_api.GetTablePlotViewsCount()
        numSPV = self.imas_viz_api.GetStackedPlotViewsCount()

        # Set new popup menu
        self.contextMenu = QMenu()

        if not self.treeNode.is2DOrLarger():

            # SET TOP ACTIONS
            # - Add action for setting signal node select/unselect status
            if self.treeNode.is0DAndDynamic() or self.treeNode.is1DAndDynamic():
                self.contextMenu.addAction(self.actionSelectOrUnselectSignalNode())

            # - Add action for selection of all signals from the same array of
            #   structures
            if self.treeNode.is1DAndDynamic():
                if self.nodeData.get('aos_parents_count') != '0':
                    self.contextMenu.addAction(self.actionSelectAllSignalNodesFromSameAOS())

            # SET TOP MENU ITEMS
            # - Add menu for handling plotting using the under-the-mouse selected
            #   signal node
            if self.treeNode.is1DAndDynamic():
                self.contextMenu.addMenu(self.menuPlotCurrentSignalNode())
            elif self.treeNode.is0DAndDynamic():
                self.contextMenu.addMenu(self.menuPlotCurrentSignal0DNode())

            # - Add menu for handling unselection of signal nodes
            if self.treeNode.is0DAndDynamic() or self.treeNode.is1DAndDynamic():
                self.contextMenu.addMenu(self.menuUnselectSignalNodes())

            # - Add menu for handling plotting a selection of signal nodes
            if self.treeNode.is0DAndDynamic() or self.treeNode.is1DAndDynamic():
                self.contextMenu.addMenu(
                    self.menuPlotSelectedSignalNodes(parentMenu=self.contextMenu))

        # - Add menu for handling show/hide if figures, TablePlotViews and
        #   StackedPlotViews.
        self.menusShowHideAndDelete(numFig, numTPV, numSPV, self.contextMenu)
        self.menusPlugins()

        # TODO:
        """
        - 'Show/Hide subplots'
        - 'Add selection to TablePlotView'
        - 'Delete subplot'
        - 'Open subplots manager'
        """
        return self.contextMenu

    def menusPlugins(self):
        # Create the sub menu for plugins
        self.pluginsPopUpMenu = QVizPluginsPopUpMenu()
        sub_menu = self.contextMenu.addMenu('Plugins')
        self.pluginsPopUpMenu.upateMenu(self.treeNode, self.dataTreeView, sub_menu)


    def actionPlotAsFunctionOfTime(self):
        # Add action to plot the signal data as a function of time
        # TODO: icon
        action_plotAsFunctionOfTime = None
        if self.treeNode.is1DAndDynamic() and self.treeNode.treeNodeExtraAttributes.time_dependent(
                        self.treeNode.treeNodeExtraAttributes.parametrizedPath):
            icon = GlobalIcons.getCustomQIcon(QApplication, 'plotSingle')
            action_plotAsFunctionOfTime = QAction(icon, 'Plot as function of time', self)
            action_plotAsFunctionOfTime.triggered.connect(self.plotSignalVsTimeCommand)
            action_plotAsFunctionOfTime.setDisabled(False)

        return action_plotAsFunctionOfTime


    def actionSelectOrUnselectSignalNode(self):
        """Set action to select/unselect signal node.
        """
        s = ''
        if self.nodeData['isSelected'] == 1:
            # If the node is selected, show unselect menu
            s = 'Unselect '
            # Bitmap icon
            icon = GlobalIcons.getCustomQIcon(QApplication, 'unselect')
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
        # - Add action for ploting signal node as a function of time
        if self.actionPlotAsFunctionOfTime() is not None:
            self.contextMenu.addAction(self.actionPlotAsFunctionOfTime())

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
            if self.nodeDataShareSameCoordinates(figureKey, self.nodeData):
                # Set action
                action_addSignalPlotToFig = QAction(figureKey, self)
                action_addSignalPlotToFig.triggered.connect(
                    partial(self.addSignalPlotToFig, id_Fig))
                # Add to submenu
                menu_figure.addAction(action_addSignalPlotToFig)


        return menu

    def menuPlotCurrentSignal0DNode(self):
        """Set menu for plotting current (under the mouse selected) signal node.
        """
        menu = QMenu('Plot ' + self.signalNodeName + ' to', self.contextMenu)
        menu.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'plotSingle'))

        icon_new = GlobalIcons.getCustomQIcon(QApplication, 'new')
        action_plotNewFigure = QAction(icon_new, 'New', self)
        action_plotNewFigure.triggered.connect(self.plot0D_DataVsTimeCommand)

        menu_figure = menu.addMenu('Figure')
        menu_figure.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'Figure'))
        menu_figure.addAction(action_plotNewFigure)

        for figureKey in self.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.FIGURETYPE):
            # Get figure number out from the figureKey string
            # (e.g. 'Figure:0' -> 0)
            # id_Fig = int(figureKey.split(':')[1])
            id_Fig = self.imas_viz_api.getFigureKeyNum(figureKey)

            # Add menu item to add plot to specific existing figure
            # Check for figures that share the same coordinates
            if self.nodeDataShareSameCoordinates(figureKey, self.nodeData):
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
        menu.setObjectName('Plot selected nodes to')

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
            icon_allDTV = GlobalIcons.getCustomQIcon(QApplication, 'allDTV')
            if self.shareSameCoordinates(self.dataTreeView.selectedSignalsDict):
                action_figure_thisDTV = QAction(icon_thisDTV, 'This IMAS Database', self)
                action_figure_thisDTV.triggered.connect(
                    partial(self.plotSelectedSignals, False))
                # Add to submenu
                subMenu_figure_new.addAction(action_figure_thisDTV)

            # --------------------------------------------------------------
            # Add menu item to plot selected signals to single
            # plot - All DTVs
            action_figure_allDTV = QAction(icon_allDTV, 'All IMAS Databases',self)
            if self.shareSameCoordinates(self.dataTreeView.selectedSignalsDict):
                action_figure_allDTV.triggered.connect(
                    partial(self.plotSelectedSignals, True))
                # Add to submenu
                subMenu_figure_new.addAction(action_figure_allDTV)

            for figureKey in self.imas_viz_api.GetFiguresKeys(
                    figureType=FigureTypes.FIGURETYPE):
                # Check for figures that share the same coordinates
                if not self.shareSameCoordinates(self.dataTreeView.selectedSignalsDict):
                    continue

                if not self.currentSelectionShareSameCoordinates(figureKey):
                    continue

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
            action_TPV_thisDTV = QAction(icon_thisDTV, 'This IMAS Database', self)
            action_TPV_thisDTV.triggered.connect(
                partial(self.onPlotToTablePlotView, all_DTV=False, configFile=None))
            # Add to submenu
            subMenu_TPV_new.addAction(action_TPV_thisDTV)

            # -----
            # Add menu item to plot selected signals to single
            # plot - All DTVs
            #icon_allDTV = GlobalIcons.getCustomQIcon(QApplication, 'allDTV')
            action_TPV_allDTV = QAction(icon_allDTV, 'All IMAS Databases', self)
            action_TPV_allDTV.triggered.connect(
                partial(self.onPlotToTablePlotView, all_DTV=True,
                        configFile=None))
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

    def menusShowHideAndDelete(self, numFig, numTPV, numSPV, menu):
        """Set two menus: first  for handling show/hide and second for deleting
        of existing figures, TablePlotViews and StackedPlotViews.
        """

        # Create and add empty menu to handle show/hide status of plot views and
        # figures
        menu_showHide = QMenu('Show/Hide', menu)
        menu_showHide.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'showHide'))

        menu_showHide.setDisabled(True)
        # Create and add empty menu to handle deletion of plot views and
        # figures
        menu_delete = QMenu('Delete', menu)
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

        menu.addMenu(menu_showHide)
        menu.addMenu(menu_delete)

    def updateNodeData(self):
        """ Update tree node/item data.
            TODO: use the global routine 'updateNodeData' defined in
                  QVizAbstractCommand instead.
        """
        self.nodeData = self.dataTreeView.selectedItem.getInfoDict()
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
        """Basic plotting of signal node plottable data command.
        """
        try:

            # Get next figure label (e.g. 'Figure:0')
            self.currentFigureKey = self.imas_viz_api.GetNextKeyForFigurePlots()
            label = None
            xlabel = None

            addTimeSlider = False

            # If signal node is a part of time_slice array of structures
            # (e.g. 'equilibrium.time_slice[0].profiles_1d.psi')
            if self.treeNode is not None and \
                self.treeNode.treeNodeExtraAttributes.time_dependent_aos():
                aos_vs_itime = self.treeNode.getDataPathVsTime(
                    self.treeNode.treeNodeExtraAttributes.parametrizedPath)
                #label = self.treeNode.getPath()
                xlabel = QVizGlobalOperations.replaceBrackets(
                    self.treeNode.evaluateCoordinate1At(
                        self.treeNode.infoDict['i']))
                addTimeSlider = True

            figureKey, plotWidget = self.getPlotWidget(figureKey=None, addTimeSlider=addTimeSlider)
            # Get the signal data for plot widget
            p = QVizPlotSignal(self.dataTreeView, self.nodeData, signal=None, label=label,xlabel=xlabel)
            # Plot signal data to plot widget
            p.execute(plotWidget, figureKey=figureKey)

        except ValueError as e:
            logging.error(str(e))

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
            logging.error(str(e))

    # @pyqtSlot(bool)
    def plotSelectedSignals(self, all_DTV=True):
        """Plot selected signals from current or all DTV instances.

        Arguments:
            all_DTV (bool) : Boolean operator specifying if current or all DTVs
                             should be considered.
        """
        # Get label for the next figure (e.c. if 'Figure 2' already exists,
        # value 'Figure 3' will be returned)
        try:
            figureKey = self.imas_viz_api.GetNextKeyForFigurePlots()
            # Plot the selected signals
            if all_DTV == False:
                QVizPlotSelectedSignals(self.dataTreeView, figureKey,
                                        all_DTV=False).execute()
            else:
                QVizPlotSelectedSignals(self.dataTreeView, figureKey,
                                        all_DTV=True).execute()
        except ValueError as e:
            logging.error(str(e))

    @pyqtSlot(bool)
    def onPlotToTablePlotView(self, all_DTV=False, configFile=None):
        """Plot selected nodes from single/all opened DTVs to MultiPlot
        TablePlotView.

        Arguments:
            all_DTV (bool) : Operator to read selected signals from the
                             current or all DTVs.
        """
        # Get next figure key/label
        try:
            figureKey = self.dataTreeView.imas_viz_api.getNextKeyForTablePlotView()
            # Note: figureKey that includes 'TablePlotView' is expected
            if not all_DTV:
                QVizMultiPlotWindow(dataTreeView=self.dataTreeView,
                                    figureKey=figureKey,
                                    update=0,
                                    configFile=configFile,
                                    all_DTV=False)
            else:
                QVizMultiPlotWindow(dataTreeView=self.dataTreeView,
                                    figureKey=figureKey,
                                    update=0,
                                    configFile=configFile,
                                    all_DTV=True)
        except ValueError as e:
            logging.error(str(e))

    @pyqtSlot(bool)
    def onPlotToStackedPlotView(self, all_DTV=False):
        """Plot selected nodes from single/all opened DTVs to MultiPlot
        StackedPlotView.

        Arguments:
            all_DTV (bool) : Operator to read selected signals from the
                             current or all DTVs.
        """
        try:
            # Get next figure key/label
            figureKey = self.dataTreeView.imas_viz_api.getNextKeyForStackedPlotView()
            # Note: figureKey that includes 'StackedPlotView' is expected
            if all_DTV != True:
                QVizMultiPlotWindow(dataTreeView=self.dataTreeView, figureKey=figureKey,
                                    update=0, all_DTV=False)
            else:
                QVizMultiPlotWindow(dataTreeView=self.dataTreeView, figureKey=figureKey,
                                    update=0, all_DTV=True)
        except ValueError as e:
            logging.error(str(e))

    @pyqtSlot(int)
    def addSignalPlotToFig(self, numFig):
        """Add signal plot to existing figure.

        Arguments:
            numFig (int) : Number identification of the existing figure.
        """
        try:

            label = None
            title = None
            if self.treeNode.is0DAndDynamic():
                # Get label and title (dummy = obsolete xlabel)
                label = self.dataTreeView.dataSource.getShortLabel() + ":" + self.treeNode.getPath()
                label, title = self.treeNode.correctLabelForTimeSlices(label, title)

            # Get figure key (e.g. 'Figure:0' string)
            figureKey = self.imas_viz_api. \
                GetFigureKey(str(numFig), figureType=FigureTypes.FIGURETYPE)
            # Get widget linked to this figure
            figureKey, plotWidget = self.getPlotWidget(figureKey)
            QVizPlotSignal(dataTreeView=self.dataTreeView,
                               label=label,
                               title=title,
                               nodeData=self.nodeData,
                               update=0).execute(plotWidget, figureKey=figureKey)
        except ValueError as e:
            logging.error(str(e))

    def getPlotWidget(self, figureKey, addTimeSlider=False, addCoordinateSlider=False):
        api = self.dataTreeView.imas_viz_api
        if figureKey in api.figureframes:
            plotWidget = api.figureframes[figureKey]
        else:
            figureKey = api.GetNextKeyForFigurePlots()
            plotWidget = QVizPlotWidget(size=(600, 550), title=figureKey,
                                        addTimeSlider=addTimeSlider,
                                        addCoordinateSlider=addCoordinateSlider,
                                        signalHandling=self)
            api.figureframes[figureKey] = plotWidget
        return figureKey, plotWidget

    @pyqtSlot(int)
    def addSelectedSignalsPlotToFig(self, numFig, all_DTV=False):
        """Add/Plot selected signals to existing figure.

        Arguments:
            numFig (int) : Number identification of the existing figure.
        """
        # Get figure key (e.g. 'Figure:0' string)
        try:
            figureKey = self.imas_viz_api. \
                GetFigureKey(str(numFig), figureType=FigureTypes.FIGURETYPE)

            QVizPlotSelectedSignals(self.dataTreeView, figureKey, update=0,
                                    all_DTV=all_DTV).execute()
        except ValueError as e:
            logging.error(str(e))


    def nodeDataShareSameCoordinatesAs(self, selectedNodeDataList, currentNodeData):
        """Check if data already in figure and next to be added signal plot
        share the same coordinates and other conditions for a meaningful plot.
        """
        s = currentNodeData
        if self.treeNode.is1DAndDynamic():
            for si in selectedNodeDataList:
                if s.get('coordinate1') != si.get('coordinate1'):
                    return False
                if s.get('units') != si.get('units'):
                    return False
        elif self.treeNode.is0DAndDynamic():
            for si in selectedNodeDataList:
                if s.get('units') != si.get('units'):
                    return False
        return True

    def figureDataToNodeDataList(self, figureDataList):
        figureNodeDataList = []
        for k in figureDataList:
            v = figureDataList[k]
            figureNodeDataList.append(v[1])  # v[0] = shot number, v[1] = node data
        return figureNodeDataList

    def nodeDataShareSameCoordinates(self, figureKey, currentNodeData):
        figureDataList = self.imas_viz_api.figToNodes[figureKey]
        figureNodeDataList = []
        for k in figureDataList:
            v = figureDataList[k]
            figureNodeDataList.append(v[1])  # v[0] = shot number, v[1] = node data
        return self.nodeDataShareSameCoordinatesAs(figureNodeDataList, currentNodeData)

    def currentSelectionShareSameCoordinates(self, figureKey):
        for k in self.dataTreeView.selectedSignalsDict:
            signal = self.dataTreeView.selectedSignalsDict[k]
            vizTreeNode = signal['QTreeWidgetItem']
            if not self.nodeDataShareSameCoordinates(figureKey, vizTreeNode.getNodeData()):  # s[1] refers to node data
                return False
        return True

    def shareSameCoordinates(self, signalsList):
        """Check if data already in figure and next to be added signal plot
        share the same coordinates.
        """
        selectedNodeDataList = []
        for k in signalsList:
            signal = signalsList[k]
            vizTreeNode = signal['QTreeWidgetItem']
            selectedNodeDataList.append(vizTreeNode.getNodeData())  # v[0] = shot number,
            # v[1] = node data

        return self.shareSameCoordinates2(selectedNodeDataList)

    def shareSameCoordinates2(self, selectedNodeDataList):
        """Check if data share the same coordinates.
        """
        for si in selectedNodeDataList:
            if not self.nodeDataShareSameCoordinatesAs(selectedNodeDataList, si):
                return False
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
            logging.error(str(e))

    def plotSignalVsTimeCommand(self):
        """Plotting of signal node, found within the 'time_slice[:]' array of
        structures in IDS. For certain physical quantities (e.g.
        equilibrium.time_slice[:].profiles_1d.phi) it plots how it changes
        through time.

        Example:
        (e=equilibrium)
        Index i -> x = array time values (e.time). n = len(e.time)
                   y = array of values ([e.time_slice[0].profiles_1d.phi[i],
                                         e.time_slice[1].profiles_1d.phi[i],
                                         ...
                                         e.time_slice[n].profiles_1d.phi[i])

        Note: The wxPython predecessor of this function is
        plotSelectedSignalVsTime.

        """
        # self.updateNodeData()
        # Get currently selected QVizTreeNode (QTreeWidgetItem)
        try:
            treeNode = self.dataTreeView.selectedItem
            # Get signal node index
            # index = 0
            index = treeNode.infoDict['i']
            dataAccess = QVizDataAccessFactory(self.dataTreeView.dataSource).create()
            signal = dataAccess.GetSignalVsTime(treeNode, index)
            # Get label and title (dummy = obsolete xlabel)
            label, title, dummy = \
                treeNode.coordinate1LabelAndTitleForTimeSlices(dtv=self.dataTreeView, node=treeNode, index=index)
            # TODO: fix routines for obtaining label
            #idsName = treeNode.getInfoDict()['IDSName']
            label = label.replace('time_slice(0)', 'time_slice(:)')
            label = label.replace('profiles_1d(0)','profiles_1d(:)')
            label = label + '[' + str(index) + ']'
            self.treeNode = treeNode
            self.timeSlider = False
            figureKey, plotWidget = self.getPlotWidget(figureKey=None, addCoordinateSlider=True)
            p = QVizPlotSignal(dataTreeView=self.dataTreeView,
                           nodeData=self.nodeData,
                           signal=signal,
                           title=title,
                           label=label,
                           xlabel="time[s]",
                           update=0)
            p.execute(plotWidget, figureKey=figureKey)
        except ValueError as e:
            logging.error(str(e))

    def plot0D_DataVsTimeCommand(self):

        """Plotting of 0D data nodes, found within timed AOS
        """

        # Get currently selected QVizTreeNode (QTreeWidgetItem)
        try:
            self.treeNode = self.dataTreeView.selectedItem
            dataAccess = QVizDataAccessFactory(self.dataTreeView.dataSource).create()
            signal = dataAccess.Get0DSignalVsTime(self.treeNode)
            # Get label and title (dummy = obsolete xlabel)
            label = self.dataTreeView.dataSource.getShortLabel() + ":" + self.treeNode.getPath()
            label, title = self.treeNode.correctLabelForTimeSlices(label, '')
            figureKey, plotWidget = self.getPlotWidget(figureKey=None) #None will force a new Figure
            p = QVizPlotSignal(dataTreeView=self.dataTreeView,
                           nodeData=self.nodeData,
                           signal=signal,
                           title=title,
                           label=label,
                           xlabel="time[s]",
                           update=0)
            p.execute(plotWidget, figureKey=figureKey)
        except ValueError as e:
            logging.error(str(e))

    def plotSelectedSignalVsTimeAtCoordinate1D(self, index, currentFigureKey, treeNode):
        """Overwrite/Update the existing plot (done with
        'plotSignalVsTimeCommand' routine and currently still shown in
        the plot window labeled as 'currentFigureKey') using the same
        physical quantity (found in sibling node of the same structure (AOS))
        but with different array positional index.

        Arguments:
            index             (int) : Array positional index.
            currentFigureKey  (str) : Label of the current/relevant figure
                                      window.
            treeNode (QVizTreeNode) : QTreeWidgetItem holding node data to
                                      replace the current plot in figure window.
        """
        try:
            dataAccess = QVizDataAccessFactory(self.dataTreeView.dataSource).create()
            signal = dataAccess.GetSignalVsTime(treeNode,index)

            # Get label, title and xlabel
            label, title, xlabel = treeNode.coordinate1LabelAndTitleForTimeSlices(
                dtv=self.dataTreeView, node=treeNode, index=index)
            # TODO: fix routines for obtaining label
            idsName = treeNode.getInfoDict()['IDSName']
            xlabel = xlabel.replace(idsName + 'time_slice(0)', idsName + 'time_slice(:)')
            label = label.replace(idsName + 'time_slice(0)', idsName + 'time_slice(:)')

            xlabel = xlabel.replace(idsName + 'profiles_1d(0)', idsName + 'profiles_1d(:)')
            label = label.replace(idsName + 'profiles_1d(0)', idsName + 'profiles_1d(:)')

            label = label + '[' + str(index) + ']'
            xlabel = xlabel + '[' + str(index) + ']'
            currentFigureKey, plotWidget = self.getPlotWidget(currentFigureKey, addCoordinateSlider=True)
            # Update/Overwrite plot
            QVizPlotSignal(dataTreeView=self.dataTreeView,
                           nodeData=treeNode.getInfoDict(),
                           signal=signal,
                           title=title,
                           label=label,
                           xlabel="time[s]",
                           update=1,
                           vizTreeNode=treeNode).execute(plotWidget, figureKey=currentFigureKey)
        except ValueError as e:
            logging.error(str(e))

    def plotSelectedSignalVsCoordAtTimeIndex(self, time_index, currentFigureKey,
                                             treeNode):
        """Overwrite/Update the existing plot (done with
        'plotSignalCommand' routine and currently still shown in
        the plot window labeled as 'currentFigureKey') but for different time
        slice. The node must be of the same structure (sibling to the node used
        for the previous plot and both are located within the 'time_slice[:]'
        structure').

        Arguments:
            time_index        (int) : Time slice index.
            currentFigureKey  (str) : Label of the current/relevant figure
                                      window.
            treeNode (QVizTreeNode) : QTreeWidgetItem holding node data to
                                      replace the current plot in figure window.
        """
        try:
            # self.updateNodeData()
            dataAccess = QVizDataAccessFactory(self.dataTreeView.dataSource).create()
            # Get signal node
            signal = dataAccess.GetSignalAt(treeNode, time_index)
            # Get label and xlabel (title in this form is not needed)
            label, title, xlabel = treeNode.coordinate1LabelAndTitleForTimeSlices(
                                dtv=self.dataTreeView, node=treeNode,
                                index=time_index)

            idsName = treeNode.getInfoDict()['IDSName']
            xlabel = xlabel.replace(idsName + '/time_slice(0)', idsName + '/time_slice(' + str(time_index) + ')')
            label = label.replace(idsName + '/time_slice(0)', idsName + '/time_slice(' + str(time_index) + ')')
            xlabel = xlabel.replace(idsName + '/profiles_1d(0)', idsName + '/profiles_1d(' + str(time_index) + ')')
            label = label.replace(idsName + '/profiles_1d(0)', idsName + '/profiles_1d(' + str(time_index) + ')')
            currentFigureKey, plotWidget = self.getPlotWidget(figureKey=currentFigureKey, addTimeSlider=True)
            # Update/Overwrite plot
            QVizPlotSignal(dataTreeView=self.dataTreeView,
                           nodeData=treeNode.getInfoDict(),
                           signal=signal,
                           label=label,
                           xlabel=xlabel,
                           update=1,
                           vizTreeNode=treeNode).execute(plotWidget, figureKey=currentFigureKey)
        except ValueError as e:
            logging.error(str(e))