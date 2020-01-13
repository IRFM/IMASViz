#  Name   : tabETSSummary
#
#           Summary tab for ETS plugin.
#
#  Author :
#         Dejan Penko
#  E-mail :
#         dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2019- D. Penko, J. Ferreira

from PyQt5.QtWidgets import QWidget, QGridLayout, QSlider, QLabel
from PyQt5.QtCore import Qt
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.figure import Figure
from matplotlib import ticker
from matplotlib.backends.backend_qt5agg import \
    FigureCanvasQTAgg as FigCanvas
from matplotlib.backends.backend_qt5agg import \
    NavigationToolbar2QT as NavigationToolbar

import pylab

class tabETSSummary(QWidget):

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)

        self.parent = parent
        # Get/set IDS
        if self.parent.ids == None:
            self.parent.setIDS()
        self.ids  = self.parent.ids

        # Set tab user interface
        self.setTabUI()

    def setTabUI(self):
        """Set tab user interface.
        """

        self.setLayout(QGridLayout())
        self.parent.tabWidget.addTab(self, "ETS summary")

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
        self.grid_subp    = matplotlib.gridspec.GridSpec(2, 3)
        self.ax1 = self.fig.add_subplot(self.grid_subp[0, 0])
        self.ax2 = self.fig.add_subplot(self.grid_subp[0, 1])
        self.ax3 = self.fig.add_subplot(self.grid_subp[0, 2])
        self.ax3_2 = self.ax3.twinx()
        self.ax4 = self.fig.add_subplot(self.grid_subp[1, 0])
        self.ax5 = self.fig.add_subplot(self.grid_subp[1, 1])
        self.ax6 = self.fig.add_subplot(self.grid_subp[1, 2])

    def plot(self):
        """Main plot function.
        """

        # Set list of colors for plots
        self.ion_colors = ['DarkBlue','Purple', 'RoyalBlue','Magenta',
                           'Tomato', 'LimeGreen',  'DarkCyan']
        self.ion_ni_colors = ['DarkGreen','Olive',  'Orange', 'darkgoldenrod',
                              'peru', 'indianred', 'amber']

        # Ticker minor interval
        self._nminor_interval = 4

        nslices = len(self.ids.core_profiles.profiles_1d)
        self.nslices2plot = 1

        self.cp = self.ids.core_profiles.profiles_1d[0]

        # Re-plot te/ti (electron/ion temperature)
        self.plot_te_ti()
        # Re-plot ne/ni (electron/ion density)
        self.plot_ne_ni()
        # Plot j_total and q (total parallel current density and safety factor)
        self.plot_jtotal_q()
        # Plot zeff profile.
        self.plot_zeff()

        self.show()

    def plotUpdate(self, time_value):
        """Clear and re-plot.
        """

        self.cp = self.ids.core_profiles.profiles_1d[time_value]

        # Re-plot te/ti (electron/ion temperature)
        self.plot_te_ti()
        # Re-plot ne/ni (electron/ion density)
        self.plot_ne_ni()
        # Plot j_total and q (total parallel current density and safety factor)
        self.plot_jtotal_q()
        # Plot zeff profile.
        self.plot_zeff()

        # Update the figure display
        self.canvas.draw()
        self.canvas.flush_events()

    def plot_te_ti(self):
        """Plot electron temperature (te) and ion temperature (ti)
        """

        # Clear plot first
        self.ax1.cla()

        try:
            rhotor = self.cp.grid.rho_tor_norm
            te = self.cp.electrons.temperature
            self.ax1.plot(rhotor, 1.0e-3*te,
                          label = "Te",
                          color='r',
                          linewidth=1.5)
            for i in range(len(self.cp.ion)):
                ti = self.cp.ion[i].temperature
                if self.cp.ion[i].multiple_states_flag == 0 :
                    self.ax1.plot(rhotor,
                                  1.0e-3*self.cp.ion[i].temperature,
                                  label='Ti %d'%(i+1),
                                  color=self.ion_colors[min(i,len(self.ion_colors)-1)],
                                  linewidth=1.5)

        except Exception as err:
            raise ValueError( 'ERROR occurred when plotting temperatures. (%s) ' % err )

        self.ax1.set(xlabel= "rhotor [m]", ylabel='Temperature [keV]')
        # self.ax1.set_yticks([])
        self.ax1.xaxis.set_minor_locator(
            ticker.AutoMinorLocator(self._nminor_interval))
        self.ax1.yaxis.set_minor_locator(
            ticker.AutoMinorLocator(self._nminor_interval))
        self.ax1.grid()
        leg = self.ax1.legend()
        leg.set_draggable(True)

    def plot_ne_ni(self):
        """Plot electron density (te) and ion density (ti)
        """

        # Clear plot first
        self.ax2.cla()

        try:
            rhotor = self.cp.grid.rho_tor_norm
            ne = self.cp.electrons.density
            self.ax2.plot(rhotor, 1.0e-19*ne,
                          label = "Ne",
                          color='r',
                          linewidth=1.5)
            for i in range(len(self.cp.ion)):
                ni = self.cp.ion[i].density
                if self.cp.ion[i].multiple_states_flag == 0 :
                    self.ax2.plot(rhotor,
                                  1.0e-19*self.cp.ion[i].density,
                                  label='Ni %d'%(i+1),
                                  color=self.ion_colors[min(i,len(self.ion_colors)-1)],
                                  linewidth=1.5)

        except Exception as err:
            raise ValueError( 'ERROR occurred when plotting densities. (%s) ' % err )

        self.ax2.set(xlabel= "rhotor [m]", ylabel='Density [10^19 m-3]')
        # self.ax2.set_yticks([])
        self.ax2.xaxis.set_minor_locator(
            ticker.AutoMinorLocator(self._nminor_interval))
        self.ax2.yaxis.set_minor_locator(
            ticker.AutoMinorLocator(self._nminor_interval))
        self.ax2.grid()
        leg = self.ax2.legend()
        leg.set_draggable(True)

    def plot_jtotal_q(self):
        """Plot total parallel current density (j_total) and safety factor (q).
        """

        # Clear plot first
        self.ax3.cla()
        self.ax3_2.cla()

        try:
            rhotor = self.cp.grid.rho_tor_norm
            q = self.cp.q
            j_total = self.cp.j_total
            pl1 = self.ax3.plot(rhotor, 1.0e-6*abs(j_total),
                          label = "j_total",
                          color='b',
                          linewidth=1.5)
            self.ax3.tick_params(axis='y', colors='blue')
            pl2 = self.ax3_2.plot(rhotor, abs(q),
                          label = "q",
                          color='r',
                          linewidth=1.5)
            self.ax3_2.tick_params(axis='y', colors='red')

        except Exception as err:
            raise ValueError( 'ERROR occurred when plotting equilibrium related profiles. (%s) ' % err )


        # Combine legend of the both plots into a single legend box
        pl = pl1 + pl2
        labs = [l.get_label() for l in pl]
        leg = self.ax3_2.legend(pl, labs, loc=0)
        leg.set_draggable(True)

        self.ax3.set(xlabel= "rhotor [m]", ylabel='j_total [MA/m2]')
        self.ax3_2.set(xlabel= "rhotor [m]", ylabel='q [MA/m2]')
        # self.ax3.set_yticks([])
        self.ax3.xaxis.set_minor_locator(
            ticker.AutoMinorLocator(self._nminor_interval))
        self.ax3.yaxis.set_minor_locator(
            ticker.AutoMinorLocator(self._nminor_interval))
        self.ax3_2.yaxis.set_minor_locator(
            ticker.AutoMinorLocator(self._nminor_interval))
        self.ax3.grid(color="Blue")
        self.ax3_2.grid(color="Red")


    def plot_zeff(self):
        """Plot zeff profile.
        """

        # Clear plot first
        self.ax4.cla()

        try:
            rhotor = self.cp.grid.rho_tor_norm
            zeff = self.cp.zeff
            self.ax4.set_xlim(0, max(rhotor))
            self.ax4.set_ylim(1, max(zeff)*1.05)
            self.ax4.plot(rhotor, zeff,
                          label = "zeff",
                          color='b',
                          linewidth=1.5)
            self.ax4.tick_params(axis='y', colors='blue')

        except Exception as err:
            raise ValueError( 'ERROR occurred when plotting Zeff profile. (%s) ' % err )

        self.ax4.set(xlabel= "rhotor [m]", ylabel='Zeff [-]')
        # self.ax4.set_yticks([])
        self.ax4.yaxis.set_major_formatter(pylab.NullFormatter())
        self.ax4.xaxis.set_minor_locator(
            ticker.AutoMinorLocator(self._nminor_interval))
        self.ax4.yaxis.set_minor_locator(
            ticker.AutoMinorLocator(self._nminor_interval))
        self.ax4.grid()
        leg = self.ax4.legend()
        leg.set_draggable(True)
