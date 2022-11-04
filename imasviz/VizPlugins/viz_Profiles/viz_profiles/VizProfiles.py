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
import inspect
import time
from functools import partial

# Third party imports
import numpy as np
import imas
from PyQt5.QtWidgets import (QWidget, QTabWidget, QApplication, QMainWindow,
                             QSlider, QLabel, QSpinBox, QCheckBox, QPushButton,
                             QLineEdit, QHBoxLayout, QVBoxLayout, QMenuBar,
                             QAction, QFrame, QScrollArea, QProgressBar)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, pyqtSlot, QThread
from PyQt5.QtGui import QDoubleValidator

from imasviz.VizUtils import QVizGlobalOperations, QVizGlobalValues
from imasviz.Viz_API import Viz_API
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizPlugins.viz_Profiles.viz_profiles.QVizTablePlotViewForPlugin import QVizTablePlotViewForPlugin

from imasviz.VizPlugins.viz_Profiles.viz_profiles.tabQt import QVizTab


class VizProfiles(QMainWindow):

    def __init__(self, viz_api, IDS_parameters, data_entry, dataTreeView, request):
        """
        Arguments:
            IDS_parameters (Dictionary) : Dictionary containing IDS parameters
                                          (shot, run, user, database)
            ids            (obj)        : IDS object
        """
        super(QMainWindow, self).__init__()

        # Set log parser
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
        title = "'" + request.ids_related + "'" + " IDS (0D/1D data visualization"
        if request.strategy == 'COORDINATE1':
            title += " along coordinate1 axis)"
        elif request.strategy == 'TIME':
            title += " along time axis)"
        else:
            raise ValueError("Unexpected strategy")

        figureKey = viz_api.GetNextKeyForProfilesPlotView()

        self.setWindowTitle(title + ' [' + str(figureKey) + ']')
        self.data_entry = data_entry
        self.ids_related = request.ids_related
        self.IDS_parameters = IDS_parameters
        self.dataTreeView = dataTreeView

        self.strategy = request.strategy
        self.request = request

        self.imas_viz_api = viz_api

        # Set initial time slice
        self.time_index = 0

        key = dataTreeView.dataSource.dataKey2(figureKey)
        tup = (dataTreeView.dataSource.shotNumber, None)
        viz_api.AddNodeToFigure(figureKey, key, tup)
        viz_api.figureframes[figureKey] = self
        self.ex1 = Example(self)
        self.ex1.btnFunc(viz_api, self.ids_related, dataTreeView, self.request.list_of_filters,
                         self.strategy, self.request.tab_names)

        self.ex1.thread.join()

        self.ex1.show()
        # Set user interface of the main window
        self.setUI()

        self.ex1.end_of_progress()
        self.ex1.close()

    def getLogger(self):
        return self.log

    # def setTabs(self):
    #
    #     filter_index = 0
    #     j = 0
    #     for str_filter_only in self.request.list_of_filters:
    #         # print("str_filter_only-->", str_filter_only)
    #         nodes_id, dtv_nodes = self.imas_viz_api.getAll1DNodes(self.ids_related,
    #                                                               self.dataTreeView,
    #                                                               self.dataTreeView.IDSRoots[self.ids_related], None,
    #                                                               None, errorBars=False,
    #                                                               str_filter_only=str_filter_only)
    #         w = GlobalPlotWidget(plotStrategy=self.strategy)
    #         self.plottable_signals = self.imas_viz_api.getAllPlottable1DSignals(dtv_nodes, self.dataTreeView,
    #                                                                             w)  # return tuple (node, signal)
    #
    #         ncurves_per_page = 6
    #         remaining_page = 0
    #         if (len(self.plottable_signals) % ncurves_per_page) != 0:
    #             remaining_page = 1
    #
    #         ntabs = int((len(self.plottable_signals) / ncurves_per_page)) + remaining_page
    #         self.tabs = []
    #
    #         for i in range(ntabs):
    #             j = j + 1
    #             self.ex1.setProgress(j)
    #             tab_name = self.request.tab_names[filter_index] + ' (' + str(i + 1) + '/' + str(ntabs) + ')'
    #             tab = QVizTab(parent=self, tab_page_name=tab_name)
    #             last_index = (i + 1) * ncurves_per_page
    #             if last_index > ntabs * ncurves_per_page:
    #                 last_index = ntabs * ncurves_per_page
    #             multiPlots = QVizTablePlotViewForPlugin(self.imas_viz_api, self.dataTreeView)
    #             tab.setTabUI(multiPlots=multiPlots, signals=self.plottable_signals[i * ncurves_per_page:last_index],
    #                          plotWidget=w)
    #             self.tabs.append(tab)
    #
    #         filter_index += 1

    def setUI(self):
        """Set user interface of the main window
        """
        self.mainWidget = QWidget(parent=self)
        self.mainWidget.setLayout(QVBoxLayout())
        self.tabWidget = QTabWidget(parent=self)

        # Add menu bar
        self.addMenuBar()

        # Set tabs
        # self.setTabs()
        self.ex1.btnFunc()

        # Position widgets
        self.mainWidget.layout().addWidget(self.tabWidget)

        if self.strategy == 'COORDINATE1':
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

        self.setCentralWidget(self.mainWidget)

        # set status bar
        self.setStatusBar()
        # self.setStatusBarText_1(text="OK")

        # Set initial window size
        dh = self.app.desktop().availableGeometry().height()
        dw = self.app.desktop().availableGeometry().width()
        self.height = dh * 0.8
        self.width = dw * 0.65

        # Move window to the center of the screen
        self.setFixedWidth(int(self.width))
        # Note: for actually resizing the window the SizeHint is required.
        #       fixed dimensions are set here so that they are properly
        #       rezognized by the self.frameGeometry() command
        self.setFixedHeight(int(self.height))
        qtRectangle = self.frameGeometry()
        centerPoint = self.app.desktop().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())

        # On tab change update the tab-containing plots
        self.tabWidget.currentChanged.connect(partial(
            self.updatePlotOfCurrentTab))

        # self.spinBox_timeIndex.valueChanged.connect(self.onTimeIndexChanged)

    def sizeHint(self):
        """Set initial window size.
        Note: Qt calls this routine automatically by default when creating this
              window/widget.
        """
        return QSize(int(self.width), int(self.height))

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
        time_slices_count = eval("len(self.data_entry." + self.ids_related + "." + self.request.slices_aos_name + ")")

        if time_slices_count == 0:
            message = "No time slice found for " + self.ids_related + "."
            raise ValueError(message)

        if time_index > time_slices_count - 1:
            message = "Time index=" + str(time_index) + " exceeds the number of slices."
            raise ValueError(message)

        time_value = eval(
            "self.data_entry." + self.ids_related + "." + self.request.slices_aos_name + "[time_index].time")

        if time_value == -9e+40:
            time_value = eval("self.data_entry." + self.ids_related + ".time[time_index]")
        return time_value

    def getCurrentTab(self):
        """Get currently selected tab.
        """
        return self.tabWidget.currentWidget()

    def updatePlotOfCurrentTab(self):
        """Update plot of current tab.
        """
        from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal \
            import QVizPlotSignal
        qvizTab = self.getCurrentTab()
        multiplots = qvizTab.layout().itemAt(0).widget()  # returns a QVizTablePlotViewForPlugin
        w = GlobalPlotWidget(plotStrategy=self.strategy)
        updated_signals = self.imas_viz_api.updateAllPlottable1DSignals(qvizTab.signals, self.time_index, plotWidget=w)
        multiplots.updatePlot(updated_signals)

    def setTimeSlider(self):
        # Set time slider
        slider_time = QSlider(Qt.Horizontal, self)
        slider_time.setValue(0)
        slider_time.setMinimum(0)
        time_slices_count = eval("len(self.data_entry." + self.ids_related + ".time)")
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
        ntimevalues = eval("len(self.data_entry." + self.ids_related + "." + self.request.slices_aos_name + ")")
        tmin = -9e+40
        tmax = -9e+40

        if ntimevalues > 0:
            tmin = eval("self.data_entry." + self.ids_related + "." + self.request.slices_aos_name + "[0].time")
            tmax = eval("self.data_entry." + self.ids_related + "." + self.request.slices_aos_name + "[-1].time")

        n = eval("len(self.data_entry." + self.ids_related + ".time)")
        # Check if empty time values were read
        # (-9e+40 is default value == empty)
        if n > 0 and (tmin == -9e+40 or tmax == -9e+40):
            tmin = eval("self.data_entry." + self.ids_related + ".time[0]")
            tmax = eval("self.data_entry." + self.ids_related + ".time[-1]")

        self.label_slider_tmin.setText(f"n<sub>t</sub> = {ntimevalues}; "
                                       f"t<sub>min</sub> = {tmin:.2f}")
        self.label_slider_tmax.setText(f"t<sub>max</sub> = {tmax:.2f}")

    def setTimeSpinBox(self):
        spinBox_timeIndex = QSpinBox(parent=self)
        spinBox_timeIndex.setValue(0)
        spinBox_timeIndex.setMinimum(0)
        maxIndex = eval("len(self.data_entry." + self.ids_related + ".time) - 1")
        spinBox_timeIndex.setMaximum(maxIndex)
        spinBox_timeIndex.setFixedWidth(65)
        spinBox_timeIndex.valueChanged.connect(self.onSpinBoxChange)
        # spinBox_timeIndex.editingFinished.connect(partial(
        #    self.updatePlotOfCurrentTab, time_index=self.time_index))
        return spinBox_timeIndex

    @pyqtSlot()
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

    @pyqtSlot()
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

        value = float(self.lineEdit_timeValue.text())
        time_profiles0 = eval("self.data_entry." + self.ids_related + "." + self.request.slices_aos_name + "[0].time")
        time = eval("self.data_entry." + self.ids_related + ".time")
        ntimevalues = len(eval("self.data_entry." + self.ids_related + "." + self.request.slices_aos_name))
        time_values = None

        if time_profiles0 == -9e+40:
            time_values = time
        else:
            time_values = [0] * ntimevalues
            for i in range(len(time_values)):
                time_values[i] = eval("self.data_entry." + self.ids_related + "." +
                                      self.request.slices_aos_name + "[i].time")

        closest_value, index = find_nearest(time_values, value)
        self.spinBox_timeIndex.setValue(index)
        if self.checkBox_instant.isChecked():
            self.updatePlotOfCurrentTab()

    def setStatusBar(self):
        self.statusBar_text_1 = QLabel("")
        self.statusBar_text_1.setStyleSheet('border: 0; color:  green;')
        self.setStatusBarTexts()
        VertLine = QFrame(self)
        VertLine.setFrameShape(VertLine.VLine | VertLine.Sunken)
        self.statusBar().addPermanentWidget(VertLine)
        self.statusBar().addPermanentWidget(self.statusBar_text_1)
        self.statusBar().show()

    def setStatusBarTexts(self, text=" "):

        self.statusBar().showMessage(f"USER={self.IDS_parameters['user']}; "
                                     f"DATABASE={self.IDS_parameters['database']}; "
                                     f"SHOT={self.IDS_parameters['shot']}; "
                                     f"RUN={self.IDS_parameters['run']} ")
        self.statusBar_text_1.setText(text)


