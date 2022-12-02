# -*- coding: utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
# If you need to restart vim tabs then :retab
'''
    This demo demonstrates how to embed a matplotlib (mpl) plot
    into a PyQt5 GUI application for IMAS visualization, including:
    * Using the navigation toolbar
    * Adding data to the plot
    * Dynamically modifying the plot's properties
    * Processing mpl events
    * Saving the plot to a file from a menu
    The main goal is to serve as a basis for developing rich wx GUI
    applications featuring mpl plots (using the mpl OO API).
    Jorge Morales (jorge.morales2@cea.fr)
    Based on a work by:
    Eli Bendersky (eliben@gmail.com)
    Coverted from wxPython to PyQt5 by:
    Dejan Penko (dejan.penko@lecad.fs.uni-lj.si)
    License: this code is in the public domain
'''
# Standard python modules
from __future__ import (unicode_literals, absolute_import,  \
                        print_function, division)
import argparse
from datetime import datetime
import getpass
import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import \
    FigureCanvasQTAgg as FigCanvas
from matplotlib.backends.backend_qt5agg import \
    NavigationToolbar2QT as NavigationToolbar
import matplotlib.ticker as tick
import numpy as np
import os
import sys, logging
from PySide2.QtWidgets import QDockWidget, QMenuBar, QAction, QApplication, QMainWindow, QTreeWidget, \
    QTreeWidgetItem, QWidget, QGridLayout, QVBoxLayout, QLineEdit, QSlider, QPushButton, QHBoxLayout,  \
    QLabel, QMessageBox, QStatusBar, QCheckBox
from PySide2 import QtCore

# Local python modules
import imas

from imasviz.VizPlugins.VizPlugin import VizPlugin

# Project python modules
from imasviz.VizPlugins.viz_equi.ids_read_multiprocess import \
    ids_read_multiprocess

# Figures options
nbr_levels         = 30  # For Psi (magnetic flux function)
fontsize_requested = 9   # Font size for axis labels and subfigure titles
fontsize_req_ticks = 9   # Font size for tick labels
fontsize_title     = 11  # Font size for title

