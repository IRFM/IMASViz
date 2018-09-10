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
# from pyqtgraph.Qt import QtGui, QtCore
from PyQt5 import QtGui, QtCore
import pyqtgraph as pg
# import numpy as np


class QVizPlotWidget(PlotWidget):
    def __init__(self, x,y, parent=None,  name='PlotWidget', title='', **kws):
        super(QVizPlotWidget, self).__init__()

        self.parent = parent

        layout = QtGui.QVBoxLayout(self)
        # layout = QtGui.QGridLayout()
        self.setLayout(layout)

        self.resize(400,400)
        # p1.setPen((200,200,100))

        ## Add in some extra graphics
        # rect = QtGui.QGraphicsRectItem(QtCore.QRectF(0, 0, 1, 5e-11))
        # rect.setPen(pg.mkPen(100, 200, 100))
        # self.addItem(rect)

        self.setLabel('left', 'Value', units='V')
        self.setLabel('bottom', 'Time', units='s')

        # yd, xd = self.rand(10000)
        p1 = self.plot(x, y, pen='r')
        # p1.setData(y=yd, x=xd)
        layout.addWidget(self)
        self.show()
