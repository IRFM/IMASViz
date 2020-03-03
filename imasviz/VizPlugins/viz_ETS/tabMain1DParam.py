#  Name   : tabMain1DParam
#
#           "Main 1-D parameters" tab for the ETS plugin.
#
#  Author :
#         Dejan Penko
#         Note: Followed ETSviz (ETS 5.x) design.
#  E-mail :
#         dejan.penko@lecad.fs.uni-lj.si
#
# ****************************************************
#     Copyright(c) 2019- D. Penko

import inspect
import matplotlib
from matplotlib.figure import Figure
from matplotlib import ticker
from matplotlib.backends.backend_qt5agg import \
    FigureCanvasQTAgg as FigCanvas
from matplotlib.backends.backend_qt5agg import \
    NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import QWidget, QGridLayout

import pylab
matplotlib.use('Qt5Agg')

class tabMain1DParam(QWidget):

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)

        self.parent = parent
        # Get/set IDS
        if self.parent.ids is None:
            self.parent.setIDS()
        self.ids = self.parent.ids

        # Get log parser
        self.log = self.parent.getLogger()

        self.parent.writeLogDebug(self, inspect.currentframe(), "START")

        # Set tab user interface
        self.setTabUI()

        # Set initial time slice
        self.it = 0

        # Set number of slices and arrays for holding plot lines
        nslices = len(self.ids.core_profiles.profiles_1d)
        self.nslices2plot = min(nslices, 5)

        self.parent.writeLogDebug(self, inspect.currentframe(), "END")

    def setTabUI(self):
        """Set tab user interface.
        """

        self.parent.writeLogDebug(self, inspect.currentframe(), "START")

        self.setLayout(QGridLayout())
        self.parent.tabWidget.addTab(self, "Main 1-D parameters")

        # Create the matplotlib Figure and FigCanvas objects.
        # 100 dots-per-inch
        self.dpi = 100
        self.fig = Figure(dpi=self.dpi)
        self.canvas = FigCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        # Add canvas to tab widget
        self.layout().addWidget(self.canvas, 0, 0, 1, 1)
        self.layout().addWidget(self.toolbar, 1, 0, 1, 1)

        self.fig.subplots_adjust(left=0.08, right=0.90, bottom=0.1, top=0.9,
                                 wspace=0.3, hspace=0.35)

        # self.fig.suptitle('ETS plugin')
        self.grid_subp = matplotlib.gridspec.GridSpec(2, 3)
        self.ax1 = self.fig.add_subplot(self.grid_subp[0, 0])
        self.ax2 = self.fig.add_subplot(self.grid_subp[0, 1])
        self.ax3 = self.fig.add_subplot(self.grid_subp[0, 2])
        self.ax3_2 = self.ax3.twinx()
        self.ax4 = self.fig.add_subplot(self.grid_subp[1, 0])
        self.ax5 = self.fig.add_subplot(self.grid_subp[1, 1])
        self.ax6 = self.fig.add_subplot(self.grid_subp[1, 2])
        self.ax6_2 = self.ax6.twinx()

        self.parent.writeLogDebug(self, inspect.currentframe(), "END")

    def plot(self):
        """Main plot function.
        """
        self.parent.writeLogDebug(self, inspect.currentframe(), "START")

        # Update slider tmin and tmax values
        self.parent.updateTimeSliderTminTmaxLabel()
        # self.nslices2plot = 1

        try:

            # Core profiles
            self.cp_1d = self.ids.core_profiles.profiles_1d[self.it]
            # Core transport
            self.ct_1d = self.ids.core_transport.model[0].profiles_1d[self.it]
            # Core Sources
            self.cs_1d = self.ids.core_sources.source[0].profiles_1d[self.it]

            # Re-plot j_Oh
            self.plot_j_Oh()
            # Re-plot Vloop
            self.plot_Vloop()
            # Plot pressure
            self.plot_pressure()
            # Plot E_parallel.
            self.plot_E_parallel()
            # Plot B_pol
            self.plot_B_pol()
            # Plot Psi
            self.plot_psi()

        except Exception as err:
            self.log.error("ERROR occurred in tabMain1DParam plot. "
                           "(%s)" % err, exc_info=True)

        self.show()

        self.parent.writeLogDebug(self, inspect.currentframe(), "END")

    def plotUpdate(self, time_index):
        """Update plot data (X and Y data) and replot.
        """

        self.parent.writeLogDebug(self, inspect.currentframe(), "START")

        # Update time value
        self.it = self.checkTimeIndex(time_index)

        self.cp_1d = self.ids.core_profiles.profiles_1d[self.it]
        self.ct_1d = self.ids.core_transport.model[0].profiles_1d[self.it]
        self.cs_1d = self.ids.core_sources.source[0].profiles_1d[self.it]

        # Plot update: _Oh
        self.plotUpdate_j_Oh()
        # Plot update: Vloop
        self.plotUpdate_Vloop()
        # Plot update: pressure
        self.plotUpdate_pressure()
        # Plot update: E_parallel.
        self.plotUpdate_E_parallel()
        # Plot update: B_pol
        self.plotUpdate_B_pol()
        # Plot update: sources
        self.plotUpdate_psi()

        # Update the figure display
        self.canvas.draw()
        # self.canvas.flush_events()

        self.parent.writeLogDebug(self, inspect.currentframe(), "END")

    def plot_j_Oh(self):
        """Plot j_Oh
        """

        self.parent.writeLogDebug(self, inspect.currentframe(), "START")

        # Clear plot first
        self.ax1.cla()

        try:
            rho_tor_norm = self.cp_1d.grid.rho_tor_norm
            j_Oh = self.cp_1d.j_ohmic
            self.ax1.set_xlim(0, max(rho_tor_norm))
            self.lines_j_Oh = [0]*self.nslices2plot
            self.lines_j_Oh[0], = self.ax1.plot(rho_tor_norm, 1.0e-6*j_Oh,
                                                label="j_Oh", color='#ff0033',
                                                linewidth=1.5)

            self.parent.writeLogDebug(self, inspect.currentframe(),
                                      f"len(self.lines_j_Oh): "
                                      f"{len(self.lines_j_Oh)}")
            j = 1
            for ii in range(-2, -self.nslices2plot-1, -1):
                i = self.it + ii + 1
                rho_tor_norm = \
                    self.ids.core_profiles.profiles_1d[i].grid.rho_tor_norm
                j_Oh = self.ids.core_profiles.profiles_1d[i].j_ohmic
                self.lines_j_Oh[j], = \
                    self.ax1.plot(rho_tor_norm, 1.0e-6*j_Oh, '--',
                                  label=f"j_Oh slice {i}", color='#ff0033',
                                  linewidth=0.5)
                j += 1

            self.ax1.set_title('j_Oh [MA/m^2]', fontsize=12, ha='center',
                               color='DarkBlue')
            self.ax1.set(xlabel="rho_tor_norm [-]")
            self.ax1.grid()
            leg = self.ax1.legend()
            leg.set_draggable(True)

        except Exception as err:
            self.log.error("ERROR occurred when plotting j_Oh. (%s)"
                           % err, exc_info=True)

        self.parent.writeLogDebug(self, inspect.currentframe(), "END")

    def plotUpdate_j_Oh(self):
        """Update plot: j_Oh
        """

        self.parent.writeLogDebug(self, inspect.currentframe(), "START")

        try:
            rho_tor_norm = self.cp_1d.grid.rho_tor_norm
            j_Oh = self.cp_1d.j_ohmic

            self.lines_j_Oh[0].set_xdata(rho_tor_norm)
            self.lines_j_Oh[0].set_ydata(1.0e-6*j_Oh)

            self.parent.writeLogDebug(self, inspect.currentframe(),
                                      f"len(self.lines_j_Oh): "
                                      f"{len(self.lines_j_Oh)}")
            self.parent.writeLogDebug(self, inspect.currentframe(),
                                      f"self.lines_j_Oh: "
                                      f"{self.lines_j_Oh}")
            j = 1
            for ii in range(-2, -self.nslices2plot-1, -1):
                i = self.it + ii + 1
                rho_tor_norm = \
                    self.ids.core_profiles.profiles_1d[i].grid.rho_tor_norm
                j_Oh = self.ids.core_profiles.profiles_1d[i].j_ohmic
                self.lines_j_Oh[j].set_xdata(rho_tor_norm)
                self.lines_j_Oh[j].set_ydata(1.0e-6*j_Oh)
                self.lines_j_Oh[j].set_label(f"j_Oh slice {i}")

                j += 1

        except Exception as err:
            self.log.error("ERROR occurred when re-plotting J_Oh. (%s)"
                           % err, exc_info=True)

        self.parent.writeLogDebug(self, inspect.currentframe(), "END")

    def plot_Vloop(self):
        """Plot Vloop
        """

        self.parent.writeLogDebug(self, inspect.currentframe(), "START")

        # Clear plot first
        self.ax2.cla()

        try:
            rho_tor_norm = self.cp_1d.grid.rho_tor_norm
            # ne = self.cp_1d.electrons.density
            # self.line_ne, = self.ax2.plot(rho_tor_norm, 1.0e-19*ne,
            #                               label="Ne",
            #                               color='r',
            #                               linewidth=1.5)
            # self.line_ni = [0]*len(self.cp_1d.ion)
            # for i in range(len(self.cp_1d.ion)):
            #     ni = self.cp_1d.ion[i].density
            #     if self.cp_1d.ion[i].multiple_states_flag == 0:
            #         self.line_ni[i], = \
            #             self.ax2.plot(rho_tor_norm,
            #                           1.0e-19*ni,
            #                           label='Ni %d' % (i+1),
            #                           color=self.ion_colors[
            #                               min(i, len(self.ion_colors)-1)],
            #                           linewidth=1.5)

            # self.ax2.set(xlabel="rho_tor_norm [-]", title='Density [10^19 m-3]')
            # # self.ax2.set_yticks([])
            # self.ax2.xaxis.set_minor_locator(
            #     ticker.AutoMinorLocator(self._nminor_interval))
            # self.ax2.yaxis.set_minor_locator(
            #     ticker.AutoMinorLocator(self._nminor_interval))
            # self.ax2.grid()
            # leg = self.ax2.legend()
            # leg.set_draggable(True)

        except Exception as err:
            self.log.error("ERROR occurred when plotting Vloop. (%s)"
                           % err, exc_info=True)

        self.parent.writeLogDebug(self, inspect.currentframe(), "END")

    def plotUpdate_Vloop(self):
        """Plot update: Vloop
        """

        self.parent.writeLogDebug(self, inspect.currentframe(), "START")

        try:
            rho_tor_norm = self.cp_1d.grid.rho_tor_norm
            # ne = self.cp_1d.electrons.density
            # self.line_ne.set_xdata(rho_tor_norm)
            # self.line_ne.set_ydata(1.0e-19*ne)

            # for i in range(len(self.cp_1d.ion)):
            #     ni = self.cp_1d.ion[i].density
            #     if self.cp_1d.ion[i].multiple_states_flag == 0:
            #         self.line_ni[i].set_xdata(rho_tor_norm)
            #         self.line_ni[i].set_ydata(1.0e-19*ni)

        except Exception as err:
            self.log.error("ERROR occurred when re-plotting Vloop. (%s)"
                           % err, exc_info=True)

        self.parent.writeLogDebug(self, inspect.currentframe(), "END")

    def plot_pressure(self):
        """Plot pressure
        """

        self.parent.writeLogDebug(self, inspect.currentframe(), "START")

        # Clear plot first
        self.ax3.cla()
        self.ax3_2.cla()

        try:
            rho_tor_norm = self.cp_1d.grid.rho_tor_norm
            # q = self.cp_1d.q
            # j_total = self.cp_1d.j_total
            # pl1 = self.ax3.plot(rho_tor_norm, 1.0e-6*abs(j_total),
            #                     label="j_total",
            #                     color='b',
            #                     linewidth=1.5)
            # self.line_jtotal = pl1[0]
            # self.ax3.tick_params(axis='y', colors='blue')
            # pl2 = self.ax3_2.plot(rho_tor_norm, abs(q),
            #                       label="q",
            #                       color='r',
            #                       linewidth=1.5)
            # self.line_q = pl2[0]
            # self.ax3_2.tick_params(axis='y', colors='red')

            # # Combine legend of the both plots into a single legend box
            # pl = pl1 + pl2
            # labs = [l.get_label() for l in pl]
            # leg = self.ax3_2.legend(pl, labs, loc=0)
            # leg.set_draggable(True)

            # sign_q = ' '
            # sign_jtot = ' '
            # if q[0]/abs(q[0]) == -1:
            #     sign_q = '-'
            # if j_total[0]/abs(j_total[0]) == -1:
            #     sign_jtot = '-'

            # self.ax3.set(xlabel="rho_tor_norm [-]")
            # self.ax3.set_title('%cj_total [MA/m2]' % sign_jtot[0], color='b',
            #                    ha='right')
            # self.ax3_2.set(xlabel="rho_tor_norm [-]")
            # self.ax3_2.set_title(10*' '+'%cq [MA/m2]' % sign_q[0], color='r',
            #                      ha='left')
            # # self.ax3.set_yticks([])
            # self.ax3.xaxis.set_minor_locator(
            #     ticker.AutoMinorLocator(self._nminor_interval))
            # self.ax3.yaxis.set_minor_locator(
            #     ticker.AutoMinorLocator(self._nminor_interval))
            # self.ax3_2.yaxis.set_minor_locator(
            #     ticker.AutoMinorLocator(self._nminor_interval))
            # self.ax3.grid(color="Blue")
            # self.ax3_2.grid(color="Red")

        except Exception as err:
            self.log.error("ERROR occurred when plotting pressure. "
                           "(%s)" % err, exc_info=True)

        self.parent.writeLogDebug(self, inspect.currentframe(), "END")

    def plotUpdate_pressure(self):
        """Plot update: pressure
        """

        self.parent.writeLogDebug(self, inspect.currentframe(), "START")

        try:
            rho_tor_norm = self.cp_1d.grid.rho_tor_norm
            # q = self.cp_1d.q
            # j_total = self.cp_1d.j_total
            # self.line_jtotal.set_xdata(rho_tor_norm)
            # self.line_jtotal.set_ydata(1.0e-6*abs(j_total))
            # self.line_q.set_xdata(rho_tor_norm)
            # self.line_q.set_ydata(abs(q))

        except Exception as err:
            self.log.error("ERROR occurred when re-plotting pressure. "
                           "(%s)" % err, exc_info=True)

        self.parent.writeLogDebug(self, inspect.currentframe(), "END")

    def plot_E_parallel(self):
        """Plot E_parallel.
        """

        self.parent.writeLogDebug(self, inspect.currentframe(), "START")

        # Clear plot first
        self.ax4.cla()

        try:
            rho_tor_norm = self.cp_1d.grid.rho_tor_norm
            # zeff = self.cp_1d.zeff
            # self.ax4.set_xlim(0, max(rho_tor_norm))
            # self.ax4.set_ylim(1, max(zeff)*1.05)
            # self.line_zeff, = self.ax4.plot(rho_tor_norm, zeff,
            #                                 label="zeff",
            #                                 color='b',
            #                                 linewidth=1.5)
            # self.ax4.tick_params(axis='y', colors='blue')
            # self.ax4.set(xlabel="rho_tor_norm [-]", title='Zeff [-]')
            # # self.ax4.set_yticks([])
            # self.ax4.yaxis.set_major_formatter(pylab.NullFormatter())
            # self.ax4.xaxis.set_minor_locator(
            #     ticker.AutoMinorLocator(self._nminor_interval))
            # self.ax4.yaxis.set_minor_locator(
            #     ticker.AutoMinorLocator(self._nminor_interval))
            # self.ax4.grid()
            # leg = self.ax4.legend()
            # leg.set_draggable(True)

        except Exception as err:
            self.log.error("ERROR occurred when plotting E_parallel. (%s)"
                           % err, exc_info=True)

        self.parent.writeLogDebug(self, inspect.currentframe(), "END")

    def plotUpdate_E_parallel(self):
        """Plot update: E_parallel.
        """

        self.parent.writeLogDebug(self, inspect.currentframe(), "START")

        try:
            rho_tor_norm = self.cp_1d.grid.rho_tor_norm
            # zeff = self.cp_1d.zeff
            # self.ax4.set_xlim(0, max(rho_tor_norm))
            # self.ax4.set_ylim(1, max(zeff)*1.05)
            # self.line_zeff.set_xdata(rho_tor_norm)
            # self.line_zeff.set_ydata(zeff)

        except Exception as err:
            self.log.error("ERROR occurred when re-plotting E_parallel. (%s)"
                           % err, exc_info=True)

        self.parent.writeLogDebug(self, inspect.currentframe(), "END")

    def plot_B_pol(self):
        """Plot B_pol.
        """

        self.parent.writeLogDebug(self, inspect.currentframe(), "START")

        # Clear plot
        self.ax5.cla()

        try:
            # rho_tor_norm = self.cp_1d.grid.rho_tor_norm
            rho_tor_norm = self.ct_1d.grid_d.rho_tor_norm
            # diff_te = self.ct_1d.electrons.energy.d
            # # diff_ti = self.ct_1d.total_ion_energy.d
            # self.ax5.set_xlim(0, max(rho_tor_norm))
            # self.line_diff_te, = self.ax5.plot(rho_tor_norm, diff_te,
            #                                    color='r', linewidth=1.5)

            # self.line_diff_ti = [0]*len(self.ct_1d.ion)
            # self.line_diff_ni = [0]*len(self.ct_1d.ion)

            # for i in range(len(self.ct_1d.ion)):
            #     diff_ti = self.ct_1d.ion[i].energy.d
            #     diff_ni = self.ct_1d.ion[i].particles.d

            #     self.line_diff_ti[i], = \
            #         self.ax5.plot(rho_tor_norm, diff_ti, label="diff_ti",
            #                       color=self.ion_colors[
            #                           min(i, len(self.ion_colors)-1)],
            #                       linewidth=1.5)
            #     self.line_diff_ni[i], = \
            #         self.ax5.plot(rho_tor_norm, diff_ni, label="diff_ni",
            #                       color=self.ion_ni_colors[
            #                           min(i, len(self.ion_ni_colors)-1)],
            #                       linewidth=1.5)

            # self.ax5.set_title('diff [m^2/s]')
            # self.ax5.set_xlabel('rho_tor_norm [-]')
            # # self.ax5.xaxis.set_major_formatter(pylab.NullFormatter())
            # self.ax5.yaxis.set_major_formatter(pylab.NullFormatter())
            # self.ax5.set_yticks([])
            # self.ax5.grid()
            # self.ax5.xaxis.set_minor_locator(ticker.AutoMinorLocator(
            #                                  self._nminor_interval))
            # self.ax5.yaxis.set_minor_locator(ticker.AutoMinorLocator(
            #                                  self._nminor_interval))
            # # self.ax5.yaxis.set_minor_locator(ticker.AutoMinorLocator(
            # #                                  self._nminor_interval))
            # leg = self.ax5.legend()
            # leg.set_draggable(True)

        except Exception as err:
            self.log.error("ERROR occurred when plotting B_pol. "
                           "(%s)" % err, exc_info=True)

        self.parent.writeLogDebug(self, inspect.currentframe(), "END")

    def plotUpdate_B_pol(self):
        """Plot Update: B_pol.
        """

        self.parent.writeLogDebug(self, inspect.currentframe(), "START")

        try:
            # rho_tor_norm = self.cp_1d.grid.rho_tor_norm
            rho_tor_norm = self.ct_1d.grid_d.rho_tor_norm
            # diff_te = self.ct_1d.electrons.energy.d
            # # diff_ti = self.ct_1d.total_ion_energy.d
            # self.ax5.set_xlim(0, max(rho_tor_norm))
            # self.line_diff_te.set_ydata(rho_tor_norm)
            # self.line_diff_te.set_xdata(diff_te)

            # for i in range(len(self.ct_1d.ion)):
            #     diff_ti = self.ct_1d.ion[i].energy.d
            #     diff_ni = self.ct_1d.ion[i].particles.d

            #     self.line_diff_ti[i].set_xdata(rho_tor_norm)
            #     self.line_diff_ti[i].set_ydata(diff_ti)

            #     self.line_diff_ni[i].set_xdata(rho_tor_norm)
            #     self.line_diff_ni[i].set_ydata(diff_ni)

        except Exception as err:
            self.log.error("ERROR occurred when re-plotting B_pol "
                           "(%s)" % err, exc_info=True)

        self.parent.writeLogDebug(self, inspect.currentframe(), "END")

    def plot_psi(self):
        """Plot Psi.
        """

        self.parent.writeLogDebug(self, inspect.currentframe(), "START")

        # Clear plot
        self.ax6.cla()

        try:
            rho_tor_norm = self.cs_1d.grid.rho_tor_norm
            # sour_te = self.cs_1d.electrons.energy
            # sour_ti_tot = self.cs_1d.total_ion_energy
            # sour_ni0 = self.cs_1d.ion[0].particles

            # self.ax6_2.set_ylim(-1, 1)

            # self.ax6.set_xlim(0, max(rho_tor_norm))
            # norm = abs(max(1, max(sour_te), max(sour_ti_tot),
            #            -min(sour_te), -min(sour_ti_tot)))
            # pl1 = self.ax6.plot(rho_tor_norm, sour_te/norm,
            #                     label="sour_te/norm",
            #                     color='r',
            #                     linewidth=1.5)
            # self.line_sour_te = pl1[0]
            # norm1 = abs(max(1, max(sour_ni0), -min(sour_ni0)))

            # self.line_sour_ti = [0]*len(self.ct_1d.ion)
            # self.line_sour_ni = [0]*len(self.ct_1d.ion)
            # for i in range(len(self.ct_1d.ion)):
            #     sour_ti = self.cs_1d.ion[i].energy
            #     sour_ni = self.cs_1d.ion[i].particles

            #     norm = abs(max(norm, max(sour_ti), -min(sour_ti)))
            #     norm1 = abs(max(norm1, max(sour_ni), -min(sour_ni)))

            #     pl2 = self.ax6.plot(rho_tor_norm, sour_ti/norm,
            #                         label="sour_ti/norm",
            #                         color=self.ion_colors[
            #                             min(i, len(self.ion_colors)-1)],
            #                         linewidth=1.5)
            #     self.line_sour_ti[i] = pl2[0]
            #     pl3 = self.ax6.plot(rho_tor_norm, sour_ni/norm1,
            #                         label="sour_ni/norm",
            #                         color=self.ion_ni_colors[
            #                             min(i, len(self.ion_ni_colors)-1)],
            #                         linewidth=1.5)
            #     self.line_sour_ni[i] = pl3[0]

            # self.ax6_2.axhline(y=0, linewidth=0.3)

            # self.ax6.set_title(' '*10+'q [kW.m-3]', color='g', ha='left', )
            # self.ax6.set_xlabel('rho_tor_norm [-]')
            # self.ax6_2.set_title("s [m-3 s-1]", ha='right')
            # self.ax6.grid()
            # self.ax6.xaxis.set_minor_locator(ticker.AutoMinorLocator(
            #                                  self._nminor_interval))
            # self.ax6.yaxis.set_minor_locator(ticker.AutoMinorLocator(
            #                                  self._nminor_interval))
            # self.ax6_2.yaxis.set_minor_locator(ticker.AutoMinorLocator(
            #                                    self._nminor_interval))
            # # Combine legend of the both plots into a single legend box
            # pl = pl1 + pl2 + pl3
            # labs = [l.get_label() for l in pl]
            # leg = self.ax6_2.legend(pl, labs, loc=0)
            # leg.set_draggable(True)

        except Exception as err:
            self.log.error("ERROR occurred when plotting Psi. "
                           "(%s)" % err, exc_info=True)

        self.parent.writeLogDebug(self, inspect.currentframe(), "END")

    def plotUpdate_psi(self):
        """Plot Update: Sources.
        """

        self.parent.writeLogDebug(self, inspect.currentframe(), "START")

        try:
            rho_tor_norm = self.cs_1d.grid.rho_tor_norm
            # sour_te = self.cs_1d.electrons.energy
            # sour_ti_tot = self.cs_1d.total_ion_energy
            # sour_ni0 = self.cs_1d.ion[0].particles

            # self.ax6.set_xlim(0, max(rho_tor_norm))
            # norm = abs(max(1, max(sour_te), max(sour_ti_tot),
            #            -min(sour_te), -min(sour_ti_tot)))
            # self.line_sour_te.set_xdata(rho_tor_norm)
            # self.line_sour_te.set_ydata(sour_te/norm)

            # norm1 = abs(max(1, max(sour_ni0), -min(sour_ni0)))

            # for i in range(len(self.ct_1d.ion)):
            #     sour_ti = self.cs_1d.ion[i].energy
            #     sour_ni = self.cs_1d.ion[i].particles

            #     norm = abs(max(norm, max(sour_ti), -min(sour_ti)))
            #     norm1 = abs(max(norm1, max(sour_ni), -min(sour_ni)))

            #     self.line_sour_ti[i].set_xdata(rho_tor_norm)
            #     self.line_sour_ti[i].set_ydata(sour_ti/norm)

            #     self.line_sour_ni[i].set_xdata(rho_tor_norm)
            #     self.line_sour_ni[i].set_ydata(sour_ti/norm)

        except Exception as err:
            self.log.error("ERROR occurred when re-plotting Psi. "
                           "(%s)" % err, exc_info=True)

        self.parent.writeLogDebug(self, inspect.currentframe(), "END")

    def checkTimeIndex(self, time_index):
        """Check if the given time index is legal, otherwise return default.
        """

        if time_index > len(self.ids.core_profiles.profiles_1d)-1:
            new_time_index = 0
        else:
            new_time_index = time_index

        return time_index
