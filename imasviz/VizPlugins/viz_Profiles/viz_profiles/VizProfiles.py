#  Name   : VizProfiles
#
#           Main VizProfiles plugin code source.
#
#  Author :
#         Ludovic Fleury
#  E-mail :
#         ludovic.fleury@cea.fr
#
# ****************************************************
#     Copyright(c) 2022- L. Fleury

# Standard library imports
import logging
import sys
from functools import partial

# Third party imports
import numpy as np
from PySide6.QtWidgets import (QWidget, QTabWidget, QApplication, QMainWindow,
                             QSlider, QLabel, QSpinBox, QCheckBox, QPushButton,
                             QLineEdit, QHBoxLayout, QVBoxLayout, QMenuBar,
                             QFrame, QScrollArea, QProgressBar, QLayout, QInputDialog,
                             QSizePolicy)
from PySide6.QtGui import QAction
from PySide6.QtGui import QScreen, QGuiApplication
from PySide6.QtCore import Qt, QSize, Signal, Slot, QThread, QObject
from PySide6.QtGui import QDoubleValidator

from imasviz.VizUtils import QVizGlobalOperations, QVizGlobalValues
from imasviz.Viz_API import Viz_API
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizPlugins.viz_Profiles.viz_profiles.QVizTablePlotView import QVizTablePlotView

from imasviz.VizPlugins.viz_Profiles.viz_profiles.tabQt import QVizTab


