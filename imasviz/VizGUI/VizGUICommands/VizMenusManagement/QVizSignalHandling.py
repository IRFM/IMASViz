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

from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsSlices import QVizPlotAsSlices
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsStacked import QVizPlotAsStacked
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsTable import QVizPlotAsTable
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode import QVizPlotOneNode
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPreviewPlot import QVizPreviewPlot
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectNodes import QVizSelectNodes
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizPluginsPopUpMenu import QVizPluginsPopUpMenu
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

    def actionSelectOrUnselectSignalNode(self):
        """Set action to select/unselect signal node.

        Asked of the view's selection, which is what every plot command reads.
        The flag this used to ask (`infoDict['isSelected']`) was a second record
        of the same fact, written by the selection commands beside it and never
        cleared when the selection was: measured, a node the selection had lost
        was still offered as "Unselect ...", and the entry it triggered answered
        with a KeyError instead of clearing the flag.
        """
        s = ''
        if QVizSelectNodes(self.dataTreeView,
                           self.treeNode).isSelected(self.treeNode):
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
        #
        # The submenu is named after the frame the entry is about to open, since
        # the two frames answer different questions and nothing else in the menu
        # says which window is coming. A quantity with two axes to draw needs the
        # image frame, and that frame holds one quantity per figure, so no window
        # is already open that its axes could join: 'New' is the whole menu. Which
        # frame it is comes from the axes alone -- curveAxisKey() answers None as
        # soon as the leaf has more than one axis of its own -- because the answer
        # that measures values, plottedAxes(), would extract a tensor for a right
        # click that may never draw anything.
        curveAxis = QVizNodePlotting(self.treeNode).curveAxisKey()
        frameType = 'Figure' if curveAxis is not None else 'Image'
        menu_frame = QMenu(frameType, menu)
        menu_frame.setIcon(GlobalIcons.getCustomQIcon(QApplication, frameType))
        menu.addMenu(menu_frame)

        # Add action to plot the signal data to a new figure
        icon_new = GlobalIcons.getCustomQIcon(QApplication, 'new')
        action_plotNewFigure = QAction(icon_new, 'New', self)
        action_plotNewFigure.triggered.connect(self.plotSignalCommand)
        menu_frame.addAction(action_plotNewFigure)

        for figureKey in self.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.CURVEPLOTTYPE):

            # Add menu item to add plot to specific existing figure. A figure has
            # one abscissa, so a quantity read along another one does not belong
            # in it; and a picture has no abscissa at all to share.
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
            menu_frame.addAction(action_addSignalPlotToFig)

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

            # One entry per intent, not two. This branch built its windows
            # through the old frame factory and hid them behind
            # shareSameCoordinates, while a second branch just below drew the
            # same selection through the tensor read -- two entries, two key
            # namespaces, two answers for one gesture. A user selects quantities
            # and not figure types, so the command picks the frame: a curve
            # figure for what has one axis to draw, one window per picture. And
            # there is nothing left to gate: the gate kept one slider group from
            # mixing quantities with different coordinates, and each quantity now
            # carries the controls for the axes its frame leaves out.
            #
            # Submenus built as QMenu(title, parent) -- the dangling submenu T0
            # removed from the Show/Hide menus.
            subMenu_figure = QMenu('Figure', menu)
            subMenu_figure.setIcon(GlobalIcons.getCustomQIcon(QApplication,
                                                              'Figure'))
            menu.addMenu(subMenu_figure)

            subMenu_figure_new = QMenu('New', subMenu_figure)
            subMenu_figure_new.setIcon(GlobalIcons.getCustomQIcon(QApplication,
                                                                  'new'))
            subMenu_figure.addMenu(subMenu_figure_new)

            icon_thisDTV = GlobalIcons.getCustomQIcon(QApplication, 'thisDTV')
            icon_allDTV = GlobalIcons.getCustomQIcon(QApplication, 'allDTV')

            # --------------------------------------------------------------
            # Add menu item to plot selected signals to single
            # plot - This DTV, then all DTVs
            for icon, label, all_DTV in ((icon_thisDTV, 'This IMAS Database',
                                          False),
                                         (icon_allDTV, 'All IMAS Databases',
                                          True)):
                action_figure = QAction(icon, label, self)
                action_figure.triggered.connect(
                    partial(self.plotSelectedSignals, all_DTV))
                subMenu_figure_new.addAction(action_figure)

            for figureKey in self.imas_viz_api.GetFiguresKeys(
                    figureType=FigureTypes.CURVEPLOTTYPE):

                # Only the frames this command can fill. A picture window holds
                # one quantity, with its colour scale and its controls, so it is
                # not offered here; and the legacy 'Figure:' keys are not offered
                # either, because the old path that filled them is gone.
                id_Fig = self.imas_viz_api.getFigureKeyNum(figureKey,
                                                           FigureTypes.CURVEPLOTTYPE)
                subMenu_figure_existing = QMenu(figureKey, subMenu_figure)
                subMenu_figure.addMenu(subMenu_figure_existing)
                for icon, label, all_DTV in ((icon_thisDTV,
                                              'This IMAS Database', False),
                                             (icon_allDTV, 'All IMAS Databases',
                                              True)):
                    action_figure_existing = QAction(icon, label, self)
                    action_figure_existing.triggered.connect(
                        partial(self.addSelectedSignalsPlotToFig, id_Fig,
                                all_DTV))
                    subMenu_figure_existing.addAction(action_figure_existing)

            # ------------------------------------------------------------------

            # TablePlotView: one panel per quantity, each read on the axes it
            # sits on. Two strategies stay because the user is the one who says
            # whether a quantity in a dynamic array is followed along time or
            # along its own coordinate; 'DEFAULT' leaves that answer to the read
            # per quantity, which is what lets a selection mixing coordinates
            # come out with one labelled panel each.
            #
            # The gate this branch used to hide behind -- do these signals share
            # coordinates? -- is gone: a panel shares nothing, so there is
            # nothing to agree on. Measured on the old window, that gate returned
            # False for a selection it drew correctly anyway.
            subMenu_TPV = QMenu('TablePlotView', menu)
            subMenu_TPV.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'TPV'))
            menu.addMenu(subMenu_TPV)

            for title, plotAxis in (("New (default axis)", 'DEFAULT'),
                                    ("New ('TIME' axis)", 'TIME')):
                subMenu_TPV_new = QMenu(title, subMenu_TPV)
                subMenu_TPV_new.setIcon(GlobalIcons.getCustomQIcon(QApplication,
                                                                   'new'))
                subMenu_TPV.addMenu(subMenu_TPV_new)
                for icon, label, all_DTV in ((icon_thisDTV,
                                              'This IMAS Database', False),
                                             (icon_allDTV,
                                              'All IMAS Databases', True)):
                    action_TPV = QAction(icon, label, self)
                    action_TPV.triggered.connect(
                        partial(self.onPlotToTablePlotView, all_DTV=all_DTV,
                                configFile=None, plotAxis=plotAxis))
                    subMenu_TPV_new.addAction(action_TPV)

            # ------------------------------------------------------------------
            # StackedPlotView: the same panels as the table, stacked in one
            # column against one abscissa. The two strategies stay for the same
            # reason as above; what differs is that the abscissa is shared here,
            # so the command refuses by name a quantity the read would take
            # along another axis, and sends the user to TablePlotView.
            #
            # The gate this branch hid behind -- do these signals share
            # coordinates? -- is gone. Measured, it answered False for the very
            # selection the old window drew, and it picked which of the four
            # entries asked for the time axis: three of them asked for it
            # whatever the selection was.
            subMenu_SPV = QMenu('StackedPlotView', menu)
            subMenu_SPV.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'SPV'))
            menu.addMenu(subMenu_SPV)

            for title, plotAxis in (("New (default axis)", 'DEFAULT'),
                                    ("New ('TIME' axis)", 'TIME')):
                subMenu_SPV_new = QMenu(title, subMenu_SPV)
                subMenu_SPV_new.setIcon(GlobalIcons.getCustomQIcon(QApplication,
                                                                   'new'))
                subMenu_SPV.addMenu(subMenu_SPV_new)
                for icon, label, all_DTV in ((icon_thisDTV,
                                              'This IMAS Database', False),
                                             (icon_allDTV,
                                              'All IMAS Databases', True)):
                    action_SPV = QAction(icon, label, self)
                    action_SPV.triggered.connect(
                        partial(self.onPlotToStackedPlotView, all_DTV=all_DTV,
                                plotAxis=plotAxis))
                    subMenu_SPV_new.addAction(action_SPV)


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
        QVizSelectNodes(self.dataTreeView, self.treeNode).execute()

    @Slot()
    def selectOrUnselectSignal(self):
        QVizSelectNodes(self.dataTreeView, self.treeNode).execute()

    @Slot(bool)
    def onUnselectSignals(self, all_DTV=False):
        """Unselect all signals (single or all DTVs)."""
        QVizSelectNodes(self.dataTreeView, all_DTV=all_DTV).unselectAll()

    @Slot()
    def selectAllSignalsFromSameAOS(self):
        QVizSelectNodes(self.dataTreeView, self.treeNode).sameAos()

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
    def plotSelectedSignals(self, all_DTV=True, intoFigureKey=None):
        """Plot the selected nodes, in the frame each quantity needs.

        The old entry asked the api for a figure and embedded it in the MDI area
        before anything had been read, so a selection that could not be read still
        cost the user a window to close -- and an empty selection died on a
        `str(e)` written outside any except. Here the command reads first and
        builds whatever the selection needs: one curve figure for the quantities
        with one axis to draw, one window per picture. Only the frames it built
        are embedded, so adding to a figure already on screen does not embed it a
        second time.

        Arguments:
            all_DTV (bool) : Whether to consider the current or all DTVs.
            intoFigureKey (str) : an open curve figure to add the selection to.
        """
        if len(self.dataTreeView.selectedSignalsDict) == 0:
            # Not an error to report through the exception path: the menu holds
            # this entry disabled when nothing is selected, so reaching here means
            # the selection went away between the menu and the click.
            logging.getLogger(self.dataTreeView.uri).error("No selection found.")
            return
        try:
            command = QVizPlotAsSlices(dataTreeView=self.dataTreeView,
                                       all_DTV=all_DTV,
                                       intoFigureKey=intoFigureKey)
            for plotWidget in command.execute():
                self.imas_viz_api.addPlotWidgetToMDI(plotWidget)
        except ValueError as e:
            logging.getLogger(self.dataTreeView.uri).error(str(e))

    @Slot(bool)
    def onPlotToTablePlotView(self, all_DTV=False, configFile=None,
                              plotAxis=None):
        """Plot selected nodes from single/all opened DTVs to a Table Plot View.

        The command reads the quantities first and gives each one a panel of its
        own, read on the axes it actually sits on; the old path built the window
        before reading anything, so a selection that could not be read still cost
        the user a window to close, and a quantity with two axes to draw either
        died on the read or came back as a curve of one of its elements.

        Arguments:
            all_DTV (bool) : Whether to consider the current or all DTVs.
            configFile (str) : a saved plot configuration: it names the
                               quantities by path instead of taking them from
                               the selection.
            plotAxis (str) : 'TIME' to read every quantity along time, anything
                             else to let the read answer per quantity.
        """
        try:
            command = QVizPlotAsTable(dataTreeView=self.dataTreeView,
                                      all_DTV=all_DTV,
                                      plotAxis=plotAxis,
                                      configFile=configFile)
            frame = command.execute()
            if frame is not None:
                self.imas_viz_api.addPlotWidgetToMDI(frame)
        except ValueError as e:
            logging.getLogger(self.dataTreeView.uri).error(str(e))

    @Slot(bool)
    def onPlotToStackedPlotView(self, all_DTV=False, plotAxis='TIME'):
        """Plot selected nodes from single/all opened DTVs to a Stacked Plot View.

        The command reads the quantities first, then stacks one panel per
        quantity against the abscissa the first one gives: the old path built the
        window before reading anything, so an unreadable selection still cost the
        user a registered window with no plot in it, and a quantity the window
        could not share was drawn against another quantity's abscissa and
        labelled with it.

        The default stays 'TIME' because that is what the scripting entry has
        always asked for; the menu says which of the two strategies it wants.

        Arguments:
            all_DTV (bool) : Whether to consider the current or all DTVs.
            plotAxis (str) : 'TIME' to read every quantity along time, anything
                             else to let the read answer per quantity.
        """
        try:
            command = QVizPlotAsStacked(dataTreeView=self.dataTreeView,
                                        all_DTV=all_DTV,
                                        plotAxis=plotAxis)
            frame = command.execute()
            if frame is not None:
                self.imas_viz_api.addPlotWidgetToMDI(frame)
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
        """Add the selected nodes to an already open curve figure.

        Arguments:
            numFig (int) : Number identification of the existing figure.
            all_DTV (bool) : Whether to consider the current or all DTVs.
        """
        # The figure the entry listed is one of the frames this command builds:
        # the legacy 'Figure:' keys are not offered any more, because the path
        # that filled them is gone.
        try:
            self.plotSelectedSignals(
                all_DTV=all_DTV,
                intoFigureKey=self.imas_viz_api.GetFigureKey(
                    str(numFig), FigureTypes.CURVEPLOTTYPE))
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
