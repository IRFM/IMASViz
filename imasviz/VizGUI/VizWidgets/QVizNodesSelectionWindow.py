#  Name   : QVizPlotWidget
#
#          Provides node documentation widget template.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#****************************************************

import numpy
import sys

from functools import partial
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import QAbstractScrollArea, QMainWindow, QPushButton, QVBoxLayout, \
    QHBoxLayout, QTableWidget, QTableWidgetItem, QDialog, QSizePolicy, QGridLayout, QHeaderView, QMenu, QApplication, QAction

from imasviz.VizUtils.QVizGlobalValues import GlobalColors, GlobalFonts
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizUtils.QVizGlobalValues import GlobalIcons, FigureTypes
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal import QVizPlotSignal


# class QVizHandleRightClickInNodesSelectionWindow:
#     """ Handle the mouse right click event on a PyQt5 QTreeWidget.
#     """
#
#     def __init__(self, dataTreeView):
#         """
#         Arguments:
#             dataTreeView (QTreeWidget) : QVizDataTreeView object.
#         """
#         self.dataTreeView = dataTreeView
#
#     def execute(self, node):
#
#         showPopUpMenu = QVizSignalHandling(dataTreeView=self.dataTreeView)
#         showPopUp = showPopUpMenu.showPopUpMenu(signalNodeName=dataName)
#         return showPopUp

class QVizNodesSelectionWindow(QDialog):
    """Set nodes selection window.
    """
    def __init__(self, dataTreeView, parent=None):
        super(QVizNodesSelectionWindow, self).__init__(parent=parent)
        self.create(dataTreeView)

    def create(self,dataTreeView):

        self.dataTreeView = dataTreeView

        #self.setContextMenuPolicy(Qt.DefaultContextMenu)

        #self.contextMenu = QMenu()

        #self.contextMenu.addMenu(self.menuPlotCurrentSignalNode())

        selectedSignalsDict = self.dataTreeView.selectedSignalsDict
        """Create window displaying current selected paths.
        """
        title = 'Selected paths'
        table = QTableWidget()
        table.setRowCount(len(selectedSignalsDict))
        table.setColumnCount(2)
        tableHeader = ["IMAS Path", "IDS Occurrence"]
        table.setHorizontalHeaderLabels(tableHeader)
        table.setColumnWidth(1, 500)
        table.setColumnWidth(2, 100)
        row = 0
        for key in selectedSignalsDict:
            v = selectedSignalsDict[key]
            vizTreeNode = v['QTreeWidgetItem']
            table.setItem(row, 0, QTableWidgetItem(vizTreeNode.getPath()))
            table.setItem(row, 1, QTableWidgetItem(str(vizTreeNode.getOccurrence())))
            row += 1

        self.setObjectName('Current selected paths')
        self.resize(600, 600)
        self.setModal(True)
        layout = QGridLayout()
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # layout.addWidget(QPushButton('Top'))
        # layout.addWidget(QPushButton('Bottom'))
        layout.addWidget(table)
        self.setLayout(layout)

    # def contextMenuEvent(self, event):
    #     """ Custom menu event on right click on the table widget.
    #     """
    #     treeNode = self.selectedItems()[0]  # QTreeWidgetItem object
    #
    #     # Set selected QTreeWidgetItem on right click
    #     self.setSelectedItem(item=treeNode, mouseButton="RIGHT")
    #
    #     # Get position
    #     self.pos = event.pos()
    #
    #     # Set and show the popup
    #     handleRightClick = QVizHandleRightClickInNodesSelectionWindow(self)
    #     showPopUp = handleRightClick.execute(treeNode)
    #
    # def menuPlotCurrentSignalNode(self):
    #     """Set menu for plotting current (under the mouse selected) signal node.
    #     """
    #
    #     menu = QMenu('Plot ' + self.signalNodeName + ' to', self.contextMenu)
    #     menu.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'plotSingle'))
    #
    #     menu_figure = menu.addMenu('Figure')
    #     menu_figure.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'Figure'))
    #
    #     # Add action to plot the signal data to a new figure
    #     icon_new = GlobalIcons.getCustomQIcon(QApplication, 'new')
    #     action_plotNewFigure = QAction(icon_new, 'New', self)
    #     action_plotNewFigure.triggered.connect(self.plotSignalCommand)
    #     menu_figure.addAction(action_plotNewFigure)
    #
    #     for figureKey in self.imas_viz_api.GetFiguresKeys(
    #             figureType=FigureTypes.FIGURETYPE):
    #         # Get figure number out from the figureKey string
    #         # (e.g. 'Figure:0' -> 0)
    #         # id_Fig = int(figureKey.split(':')[1])
    #         id_Fig = self.imas_viz_api.getFigureKeyNum(figureKey)
    #
    #         # Add menu item to add plot to specific existing figure
    #         # Check for figures that share the same coordinates
    #         if self.shareSameCoordinatesFrom(figureKey):
    #             # Set action
    #             action_addSignalPlotToFig = QAction(figureKey, self)
    #             action_addSignalPlotToFig.triggered.connect(
    #                 partial(self.addSignalPlotToFig, id_Fig))
    #             # Add to submenu
    #             menu_figure.addAction(action_addSignalPlotToFig)
    #
    #
    #     return menu
    #
    # @pyqtSlot(int)
    # def addSignalPlotToFig(self, numFig):
    #     """Add signal plot to existing figure.
    #
    #     Arguments:
    #         numFig (int) : Number identification of the existing figure.
    #     """
    #     try:
    #         # Get figure key (e.g. 'Figure:0' string)
    #         figureKey = self.imas_viz_api. \
    #             GetFigureKey(str(numFig), figureType=FigureTypes.FIGURETYPE)
    #         QVizPlotSignal(dataTreeView=self.dataTreeView,
    #                        nodeData=self.nodeData,
    #                        figureKey=figureKey,
    #                        update=0).execute()
    #     except ValueError as e:
    #         self.dataTreeView.log.error(str(e))
    #
    # @pyqtSlot()
    # def plotSignalCommand(self):
    #     """Basic plotting of signal node plottable data command.
    #     """
    #     try:
    #
    #         # Get next figure label (e.g. 'Figure:0')
    #         self.currentFigureKey = self.imas_viz_api.GetNextKeyForFigurePlots()
    #         label = None
    #         xlabel = None
    #
    #         # If signal node is a part of time_slice array of structures
    #         # (e.g. 'equilibrium.time_slice[0].profiles_1d.psi')
    #         if self.treeNode != None and \
    #             self.treeNode.treeNodeExtraAttributes.time_dependent_aos():
    #             aos_vs_itime = self.treeNode.getDataPathVsTime(
    #                 self.treeNode.treeNodeExtraAttributes.aos)
    #             label = self.treeNode.getPath()
    #             xlabel = QVizGlobalOperations.replaceBrackets(
    #                 self.treeNode.evaluateCoordinate1At(
    #                     self.treeNode.infoDict['i']))
    #             self.timeSlider = True
    #
    #         # Get the signal data for plot widget
    #         # TODO: remove signalHandling as an argument
    #         p = QVizPlotSignal(self.dataTreeView, self.nodeData, signal=None,
    #                            figureKey=self.currentFigureKey, label=label,
    #                            xlabel=xlabel, signalHandling=self)
    #         # Plot signal data to plot widget
    #         p.execute()
    #
    #     except ValueError as e:
    #         self.dataTreeView.log.error(str(e))

