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
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
#****************************************************

import pyqtgraph as pg
from PyQt5.QtGui import QWidget, QGridLayout, QCheckBox, QMenuBar, QAction
from PyQt5.QtCore import Qt, QMetaObject, QSize
from imasviz.VizGUI.VizPlot.QVizCustomPlotContextMenu \
    import QVizCustomPlotContextMenu

class QVizPreviewPlotWidget(QWidget):
    """PlotWidget containing pyqtgraph PlotWidget. Used for creating preview
    plots.
    """
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

        # Set up the QWidget contents (pyqtgraph PlotWidget etc.)
        self.setContents()

        self.vizTreeNodesList = []

        self.addTimeSlider = False
        self.addCoordinateSlider = False

    def plot(self, x=[0], y=[0], title='', label='', xlabel='', ylabel='',
             pen=pg.mkPen('b', width=3, style=Qt.SolidLine)):
        """Add plot.

        Arguments:
            shotnumber  (int) : IDS database parameter - shot number of the
                                case.
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
        # Access the UI elements through the `ui` attribute
        # Add plot
        self.pgPlotWidget.plot(x, y, title='', pen=pen, name=label)
        # Set x-axis label
        self.pgPlotWidget.setLabel('left', ylabel, units='')
        # Set y-axis label
        self.pgPlotWidget.setLabel('bottom', xlabel, units='')
        # Enable grid
        self.pgPlotWidget.showGrid(x=True, y=True)
        return self

    def clear(self):
        """Clear the widgets plot.
        """
        self.pgPlotWidget.clear()

    def setContents(self):
        """ Set QVizPreviewPlotWidget contents.
        """

        # Set layout
        self.gridLayout = QGridLayout(self)
        self.gridLayout.setObjectName("gridLayout")

        # Set plotwidget (use IMASViz custom plot context menu)
        self.pgPlotWidget = pg.PlotWidget(self,
            viewBox=QVizCustomPlotContextMenu(qWidgetParent=self))
        self.pgPlotWidget.setObjectName("pg_PreviewPlot")
        # Add legend (must be called before adding plot!!!)
        # self.pgPlotWidget.addLegend()

        # Set menu bar
        # Note: Currently disabled as there are no features for preview plot
        #       yet available
        # menuBar = self.menuBar()
        # self.gridLayout.setMenuBar(menuBar)

        # Set checkbox for toggling mouse
        #checkBox = self.customUI()

        # Set layout marigin (left, top, right, bottom)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)

        # Add widgets to layout
        self.gridLayout.addWidget(self.pgPlotWidget, 1, 0, 1, 1)
        # self.gridLayout.addWidget(checkBox, 2, 0, 1, 1)
        self.gridLayout.update()

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
        """ Add custom UI elements - pure PyQt widgets, to interact with
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

