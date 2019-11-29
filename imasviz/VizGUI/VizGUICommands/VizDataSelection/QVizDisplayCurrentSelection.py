#  Name   : QVizDisplayCurrentSelection.py
#
#          Displays current nodes selection.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- L. Fleury, X. Li., D. Penko
#****************************************************

import time
import xml.etree.ElementTree as ET
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand


from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QWindow


class QVizDisplayCurrentSelection(QVizAbstractCommand):
    """Displays current nodes selection.

    Arguments:
        dataTreeView (QTreeWidget) : Corresponding DataTreeView.
    """

    def __init__(self, dataTreeView, treeNode=None):
        """Set self.nodeData = nodeData etc. with the use of the
           QVizAbstractCommand
        """
        QVizAbstractCommand.__init__(self, treeNode)
        self.dataTreeView = dataTreeView

    def execute(self):
        # Get list of signals, selected in the DataTreeView (dataTreeView)
        self.dataTreeView.imas_viz_api.ShowNodesSelection(self.dataTreeView)