class GlobalPlotWidget():

    def __init__(self, plotStrategy):
        super(GlobalPlotWidget, self).__init__()
        self.addTimeSlider = True
        self.addCoordinateSlider = False
        self.plotStrategy = plotStrategy
        self.sliderGroup = None

    def getStrategy(self):
        return self.plotStrategy


class Request():
    def __init__(self, ids_related, tab_names, list_of_filters, slices_aos_name, strategy):
        super(Request, self).__init__()
        self.ids_related = ids_related
        self.list_of_filters = list_of_filters
        self.tab_names = tab_names
        self.slices_aos_name = slices_aos_name
        self.strategy = strategy


class Thread(QThread):
    _signal = pyqtSignal(int)

    def __init__(self, imas_viz_api, ids_related, dataTreeView, list_of_filters, strategy, tab_names):
        super(Thread, self).__init__()
        self.tabs = None
        self.imas_viz_api = imas_viz_api
        self.ids_related = ids_related
        self.dataTreeView = dataTreeView
        self.list_of_filters = list_of_filters
        self.strategy = strategy
        self.tab_names = tab_names
        self.end_of_progress = False

    def __del__(self):
        self.wait()

    def run(self):
        self.setTabs()

    def setTabs(self):

        filter_index = 0
        j = 0
        for str_filter_only in self.list_of_filters:
            # print("str_filter_only-->", str_filter_only)
            nodes_id, dtv_nodes = self.imas_viz_api.getAll1DNodes(self.ids_related,
                                                                  self.dataTreeView,
                                                                  self.dataTreeView.IDSRoots[
                                                                      self.ids_related], None,
                                                                  None, errorBars=False,
                                                                  str_filter_only=str_filter_only)
            w = GlobalPlotWidget(plotStrategy=self.strategy)
            plottable_signals = self.imas_viz_api.getAllPlottable1DSignals(dtv_nodes,
                                                                           self.dataTreeView,
                                                                           w)  # return tuple (
            # node, signal)

            ncurves_per_page = 6
            remaining_page = 0
            if (len(plottable_signals) % ncurves_per_page) != 0:
                remaining_page = 1

            ntabs = int((len(plottable_signals) / ncurves_per_page)) + remaining_page
            self.tabs = []

            for i in range(ntabs):
                j = j + 1
                self._signal.emit(10 * j)
                tab_name = self.tab_names[filter_index] + ' (' + str(i + 1) + '/' + str(ntabs) + ')'
                tab = QVizTab(request=request, tab_page_name=tab_name)
                last_index = (i + 1) * ncurves_per_page
                if last_index > ntabs * ncurves_per_page:
                    last_index = ntabs * ncurves_per_page
                multiPlots = QVizTablePlotViewForPlugin(self.imas_viz_api, self.dataTreeView)
                tab.setTabUI(multiPlots=multiPlots,
                             signals=plottable_signals[i * ncurves_per_page:last_index],
                             plotWidget=w,
                             tabWidget=)
                self.tabs.append(tab)

            filter_index += 1

    @property
    def signal(self):
        return self._signal


