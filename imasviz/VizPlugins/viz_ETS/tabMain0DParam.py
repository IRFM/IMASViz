#  Name   : tabMain0DParam
#
#           "Main 0-D parameters" tab for ETS plugin.
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


class tabMain0DParam(QWidget):

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

        self.parent.writeLogDebug(self, inspect.currentframe(), "END")

    def setTabUI(self):

        """Set tab user interface.
        """

        self.parent.writeLogDebug(self, inspect.currentframe(), "START")

        self.setLayout(QGridLayout())
        self.parent.tabWidget.addTab(self, "Main 0-D parameters")

        # Create the matplotlib Figure and FigCanvas objects.
        # 100 dots-per-inch
        self.dpi = 100
        self.fig = Figure(dpi=self.dpi)
        self.canvas = FigCanvas(self.fig)

        # Add canvas to tab widget
        self.layout().addWidget(self.canvas, 0, 0, 1, 1)

        self.parent.writeLogDebug(self, inspect.currentframe(), "END")

    def plot(self):
        """Main plot function.
        """

        self.parent.writeLogDebug(self, inspect.currentframe(), "START")

        # Get time index
        self.it = self.parent.getTimeIndex()
        # Get instance of Equilibrium IDS
        self.eq = self.parent.ids.equilibrium

        self.fig.clf()

        xtext1 = 0.05
        xtext2 = 0.40
        xtext3 = 0.70
        ytext1 = 0.90
        ytext2 = 0.90
        ytext3 = 0.90
        ystep = 0.03

        xtext11 = xtext1 + 0.01
        xtext21 = xtext2 + 0.01
        xtext31 = xtext3 + 0.01

        colormap = '#000066', '#660000', '#006666'

        # Titles:
        self.fig.text(xtext1, ytext1, 'EQUILIBRIUM:', color=colormap[0],
                      fontsize=14, weight='bold')
        self.fig.text(xtext2, ytext2, 'PLASMA:', color=colormap[1],
                      fontsize=14, weight='bold')
        self.fig.text(xtext3, ytext3, 'SOURCES&SINKS:', color=colormap[2],
                      fontsize=14, weight='bold')

        # Equilibrium quantities:
        try:
            ytext1 = ytext1 - ystep
            # Note: In ETSviz (CPO) it was set:
            #       self.eq.array[self.it].datainfo.cocos
            #       In IDS: can't find it in Equilibrium IDS. Set as
            #       -999 for now
            self.fig.text(xtext11, ytext1,
                          'COCOS            =  %d' % (-999),
                          color=colormap[0], fontsize=12, weight='bold')
        except Exception as err:
            self.log.error("ERROR occurred when reading Equilibrium COCOS. (%s)"
                           % err, exc_info=True)
        try:
            ytext1 = ytext1 - ystep
            # Note: In ETSviz (CPO) it was set:
            #       self.eq.array[self.it].global_param.toroid_field.b0
            #       In IDS: can't find it in Equilibrium IDS. Set as
            #       self.ids_core_profiles.vacuum_toroidal_field.b0[self.it]
            #       for now
            self.fig.text(xtext11, ytext1,
                          'BT                   =  %6.4f [T]' %
                          (self.ids.core_profiles.vacuum_toroidal_field.b0[self.it]),
                          color=colormap[0], fontsize=12, weight='bold')
        except Exception as err:
            self.log.error("ERROR occurred when reading Equilibrium "
                           "BT. (%s)" % err, exc_info=True)
        try:
            ytext1 = ytext1 - ystep
            self.fig.text(xtext11, ytext1,
                          'VOLUME          =  %6.4f [m^3]' %
                          (self.eq.time_slice[self.it].global_quantities.volume),
                          color=colormap[0], fontsize=12, weight='bold')
        except Exception as err:
            self.log.error("ERROR occurred when reading Equilibrium "
                           "VOLUME. (%s)" % err, exc_info=True)

        try:
            ytext1 = ytext1 - ystep
            self.fig.text(xtext11, ytext1,
                          'AREA               =  %6.4f [m^2]' %
                          (self.eq.time_slice[self.it].global_quantities.area),
                          color=colormap[0], fontsize=12, weight='bold')
        except Exception as err:
            self.log.error("ERROR occurred when reading Equilibrium "
                           "AREA. (%s)" % err, exc_info=True)
        try:
            ytext1 = ytext1 - ystep
            self.fig.text(xtext11, ytext1,
                          'MAX_AX(R,Z)  =  (%6.4f,%6.4f) [m]' %
                          (self.eq.time_slice[
                                self.it].global_quantities.magnetic_axis.r,
                           self.eq.time_slice[
                                self.it].global_quantities.magnetic_axis.z),
                          color=colormap[0], fontsize=12, weight='bold')
        except Exception as err:
            self.log.error("ERROR occurred when reading Equilibrium "
                           "MAX_AX(R,Z). (%s)" % err, exc_info=True)
        try:
            ytext1 = ytext1 - ystep
            self.fig.text(xtext11, ytext1,
                          'A_min              =  %6.4f [m]' %
                          (self.eq.time_slice[self.it].boundary.minor_radius),
                          color=colormap[0], fontsize=12, weight='bold')
        except Exception as err:
            self.log.error("ERROR occurred when reading Equilibrium "
                           "A_min. (%s)" % err, exc_info=True)
        try:
            ytext1 = ytext1 - ystep
            self.fig.text(xtext11, ytext1,
                          'ELONG_UP       =  %6.4f [-]' %
                          (self.eq.time_slice[self.it].boundary.elongation_upper),
                          color=colormap[0], fontsize=12, weight='bold')
        except Exception as err:
            self.log.error("ERROR occurred when reading Equilibrium "
                           "ELONG_UP. (%s)" % err, exc_info=True)
        try:
            ytext1 = ytext1 - ystep
            self.fig.text(xtext11, ytext1,
                          'ELONG_LOW    =  %6.4f [-]' %
                          (self.eq.time_slice[self.it].boundary.elongation_lower),
                          color=colormap[0], fontsize=12, weight='bold')
        except Exception as err:
            self.log.error("ERROR occurred when reading Equilibrium "
                           "ELONG_LOW. (%s)" % err, exc_info=True)
        try:
            ytext1 = ytext1 - ystep
            self.fig.text(xtext11, ytext1,
                          'TRIA_UP          =  %6.4f [-]' %
                          (self.eq.time_slice[self.it].boundary.triangularity_upper ),
                          color=colormap[0], fontsize=12, weight='bold')
        except Exception as err:
            self.log.error("ERROR occurred when reading Equilibrium "
                           "TRIA_UP. (%s)" % err, exc_info=True)
        try:
            ytext1 = ytext1 - ystep
            self.fig.text(xtext11, ytext1,
                          'TRIA_LOW       =  %6.4f [-]' %
                          (self.eq.time_slice[self.it].boundary.triangularity_lower),
                          color=colormap[0], fontsize=12, weight='bold')
        except Exception as err:
            self.log.error("ERROR occurred when reading Equilibrium "
                           "TRIA_LOW. (%s)" % err, exc_info=True)
        try:
            ytext1 = ytext1 - ystep
            self.fig.text(xtext11, ytext1,
                          'PSI_AX            =  %6.4f [Wb]' %
                          (self.eq.time_slice[self.it].global_quantities.psi_axis),
                          color=colormap[0], fontsize=12, weight='bold')
        except Exception as err:
            self.log.error("ERROR occurred when reading Equilibrium "
                           "PSI_AX. (%s)" % err, exc_info=True)
        try:
            ytext1 = ytext1 - ystep
            self.fig.text(xtext11, ytext1,
                          'PSI_BND          =  %6.4f [Wb]' %
                          (self.eq.time_slice[self.it].global_quantities.psi_boundary),
                          color=colormap[0], fontsize=12, weight='bold')
        except Exception as err:
            self.log.error("ERROR occurred when reading Equilibrium "
                           "PSI_BND. (%s)" % err, exc_info=True)
        try:
            ytext1 = ytext1 - ystep
            self.fig.text(xtext11, ytext1,
                          'q_95                =  %6.4f [-]' %
                          (self.eq.time_slice[self.it].global_quantities.q_95),
                          color=colormap[0], fontsize=12, weight='bold')
        except Exception as err:
            self.log.error("ERROR occurred when reading Equilibrium "
                           "q_95. (%s)" % err, exc_info=True)
        try:
            ytext1 = ytext1 - ystep
            # Note: In ETSviz (CPO) it was set:
            #       self.eq.array[i].global_param.li
            #       In IDS: can't find it in Equilibrium IDS. Set as
            #       self.ids_core_profiles.global_quantities.li[self.it]
            #       for now
            self.fig.text(xtext11, ytext1,
                          'Li                     =  %6.4f [-]' %
                          (self.ids.core_profiles.global_quantities.li[self.it]),
                          color=colormap[0], fontsize=12, weight='bold')
        except Exception as err:
            self.log.error("ERROR occurred when reading Equilibrium "
                           "Li. (%s)" % err, exc_info=True)
        try:
            ytext1 = ytext1 - ystep
            # Note: In ETSviz (CPO) it was set:
            #       self.eq.array[self.it].global_param.beta_normal
            #       In IDS: can't find it in Equilibrium IDS. Set as
            #       self.ids_core_profiles.global_quantities.beta_tor_norm[self.it]
            #       for now
            self.fig.text(xtext11, ytext1,
                          'BETA_N            =  %6.4f [-]' %
                          (self.ids.core_profiles.global_quantities.beta_tor_norm[self.it]),
                          color=colormap[0], fontsize=12, weight='bold')
        except Exception as err:
            self.log.error("ERROR occurred when reading Equilibrium "
                           "BETA_N. (%s)" % err, exc_info=True)
        try:
            ytext1 = ytext1 - ystep
            self.fig.text(xtext11, ytext1,
                          'MAG_ENERGY  =  %6.4f [J]' %
                          (self.eq.time_slice[self.it].global_quantities.energy_mhd),
                          color=colormap[0], fontsize=12, weight='bold')
        except Exception as err:
            self.log.error("ERROR occurred when reading Equilibrium "
                           "MAG_ENERGY. (%s)" % err, exc_info=True)

        # Plasma quantities:
        # TODO

    def plotUpdate(self, time_index):
        """Update data.
        """
        self.plot() # TODO. make proper plotUpdate function