class VizProfiles(QMainWindow):
    updateProgressBar = Signal()

    def __init__(self, viz_api, IDS_parameters, selectedTreeNode,
                 dataTreeView, requests_list, ids_name, plotAxis):
        """
        Arguments:
            IDS_parameters (Dictionary) : Dictionary containing IDS parameters
                                          (shot, run, user, database)
            ids            (obj)        : IDS object
        """
        super(VizProfiles, self).__init__()

        # Set log parser
        self.addNewTabsButton = None
        self.signals_last_index = []
        self.total_tabs = []
        self.total_undisplayed_tabs = []
        self.tabs_index = {}  # map tab name to tab index
        self.total_displayed_plots = 0
        self.n_curves_per_page = 100

        self.tabWidget = None
        self.mainWidget = None
        self.tabs = None
        self.plottable_signals = None
        self.log = logging.getLogger(__name__)
        self.log.addHandler(logging.StreamHandler())

        # Get app
        self.app = QApplication.instance()
        if self.app is None:
            # if it does not exist then a QApplication is created
            self.app = QApplication([])

        title = "'" + ids_name + "'" + " IDS (0D/1D data visualization"
        if plotAxis == 'COORDINATE1':
            title += " along coordinate1 axis)"
        elif plotAxis == 'TIME':
            title += " along time axis)"
        else:
            raise ValueError("Unexpected plot Axis")

        figureKey = viz_api.GetNextKeyForProfilesPlotView()

        self.setWindowTitle(title + ' [' + str(figureKey) + ']')
        self.selectedTreeNode = selectedTreeNode

        self.IDS_parameters = IDS_parameters
        self.dataTreeView = dataTreeView
        self.imas_viz_api = viz_api

        # Set initial time slice
        self.time_index = 0

        key = dataTreeView.dataSource.dataKey2(figureKey)
        tup = (dataTreeView.dataSource.uri, None)
        viz_api.AddNodeToFigure(figureKey, key, tup)
        viz_api.figureframes[figureKey] = self

        self.pb = ProgressBar()
        self.pb.show()

        # Set user interface of the main window
        self.plotAxis = plotAxis
        self.ids_related = ids_name
        self.dataSource = dataTreeView.dataSource
        self.buildUI_in_separate_thread(requests_list)

    def getLogger(self):
        return self.log

    def closeProgressBar(self):
        self.pb.close()

    def setTabs(self):
        no_result = True
        for key in self.worker.results_map:
            if len(self.worker.results_map[key]) != 0:
                no_result = False
                break
        if no_result:
            self.close()
            logging.getLogger(self.dataSource.uri).error("No data available for plotting.")
            return

        self.mainWidget = QWidget(parent=self)
        self.mainWidget.setLayout(QVBoxLayout())
        self.tabWidget = QTabWidget(parent=self)

        self.tabWidget.currentChanged.connect(self.disableOrEnabledAddNewTabsIfRequired)
        success = self.addTabs()
        if success == 0:
            logging.getLogger(self.dataSource.uri).error("An error has occurred.")
            return
        self.setUI()
        self.disableOrEnabledAddNewTabsIfRequired()

    def addTabs(self, nb_tabs_count=1):

        self.total_undisplayed_tabs = {}
        self.total_tabs = {}
        self.signals_last_index = {}
        success = 0
        for key in self.worker.slices_aos_names:
            self.total_undisplayed_tabs[key] = []
            self.total_tabs[key] = []
            self.signals_last_index[key] = []
            for filter_index in range(len(self.worker.results_map[key])):
                self.total_undisplayed_tabs[key].append(0)
                self.total_tabs[key].append(0)
                self.signals_last_index[key].append(0)

        w = GlobalPlotWidget(plotAxis=self.plotAxis)
        for key in self.worker.slices_aos_names:
            tab_names_per_key = self.worker.tab_names_map[key]
            results_per_key = self.worker.results_map[key]
            static_aos_index = self.worker.static_aos_index_map[key]
            for filter_index in range(len(results_per_key)):
                remaining_page = 0
                plottable_signals = results_per_key[filter_index]
                if len(plottable_signals) == 0:
                    continue
                if (len(plottable_signals) % self.n_curves_per_page) != 0:
                    remaining_page = 1
                n_tabs = int((len(plottable_signals) / self.n_curves_per_page)) + remaining_page
                self.total_tabs[key][filter_index] = n_tabs
                self.total_undisplayed_tabs[key][filter_index] = n_tabs - nb_tabs_count
                #print("-->key=", key)
                #print("-->filter_index=", filter_index)
                #print("-->self.total_undisplayed_tabs[filter_index]=", self.total_undisplayed_tabs[filter_index])
                for i in range(nb_tabs_count):
                    start_index = i * self.n_curves_per_page + self.signals_last_index[key][filter_index]
                    last_index = start_index + self.n_curves_per_page
                    self.signals_last_index[key][filter_index] = last_index
                    n_curves = len(plottable_signals[start_index:last_index])
                    tab_name = None
                    if n_tabs == 1:
                        tab_name = tab_names_per_key[filter_index]
                    else:
                        tab_name = tab_names_per_key[filter_index] + ' (' + str(i + 1) + '/' + str(n_tabs) + ')'
                    tab = QVizTab(parent=self, tab_page_name=tab_name, filter_index=filter_index, slices_aos_name=key)
                    # tab.setTabUI(self.tabWidget.currentIndex() + 1, self.tabWidget
                    tab.setTabUI(self.tabWidget.count(), self.tabWidget)
                    self.tabs_index[tab_name] = tab.tab_index
                    multiPlots = QVizTablePlotView(self.imas_viz_api, self.dataTreeView,
                                                   n_curves, key, static_aos_index)
                    tab.buildPlots(multiPlots=multiPlots,
                                   signals=plottable_signals[start_index:last_index],
                                   plotWidget=w,
                                   plotAxis=self.plotAxis)
                    success = 1
        return success

    def disableOrEnabledAddNewTabsIfRequired(self):
        if self.addNewTabsButton is None or self.askForAddingNewTabsButton is None:
            return
        filter_index = self.getCurrentTab().filter_index
        slices_aos_name = self.getCurrentTab().slices_aos_name
        if self.total_undisplayed_tabs[slices_aos_name][filter_index] == 0:
            self.addNewTabsButton.setEnabled(False)
            self.askForAddingNewTabsButton.setEnabled(False)
        else:
            self.addNewTabsButton.setEnabled(True)
            self.askForAddingNewTabsButton.setEnabled(True)

    def askForAddingNewTabs(self):
        user_input = QInputDialog()
        filter_index = self.getCurrentTab().filter_index
        slices_aos_name = self.getCurrentTab().slices_aos_name
        nb_tabs_to_add_max = self.total_undisplayed_tabs[slices_aos_name][filter_index]
        nb_tabs_to_add, ok = user_input.getInt(None, "Number of tab(s) to add:", "Number of tabs:",
                                               value=nb_tabs_to_add_max, minValue=1, maxValue=nb_tabs_to_add_max)
        if not ok:
            logging.getLogger(self.dataSource.uri).error('Bad input from user.')
            return
        for i in range(nb_tabs_to_add):
            self.addNewTab()

    def addNewTab(self):
        nb_tabs_count = 1
        w = GlobalPlotWidget(plotAxis=self.plotAxis)
        key = self.getCurrentTab().slices_aos_name
        results = self.worker.results_map[key]
        tab_names = self.worker.tab_names_map[key]
        static_aos_index = self.worker.static_aos_index_map[key]

        filter_index = self.getCurrentTab().filter_index

        n_tabs = self.total_tabs[key][filter_index]
        n_tabs_displayed = n_tabs - self.total_undisplayed_tabs[key][filter_index]
        if n_tabs_displayed == n_tabs:
            return

        plottable_signals = results[filter_index]
        self.total_undisplayed_tabs[key][filter_index] -= nb_tabs_count
        for i in range(nb_tabs_count):
            start_index = i * self.n_curves_per_page + self.signals_last_index[key][filter_index]
            last_index = start_index + self.n_curves_per_page
            self.signals_last_index[key][filter_index] = last_index
            j = i + n_tabs_displayed + 1
            n_curves = len(plottable_signals[start_index:last_index])
            tab_name = tab_names[filter_index] + ' (' + str(j) + '/' + str(n_tabs) + ')'
            tab = QVizTab(parent=self, tab_page_name=tab_name, filter_index=filter_index, slices_aos_name=key)
            # search the latest tab of this group
            index = self.tabWidget.currentIndex() + 1
            if n_tabs_displayed > 1:
                latest_tab_name = tab_names[filter_index] + ' (' + str(n_tabs_displayed) + '/' \
                                  + str(n_tabs) + ')'
                # print("latest_tab_name=", latest_tab_name)
                index = self.tabs_index[latest_tab_name] + 1
            tab.setTabUI(index, self.tabWidget)
            self.tabs_index[tab_name] = tab.tab_index
            multiPlots = QVizTablePlotView(self.imas_viz_api, self.dataTreeView, n_curves, key, static_aos_index)
            tab.buildPlots(multiPlots=multiPlots,
                           signals=plottable_signals[start_index:last_index],
                           plotWidget=w,
                           plotAxis=self.plotAxis)

        self.disableOrEnabledAddNewTabsIfRequired()

    def showWindow(self):
        if len(self.worker.results_map) != 0:
            self.show()
        else:
            logging.getLogger(self.dataTreeView.uri).warning("No data found.")

    def buildUI_in_separate_thread(self, requests_list):
        # Create a QThread object
        self.thread = QThread()
        # Create a worker object
        self.worker = Worker(requests_list, self.imas_viz_api, self.dataTreeView, self.plotAxis, self.ids_related)
        # Move worker to the thread
        self.worker.moveToThread(self.thread)
        # Connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self.closeProgressBar)
        self.worker.call.connect(self.setTabs)
        self.worker.finished.connect(self.showWindow)
        self.worker.progressBar.connect(self.pb.updateProgressBar)
        self.worker.maxProgressBar.connect(self.pb.setMaxProgressBar)
        self.worker.titleProgressBar.connect(self.pb.setTitleProgressBar)
        # Start the thread
        self.thread.start()

    def setUI(self):
        """Set user interface of the main window
        """
        # Add menu bar
        self.addMenuBar()
        # Position widgets
        self.mainWidget.layout().addWidget(self.tabWidget)

        if self.plotAxis == 'COORDINATE1':
            # Set time slider
            self.label_slider_tmin = QLabel("t<sub>min</sub>", parent=self)
            self.label_slider_tmax = QLabel("t<sub>max</sub>", parent=self)
            self.slider_time = self.setTimeSlider()

            # Set time slice index label
            self.time_indexLabel = QLabel("Time slice index: ")
            self.time_indexLabel.setFixedWidth(120)
            # Set spinbox
            self.spinBox_timeIndex = self.setTimeSpinBox()

            # Set time value label
            self.label_timeValue = QLabel("Time value: ")
            self.label_timeValue.setFixedWidth(120)
            # Set time value line edit
            self.lineEdit_timeValue = self.setTimeValueLineEdit()

            # Set buttons
            self.plotButton = QPushButton("Plot", parent=self)
            self.plotButton.setFixedWidth(120)
            self.plotButton.clicked.connect(self.onPlotClicked)

            # Set check box
            self.checkBox_instant_label = QLabel("Refresh plot(s) automatically on time "
                                                 "index change: ")
            self.checkBox_instant_label.setFixedWidth(350)
            self.checkBox_instant = QCheckBox(parent=self)
            self.checkBox_instant.setChecked(False)

            whbox1 = QWidget(self)
            whbox1.setLayout(QHBoxLayout())
            whbox1.layout().setContentsMargins(0, 0, 0, 0)
            whbox1.layout().addWidget(self.label_slider_tmin)
            whbox1.layout().addWidget(self.slider_time)
            whbox1.layout().addWidget(self.label_slider_tmax)
            self.mainWidget.layout().addWidget(whbox1)

            whbox2 = QWidget(self)
            whbox2.setLayout(QHBoxLayout())
            whbox2.layout().setContentsMargins(0, 0, 0, 0)
            whbox2.layout().addWidget(self.time_indexLabel)
            whbox2.layout().addWidget(self.spinBox_timeIndex)
            whbox2.layout().addStretch()
            self.mainWidget.layout().addWidget(whbox2)

            whbox3 = QWidget(self)
            whbox3.setLayout(QHBoxLayout())
            whbox3.layout().setContentsMargins(0, 0, 0, 0)
            whbox3.layout().addWidget(self.label_timeValue)
            whbox3.layout().addWidget(self.lineEdit_timeValue)
            whbox3.layout().addStretch()
            self.mainWidget.layout().addWidget(whbox3)

            whbox4 = QWidget(self)
            whbox4.setLayout(QHBoxLayout())
            whbox4.layout().setContentsMargins(0, 0, 0, 0)
            whbox4.layout().addWidget(self.plotButton)
            whbox4.layout().addWidget(self.checkBox_instant_label)
            whbox4.layout().addWidget(self.checkBox_instant)
            whbox4.layout().addStretch()
            self.mainWidget.layout().addWidget(whbox4)

        self.addNewTabsButton = QPushButton("Add 1 tab of plots", parent=self)
        self.addNewTabsButton.setFixedWidth(200)
        self.addNewTabsButton.clicked.connect(self.addNewTab)

        self.askForAddingNewTabsButton = QPushButton("Add more tabs", parent=self)
        self.askForAddingNewTabsButton.setFixedWidth(200)
        self.askForAddingNewTabsButton.clicked.connect(self.askForAddingNewTabs)

        whbox5 = QWidget(self)
        whbox5.setLayout(QHBoxLayout())
        whbox5.layout().setContentsMargins(0, 0, 0, 0)
        whbox5.layout().addWidget(self.addNewTabsButton)
        whbox5.layout().addWidget(self.askForAddingNewTabsButton)
        whbox5.layout().addStretch()
        self.mainWidget.layout().addWidget(whbox5)

        self.setCentralWidget(self.mainWidget)

        # set status bar
        self.setStatusBar()
        # self.setStatusBarText_1(text="OK")

        # Set initial window size
        dw, dh = self.app.primaryScreen().size().toTuple()

        height = dh * 0.9
        width = dw * 0.7

        self.resize(height, width)

        # self.resize(int(self.width), int(self.height))
        # Move window to the center of the screen
        # self.setFixedWidth(400)
        # self.setFixedHeight(600)

        qtRectangle = self.frameGeometry()
        centerPoint = QScreen().availableGeometry().center()

        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())

        # On tab change update the tab-containing plots
        self.tabWidget.currentChanged.connect(self.updatePlotOfCurrentTab)

        # self.spinBox_timeIndex.valueChanged.connect(self.onTimeIndexChanged)

    # def sizeHint(self):
    #     """Set initial window size.
    #     Note: Qt calls this routine automatically by default when creating this
    #           window/widget.
    #     """
    #     return QSize(int(self.width), int(self.height))

    def addMenuBar(self):
        """Create and configure the menu bar.
        """
        # Main menu bar
        # menuBar = QMenuBar(self)
        # options = menuBar.addMenu('Options')
        # Set menu bar
        # self.setMenuBar(menuBar)

    def toggleDebugMode(self, state):
        """ Toggle debug mode.
        """
        if state:
            self.log.setLevel(logging.DEBUG)
        else:
            self.log.setLevel(logging.INFO)

    def getTimeIndex(self):
        return self.time_index

    def getTimeValueForTimeIndex(self, time_index):
        """ Get time value for given time index.
        """
        slices_aos_name = self.getCurrentTab().slices_aos_name
        exec(self.ids_related + " = self.dataSource.get(self.ids_related, self.IDS_parameters['occurrence'])")
        time_slices_count = len(eval(self.ids_related + "." + slices_aos_name))

        if time_slices_count == 0:
            message = "No time slice found for " + self.ids_related + "."
            logging.getLogger(self.dataSource.uri).error(message)
            self.close()
            raise ValueError(message)

        if time_index > time_slices_count - 1:
            message = "Time index=" + str(time_index) + " exceeds the number of slices."
            raise ValueError(message)

        time_value = eval(self.ids_related + "." + slices_aos_name + "[time_index].time")

        if time_value == -9e+40:
            time_value = eval(self.ids_related + ".time[time_index]")
        return time_value

    def getCurrentTab(self):
        """Get currently selected tab if type QVizTab
        """
        if self.tabWidget.currentWidget() is not None:
            return self.tabWidget.currentWidget().parent

    def getTablePlotView(self):
        """Get a QVizTablePlotView instance attached to the current QVizTab tab
        """
        return self.getCurrentTab().layout.itemAt(0).widget()

    def updatePlotOfCurrentTab(self):
        """Update plot of current tab.
        """
        qvizTab = self.getCurrentTab()
        w = GlobalPlotWidget(plotAxis=self.plotAxis)
        updated_signals = self.imas_viz_api.updateAllPlottable_0D_1D_Signals(qvizTab.signals, self.time_index,
                                                                             plotWidget=w)
        self.getTablePlotView().updatePlot(updated_signals)

    def setTimeSlider(self):
        # Set time slider
        slider_time = QSlider(Qt.Horizontal, self)
        slider_time.setValue(0)
        slider_time.setMinimum(0)
        exec(self.ids_related + " = self.dataSource.get(self.ids_related, self.IDS_parameters['occurrence'])")
        time_slices_count = len(eval(self.ids_related + ".time"))
        slider_time.setMaximum(time_slices_count - 1)
        # self.slider_time.adjustSize()
        # self.slider_time.setMinimumWidth(600)
        # Set slider event handling
        self.updateTimeSliderTminTmaxLabel()
        slider_time.sliderReleased.connect(self.onSliderChange)
        slider_time.valueChanged.connect(self.onSliderChange)
        return slider_time

    def updateTimeSliderTminTmaxLabel(self):
        """ Update tmin and tmax label/values.
        """
        if self.getCurrentTab() is None:
            return
        slices_aos_name = self.getCurrentTab().slices_aos_name
        exec(self.ids_related + " = self.dataSource.get(self.ids_related, self.IDS_parameters['occurrence'])")
        ntimevalues = eval("len(" + self.ids_related + "." + slices_aos_name + ")")
        tmin = -9e+40
        tmax = -9e+40

        if ntimevalues > 0:
            tmin = eval(self.ids_related + "." + slices_aos_name + "[0].time")
            tmax = eval(self.ids_related + "." + slices_aos_name + "[-1].time")

        n = eval("len(" + self.ids_related + ".time)")
        # Check if empty time values were read
        # (-9e+40 is default value == empty)
        if n > 0 and (tmin == -9e+40 or tmax == -9e+40):
            tmin = eval(self.ids_related + ".time[0]")
            tmax = eval(self.ids_related + ".time[-1]")

        self.label_slider_tmin.setText(f"n<sub>t</sub> = {ntimevalues}; "
                                       f"t<sub>min</sub> = {tmin:.2f}")
        self.label_slider_tmax.setText(f"t<sub>max</sub> = {tmax:.2f}")

    def setTimeSpinBox(self):
        spinBox_timeIndex = QSpinBox(parent=self)
        spinBox_timeIndex.setValue(0)
        spinBox_timeIndex.setMinimum(0)
        exec(self.ids_related + " = self.dataSource.get(self.ids_related, self.IDS_parameters['occurrence'])")
        maxIndex = eval("len(" + self.ids_related + ".time) - 1")
        spinBox_timeIndex.setMaximum(maxIndex)
        spinBox_timeIndex.setFixedWidth(65)
        spinBox_timeIndex.valueChanged.connect(self.onSpinBoxChange)
        # spinBox_timeIndex.editingFinished.connect(partial(
        #    self.updatePlotOfCurrentTab, time_index=self.time_index))
        return spinBox_timeIndex

    @Slot()
    def onSpinBoxChange(self, event=None):
        # Update global time_index value (auto spinbox value update)
        # print('onSpinBoxChange')
        self.time_index = self.spinBox_timeIndex.value()
        # print('--->self.time_index =', self.time_index)
        self.lineEdit_timeValue.setText(
            f"{self.getTimeValueForTimeIndex(time_index=self.time_index)}")
        if self.time_index != self.slider_time.value():
            self.slider_time.setValue(self.time_index)
        if self.checkBox_instant.isChecked():
            # Update plots
            self.updatePlotOfCurrentTab()

    def onSliderChange(self, event=None):
        """ PyQt slot: on change of the slider value.
        """
        self.time_index = self.slider_time.value()
        self.lineEdit_timeValue.setText(
            f"{self.getTimeValueForTimeIndex(time_index=self.time_index)}")
        if self.time_index != self.spinBox_timeIndex.value():
            self.spinBox_timeIndex.setValue(self.time_index)

    def onPlotClicked(self, event=None):
        self.updatePlotOfCurrentTab()

    def setTimeValueLineEdit(self):
        lineEdit_timeValue = QLineEdit("", parent=self)
        self.onlyDouble = QDoubleValidator()
        lineEdit_timeValue.setValidator(self.onlyDouble)
        lineEdit_timeValue.setFixedWidth(200)
        lineEdit_timeValue.setText(
            f"{self.getTimeValueForTimeIndex(time_index=0)}")
        lineEdit_timeValue.editingFinished.connect(
            self.onTimeValueLineEditEditingFinished)

        return lineEdit_timeValue

    @Slot()
    def onTimeValueLineEditEditingFinished(self, event=None):
        """ When finished editing the time value line edit (pressing enter etc.)
        find the closest value (and its array index -> time index) based on the
        inserted value.
        """

        # A simple routine to find the nearest value (and its index) based on
        # given value
        def find_nearest(array, value):
            array = np.asarray(array)
            idx = (np.abs(array - value)).argmin()
            return array[idx], idx

        exec(self.ids_related + " = self.dataSource.get(self.ids_related, self.IDS_parameters['occurrence'])")
        value = float(self.lineEdit_timeValue.text())
        slices_aos_name = self.getCurrentTab().slices_aos_name
        time_profiles0 = eval(self.ids_related + "." + slices_aos_name + "[0].time")
        time = eval(self.ids_related + ".time")
        ntimevalues = len(eval(self.ids_related + "." + slices_aos_name))
        time_values = None

        if time_profiles0 == -9e+40:
            time_values = time
        else:
            time_values = [0] * ntimevalues
            for i in range(len(time_values)):
                time_values[i] = eval(self.ids_related + "." +
                                      slices_aos_name + "[i].time")

        closest_value, index = find_nearest(time_values, value)
        self.spinBox_timeIndex.setValue(index)
        if self.checkBox_instant.isChecked():
            self.updatePlotOfCurrentTab()

    def setStatusBar(self):
        self.statusBar_text_1 = QLabel("")
        self.statusBar_text_1.setStyleSheet('border: 0; color:  green;')
        self.setStatusBarTexts()
        VertLine = QFrame(self)
        # VertLine.setFrameShape(VertLine.VLine | VertLine.Sunken)
        self.statusBar().addPermanentWidget(VertLine)
        self.statusBar().addPermanentWidget(self.statusBar_text_1)
        self.statusBar().show()

    def setStatusBarTexts(self, text=" "):

        self.statusBar().showMessage(f"URI={self.IDS_parameters['uri']}; " 
                                     f"OCCURRENCE={self.IDS_parameters['occurrence']} ")
        self.statusBar_text_1.setText(text)