def DataGen(vizTreeNode, vizAPI, dataTreeView):

    dataSource = vizAPI.GetDataSource(dataTreeView)
    shot = dataSource.shotNumber
    run = dataSource.runNumber
    machine = dataSource.imasDbName
    user = dataSource.userName
    status = 0

    print('shot    =', shot)
    print('run     =', run)
    print('user    =', user)
    print('machine =', machine)
    print('Reading data...')

    # Open shot and run of machine
    occurrence = 0 # default occurrence
    
    #root = logging.getLogger()
    #root.setLevel(logging.DEBUG)

    #handler = logging.StreamHandler(sys.stdout)
    #handler.setLevel(logging.DEBUG)
    #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    #handler.setFormatter(formatter)
    #root.addHandler(handler)

    logging.info("Here are the requirements for the ''Equilibrium'' plugin:"
                 "non empty equilibrium IDS with time slices,"
                 "non empty GGD (equilibrium.time_slice[:].ggd),"
                 "non empty IDS Wall.")
    logging.info("-------------------")             
    logging.info("Here are the required data for the 'equilibrium' IDS for all time slices:")
    logging.info("--> time_slice[itime].profiles_1d.q")
    logging.info("--> time_slice[itime].profiles_1d.elongation")
    logging.info("--> time_slice([itime].profiles_1d.triangularity_upper")
    logging.info("--> time_slice[itime].profiles_1d.triangularity_lower")
    logging.info("--> time_slice[itime].profiles_1d.j_tor")
    logging.info("--> time_slice[itime].profiles_1d.pressure")
    logging.info("--> time_slice[itime].profiles_1d.f_df_dpsi")
    logging.info("--> time_slice[itime].profiles_1d.dpressure_dpsi")
    logging.info("--> time_slice[itime].global_quantities.ip")
    logging.info("--> time_slice[itime].global_quantities.q_95")
    logging.info("--> time_slice[itime].global_quantities.q_axis")
    logging.info("--> time_slice[itime].global_quantities.li_3")
    logging.info("--> time_slice[itime].global_quantities.w_mhd")
    logging.info("--> time_slice[itime].global_quantities.magnetic_axis.r")
    logging.info("--> time_slice[itime].global_quantities.magnetic_axis.z")
    logging.info("--> time_slice[itime].boundary.outline.r")
    logging.info("--> time_slice[itime].boundary.outline.z")
    logging.info("--> time_slice[itime].ggd[0]")
    logging.info("--> grids_ggd[0]")
    
    logging.info("") 
    logging.info("Here are the required data for the 'wall' IDS:")
    logging.info("--> description_2d[0].limiter.unit[0].outline.r")
    logging.info("--> description_2d[0].limiter.unit[0].outline.z")
    logging.info("-------------------") 

    if not vizAPI.IDSDataAlreadyFetched(dataTreeView, 'equilibrium', occurrence):
        logging.info('Loading equilibrium IDS...')
        vizAPI.LoadIDSData(dataTreeView, 'equilibrium', occurrence)

    idd = dataSource.getImasEntry(occurrence)
    ht = idd.equilibrium.ids_properties.homogeneous_time
    if ht != 0 and ht != 1 and ht != 2:
        logging.error('Unable to start the Equilibrium plugin; ''Equilibrium'' IDS is empty.')
        status = -1

    elif len(idd.equilibrium.time_slice) == 0:
        logging.error('Unable to start the Equilibrium plugin; ''Equilibrium'' IDS has no time slices.')
        status = -1

    # elif len(idd.equilibrium.time_slice[0].ggd) == 0:
    #     logging.info('Unable to start the Equilibrium plugin; GGD is empty.')
    #     status = -1

    # Get wall geometry
    if not vizAPI.IDSDataAlreadyFetched(dataTreeView, 'wall', occurrence):
        logging.info('Loading wall IDS...')
        vizAPI.LoadIDSData(dataTreeView, 'wall', occurrence)


    idd = vizAPI.GetIMASDataEntry(dataTreeView, occurrence)

    ht = idd.wall.ids_properties.homogeneous_time
    if ht != 0 and ht != 1 and ht != 2:
        logging.error('Unable to start the Equilibrium plugin; ''Wall'' IDS is empty.')
        status = -1

    if status == -1:
        return shot, run, machine, user, \
                   None, None, \
                   None, None, None, None, None, None, None, \
                   None, None, None, None, None, \
                   None, None, \
                   None, None, None, None, None, None, -1

    # Array with all times requested
    lenArrTimes = len(idd.equilibrium.time)
    if lenArrTimes != len(idd.equilibrium.time_slice):
        logging.error('ERROR: length time and time_slice differ')
        return

    logging.info('Equilibrium plugin: preparing data...')

    timeEquiIDS = np.zeros(lenArrTimes)
    timeEquiIDS = idd.equilibrium.time
    #print('timeEquiIDS    =', timeEquiIDS)
    print('len idd.equilibrium.time       =', len(idd.equilibrium.time))
    print('len idd.equilibrium.time_slice =', len(idd.equilibrium.time_slice))

    # Declaration of arrays time traces
    Ip       = np.zeros(lenArrTimes)
    q95      = np.zeros(lenArrTimes)
    q_axis   = np.zeros(lenArrTimes)
    li_3     = np.zeros(lenArrTimes)
    w_mhd    = np.zeros(lenArrTimes)
    mag_ax_R = np.zeros(lenArrTimes)
    mag_ax_Z = np.zeros(lenArrTimes)
    NbrPoints = 0
    triKnots = []

    equi_tSlice = idd.equilibrium.time_slice[0]

    num_ggd_slices = len(idd.equilibrium.time_slice[0].ggd)
    num_grids_ggd_slices = len(idd.equilibrium.grids_ggd)
    num_grid_slices = 0

    if num_grids_ggd_slices > 0:
        num_grid_slices = len(idd.equilibrium.grids_ggd[0].grid)

    print(f"Number of GGD slices: {num_ggd_slices}")
    if num_ggd_slices > 0:
        print("Searching for grid in ggd node")
        equi_space  = idd.equilibrium.time_slice[0].ggd[0]

        if len(equi_space.grid.space) != 0:
            NbrPoints   = len(equi_space.grid.space[0].objects_per_dimension[0].object)
            print('NbrPoints (number of grid points) =', NbrPoints)
            # Declaration of arrays 2d plots
            RNodes   = np.zeros(NbrPoints)
            ZNodes   = np.zeros(NbrPoints)

            for i in range(NbrPoints):
                RNodes[i] = equi_space.grid.space[0].objects_per_dimension[0]. \
                            object[i].geometry[0]
                ZNodes[i] = equi_space.grid.space[0].objects_per_dimension[0]. \
                            object[i].geometry[1]

            Ntri = len(equi_space.grid.space[0].objects_per_dimension[2].object)
            triKnots = np.zeros((Ntri, 3))
            print('Ntri (number of grid triangles) =', Ntri)
            # Read triangle knots indices
            for i in range(0,Ntri):
                triKnots[i,0] = equi_space.grid.space[0].objects_per_dimension[2]. \
                                object[i].nodes[0]
                triKnots[i,1] = equi_space.grid.space[0].objects_per_dimension[2]. \
                                object[i].nodes[1]
                triKnots[i,2] = equi_space.grid.space[0].objects_per_dimension[2]. \
                                object[i].nodes[2]

        elif (num_grids_ggd_slices > 0) and (num_grid_slices > 0):
            print("Searching for grid in grids_ggd node")
            equi_grid = idd.equilibrium.grids_ggd[0].grid[0]
            NbrPoints = len(equi_grid.space[0].objects_per_dimension[0].object)
            print('NbrPoints (number of grid points) =', NbrPoints)
            # Declaration of arrays 2d plots
            RNodes = np.zeros(NbrPoints)
            ZNodes = np.zeros(NbrPoints)

            for i in range(NbrPoints):
                RNodes[i] = equi_grid.space[0].objects_per_dimension[0]. \
                    object[i].geometry[0]
                ZNodes[i] = equi_grid.space[0].objects_per_dimension[0]. \
                    object[i].geometry[1]

            Ntri = len(equi_grid.space[0].objects_per_dimension[2].object)
            triKnots = np.zeros((Ntri, 3))
            print('Ntri (number of grid triangles) =', Ntri)
            # Read triangle knots indices
            for i in range(0, Ntri):
                triKnots[i, 0] = equi_grid.space[0].objects_per_dimension[2]. \
                    object[i].nodes[0]
                triKnots[i, 1] = equi_grid.space[0].objects_per_dimension[2]. \
                    object[i].nodes[1]
                triKnots[i, 2] = equi_grid.space[0].objects_per_dimension[2]. \
                    object[i].nodes[2]

    # If GGD is empty
    else:
        print("GGD is empty. Searching for grid in profiles_2d node")
        print("Number of progiles_2d slices: ", len(idd.equilibrium.time_slice[0].profiles_2d))
        for j in range(len(idd.equilibrium.time_slice[0].profiles_2d)):
            if idd.equilibrium.time_slice[0].profiles_2d[j].grid_type.index == 1:
                print("profiles_2D for grid type index 1 found.")
                NbrPoints = len(idd.equilibrium.time_slice[0].profiles_2d[j].r)
                print('NbrPoints (number of grid points) =', NbrPoints)
                # Declaration of arrays 2d plots
                RNodes = []
                ZNodes = []

                for i in range(NbrPoints):
                    RNodes = idd.equilibrium.time_slice[0].profiles_2d[j].r
                    ZNodes = idd.equilibrium.time_slice[0].profiles_2d[j].z

                break

    unicode_type = np.dtype((np.unicode_, 12))

    min_Psi_val = np.zeros(lenArrTimes)
    max_Psi_val = np.zeros(lenArrTimes)
    Psi_val     = np.zeros((lenArrTimes, NbrPoints))

    levels1_requested = np.zeros((lenArrTimes, nbr_levels))

    boundPlasma = np.zeros((lenArrTimes, 2, 201))

    magAxis = np.zeros((lenArrTimes, 2))
    xPoint  = np.zeros((lenArrTimes, 2))

    wall = np.zeros((2, \
           len(idd.wall.description_2d[0].limiter.unit[0].outline.r)))

    b0 = np.zeros(lenArrTimes)

    # profiles 1d
    lenProf1d = len(equi_tSlice.profiles_1d.rho_tor)
    print('length of rho_tor = ', lenProf1d)
    prof_1d       = np.zeros((lenArrTimes, 9, lenProf1d))
    rho_tor_label = np.array([None]*lenArrTimes, dtype=unicode_type)

    # Wall
    status = -1
        
    try:
        wall[0, :] = idd.wall.description_2d[0].limiter.unit[0].outline.r
        wall[1, :] = idd.wall.description_2d[0].limiter.unit[0].outline.z
        status = 0
    except Exception as e:
        logging.error(e)
        
    if status == -1:
        return shot, run, machine, user, \
                   None, None, \
                   None, None, None, None, None, None, None, \
                   None, None, None, None, None, \
                   None, None, \
                   None, None, None, None, None, None, -1

    # b0 vacuum toroidal field and r0
    b0 = idd.equilibrium.vacuum_toroidal_field.b0
    r0 = idd.equilibrium.vacuum_toroidal_field.r0

    # Organise quantities for plot
    for timeit in range(lenArrTimes):
        startTime = datetime.now()

        print('-----')
        print('It:', timeit, ', time in equilibrium IDS =', timeEquiIDS[timeit])

        equi_tSlice = idd.equilibrium.time_slice[timeit]

        status = -1
        
        try:
            Ip[timeit]       = 1e-3*equi_tSlice.global_quantities.ip
            q95[timeit]      = equi_tSlice.global_quantities.q_95
            q_axis[timeit]   = equi_tSlice.global_quantities.q_axis
            li_3[timeit]     = equi_tSlice.global_quantities.li_3
            w_mhd[timeit]    = 1e-3*equi_tSlice.global_quantities.w_mhd
            mag_ax_R[timeit] = equi_tSlice.global_quantities.magnetic_axis.r
            mag_ax_Z[timeit] = equi_tSlice.global_quantities.magnetic_axis.z
            status = 0
        except Exception as e:
            logging.error(e)
            
        if status == -1:
            return shot, run, machine, user, \
                       None, None, \
                       None, None, None, None, None, None, None, \
                       None, None, None, None, None, \
                       None, None, \
                       None, None, None, None, None, None, -1

        num_ggd_slices = len(idd.equilibrium.time_slice[0].ggd)
        if num_ggd_slices > 0:
            print("Getting psi values from GGD")
            equi_space  = idd.equilibrium.time_slice[timeit].ggd[0]
            # Psi and plasma boundary
            Psi_val[timeit, :] = equi_space.psi[0].values

            min_Psi_val[timeit] = np.min(Psi_val[timeit, :])
            max_Psi_val[timeit] = np.max(Psi_val[timeit, :])

            levels1_requested[timeit, :] = np.linspace(min_Psi_val[timeit], \
                                             max_Psi_val[timeit], nbr_levels)
        # else:
        #    print("Getting psi values from profiles_2d")

            # psi = idd.equilibrium.time_slice[timeit].profiles_2d[0].psi # 2D array
            # Psi_val[timeit, :] = np.sqrt( abs( psi[:, - min(psi) ] ))

            # min_Psi_val[timeit] = np.min(Psi_val[timeit, :])
            # max_Psi_val[timeit] = np.max(Psi_val[timeit, :])

            # levels1_requested[timeit, :] = np.linspace(min_Psi_val[timeit], \
            #                                  max_Psi_val[timeit], nbr_levels)

        print('len equi_tSlice.boundary.outline.r =', len(equi_tSlice.boundary.outline.r))
        boundPlasma[timeit, 0, :] = np.interp(np.linspace(0, 1, 201), \
                                    np.linspace(0, 1, len(equi_tSlice.boundary.outline.r)), \
                                    equi_tSlice.boundary.outline.r)
        boundPlasma[timeit, 1, :] = np.interp(np.linspace(0, 1, 201), \
                                    np.linspace(0, 1, len(equi_tSlice.boundary.outline.z)), \
                                    equi_tSlice.boundary.outline.z)

        magAxis[timeit, 0] = equi_tSlice.global_quantities.magnetic_axis.r
        magAxis[timeit, 1] = equi_tSlice.global_quantities.magnetic_axis.z

        if (len(equi_tSlice.boundary.x_point) != 0):
            if (equi_tSlice.boundary.x_point[0].r != 0):
                xPoint[timeit, 0] = equi_tSlice.boundary.x_point[0].r
                xPoint[timeit, 1] = equi_tSlice.boundary.x_point[0].z
            else:
                xPoint[timeit, 0] = None
                xPoint[timeit, 1] = None
        else:
            xPoint[timeit, 0] = None
            xPoint[timeit, 1] = None

        # Compute profiles 1d
        prof_1d[timeit, 1, :] = equi_tSlice.profiles_1d.q
        prof_1d[timeit, 2, :] = equi_tSlice.profiles_1d.elongation
        prof_1d[timeit, 3, :] = equi_tSlice.profiles_1d.triangularity_upper
        prof_1d[timeit, 4, :] = equi_tSlice.profiles_1d.triangularity_lower
        prof_1d[timeit, 5, :] = 1e-6*equi_tSlice.profiles_1d.j_tor
        prof_1d[timeit, 6, :] = 1e-3*equi_tSlice.profiles_1d.pressure
        prof_1d[timeit, 7, :] = equi_tSlice.profiles_1d.f_df_dpsi
        prof_1d[timeit, 8, :] = equi_tSlice.profiles_1d.dpressure_dpsi
        if (equi_tSlice.profiles_1d.rho_tor[-1] != 0.):
            prof_1d[timeit, 0, :] = equi_tSlice.profiles_1d.rho_tor \
                                    / equi_tSlice.profiles_1d.rho_tor[-1]
            rho_tor_label[timeit] = 'rho_tor_norm'
        else:
            print('WARNING: final value of rho_tor (at separatrix) is:', \
                   equi_tSlice.profiles_1d.rho_tor[-1])
            print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            print('WARNING: using points instead of rho_tor_norm !!!')
            print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            prof_1d[timeit, 0, :] = np.linspace(0, 1, lenProf1d)
            rho_tor_label[timeit] = 'Eq_space_pts'

        # Print time of the loop
        #print('Time loop', timeit, '=', datetime.now() - startTime)
        #print('In DataDen id(Psi_val) =', id(Psi_val))
    logging.info('Equilibrium plugin: data ready.')


    return shot, run, machine, user, \
           timeEquiIDS, lenArrTimes, \
           Ip, q95, q_axis, li_3, w_mhd, mag_ax_R, mag_ax_Z, \
           Psi_val, RNodes, ZNodes, triKnots, levels1_requested, \
           rho_tor_label, prof_1d, \
           boundPlasma, magAxis, wall, b0, r0, xPoint, status

