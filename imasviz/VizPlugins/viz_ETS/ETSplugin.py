#  Name   : ETSplugin
#
#           Initial ETS plugin.
#
#  Author :
#         Dejan Penko
#  E-mail :
#         dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2019- D. Penko

# Standard library imports
import logging, os, sys
from functools import partial

# Third party imports
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import \
    FigureCanvasQTAgg as FigCanvas
from matplotlib.backends.backend_qt5agg import \
    NavigationToolbar2QT as NavigationToolbar
import imas
from PyQt5.QtWidgets import (QWidget, QTabWidget, QApplication, QMainWindow,
    QGridLayout, QSlider, QLabel, QSpinBox, QCheckBox)
from PyQt5.QtCore import Qt, QSize

# IMASViz application imports
from imasviz.VizPlugins.viz_ETS.tabCoreProfiles import tabCoreProfiles
from imasviz.VizPlugins.viz_ETS.tabETSSummary import tabETSSummary

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
        IDS_parameters = {  "shot": args.shot,
                            "run": args.run,
                            "user": args.user,
                            "device": args.device}
    else:
        # Default parameters
        print("Using default parameters")
        IDS_parameters = {  "shot": 36440,
                            "run": 1,
                            "user": "penkod",
                            "device": "aug"}

    return IDS_parameters

