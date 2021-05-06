#  Name   : QVizPlotServices
#
#          Provides basic pyqtgraph plot window template.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
# *****************************************************************************
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
# *****************************************************************************

# from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt
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
