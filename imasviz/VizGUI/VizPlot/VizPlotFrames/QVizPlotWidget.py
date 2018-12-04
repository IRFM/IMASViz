#  Name   : QVizPlotWidget
#
#          Provides plot widget template.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#*******************************************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#*******************************************************************************

import pyqtgraph as pg
from PyQt5.QtCore import Qt, QMetaObject
from PyQt5.QtGui import QWidget, QGridLayout, QCheckBox, QMenuBar, QAction
from imasviz.VizUtils.QVizGlobalValues import getRGBColorList
from imasviz.VizGUI.VizPlot.QVizCustomPlotContextMenu \
    import QVizCustomPlotContextMenu


class QVizPlotWidget(QWidget):
    """PlotWidget containing pyqtgraph PlotWidget. Used for main plotting
    feature.
    """

    def __init__(self, parent=None, size=(500, 400), title='QVizPlotWidget'):
        super(QVizPlotWidget, self).__init__(parent)

        # Set default background color: white
        pg.setConfigOption('background', 'w')
        # Set default foreground (text etc.) color: black
        pg.setConfigOption('foreground', 'k')

        # Enable antialiasing for prettier plots
        # Note: Considerably decreases performance
        pg.setConfigOptions(antialias=True)
        # pg.setConfigOptions(useOpenGL=True)

        # QVizPlotWidget settings
        self.setObjectName("QVizPlotWidget")
        self.setWindowTitle(title)
        self.resize(size[0], size[1])

        # Set up the QWidget contents (pyqtgraph PlotWidget etc.)
        self.setContents()

        # Get list of available global colors (RGB)
        self.RGBlist = getRGBColorList()

    def plot(self, x=None, y=None, title='', label='', xlabel='', ylabel='',
             pen=pg.mkPen('b', width=3, style=Qt.SolidLine)):
        """Add plot.

        Arguments:
            x      (1D array) : 1D array of X-axis values.
            y      (1D array) : 1D array of Y-axis values.
            title       (str) : Plot title.
            label       (str) : Label describing IMAS database (device, shot)
                                and path to signal/node in IDS database
                                structure.
            xlabel      (str) : Plot X-axis label.
            ylabel      (str) : Plot Y-axis label.
            pen        (QPen) : Plot line style.
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
            color_loop_counter = int(num_plots / num_avail_colors)
            # Set next RGB ID
            next_RGB_ID = num_plots - color_loop_counter * num_avail_colors
            # Set pen style
            if color_loop_counter % 2 == 0:
                style = Qt.SolidLine
            else:
                style = Qt.DotLine

            # Set pen
            # Note: width higher than '1' considerably decreases performance
            pen = pg.mkPen(color=self.RGBlist[next_RGB_ID], width=1, style=style)

        # Plot and plot settings
        # - Add plot
        self.pgPlotWidget.plot(x, y, title=title, pen=pen, name=label)
        # Set only when adding the first plot. All additionally added plots
        # should correspond to the same xlabel, ylabel and grid and thus
        # should NOT change it.
        if len(self.getPlotList()) == 1:
            # - Set x-axis label
            self.pgPlotWidget.setLabel('left', ylabel, units='')
            # - Set y-axis label
            self.pgPlotWidget.setLabel('bottom', xlabel, units='')
            # - Enable grid
            self.pgPlotWidget.showGrid(x=True, y=True)

        return self

    def getPlotItem(self):
        """Return the PlotItem contained in QVizPlotWidget.
        Note: PlotItem contains the list of plots (see getPlotList).
        """
        return self.pgPlotWidget.getPlotItem()

    def getPlotList(self):
        """Return a list of all plots (PlotDataItem, PlotCurveItem,
        ScatterPlotItem, etc) contained in QVizPlotWidget.
        """
        return self.pgPlotWidget.getPlotItem().listDataItems()

    def setContents(self):
        """Setup QVizPlotWidget contents.
        """
        self.gridLayout = QGridLayout(self)
        self.gridLayout.setObjectName("gridLayout")

        # Set plot widget (use IMASViz custom plot context menu)
        self.pgPlotWidget = pg.PlotWidget(self,
                                          viewBox=QVizCustomPlotContextMenu(qWidgetParent=self))
        self.pgPlotWidget.setObjectName("plotWidget")
        # Add legend (must be called before adding plot!!!)
        self.pgPlotWidget.addLegend()

        # Set menu bar
        menuBar = self.menuBar()
        self.gridLayout.setMenuBar(menuBar)

        # Set checkbox for toggling mouse
        checkBox = self.customUI()

        # Set layout marigin (left, top, right, bottom)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)

        # Add widgets to layout
        self.gridLayout.addWidget(self.pgPlotWidget, 1, 0, 1, 1)
        self.gridLayout.addWidget(checkBox, 2, 0, 1, 1)

        # Connect custom UI elements
        QMetaObject.connectSlotsByName(self)

    def menuBar(self):
        """Set menu bar.
        """
        menuBar = QMenuBar(self)
        exitMenu = menuBar.addMenu('File')
        exitAction = QAction('Exit', self.pgPlotWidget)
        exitAction.triggered.connect(self.close)
        exitMenu.addAction(exitAction)
        return menuBar

    def customUI(self):
        """Add custom UI elements - pure PyQt widgets, to interact with
        pyqtgraph.
        """

        # Set and add checkbox for toggling mouse plot interaction on/off
        checkBox = QCheckBox(self)
        checkBox.setChecked(True)
        checkBox.setObjectName("checkBox")
        checkBox.setText("Mouse Enabled")
        checkBox.stateChanged.connect(self.toggleMouse)
        return checkBox

    def toggleMouse(self, state):
        """Enable/Disable mouse interaction with the plot.
        Note: currently enables/disables only zoom in/out.
        """
        if state == Qt.Checked:
            enabled = True
        else:
            enabled = False

        self.pgPlotWidget.setMouseEnabled(x=enabled, y=enabled)
