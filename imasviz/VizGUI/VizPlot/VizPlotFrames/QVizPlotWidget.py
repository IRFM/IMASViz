#  Name   : QVizPlotWidget
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

import numpy as np
import logging
from PySide6.QtCore import Qt, QMetaObject, QRect
from PySide6.QtWidgets import QWidget, QGridLayout, QCheckBox, QMenuBar, \
                        QLabel, QFrame, QTextEdit
from PySide6.QtGui import QAction
from functools import partial
from PySide6.QtWidgets import QApplication, QMenu, QStyle
import PySide6.QtWidgets as QtWidgets
from imasviz.VizUtils import (QVizGlobalOperations, getRGBColorList,
                              GlobalFonts, PlotTypes)
from imasviz.VizGUI.VizPlot.QVizCustomPlotContextMenu \
    import QVizCustomPlotContextMenu

import pyqtgraph as pg


class QVizPlotWidget(QWidget):
    """PlotWidget containing pyqtgraph PlotWidget. Used for main plotting
    feature.
    """

    def __init__(self, dataTreeView, parent=None, size=(500, 400),
                 title='QVizPlotWidget', addTimeSlider=False,
                 addCoordinateSlider=False):
        super(QVizPlotWidget, self).__init__(parent)

        self.addTimeSlider = addTimeSlider
        self.addCoordinateSlider = addCoordinateSlider
        self.dataTreeView = dataTreeView

        # Set default background color: white
        pg.setConfigOption('background', 'w')
        # Set default foreground (text etc.) color: black
        pg.setConfigOption('foreground', 'k')

        # Enable antialiasing for prettier plots
        # Note: Considerably decreases performance
        pg.setConfigOptions(antialias=True)
        # pg.setConfigOptions(useOpenGL=True)

        # QVizPlotWidget settings
        # self.setObjectName("QVizPlotWidget")
        self.setObjectName(type(self).__name__)
        self.setWindowTitle(title)
        self.resize(size[0], size[1])

        # Set up the QWidget contents (pyqtgraph PlotWidget etc.)
        self.setContents()

        # Get list of available global colors (RGB)
        self.RGBlist = getRGBColorList()

        self.plotAxis = None

    def getType(self):
        return PlotTypes.SIMPLE_PLOT

    def isPlotAlongTimeAxis(self):
        if len(self.getViewBox().vizTreeNodesList) == 0:
            return None
        elif self.addTimeSlider:
            return False
        elif self.addCoordinateSlider:
            return True
        else:
            return None

    def setPlotAxis(self, plotAxis):
        self.plotAxis = plotAxis

    def getPlotAxis(self):
        return self.plotAxis

    def plot(self, vizTreeNode=None, x=None, y=None, title='', label='',
             xlabel='', ylabel='',
             pen=None, update=1, preview=0):
        """Add plot.
        
        Arguments:
            x      (1D array) : 1D array of X-axis values.
            y      (1D array) : 1D array of Y-axis values.
            title       (str) : Plot title.
            label       (str) : Label describing IMAS database (URI)
                                and path to signal/node in IDS database
                                structure.
            xlabel      (str) : Plot X-axis label.
            ylabel      (str) : Plot Y-axis label.
            pen        (QPen) : Plot line style.
        """
        # Set pen (line design). Color and style are chosen depending on the
        # number of already present plots

        if pen is None:
            pen=pg.mkPen('b', width=3, style=Qt.SolidLine)

        if self.RGBlist is not None:
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
            pen = pg.mkPen(color=self.RGBlist[next_RGB_ID], width=1,
                           style=style)

        # Plot and plot settings
        # - Add plot
        try:
            if vizTreeNode is not None and vizTreeNode.hasClosedOutline(
                    self.dataTreeView) and self.getPlotAxis() == 'COORDINATE1':
                x = np.append(x, [x[0]])
                y = np.append(y, [y[0]])
        except:
            logging.getLogger(vizTreeNode.dataTreeView.uri).error('closed attribute not found')

        plotDataItem = self.pgPlotWidget.plot(x, y, title=title, pen=pen, name=label)

        # Set only when adding the first plot. All additionally added plots
        # should correspond to the same xlabel, ylabel and grid and thus
        # should NOT change it.

        if len(self.getPlotList()) == 1:
            # - Set title
            # Note: dummy empty title, otherwise title updates in plot
            #       configuration will not work)
            self.pgPlotWidget.setTitle("")
            # - Set x-axis label
            self.pgPlotWidget.setLabel('left', ylabel, units='')
            # - Set y-axis label
            self.pgPlotWidget.setLabel('bottom', xlabel, units='')
            # - Set top and right axis default labels
            self.pgPlotWidget.setLabel('top', '', units='')
            self.pgPlotWidget.setLabel('right', '', units='')
            # - Enable grid
            self.pgPlotWidget.showGrid(x=True, y=True)

        self.pgPlotWidget.getViewBox().addVizTreeNode(vizTreeNode, preview=preview)
        self.pgPlotWidget.getViewBox().addVizTreeNodeDataItem(vizTreeNode, plotDataItem)

        self.updateSlider(vizTreeNode)

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

    def getPlotsData(self, plotIndex):
        """
        Returns a tuple (x,y) for the given plot index
        :param plotIndex: the index of a plot contained in this plot Widget
        :return: a tuple (x,y)
        """
        listDataItems = self.getPlotList()
        if listDataItems is not None and len(listDataItems) > plotIndex:
            return listDataItems[plotIndex].getData()
        return None

    def getGlobalTimeVectors(self):
        timeVectors = []
        for node in self.getViewBox().vizTreeNodesList:
            timeVectors.append(node.globalTime)
        return timeVectors

    def getCoordinate1Values(self):
        coordinate1Vectors = []
        for node in self.getViewBox().vizTreeNodesList:
            if node.is1DAndDynamic():
                coordinate1Vectors.append(
                    node.coordinateValues(coordinateNumber=1, dataTreeView=node.getDataTreeView()))
        return coordinate1Vectors

    def plotsHaveSameCoordinate1(self, vizTreeNode):
        if self.addCoordinateSlider:
            # Ignore 0D data, they have no coordinate1, so they remain
            # constant when sliding along coordinate1
            if vizTreeNode.is0DAndDynamic():
                return True
            coordinate1Vectors = self.getCoordinate1Values()
            if len(coordinate1Vectors) == 0:  # Happens when the first plot is added
                return True
                coordinate1Vectors.append(vizTreeNode.getCoordinate1Values())
            sameCoordinate1 = True
            for i in range(1, len(coordinate1Vectors)):
                if not np.array_equal(coordinate1Vectors[i - 1], coordinate1Vectors[i]):
                    sameCoordinate1 = False
                    break
            if not sameCoordinate1:
                logging.getLogger(vizTreeNode.dataTreeView.uri).error("Could not add plot for: " + vizTreeNode.getPath() +
                              ". Existing plot(s) has/have not the same coordinate1 values.")
                return False
            else:
                return True
        return True

    def setContents(self):
        """Setup QVizPlotWidget contents.
        """
        self.gridLayout = QGridLayout(self)
        self.gridLayout.setObjectName("gridLayout")

        # Set plot widget (use IMASViz custom plot context menu)
        self.viewBox = QVizCustomPlotContextMenu(qWidgetParent=self)
        self.pgPlotWidget = pg.PlotWidget(self, viewBox=self.viewBox)
        self.pgPlotWidget.setObjectName("plotWidget")

        # Set checkbox for toggling mouse
        checkBox = self.checkBox()

        # Set layout margin (left, top, right, bottom)
        self.gridLayout.setContentsMargins(10, 10, 10, 10)

        # Add widgets to layout
        self.gridLayout.addWidget(self.pgPlotWidget, 0, 0, 1, 10)
        self.gridLayout.addWidget(checkBox, 1, 0, 1, 1)

        # If the plottable array needs a slider for the X axis (time or coordinate)
        if self.addTimeSlider or self.addCoordinateSlider:
            # Add slider time or coordinate1D and its corresponding widgets
            self.sliderGroup = sliderGroup(self.addTimeSlider, parent=self,
                                           dataTreeView=self.dataTreeView)
            self.sliderGroupDict = self.sliderGroup.setupSlider()
            self.separatorLine = self.sliderGroupDict['separatorLine']
            self.slider = self.sliderGroupDict['slider']
            self.sliderLabel = self.sliderGroupDict['sliderLabel']
            self.sliderFieldLabel = self.sliderGroupDict['sliderFieldLabel']
            self.indexLabel = self.sliderGroupDict['indexLabel']
            self.sliderValueIndicator = self.sliderGroupDict['sliderValueIndicator']

            self.setSliderComponentsDisabled(False)

            self.gridLayout.addWidget(self.separatorLine, 2, 0, 1, 10)
            # Add time slider label
            self.gridLayout.addWidget(self.sliderLabel, 3, 0, 1, 10)
            # Add time slider
            self.gridLayout.addWidget(self.slider, 4, 0, 1, 10)
            # Add time slider index label and value indicator
            self.gridLayout.addWidget(self.indexLabel, 5, 0, 1, 1)
            self.gridLayout.addWidget(self.sliderValueIndicator, 5, 1, 1, 1)

            # Add time label
            self.gridLayout.addWidget(self.sliderFieldLabel, 6, 0, 1, 10)

        # Add a legend
        self.pgPlotWidget.getPlotItem().addLegend()

        # Connect custom UI elements
        QMetaObject.connectSlotsByName(self)

    def setSliderComponentsDisabled(self, flag):
        self.separatorLine.setDisabled(flag)
        self.slider.setDisabled(flag)
        self.sliderLabel.setDisabled(flag)
        self.sliderFieldLabel.setDisabled(flag)
        self.indexLabel.setDisabled(flag)
        self.sliderValueIndicator.setDisabled(flag)

    def menuBar(self):
        """Set menu bar.
        """
        menuBar = QMenuBar(self)
        exitMenu = menuBar.addMenu('File')
        exitAction = QAction('Exit', self.pgPlotWidget)
        exitAction.triggered.connect(self.close)
        exitMenu.addAction(exitAction)
        return menuBar

    def checkBox(self):
        """ Set and checkbox for toggling mouse plot interaction on/off.
        """

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

    def updateSlider(self, treeNode):
        logging.debug("updateSlider called")
        nodesList = self.pgPlotWidget.getViewBox().vizTreeNodesList
        if len(nodesList) == 1 and treeNode.embedded_in_time_dependent_aos() and treeNode.is1DAndDynamic():
            self.setSliderComponentsDisabled(False)

        if not (treeNode.is2DOrLarger()):
            if self.sliderGroup.slider.isEnabled():
                logging.debug("updateSlider::setSlider called")
                self.sliderGroup.setSlider()


