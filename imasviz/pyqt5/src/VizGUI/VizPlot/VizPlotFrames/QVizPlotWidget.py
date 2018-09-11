#  Name   : QVizPlotWidget
#
#          Provides basic plot widget required for plotting.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#****************************************************

from pyqtgraph import PlotWidget
from PyQt5 import QtGui, QtCore
import pyqtgraph as pg

class QVizPlotServices():
    def __init__(self):
        pass

    def plot(self, x=None, y=None, title='Single plot', pen='b'):
        plotWidget = pg.plot(title=title)
        plotWidget.resize(400, 400)
        plotWidget.plot(x, y, pen=pen)
        plotWidget.setLabel('left', 'Value', units='V')
        plotWidget.setLabel('bottom', 'Time', units='s')
        return plotWidget