class ETSplugin(QMainWindow):
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
        # self.log.setLevel(logging.DEBUG)
        self.log.setLevel(logging.INFO)
        self.log.addHandler(logging.StreamHandler())

        # Set initial time slice
        self.time_index = 0

        # Get app
        self.app = QApplication.instance()
        if self.app is None:
            # if it does not exist then a QApplication is created
            self.app = QApplication([])

        self.setWindowTitle("European Transport Simulator (IMASViz plugin sample, work in progress)")
        self.ids = ids
        self.IDS_parameters = IDS_parameters
        if ids == None:
            self.setIDS()

        self.checkIDS()

        # Set user interface of the main window
        self.setUI()

    def getLogger(self):
        return self.log

    def setUI(self):
        """Set user interface of the main window
        """
        print("ETS plugin: setting UI")
        self.mainWidget = QWidget(parent=self)
        self.mainWidget.setLayout(QGridLayout())
        self.tabWidget = QTabWidget(parent=self)

        # Set time slider
        self.slider_time = self.setTimeSlider()
        self.mainWidget.layout().addWidget(self.slider_time, 0, 0, 1, 1)
        self.mainWidget.layout().addWidget(self.tabWidget, 2, 0, 1, 3)

        # Set tabs
        self.tabETSSummary = tabETSSummary(parent=self)
        self.tabCoreProfiles = tabCoreProfiles(parent=self)

        # Set time slice label
        self.time_indexLabel = QLabel("Time slice: ")
        # Set spinbox
        self.spinBox_time = self.setTimeSpinBox()

        # Set check box
        self.checkBox_instant_label = QLabel("Instant plot update on time index change: ")
        self.checkBox_instant = QCheckBox(parent=self)
        self.checkBox_instant.setChecked(False)

        self.mainWidget.layout().addWidget(self.time_indexLabel, 0, 1, 1, 1)
        self.mainWidget.layout().addWidget(self.spinBox_time, 0, 2, 1, 1)
        self.mainWidget.layout().addWidget(self.checkBox_instant_label, 1, 1, 1, 1)
        self.mainWidget.layout().addWidget(self.checkBox_instant, 1, 2, 1, 1)
        self.setCentralWidget(self.mainWidget)

        # Set initial window size
        self.height = self.app.desktop().availableGeometry().height()*0.7
        self.width = self.app.desktop().availableGeometry().width()*0.95

        # Move window to the center of the screen
        Ycenter = (self.app.desktop().availableGeometry().height() - self.height)*0.5
        Xcenter = (self.app.desktop().availableGeometry().width() - self.width)*0.5
        self.move(int(Xcenter), int(Ycenter))

        # On tab change update the tab-containing plots
        self.tabWidget.currentChanged.connect(partial(
            self.updatePlotOfCurrentTab, time_index=self.getTimeIndex()))

    def sizeHint(self):
        """Set initial window size.
        Note: Qt calls this routine automatically by default when creating this
              window/widget.
        """
        return QSize(self.width,self.height)

    def getTimeIndex(self):
        return self.time_index

    def setTimeIndex(self, time_index):
        self.time_index = time_index

    def setTimeSlider(self):
        # Set time slider
        slider_time = QSlider(Qt.Horizontal, self)
        slider_time.setValue(0)
        slider_time.setMinimum(0)
        slider_time.setMaximum(len(self.ids.core_profiles.time)-1)
        # self.slider_time.adjustSize()
        # self.slider_time.setMinimumWidth(600)
        # Set slider event handling
        slider_time.valueChanged.connect(self.onSliderChange)

        # slider_time.sliderMoved.connect(self.onSliderChange)
        # slider_time.sliderReleased.connect(self.onSliderChange)
        return slider_time

    def updatePlotOfCurrentTab(self, time_index=0):
        """Update plot of current tab.
        """

        self.log.debug(f"DEBUG | {type(self).__name__} | updatePlotOfCurrentTab() | START.")
        time_index = self.time_index
        cw = self.getCurrentTab()
        cw.plotUpdate(time_index)

    def onSliderChange(self, event=None):

        self.log.debug(f"DEBUG | {type(self).__name__} | onSliderChange() | START.")
        if self.slider_time.value() != self.spinBox_time.value():
            # Update spinbox value
            self.spinBox_time.setValue(self.slider_time.value())
        # Update plots
        # self.getCurrentTab().plotUpdate(time_index=self.slider_time.value())

    def getCurrentTab(self):

        self.log.debug(f"DEBUG | {type(self).__name__} | getCurrentTab() | START.")
        # currentIndex=self.tabWidget.currentIndex()
        currentWidget=self.tabWidget.currentWidget()

        return currentWidget

    def setTimeSpinBox(self):
        spinBox_time = QSpinBox(parent=self)
        spinBox_time.setValue(0)
        spinBox_time.setMinimum(0)
        spinBox_time.setMaximum(len(self.ids.core_profiles.time)-1)

        spinBox_time.valueChanged.connect(self.onSpinBoxChange)
        spinBox_time.editingFinished.connect(partial(
            self.updatePlotOfCurrentTab, time_index=self.time_index))

        return spinBox_time

    def onSpinBoxChange(self, event=None):

        self.log.debug(f"DEBUG | {type(self).__name__} | onSpinBoxChange() | START.")
        # Update slider value
        self.time_index = self.spinBox_time.value()
        self.slider_time.setValue(self.time_index)

        if self.checkBox_instant.isChecked():
            # Update plots
            # self.getCurrentTab().plotUpdate(time_index=self.spinBox_time.value())
            self.updatePlotOfCurrentTab(time_index=self.time_index)

    def setIDS(self):
        self.log.debug(f"DEBUG | {type(self).__name__} | setIDS() | START.")
        try:
            self.ids = imas.ids(self.IDS_parameters["shot"],
                                self.IDS_parameters["run"])
            self.ids.open_env(self.IDS_parameters["user"],
                              self.IDS_parameters["device"], '3')
        except:
            self.ids = None
            print("Error when trying to get() the IDS. Data for given IDS " \
                  "parameters either doesn't exist or is corrupted.")
        # Read data from the required IDSs (get() routine)
        self.getCoreProfiles()
        self.getCoreTransport()
        self.getCoreSources()

    def getCoreProfiles(self, ):
        if self.ids != None:
            self.ids.core_profiles.get()
            # Second method of opening slice
            # ts = 2.0
            # self.ids.core_profiles.getSlice(ts, imas.imasdef.CLOSEST_SAMPLE)

    def getCoreTransport(self):
        if self.ids != None:
            self.ids.core_transport.get()

    def getCoreSources(self):
        if self.ids != None:
            self.ids.core_sources.get()

    def checkIDS(self):
        if self.ids == None:
            print("IDS object is None!")
            return

        # Displaying basic information
        print('Reading data...')
        print('Shot    =', self.IDS_parameters["shot"])
        print('Run     =', self.IDS_parameters["run"])
        print('User    =', self.IDS_parameters["user"])
        print('Device =', self.IDS_parameters["device"])
        # print('ts =', ts)

        print("Number of time slices: ", len(self.ids.core_profiles.time))
        print("Number of profiles_1d slices: ", len(self.ids.core_profiles.profiles_1d))

if  __name__ == "__main__":
    # Set mandatory arguments
    IDS_parameters = checkArguments()

    app = QApplication(sys.argv)

    ets = ETSplugin(IDS_parameters)
    ets.tabETSSummary.plot()
    # ets.tabCoreProfiles.plot()

    ets.show()

    sys.exit(app.exec_())