class sliderGroup():
    """Set slider widget and its corresponding widgets (label,
    line edit etc.) to set and show time slice (change plot on
    slider change).
    """

    def __init__(self, isTimeSlider, dataTreeView, parent=None):
        self.parent = parent
        self.slider = QtWidgets.QSlider(Qt.Horizontal, self.parent)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        logging.debug("setting slider to 0")
        self.slider.setValue(0)
        # Set slider press variable as false
        self.sliderPress = False
        self.isTimeSlider = isTimeSlider  # otherwise it is a coordinate1D slider
        if dataTreeView is None:
            raise ValueError('inner sliderGroup class needs a not None '
                             'dataTreeView object to operate')
        self.dataTreeView = dataTreeView
        self.ignoreEvent = False

    def setupSlider(self):
        """Set and return the group of widgets.
        """

        self.separatorLine = self.setSeparatorLine()

        # Set labels
        if self.isTimeSlider:
            self.sliderLabel = self.setLabel(text='Time slider')
            # Set index label
            self.indexLabel = self.setLabel(text='Index Value: ')
        else:
            self.sliderLabel = self.setLabel(text='Coordinate1 slider')
            # Set index label
            self.indexLabel = self.setLabel(text='Index Value: ')

        self.sliderValueIndicator = self.setSliderValueIndicator()  # Set slider value indicator

        self.sliderFieldLabel = self.setSliderFieldLabel('')

        # Connect on signals
        self.slider.valueChanged.connect(self.onSliderChange)
        self.slider.sliderReleased.connect(self.onSliderRelease)
        self.slider.sliderPressed.connect(self.onSliderPress)

        # Set dictionary (for easier handling)
        self.timeSliderGroup = \
            {'separatorLine': self.separatorLine,
             'slider': self.slider,
             'sliderLabel': self.sliderLabel,
             'sliderFieldLabel': self.sliderFieldLabel,
             'indexLabel': self.indexLabel,
             'sliderValueIndicator': self.sliderValueIndicator}

        return self.timeSliderGroup

    def updateTimeValues(self, indexValue):

        logging.debug("updateTimeValues called")
        if not self.slider.isEnabled():
            logging.debug("updateTimeValues() returns without action")
            return

        if self.isTimeSlider:
            self.sliderFieldLabel = self.setLabel(text='Time:')
            nodesList = self.parent.pgPlotWidget.getViewBox().vizTreeNodesList
            i = 0
            for node in nodesList:
                label = node.setLabelForFigure(node.getDataTreeView().dataSource)
                if node.globalTime is None:
                    node.globalTime = \
                        node.getGlobalTimeForArraysInDynamicAOS()
                if node.globalTime is not None:
                    time = "{:.6f}".format(float(node.globalTime[indexValue]))
                    if i == 0:
                        self.parent.sliderFieldLabel.setText(
                            "Time [" + label + "]: " + str(time) + " [s]")
                    else:
                        self.parent.sliderFieldLabel.setText(self.parent.sliderFieldLabel.toPlainText() + "\n" +
                                                             "Time [" + label + "]: " + str(time) + " [s]")
                    i = i + 1
                else:
                    self.parent.sliderFieldLabel.setText("Undefined IDS global time.")
        else:
            nodesList = self.parent.pgPlotWidget.getViewBox().vizTreeNodesList
            i = 0
            self.sliderFieldLabel = self.setLabel(text='Coordinate1:')
            for node in nodesList:
                if node.is1DAndDynamic() and node.embedded_in_time_dependent_aos():

                    if node.getCoordinate(coordinateNumber=1) == "1..N" or \
                            node.getCoordinate(coordinateNumber=1) == "1...N":
                        s = "1..N"
                    else:
                        s = node.getIDSName() + "." + \
                            node.evaluateCoordinateVsTime(coordinateNumber=1)
                        s = QVizGlobalOperations.makePythonPath(s)
                    value = node.coordinateValues(coordinateNumber=1,
                                                  dataTreeView=self.dataTreeView)[indexValue]
                    if i == 0:
                        self.parent.sliderFieldLabel.setText(s + " (Value = " + str(value) + ")")
                    else:
                        self.parent.sliderFieldLabel.setText(self.parent.sliderFieldLabel.toPlainText() + "\n" +
                                                             s + " (Value = " + str(value) + ")")

    def setSlider(self):
        """Set slider.
        """
        from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal import QVizPlotSignal
        logging.debug("setSlider called")
        minValue = self.slider.minimum()
        maxValue = self.slider.maximum()

        if self.isTimeSlider:
            # Set index slider using coordinates as index (e.g. psi)
            # Set minimum and maximum value
            logging.debug("setSlider:: isTimeSlider=True")
            minValue = 0
            nodesList = self.parent.pgPlotWidget.getViewBox().vizTreeNodesList
            for node in nodesList:
                if node.embedded_in_time_dependent_aos() and \
                        node.is1DAndDynamic():
                    # - Get maximum value by getting the length of the array
                    newMaxValue = int(node.timeMaxValue()) - 1
                    if newMaxValue < self.slider.maximum() or maxValue == 0:
                        maxValue = newMaxValue
        else:
            logging.debug("setSlider:: isTimeSlider=False")
            # Set minimum and maximum value
            minValue = 0
            # - Get maximum value by getting the length of the array
            nodesList = self.parent.pgPlotWidget.getViewBox().vizTreeNodesList
            for node in nodesList:
                if node.embedded_in_time_dependent_aos() and \
                        node.is1DAndDynamic():
                    newMaxValue = node.coordinateLength(
                        coordinateNumber=1, dataTreeView=self.dataTreeView) - 1
                    if newMaxValue < self.slider.maximum() or maxValue == 0:
                        maxValue = newMaxValue

        # Set default value
        self.ignoreEvent = True
        self.slider.setMinimum(minValue)
        self.slider.setMaximum(maxValue)
        self.ignoreEvent = False

    def setSeparatorLine(self):
        """Set separator line.
        """

        separatorLine = QFrame(self.parent)
        separatorLine.setGeometry(QRect(0, 200, 500, 20))
        separatorLine.setFrameShape(QFrame.HLine)
        separatorLine.setFrameShadow(QFrame.Sunken)

        return separatorLine

    def setLabel(self, text=''):
        """Set label with given text.
        """

        sliderLabel = QLabel()
        sliderLabel.setText(text)
        sliderLabel.setAlignment(Qt.AlignLeft)
        sliderLabel.setWordWrap(True)
        sliderLabel.setFixedHeight(25)
        sliderLabel.setFont(GlobalFonts.TEXT_MEDIUM)

        return sliderLabel

    def setSliderFieldLabel(self, text=''):
        """Set label with given text.
        """

        # sliderFieldLabel = QLabel()
        sliderFieldLabel = QTextEdit()
        sliderFieldLabel.setText(text)
        sliderFieldLabel.setAlignment(Qt.AlignLeft)
        # sliderFieldLabel.setWordWrap(True)
        sliderFieldLabel.setFixedHeight(75)
        sliderFieldLabel.setFont(GlobalFonts.TEXT_MEDIUM)

        return sliderFieldLabel

    def setSliderValueIndicator(self):
        """Set widget displaying current slider value.
        """

        sliderValueIndicator = QtWidgets.QLineEdit()
        sliderValueIndicator.setReadOnly(True)
        sliderValueIndicator.setText(str(self.slider.value()))
        sliderValueIndicator.setMaximumWidth(50)

        return sliderValueIndicator

    def onSliderChange(self):
        """Action on slider change.
        """

        # Update slider value indicator value
        self.sliderValueIndicator.setText(str(self.slider.value()))

        # Don't plot when the slider is being dragged by mouse. Plot on slider
        # release. This is important to still plot on value change by
        # keyboard arrow keys
        if not self.sliderPress and not self.ignoreEvent:
            self.executePlot()

    def onSliderRelease(self):
        """Action on slider release.
        """

        # Set slider press status to false
        self.sliderPress = False
        # Plot
        self.executePlot()

    def onSliderPress(self):
        """Action on slider press.
        """
        # Set slider press status to true
        self.sliderPress = True

    def executePlot(self):
        """Replots according to slider values.
        """
        currentIndex = self.slider.value()

        currentFigureKey = self.parent.windowTitle()  # Get title of the current QVizPlotWidget
        i = 0
        api = self.dataTreeView.imas_viz_api
        for node in self.parent.pgPlotWidget.getViewBox().vizTreeNodesList:
            if self.isTimeSlider:           
                api.plotVsCoordinate1AtGivenTime(
                    dataTreeView=node.getDataTreeView(),
                    currentFigureKey=currentFigureKey,
                    treeNode=node,
                    update=1,
                    dataset_to_update=i)
            else:
                api.plotVsTimeAtGivenCoordinate1(
                    dataTreeView=node.getDataTreeView(),
                    coordinateIndex=currentIndex,
                    currentFigureKey=currentFigureKey,
                    treeNode=node,
                    update=1,
                    dataset_to_update=i)

            i += 1

        self.updateTimeValues(int(self.slider.value()))
        self.parent.pgPlotWidget.getViewBox().updateErrorBars()
        self.parent.pgPlotWidget.getViewBox().updateConfidenceBands()
