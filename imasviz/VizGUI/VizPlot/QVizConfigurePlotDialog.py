#  Name   : QVizConfigurePlotDialog
#
#          Tabbed widget enabling plot customization (line colors etc.).
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
from PyQt5.QtGui import QTabWidget, QWidget, QPushButton, QGridLayout, \
    QDialogButtonBox, QDialog, QVBoxLayout
from PyQt5.QtCore import Qt, QRect

class QVizConfigurePlotDialog(QDialog):
    """Tabbed widget allowing plot customization.
    """
    def __init__(self, viewBox, parent=None, size=(500,400)):
        super(QVizConfigurePlotDialog, self).__init__(parent)

        # Dialog settings
        self.setObjectName("QVizConfigurePlotDialog")
        self.setWindowTitle("Configure Plot")
        self.resize(size[0], size[1])

        # Set viewBox variable
        self.viewBox = viewBox

        # Set tabbed widget
        self.tabWidget = QTabWidget(self)
        # Add tabs
        self.tabWidget.addTab(TabColorAndLineProperties(parent=self),
                              "Color and Line Properties")
        # Set Cancel and Ok buttons
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setGeometry(QRect(50, 240, 341, 32))
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|
                                          QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        # Set main layout
        self.mainLayout = QVBoxLayout(self)
        # Add tabs and other widgets to dialog layout
        self.mainLayout.addWidget(self.tabWidget)
        self.mainLayout.addWidget(self.buttonBox)
        # Set dialog layout
        self.setLayout(self.mainLayout)

class TabColorAndLineProperties(QWidget):
    """Widget allowing plot color and line customization.
    """
    def __init__(self, parent=None, size=(500,400)):
        super(TabColorAndLineProperties, self).__init__(parent)

        # Widget settings
        self.setObjectName("TabColorAndLineProperties")
        self.setWindowTitle("Color and Line Properties")
        self.resize(size[0], size[1])

        self.parent = parent
        # Set viewBox variable
        self.viewBox = self.parent.viewBox

        # List of plotDataItems within viewBox
        self.listPlotDataItems = self.viewBox.addedItems

        # Set up the QWidget contents
        self.setContents()

    def setContents(self):
        """ Set widget contents.
        """
        # Set layout
        self.gridLayout = QGridLayout(self)
        self.gridLayout.setObjectName("gridLayout")

        # Set layout marigin (left, top, right, bottom)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)

        self.testButton = QPushButton("testButton")
        self.gridLayout.addWidget(self.testButton, 0, 0, 0, 0)

        self.setLayout(self.gridLayout)

        # self.gridLayout.update()


