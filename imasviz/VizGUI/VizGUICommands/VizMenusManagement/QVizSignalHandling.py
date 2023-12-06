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
# ****************************************************
#  TODO:
#
#    - Function definitions (from SignalHandling class)
#    def addSignalSelectionToTablePlotViewFrame
#    def showStackedPlotViewsManager
#    def # onClose
#
# ****************************************************
#     Copyright(c) 2016- L. Fleury, L. Xinyi, D. Penko
# ****************************************************

from functools import partial
import re, logging
from PySide6.QtCore import QObject, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QApplication, QStyle
from imasviz.VizUtils import GlobalIcons, QVizPreferences

from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizMultiPlotWindow import QVizMultiPlotWindow
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSelectedSignals import QVizPlotSelectedSignals
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal import QVizPlotSignal
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPreviewPlotSignal import QVizPreviewPlotSignal
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectOrUnselectSignal import QVizSelectOrUnselectSignal
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignalsGroup import QVizSelectSignalsGroup
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizUnselectAllSignals import QVizUnselectAllSignals
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizPluginsPopUpMenu import QVizPluginsPopUpMenu
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QViz2DArrayHandling import QViz2DArrayHandling
from imasviz.VizUtils import FigureTypes


class QVizSignalHandling(QObject):
    def __init__(self, dataTreeView, treeNode=None):
        """
        Arguments:
            dataTreeView (QTreeWidget) : DataTreeView object of the QTreeWidget.
        """
        super(QVizSignalHandling, self).__init__(parent=dataTreeView)
        self.dataTreeView = dataTreeView
        self.imas_viz_api = self.dataTreeView.imas_viz_api
        self.plotFrame = None
        self.currentFigureKey = None
        # Get signal node (tree item) data
        if self.dataTreeView.selectedItem is not None:
            self.nodeData = self.dataTreeView.selectedItem.getInfoDict()
        elif treeNode is not None:
            self.nodeData = treeNode.getInfoDict()
        if treeNode is not None:
           self.treeNode = treeNode
        else:
           self.treeNode = self.dataTreeView.selectedItem

    def buildContextMenu(self, signalNode):
        """Build context menu.
        """

        self.signalNodeName = signalNode.getDataName()

        # Get total count of figures, tablePlotViews, stackedPlotViews etc.
        numFig = self.imas_viz_api.GetFigurePlotsCount()
        numTPV = self.imas_viz_api.GetTablePlotViewsCount()
        numSPV = self.imas_viz_api.GetStackedPlotViewsCount()
        numImg = self.imas_viz_api.GetImagePlotsCount()
        numPro = self.imas_viz_api.GetProfilesPlotViewsCount()

        # Set new popup menu
        self.contextMenu = QMenu()

        if self.treeNode.is2D():
            array2DHandling = QViz2DArrayHandling(self.dataTreeView)
            self.contextMenu.addMenu(array2DHandling.menuPlotCurrentArrayNode(self))
        elif not self.treeNode.is2DOrLarger() and self.treeNode.getDataType() != 'STR_1D':

            # SET TOP ACTIONS
            # - Add action for setting signal node select/unselect status
            if self.treeNode.is0DAndDynamic() or self.treeNode.is1D():
                self.contextMenu.addAction(self.actionSelectOrUnselectSignalNode())

            # - Add action for selection of all signals from the same array of
            #   structures
            if self.treeNode.is1D():
                if self.nodeData.get('aos_parents_count') != '0':
                    self.contextMenu.addAction(self.actionSelectAllSignalNodesFromSameAOS())

            # SET TOP MENU ITEMS
            # - Add menu for handling plotting using the under-the-mouse selected
            #   signal node
            if self.treeNode.is1D():
                self.contextMenu.addMenu(self.menuPlotCurrentSignalNode())
            elif self.treeNode.is0DAndDynamic():
                self.contextMenu.addMenu(self.menuPlotCurrentSignal0DNode())

            # - Add menu for handling unselection of signal nodes
            if self.treeNode.is0DAndDynamic() or self.treeNode.is1D():
                self.contextMenu.addMenu(self.menuUnselectSignalNodes())

            # - Add menu for handling plotting a selection of signal nodes
            if self.treeNode.is0DAndDynamic() or self.treeNode.is1D():
                self.contextMenu.addMenu(
                    self.menuPlotSelectedSignalNodes(parentMenu=self.contextMenu))

        # - Add menu for handling show/hide if figures, TablePlotViews and
        #   StackedPlotViews.
        self.menusShowHideAndDelete(numFig, numTPV, numSPV, numImg, numPro, self.contextMenu)
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
        self.pluginsPopUpMenu.upateMenu(self.treeNode, self.dataTreeView,
                                        sub_menu)

    def actionPlotAsFunctionOfTime(self):
        # Add action to plot the signal data as a function of time
        # TODO: icon
        action_plotAsFunctionOfTime = None
        if self.treeNode.is1DAndDynamic() and self.treeNode.time_dependent(
                        self.treeNode.parametrizedPath):
            icon = GlobalIcons.getCustomQIcon(QApplication, 'plotSingle')
            action_plotAsFunctionOfTime = QAction(icon,
                                                  'Plot as function of time',
                                                  self)
            api = self.dataTreeView.imas_viz_api
            action_plotAsFunctionOfTime.triggered.connect(
                partial(api.plotSignalVsTimeCommand, self.dataTreeView))
            action_plotAsFunctionOfTime.setDisabled(False)

        return action_plotAsFunctionOfTime

    def actionPlot2DArray(self):
        # Add action to plot 2D array data
        # TODO: icon
        action_plot2DArray = None
        if self.treeNode.is2D():
            icon = GlobalIcons.getCustomQIcon(QApplication, 'plotSingle')
            action_plot2DArray = QAction(icon, 'Plot 2D image', self)
            api = self.dataTreeView.imas_viz_api
            action_plot2DArray.triggered.connect(
                partial(api.Plot2DArray, self.dataTreeView, self.treeNode))
            action_plot2DArray.setDisabled(False)
        return action_plot2DArray

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
            id_Fig = self.imas_viz_api.getFigureKeyNum(figureKey,
                                                       FigureTypes.FIGURETYPE)

            # Add menu item to add plot to specific existing figure
            # Check for figures that share the same coordinates
            if self.nodeDataShareSameCoordinates(figureKey, self.treeNode):
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
        api = self.dataTreeView.imas_viz_api
        action_plotNewFigure.triggered.connect(
            partial(api.plot0D_DataVsTimeCommand, self.dataTreeView, None))

        menu_figure = menu.addMenu('Figure')
        menu_figure.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'Figure'))
        menu_figure.addAction(action_plotNewFigure)

        for figureKey in self.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.FIGURETYPE):

            # Get figure number out from the figureKey string
            # (e.g. 'Figure:0' -> 0)
            # id_Fig = int(figureKey.split(':')[1])
            id_Fig = self.imas_viz_api.getFigureKeyNum(figureKey,
                                                       FigureTypes.FIGURETYPE)

            # Add menu item to add plot to specific existing figure
            # Check for figures that share the same coordinates
            if self.nodeDataShareSameCoordinates(figureKey, self.treeNode):
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
        menu.setIcon(GlobalIcons.getCustomQIcon(QApplication,
                                                'unselectMultiple'))
        # Set disables as default
        menu.setDisabled(True)

        # If selected signals list exists, set actions for unselection of all
        # selected signals and enable the menu item
        if len(self.dataTreeView.selectedSignalsDict) > 0:
            menu.setDisabled(False)

            # Add menu item to unselect all signals - This/Current DTV
            icon_thisDTV = GlobalIcons.getCustomQIcon(QApplication, 'thisDTV')
            action_onUnselectSignals = QAction(icon_thisDTV,
                                               'This IMAS Database',
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
            subMenu_figure.setIcon(GlobalIcons.getCustomQIcon(QApplication,
                                                              'Figure'))

            subMenu_figure_new = subMenu_figure.addMenu('New')
            subMenu_figure_new.setIcon(GlobalIcons.getCustomQIcon(QApplication,
                                                                  'new'))

            plotAxis = self.treeNode.getPlotAxisForDefaultPlotting()

            # --------------------------------------------------------------
            # Add menu item to plot selected signals to single
            # plot - This DTV
            icon_thisDTV = GlobalIcons.getCustomQIcon(QApplication, 'thisDTV')
            icon_allDTV = GlobalIcons.getCustomQIcon(QApplication, 'allDTV')
            if self.shareSameCoordinates(self.dataTreeView.selectedSignalsDict):
                action_figure_thisDTV = QAction(icon_thisDTV,
                                                'This IMAS Database',
                                                self)
                action_figure_thisDTV.triggered.connect(
                    partial(self.plotSelectedSignals, False, plotAxis=plotAxis))
                # Add to submenu
                subMenu_figure_new.addAction(action_figure_thisDTV)

            # --------------------------------------------------------------
            # Add menu item to plot selected signals to single
            # plot - All DTVs
            action_figure_allDTV = QAction(icon_allDTV,
                                           'All IMAS Databases',
                                           self)
            if self.shareSameCoordinates(self.dataTreeView.selectedSignalsDict):
                action_figure_allDTV.triggered.connect(
                    partial(self.plotSelectedSignals, True, plotAxis=plotAxis))
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
                id_Fig = self.imas_viz_api.getFigureKeyNum(figureKey,
                                                           FigureTypes.FIGURETYPE)
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

            subMenu_TPV_new = subMenu_TPV.addMenu('New (default axis)')
            subMenu_TPV_new.setIcon(GlobalIcons.getCustomQIcon(QApplication,
                                                               'new'))

            subMenu_TPV_new2 = subMenu_TPV.addMenu("New ('TIME' axis)")
            subMenu_TPV_new2.setIcon(GlobalIcons.getCustomQIcon(QApplication,
                                                                'new'))

            # -----
            # Add menu item to plot selected signals to single
            # plot - This DTV
            action_TPV_thisDTV = QAction(icon_thisDTV, 'This IMAS Database',
                                         self)
            commonPlotAxis = 'TIME'
            if self.shareSameCoordinates(self.dataTreeView.selectedSignalsDict):
                commonPlotAxis = plotAxis

            action_TPV_thisDTV.triggered.connect(
                partial(self.onPlotToTablePlotView, all_DTV=False,
                        configFile=None, plotAxis=commonPlotAxis))
            # Add to submenu
            subMenu_TPV_new.addAction(action_TPV_thisDTV)

            # -----
            # Add menu item to plot selected signals to single
            # plot - All DTVs
            # icon_allDTV = GlobalIcons.getCustomQIcon(QApplication, 'allDTV')
            action_TPV_allDTV = QAction(icon_allDTV, 'All IMAS Databases',
                                        self)
            action_TPV_allDTV.triggered.connect(
                partial(self.onPlotToTablePlotView, all_DTV=True,
                        configFile=None, plotAxis='TIME'))
            # Add to submenu
            subMenu_TPV_new.addAction(action_TPV_allDTV)

            # Add menu item to plot selected signals to single
            # plot - This DTV
            action_TPV_thisDTV2 = QAction(icon_thisDTV, 'This IMAS Database',
                                          self)
            action_TPV_thisDTV2.triggered.connect(
                partial(self.onPlotToTablePlotView, all_DTV=False,
                        configFile=None, plotAxis='TIME'))
            # Add to submenu
            subMenu_TPV_new2.addAction(action_TPV_thisDTV2)

            # -----
            # Add menu item to plot selected signals to single
            # plot - All DTVs
            # icon_allDTV = GlobalIcons.getCustomQIcon(QApplication, 'allDTV')
            action_TPV_allDTV2 = QAction(icon_allDTV, 'All IMAS Databases',
                                         self)
            action_TPV_allDTV2.triggered.connect(
                partial(self.onPlotToTablePlotView, all_DTV=True,
                        configFile=None, plotAxis='TIME'))
            # Add to submenu
            subMenu_TPV_new2.addAction(action_TPV_allDTV2)

            # ------------------------------------------------------------------
            # StackedPlotView
            subMenu_SPV = menu.addMenu('StackedPlotView')
            subMenu_SPV.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'SPV'))

            subMenu_SPV_new = subMenu_SPV.addMenu('New (default axis)')
            subMenu_SPV_new.setIcon(GlobalIcons.getCustomQIcon(QApplication,
                                                               'new'))
                                                               
            subMenu_SPV_new2 = subMenu_SPV.addMenu("New ('TIME' axis)")
            subMenu_SPV_new2.setIcon(GlobalIcons.getCustomQIcon(QApplication,
                                                               'new'))

            # -----
            # Add menu item to plot selected signals to single
            # plot - This DTV
            action_SPV_thisDTV = QAction(icon_thisDTV, 'This IMAS Database',
                                         self)

            commonPlotAxis = 'TIME'
            if self.shareSameCoordinates(self.dataTreeView.selectedSignalsDict):
                commonPlotAxis = plotAxis

            action_SPV_thisDTV.triggered.connect(
                partial(self.onPlotToStackedPlotView, False, commonPlotAxis))
            # Add to submenu
            subMenu_SPV_new.addAction(action_SPV_thisDTV)

            # -----
            # Add menu item to plot selected signals to single
            # plot - All DTVs
            action_SPV_allDTV = QAction(icon_allDTV, 'All IMAS Databases',
                                        self)
            action_SPV_allDTV.triggered.connect(
                partial(self.onPlotToStackedPlotView, True, 'TIME'))
            # Add to submenu
            subMenu_SPV_new.addAction(action_SPV_allDTV)
            
            
            
            action_SPV_thisDTV2 = QAction(icon_thisDTV, 'This IMAS Database',
                                         self)
            action_SPV_thisDTV2.triggered.connect(
                partial(self.onPlotToStackedPlotView, False, 'TIME'))
            # Add to submenu
            subMenu_SPV_new2.addAction(action_SPV_thisDTV2)

            # -----
            # Add menu item to plot selected signals to single
            # plot - All DTVs
            action_SPV_allDTV2 = QAction(icon_allDTV, 'All IMAS Databases',
                                        self)
            action_SPV_allDTV2.triggered.connect(
                partial(self.onPlotToStackedPlotView, True, 'TIME'))
            # Add to submenu
            subMenu_SPV_new2.addAction(action_SPV_allDTV2)
            

        return menu

    def menusShowHideAndDelete(self, numFig, numTPV, numSPV, numImg, numPro, menu):
        """Set two menus: first  for handling show/hide and second for deleting
        of existing figures, TablePlotViews and StackedPlotViews.
        """

        # Create and add empty menu to handle show/hide status of plot views and
        # figures
        menu_showHide = QMenu('Show/Hide', menu)
        menu_showHide.setIcon(GlobalIcons.getCustomQIcon(QApplication,
                                                         'showHide'))

        menu_showHide.setDisabled(True)
        # Create and add empty menu to handle deletion of plot views and
        # figures
        menu_delete = QMenu('Delete', menu)
        menu_delete.setIcon(GlobalIcons.getStandardQIcon(QApplication,
                                                         QStyle.SP_DialogDiscardButton))
        menu_delete.setDisabled(True)

        if numFig > 0 or numTPV > 0 or numSPV > 0 or numImg > 0 or numPro >0:
            menu_showHide.setDisabled(False)
            menu_delete.setDisabled(False)

        # Set handling existing figures
        if numFig > 0:

            # Create and add empty submenu to handle figures show/hide
            submenu_showHideFigure = menu_showHide.addMenu('Figure')
            submenu_showHideFigure.setIcon(
                GlobalIcons.getCustomQIcon(QApplication,
                                           'Figure'))
            # Create and add empty submenu to handle figures deletion
            subMenu_deleteFigure = menu_delete.addMenu('Figure')
            subMenu_deleteFigure.setIcon(
                GlobalIcons.getCustomQIcon(QApplication,
                                           'Figure'))

            for figureKey in self.imas_viz_api.GetFiguresKeys(
                    figureType=FigureTypes.FIGURETYPE):
                # Get figure number out from the figureKey string
                # (e.g. 'Figure:0' -> 0)
                # id_Fig = int(figureKey.split(':')[1])
                id_Fig = self.imas_viz_api.getFigureKeyNum(figureKey,
                                                           FigureTypes.FIGURETYPE)

                # --------------------------------------------------------------
                # Add menu item to show/hide existing figure
                # Set action
                action_showHide_figure = QAction(figureKey, self)
                action_showHide_figure.triggered.connect(
                    partial(self.showHideFigure, id_Fig,
                            FigureTypes.FIGURETYPE))
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
            subMenu_showHideTPV.setIcon(GlobalIcons.getCustomQIcon(QApplication,
                                                                   'TPV'))
            # Create and add empty submenu to handle tablePlotViews deletion
            subMenu_deleteTPV = menu_delete.addMenu('TablePlotView')
            subMenu_deleteTPV.setIcon(GlobalIcons.getCustomQIcon(QApplication,
                                                                 'TPV'))

            for figureKey in self.imas_viz_api.GetFiguresKeys(
                    figureType=FigureTypes.TABLEPLOTTYPE):
                # Get figure id number out from the figureKey string
                # (e.g. 'Figure:0' -> 0)
                id_TPV = self.imas_viz_api.getFigureKeyNum(figureKey,
                                                           FigureTypes.TABLEPLOTTYPE)

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
            subMenu_showHideSPV.setIcon(GlobalIcons.getCustomQIcon(QApplication,
                                                                   'SPV'))
            # Create and add empty submenu to handle deletion
            subMenu_deleteSPV = menu_delete.addMenu('StackedPlotView')
            subMenu_deleteSPV.setIcon(GlobalIcons.getCustomQIcon(QApplication,
                                                                 'SPV'))

            for figureKey in self.imas_viz_api.GetFiguresKeys(
                    figureType=FigureTypes.STACKEDPLOTTYPE):
                # Get figure id number out from the figureKey string
                # (e.g. 'Figure:0' -> 0)
                id_SPV = self.imas_viz_api.getFigureKeyNum(figureKey,
                                                           FigureTypes.STACKEDPLOTTYPE)

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

        # Set handling existing figures
        if numImg > 0:

            # Create and add empty submenu to handle figures show/hide
            submenu_showHideFigure = menu_showHide.addMenu('Image')
            submenu_showHideFigure.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'Image'))
            # Create and add empty submenu to handle figures deletion
            subMenu_deleteFigure = menu_delete.addMenu('Image')
            subMenu_deleteFigure.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'Image'))

            for imageKey in self.imas_viz_api.GetFiguresKeys(
                    figureType=FigureTypes.IMAGETYPE):
                # Get image number out from the figureKey string
                # (e.g. 'Image:0' -> 0)
                # id_Fig = int(figureKey.split(':')[1])
                id_Fig = self.imas_viz_api.getFigureKeyNum(imageKey, FigureTypes.IMAGETYPE)

                # --------------------------------------------------------------
                # Add menu item to show/hide existing figure
                # Set action
                action_showHide_figure = QAction(imageKey, self)
                action_showHide_figure.triggered.connect(
                    partial(self.showHideFigure, id_Fig, FigureTypes.IMAGETYPE))
                # Add to submenu
                submenu_showHideFigure.addAction(action_showHide_figure)

                # --------------------------------------------------------------
                # Add menu item to delete existing figure
                # Set action
                action_delete_figure = QAction(imageKey, self)
                action_delete_figure.triggered.connect(
                    partial(self.deleteFigure, id_Fig, FigureTypes.IMAGETYPE))
                # Add to submenu
                subMenu_deleteFigure.addAction(action_delete_figure)

            # ------------------------------------------------------------------
            # Add menu item to delete all existing figures
            # Set action
            action_deleteAll_figure = QAction('All', self)
            action_deleteAll_figure.triggered.connect(partial(
                self.deleteAllFigures, figureType=FigureTypes.IMAGETYPE))
            # Add to submenu
            subMenu_deleteFigure.addAction(action_deleteAll_figure)
            # Bitmap icon
            # TODO
            
        if numPro > 0:
            self.update_menus(menu_showHide, menu_delete, 'Profiles', figureType=FigureTypes.PROFILESPLOTTYPE)

        menu.addMenu(menu_showHide)
        menu.addMenu(menu_delete)

    def update_menus(self, menu_showHide, menu_delete, name, figureType):
        # Create and add empty submenu to handle figures show/hide
            submenu_showHideFigure = menu_showHide.addMenu(name)
            if GlobalIcons.getCustomQIcon(QApplication, name) is not None:
               submenu_showHideFigure.setIcon(GlobalIcons.getCustomQIcon(QApplication, name))
            # Create and add empty submenu to handle figures deletion
            subMenu_deleteFigure = menu_delete.addMenu(name)
            if GlobalIcons.getCustomQIcon(QApplication, name) is not None:
               subMenu_deleteFigure.setIcon(GlobalIcons.getCustomQIcon(QApplication, name))

            for key in self.imas_viz_api.GetFiguresKeys(
                    figureType=figureType):
                # Get image number out from the figureKey string
                # (e.g. 'Image:0' -> 0)
                # id_Fig = int(figureKey.split(':')[1])
                id_Fig = self.imas_viz_api.getFigureKeyNum(key, figureType)

                # --------------------------------------------------------------
                # Add menu item to show/hide existing figure
                # Set action
                action_showHide_figure = QAction(key, self)
                action_showHide_figure.triggered.connect(
                    partial(self.showHideFigure, id_Fig, figureType))
                # Add to submenu
                submenu_showHideFigure.addAction(action_showHide_figure)

                # --------------------------------------------------------------
                # Add menu item to delete existing figure
                # Set action
                action_delete_figure = QAction(key, self)
                action_delete_figure.triggered.connect(
                    partial(self.deleteFigure, id_Fig, figureType))
                # Add to submenu
                subMenu_deleteFigure.addAction(action_delete_figure)

            # ------------------------------------------------------------------
            # Add menu item to delete all existing figures
            # Set action
            action_deleteAll_figure = QAction('All', self)
            action_deleteAll_figure.triggered.connect(partial(
                self.deleteAllFigures, figureType=figureType))
            # Add to submenu
            subMenu_deleteFigure.addAction(action_deleteAll_figure)
            # Bitmap icon
            # TODO
        
    def selectSignal(self):
        QVizSelectOrUnselectSignal(self.dataTreeView, self.treeNode).execute()

    @Slot()
    def selectOrUnselectSignal(self):
        QVizSelectOrUnselectSignal(self.dataTreeView, self.treeNode).execute()

    @Slot(bool)
    def onUnselectSignals(self, all_DTV=False):
        """Unselect all signals (single or all DTVs)."""
        QVizUnselectAllSignals(self.dataTreeView, all_DTV).execute()

    @Slot()
    def selectAllSignalsFromSameAOS(self):
        QVizSelectSignalsGroup(self.dataTreeView, self.treeNode).execute()

    @Slot()
    def plotSignalCommand(self):
        """Basic plotting of signal node plottable data command.
        """
        try:

            # Get next figure label (e.g. 'Figure:0')
            self.currentFigureKey = self.imas_viz_api.GetNextKeyForFigurePlots()
            label = None
            xlabel = None

            plotAxis = self.treeNode.getPlotAxisForDefaultPlotting()

            api = self.dataTreeView.imas_viz_api
            figureKey, plotWidget = api.GetPlotWidget(dataTreeView=self.dataTreeView,
                                                      figureKey=None,  # passing figureKey=None means we want
                                                      # a new plotWidget
                                                      plotAxis=plotAxis,
                                                      treeNode=self.treeNode)
            self.addPlotWidgetToMDI(plotWidget)
            # Get the signal data for plot widget
            p = QVizPlotSignal(plotWidget=plotWidget,
                               dataTreeView=self.dataTreeView,
                               label=label,
                               xlabel=xlabel,
                               vizTreeNode=self.treeNode)
            # Plot signal data to plot widget
            p.execute(figureKey=figureKey, update=0)

        except ValueError as e:
            logging.getLogger(self.dataTreeView.uri).error(str(e))

    def plotPreviewSignalCommand(self):
        """Show preview plot.
        """
        try:
            # Get the signal data for preview plot update
            p = QVizPreviewPlotSignal(dataTreeView=self.dataTreeView,
                                      treeNode=self.treeNode,
                                      signalHandling=self)
            # Plot signal data to preview plot widget
            p.execute()

        except ValueError as e:
            logging.getLogger(self.dataTreeView.uri).error(str(e))

    # @Slot(bool)
    def plotSelectedSignals(self, all_DTV=True, plotAxis='TIME'):
        """Plot selected signals from current or all DTV instances.

        Arguments:
            all_DTV (bool) : Boolean operator specifying if current or all DTVs
                             should be considered.
                             :param all_DTV:
                             :param plotAxis:
        """
        # Get label for the next figure (e.c. if 'Figure 2' already exists,
        # value 'Figure 3' will be returned)
        try:
            # figureKey = self.imas_viz_api.GetNextKeyForFigurePlots()
            if len(self.dataTreeView.selectedSignalsDict) == 0:
                logging.getLogger(self.dataTreeView.uri).error(str(e)).error("No selection found.")
                return
            first_key = list(self.dataTreeView.selectedSignalsDict.keys())[0]
            v = self.dataTreeView.selectedSignalsDict[first_key]

            api = self.dataTreeView.imas_viz_api
            # passing figureKey=None means we want a new plotWidget
            figureKey, plotWidget = api.GetPlotWidget(dataTreeView=self.dataTreeView,
                                                      figureKey=None,
                                                      plotAxis=plotAxis)
            self.addPlotWidgetToMDI(plotWidget)
            # Plot the selected signals
            QVizPlotSelectedSignals(dataTreeView=self.dataTreeView,
                                    figureKey=figureKey,
                                    all_DTV=all_DTV,
                                    plotAxis=plotAxis).execute()

        except ValueError as e:
            logging.getLogger(self.dataTreeView.uri).error(str(e))

    @Slot(bool)
    def onPlotToTablePlotView(self, all_DTV=False, configFile=None,
                              plotAxis=None):
        """Plot selected nodes from single/all opened DTVs to MultiPlot
        TablePlotView.

        Arguments:
            all_DTV (bool) : Operator to read selected signals from the
                             current or all DTVs.
                             :param all_DTV:
                             :param configFile:
                             :param plotAxis:
        """
        # Get next figure key/label
        try:
            figureKey = self.dataTreeView.imas_viz_api.GetNextKeyForTablePlotView()
            # Note: figureKey that includes 'TablePlotView' is expected
            if not all_DTV:
                QVizMultiPlotWindow(dataTreeView=self.dataTreeView,
                                    figureKey=figureKey,
                                    update=0,
                                    configFile=configFile,
                                    all_DTV=False,
                                    plotAxis=plotAxis)
            else:
                QVizMultiPlotWindow(dataTreeView=self.dataTreeView,
                                    figureKey=figureKey,
                                    update=0,
                                    configFile=configFile,
                                    all_DTV=True,
                                    plotAxis=plotAxis)
        except ValueError as e:
            logging.getLogger(self.dataTreeView.uri).error(str(e))

    @Slot(bool)
    def onPlotToStackedPlotView(self, all_DTV=False, plotAxis="TIME"):
        """Plot selected nodes from single/all opened DTVs to MultiPlot
        StackedPlotView.

        Arguments:
            all_DTV (bool) : Operator to read selected signals from the
                             current or all DTVs.
                             :param all_DTV:
                             :param plotAxis:
        """
        try:
            # Get next figure key/label
            figureKey = self.dataTreeView.imas_viz_api.GetNextKeyForStackedPlotView()
            # Note: figureKey that includes 'StackedPlotView' is expected
            if all_DTV is not True:
                QVizMultiPlotWindow(dataTreeView=self.dataTreeView,
                                    figureKey=figureKey,
                                    update=0,
                                    all_DTV=False,
                                    plotAxis=plotAxis)
            else:
                QVizMultiPlotWindow(dataTreeView=self.dataTreeView,
                                    figureKey=figureKey,
                                    update=0,
                                    all_DTV=True,
                                    plotAxis=plotAxis)
        except ValueError as e:
            logging.getLogger(self.dataTreeView.uri).error(str(e))

    @Slot(int)
    def addSignalPlotToFig(self, numFig):
        """Add signal plot to existing figure.

        Arguments:
            numFig (int) : Number identification of the existing figure.
        """
        api = self.dataTreeView.imas_viz_api
        logging.debug("QVizSignalHandling::addSignalPlotToFig:treeNode=" + self.treeNode.getName())
        print(id(self.treeNode))
        api.AddPlot1DToFig(numFig, self.treeNode)

    def addPlotWidgetToMDI(self, plotWidget):
        """Embeds the plotWidget inside MDI subwindow.
        """
        from PySide6.QtWidgets import QMdiSubWindow

        subWindow = QMdiSubWindow()
        subWindow.setWidget(plotWidget)
        subWindow.resize(plotWidget.width(), plotWidget.height())
        if self.getMDI() is not None:
           self.getMDI().addSubWindow(subWindow)
        else:
            self.subWindow = subWindow

    @Slot(int)
    def addSelectedSignalsPlotToFig(self, numFig, all_DTV=False):
        """Add/Plot selected signals to existing figure.

        Arguments:
            numFig (int) : Number identification of the existing figure.
        """
        # Get figure key (e.g. 'Figure:0' string)
        try:
            figureKey = self.imas_viz_api. \
                GetFigureKey(str(numFig), figureType=FigureTypes.FIGURETYPE)

            QVizPlotSelectedSignals(dataTreeView=self.dataTreeView,
                                    figureKey=figureKey,
                                    update=0,
                                    all_DTV=all_DTV).execute()
        except ValueError as e:
            logging.getLogger(self.dataTreeView.uri).error(str(e))

    def nodeDataShareSameCoordinatesAs(self, selectedNodeList, vizTreeNode,
                                       figureKey=None):
        """Check if data already in figure and next to be added signal plot
        share the same coordinates and other conditions for a meaningful plot.
        """
        if vizTreeNode.is1DAndDynamic():
            api = self.dataTreeView.imas_viz_api
            for si in selectedNodeList:
                if figureKey is not None:
                    figureKey, plotWidget = api.GetPlotWidget(dataTreeView=self.dataTreeView,
                                                              figureKey=figureKey, treeNode=vizTreeNode)
                    # Following check on coordinates is performed only if the current plot axis is not the time axis
                    if plotWidget.getPlotAxis() != 'TIME':
                        if vizTreeNode.getCoordinate(coordinateNumber=1) != si.getCoordinate(coordinateNumber=1):
                            return False
                if QVizPreferences.Allow_data_to_be_plotted_with_different_units == 0 and vizTreeNode.getUnits() != si.getUnits():
                    return False
        elif vizTreeNode.is0DAndDynamic():
            for si in selectedNodeList:
                if QVizPreferences.Allow_data_to_be_plotted_with_different_units == 0 and vizTreeNode.getUnits() != si.getUnits():
                    return False
        return True

    def nodeDataShareSameCoordinates(self, figureKey, vizTreeNode):
        figureDataList = self.imas_viz_api.figToNodes.get(figureKey)
        if figureDataList is None:
            return False
        figureNodesList = []
        for k in figureDataList:
            v = figureDataList[k]
            figureNodesList.append(v[1])  # v[0] = uri, v[1] = vizNode
        return self.nodeDataShareSameCoordinatesAs(figureNodesList, vizTreeNode,
                                                   figureKey)

    def currentSelectionShareSameCoordinates(self, figureKey):
        for k in self.dataTreeView.selectedSignalsDict:
            signal = self.dataTreeView.selectedSignalsDict[k]
            vizTreeNode = signal['QTreeWidgetItem']
            if not self.nodeDataShareSameCoordinates(figureKey, vizTreeNode):  # s[1] refers to node data
                return False
        return True

    def shareSameCoordinates(self, signalsList):
        """Check if data already in figure and next to be added signal plot
        share the same coordinates.
        """
        selectedNodesList = []
        for k in signalsList:
            signal = signalsList[k]
            vizTreeNode = signal['QTreeWidgetItem']
            selectedNodesList.append(vizTreeNode)
        return self.shareSameCoordinates2(selectedNodesList)


    def shareSameCoordinates2(self, selectedNodesList):
        """Check if data share the same coordinates.
        """
        for node in selectedNodesList:
            if not self.nodeDataShareSameCoordinatesAs(selectedNodesList, node):
                return False
        return True

    @Slot(int, str)
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

    @Slot(str)
    def deleteAllFigures(self, figureType=FigureTypes.FIGURETYPE):
        figureKeys = self.imas_viz_api.GetFiguresKeys(figureType)
        for figureKey in figureKeys:
            self.imas_viz_api.DeleteFigure(figureKey)

    @Slot(int, str)
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
            logging.getLogger(self.dataTreeView.uri).error(str(e))

    def getMDI(self):
        if self.parent().getMDI() is not None:
            return self.parent().getMDI()
        else:
            return None
