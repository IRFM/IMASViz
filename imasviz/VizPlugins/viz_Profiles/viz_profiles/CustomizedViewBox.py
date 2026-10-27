# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

import pyqtgraph as pg
from functools import partial
from pyqtgraph.graphicsItems.ViewBox.ViewBoxMenu import ViewBoxMenu
from PySide6.QtWidgets import QMessageBox, QLineEdit, QMenu
from PySide6.QtGui import QAction
from imasviz.VizGUI.VizPlot.QVizPlotStyleUI import QVizPlotStyleUI
from imasviz.VizGUI.VizPlot.QVizCurveErrors import (CONFIDENCE_BANDS, ERROR_BARS,
                                                    ERROR_BARS_SLICED,
                                                    QVizCurveErrors)
from imasviz.VizDataAccess.QVizNodePlotting import QVizNodePlotting
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode \
    import QVizPlotOneNode
from imasviz.VizUtils import FigureTypes


class CustomizedViewBox(pg.ViewBox):
    """Subclass of ViewBox.
    """

    def __init__(self, qWidgetParent, imas_viz_api, parent=None):
        """Constructor of this plugin's view box.

        Arguments:
            qWidgetParent (QWidget) : the widget this view box is drawn in. A
                                      QWidget cannot be given as a pyqtgraph
                                      ViewBox's parent, so the link is held by
                                      name here instead.
            imas_viz_api  (Viz_API)  : the session's figure bookkeeping, which
                                      the "plot this into that figure" lines are
                                      read from.
            parent        (obj)     : Parent.
        """
        self.plotConfDialog = None
        self.actionPlotVsTimeToNewFigure = None
        self.actionPlotToNewFigure = None
        self.actionShowHideConfidenceBands = None
        self.actionShowHideErrorBarsWithSlicing = None
        self.actionShowHideErrorBars = None
        self.actionConfigurePlot = None
        self.actionAutoRange = None
        self.qWidgetParent = qWidgetParent

        super(CustomizedViewBox, self).__init__(parent)

        self.menu = ViewBoxMenu(self)
        self.contextMenu = None

        self.imas_viz_api = imas_viz_api

        # Menu update property
        self.menuUpdate = True

        self.vizTreeNodesList = []
        self.vizNodeToPlotDataItems = {}  # map from data key (key = dataTreeView.dataSource.dataKey(treeNode)) to PlotDataItem

        # The error bars and the band are drawn by the same object the curve
        # figures use: what this window has of its own is the menu that offers
        # them, and the pairing of a curve with the node it came from. `self`,
        # not `self.errorQuantities` -- see QVizCurvePlot for why a bound method
        # here would be a reference cycle and a segfault waiting in the collector.
        self.errors = QVizCurveErrors(self, self)

        self.plotAxis = None

    def addVizTreeNode(self, node, preview=0):
        if preview != 1:
            if node not in self.vizTreeNodesList:
                self.vizTreeNodesList.append(node)
        else:  # for the preview widget, we replace the item in the list if it exists already
            if len(self.vizTreeNodesList) == 0:
                self.vizTreeNodesList.append(node)
            else:
                self.vizTreeNodesList[0] = node

    def addVizTreeNodeDataItems(self, node, plotDataItems):
        self.vizNodeToPlotDataItems[node.getDataTreeView().dataSource.dataKey(node)] = plotDataItems

    def clearPlotDataItemsMap(self, node=None):
        if node is not None:
            self.vizNodeToPlotDataItems.pop(node.getDataTreeView().dataSource.dataKey(node), None)
        else:
            self.vizNodeToPlotDataItems.clear()

    def getMenu(self, event=None):
        """Modify the menu. Called by the pyqtgraph.ViewBox raiseContextMenu()
        routine.
        Note: Overwriting the ViewBox.py getMenu() function.
        """

        if self.menuUpdate is True:
            # Rename the two mouse-mode choices. They are held in
            # ViewBoxMenu.mouseModes: on pyqtgraph 0.13.7 the "Mouse Mode"
            # sub-menu is a local of its constructor, so the `leftMenu` attribute
            # this used to walk does not exist and the right click on a plugin
            # plot raised AttributeError before the menu could open.
            for mouseAction in self.menu.mouseModes:
                if "3 button" in mouseAction.text():
                    mouseAction.setText("Pan Mode")
                elif "1 button" in mouseAction.text():
                    mouseAction.setText("Area Zoom Mode")

            # Add custom contents to menu
            self.addCustomMenu()

            # Set menu update to false
            self.menuUpdate = False

        if self.contextMenu is None:
            self.contextMenu = QMenu()

        self.contextMenu.clear()
        self.buildContextMenu()
        self.menu.addMenu(self.contextMenu)

        return self.menu

    def addCustomMenu(self):
        """Add custom actions to the menu.
        """
        self.menu.addSeparator()
        # Auto-range feature
        self.actionAutoRange = QAction("Auto Range", self.menu)
        self.actionAutoRange.triggered.connect(self.autoRange)
        # - Add to main menu
        self.menu.addAction(self.actionAutoRange)

        # Configure plot
        self.actionConfigurePlot = QAction("Configure Plot", self.menu)
        self.actionConfigurePlot.triggered.connect(self.showConfigurePlot)
        # - Add to main menu
        self.menu.addAction(self.actionConfigurePlot)

        # The three lines the manual names, spelled once in `QVizCurveErrors`:
        # what a curve figure's right click answers and what this window answers
        # are the same words because they come from the same constants.
        self.actionShowHideErrorBars = QAction(ERROR_BARS, self.menu)
        self.actionShowHideErrorBars.triggered.connect(self.errors.toggleErrorBars)
        # - Add to main menu
        self.menu.addAction(self.actionShowHideErrorBars)

        self.actionShowHideErrorBarsWithSlicing = QAction(ERROR_BARS_SLICED, self.menu)
        self.actionShowHideErrorBarsWithSlicing.triggered.connect(self.errors.toggleSlicedErrorBars)
        # - Add to main menu
        self.menu.addAction(self.actionShowHideErrorBarsWithSlicing)

        self.actionShowHideConfidenceBands = QAction(CONFIDENCE_BANDS, self.menu)
        self.actionShowHideConfidenceBands.triggered.connect(self.errors.toggleConfidenceBands)
        # - Add to main menu
        self.menu.addAction(self.actionShowHideConfidenceBands)

        if self.plotAxis == 'TIME':
            self.actionPlotToNewFigure = QAction("Plot this in a new separate figure", self.menu)
            self.actionPlotToNewFigure.triggered.connect(self.plotVsTimeToNewFigure)
            # - Add to main menu
            self.menu.addAction(self.actionPlotToNewFigure)

            node = self.vizTreeNodesList[0]
            if node.is1D():
                self.actionPlotVsTimeToNewFigure = QAction("Plot in a new separate figure (along coordinate1 axis)",
                                                           self.menu)
                self.actionPlotVsTimeToNewFigure.triggered.connect(self.plotVsCoordinate1ToNewFigure)
                # - Add to main menu
                self.menu.addAction(self.actionPlotVsTimeToNewFigure)

        elif self.plotAxis == 'COORDINATE1':
            self.actionPlotToNewFigure = QAction("Plot this in a new separate figure", self.menu)
            self.actionPlotToNewFigure.triggered.connect(self.plotVsCoordinate1ToNewFigure)
            # - Add to main menu
            self.menu.addAction(self.actionPlotToNewFigure)

            self.actionPlotVsTimeToNewFigure = QAction("Plot in a new separate figure (along time axis)", self.menu)
            self.actionPlotVsTimeToNewFigure.triggered.connect(self.plotVsTimeToNewFigure)
            # - Add to main menu
            self.menu.addAction(self.actionPlotVsTimeToNewFigure)
        else:
            raise ValueError("Unknow plot Axis")

    def buildContextMenu(self):
        node = self.vizTreeNodesList[0]
        self.contextMenu.setTitle('Plot ' + node.getName() + ' to')
        # The windows this quantity can join are the open curve figures whose
        # curves run along the same abscissa, asked of the same registry the shot
        # view's own menu reads: two copies of that rule is two chances for the
        # two menus to list different windows. A quantity with two axes to draw
        # has no abscissa to share, so it gets no line here.
        if not QVizNodePlotting(node).curveAbscissae():
            return
        for figureKey in self.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.CURVEPLOTTYPE):
            if not self.imas_viz_api.figureDrawsSameCurveAxis(figureKey, node):
                continue

            # Set action
            action_addSignalPlotToFig = QAction(figureKey, self)
            action_addSignalPlotToFig.triggered.connect(
                partial(self.plotIntoFigure, figureKey))
            # Add to submenu
            self.contextMenu.addAction(action_addSignalPlotToFig)

    def plotIntoFigure(self, figureKey):
        """Add this plot's quantity to a figure that is already open."""
        self.plotNode(intoFigureKey=figureKey)

    def setRectMode(self):
        """Set mouse mode to rect mode for convenient zooming.
        """
        self.setMouseMode(self.RectMode)

    def setPanMode(self):
        """Set mouse mode to pan.
        """
        self.setMouseMode(self.PanMode)

    def showConfigurePlot(self):
        """Set and show custom plot configuration GUI.
        """
        self.plotConfDialog = QVizPlotStyleUI(viewBox=self)
        self.plotConfDialog.show()

    # -- what the Configure Plot dialogue asks this view box ---------------
    #
    # The dialogue used to work that out by asking what the window it is drawn
    # in is *called*: four branches on `qWidgetParent.objectName()`, of which the
    # only caller in the package took one ('QVizPlugin'), and a last branch
    # reading a `pgPlotWidget` attribute no frame of the package has. These three
    # answers are asked directly, so the dialogue needs no name and no fallback.

    def styleCurves(self):
        """The drawn curves of this panel that hand styling may change.

        `listDataItems()` answers the `PlotDataItem`s of the plot and nothing
        else: measured on a panel holding 4 curves plus an `ErrorBarItem`, an
        `InfiniteLine` and a `FillBetweenItem` -- all three in `addedItems` --
        it answers **4**. So the error bars and the band this window can draw are
        not offered as curves to style, and no list of item types to skip is
        needed to keep them out.
        """
        return list(self.plotItem.listDataItems())

    def styleText(self):
        """The plot item holding this panel's title and axis labels."""
        return self.plotItem

    def styleMargins(self):
        """The layout whose margins to set, or None for no margins section.

        Asked of the window, which is where the answer is: a panel of this table
        lives in the layout of its window's `ci`, not in one of the view box.
        """
        return self.qWidgetParent.panelLayout()

    def errorQuantities(self):
        """Which drawn curve came from which node, as [(node, PlotDataItem)].

        What `QVizCurveErrors` cannot know by itself: this window holds several
        plots per node, and the map is keyed by the node's data key, not by the
        items.
        """
        pairs = []
        for node in self.vizTreeNodesList:
            key = node.getDataTreeView().dataSource.dataKey(node)
            for dataItem in self.vizNodeToPlotDataItems.get(key) or []:
                pairs.append((node, dataItem))
        return pairs

    def plotVsCoordinate1ToNewFigure(self):
        """This quantity, in a figure of its own, read along its own coordinate."""
        self.plotNode()

    def plotVsTimeToNewFigure(self):
        """This quantity, in a figure of its own, read along time."""
        self.plotNode(alongTime=True)

    def plotNode(self, intoFigureKey=None, alongTime=False):
        """Run the one-node command, the same the shot view's menu runs.

        The frame is the one the axes call for and the api knows how to fill:
        embedded in the MDI area, listed by the Show/Hide and Delete menus, and
        offered to the "add to" gestures -- which the legacy window these two
        entries used to open was none of those. A quantity the read cannot
        answer for costs no window, and its reason goes to the log of the case
        it came from.
        """
        node = self.vizTreeNodesList[0]
        command = QVizPlotOneNode(dataTreeView=node.getDataTreeView(),
                                  treeNode=node,
                                  intoFigureKey=intoFigureKey,
                                  alongTime=alongTime)
        frame = command.execute()
        if frame is None:
            return
        if command.builtFigure:
            self.imas_viz_api.addPlotWidgetToMDI(frame)
        frame.show()
