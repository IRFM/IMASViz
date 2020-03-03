#  Name   : ETSplugin
#
#           Initial ETS plugin.
#
#  Author :
#         Dejan Penko
#  E-mail :
#         dejan.penko@lecad.fs.uni-lj.si
#
# ****************************************************
#     Copyright(c) 2019- D. Penko

# Standard library imports
import logging
import sys
import inspect
from functools import partial

# Third party imports
import matplotlib
import numpy as np
import imas
from PyQt5.QtWidgets import (QWidget, QTabWidget, QApplication, QMainWindow,
                             QSlider, QLabel, QSpinBox, QCheckBox, QPushButton,
                             QLineEdit, QHBoxLayout, QVBoxLayout, QMenuBar,
                             QAction, QFrame)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QDoubleValidator

# IMASViz application imports
from imasviz.VizPlugins.viz_ETS.tabETSSummary import tabETSSummary
from imasviz.VizPlugins.viz_ETS.tabMain0DParam import tabMain0DParam
from imasviz.VizPlugins.viz_ETS.tabCoreProfiles import tabCoreProfiles
matplotlib.use('Qt5Agg')


def checkArguments():
    """ Check arguments when running plugin from the terminal (standalone).
    """

    if (len(sys.argv) > 1):
        import argparse
        from argparse import RawTextHelpFormatter
        description = """ETS plugin. Example for running it from terminal:
>> python3 ETSplugin.py --shot=36440 --run=1 --user=penkod --device=aug
"""

        parser = argparse.ArgumentParser(description=description,
                                         formatter_class=RawTextHelpFormatter)

        parser.add_argument("-s", "--shot", type=int, required=True,
                            help="Case parameter: shot")
        parser.add_argument("-r", "--run", type=int, required=True,
                            help="Case parameter: run")
        parser.add_argument("-u", "--user", type=str, required=True,
                            help="Case parameter: username")
        parser.add_argument("-d", "--device", type=str, required=True,
                            help="Case parameter: device")

        args = parser.parse_args()
        IDS_parameters = {"shot": args.shot,
                          "run": args.run,
                          "user": args.user,
                          "device": args.device}
    else:
        # Default parameters
        print("Using default parameters")
        IDS_parameters = {"shot": 36440,
                          "run": 1,
                          "user": "penkod",
                          "device": "aug"}

    return IDS_parameters


