#  Name   : QVizPlotWidget
#
#          Provides node documentation widget template.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
# ****************************************************
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
# ****************************************************

from PySide2.QtWidgets import (QTableWidget, QTableWidgetItem, QDialog,
                             QSizePolicy, QGridLayout, QHeaderView)

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
        """Create window displaying current selected paths.
        """
        self.dataTreeView = dataTreeView
        selectedSignalsDict = self.dataTreeView.selectedSignalsDict
        title = 'Selected paths: (' + self.dataTreeView.dataSource.getName() + ")"
        self.setWindowTitle(title)
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
