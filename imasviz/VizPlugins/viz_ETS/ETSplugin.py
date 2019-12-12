#  Name   : ETSplugin
#
#           Initial ETS plugin.
#
#  Author :
#         Dejan Penko
#         Jorge Ferreira
#  E-mail :
#         dejan.penko@lecad.fs.uni-lj.si
#         jferreira@ipfn.tecnico.ulisboa.pt
#
#****************************************************
#     Copyright(c) 2019- D. Penko, J. Ferreira

import logging, os, sys
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import \
    FigureCanvasQTAgg as FigCanvas
from matplotlib.backends.backend_qt5agg import \
    NavigationToolbar2QT as NavigationToolbar
import imas
from PyQt5.QtWidgets import (QWidget, QTabWidget, QApplication, QMainWindow,
    QGridLayout, QSlider, QLabel)
from PyQt5.QtCore import Qt

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
        self.ids = ids
        self.IDS_parameters = IDS_parameters
        self.tabWidget = QTabWidget(parent=self)
        if ids == None:
            self.setIDS()

        self.checkIDS()
        self.setTab1()

        self.setCentralWidget(self.tabWidget)

    def setIDS(self):
        try:
            self.ids = imas.ids(self.IDS_parameters["shot"],self.IDS_parameters["run"])
            self.ids.open_env(self.IDS_parameters["user"], self.IDS_parameters["device"], '3')
        except:
            self.ids = None
            print("Error when trying to get() the IDS. Data for given IDS " \
                  "parameters either doesn't exist or is corrupted.")
        self.getCoreProfiles()

    def getCoreProfiles(self):
        if self.ids != None:
            self.ids.core_profiles.get()
            # Second method of opening slice
            # ts = 2.0
            # self.ids.core_profiles.getSlice(ts, imas.imasdef.CLOSEST_SAMPLE)

    def setTab1(self):

        self.tab1 = QWidget(self)
        self.tab1.setLayout(QGridLayout())
        self.tabWidget.addTab(self.tab1, "Core Profiles")

        # Create the matplotlib Figure and FigCanvas objects.
        # 100 dots-per-inch
        self.dpi = 100
        self.fig = Figure(dpi=self.dpi)
        self.canvas = FigCanvas(self.fig)
        # Add canvas to tab widget
        self.tab1.layout().addWidget(self.canvas, 0, 0, 1, 10)

        self.fig.subplots_adjust(left=0.08, right=0.90, bottom=0.1, top=0.9, \
                                 wspace=0.3, hspace=0.35)

        self.fig.suptitle('ETS plugin')
        self.grid_subp    = matplotlib.gridspec.GridSpec(2, 2)
        self.ax1 = self.fig.add_subplot(self.grid_subp[0, 0])

        self.setSlider()
        self.tab1.layout().addWidget(self.slider_time, 1, 0, 1, 8)

        self.timeLabel = QLabel("Time slice: " + str(self.slider_time.value()))
        self.tab1.layout().addWidget(self.timeLabel, 1, 9, 1, 10)

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

    def setSlider(self):
        # Set time slider
        self.slider_time = QSlider(Qt.Horizontal, self.tab1)
        self.slider_time.setValue(0)
        self.slider_time.setMinimum(0)
        self.slider_time.setMaximum(len(self.ids.core_profiles.time)-1)
        # self.slider_time.adjustSize()
        # self.slider_time.setMinimumWidth(600)

        # Set slider event handling
        self.slider_time.valueChanged.connect(self.on_slider)
        # self.slider_time.sliderMoved.connect(self.on_slider_track)
        # self.slider_time.sliderReleased.connect(self.on_slider_time)

    def on_slider(self, event=None):
        self.plotUpdate()

    def plotTab1(self):

        self.cp = self.ids.core_profiles.profiles_1d[0]

        self.ax1.plot(self.cp.grid.rho_tor_norm, 1.0e-3*self.cp.electrons.temperature, label='el')
        for i in range(len(self.cp.ion)):
            if self.cp.ion[i].multiple_states_flag == 0 :
                self.ax1.plot(self.cp.grid.rho_tor_norm, 1.0e-3*self.cp.ion[i].temperature, label='ion %d'%(i+1))
        self.ax1.set(title='Temperature', ylabel='[keV]')
        self.ax1.legend()

        self.ax2 = self.fig.add_subplot(self.grid_subp[0, 1])
        self.ax2.plot(self.cp.grid.rho_tor_norm, 1.0e-19*self.cp.electrons.density_thermal, label='el')
        for i in range(len(self.cp.ion)):
            if self.cp.ion[i].multiple_states_flag == 0 :
                self.ax2.plot(self.cp.grid.rho_tor_norm, 1.0e-19*self.cp.ion[i].density_thermal, label='ion %d'%(i+1))
        self.ax2.set(title='Density', ylabel='[10^19 m-3]')
        self.ax2.legend()

        self.ax3 = self.fig.add_subplot(self.grid_subp[1, 0])
        self.ax3.plot(self.cp.grid.rho_tor_norm, 1.0e-6*self.cp.j_total, label='j_tor')
        self.ax3.set(title='Current', xlabel='rhon', ylabel='[MA m-2]')
        self.ax3.legend()

        self.ax4 = self.fig.add_subplot(self.grid_subp[1, 1])
        pl4 = self.ax4.plot(self.cp.grid.rho_tor_norm, self.cp.q, label='q')
        self.ax5 = self.ax4.twinx()
        pl5 = self.ax5.plot(self.cp.grid.rho_tor_norm, self.cp.magnetic_shear, color='C1', label='shear')
        self.ax4.set(title='safety factor / shear', xlabel='rhon', ylabel='[-]')
        # Combine legend of the both plots into a single legend box
        pl = pl4+pl5
        labs = [l.get_label() for l in pl]
        leg5 = self.ax5.legend(pl, labs, loc=0)
        leg5.set_draggable(True)

        self.show()

    def plotUpdate(self):

        sliderValue = int(round(self.slider_time.value()))
        self.timeLabel.setText("Time slice: " + str(sliderValue))
        # print("Slider value: ", sliderValue)
        cp = self.ids.core_profiles.profiles_1d[sliderValue]

        self.ax1.cla()
        self.ax2.cla()
        self.ax3.cla()
        self.ax4.cla()
        self.ax5.cla()
        self.ax1.plot(cp.grid.rho_tor_norm, 1.0e-3*cp.electrons.temperature, label='el')
        for i in range(len(cp.ion)):
            if cp.ion[i].multiple_states_flag == 0 :
                self.ax1.plot(cp.grid.rho_tor_norm, 1.0e-3*cp.ion[i].temperature, label='ion %d'%(i+1))
        self.ax1.set(title='Temperature', ylabel='[keV]')
        self.ax1.legend()

        self.ax2.plot(cp.grid.rho_tor_norm, 1.0e-19*cp.electrons.density_thermal, label='el')
        for i in range(len(cp.ion)):
            if cp.ion[i].multiple_states_flag == 0 :
                self.ax2.plot(cp.grid.rho_tor_norm, 1.0e-19*cp.ion[i].density_thermal, label='ion %d'%(i+1))
        self.ax2.set(title='Density', ylabel='[10^19 m-3]')
        self.ax2.legend()

        self.ax3.plot(cp.grid.rho_tor_norm, 1.0e-6*cp.j_total, label='j_tor')
        self.ax3.set(title='Current', xlabel='rhon', ylabel='[MA m-2]')
        self.ax3.legend()

        pl4 = self.ax4.plot(cp.grid.rho_tor_norm, cp.q, label='q')
        pl5 = self.ax5.plot(cp.grid.rho_tor_norm, cp.magnetic_shear, color='C1', label='shear')
        # Combine legend of the both plots into a single legend box
        pl = pl4+pl5
        labs = [l.get_label() for l in pl]
        leg5 = self.ax5.legend(pl, labs, loc=0)
        leg5.set_draggable(True)

        # Update the figure display
        self.canvas.draw()
        self.canvas.flush_events()



if  __name__ == "__main__":
    # Set mandatory arguments
    IDS_parameters = checkArguments()

    app = QApplication(sys.argv)

    ets = ETSplugin(IDS_parameters)
    ets.plotTab1()

    sys.exit(app.exec_())