class ETSplugin(QMainWindow):

    time_index_changed = pyqtSignal()

    def __init__(self, IDS_parameters, ids=None):
        """
        Arguments:
            IDS_parameters (Dictionary) : Dictionary containing IDS parameters
                                          (shot, run, user, device)
            ids            (obj)        : IDS object
        """
        super(QMainWindow, self).__init__()

        # Set log parser
        self.log = logging.getLogger(__name__)
        self.log.addHandler(logging.StreamHandler())
        self.writeLogDebug(self, inspect.currentframe(), "START")

        # Set initial time slice
        self.time_index = 0

        # Get app
        self.app = QApplication.instance()
        if self.app is None:
            # if it does not exist then a QApplication is created
            self.app = QApplication([])

        self.setWindowTitle("European Transport Simulator (IMASViz plugin "
                            "sample, work in progress)")
        self.ids = ids
        self.IDS_parameters = IDS_parameters
        if ids is None:
            self.setIDS()

        self.checkIDS()

        # Set user interface of the main window
        self.setUI()

        # When self.time_index changes update all widgets that display time
        # index value (spinbox, slider etc.)
        self.time_index_changed.connect(self.updateWidgetsTimeIndexValue)

        self.writeLogDebug(self, inspect.currentframe(), "END")

    def setIDS(self):
        self.writeLogDebug(self, inspect.currentframe(), "START")
        try:
            self.ids = imas.ids(self.IDS_parameters["shot"],
                                self.IDS_parameters["run"])
            self.ids.open_env(self.IDS_parameters["user"],
                              self.IDS_parameters["database"], '3')
        except:
            self.ids = None
            print("Error when trying to get() the IDS. Data for given IDS "
                  "parameters either doesn't exist or is corrupted.")

        # Read data from the required IDSs (get() routine)
        self.getCoreProfiles()
        self.getCoreTransport()
        self.getCoreSources()
        self.getEquilibrium()
        self.writeLogDebug(self, inspect.currentframe(), "END")

    def getCoreProfiles(self, ):
        self.writeLogDebug(self, inspect.currentframe(), "START")
        if self.ids is not None:
            self.ids.core_profiles.get()
            # Second method of opening slice
            # ts = 2.0
            # self.ids.core_profiles.getSlice(ts, imas.imasdef.CLOSEST_SAMPLE)
        self.writeLogDebug(self, inspect.currentframe(), "END")

    def getCoreTransport(self):
        self.writeLogDebug(self, inspect.currentframe(), "START")
        if self.ids is not None:
            self.ids.core_transport.get()
        self.writeLogDebug(self, inspect.currentframe(), "END")

    def getCoreSources(self):
        self.writeLogDebug(self, inspect.currentframe(), "START")

        if self.ids is not None:
            self.ids.core_sources.get()
        self.writeLogDebug(self, inspect.currentframe(), "END")

    def getEquilibrium(self):
        self.writeLogDebug(self, inspect.currentframe(), "START")

        if self.ids is not None:
            self.ids.equilibrium.get()
        self.writeLogDebug(self, inspect.currentframe(), "END")

    def checkIDS(self):
        self.writeLogDebug(self, inspect.currentframe(), "START")
        if self.ids is None:
            print("IDS object is None!")
            return

        # Displaying basic information
        print('Reading data...')
        print('Shot    =', self.IDS_parameters["shot"])
        print('Run     =', self.IDS_parameters["run"])
        print('User    =', self.IDS_parameters["user"])
        print('Database =', self.IDS_parameters["database"])
        # print('ts =', ts)

        print("Number of time slices: ", len(self.ids.core_profiles.time))
        print("Number of profiles_1d slices: ",
              len(self.ids.core_profiles.profiles_1d))

        if len(self.ids.core_profiles.profiles_1d) == 0:
            self.log.warning("WARNING: Found 0 profiles_1d arrays in "
                             "Core Profiles!")

        self.writeLogDebug(self, inspect.currentframe(), "END")

    def writeLogDebug(self, instance, currentframe, msg):
        """ Print to DEBUG log.
        Arguments:
            instance     (obj) : Class instance (e.g. self).
            currentframe (obj) : Frame object for the caller’s stack frame.
            msg          (str) : Additional message (usually "START" or "END")
        """

        self.log.debug(f"DEBUG | {type(instance).__name__} | "
                       f"{currentframe.f_code.co_name}  | {msg}.")

    def getLogger(self):
        return self.log

    def setUI(self):
        """Set user interface of the main window
        """
        self.writeLogDebug(self, inspect.currentframe(), "START")
        self.log.info("ETS plugin: setting UI")
        self.mainWidget = QWidget(parent=self)
        self.mainWidget.setLayout(QVBoxLayout())
        self.tabWidget = QTabWidget(parent=self)

        # Add menu bar
        self.addMenuBar()

        # Set time slider
        self.slider_time = self.setTimeSlider()
        self.label_slider_tmin = QLabel("t<sub>min</sub>", parent=self)
        self.label_slider_tmax = QLabel("t<sub>max</sub>", parent=self)

        # Set tabs
        self.tabETSSummary = tabETSSummary(parent=self)
        self.tabMain0DParam = tabMain0DParam(parent=self)
        self.tabCoreProfiles = tabCoreProfiles(parent=self)

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
        self.plotButton.clicked.connect(partial(self.updatePlotOfCurrentTab))
        self.indexMinus10Button = QPushButton("<<", parent=self)
        self.indexMinus10Button.setFixedWidth(80)
        self.indexMinus10Button.clicked.connect(partial(
            self.updatePlotOfCurrentTab, modify=-10))
        self.indexMinus1Button = QPushButton("<", parent=self)
        self.indexMinus1Button.setFixedWidth(80)
        self.indexMinus1Button.clicked.connect(partial(
            self.updatePlotOfCurrentTab, modify=-1))
        self.indexPlus1Button = QPushButton(">", parent=self)
        self.indexPlus1Button.setFixedWidth(80)
        self.indexPlus1Button.clicked.connect(partial(
            self.updatePlotOfCurrentTab, modify=+1))
        self.indexPlus10Button = QPushButton(">>", parent=self)
        self.indexPlus10Button.setFixedWidth(80)
        self.indexPlus10Button.clicked.connect(partial(
            self.updatePlotOfCurrentTab, modify=+10))

        # Set check box
        self.checkBox_instant_label = QLabel("Instant plot update on time "
                                             "index change: ")
        self.checkBox_instant_label.setFixedWidth(285)
        self.checkBox_instant = QCheckBox(parent=self)
        self.checkBox_instant.setChecked(False)

        # Position widgets
        self.mainWidget.layout().addWidget(self.tabWidget)

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
        whbox2.layout().addWidget(self.indexMinus10Button)
        whbox2.layout().addWidget(self.indexMinus1Button)
        whbox2.layout().addWidget(self.indexPlus1Button)
        whbox2.layout().addWidget(self.indexPlus10Button)
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
        self.setStatusBarText_1(text="OK")

        # Set initial window size
        dh = self.app.desktop().availableGeometry().height()
        dw = self.app.desktop().availableGeometry().width()
        self.height = dh*0.7
        self.width = dw*0.95

        # Move window to the center of the screen
        Ycenter = (dh - self.height)*0.5
        Xcenter = (dw - self.width)*0.5
        self.move(int(Xcenter), int(Ycenter))

        # On tab change update the tab-containing plots
        self.tabWidget.currentChanged.connect(partial(
            self.updatePlotOfCurrentTab, time_index=self.getTimeIndex()))
        self.writeLogDebug(self, inspect.currentframe(), "START")

    def sizeHint(self):
        """Set initial window size.
        Note: Qt calls this routine automatically by default when creating this
              window/widget.
        """
        return QSize(self.width, self.height)

    def addMenuBar(self):
        """Create and configure the menu bar.
        """
        # Main menu bar
        menuBar = QMenuBar(self)
        options = menuBar.addMenu('Options')

        # Set new menu item for saving plot configuration
        act_setDebugMode = QAction('Debug mode', self, checkable=True)
        act_setDebugMode.setStatusTip('Enable/disable debug mode')
        act_setDebugMode.setChecked(False)
        act_setDebugMode.triggered.connect(self.toggleDebugMode)
        options.addAction(act_setDebugMode)

        # Set menu bar
        self.setMenuBar(menuBar)

    def toggleDebugMode(self, state):
        """ Toggle debug mode.
        """
        if state:
            self.log.setLevel(logging.DEBUG)
        else:
            self.log.setLevel(logging.INFO)

    def getTimeIndex(self):
        return self.time_index

    def setTimeIndex(self, time_index):

        self.writeLogDebug(self, inspect.currentframe(),
                           f"Given time_index: {time_index}")

        # time slice index lower than 0 is not allowed
        if time_index < 0:
            self.time_index = 0
        else:
            self.time_index = time_index

        self.time_index_changed.emit()

    def getTimeValueForTimeIndex(self, time_index):
        """ Get time value for given time index.
        """

        if time_index < 0:
            time_index = 0
        time_value = 0

        if self.ids.core_profiles.profiles_1d[0].time == -9e+40:
            if len(self.ids.core_profiles.time) > (time_index+1):
                time_value = self.ids.core_profiles.time[time_index]
        else:
            time_value = self.ids.core_profiles.profiles_1d[time_index].time


        return time_value

    def getCurrentTab(self):
        """Get currently opened tab.
        """

        self.writeLogDebug(self, inspect.currentframe(), "START")
        # currentIndex=self.tabWidget.currentIndex()
        currentWidget = self.tabWidget.currentWidget()

        self.writeLogDebug(self, inspect.currentframe(), "END")

        return currentWidget

    def updatePlotOfCurrentTab(self, time_index=0, modify=None):
        """Update plot of current tab.
        """

        self.writeLogDebug(self, inspect.currentframe(), "START")
        self.writeLogDebug(self, inspect.currentframe(),
                           f"given time_index: {time_index}")

        if time_index != 0:
            self.setTimeIndex(time_index)

        if modify:
            self.setTimeIndex(self.getTimeIndex()+modify)
        else:
            self.setTimeIndex(self.getTimeIndex())

        self.writeLogDebug(self, inspect.currentframe(),
                           f"Global time_index: {self.getTimeIndex()}")

        cw = self.getCurrentTab()
        cw.plotUpdate(self.time_index)
        self.writeLogDebug(self, inspect.currentframe(), "END")

    @pyqtSlot()
    def updateWidgetsTimeIndexValue(self):
        self.writeLogDebug(self, inspect.currentframe(),
                           f"Updating to {self.getTimeIndex()}")
        self.slider_time.setValue(self.getTimeIndex())
        self.spinBox_timeIndex.setValue(self.getTimeIndex())
        self.lineEdit_timeValue.setText(
            f"{self.getTimeValueForTimeIndex(time_index=self.getTimeIndex())}")

    def setTimeSlider(self):
        self.writeLogDebug(self, inspect.currentframe(), "START")
        # Set time slider
        slider_time = QSlider(Qt.Horizontal, self)
        slider_time.setValue(0)
        slider_time.setMinimum(0)
        slider_time.setMaximum(len(self.ids.core_profiles.time)-1)
        # self.slider_time.adjustSize()
        # self.slider_time.setMinimumWidth(600)
        # Set slider event handling
        slider_time.valueChanged.connect(self.onSliderChange)

        self.writeLogDebug(self, inspect.currentframe(), "END")
        return slider_time

    def onSliderChange(self, event=None):
        """ PyQt slot: on change of the slider value.
        """

        self.writeLogDebug(self, inspect.currentframe(), "START")
        self.setTimeIndex(self.slider_time.value())
        self.writeLogDebug(self, inspect.currentframe(), "END")

    def updateTimeSliderTminTmaxLabel(self):
        """ Update tmin and tmax label/values.
        """
        nslices = len(self.ids.core_profiles.profiles_1d)
        ntimevalues = nslices

        tmin = self.ids.core_profiles.profiles_1d[0].time
        tmax = self.ids.core_profiles.profiles_1d[-1].time

        # Check if empty time values were read
        # (-9e+40 is default value == empty)
        if tmin == -9e+40 or tmax == -9e+40:
            self.writeLogDebug(self,
                               inspect.currentframe(),
                               "core_profiles.profiles_1d[:].time is empty. "
                               "Switching to read core_profiles.time")
            tmin = self.ids.core_profiles.time[0]
            tmax = self.ids.core_profiles.time[-1]
            ntimevalues = len(self.ids.core_profiles.time)

        self.label_slider_tmin.setText(f"n<sub>t</sub> = {ntimevalues}; "
                                       f"t<sub>min</sub> = {tmin:.2f}")
        self.label_slider_tmax.setText(f"t<sub>max</sub> = {tmax:.2f}")

    def setTimeSpinBox(self):
        self.writeLogDebug(self, inspect.currentframe(), "START")
        spinBox_timeIndex = QSpinBox(parent=self)
        spinBox_timeIndex.setValue(0)
        spinBox_timeIndex.setMinimum(0)
        spinBox_timeIndex.setMaximum(len(self.ids.core_profiles.time)-1)
        spinBox_timeIndex.setFixedWidth(65)

        spinBox_timeIndex.valueChanged.connect(self.onSpinBoxChange)
        spinBox_timeIndex.editingFinished.connect(partial(
            self.updatePlotOfCurrentTab, time_index=self.time_index))
        self.writeLogDebug(self, inspect.currentframe(), "END")

        return spinBox_timeIndex

    @pyqtSlot()
    def onSpinBoxChange(self, event=None):

        self.writeLogDebug(self, inspect.currentframe(), "START")
        # Update global time_index value (auto spinbox value update)
        self.time_index = self.spinBox_timeIndex.value()

        if self.checkBox_instant.isChecked():
            # Update plots
            # self.getCurrentTab().plotUpdate(time_index=self.spinBox_timeIndex.value())
            self.updatePlotOfCurrentTab(time_index=self.time_index)
        self.writeLogDebug(self, inspect.currentframe(), "END")

    def setTimeValueLineEdit(self):
        self.writeLogDebug(self, inspect.currentframe(), "START")
        lineEdit_timeValue = QLineEdit("", parent=self)
        self.onlyDouble = QDoubleValidator()
        lineEdit_timeValue.setValidator(self.onlyDouble)
        lineEdit_timeValue.setFixedWidth(200)
        lineEdit_timeValue.setText(
            f"{self.getTimeValueForTimeIndex(time_index=0)}")
        lineEdit_timeValue.editingFinished.connect(
            self.onTimeValueLineEditEditingFinished)
        self.writeLogDebug(self, inspect.currentframe(), "END")

        return lineEdit_timeValue

    @pyqtSlot()
    def onTimeValueLineEditEditingFinished(self, event=None):
        """ When finished editing the time value line edit (pressing enter etc.)
        find the closest value (and its array index -> time index) based on the
        inserted value.
        """
        self.writeLogDebug(self, inspect.currentframe(), "START")

        # A simple routine to find the nearest value (and its index) based on
        # given value
        def find_nearest(array, value):
            array = np.asarray(array)
            idx = (np.abs(array - value)).argmin()
            return array[idx], idx

        value = float(self.lineEdit_timeValue.text())

        time_values = 0
        if self.ids.core_profiles.profiles_1d[0].time == -9e+40:
            time_values = self.ids.core_profiles.time
        else:
            time_values = [0]*len(self.ids.core_profiles.profiles_1d)

            for i in range(time_values):
                time_values[i] = self.ids.core_profiles.profiles_1d[i].time

        closest_value, index = find_nearest(time_values, value)

        # by setting global time_index using setTimeIndex array all widgets
        # get updated automatically
        self.setTimeIndex(index)
        self.updatePlotOfCurrentTab()
        self.writeLogDebug(self, inspect.currentframe(), "END")

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
                                     f"DEVICE={self.IDS_parameters['device']}; "
                                     f"SHOT={self.IDS_parameters['shot']}; "
                                     f"RUN={self.IDS_parameters['run']} ")
        self.statusBar_text_1.setText(text)

        # self.status_text.repaint()
        # self.statusBar().show()

    def setStatusBarText_1(self, text="", color="green"):
        self.statusBar_text_1.setText(text)
        self.statusBar_text_1.setStyleSheet(f'border: 0; color:  {color};')


if __name__ == "__main__":
    # Set mandatory arguments
    IDS_parameters = checkArguments()

    app = QApplication(sys.argv)

    ets = ETSplugin(IDS_parameters)
    ets.tabETSSummary.plot()

    ets.show()

    sys.exit(app.exec_())
