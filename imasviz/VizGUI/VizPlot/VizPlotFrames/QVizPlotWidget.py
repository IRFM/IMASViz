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
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
#*******************************************************************************

import pyqtgraph as pg
from PyQt5.QtCore import Qt, QMetaObject, QRect
from PyQt5.QtGui import QWidget, QGridLayout, QCheckBox, QMenuBar, QAction, \
                        QLabel, QFrame
import PyQt5.QtWidgets as QtWidgets
from imasviz.VizUtils.QVizGlobalValues import getRGBColorList, GlobalFonts
from imasviz.VizGUI.VizPlot.QVizCustomPlotContextMenu \
    import QVizCustomPlotContextMenu


class QVizPlotWidget(QWidget):
    """PlotWidget containing pyqtgraph PlotWidget. Used for main plotting
    feature.
    """

    def __init__(self, parent=None, size=(500, 400), title='QVizPlotWidget',
                 addTimeSlider=False, addCoordinateSlider=False, signalHandling=None):
        super(QVizPlotWidget, self).__init__(parent)

        self.addTimeSlider = addTimeSlider
        self.addCoordinateSlider = addCoordinateSlider
        self.signalHandling = signalHandling

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

        self.vizTreeNodesList = []


    def plot(self, vizTreeNode=None, x=None, y=None, title='', label='', xlabel='', ylabel='',
             pen=pg.mkPen('b', width=3, style=Qt.SolidLine), update=1):
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

        if vizTreeNode is not None:
            self.vizTreeNodesList.append(vizTreeNode)
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

        # Set checkbox for toggling mouse
        checkBox = self.checkBox()

        # Set layout margin (left, top, right, bottom)
        self.gridLayout.setContentsMargins(10, 10, 10, 10)

        # Add widgets to layout
        self.gridLayout.addWidget(self.pgPlotWidget, 0, 0, 1, 10)
        self.gridLayout.addWidget(checkBox, 1, 0, 1, 1)

        # If the plottable array needs a slider for the X axis (time or coordinate)
        if self.addTimeSlider or self.addCoordinateSlider:

            # Add slider time or corrdiante1D and its corresponding widgets
            self.sliderGroup = sliderGroup(self.addTimeSlider, parent=self, signalHandling=self.signalHandling)
            self.sliderGroupDict = self.sliderGroup.execute()
            self.separatorLine = self.sliderGroupDict['separatorLine']
            self.slider = self.sliderGroupDict['slider']
            self.sliderLabel = self.sliderGroupDict['sliderLabel']
            self.timeFieldLabel = self.sliderGroupDict['timeFieldLabel']
            self.indexLabel = self.sliderGroupDict['indexLabel']
            self.sliderValueIndicator = self.sliderGroupDict['sliderValueIndicator']

            self.gridLayout.addWidget(self.separatorLine, 2, 0, 1, 10)
            # Add time slider label
            self.gridLayout.addWidget(self.sliderLabel, 3, 0, 1, 10)
            # Add time slider
            self.gridLayout.addWidget(self.slider, 4, 0, 1, 10)
            # Add time slider index label and value indicator
            self.gridLayout.addWidget(self.indexLabel, 5, 0, 1, 1)
            self.gridLayout.addWidget(self.sliderValueIndicator, 5, 1, 1, 1)

            # Add time label
            self.gridLayout.addWidget(self.timeFieldLabel, 6, 0, 1, 10)

        #Add a legend
        self.pgPlotWidget.getPlotItem().addLegend()

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

