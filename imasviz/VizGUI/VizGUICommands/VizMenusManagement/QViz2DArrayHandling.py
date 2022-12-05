#  Name   : QViz2DArrayHandling
#
#          Container to handle right-click events for 2D arrays
#          tree items (PyQt5).
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
# ****************************************************
#     Copyright(c) 2016- L. Fleury, L. Xinyi, D. Penko
# ****************************************************

from functools import partial
import re, logging
from PySide6.QtCore import QObject, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QApplication, QStyle
from imasviz.VizUtils import GlobalIcons, QVizPreferences, FigureTypes

class QViz2DArrayHandling(QObject):
    def __init__(self, dataTreeView):
        """
        Arguments:
            dataTreeView (QTreeWidget) : DataTreeView object of the QTreeWidget.
        """
        super(QViz2DArrayHandling, self).__init__(parent=dataTreeView)
        self.dataTreeView = dataTreeView
        self.imas_viz_api = self.dataTreeView.imas_viz_api
        # Get signal node (tree item) data
        if self.dataTreeView.selectedItem is not None:
            self.nodeData = self.dataTreeView.selectedItem.getInfoDict()
        self.treeNode = self.dataTreeView.selectedItem

    def plot2DArray(self):
        try:
            self.imas_viz_api.Plot2DArray(self.dataTreeView, self.treeNode)
        except ValueError as e:
            logging.error(str(e))


    def menuPlotCurrentArrayNode(self, signalHandling):
        """Set menu for plotting current (under the mouse selected) signal node.
        """
        # - Add action for ploting array node
        #self.contextMenu.addAction(self.actionPlot2DArray())

        menu = QMenu('Plot ' + self.treeNode.getDataName() + ' to', signalHandling.contextMenu)
        menu.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'plotSingle'))

        menu_figure = menu.addMenu('Image')
        menu_figure.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'Image'))

        # Add action to plot the signal data to a new figure
        icon_new = GlobalIcons.getCustomQIcon(QApplication, 'new')
        action_plotNewFigure = QAction(icon_new, 'New', signalHandling)
        action_plotNewFigure.triggered.connect(self.plot2DArray)
        menu_figure.addAction(action_plotNewFigure)

        # for figureKey in self.imas_viz_api.GetFiguresKeys(
        #         figureType=FigureTypes.FIGURETYPE):
        #
        #     # Get figure number out from the figureKey string
        #     # (e.g. 'Figure:0' -> 0)
        #     # id_Fig = int(figureKey.split(':')[1])
        #     id_Fig = self.imas_viz_api.getFigureKeyNum(figureKey, FigureTypes.FIGURETYPE)
        #
        #     # Add menu item to add plot to specific existing figure
        #     # Check for figures that share the same coordinates
        #     if self.nodeDataShareSameCoordinates(figureKey, self.treeNode):
        #         # Set action
        #         action_addSignalPlotToFig = QAction(figureKey, self)
        #         action_addSignalPlotToFig.triggered.connect(
        #             partial(self.addSignalPlotToFig, id_Fig))
        #         # Add to submenu
        #         menu_figure.addAction(action_addSignalPlotToFig)


        return menu

    # def actionPlot2DArray(self):
    #     # Add action to plot 2D array data
    #     # TODO: icon
    #     try:
    #         icon = GlobalIcons.getCustomQIcon(QApplication, 'plotSingle')
    #         action_plot2DArray = QAction(icon, 'Plot 2D image', self)
    #         api = self.dataTreeView.imas_viz_api
    #         action_plot2DArray.triggered.connect(
    #             partial(api.Plot2DArray, self.dataTreeView, self.treeNode))
    #         action_plot2DArray.setDisabled(False)
    #         return action_plot2DArray
    #     except ValueError as e:
    #         logging.error(str(e))
