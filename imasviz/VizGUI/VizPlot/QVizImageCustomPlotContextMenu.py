#  Name   : QVizCustomPlotContextMenu
#
#          Modified plot context menu.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
# *****************************************************************************
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
# *****************************************************************************

import pyqtgraph as pg
from PySide2.QtCore import Qt, Signal
from PySide2.QtWidgets import QAction, QMenu
from imasviz.VizGUI.VizPlot.QVizCustomPlotContextMenu import QVizCustomPlotContextMenu
from imasviz.VizGUI.VizPlot.QVizImageSlicesPlotConfigUI \
    import QVizImageSlicesPlotConfigUI


class QVizImageCustomPlotContextMenu(QVizCustomPlotContextMenu):
    """Subclass of ViewBox.
    """

    def __init__(self, qWidgetParent, parent=None, axis=1):
        """Constructor of the QVizCustomPlotContextMenu

        Arguments:
            qWidgetParent (QWidget) : Parent of ViewBox which is PyQt5 QWidget
                                      object (setting QWidget (PyQt5) as a
                                      regular ViewBox (pyqtgraph) parent doesn't
                                      seem to be allowed).
            parent        (obj)     : Parent.
        """
        self.qWidgetParent = qWidgetParent
        self.axis = axis
        super(QVizImageCustomPlotContextMenu, self).__init__(
            qWidgetParent=qWidgetParent, parent=parent)
        self.plotConfDialog = None

        self.displayMenu1D = False

    def showConfigurePlot(self):
        """Set and show custom plot configuration GUI.
        """
        if self.axis == 1:
            self.plotConfDialog = QVizImageSlicesPlotConfigUI(
                slicesPlotItem=self.qWidgetParent.slicesXPlotItem,
                axis=self.axis)
        else:
            self.plotConfDialog = QVizImageSlicesPlotConfigUI(
                slicesPlotItem=self.qWidgetParent.slicesYPlotItem,
                axis=self.axis)

        self.plotConfDialog.show()

    def addCustomMenu(self):

        super().addCustomMenu()

        """Add custom actions to the menu.
        """
        self.menu.addSeparator()

        #Plot to a new figure
        self.actionPlotToNewFigure = QAction("Plot this in a new separate figure", self.menu)
        if self.axis == 1:
            self.actionPlotToNewFigure.triggered.connect(self.qWidgetParent.slicesXPlotItem.plotToNewFigure)
        else:
            self.actionPlotToNewFigure.triggered.connect(self.qWidgetParent.slicesYPlotItem.plotToNewFigure)
        # - Add to main menu
        self.menu.addAction(self.actionPlotToNewFigure)

        # Plot a slice
        self.keepSlice = QAction("Keep this slice", self.menu)
        if self.axis == 1:
            self.keepSlice.triggered.connect(self.qWidgetParent.slicesXPlotItem.keepSlice)
        else:
            self.keepSlice.triggered.connect(self.qWidgetParent.slicesYPlotItem.keepSlice)
        self.menu.addAction(self.keepSlice)

        # Remove all slices
        self.removeAllSlices = QAction("Delete all slices", self.menu)
        if self.axis == 1:
            self.removeAllSlices.triggered.connect(
                self.qWidgetParent.slicesXPlotItem.removeAllSlices)
        else:
            self.removeAllSlices.triggered.connect(
                self.qWidgetParent.slicesYPlotItem.removeAllSlices)
        self.menu.addAction(self.removeAllSlices)

        # Add a new marker
        self.addMarker = QAction("Add new marker", self.menu)
        if self.axis == 1:
            self.addMarker.triggered.connect(
                self.qWidgetParent.slicesXPlotItem.addNewMarker)
        else:
            self.addMarker.triggered.connect(
                self.qWidgetParent.slicesYPlotItem.addNewMarker)
        self.menu.addAction(self.addMarker)
