#  Name   : QVizCustomPlotContextMenu
#
#          Modified plot context menu.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
#****************************************************

import pyqtgraph as pg
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QAction, QMenu
from imasviz.VizGUI.VizPlot.QVizCustomPlotContextMenu import QVizCustomPlotContextMenu

class QVizImageCustomPlotContextMenu(QVizCustomPlotContextMenu):
    """Subclass of ViewBox.
    """

    def __init__(self, qWidgetParent, parent=None):
        """Constructor of the QVizCustomPlotContextMenu

        Arguments:
            qWidgetParent (QWidget) : Parent of ViewBox which is PyQt5 QWidget
                                      object (setting QWidget (PyQt5) as a
                                      regular ViewBox (pyqtgraph) parent doesn't
                                      seem to be allowed).
            parent        (obj)     : Parent.
        """
        self.qWidgetParent = qWidgetParent
        super(QVizImageCustomPlotContextMenu, self).__init__(qWidgetParent=qWidgetParent, parent=parent)


    def addCustomMenu(self):

        super().addCustomMenu()

        """Add custom actions to the menu.
        """
        self.menu.addSeparator()

        # Plot a slice
        self.keepSlice = QAction("Keep this slice", self.menu)
        self.keepSlice.triggered.connect(self.qWidgetParent.keepSlice)
        self.menu.addAction(self.keepSlice)

        #Remove all slices
        self.removeAllSlices = QAction("Delete all slices", self.menu)
        self.removeAllSlices.triggered.connect(self.qWidgetParent.removeAllSlices)
        self.menu.addAction(self.removeAllSlices)



