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

def element(zn, am):
    import re
    import numpy as np
    elStr = ("HHeLiBeBCNOFNeNaMgAlSiPSClArKCaScTiVCrMnFeCoNiCuZnGaGeAsSeBrKrRb"
             "SrYZrNbMoTcRuRhPdAgCdInSnSbTeIXeCsBaLaCePrNdPmSmEuGdTbDyHoErTmYb"
             "LuHfTaWReOsIrPtAuHgTlPbBiPoAtRnFrRaAcThPaUNpPuAmCmBkCfEsFmMdNoLr"
             "RfDbSgBhHsMtDsRgCnNhFlMcLvTsOg")
    elements = np.array(re .compile ("[A-Z][a-z]*").findall(elStr))
    return '%i-%s' % (int(am), elements[int(zn)-1])

class tabETSSummary(QWidget):

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)

        self.parent = parent
        # Get/set IDS
        if self.parent.ids == None:
            self.parent.setIDS()
        self.ids  = self.parent.ids

        # Get log parser
        self.log = self.parent.getLogger()

        self.log.debug(f"DEBUG | {type(self).__name__} | __init__() | START.")

        # Set tab user interface
        self.setTabUI()

        # Set list of colors for plots
        self.ion_colors = ['DarkBlue','Purple', 'RoyalBlue','Magenta',
                           'Tomato', 'LimeGreen',  'DarkCyan']
        self.ion_ni_colors = ['DarkGreen','Olive',  'Orange', 'darkgoldenrod',
                              'peru', 'indianred', 'amber']
        # Ticker minor interval
        self._nminor_interval = 4

        # Set initial time slice
        self.it = 0

        self.log.debug(f"DEBUG | {type(self).__name__} | __init__() | END.")

    def setTabUI(self):
        """Set tab user interface.
        """

        self.log.debug(f"DEBUG | {type(self).__name__} | setTabUI() | START.")

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
        self.ax6_2 = self.ax6.twinx()

        self.log.debug(f"DEBUG | {type(self).__name__} | setTabUI() | END.")

    def plot(self):
        """Main plot function.
        """

        self.log.debug(f"DEBUG | {type(self).__name__} | plot() | START.")

        nslices = len(self.ids.core_profiles.profiles_1d)
        self.nslices2plot = 1

        # Core profiles
        self.cp_1d = self.ids.core_profiles.profiles_1d[self.it]
        # Core transport
        self.ct_1d = self.ids.core_transport.model[0].profiles_1d[self.it]
        # Core Sources
        self.cs_1d = self.ids.core_sources.source[0].profiles_1d[self.it]

        # Re-plot te/ti (electron/ion temperature)
        self.plot_te_ti()
        # Re-plot ne/ni (electron/ion density)
        self.plot_ne_ni()
        # Plot j_total and q (total parallel current density and safety factor)
        self.plot_jtotal_q()
        # Plot zeff profile.
        self.plot_zeff()
        # Plot transport coefficients
        self.plot_transport_coeff()
        # Plot sources
        self.plot_sources()

        # Add text beside plots
        self.main_discharge_parameters()

        self.show()

        self.log.debug(f"DEBUG | {type(self).__name__} | plot() | END.")

    def plotUpdate(self, time_index):
        """Clear and re-plot.
        """

        self.log.debug(f"DEBUG | {type(self).__name__} | plotUpdate() | START.")

        # Update time value
        self.it = time_index

        self.cp_1d = self.ids.core_profiles.profiles_1d[self.it]
        self.ct_1d = self.ids.core_transport.model[0].profiles_1d[self.it]
        self.cs_1d = self.ids.core_sources.source[0].profiles_1d[self.it]

        # Re-plot te/ti (electron/ion temperature)
        self.plot_te_ti()
        # Re-plot ne/ni (electron/ion density)
        self.plot_ne_ni()
        # Plot j_total and q (total parallel current density and safety factor)
        self.plot_jtotal_q()
        # Plot zeff profile.
        self.plot_zeff()
        # Plot transport coefficients
        self.plot_transport_coeff()
        # Plot sources
        self.plot_sources()

        # Add text beside plots
        self.main_discharge_parameters()

        # Update the figure display
        self.canvas.draw()
        self.canvas.flush_events()

        self.log.debug(f"DEBUG | {type(self).__name__} | plotUpdate() | END.")

    def plot_te_ti(self):
        """Plot electron temperature (te) and ion temperature (ti)
        """

        self.log.debug(f"DEBUG | {type(self).__name__} | plot_te_ti() | START.")

        # Clear plot first
        self.ax1.cla()

        try:
            rhotor = self.cp_1d.grid.rho_tor_norm
            te = self.cp_1d.electrons.temperature
            self.ax1.plot(rhotor, 1.0e-3*te,
                          label = "Te",
                          color='r',
                          linewidth=1.5)
            for i in range(len(self.cp_1d.ion)):
                ti = self.cp_1d.ion[i].temperature
                if self.cp_1d.ion[i].multiple_states_flag == 0 :
                    self.ax1.plot(rhotor,
                                  1.0e-3*self.cp_1d.ion[i].temperature,
                                  label='Ti %d'%(i+1),
                                  color=self.ion_colors[min(i,len(self.ion_colors)-1)],
                                  linewidth=1.5)

        except Exception as err:
            self.log.error( 'ERROR occurred when plotting temperatures. (%s) ' % err )

        self.ax1.set(xlabel= "rhotor [m]", ylabel='Temperature [keV]')
        # self.ax1.set_yticks([])
        self.ax1.xaxis.set_minor_locator(
            ticker.AutoMinorLocator(self._nminor_interval))
        self.ax1.yaxis.set_minor_locator(
            ticker.AutoMinorLocator(self._nminor_interval))
        self.ax1.grid()
        leg = self.ax1.legend()
        leg.set_draggable(True)

        self.log.debug(f"DEBUG | {type(self).__name__} | plot_te_ti() | END.")

    def plot_ne_ni(self):
        """Plot electron density (te) and ion density (ti)
        """

        self.log.debug(f"DEBUG | {type(self).__name__} | plot_ne_ni() | START.")

        # Clear plot first
        self.ax2.cla()

        try:
            rhotor = self.cp_1d.grid.rho_tor_norm
            ne = self.cp_1d.electrons.density
            self.ax2.plot(rhotor, 1.0e-19*ne,
                          label = "Ne",
                          color='r',
                          linewidth=1.5)
            for i in range(len(self.cp_1d.ion)):
                ni = self.cp_1d.ion[i].density
                if self.cp_1d.ion[i].multiple_states_flag == 0 :
                    self.ax2.plot(rhotor,
                                  1.0e-19*self.cp_1d.ion[i].density,
                                  label='Ni %d'%(i+1),
                                  color=self.ion_colors[min(i,len(self.ion_colors)-1)],
                                  linewidth=1.5)

        except Exception as err:
            self.log.error( 'ERROR occurred when plotting densities. (%s) ' % err )

        self.ax2.set(xlabel= "rhotor [m]", ylabel='Density [10^19 m-3]')
        # self.ax2.set_yticks([])
        self.ax2.xaxis.set_minor_locator(
            ticker.AutoMinorLocator(self._nminor_interval))
        self.ax2.yaxis.set_minor_locator(
            ticker.AutoMinorLocator(self._nminor_interval))
        self.ax2.grid()
        leg = self.ax2.legend()
        leg.set_draggable(True)

        self.log.debug(f"DEBUG | {type(self).__name__} | plot_ne_ni() | END.")

    def plot_jtotal_q(self):
        """Plot total parallel current density (j_total) and safety factor (q).
        """

        self.log.debug(f"DEBUG | {type(self).__name__} | plot_jtotal_q() | START.")

        # Clear plot first
        self.ax3.cla()
        self.ax3_2.cla()

        try:
            rhotor = self.cp_1d.grid.rho_tor_norm
            q = self.cp_1d.q
            j_total = self.cp_1d.j_total
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
            self.log.error('ERROR occurred when plotting equilibrium related profiles. (%s) ' % err )


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

        self.log.debug(f"DEBUG | {type(self).__name__} | plot_jtotal_q() | END.")

    def plot_zeff(self):
        """Plot zeff profile.
        """

        self.log.debug(f"DEBUG | {type(self).__name__} | plot_zeff() | START.")

        # Clear plot first
        self.ax4.cla()

        try:
            rhotor = self.cp_1d.grid.rho_tor_norm
            zeff = self.cp_1d.zeff
            self.ax4.set_xlim(0, max(rhotor))
            self.ax4.set_ylim(1, max(zeff)*1.05)
            self.ax4.plot(rhotor, zeff,
                          label = "zeff",
                          color='b',
                          linewidth=1.5)
            self.ax4.tick_params(axis='y', colors='blue')

        except Exception as err:
            self.log.error( 'ERROR occurred when plotting Zeff profile. (%s) ' % err )

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

        self.log.debug(f"DEBUG | {type(self).__name__} | plot_zeff() | END.")

    def plot_transport_coeff(self):
        """Plot Transport Coefficients.
        """

        self.log.debug(f"DEBUG | {type(self).__name__} | plot_transport_coeff() | START.")

        # Clear plot
        self.ax5.cla()

        try:
            # rhotor = self.cp_1d.grid.rho_tor_norm
            rhotor = self.ct_1d.grid_d.rho_tor_norm
            diff_te = self.ct_1d.electrons.energy.d
            # diff_ti = self.ct_1d.total_ion_energy.d
            self.ax5.set_xlim(0, max(rhotor))
            self.ax5.plot(rhotor, diff_te,color='r', linewidth=1.5)

            for i in range(len(self.ct_1d.ion)):
                diff_ti = self.ct_1d.ion[i].energy.d
                diff_ni = self.ct_1d.ion[i].particles.d

                self.ax5.plot(rhotor, diff_ti,
                                label = "diff_ti",
                                color=self.ion_colors[min(i,len(self.ion_colors)-1)],
                                linewidth=1.5)
                self.ax5.plot(rhotor, diff_ni,
                                label = "diff_ni",
                                color=self.ion_ni_colors[min(i,len(self.ion_ni_colors)-1)],
                                linewidth=1.5)

        except Exception as err:
            self.log.error( 'ERROR occurred when plotting Transport coefficients. (%s) ' % err )

        self.ax5.set_ylabel('diff [m^2/s]')
        self.ax5.set_xlabel('rhotor [m]')
        #self.ax5.xaxis.set_major_formatter(pylab.NullFormatter())
        self.ax5.yaxis.set_major_formatter(pylab.NullFormatter())
        self.ax5.set_yticks([])
        self.ax5.grid()
        self.ax5.xaxis.set_minor_locator(ticker.AutoMinorLocator(self._nminor_interval))
        self.ax5.yaxis.set_minor_locator(ticker.AutoMinorLocator(self._nminor_interval))
        #self.ax5.yaxis.set_minor_locator(ticker.AutoMinorLocator(self._nminor_interval))
        leg = self.ax5.legend()
        leg.set_draggable(True)

        self.log.debug(f"DEBUG | {type(self).__name__} | plot_transport_coeff() | END.")

    def plot_sources(self):
        """Plot Sources.
        """

        self.log.debug(f"DEBUG | {type(self).__name__} | plot_sources() | START.")

        # Clear plot
        self.ax6.cla()

        try:
            rhotor = self.cs_1d.grid.rho_tor_norm
            sour_te = self.cs_1d.electrons.energy
            sour_ti_tot = self.cs_1d.total_ion_energy
            sour_ni0 = self.cs_1d.ion[0].particles

            self.ax6_2.set_ylim(-1,1)

            self.ax6.set_xlim(0, max(rhotor))
            norm = abs(max(1,max(sour_te),max(sour_ti_tot),-min(sour_te),-min(sour_ti_tot)))
            pl1 = self.ax6.plot(rhotor, sour_te/norm, color='r', linewidth=1.5)
            norm1 = abs(max(1,max(sour_ni0),-min(sour_ni0)))

            for i in range(len(self.ct_1d.ion)):
                sour_ti = self.cs_1d.ion[i].energy
                sour_ni = self.cs_1d.ion[i].particles

                norm = abs(max(norm,max(sour_ti),-min(sour_ti)))
                norm1 = abs(max(norm1,max(sour_ni),-min(sour_ni)))

                pl1 = self.ax6.plot(rhotor, sour_ti/norm,
                                label = "sour_ti/norm",
                                color=self.ion_colors[min(i,len(self.ion_colors)-1)],
                                linewidth=1.5)
                pl2 = self.ax6.plot(rhotor, sour_ni/norm1,
                                label = "sour_ni/norm",
                                color=self.ion_ni_colors[min(i,len(self.ion_ni_colors)-1)],
                                linewidth=1.5)

        except Exception as err:
            self.log.error( 'ERROR occurred when plotting source related profiles. (%s) ' % err )

        self.ax6_2.axhline(y=0, linewidth=0.3)

        self.ax6.set_ylabel('q [kW.m-3]')
        self.ax6.set_xlabel('rhotor [m]')
        self.ax6_2.set_ylabel(" s [m-3 s-1]")
        self.ax6.grid()
        self.ax6.xaxis.set_minor_locator(ticker.AutoMinorLocator(self._nminor_interval))
        self.ax6.yaxis.set_minor_locator(ticker.AutoMinorLocator(self._nminor_interval))
        self.ax6_2.yaxis.set_minor_locator(ticker.AutoMinorLocator(self._nminor_interval))
        # Combine legend of the both plots into a single legend box
        pl = pl1 + pl2
        labs = [l.get_label() for l in pl]
        leg = self.ax6_2.legend(pl, labs, loc=0)
        leg.set_draggable(True)

        self.log.debug(f"DEBUG | {type(self).__name__} | plot_sources() | END.")

    def main_discharge_parameters(self):
        """Display Main discharge parameters.
        """

        self.log.debug(f"DEBUG | {type(self).__name__} | main_discharge_parameters() | START.")

        xtext  = 0.80
        xtext1 = 0.82
        xtext2 = 0.83
        ytext  = 0.87
        ystep  = 0.03

        # Clear plot text to avoid text stacking one over the previous one
        for t in self.fig.texts:
            t.set_text("")

        try:
            # Get vacuum toroidal field at R0 (R0 = major radius)
            b0 = self.ids.core_profiles.vacuum_toroidal_field.b0[self.it]
            # Get total toroidal plasma current
            ip = self.ids.core_profiles.global_quantities.ip[self.it]

            # Note: In ETSviz the total toroidal plasma current gets read from
            #       the Equilibrium IDS. Possible IDS equivalent path:
            # ip = self.equilibrium.time_slice[self.it].global_quantities.ip

            self.fig.text(xtext,ytext,'Main discharge parameters: %f' % float(b0),
                        color='black',fontsize=11, weight='bold')
            ytext = ytext - ystep
            self.fig.text(xtext1,ytext,'BT =  %6.4f [T]' % float(b0),
                        color='black',fontsize=10, weight='bold')
            ytext = ytext - ystep
            self.fig.text(xtext1,ytext,'IP =  %6.4f [MA]' % float(ip/1.e6),
                        color='black',fontsize=10, weight='bold')
            ytext = ytext - ystep*2.0
        except Exception as err:
            self.log.error('ERROR: in Main discharge parameters  (%s)' % err)

        try:
            cp_1d = self.ids.core_profiles.profiles_1d[self.it]
            # Number of ions
            NION = len(cp_1d.ion)

            for iion in range(NION):

                self.log.debug(f"DEBUG: len(core_profiles[{self.it}].ion[{iion}].element): "
                    f"{len(cp_1d.ion[iion].element)}")
                # Atomic mass number
                amn = cp_1d.ion[iion].element[0].a
                # Nuclear charge
                zn = cp_1d.ion[iion].element[0].z_n

                ytext = ytext-ystep
                self.fig.text(xtext1,ytext,"Ion_%d:" % int(iion+1),
                            color=self.ion_colors[min(iion,len(self.ion_colors)-1)],
                            fontsize=11, weight='bold')
                ytext   = ytext - ystep * 0.8
                # fig.text(xtext2,ytext,"amn = %d" % int(amn), color='black',
                #             fontsize=10, weight='bold')
                # ytext   = ytext - ystep * 0.8
                # fig.text(xtext2,ytext,"zn    = %d" % int(zn),color='black',
                            # fontsize=10, weight='bold')
                self.fig.text(xtext2, ytext, element(zn, amn), color='black',
                            fontsize=10, weight='bold')

            # Number of impurities
            # TODO
            # NIMP = ? # unknown where in IDSs this data resides
            # for iimp in range(NIMP):

            #     self.log.debug(f"DEBUG: len(core_profiles[{self.it}].ion[{iion}].element): "
            #         f"{len(cp_1d.ion[iion].element)}")
            #     nucind  = ? - 1 # unknown where in IDSs this data resides
            #     # Atomic mass number
            #     amn = cp_1d.ion[iion].element[0].a
            #     # Nuclear charge
            #     zn = cp_1d.ion[iion].element[0].z_n
            #     ytext   = ytext -ystep
            #     self.fig.text(xtext1,ytext,"Impurity_%d:" % int(iimp+1),
            #                     color='black',fontsize=11, weight='bold')
            #     ytext   = ytext - ystep * 0.8
            #     # self.fig.text(xtext2,ytext,"amn = %d" % int(amn), color='black',
            #     #                 fontsize=10, weight='bold')
            #     # ytext   = ytext - ystep * 0.8
            #     # self.fig.text(xtext2,ytext,"zn    = %d" % int(zn),color='black',
            #     #                 fontsize=10, weight='bold')
            #     self.fig.text(xtext2, ytext, element(zn, amn), color='black',
            #                     fontsize=10, weight='bold')

            ytext   = ytext - ystep
            self.fig.text(xtext1,ytext,"electrons", color='r',fontsize=10,
                            weight='bold')
            ytext   = ytext - ystep*2.0
            self.fig.text(xtext,ytext,"particle transport coefficients",
                            color='g',fontsize=10, weight='bold')
            ytext   = ytext - ystep*0.75
            self.fig.text(xtext,ytext,"and sources", color='g',fontsize=10,
                            weight='bold')
        except Exception as err:
            self.log.error('ERROR: in Main discharge parameters ions (%s)' % err,
                exc_info=True)

        self.fig.subplots_adjust(left=0.05, right=0.75, bottom=0.1, top=0.9)

        self.log.debug(f"DEBUG | {type(self).__name__} | main_discharge_parameters() | END.")