class PlotFrame(QMainWindow):
    """ The main frame of the application
    """

    title = 'Equilibrium charts'

    def __init__(self, vizTreeNode, vizAPI, parent=None, title=title):

        super(PlotFrame, self).__init__(parent)

        self.shot,          self.run,               self.machine, \
        self.user,          self.timeEquiIDS,       self.lenArrTimes,\
        self.Ip,            self.q95,               self.q_axis, \
        self.li_3,          self.w_mhd,             self.mag_ax_R, \
        self.mag_ax_Z,      self.Psi_val,           self.RNodes, \
        self.ZNodes,        self.triKnots,          self.levels1_requested, \
        self.rho_tor_label, self.prof_1d,           self.boundPlasma, \
        self.magAxis,       self.wall,              self.b0, \
        self.r0,            self.xPoint, status = DataGen(vizTreeNode, vizAPI,
                                                  dataTreeView=parent)

        if status == -1:
            return

        # Set main widget
        self.mainWidget = QWidget(self)

        self.dataTimes = [round(0.5*(self.timeEquiIDS[0]+self.timeEquiIDS[-1]), 1)]
        self.dataTimes_old = self.dataTimes
        self.boolOnTextEnter = False
        self.line_color = ('#1f77b4', 'darkorange', 'g', 'Brown', \
                           'r', 'Purple', 'Blue', 'm', 'c', 'k')
        self.nt_line_color = 0

        self.create_menu()
        self.create_status_bar()
        self.create_main_panel()

        self.setCentralWidget(self.mainWidget)

        self.redraw_timer = QtCore.QTimer(self)
        self.redraw_timer.timeout.connect(self.on_redraw_timer)

        self.textbox.setText(' '.join(map(str, self.dataTimes)))
        self.draw_figure()

    def create_menu(self):

        # Main menu bar
        self.menuBar = QMenuBar(self)

        menu_file = self.menuBar.addMenu('File')
        #TODO m_exit = menu_file.Append(wx.ID_EXIT, "Exit\tCtrl-X", "Exit")
        exitAction = QAction('Exit', self)
        # exitAction.triggered.connect(self.close)
        exitAction.triggered.connect(self.on_exit)
        menu_file.addAction(exitAction)

        menu_help = self.menuBar.addMenu('Help')
        #TODO m_about = menu_help.Append(wx.ID_ABOUT, "About\tF1", "About the demo")
        aboutAction = QAction('About', self)
        aboutAction.triggered.connect(self.on_about)
        menu_help.addAction(aboutAction)

        # Set menu bar
        self.setMenuBar(self.menuBar)

    def create_main_panel(self):
        """ Creates the main panel with all the controls on it:
             * mpl canvas
             * mpl navigation toolbar
             * Control panel for interaction
        """
        self.panel = self.mainWidget

        # Create the mpl Figure and FigCanvas objects.
        # 100 dots-per-inch
        self.dpi = 110
        self.fig = Figure(dpi=self.dpi)
        # self.fig = Figure(figsize=(5, 3))
        # Set canvas containing plots
        self.canvas = FigCanvas(self.fig)

        self.fig.subplots_adjust(left=0.08, right=0.99, bottom=0.1, top=0.9, \
                                 wspace=0.3, hspace=0.0)

        self.fig.suptitle('Equilibrium' \
                        + '       ' + 'Shot ' + str(self.shot) + '     Run ' \
                        + str(self.run) + '     ' + 'Machine ' + self.machine \
                        + '     User '  + self.user, fontsize=fontsize_title)

        # Since we have only one plot, we can use add_axes
        # instead of add_subplot, but then the subplot
        # configuration tool in the navigation toolbar wouldn't
        # work.

        # For semi-automatic configuration...
        #self.numAxes = (nrow*ncol + 1)
        #self.axes    = [None]*self.numAxes
        #for nplt in range(nrow*ncol):
        #    print('nplt =', nplt)
        #    self.axes[nplt] = self.fig.add_subplot(nrow, ncol, nplt+1)

        grid_subp    = matplotlib.gridspec.GridSpec(6, 3)
        self.numAxes = 14
        self.axes    = [None]*self.numAxes
        self.pltaxv  = [None]*6

        # 1 column
        # Ip
        self.axes[0] = self.fig.add_subplot(grid_subp[0, 0])
        # q95 and q_axis
        self.axes[1] = self.fig.add_subplot(grid_subp[1, 0], sharex=self.axes[0])
        # li3
        self.axes[2] = self.fig.add_subplot(grid_subp[2, 0], sharex=self.axes[0])
        # w_mhd
        self.axes[3] = self.fig.add_subplot(grid_subp[3, 0], sharex=self.axes[0])
        # mag ax R
        self.axes[4] = self.fig.add_subplot(grid_subp[4, 0], sharex=self.axes[0])
        # mag ax Z
        self.axes[5] = self.fig.add_subplot(grid_subp[5, 0], sharex=self.axes[0])

        # 2 column
        # Psi 2D
        self.axes[6] = self.fig.add_subplot(grid_subp[:4, 1])
        # q
        self.axes[7] = self.fig.add_subplot(grid_subp[5, 1])

        # 3 column
        # elong
        self.axes[8]  = self.fig.add_subplot(grid_subp[0, 2], xticklabels=[])
        # triang
        self.axes[9]  = self.fig.add_subplot(grid_subp[1, 2], xticklabels=[])
        # j_tor
        self.axes[10] = self.fig.add_subplot(grid_subp[2, 2], xticklabels=[])
        # Pressure
        self.axes[11] = self.fig.add_subplot(grid_subp[3, 2], xticklabels=[])
        # ff'
        self.axes[12] = self.fig.add_subplot(grid_subp[4, 2], xticklabels=[])
        # P'
        self.axes[13] = self.fig.add_subplot(grid_subp[5, 2])

        # Set checkbox to enable/disable grid in plots
        self.cb_grid = QCheckBox('Grid', self.panel)
        self.cb_grid.setChecked(False)
        self.cb_grid.setObjectName("GridCheckBox")
        self.cb_grid.setText("Enable Grid")
        self.cb_grid.stateChanged.connect(self.on_cb_grid)

        # Set time value text box
        self.textbox = QLineEdit(self.panel)
        self.textbox.setObjectName("TimeTextBox")
        self.textbox.returnPressed.connect(self.on_text_enter)

        self.drawButtonRun = QPushButton("Run", self.panel)
        self.drawButtonRun.clicked.connect(self.on_draw_buttonRun)
        # Set a flag to mark the status if the run is operating
        self.runIsActive = False

        self.drawButtonStop = QPushButton("Stop", self.panel)
        self.drawButtonStop.clicked.connect(self.on_draw_buttonStop)

        # Set time slider
        self.slider_time = QSlider(QtCore.Qt.Horizontal, self.panel)
        self.slider_time.setValue(0)
        self.slider_time.setMinimum(0)
        self.slider_time.setMaximum(self.lenArrTimes-1)
        # self.slider_time.adjustSize()
        self.slider_time.setMinimumWidth(600)

        # Set slider event handling
        self.slider_time.valueChanged.connect(self.on_slider)
        # self.slider_time.sliderMoved.connect(self.on_slider_track)
        self.slider_time.sliderReleased.connect(self.on_slider_time)

        self.textbox_label = QLabel('Time value to draw (press enter)',
                                    self.panel)

        # Create the navigation toolbar, tied to the canvas
        self.toolbar = NavigationToolbar(self.canvas, self.panel)

        # Set vertical box layout
        self.vboxLayout = QVBoxLayout(self.mainWidget)
        # Add canvas to box layout of the main widget
        self.vboxLayout.addWidget(self.canvas)
        self.vboxLayout.addWidget(self.toolbar)
        self.vboxLayout.addSpacing(20)

        # Add widget for buttons etc.
        self.interface_widget = QWidget(self.panel)
        # Add horizontal layout
        self.hboxLayout = QHBoxLayout(self.interface_widget)
        # Add buttons etc.
        self.hboxLayout.addWidget(self.slider_time)
        self.hboxLayout.addSpacing(10)
        self.hboxLayout.addWidget(self.drawButtonRun)
        self.hboxLayout.addSpacing(10)
        self.hboxLayout.addWidget(self.drawButtonStop)
        self.hboxLayout.addSpacing(3)
        self.hboxLayout.addWidget(self.cb_grid)
        self.hboxLayout.addSpacing(10)
        self.hboxLayout.addWidget(self.textbox_label)
        self.hboxLayout.addSpacing(10)
        self.hboxLayout.addWidget(self.textbox)
        self.hboxLayout.addSpacing(10)

        self.vboxLayout.addWidget(self.interface_widget)

    def create_status_bar(self):
        # self.statusBar = self.CreateStatusBar()
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

    def draw_figure(self):
        """ Draws figure
        """

        sliderValue = int(round(self.slider_time.value()))
        # sliderValue = 0

        print('In draw_figure, self.slider_time.value = ', sliderValue)

        self.axes[0].plot(self.timeEquiIDS, self.Ip)
        self.axes[0].set_ylabel('Ip [kA]', fontsize=fontsize_requested)

        self.axes[1].plot(self.timeEquiIDS, self.q95, label='q95')
        self.axes[1].plot(self.timeEquiIDS, self.q_axis, \
                          color='g', linestyle='--', label='q_axis')
        self.axes[1].set_ylabel('q', fontsize=fontsize_requested)
        self.axes[1].legend(loc=1, fontsize=fontsize_requested)

        self.axes[2].plot(self.timeEquiIDS, self.li_3)
        self.axes[2].set_ylabel('li3', fontsize=fontsize_requested)

        self.axes[3].plot(self.timeEquiIDS, self.w_mhd)
        self.axes[3].set_ylabel('Wmhd [kJ]', fontsize=fontsize_requested)

        self.axes[4].plot(self.timeEquiIDS, self.mag_ax_R)
        self.axes[4].set_ylabel('Ax R [m]', fontsize=fontsize_requested)

        self.axes[5].plot(self.timeEquiIDS, self.mag_ax_Z)
        self.axes[5].set_xlabel('Time [s]', fontsize=fontsize_requested)
        self.axes[5].set_ylabel('Ax Z [m]', fontsize=fontsize_requested)

        for it_ax in range(6):
            self.pltaxv[it_ax] = \
                 self.axes[it_ax].axvline(self.timeEquiIDS[sliderValue], \
                 color='r', linestyle='--')
            self.axes[it_ax].label_outer()

        if len(self.triKnots) > 0:
            self.axes[6].tricontour(self.RNodes, self.ZNodes, self.triKnots, \
                                    self.Psi_val[sliderValue], \
                                    colors='#1f77b4', \
                                    linestyles='solid', linewidths=0.7, \
                                    levels=self.levels1_requested[sliderValue, :])
        self.plt6a, = self.axes[6].plot(self.boundPlasma[sliderValue, 0, :], \
                                        self.boundPlasma[sliderValue, 1, :], 'r')
        self.plt6b, = self.axes[6].plot(self.magAxis[sliderValue, 0], \
                                        self.magAxis[sliderValue, 1], \
                                        '+r', markersize=15)
        self.plt6c, = self.axes[6].plot(self.xPoint[sliderValue, 0], \
                                        self.xPoint[sliderValue, 1], \
                                        'x', color='k', markersize=20)
        self.plt6d, = self.axes[6].plot(self.wall[0, :], \
                                        self.wall[1, :], '-k', linewidth=2)
        self.axes[6].set(aspect=1)
        self.axes[6].set_title('Psi with B0='+ \
                      '{:.3f}'.format(self.b0[sliderValue])+ \
                      ' [T] at R0=' + '{:.3f}'.format(self.r0) + ' [m]', \
                      fontsize=fontsize_requested)
        self.axes[6].set_xlabel('R [m]', fontsize=fontsize_requested)
        self.axes[6].set_ylabel('Z [m]', fontsize=fontsize_requested)

        #if (not self.boolOnTextEnter):
        self.timeText = self.axes[7].set_title('Time = ' \
                                        + str(self.timeEquiIDS[sliderValue]), \
                                        fontsize=fontsize_title)
        #else:
        #    self.timeText.set_text('')

        self.plt7, = self.axes[7].plot(self.prof_1d[sliderValue, 0], \
                                       self.prof_1d[sliderValue, 1])
        self.axes[7].axhline(1, color='k', linestyle='--')
        self.axes[7].set_xlabel(self.rho_tor_label[sliderValue], fontsize=fontsize_requested)
        self.axes[7].set_ylabel('q', fontsize=fontsize_requested)

        self.plt8, = self.axes[8].plot(self.prof_1d[sliderValue, 0], \
                                       self.prof_1d[sliderValue, 2])
        self.axes[8].set_ylabel('elong', fontsize=fontsize_requested)

        self.plt9a, = self.axes[9].plot(self.prof_1d[sliderValue, 0], \
                                        self.prof_1d[sliderValue, 3], \
                                        label='triang up')
        self.plt9b, = self.axes[9].plot(self.prof_1d[sliderValue, 0], \
                                        self.prof_1d[sliderValue, 4], \
                                        label='triang low', color='g', \
                                        linestyle='--')
        self.axes[9].set_ylabel('triang', fontsize=fontsize_requested)
        self.axes[9].legend(loc=1, fontsize=fontsize_requested)

        self.plt10, = self.axes[10].plot(self.prof_1d[sliderValue, 0], \
                                         self.prof_1d[sliderValue, 5])
        self.axes[10].set_ylabel('jtor [MA/m2]', fontsize=fontsize_requested)

        self.plt11, = self.axes[11].plot(self.prof_1d[sliderValue, 0], \
                                         self.prof_1d[sliderValue, 6])
        self.axes[11].set_ylabel('P [kPa]', fontsize=fontsize_requested)

        self.plt12, = self.axes[12].plot(self.prof_1d[sliderValue, 0], \
                                         self.prof_1d[sliderValue, 7])
        self.axes[12].set_ylabel('ff\'', fontsize=fontsize_requested)

        self.plt13, = self.axes[13].plot(self.prof_1d[sliderValue, 0], \
                                         self.prof_1d[sliderValue, 8])
        self.axes[13].set_ylabel('P\'', fontsize=fontsize_requested)
        self.axes[13].yaxis.set_major_formatter(tick.FormatStrFormatter('%2.0e'))
        self.axes[13].set_xlabel(self.rho_tor_label[sliderValue], fontsize=fontsize_requested)

        for it_ax in range(8, (self.numAxes - 1)):
            self.axes[it_ax].set_xticklabels([])

        for it_ax in range(self.numAxes):
            for label in (self.axes[it_ax].get_xticklabels() + \
                          self.axes[it_ax].get_yticklabels()):
                label.set_fontsize(fontsize_req_ticks)

        self.canvas.draw()


    def update_figure(self):
        """ Updates the figure
        """

        sliderValue = int(round(self.slider_time.value()))
        #print('self.slider_time.value = ', sliderValue)

        #self.timeText.set_text('Time = ' + str(self.timeEquiIDS[sliderValue]))

        self.axes[6].cla()
        if len(self.triKnots) > 0:
            self.axes[6].tricontour(self.RNodes, self.ZNodes, self.triKnots, \
                                    self.Psi_val[sliderValue], \
                                    colors='#1f77b4', \
                                    linestyles='solid', linewidths=0.7, \
                                    levels=self.levels1_requested[sliderValue, :])
        self.axes[6].plot(self.boundPlasma[sliderValue, 0, :], \
                          self.boundPlasma[sliderValue, 1, :], 'r')
        self.axes[6].plot(self.magAxis[sliderValue, 0], \
                          self.magAxis[sliderValue, 1], \
                          '+r', markersize=15)
        self.axes[6].plot(self.xPoint[sliderValue, 0], \
                          self.xPoint[sliderValue, 1], \
                          'x', color='k', markersize=20)
        self.axes[6].plot(self.wall[0, :], \
                          self.wall[1, :], '-k', linewidth=2)
        self.axes[6].set(aspect=1)
        self.axes[6].set_title('Psi with B0='+ \
                      '{:.3f}'.format(self.b0[sliderValue])+ \
                      ' [T] at R0=' + '{:.3f}'.format(self.r0) + ' [m]', \
                      fontsize=fontsize_requested)
        self.axes[6].set_xlabel('R [m]', fontsize=fontsize_requested)
        self.axes[6].set_ylabel('Z [m]', fontsize=fontsize_requested)

        for label in (self.axes[6].get_xticklabels() + \
                      self.axes[6].get_yticklabels()):
            label.set_fontsize(fontsize_req_ticks)

        if (self.cb_grid.isChecked()):
            self.axes[6].minorticks_on()
            self.axes[6].grid(b=True, which='major', linestyle='-', \
                              linewidth=0.5)
            self.axes[6].grid(b=True, which='minor', linestyle=':', \
                              linewidth=0.2)

        #if (not self.boolOnTextEnter):
        self.timeText = self.axes[7].set_title('Time = ' \
                                        + str(self.timeEquiIDS[sliderValue]), \
                                        fontsize=fontsize_title)
        #else:
        #    self.timeText.set_text('')

        self.plt7.set_data(self.prof_1d[sliderValue, 0], \
                           self.prof_1d[sliderValue, 1])
        self.axes[7].relim()
        self.axes[7].autoscale_view(scalex=False)
        self.axes[7].set_xlabel(self.rho_tor_label[sliderValue], \
                                fontsize=fontsize_requested)

        self.plt8.set_data(self.prof_1d[sliderValue, 0], \
                           self.prof_1d[sliderValue, 2])
        self.axes[8].relim()
        self.axes[8].autoscale_view(scalex=False)

        self.plt9a.set_data(self.prof_1d[sliderValue, 0], \
                            self.prof_1d[sliderValue, 3])
        self.plt9b.set_data(self.prof_1d[sliderValue, 0], \
                            self.prof_1d[sliderValue, 4])
        self.axes[9].relim()
        self.axes[9].autoscale_view(scalex=False)

        self.plt10.set_data(self.prof_1d[sliderValue, 0], \
                            self.prof_1d[sliderValue, 5])
        self.axes[10].relim()
        self.axes[10].autoscale_view(scalex=False)

        self.plt11.set_data(self.prof_1d[sliderValue, 0], \
                            self.prof_1d[sliderValue, 6])
        self.axes[11].relim()
        self.axes[11].autoscale_view(scalex=False)

        self.plt12.set_data(self.prof_1d[sliderValue, 0], \
                            self.prof_1d[sliderValue, 7])
        self.axes[12].relim()
        self.axes[12].autoscale_view(scalex=False)

        self.plt13.set_data(self.prof_1d[sliderValue, 0], \
                            self.prof_1d[sliderValue, 8])
        self.axes[13].relim()
        self.axes[13].autoscale_view(scalex=False)
        self.axes[13].set_xlabel(self.rho_tor_label[sliderValue], \
                                 fontsize=fontsize_requested)

        for it_ax in range(6):
            self.pltaxv[it_ax].set_xdata(self.timeEquiIDS[sliderValue])

        self.canvas.draw()
        self.canvas.show()

    def draw_figure_on_text(self):
        """ Draws figure when enter on text
        """

        sliderValue = int(round(self.slider_time.value()))
        print('In draw_figure, self.slider_time.value = ', sliderValue)

        if (self.nt_line_color == 0):
            self.axes[0].plot(self.timeEquiIDS, self.Ip, 'k')
            self.axes[0].set_ylabel('Ip [kA]', fontsize=fontsize_requested)

            self.axes[1].plot(self.timeEquiIDS, self.q95, 'k', label='q95')
            self.axes[1].plot(self.timeEquiIDS, self.q_axis, \
                              color='k', \
                              linestyle='--', label='q_axis')
            self.axes[1].set_ylabel('q', fontsize=fontsize_requested)
            self.axes[1].legend(loc=1, fontsize=fontsize_requested)

            self.axes[2].plot(self.timeEquiIDS, self.li_3, 'k')
            self.axes[2].set_ylabel('li3', fontsize=fontsize_requested)

            self.axes[3].plot(self.timeEquiIDS, self.w_mhd, 'k')
            self.axes[3].set_ylabel('Wmhd [kJ]', fontsize=fontsize_requested)

            self.axes[4].plot(self.timeEquiIDS, self.mag_ax_R, 'k')
            self.axes[4].set_ylabel('Ax R [m]', fontsize=fontsize_requested)

            self.axes[5].plot(self.timeEquiIDS, self.mag_ax_Z, 'k')
            self.axes[5].set_xlabel('Time [s]', fontsize=fontsize_requested)
            self.axes[5].set_ylabel('Ax Z [m]', fontsize=fontsize_requested)

            for it_ax in range(6):
                self.axes[it_ax].label_outer()
                for label in (self.axes[it_ax].get_xticklabels() + \
                              self.axes[it_ax].get_yticklabels()):
                    label.set_fontsize(fontsize_req_ticks)

        color_index = self.nt_line_color % len(self.line_color)
        #print('color_index =', color_index)

        for it_ax in range(6):
            self.pltaxv[it_ax] = \
                 self.axes[it_ax].axvline(self.timeEquiIDS[sliderValue], \
                 color=self.line_color[color_index], linestyle='--')

        self.axes[6].plot(self.boundPlasma[sliderValue, 0, :], \
                          self.boundPlasma[sliderValue, 1, :], \
                          color=self.line_color[color_index], \
                          label='t='+str(self.timeEquiIDS[sliderValue]))
        self.axes[6].plot(self.magAxis[sliderValue, 0], \
                          self.magAxis[sliderValue, 1], \
                          color=self.line_color[color_index], \
                          marker='+', markersize=15)
        self.axes[6].plot(self.xPoint[sliderValue, 0], \
                          self.xPoint[sliderValue, 1], \
                          color=self.line_color[color_index], \
                          marker='x', markersize=20)
        if (self.nt_line_color == 0):
            self.axes[6].plot(self.wall[0, :], \
                                        self.wall[1, :], '-k', linewidth=2)
        self.axes[6].set(aspect=1)
        self.axes[6].set_xlabel('R [m]', fontsize=fontsize_requested)
        self.axes[6].set_ylabel('Z [m]', fontsize=fontsize_requested)
        self.axes[6].legend(loc=1, fontsize=fontsize_requested)

        self.axes[7].plot(self.prof_1d[sliderValue, 0], \
                          self.prof_1d[sliderValue, 1], \
                          color=self.line_color[color_index])
        self.axes[7].axhline(1, color='k', linestyle='--')
        self.axes[7].set_xlabel(self.rho_tor_label[sliderValue], fontsize=fontsize_requested)
        self.axes[7].set_ylabel('q', fontsize=fontsize_requested)

        self.axes[8].plot(self.prof_1d[sliderValue, 0], \
                          self.prof_1d[sliderValue, 2], \
                          color=self.line_color[color_index])
        self.axes[8].set_ylabel('elong', fontsize=fontsize_requested)

        self.axes[9].plot(self.prof_1d[sliderValue, 0], \
                          self.prof_1d[sliderValue, 3], \
                          color=self.line_color[color_index], \
                          label='triang up')
        self.axes[9].plot(self.prof_1d[sliderValue, 0], \
                          self.prof_1d[sliderValue, 4], \
                          color=self.line_color[color_index], \
                          label='triang low', \
                          linestyle='--')
        self.axes[9].set_ylabel('triang', fontsize=fontsize_requested)
        if (self.nt_line_color == 0):
            self.axes[9].legend(loc=1, fontsize=fontsize_requested)

        self.axes[10].plot(self.prof_1d[sliderValue, 0], \
                           self.prof_1d[sliderValue, 5], \
                           color=self.line_color[color_index])
        self.axes[10].set_ylabel('jtor [MA/m2]', fontsize=fontsize_requested)

        self.axes[11].plot(self.prof_1d[sliderValue, 0], \
                           self.prof_1d[sliderValue, 6], \
                           color=self.line_color[color_index])
        self.axes[11].set_ylabel('P [kPa]', fontsize=fontsize_requested)

        self.axes[12].plot(self.prof_1d[sliderValue, 0], \
                           self.prof_1d[sliderValue, 7], \
                           color=self.line_color[color_index])
        self.axes[12].set_ylabel('ff\'', fontsize=fontsize_requested)

        self.axes[13].plot(self.prof_1d[sliderValue, 0], \
                           self.prof_1d[sliderValue, 8], \
                           color=self.line_color[color_index])
        self.axes[13].set_ylabel('P\'', fontsize=fontsize_requested)
        self.axes[13].yaxis.set_major_formatter(tick.FormatStrFormatter('%2.0e'))
        self.axes[13].set_xlabel(self.rho_tor_label[sliderValue], fontsize=fontsize_requested)

        for it_ax in range(8, (self.numAxes - 1)):
            self.axes[it_ax].set_xticklabels([])

        for it_ax in range(6, self.numAxes):
            for label in (self.axes[it_ax].get_xticklabels() + \
                          self.axes[it_ax].get_yticklabels()):
                label.set_fontsize(fontsize_req_ticks)

        self.canvas.draw()

    def update_time_line(self):
        ''' Updates vertical time line
        '''
        sliderValue = int(round(self.slider_time.value()))

        for it_ax in range(6):
            self.pltaxv[it_ax].set_xdata(self.timeEquiIDS[sliderValue])

        self.canvas.draw()

    def on_cb_grid(self, event=None):
        if (self.cb_grid.isChecked()):
            for it_ax in range(self.numAxes):
                self.axes[it_ax].minorticks_on()
                self.axes[it_ax].grid(b=True, which='major', linestyle='-', \
                                      linewidth=0.5)
                self.axes[it_ax].grid(b=True, which='minor', linestyle=':', \
                                      linewidth=0.2)
        else:
            for it_ax in range(self.numAxes):
                self.axes[it_ax].minorticks_off()
                self.axes[it_ax].grid(b=False)
        self.canvas.draw()

    def on_text_enter(self, event=None):
        if (self.redraw_timer.isActive()):
            self.redraw_timer.stop()
        str_in = self.textbox.text()
        dataTimes_in = list(map(float, str_in.split()))
        # If no data in text entry
        if (not dataTimes_in):
            for it_ax in range(self.numAxes):
                self.axes[it_ax].cla()
            if (self.cb_grid.isChecked()):
                self.on_cb_grid.stateChanged.emit()
            self.boolOnTextEnter = False
            self.slider_time.setValue(0)
            self.draw_figure()
            return
        if (not self.boolOnTextEnter):
            for it_ax in range(self.numAxes):
                self.axes[it_ax].cla()
            if (self.cb_grid.isChecked()):
                self.on_cb_grid.stateChanged.emit()
            self.dataTimes_old = dataTimes_in
            self.dataTimes     = dataTimes_in
            self.boolOnTextEnter = True
            self.nt_line_color = 0
        else:
            self.dataTimes = []
            for valT in dataTimes_in:
                if (not valT in self.dataTimes_old):
                    self.dataTimes.append(valT)
                    self.dataTimes_old.append(valT)
            # If no new data
            if (not self.dataTimes):
                # If double click with one time: draw new image and return
                if (len(self.dataTimes_old) == 1):
                    for it_ax in range(self.numAxes):
                        self.axes[it_ax].cla()
                    if (self.cb_grid.isChecked()):
                        self.on_cb_grid.stateChanged.emit()
                    self.boolOnTextEnter = False
                    idxTime = \
                     (np.abs(self.timeEquiIDS-self.dataTimes_old[0])).argmin()
                    print('idxTime in old==1 =', idxTime)
                    self.slider_time.setValue(idxTime)
                    self.draw_figure()
                    return
                # If some time entries are removed from text:
                # redraw image (clean axes)
                if (len(self.dataTimes_old) > len(dataTimes_in)):
                    print('old > new')
                    for it_ax in range(self.numAxes):
                        self.axes[it_ax].cla()
                    if (self.cb_grid.isChecked()):
                        self.on_cb_grid.stateChanged.emit()
                    self.dataTimes_old = dataTimes_in
                    self.dataTimes     = dataTimes_in
                    self.nt_line_color = 0
        #print('self.dataTimes =', self.dataTimes)
        if (self.dataTimes):
            for varTime in self.dataTimes:
                idxTime = (np.abs(self.timeEquiIDS-varTime)).argmin()
                print('idxTime =', idxTime)
                self.slider_time.setValue(idxTime)
                self.draw_figure_on_text()
                self.nt_line_color += 1

    def on_draw_buttonRun(self, event=None):
        # Update the run status
        self.runIsActive = True
        if (self.redraw_timer.isActive()):
            pass
        else:
            if (self.boolOnTextEnter):
                self.boolOnTextEnter = False
                for it_ax in range(self.numAxes):
                    self.axes[it_ax].cla()
                if (self.cb_grid.isChecked()):
                    self.on_cb_grid.stateChanged.emit()
                self.draw_figure()
            self.it_data = int(round(self.slider_time.value()))
            self.redraw_timer.start(400)

    def on_draw_buttonStop(self, event=None):
        # Update the run status
        self.runIsActive = False
        self.redraw_timer.stop()

    def on_redraw_timer(self, event=None):
        self.slider_time.setValue(self.it_data)
        self.update_figure()
        self.it_data += 1
        self.it_data %= self.lenArrTimes
        #print('self.it_data =', self.it_data)

    def on_slider(self, event=None):
        """Run either on_slider_time or on_slider_track routines,
        depending how the slider is moved.
        """

        if self.slider_time.isSliderDown() == True:
            self.on_slider_track()
        elif self.runIsActive != True:
            # Only if 'run' is not running
            # (otherwise the run operation will be interrupted)
            self.on_slider_time()

    def on_slider_time(self, event=None):
        """Redraw ALL plots for current slider time value.
        """
        if (self.redraw_timer.isActive()):
            self.redraw_timer.stop()
        if (self.boolOnTextEnter):
            self.boolOnTextEnter = False
            for it_ax in range(self.numAxes):
                self.axes[it_ax].cla()
            if (self.cb_grid.isChecked()):
                self.on_cb_grid.stateChanged.emit()
            self.draw_figure()
        else:
            self.update_figure()

    def on_slider_track(self, event=None):
        """Redraw only time track plot for current slider time value.
        """
        if (self.redraw_timer.isActive()):
            self.redraw_timer.stop()
            self.update_time_line()
        else:
            self.update_time_line()

    def on_pick(self, event=None):
        # The event received here is of the type
        # matplotlib.backend_bases.PickEvent
        #
        # It carries lots of information, of which we're using
        # only a small amount here.
        #
        box_points = event.artist.get_bbox().get_points()
        msg = "You've clicked on a bar with coords:\n %s" % box_points

        dlg = QMessageBox(self.panel)
        dlg.setText(msg)
        # dlg.setInformativeText("...")
        dlg.setDefaultButton(QMessageBox.Ok)
        dlg.setWindowTitle("Click")
        dlg.setWindowModality(QtCore.Qt.ApplicationModal)
        dlg.exec_()
        dlg.close()

    def on_save_plot(self, event=None):
        # Note: Not implemented for PyQt version as also in the previous
        #       wxPython version) this routine was not used
        file_choices = "PNG (*.png)|*.png"

    def on_exit(self, event=None):
        self.redraw_timer.stop()
        self.close()

    def on_about(self, event=None):
        """Set 'About' dialog."""
        msg = \
            ''' VACTH-EQUINOX results visualization using PyQt5 with Matplotlib:

                * Drag the Slider to explore time
                * Click on Run to animate the equilibrium plots
                * Use the Text Box to compare multiple times
                * Show or hide the grid
                * Save plot to a file (png, jpeg, pdf...) using
                    the Matplotlib Navigation Bar located on top     '''

        dlg = QMessageBox(self.panel)
        dlg.setText(msg)
        # dlg.setInformativeText("...")
        dlg.setDefaultButton(QMessageBox.Ok)
        dlg.setWindowTitle("About")
        dlg.setWindowModality(QtCore.Qt.ApplicationModal)
        dlg.exec_()
        dlg.close()

    def flash_status_message(self, msg, flash_len_ms=1500):
        self.statusBar.SetStatusText(msg)
        self.timeroff = QtCore.QTimer(self)
        self.timeroff.timeout.connect(self.on_flash_status_off)
        self.timeroff.Start(flash_len_ms, oneShot=True)

    def on_flash_status_off(self, event=None):
        self.statusBar.SetStatusText('')