class GlobalPlotWidget():

    def __init__(self, plotAxis):
        super(GlobalPlotWidget, self).__init__()
        self.addTimeSlider = True
        self.addCoordinateSlider = False
        self.plotAxis = plotAxis
        self.sliderGroup = None

    def getPlotAxis(self):
        return self.plotAxis


class Request():
    def __init__(self, ids_related, tab_names, list_of_filters, slices_aos_name, plotAxis, static_aos_index=-1):
        super(Request, self).__init__()
        self.ids_related = ids_related
        self.list_of_filters = list_of_filters
        self.tab_names = tab_names
        self.slices_aos_name = slices_aos_name
        self.plotAxis = plotAxis
        self.static_aos_index = static_aos_index


# worker class
class Worker(QObject):
    finished = Signal()
    call = Signal()
    progressBar = Signal(int)
    maxProgressBar = Signal(int)
    titleProgressBar = Signal()

    def __init__(self, requests_list, imas_viz_api, dataTreeView, plotAxis, ids_name):
        super().__init__()
        self.results_map = {}
        self.tab_names_map = {}
        self.slices_aos_names = []
        self.static_aos_index_map = {}
        self.requests_list = requests_list
        self.imas_viz_api = imas_viz_api
        self.dataTreeView = dataTreeView
        self.ids_name = ids_name
        self.plotAxis = plotAxis

    def run(self):
        """Long-running task."""
        self.buildPlottableSignals()
        self.call.emit()
        self.finished.emit()

    def buildPlottableSignals(self):
        j = 0
        for request in self.requests_list:
            jmax = len(self.requests_list) * len(request.list_of_filters)
            self.maxProgressBar.emit(jmax)
            results = []
            for str_filter in request.list_of_filters:
                j = j + 1
                self.progressBar.emit(j)
                nodes_id, dtv_nodes = self.imas_viz_api.getAll_0D_1D_Nodes(
                    self.dataTreeView.IDSRoots[self.ids_name],
                    errorBars=False,
                    str_filter=str_filter,
                    plotAxis=self.plotAxis)
                w = GlobalPlotWidget(plotAxis=self.plotAxis)
                plottable_signals = []
                if len(dtv_nodes) != 0:
                    plottable_signals = self.imas_viz_api.getAllPlottable_0D_1D_Signals(dtv_nodes, self.dataTreeView,
                                                                                    w)  # return tuple (node, signal)
                results.append(plottable_signals)

            self.slices_aos_names.append(request.slices_aos_name)
            self.static_aos_index_map[request.slices_aos_name] = request.static_aos_index
            self.results_map[request.slices_aos_name] = results
            self.tab_names_map[request.slices_aos_name] = request.tab_names


