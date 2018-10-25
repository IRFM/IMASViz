#  Name   : QVizPlotWidget
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
from PyQt5.QtCore import Qt, QMetaObject
from PyQt5.QtGui import QWidget, QGridLayout, QCheckBox, QMenuBar, QAction
from pyqtgraph import PlotWidget, mkPen

from imasviz.VizUtils.QVizGlobalValues import getRGBColorList


class QVizPlotWidget(QWidget):

    def __init__(self, parent=None, size=(500,400), title='QVizPlotWidget'):
        super(QVizPlotWidget, self).__init__(parent=parent)

        # Set default background color: white
        pg.setConfigOption('background', 'w')
        # Set default foreground (text etc.) color: black
        pg.setConfigOption('foreground', 'k')

        # Enable antialiasing for prettier plots
        pg.setConfigOptions(antialias=True)

        # QVizPlotWidget settings
        self.setObjectName("QVizPlotWidget")
        self.setWindowTitle(title)
        self.resize(size[0], size[1])

        # set up the form class as a `ui` attribute
        self.ui = QVizPlotWidgetUI()
        self.ui.setupUi(self)

        # Get list of available global colors (RGB)
        self.RGBlist = getRGBColorList()

    def plot(self, x=None, y=None, title='', label='', xlabel='', ylabel='',
             pen=mkPen('b', width=3, style=Qt.SolidLine)):
        """Add plot.
        """

        # Set pen (line design). Color and style are chosen depending on the
        # number of already present plots
        if self.RGBlist != None:
            # Get number of already present plots
            num_plots = len(self.getPlotList())
            # Number of available colors
            num_avail_colors = len(self.RGBlist)

            # Set color loop counter (for cases where there are more plots
            # than available plot color+style variations)
            color_loop_counter = int(num_plots/num_avail_colors)
            # Set next RGB ID
            next_RGB_ID = num_plots - color_loop_counter*num_avail_colors
            # Set pen style
            if color_loop_counter % 2 == 0:
                style = Qt.SolidLine
            else:
                style = Qt.DotLine

            # Set pen
            pen = mkPen(color=self.RGBlist[next_RGB_ID], width=3, style=style)

        # access your UI elements through the `ui` attribute
        # plot = self.ui.plotWidget.plot(x, y, title='', pen=pen)
        # Add plot
        self.ui.plotWidget.plot(x, y, title='', pen=pen, name=label)
        # Set x-axis label
        self.ui.plotWidget.setLabel('left', xlabel, units='')
        # Set y-axis label
        self.ui.plotWidget.setLabel('bottom', ylabel, units='')
        # Enable grid
        self.ui.plotWidget.showGrid(x=True, y=True)
        return self

    def getPlotItem(self):
        """Return the PlotItem contained in QVizPlotWidget.
        Note: PlotItem contains the list of plots (see getPlotList).
        """
        return self.ui.plotWidget.getPlotItem()

    def getPlotList(self):
        """Return a list of all plots (PlotDataItem, PlotCurveItem,
        ScatterPlotItem, etc) contained in QVizPlotWidget.
        """
        return self.ui.plotWidget.getPlotItem().listDataItems()

class QVizPlotWidgetUI(object):
    def setupUi(self, QVizPlotWidget):
        """ Setup QVizPlotWidget User Interface.

        Arguments:
            dataTreeView (QWidget) : QWidget object.
        """

        self.QVizPlotWidget = QVizPlotWidget
        self.gridLayout = QGridLayout(self.QVizPlotWidget)
        self.gridLayout.setObjectName("gridLayout")

        # Set plot widget
        self.plotWidget = PlotWidget(self.QVizPlotWidget)
        self.plotWidget.setObjectName("plotWidget")
        # Add legend (must be called before adding plot!!!)
        self.plotWidget.addLegend()

        # Set menu bar
        menuBar = self.menuBar()
        self.gridLayout.setMenuBar(menuBar)

        # Set checkbox for toggling mouse
        checkBox = self.customUI()

        # Set lavout marigin (left, top, right, bottom)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)

        # Add widgets to layout
        self.gridLayout.addWidget(self.plotWidget, 1, 0, 1, 1)
        self.gridLayout.addWidget(checkBox, 2, 0, 1, 1)

        # Connect custom UI elements
        QMetaObject.connectSlotsByName(self.QVizPlotWidget)

    def menuBar(self):
        menuBar = QMenuBar(self.QVizPlotWidget)
        exitMenu = menuBar.addMenu('File')
        exitAction = QAction('Exit', self.plotWidget)
        exitAction.triggered.connect(self.QVizPlotWidget.close)
        exitMenu.addAction(exitAction)
        return menuBar

    def customUI(self):
        """ Add custom UI elements - pure PyQt widgets, to interact with
        pyqtgraph.

        Arguments:
            dataTreeView (QWidget) : QWidget object.
        """

        # Set and add checkbox for toggling mouse plot interaction on/off
        checkBox = QCheckBox(self.QVizPlotWidget)
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

        self.QVizPlotWidget.ui.plotWidget.setMouseEnabled(x=enabled, y=enabled)



