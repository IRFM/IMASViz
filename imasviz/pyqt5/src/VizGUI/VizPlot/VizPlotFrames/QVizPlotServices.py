#  Name   : QVizPlotWidget
#
#          Provides basic pyqtgraph plot window template.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#****************************************************

# from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt
import pyqtgraph as pg
from pyqtgraph import mkPen

class QVizPlotServices():
    def __init__(self):
        pass

    def plot(self, x=None, y=None, title='', xlabel='', ylabel='', pen=mkPen('b', width=3, style=Qt.SolidLine)):
        plotWidget = pg.plot(title=title)
        plotWidget.resize(400, 400)
        plotWidget.plot(x, y, pen=pen)
        plotWidget.setLabel('left', 'Value', units='V')
        plotWidget.setLabel('bottom', 'Time', units='s')
        return plotWidget