class equilibriumcharts(VizPlugin):

    def __init__(self):
        pass

    def isEnabled(self):
        return True

    def execute(self, vizAPI, pluginEntry):

        self.frame = PlotFrame(self.selectedTreeNode, vizAPI, parent=self.dataTreeView)
        self.frame.show()

    def getEntries(self):
        if self.selectedTreeNode.getIDSName() == "equilibrium":
            return [0]
        else:
            return []

    # def getPluginsConfiguration(self):
    #     return [{
    #                                         'time_i': 31.880, \
    #                                         'time_e': 32.020, \
    #                                         'delta_t': 0.02, \
    #                                         'shot': 50642, \
    #                                         'run': 0, \
    #                                         'machine': 'west_equinox', \
    #                                         'user': 'imas_private'}]

    def getAllEntries(self):
        return [(0, 'Equilibrium overview...')]

    def getDescription(self):
        """ Return plugin description.
        """

        return "Equilibrium plugin allows to plot magnetic surfaces, separatrix \n" \
               "and other equilibrium quantities as a function of time and space. \n" \
               "This demo demonstrates how to embed a matplotlib (mpl) \n" \
               "plot into a PyQt5 GUI application for IMAS visualization, \n" \
               "including: \n" \
               "* Using the navigation toolbar \n" \
               "* Adding data to the plot \n" \
               "* Dynamically modifying the plot's properties \n" \
               "* Processing mpl events \n" \
               "* Saving the plot to a file from a menu \n" \
               "The main goal is to serve as a basis for developing rich \n" \
               "PyQt5 GUI applications featuring mpl plots \n " \
               "(using the mpl OO API). \n" \
               "Jorge Morales (jorge.morales2@cea.fr) \n" \
               "Based on a work by: \n" \
               "Eli Bendersky (eliben@gmail.com) \n" \
               "Initially integrated in IMASViz using wxPython by: \n" \
               "Ludovic Fleury (ludovic.fleury@cea.fr) \n" \
               "Converted from wxPython to PyQt5 by: \n" \
               "Dejan Penko (dejan.penko@lecad.fs.uni-lj.si) \n" \
               "License: this code is in the public domain"