class ProgressBar(QWidget):
    def __init__(self):
        super(ProgressBar, self).__init__()
        self.thread = None
        self.setWindowTitle('Preparing plots...')
        self.pbar = QProgressBar(self)
        self.pbar.setValue(0)
        self.resize(300, 100)
        self.vbox = QVBoxLayout()
        self.vbox.addWidget(self.pbar)
        self.setLayout(self.vbox)
        self.pbar.setMinimum(0)
        self.pbar.setMaximum(100)
        self.pbar.setValue(0)
        qtRectangle = self.frameGeometry()
        centerPoint = QScreen().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())
        # self.show()

    def updateProgressBar(self, i):
        # print("updating progress bar to :" + str(i))
        self.pbar.setValue(i)

    def setMaxProgressBar(self, i):
        self.pbar.setMaximum(i)

    def setTitleProgressBar(self):
        self.pbar.setWindowTitle("Plotting...")


# Main used only for testing purposes (No GUI)
if __name__ == "__main__":

    from imasviz.VizPlugins.viz_Profiles.VizProfiles_plugin import VizProfiles_plugin

    # Set object managing the PyQt GUI application's control flow and main
    # settings
    app = QApplication(sys.argv)

    # Check if necessary system variables are set
    QVizGlobalOperations.checkEnvSettings()

    # Set Application Program Interface
    api = Viz_API()

    # Set data source retriever/factory
    dataSourceFactory = QVizDataSourceFactory()

    # shotNumber = 134173
    # runNumber = 106
    # userName = 'public'
    # database = 'ITER'
    # occurrence = 0

    # shotNumber = 130012
    # runNumber = 4
    # userName = 'public'
    # database = 'ITER_SCENARIOS'
    # occurrence = 0

    # shotNumber = 134174
    # runNumber = 117
    # userName = 'hoeneno'
    # database = 'ITER_SCENARIOS'
    # occurrence = 0

    # shotNumber = 54178
    # runNumber = 0
    # userName = 'fleuryl'
    # database = 'west'
    # occurrence = 0

    uri = ''

    IDS_parameters = {"uri": uri}

    dataSource = dataSourceFactory.create(
        uri=uri)

    # Build the data tree view frame
    f = api.CreateDataTree(dataSource)

    pluginEntry = None
    ids_name = None

    if len(sys.argv) > 1:
        ids_name = sys.argv[1]
        pluginEntry = int(sys.argv[2])
    else:
        ids_name = "core_profiles"
        pluginEntry = 0

    api.LoadIDSData(f, ids_name, occurrence)
    f.show()

    vizProfiles_plugin = VizProfiles_plugin()
    vizProfiles_plugin.dataTreeView = f.dataTreeView
    vizProfiles_plugin.selectedTreeNode = f.dataTreeView.IDSRoots[ids_name]
    vizProfiles_plugin.execute(api, pluginEntry=pluginEntry)

    sys.exit(app.exec_())
