# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

import pyqtgraph as pg
import numpy as np
from functools import partial
from pyqtgraph.graphicsItems.ViewBox.ViewBoxMenu import ViewBoxMenu
import logging
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QInputDialog, QLineEdit, QMenu
from PySide6.QtGui import QAction
from imasviz.VizGUI.VizPlot.QVizPlotConfigUI import QVizPlotConfigUI
from imasviz.VizUtils import FigureTypes

from pyqtgraph.exporters.Matplotlib import Exporter


class CustomizedViewBox(pg.ViewBox):
    """Subclass of ViewBox.
    """

    def __init__(self, qWidgetParent, imas_viz_api, parent=None):
        """Constructor of the QVizCustomPlotContextMenu

        Arguments:
            qWidgetParent (QWidget) : Parent of ViewBox which is PyQt5 QWidget
                                      object (setting QWidget (PyQt5) as a
                                      regular ViewBox (pyqtgraph) parent
                                      doesn't seem to be allowed).
            parent        (obj)     : Parent.
        """
        self.confidenceBandLower = None
        self.plotConfDialog = None
        self.confidenceBandUpper = None
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

        # Default id
        self.id = 0

        # Menu update property
        self.menuUpdate = True

        # Modify list of available exporters (in order to remove the
        # problematic Matplotlib exporter and replace it with ours)
        self.updateExportersList()

        self.vizTreeNodesList = []
        self.vizNodeToPlotDataItems = {}  # map from data key (key = dataTreeView.dataSource.dataKey(treeNode)) to PlotDataItem

        self.errorBars = 0
        self.errorBarsWithSlicing = 0
        self.errorBarsStep = 0
        self.confidenceBands = 0

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
            # Modify contents of the original ViewBoxMenu
            for action in self.menu.actions():
                # Modify the original Mouse Mode
                if "Mouse Mode" in action.text():
                    # Change action labels
                    for mouseAction in self.menu.leftMenu.actions():
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

        self.actionShowHideErrorBars = QAction("Show/Hide error bars", self.menu)
        self.actionShowHideErrorBars.triggered.connect(self.showHideViewErrorBars)
        # - Add to main menu
        self.menu.addAction(self.actionShowHideErrorBars)

        self.actionShowHideErrorBarsWithSlicing = QAction("Show error bars (with slicing)", self.menu)
        self.actionShowHideErrorBarsWithSlicing.triggered.connect(self.showHideViewErrorBarsWithSlicing)
        # - Add to main menu
        self.menu.addAction(self.actionShowHideErrorBarsWithSlicing)

        self.actionShowHideConfidenceBands = QAction("Show/Hide confidence bands", self.menu)
        self.actionShowHideConfidenceBands.triggered.connect(self.showHideViewConfidenceBands)
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
        for figureKey in self.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.FIGURETYPE):

            id_Fig = self.imas_viz_api.getFigureKeyNum(figureKey,
                                                       FigureTypes.FIGURETYPE)

            # Add menu item to add plot to specific existing figure
            # Check for figures that share the same coordinates
            if self.imas_viz_api.nodeDataShareSameCoordinates(figureKey, node):
                # Set action
                action_addSignalPlotToFig = QAction(figureKey, self)
                action_addSignalPlotToFig.triggered.connect(
                    partial(self.imas_viz_api.AddPlot1DToFig, id_Fig, node))
                # Add to submenu
                self.contextMenu.addAction(action_addSignalPlotToFig)

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
        self.plotConfDialog = QVizPlotConfigUI(viewBox=self)
        self.plotConfDialog.show()

    def showHideViewConfidenceBands(self):
        """Hide/show error bars for all plots (if error data are available).
        """
        deleted = self.removeConfidenceBands()
        if not deleted:
            self.addConfidenceBands()
            self.confidenceBands = 1

    def removeConfidenceBands(self):
        """Remove error bars for all plots (if error data are available).
        """
        deleted = False
        itemsToRemove = []
        for dataItem in self.addedItems:
            if isinstance(dataItem, pg.FillBetweenItem):
                deleted = True
                itemsToRemove.append(dataItem)
        for dataItem in itemsToRemove:
            self.removeItem(dataItem.curves[0])
            self.removeItem(dataItem.curves[1])
            self.removeItem(dataItem)
        if deleted:
            self.confidenceBands = 0
        return deleted

    def updateConfidenceBands(self):
        if self.confidenceBands == 0:
            return
        self.removeConfidenceBands()
        self.showHideViewConfidenceBands()

    def updateErrorBars(self):
        if self.errorBars == 0 and self.errorBarsWithSlicing == 0:
            return
        if self.errorBars == 1:
            self.removeErrorBars()
            self.showHideViewErrorBars()
        elif self.errorBarsWithSlicing == 1:
            self.removeErrorBars()
            self.showHideViewErrorBarsWithSlicing(useLatestSettings=1)

    def removeErrorBars(self):
        """Remove error bars for all plots (if error data are available).
        """
        deleted = False
        itemsToRemove = []
        for dataItem in self.addedItems:
            if isinstance(dataItem, pg.ErrorBarItem):
                deleted = True
                itemsToRemove.append(dataItem)
        for dataItem in itemsToRemove:
            self.removeItem(dataItem)
        if deleted:
            self.errorBars = 0
            self.errorBarsWithSlicing = 0
        return deleted

    def showHideViewErrorBars(self):
        """Hide/show error bars for all plots (if error data are available).
        """
        deleted = self.removeErrorBars()
        if not deleted:
            self.addErrorBars(1, beam=0)
            self.errorBars = 1

    def showHideViewErrorBarsWithSlicing(self, useLatestSettings=0):
        """Show error bars for all plots with slicing (if error data are available).
        """
        self.removeErrorBars()
        step = self.errorBarsStep

        if step == 0 or useLatestSettings == 0:
            user_input = QInputDialog()
            step, ok = user_input.getInt(None, "Enter a step value for slicing", "Step:", value=10, minValue=1)
            if not ok:
                logging.error("Bad input from user.")
                return

        self.addErrorBars(step, beam=0)
        self.errorBarsWithSlicing = 1

    def addConfidenceBands(self):
        for node in self.vizTreeNodesList:
            dataTreeView = node.getDataTreeView()
            plotDataItems = self.vizNodeToPlotDataItems.get(dataTreeView.dataSource.dataKey(node))
            if plotDataItems is None:
                continue
            for dataItem in plotDataItems:
                self.addConfidenceBandsForDataItem(dataItem, node)

    def addConfidenceBandsForDataItem(self, dataItem, vizTreeNode):
        (x, y) = dataItem.getData()
        shape_x = len(x)
        shape_y = len(y)
        data_error_lower = vizTreeNode.get_data_error_lower(dataItem)
        data_error_upper = vizTreeNode.get_data_error_upper(dataItem)
        add_confidence_bands = False
        upper = None
        lower = None

        if data_error_lower is not None and data_error_upper is not None:
            lower = data_error_lower
            upper = data_error_upper
            add_confidence_bands = True
        elif data_error_lower is None and data_error_upper is not None:
            lower = data_error_upper
            upper = data_error_upper
            add_confidence_bands = True
        else:
            add_confidence_bands = False

        if add_confidence_bands:
            self.confidenceBandUpper = None
            self.confidenceBandLower = None
            self.confidenceBandUpper = pg.PlotDataItem(x, y + upper)
            self.confidenceBandLower = pg.PlotDataItem(x, y - lower)
            self.addItem(self.confidenceBandUpper)
            self.addItem(self.confidenceBandLower)
            fbitem = pg.FillBetweenItem(self.confidenceBandLower, self.confidenceBandUpper)
            brush = pg.mkBrush('r')
            brush.setStyle(Qt.DiagCrossPattern)
            brush.setColor(Qt.red)
            # self.fbitem.setBrush(brush)
            self.addItem(fbitem)

        else:
            logging.getLogger(vizTreeNode.dataTreeView.dataSource.uri).error("No errors data available for: " + vizTreeNode.getParametrizedDataPath())

    def addErrorBars(self, step, beam=0.5):

        self.errorBarsStep = step

        for node in self.vizTreeNodesList:
            dataTreeView = node.getDataTreeView()
            plotDataItems = self.vizNodeToPlotDataItems.get(dataTreeView.dataSource.dataKey(node))
            if plotDataItems is None:
                continue
            for dataItem in plotDataItems:
                if beam == 0:
                    (x, y) = dataItem.getData()
                    x_range = np.amax(x) - np.amin(x)
                    minBeam = float(x_range / 1000)
                    maxBeam = float(x_range / 20)
                    beam = float(x_range / len(x))
                    beam = np.maximum(minBeam, beam)
                    beam = np.minimum(maxBeam, beam)

                self.addErrorBarsForDataItem(dataItem, node, step, beam)

    def addErrorBarsForDataItem(self, dataItem, vizTreeNode, step=1, beam=0.5):

        (x, y) = dataItem.getData()
        shape_x = len(x)
        shape_y = len(y)

        if step != 1:
            x = x[0:shape_x - 1:step]
            y = y[0:shape_y - 1:step]

        data_error_lower = vizTreeNode.get_data_error_lower(dataItem)
        data_error_upper = vizTreeNode.get_data_error_upper(dataItem)

        if step != 1:
            if data_error_lower is not None:
                data_error_lower = data_error_lower[0:shape_y - 1:step]
            if data_error_upper is not None:
                data_error_upper = data_error_upper[0:shape_y - 1:step]

        add_error_bars = False
        top = None
        bottom = None

        if data_error_lower is not None and data_error_upper is not None:
            bottom = data_error_lower
            top = data_error_upper
            add_error_bars = True
        elif data_error_lower is None and data_error_upper is not None:
            bottom = data_error_upper
            top = data_error_upper
            add_error_bars = True
        else:
            add_error_bars = False

        if add_error_bars:
            error = pg.ErrorBarItem(beam=beam)
            error.setData(x=x, y=y, top=top, bottom=bottom)
            self.addItem(error)
        else:
            logging.getLogger(vizTreeNode.dataTreeView.dataSource.uri).error("No errors data available for: " + vizTreeNode.getParametrizedDataPath())

    def updateExportersList(self):
        """Update/Modify list of available exporters (in order to remove the
        problematic Matplotlib exporter and replace it with ours).
        """
        # Remove the pyqtgrapth Matplotlib Window and add our Matplotlib Window
        # v2 to the same place on the list (initially it is on the end of the
        # list)
        for exporter in Exporter.Exporters:
            if exporter.Name == 'Matplotlib Window':
                i = Exporter.Exporters.index(exporter)
                del Exporter.Exporters[i]
            if exporter.Name == 'Matplotlib Window (v2)':
                i = Exporter.Exporters.index(exporter)
                Exporter.Exporters.insert(2, Exporter.Exporters.pop(i))

    def plotVsCoordinate1ToNewFigure(self):
        from imasviz.Viz_API import Viz_API
        node = self.vizTreeNodesList[0]
        currentFigureKey = 0
        key = node.dataTreeView.dataSource.dataKey(node)
        tup = (node.dataTreeView.dataSource.uri, node)
        figureKey = self.imas_viz_api.GetNextKeyForFigurePlots()
        self.imas_viz_api.AddNodeToFigure(figureKey, key, tup)
        self.imas_viz_api.plotVsCoordinate1AtGivenTime(node.dataTreeView, figureKey, node, 0)

    def plotVsTimeToNewFigure(self):
        from imasviz.Viz_API import Viz_API
        node = self.vizTreeNodesList[0]
        currentFigureKey = 0
        key = node.dataTreeView.dataSource.dataKey(node)
        tup = (node.dataTreeView.dataSource.uri, node)
        figureKey = self.imas_viz_api.GetNextKeyForFigurePlots()
        self.imas_viz_api.AddNodeToFigure(figureKey, key, tup)
        self.imas_viz_api.plotVsTimeAtGivenCoordinate1(node.dataTreeView, 0, figureKey, node, 0, 0)