class sliderGroup():
    """Set slider widget and its corresponding widgets (label,
    line edit etc.) to set and show time slice (change plot on
    slider change).
    """

    def __init__(self, isTimeSlider, signalHandling, parent=None):
        self.parent = parent
        # Set slider press variable as false
        self.sliderPress = False
        self.isTimeSlider = isTimeSlider #otherwise it is a coordinate1D slider
        if signalHandling is None:
            raise ValueError('inner sliderGroup class needs a not None signalHandling object to operate')
        self.signalHandling = signalHandling


    def execute(self):
        """Set and return the group of widgets.
        """

        self.separatorLine = self.setSeparatorLine()

        # Set labels
        if self.isTimeSlider:
            self.sliderLabel = self.setLabel(text='Time Slider')
        else:
            self.sliderLabel = self.setLabel(text='Coordinate1 Slider')

        # Set slider
        self.slider = self.setSlider()

        # Set index label
        self.indexLabel = self.setLabel(text='Index Value:')


        if self.isTimeSlider:
            self.timeFieldLabel = self.setLabel(text='Time:')
            if self.active_treeNode.globalTime is not None:
                self.timeFieldLabel.setText("Time: " + str(self.active_treeNode.globalTime[0]) + " [s]")
        else:
            self.timeFieldLabel = self.setLabel(text='')
        #    self.timeFieldLabel = self.setLabel(text='Coordinate1:')
        #    self.timeFieldLabel.setText("Coordinate1: " + str(self.active_treeNode.evaluateCoordinate1At(0))
        #                                + " [" + str(self.active_treeNode.getUnits()) + "]")


        # Set slider value indicator
        self.sliderValueIndicator = self.setSliderValueIndicator()

        # Connect on signals
        self.slider.valueChanged.connect(self.onSliderChange)
        self.slider.sliderReleased.connect(self.onSliderRelease)
        self.slider.sliderPressed.connect(self.onSliderPress)

        # Set dictionary (for easier handling)
        self.timeSliderGroup = \
            { 'separatorLine'        : self.separatorLine,
              'slider'               : self.slider,
              'sliderLabel'          : self.sliderLabel,
              'timeFieldLabel'       : self.timeFieldLabel,
              'indexLabel'           : self.indexLabel,
              'sliderValueIndicator' : self.sliderValueIndicator}

        return self.timeSliderGroup

    def setSlider(self):
        """Set slider.
        """

        # Get QVizTreeNode (QTreeWidgetItem) selected in the DTV
        self.active_treeNode = self.signalHandling.dataTreeView.selectedItem
        # self.currentIndex = self.active_treeNode.treeNodeExtraAttributes.itime_index
        self.currentIndex = self.active_treeNode.infoDict['i']

        if self.isTimeSlider:
            # Set index slider using coordinates as index (e.g. psi)
            # Set minimum and maximum value
            minValue = 0
            # - Get maximum value by getting the length of the array
            maxValue = int(self.active_treeNode.timeMaxValue()) - 1
        else:
            # Set index slider using time as index
            nodeData = self.active_treeNode.getInfoDict()
            # Set IDS source database
            ids = self.signalHandling.dataTreeView.dataSource.ids[self.active_treeNode.getOccurrence()]
            # Set minimum and maximum value
            minValue = 0
            # - Get maximum value by getting the length of the array
            maxValue = self.active_treeNode.coordinate1Length(nodeData, ids) - 1


        slider = QtWidgets.QSlider(Qt.Horizontal, self.parent)
        # Set default value
        slider.setMinimum(minValue)
        slider.setMaximum(maxValue)
        slider.setValue(int(self.currentIndex))

        return slider

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

    def setTimeFieldLabel(self, text=''):
        """Set label with given text.
        """

        timeFieldLabel = QLabel()
        timeFieldLabel.setText(text)
        timeFieldLabel.setAlignment(Qt.AlignLeft)
        timeFieldLabel.setWordWrap(True)
        timeFieldLabel.setFixedHeight(25)
        timeFieldLabel.setFont(GlobalFonts.TEXT_MEDIUM)

        return timeFieldLabel

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
        treeNode = self.signalHandling.dataTreeView.selectedItem

        if self.isTimeSlider:
            if treeNode.globalTime is not None:
                self.timeFieldLabel.setText("Time: " + str(treeNode.globalTime[self.slider.value()]) + " [s]")
            else:
                self.timeFieldLabel.setText("Undefined IDS global time.")

        # Don't plot when the slider is being dragged by mouse. Plot on slider
        # release. This is important to still plot on value change by
        # keyboard arrow keys
        if self.sliderPress == False:
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
        """Execute replotting using different data time slice.
        """
        self.currentIndex = self.slider.value()

        #Get title of the current QVizPlotWidget
        currentFigureKey = self.parent.windowTitle()

        i = 0
        for node in self.parent.vizTreeNodesList:

            self.active_treeNode = node

            if self.isTimeSlider:

                self.signalHandling.plotSelectedSignalVsCoordAtTimeIndex(
                    time_index=self.currentIndex,
                    currentFigureKey=currentFigureKey,
                    treeNode=self.active_treeNode, update=1, dataset_to_update=i)
            else:
                self.signalHandling.plotSelectedSignalVsTimeAtCoordinate1D(
                    index=self.currentIndex,
                    currentFigureKey=currentFigureKey,
                    treeNode=self.active_treeNode, update=1, dataset_to_update=i)

            i += 1