if (__name__ == '__main__'):
    # Test running. See also equilibrium test file.

    # A module providing a number of functions and variables that can be used to
    # manipulate different parts of the Python runtime environment.
    import sys
    # PyQt library imports
    from PySide2.QtWidgets import QApplication
    # IMASViz source imports
    from imasviz.Viz_API import Viz_API
    from imasviz.VizDataSource.QVizDataSourceFactory import \
        QVizDataSourceFactory
    from imasviz.VizUtils import QVizGlobalOperations

    # Set object managing the PyQt GUI application's control flow and main
    # settings
    app = QApplication(sys.argv)

    # Check if necessary system variables are set
    QVizGlobalOperations.checkEnvSettings()

    # Set Application Program Interface
    api = Viz_API()

    # Set data source retriever/factory
    dataSourceFactory = QVizDataSourceFactory()

    # Load IMAS database and build the data tree view frame
    f1 = api.CreateDataTree(dataSourceFactory.create(shotNumber=52344,
                                                     runNumber=0,
                                                     userName='g2penkod',
                                                     imasDbName='viztest'))

    # Get equilibrium treeWidget item (QVizTreeNode)
    eq_item = f1.dataTreeView.IDSRoots['equilibrium']

    # Get selected item/subject data dict
    dataDict = eq_item.getInfoDict()

    # Show the data tree view window
    # f1.show()

    # Get equilibrium data and set plugin frame
    app.frame = PlotFrame(dataDict, vizAPI=api, parent=f1.dataTreeView)

    # Show frame
    app.frame.show()

    # Keep the application running
    sys.exit(app.exec_())
