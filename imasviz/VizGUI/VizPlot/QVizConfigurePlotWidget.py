#  Name   : QVizConfigurePlotWidget
#
#          Widget enabling plot customization (line colors etc.).
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#****************************************************

import pyqtgraph as pg
from PyQt5.QtGui import QWidget


class QVizConfigurePlotWidget(QWidget):
    """Widget allowing plot customization.
    """
    def __init__(self, viewBox, parent=None, size=(500,400)):
        super(QVizConfigurePlotWidget, self).__init__(parent)

        # QVizConfigurePlotWidget settings
        self.setObjectName("QVizConfigurePlotWidget")
        self.setWindowTitle("Configure Plot")
        self.resize(size[0], size[1])

        self.viewBox = viewBox

        # List of plotDataItems within viewBox
        self.listPlotDataItems = self.viewBox.addedItems

        # TODO create layout


