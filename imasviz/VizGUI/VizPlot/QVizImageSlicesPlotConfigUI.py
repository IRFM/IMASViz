# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import pyqtgraph as pg
from PySide6.QtCore import Qt, QRect, Slot
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
        

