#  Name   : tabCoreProfiles
#
#           Core Profiles tab for ETS plugin.
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

from PyQt5.QtWidgets import QWidget, QGridLayout, QSlider, QLabel
from PyQt5.QtCore import Qt
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import \
    FigureCanvasQTAgg as FigCanvas
from matplotlib.backends.backend_qt5agg import \
    NavigationToolbar2QT as NavigationToolbar

class tabCoreProfiles(QWidget):

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)

        self.parent = parent

        if self.parent.ids == None:
            self.parent.setIDS()

        self.ids  = self.parent.ids
        self.setTabUI()

    def setTabUI(self):

        self.setLayout(QGridLayout())
        self.parent.tabWidget.addTab(self, "Core Profiles")

        # Create the matplotlib Figure and FigCanvas objects.
        # 100 dots-per-inch
        self.dpi = 100
        self.fig = Figure(dpi=self.dpi)
        self.canvas = FigCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        # Add canvas to tab widget
        self.layout().addWidget(self.canvas, 0, 0, 2, 10)
        self.layout().addWidget(self.toolbar, 1, 0, 1, 10)

        self.fig.subplots_adjust(left=0.08, right=0.90, bottom=0.1, top=0.9, \
                                 wspace=0.3, hspace=0.35)

        # self.fig.suptitle('ETS plugin')
        self.grid_subp    = matplotlib.gridspec.GridSpec(2, 2)
        self.ax1 = self.fig.add_subplot(self.grid_subp[0, 0])
        self.ax2 = self.fig.add_subplot(self.grid_subp[0, 1])
        self.ax3 = self.fig.add_subplot(self.grid_subp[1, 0])
        self.ax4 = self.fig.add_subplot(self.grid_subp[1, 1])
        self.ax5 = self.ax4.twinx()

    def plot(self):

        self.cp = self.ids.core_profiles.profiles_1d[0]

        self.ax1.plot(self.cp.grid.rho_tor_norm, 1.0e-3*self.cp.electrons.temperature, label='el')
        for i in range(len(self.cp.ion)):
            if self.cp.ion[i].multiple_states_flag == 0 :
                self.ax1.plot(self.cp.grid.rho_tor_norm, 1.0e-3*self.cp.ion[i].temperature, label='ion %d'%(i+1))
        self.ax1.set(title='Temperature', ylabel='[keV]')
        self.ax1.legend()
        self.ax1.grid()

        self.ax2.plot(self.cp.grid.rho_tor_norm, 1.0e-19*self.cp.electrons.density_thermal, label='el')
        for i in range(len(self.cp.ion)):
            if self.cp.ion[i].multiple_states_flag == 0 :
                self.ax2.plot(self.cp.grid.rho_tor_norm, 1.0e-19*self.cp.ion[i].density_thermal, label='ion %d'%(i+1))
        self.ax2.set(title='Density', ylabel='[10^19 m-3]')
        self.ax2.legend()
        self.ax2.grid()

        self.ax3.plot(self.cp.grid.rho_tor_norm, 1.0e-6*self.cp.j_total, label='j_tor')
        self.ax3.set(title='Current', xlabel='rhon', ylabel='[MA m-2]')
        self.ax3.legend()
        self.ax3.grid()

        pl4 = self.ax4.plot(self.cp.grid.rho_tor_norm, self.cp.q, label='q')
        pl5 = self.ax5.plot(self.cp.grid.rho_tor_norm, self.cp.magnetic_shear, color='C1', label='shear')
        self.ax4.set(title='safety factor / shear', xlabel='rhon', ylabel='[-]')
        # Combine legend of the both plots into a single legend box
        pl = pl4+pl5
        labs = [l.get_label() for l in pl]
        leg5 = self.ax5.legend(pl, labs, loc=0)
        leg5.set_draggable(True)
        self.ax4.grid()
        self.ax5.grid()

        self.show()

    def plotUpdate(self, time_value):

        cp = self.ids.core_profiles.profiles_1d[time_value]

        # Clear all plots
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
        self.ax1.grid()

        self.ax2.plot(cp.grid.rho_tor_norm, 1.0e-19*cp.electrons.density_thermal, label='el')
        for i in range(len(cp.ion)):
            if cp.ion[i].multiple_states_flag == 0 :
                self.ax2.plot(cp.grid.rho_tor_norm, 1.0e-19*cp.ion[i].density_thermal, label='ion %d'%(i+1))
        self.ax2.set(title='Density', ylabel='[10^19 m-3]')
        self.ax2.legend()
        self.ax2.grid()

        self.ax3.plot(cp.grid.rho_tor_norm, 1.0e-6*cp.j_total, label='j_tor')
        self.ax3.set(title='Current', xlabel='rhon', ylabel='[MA m-2]')
        self.ax3.legend()
        self.ax3.grid()

        pl4 = self.ax4.plot(cp.grid.rho_tor_norm, cp.q, label='q')
        pl5 = self.ax5.plot(cp.grid.rho_tor_norm, cp.magnetic_shear, color='C1', label='shear')
        # Combine legend of the both plots into a single legend box
        pl = pl4+pl5
        labs = [l.get_label() for l in pl]
        leg5 = self.ax5.legend(pl, labs, loc=0)
        leg5.set_draggable(True)
        self.ax4.grid()
        self.ax5.grid()

        # Update the figure display
        self.canvas.draw()
        self.canvas.flush_events()

