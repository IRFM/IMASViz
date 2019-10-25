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

        selectedSignalsDict = self.dataTreeView.selectedSignalsDict
        """Create window displaying current selected paths.
        """
        title = 'Selected paths'
        table = QTableWidget()
        table.setRowCount(len(selectedSignalsDict))
        table.setColumnCount(3)
        tableHeader = ["IMAS Path", "IDS Occurrence", "IDS"]
        table.setHorizontalHeaderLabels(tableHeader)
        table.horizontalHeader().setResizeMode(0, QHeaderView.Stretch)
        table.setColumnWidth(1, 500)
        table.setColumnWidth(2, 10)
        table.setColumnWidth(3, 50)
        row = 0
        for key in selectedSignalsDict:
            v = selectedSignalsDict[key]
            vizTreeNode = v['QTreeWidgetItem']
            table.setItem(row, 0, QTableWidgetItem(vizTreeNode.getPath()))
            table.setItem(row, 1, QTableWidgetItem(str(vizTreeNode.getOccurrence())))
            table.setItem(row, 2, QTableWidgetItem(vizTreeNode.getIDSName()))
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
