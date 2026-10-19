# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

from functools import partial
import re, logging
from PySide6.QtCore import QObject, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QApplication, QStyle
from imasviz.VizUtils import GlobalIcons, QVizPreferences

from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizMultiPlotWindow import QVizMultiPlotWindow
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSelectedSignals import QVizPlotSelectedSignals
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsSlices import QVizPlotAsSlices
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode import QVizPlotOneNode
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPreviewPlot import QVizPreviewPlot
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectOrUnselectSignal import QVizSelectOrUnselectSignal
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignalsGroup import QVizSelectSignalsGroup
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizUnselectAllSignals import QVizUnselectAllSignals
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizPluginsPopUpMenu import QVizPluginsPopUpMenu
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QViz2DArrayHandling import QViz2DArrayHandling
from imasviz.VizDataAccess.QVizNodePlotting import QVizNodePlotting
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
        # Get signal node (tree item) data
        if self.dataTreeView.selectedItem is not None:
            self.nodeData = self.dataTreeView.selectedItem.getInfoDict()
        elif treeNode is not None:
            self.nodeData = treeNode.getInfoDict()
        if treeNode is not None:
           self.treeNode = treeNode
        else:
           self.treeNode = self.dataTreeView.selectedItem
        # The menus name the node they act on, so the title belongs to the node,
        # not to whoever happened to build the context menu: an entry triggered
        # on its own (the preview panel, a plugin) used to die on an attribute
        # only buildContextMenu sets.
        if self.treeNode is not None:
            self.signalNodeName = self.treeNode.getDataName()

    def buildContextMenu(self, signalNode):
        """Build context menu.

        What the menu offers is decided by the axes the read would walk along the
        quantity (QVizNodePlotting), not by the dimension the data dictionary
        spells on the leaf. The two differ whenever arrays of structures hold the
        leaf: a three-axes quantity used to answer "nothing to do here" and came
        out with no entry to select it and no entry to draw it.

        :param signalNode: the node under the mouse
        """

        self.signalNodeName = signalNode.getDataName()

        # Set new popup menu
        self.contextMenu = QMenu()

        plotting = QVizNodePlotting(self.treeNode)
        signal = plotting.isPlottable()

        # SET TOP ACTIONS
        # - Add action for setting signal node select/unselect status
        if signal:
            self.contextMenu.addAction(self.actionSelectOrUnselectSignalNode())

        # - Add action for selection of all signals from the same array of
        #   structures
        if signal and plotting.inArrayOfStructures():
            self.contextMenu.addAction(self.actionSelectAllSignalNodesFromSameAOS())

        # SET TOP MENU ITEMS
        # - Add menu for handling plotting using the under-the-mouse selected
        #   signal node. The entry is offered whenever the read has an axis to
        #   draw along, and the command it triggers picks the frame from the same
        #   answer: which frame a quantity needs is not something the menu has to
        #   know, and the legacy curve figure (one slider group for everything
        #   but its curve, so one-dimension leaves only) and the legacy image
        #   frame (two of its own) are why there used to be one menu per leaf
        #   shape. What the read leaves out gets a control of its own -- see
        #   "Curves and images with slice controls" under the selection menu.
        if plotting.isPlottable():
            self.contextMenu.addMenu(
                self.menuPlotCurrentSignalNode(parentMenu=self.contextMenu))
            if plotting.legacyCanDrawAsCurve() and plotting.hasOwnCoordinate():
                self.contextMenu.addMenu(self.menuSetCoordinate1DNode())
        if plotting.legacyCanDrawAsImage():
            array2DHandling = QViz2DArrayHandling(self.dataTreeView)
            self.contextMenu.addMenu(array2DHandling.menuPlotCurrentArrayNode(self))

        if signal:
            # - Add menu for handling unselection of signal nodes
            self.contextMenu.addMenu(self.menuUnselectSignalNodes())

            # - Add menu for handling plotting a selection of signal nodes
            self.contextMenu.addMenu(
                self.menuPlotSelectedSignalNodes(parentMenu=self.contextMenu))

        # - Add menu for handling show/hide and deletion of the open figures
        self.menusShowHideAndDelete(self.contextMenu)
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
        """The entry for a quantity with a time base to read along.

        Asked of the axes, not of the leaf spelling: the gate used to be
        is1DAndDynamic() and a string test on the path, which together offered
        nothing for a number held by the dynamic array -- plainly a history --
        and offered the entry for shapes whose history was then refused by the
        command behind it.
        """
        plotting = QVizNodePlotting(self.treeNode)
        if not (plotting.isPlottable() and plotting.hasTimeAxis()):
            return None
        icon = GlobalIcons.getCustomQIcon(QApplication, 'plotSingle')
        action_plotAsFunctionOfTime = QAction(icon,
                                              'Plot as function of time',
                                              self)
        action_plotAsFunctionOfTime.triggered.connect(self.plotAlongTimeCommand)
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

    def menuSetCoordinate1DNode(self):
        """Set menu for setting the coordinate1 (under the mouse selected) 1D node.
        """
        # - Add action for setting new coordinate1
        menu = QMenu('Set coordinate1 of ' + self.signalNodeName + ' to ', self.contextMenu)
        #menu.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'plotSingle'))
        coordinateNumber = 1
        default_coordinate = self.treeNode.default_coordinates.get(coordinateNumber - 1)

        if default_coordinate is not None:
            action_setDefaultCoordinate = QAction(default_coordinate, self)
            action_setDefaultCoordinate.triggered.connect(self.default_setCoordinate1)
            menu.addAction(action_setDefaultCoordinate)

        alternative_coordinate = '1..N'
        action_setCoordinate = QAction(alternative_coordinate, self)
        action_setCoordinate.triggered.connect(partial(self.setCoordinate1, alternative_coordinate))

        menu.addAction(action_setCoordinate)
        return menu

    def default_setCoordinate1(self):
        self.treeNode.setDefaultCoordinate(1)
        self.plotPreviewSignalCommand()

    def setCoordinate1(self, alternative_coordinate):
        self.treeNode.setCoordinate(1, alternative_coordinate)
        self.plotPreviewSignalCommand()

    def menuPlotCurrentSignalNode(self, parentMenu=None):
        """The menu that plots the node the right click was built on.

        One menu for every shape. The command behind 'New' picks the frame from
        the axes the read would walk, so what used to be three menus -- one per
        leaf shape the dictionary spells -- is one entry now, and the submenu
        lists the frames that command can actually fill: the legacy 'Figure:'
        windows are built and filled by the old path, which cannot read a
        quantity of two axes, so offering them here is an entry that cannot work.

        Arguments:
            parentMenu (QMenu) : the menu to hang the "as function of time" entry
                                 from. It belongs to the context menu, not to this
                                 submenu -- but it is handed by the caller, because
                                 reading self.contextMenu made this method work
                                 only after buildContextMenu had run.
        """
        # - Add action for ploting signal node as a function of time
        action_plotAsFunctionOfTime = self.actionPlotAsFunctionOfTime()
        if action_plotAsFunctionOfTime is not None and parentMenu is not None:
            parentMenu.addAction(action_plotAsFunctionOfTime)

        menu = QMenu('Plot ' + self.signalNodeName + ' to', parentMenu)
        if parentMenu is None:
            # Parentless menus are owned by Python: held here, a caller that
            # builds this menu on its own still has something to click.
            self.plotMenu = menu
        menu.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'plotSingle'))

        # Built as a child of the menu it belongs to: the QMenu that addMenu()
        # makes from a title is owned by Python, which is the dangling submenu T0
        # removed from the Show/Hide menus -- there to look at, gone to click.
        menu_figure = QMenu('Figure', menu)
        menu_figure.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'Figure'))
        menu.addMenu(menu_figure)

        # Add action to plot the signal data to a new figure
        icon_new = GlobalIcons.getCustomQIcon(QApplication, 'new')
        action_plotNewFigure = QAction(icon_new, 'New', self)
        action_plotNewFigure.triggered.connect(self.plotSignalCommand)
        menu_figure.addAction(action_plotNewFigure)

        curveAxis = QVizNodePlotting(self.treeNode).curveAxisKey()
        for figureKey in self.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.CURVEPLOTTYPE):

            # Add menu item to add plot to specific existing figure. A figure has
            # one abscissa, so a quantity read along another one does not belong
            # in it.
            if curveAxis is None:
                continue
            if not self.figureDrawsSameCurveAxis(figureKey, curveAxis):
                continue

            # Get figure number out from the figureKey string
            # (e.g. 'SlicesPlot1' -> 1)
            id_Fig = self.imas_viz_api.getFigureKeyNum(figureKey,
                                                       FigureTypes.CURVEPLOTTYPE)
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

            # Curves and images drawn through the tensor read: any rank, the
            # frame picked by how many axes the read draws, and a named control
            # for every axis that frame leaves out. Not gated on
            # shareSameCoordinates the way the figure entries above are -- that
            # gate keeps one slider group from mixing quantities with different
            # coordinates on one figure, and here each quantity carries its own
            # controls.
            subMenu_slices = menu.addMenu('Curves and images with slice controls')
            subMenu_slices.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'new'))

            action_slices_thisDTV = QAction(icon_thisDTV, 'This IMAS Database',
                                            self)
            action_slices_thisDTV.triggered.connect(
                partial(self.plotAsSlices, False))
            subMenu_slices.addAction(action_slices_thisDTV)

            action_slices_allDTV = QAction(icon_allDTV, 'All IMAS Databases',
                                           self)
            action_slices_allDTV.triggered.connect(
                partial(self.plotAsSlices, True))
            subMenu_slices.addAction(action_slices_allDTV)

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

    def menusShowHideAndDelete(self, menu):
        """Add the Show/Hide and Delete entries for the figures that are open.

        The kinds of figure are listed once, next to the key prefixes they are
        registered under (FigureTypes.MENU_ORDER), and the two menus walk that
        list: a kind left out of the list is a window the user has no way left
        to close. That is what the five hand-copied branches, and the counts
        they were fed, bought us.

        :param menu: the QMenu being filled (the tree context menu, or the shot
                     view's "Plot windows" menu bar entry)
        """
        menu_showHide = QMenu('Show/Hide', menu)
        menu_showHide.setIcon(GlobalIcons.getCustomQIcon(QApplication,
                                                         'showHide'))
        menu_delete = QMenu('Delete', menu)
        menu_delete.setIcon(GlobalIcons.getStandardQIcon(QApplication,
                                                         QStyle.SP_DialogDiscardButton))

        openFigures = [(label, icon, figureType)
                       for label, icon, figureType in FigureTypes.MENU_ORDER
                       if self.imas_viz_api.GetFiguresCount(figureType) > 0]

        menu_showHide.setDisabled(not openFigures)
        menu_delete.setDisabled(not openFigures)

        for label, icon, figureType in openFigures:
            self.figureTypeMenus(menu_showHide, menu_delete, label, icon,
                                 figureType)

        menu.addMenu(menu_showHide)
        menu.addMenu(menu_delete)

    def figureTypeMenus(self, menu_showHide, menu_delete, label, iconLabel,
                        figureType):
        """One submenu for one kind of figure, in each of the two menus: an
        entry per open figure, plus "All" under Delete.

        Arguments:
            label      (str) : what the user reads, and the prefix the window
                               title shows
            iconLabel  (str) : the GlobalIcons name; None leaves it uniconed
            figureType (str) : the key prefix the kind is registered under
        """
        # Built parented rather than with addMenu(label): PySide6 keeps the menu
        # that call creates under Python, so it is deleted when the local variable
        # goes out of scope here and the entry the user clicks on dangles.
        submenu_showHide = QMenu(label, menu_showHide)
        subMenu_delete = QMenu(label, menu_delete)
        menu_showHide.addMenu(submenu_showHide)
        menu_delete.addMenu(subMenu_delete)
        icon = GlobalIcons.getCustomQIcon(QApplication, iconLabel)
        if icon is not None:
            submenu_showHide.setIcon(icon)
            subMenu_delete.setIcon(icon)

        for figureKey in self.imas_viz_api.GetFiguresKeys(
                figureType=figureType):
            # Get figure number out of the key string (e.g. 'Figure:0' -> 0),
            # which is what the show/hide and delete actions are keyed on
            figureNum = self.imas_viz_api.getFigureKeyNum(figureKey, figureType)

            action_showHide = QAction(figureKey, self)
            action_showHide.triggered.connect(
                partial(self.showHideFigure, figureNum, figureType))
            submenu_showHide.addAction(action_showHide)

            action_delete = QAction(figureKey, self)
            action_delete.triggered.connect(
                partial(self.deleteFigure, figureNum, figureType))
            subMenu_delete.addAction(action_delete)

        action_deleteAll = QAction('All', self)
        action_deleteAll.triggered.connect(
            partial(self.deleteAllFigures, figureType=figureType))
        subMenu_delete.addAction(action_deleteAll)

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
        """Draw the node the menu was built on, in the frame its axes call for."""
        self.plotNodeCommand()

    def plotAlongTimeCommand(self):
        """Draw the node the menu was built on as a history along time."""
        self.plotNodeCommand(alongTime=True)

    def plotNodeCommand(self, alongTime=False, intoFigureKey=None):
        """Run the one-node command and show what it drew.

        The frame is embedded only once it holds something, so a node the read
        cannot answer for costs no window; and an open figure is not embedded
        again, which is how one window ends up inside two subwindows.
        """
        command = QVizPlotOneNode(dataTreeView=self.dataTreeView,
                                  treeNode=self.treeNode,
                                  intoFigureKey=intoFigureKey,
                                  alongTime=alongTime)
        plotWidget = command.execute()
        if plotWidget is None:
            # The reason is in the log panel of this shot view already.
            return
        if command.builtFigure:
            self.imas_viz_api.addPlotWidgetToMDI(plotWidget)
        plotWidget.show()

    def plotPreviewSignalCommand(self):
        """Show preview plot.
        """
        try:
            # The panel answers for the node it is handed: it decides from the
            # axes the read would walk, draws what they allow, and says which
            # refusal it made. Nothing here has to know how big the leaf is.
            QVizPreviewPlot.forView(self.dataTreeView).showNode(self.treeNode)

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
            api.addPlotWidgetToMDI(plotWidget)
            # Plot the selected signals
            QVizPlotSelectedSignals(dataTreeView=self.dataTreeView,
                                    figureKey=figureKey,
                                    all_DTV=all_DTV,
                                    plotAxis=plotAxis).execute()

        except ValueError as e:
            logging.getLogger(self.dataTreeView.uri).error(str(e))

    # @Slot(bool)
    def plotAsSlices(self, all_DTV=True):
        """Plot the selection through the tensor read, one control per pinned axis.

        Unlike plotSelectedSignals, no figure key and no plot widget are asked
        from the api: the command builds its own frames in its own key namespace,
        so the 'Figure:' and 'Image:' entries built above cannot offer a frame the
        old path does not know how to fill. How many frames it builds is whatever
        the selection needs -- one curve figure and one figure per image -- so they
        are embedded after the read, which also keeps an empty window off the
        screen when nothing could be read.

        Arguments:
            all_DTV (bool) : Whether to consider the current or all DTVs.
        """
        if len(self.dataTreeView.selectedSignalsDict) == 0:
            logging.getLogger(self.dataTreeView.uri).error("No selection found.")
            return
        try:
            command = QVizPlotAsSlices(dataTreeView=self.dataTreeView,
                                       all_DTV=all_DTV)
            for plotWidget in command.execute():
                self.imas_viz_api.addPlotWidgetToMDI(plotWidget)
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
        """Add the node the menu was built on to a figure that is already open.

        Arguments:
            numFig (int) : Number identification of the existing figure.
        """
        # The number is read back in the namespace of the frames this command
        # fills, which is the namespace the submenu listed them from.
        self.plotNodeCommand(
            intoFigureKey=self.imas_viz_api.GetFigureKey(
                str(numFig), FigureTypes.CURVEPLOTTYPE))

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


    def figureDrawsSameCurveAxis(self, figureKey, axisKey):
        """Whether every curve already in the figure runs along this axis.

        A figure has one abscissa, and the label under it is the axis of the last
        curve read, so a quantity read along another axis does not belong in it.
        The old check asked the dictionary shape and the legacy frame factory;
        this asks the axes the read would walk, which costs a right click nothing.
        """
        for entry in self.imas_viz_api.figToNodes.get(figureKey, {}).values():
            if QVizNodePlotting(entry[1]).curveAxisKey() != axisKey:
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
        return vizTreeNode.nodeDataShareSameCoordinatesAs(figureNodesList, figureKey)

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
            if not node.nodeDataShareSameCoordinatesAs(selectedNodesList):
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
