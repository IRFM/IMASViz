#  Name   : QVizPreviewPlotWidget
#
#          Provides plot widget template.
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
from pyqtgraph import PlotWidget, mkPen
from PyQt5.QtGui import QWidget, QGridLayout, QCheckBox, QMenuBar, QAction
from PyQt5.QtCore import Qt, QMetaObject, QSize

class QVizPreviewPlotWidget(QWidget):

    def __init__(self, parent=None, size=(500,400), title='QVizPreviewPlotWidget'):
        super(QVizPreviewPlotWidget, self).__init__(parent=parent)

        # Set default background color: white
        pg.setConfigOption('background', 'w')
        # Set default foreground (text etc.) color: black
        pg.setConfigOption('foreground', 'k')

        # Enable antialiasing for prettier plots
        pg.setConfigOptions(antialias=True)

        # QVizPreviewPlotWidget settings
        self.setObjectName("QVizPreviewPlotWidget")
        self.setWindowTitle(title)
        # self.resize(size[0], size[1])

        # set up the form class as a `ui` attribute
        self.ui = QVizPlotWidgetUI()
        self.ui.setupUi(self)

    def plot(self, x=[0], y=[0], title='', label='', xlabel='', ylabel='',
             pen=mkPen('b', width=3, style=Qt.SolidLine)):
        """Add plot.

        Arguments:
            shotnumber (int) : IDS database parameter - shot number of the case.
            x     (1D array) : 1D array of X-axis values.
            y     (1D array) : 1D array of Y-axis values.
            title      (str) : Plot title.
            label      (str) : Label describing IMAS database (device, shot) and
                               path to signal/node in IDS database structure.
            xlabel     (str) : Plot X-axis label.
            ylabel     (str) : Plot Y-axis label.
            pen        ()    : Plot line style.
        """
        # Access the UI elements through the `ui` attribute
        # Add plot
        self.ui.plotWidget.plot(x, y, title='', pen=pen, name=label)
        # Set x-axis label
        self.ui.plotWidget.setLabel('left', xlabel, units='')
        # Set y-axis label
        self.ui.plotWidget.setLabel('bottom', ylabel, units='')
        # Enable grid
        self.ui.plotWidget.showGrid(x=True, y=True)
        return self

    def clear(self):
        """Clear the widgets plot.
        """
        self.ui.plotWidget.clear()

class QVizPlotWidgetUI(object):
    def setupUi(self, QVizPreviewPlotWidget):
        """ Setup QVizPreviewPlotWidget User Interface.

        Arguments:
            dataTreeView (QWidget) : QWidget object.
        """

        # Get widget
        self.QVizPreviewPlotWidget = QVizPreviewPlotWidget
        # Set layout
        self.gridLayout = QGridLayout(self.QVizPreviewPlotWidget)
        self.gridLayout.setObjectName("gridLayout")

        # Set plotwidget
        self.plotWidget = PlotWidget(self.QVizPreviewPlotWidget)
        self.plotWidget.setObjectName("pg_PreviewPlot")
        # Add legend (must be called before adding plot!!!)
        # self.plotWidget.addLegend()

        # Set menu bar
        menuBar = self.menuBar()
        self.gridLayout.setMenuBar(menuBar)

        # Set checkbox for toggling mouse
        #checkBox = self.customUI()

        # Set layout marigin (left, top, right, bottom)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)

        # Add widgets to layout
        self.gridLayout.addWidget(self.plotWidget, 1, 0, 1, 1)
        # self.gridLayout.addWidget(checkBox, 2, 0, 1, 1)
        self.gridLayout.update()

        # Connect custom UI elements
        QMetaObject.connectSlotsByName(self.QVizPreviewPlotWidget)

    def menuBar(self):
        menuBar = QMenuBar(self.QVizPreviewPlotWidget)
        exitMenu = menuBar.addMenu('File')
        exitAction = QAction('Exit', self.plotWidget)
        exitAction.triggered.connect(self.QVizPreviewPlotWidget.close)
        exitMenu.addAction(exitAction)
        return menuBar

    def customUI(self):
        """ Add custom UI elements - pure PyQt widgets, to interact with
        pyqtgraph.

        Arguments:
            dataTreeView (QWidget) : QWidget object.
        """

        # Set and add checkbox for toggling mouse plot interaction on/off
        checkBox = QCheckBox(self.QVizPreviewPlotWidget)
        checkBox.setChecked(True)
        checkBox.setObjectName("checkBox")
        checkBox.setText("Mouse Enabled")
        checkBox.stateChanged.connect(self.toggleMouse)
        return checkBox

    def toggleMouse(self, state):
        if state == Qt.Checked:
            enabled = True
        else:
            enabled = False

        self.QVizPreviewPlotWidget.ui.plotWidget.setMouseEnabled(x=enabled,
                                                                 y=enabled)



