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
        self.grid_subp    = matplotlib.gridspec.GridSpec(2, 2)
        self.ax1 = self.fig.add_subplot(self.grid_subp[0, 0])

    def plot(self):

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

        # Plot te (electron temperature) / ti (ion temperature)
        self.plot_te_ti()

        self.show()

    def plotUpdate(self, time_value):

        cp = self.ids.core_profiles.profiles_1d[time_value]

        # Clear all plots
        self.ax1.cla()
        # Re-plot te (electron temperature) / ti (ion temperature)
        self.plot_te_ti()

        # Update the figure display
        self.canvas.draw()
        self.canvas.flush_events()

    def plot_te_ti(self):

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
        self.ax1.xaxis.set_minor_locator(ticker.AutoMinorLocator(self._nminor_interval))
        self.ax1.yaxis.set_minor_locator(ticker.AutoMinorLocator(self._nminor_interval))
        self.ax1.grid()
        leg = self.ax1.legend()
        leg.set_draggable(True)