class Example(QWidget):
    def __init__(self, parent):
        super(Example, self).__init__()
        self.tabs = None
        self.parent = parent
        self.progress = None
        self.thread = None
        self.setWindowTitle('QProgressBar')
        self.pbar = QProgressBar(self)
        self.pbar.setValue(0)
        self.resize(300, 100)
        self.vbox = QVBoxLayout()
        self.vbox.addWidget(self.pbar)
        self.setLayout(self.vbox)
        # self.show()

    def btnFunc(self, imas_viz_api, ids_related, dataTreeView, str_filter_only, strategy, tab_names):
        self.thread = Thread(imas_viz_api, ids_related, dataTreeView, str_filter_only, strategy, tab_names)
        self.thread.signal.connect(self.signal_accept)
        self.thread.start()

    def end_of_progress(self):
        self.thread.end_of_progress = True

    def signal_accept(self, msg):
        print("-->setting value to :" + str(msg))
        self.pbar.setValue(int(msg))


# Main used only for testing purposes (No GUI)
if __name__ == "__main__":
    # Set object managing the PyQt GUI application's control flow and main
    # settings
    app = QApplication(sys.argv)

    # Check if necessary system variables are set
    QVizGlobalOperations.checkEnvSettings()

    # Set Application Program Interface
    api = Viz_API()

    # Set data source retriever/factory
    dataSourceFactory = QVizDataSourceFactory()

    shotNumber = 134173
    runNumber = 106
    userName = 'public'
    database = 'ITER'
    occurrence = 0

    # shotNumber = 54178
    # runNumber = 0
    # userName = 'fleuryl'
    # database = 'west'
    # occurrence = 0

    IDS_parameters = {"shot": shotNumber,
                      "run": runNumber,
                      "user": userName,
                      "database": database}

    dataSource = dataSourceFactory.create(
        dataSourceName=QVizGlobalValues.IMAS_NATIVE,
        shotNumber=shotNumber,
        runNumber=runNumber,
        userName=userName,
        imasDbName=database)

    # Build the data tree view frame
    f = api.CreateDataTree(dataSource)

    # ids_name = 'equilibrium'
    # strategy = 'TIME'
    # slices_aos_name = 'time_slice'
    # list_of_filters = ['time_slice(0)']
    # tab_names = ['time_slice']

    # ids_name = 'edge_profiles'
    # strategy = 'COORDINATE1'
    # slices_aos_name = 'profiles_1d'
    # list_of_filters = ['profiles_1d(0)/grid', 'profiles_1d(0)/electrons', 'profiles_1d(0)/ion',
    #                    'profiles_1d(0)/neutral', 'profiles_1d(0)/t_i_average_fit',
    #                    'profiles_1d(0)/n_i_total_over_n_e', 'profiles_1d(0)/n_i_thermal_total',
    #                    'profiles_1d(0)/momentum_tor', 'profiles_1d(0)/zeff', 'profiles_1d(0)/zeff_fit']
    # tab_names = ['profiles_1d/grid', 'profiles_1d/electrons', 'profiles_1d/ion', 'profiles_1d/neutral',
    #              'profiles_1d/t_i_average_fit', 'profiles_1d/n_i_total_over_n_e',
    #              'profiles_1d/n_i_thermal_total', 'profiles_1d/momentum_tor', 'profiles_1d/zeff',
    #              'profiles_1d/zeff_fit']

    # ids_name = 'core_profiles'
    # strategy = 'COORDINATE1'
    # #strategy = 'TIME'
    # slices_aos_name = 'profiles_1d'
    # list_of_filters = ['profiles_1d(0)/grid', 'profiles_1d(0)/electrons', 'profiles_1d(0)/ion', 'global_quantities']
    # tab_names = ['profiles_1d/grid', 'profiles_1d/electrons', 'profiles_1d/ion', 'global_quantities']

    # ids_name = 'core_sources'
    # strategy = 'COORDINATE1'
    # source_index = 0
    # slices_aos_name = 'source[' + str(source_index) + '].profiles_1d'
    # list_of_filters = ['source(' + str(source_index) + ')/profiles_1d(0)']
    # tab_names = ['source(' + str(source_index) + ')/profiles_1d']

    # ids_name = 'magnetics'
    # strategy = 'TIME'
    # slices_aos_name = 'flux_loop'
    # list_of_filters = ['flux_loop']
    # tab_names = ['flux_loop']

    ids_name = 'equilibrium'
    slices_aos_name = 'time_slice'
    strategy = 'COORDINATE1'
    list_of_filters = ['time_slice(0)/boundary', 'time_slice(0)/constraints', 'time_slice(0)/profiles_1d',
                       'time_slice(0)/profiles_2d', 'time_slice(0)/global_quantities',
                       'time_slice(0)/coordinate_system', 'time_slice(0)/convergence']
    tab_names = ['time_slice/boundary', 'time_slice/constraints', 'time_slice/profiles_1d',
                 'time_slice/profiles_2d', 'time_slice/global_quantities', 'time_slice/coordinate_system',
                 'time_slice/convergence']

    api.LoadIDSData(f, ids_name, occurrence)
    # f.show()
    data_entry = dataSource.getImasEntry(occurrence)

    request = Request(ids_name, tab_names, list_of_filters, slices_aos_name, strategy)
    vep = VizProfiles(api, IDS_parameters, data_entry, f.dataTreeView, request)
    vep.show()
    sys.exit(app.exec_())
