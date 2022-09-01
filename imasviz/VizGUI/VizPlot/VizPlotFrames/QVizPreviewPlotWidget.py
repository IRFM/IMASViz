#  Name   : QVizPreviewPlotWidget
#
#          Provides plot widget template.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
# *****************************************************************************
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
# *****************************************************************************

import pyqtgraph as pg
import numpy as np
from PyQt5.QtGui import (QWidget, QGridLayout, QCheckBox, QMenuBar, QAction,
                         QLabel)
from PyQt5.QtCore import Qt, QMetaObject
from imasviz.VizGUI.VizPlot.QVizCustomPlotContextMenu \
    import QVizCustomPlotContextMenu
from imasviz.VizUtils import GlobalFonts, PlotTypes
from imasviz.VizGUI.VizPlot.VizPlotFrames.QvizPlotImageWidget import QvizPlotImageWidget
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPlotWidget import QVizPlotWidget

class QVizPreviewPlotWidget(QVizPlotWidget):
    """PlotWidget containing pyqtgraph PlotWidget. Used for creating preview
    plots.
    """
    def __init__(self, dataTreeView, parent=None, size=(500, 400),
                 title='QVizPreviewPlotWidget'):
        #super(QVizPreviewPlotWidget, self).__init__(parent=parent)
        super(QVizPreviewPlotWidget, self).__init__(dataTreeView=dataTreeView, parent=parent, size=size, title=title)

        # Set default background color: white
        pg.setConfigOption('background', 'w')
        # Set default foreground (text etc.) color: black
        pg.setConfigOption('foreground', 'k')

        # Enable antialiasing for prettier plots
        pg.setConfigOptions(antialias=True)

        # QVizPreviewPlotWidget settings
        #self.setObjectName("QVizPreviewPlotWidget")
        #self.setWindowTitle(title)
        # self.resize(size[0], size[1])

        # Set up the QWidget contents (pyqtgraph PlotWidget etc.)
        #self.setContents()

        #self.vizTreeNodesList = []
        #self.dataTreeView = dataTreeView

        self.addTimeSlider = False
        self.addCoordinateSlider = False

        self.plotStrategy = "DEFAULT"

    def getType(self):
        return PlotTypes.PREVIEW_PLOT

    def setStrategy(self, strategy):
        self.plotStrategy = strategy

    def getStrategy(self):
        return self.plotStrategy

    def plot2D(self, data):
        self.pg2dPlotWidget.plot(data)

    def plot(self, vizTreeNode=None, x=[0], y=[0], title='', label='', xlabel='', ylabel='',
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

        if vizTreeNode is not None and vizTreeNode.hasClosedOutline(self.dataTreeView) and self.getStrategy() == 'COORDINATE1':
                x = np.append(x, [x[0]])
                y = np.append(y, [y[0]])
        # Access the UI elements through the `ui` attribute
        # Adding plot
        #Setting range manually (see IMAS-3658)
        self.pgPlotWidget.getPlotItem().setRange(xRange=(min(x), max(x)), yRange=(min(y), max(y)))
        self.pgPlotWidget.plot(x, y, title='', pen=pen, name=label)
        # Set x-axis label
        self.pgPlotWidget.setLabel('left', ylabel, units='')
        # Set y-axis label
        self.pgPlotWidget.setLabel('bottom', xlabel, units='')
        # Enable grid
        self.pgPlotWidget.showGrid(x=True, y=True)

        self.pgPlotWidget.autoRange()
        
        if vizTreeNode is not None and len(self.vizTreeNodesList) == 1:
            self.vizTreeNodesList[0] = vizTreeNode
        elif vizTreeNode is not None and len(self.vizTreeNodesList) == 0:
            self.vizTreeNodesList.append(vizTreeNode)
        return self

    def clear(self, treeNode, noPreviewAvailable=False):
        """Clear the widgets plot.
        """
        self.pgPlotWidget.clear()
        if noPreviewAvailable:
            self.pgPlotWidget.setVisible(False)
            self.pg2dPlotWidget.setVisible(False)
            self.noPreviewLabel.setVisible(True)
        elif treeNode.is0D() or treeNode.is1D():
            self.pgPlotWidget.setVisible(True)
            self.pg2dPlotWidget.setVisible(False)
            self.noPreviewLabel.setVisible(False)
        elif treeNode.is2D():
            self.pgPlotWidget.setVisible(False)
            self.pg2dPlotWidget.setVisible(True)
            self.noPreviewLabel.setVisible(False)

    def setContents(self):
        """ Set QVizPreviewPlotWidget contents.
        """

        # Set layout
        self.gridLayout = QGridLayout(self)
        self.gridLayout.setObjectName("gridLayout")
        # Set layout marigin (left, top, right, bottom)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)

        # Set plotwidget (use IMASViz custom plot context menu)
        self.pgPlotWidget = \
            pg.PlotWidget(self,
                          viewBox=QVizCustomPlotContextMenu(qWidgetParent=self))
        self.pgPlotWidget.setObjectName("pg_PreviewPlot")
        # Add legend (must be called before adding plot!!!)
        # self.pgPlotWidget.addLegend()

        # Add widgets to layout
        self.gridLayout.addWidget(self.pgPlotWidget, 1, 0, 1, 1)


        # Set plotwidget (use IMASViz custom plot context menu)
        self.pg2dPlotWidget = QvizPlotImageWidget(size=(500, 400), dataTreeView=None, showImageTitle=False)
        # Add widgets to layout
        self.gridLayout.addWidget(self.pg2dPlotWidget, 1, 0, 1, 1)

        # Set menu bar
        # Note: Currently disabled as there are no features for preview plot
        #       yet available
        # menuBar = self.menuBar()
        # self.gridLayout.setMenuBar(menuBar)

        # Set checkbox for toggling mouse
        # checkBox = self.customUI()

        self.noPreviewLabel = QLabel()
        self.noPreviewLabel.setText("No preview available")
        self.noPreviewLabel.setAlignment(Qt.AlignLeft)
        self.noPreviewLabel.setWordWrap(True)
        self.noPreviewLabel.setFixedHeight(25)
        self.noPreviewLabel.setFont(GlobalFonts.TEXT_MEDIUM)
        self.noPreviewLabel.setVisible(False)
        self.gridLayout.addWidget(self.noPreviewLabel, 1, 0, 1, 1)
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
