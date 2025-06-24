# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

# from PySide6 import QtGui, QtCore
from PySide6.QtCore import Qt
import pyqtgraph as pg
from pyqtgraph import mkPen


class QVizPlotServices():
    def __init__(self):
        pass

    def plot(self, x=None, y=None, title='', xlabel='', ylabel='',
             pen=mkPen('b', width=3, style=Qt.SolidLine)):
        plotWidget = pg.plot(title=title)
        plotWidget.getPlotItem().setRange(xRange=(min(x), max(x)), yRange=(min(y), max(y)))
        plotWidget.resize(400, 400)
        plotWidget.plot(x, y, pen=pen)
        plotWidget.setLabel('left', xlabel, units='')
        plotWidget.setLabel('bottom', ylabel, units='')
        return plotWidget
