#  Name   : QVizImageSlicesPlotConfigUI
#
#          Dialog containing tabs with options for direct plot customization of image slices
#          (line colors etc.).
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
# ****************************************************
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
# ****************************************************

import pyqtgraph as pg
from PyQt5.QtCore import Qt, QRect, pyqtSlot
from functools import partial
from imasviz.VizUtils import GlobalQtStyles, GlobalPgSymbols, GlobalIcons
from imasviz.VizGUI.VizPlot.QVizPlotConfigUI import QVizPlotConfigUI


class QVizImageSlicesPlotConfigUI(QVizPlotConfigUI):
    """Tabbed widget allowing plot customization.
    """

    def __init__(self, slicesPlotItem, parent=None, size=(1000, 400), axis=1):

        # Set viewBox variable
        self.axis = axis
        self.slicesPlotItem = slicesPlotItem

        viewBox = self.slicesPlotItem.slice_plotItem.getViewBox()

        super(QVizImageSlicesPlotConfigUI, self).__init__(viewBox=viewBox, parent=parent)
        self.setObjectName("QVizImageSlicesPlotConfigUI")

    def saveLegendItem(self):
        if self.axis == 1:
            self.legendItem = self.slicesPlotItem.slice_plotItem.legend
        else:
            self.legendItem = self.slicesPlotItem.slice_plotItem.legend
        

