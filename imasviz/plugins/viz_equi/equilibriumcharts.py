# -*- coding: utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
# If you need to restart vim tabs then :retab
"""
This demo demonstrates how to embed a matplotlib (mpl) plot 
into a wxPython GUI application for IMAS visualization, including:
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
License: this code is in the public domain
Last modifications: 2017
"""

from __future__ import (unicode_literals, absolute_import,  \
                        print_function, division)
from datetime import datetime
import getpass
# The recommended way to use wx with mpl is with the WXAgg
# backend. 
import matplotlib
matplotlib.use('WXAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import \
    FigureCanvasWxAgg as FigCanvas, \
    NavigationToolbar2WxAgg as NavigationToolbar
import matplotlib.mlab      as mlab
import matplotlib.ticker    as tick
import matplotlib.tri       as tri
import numpy as np
import os
import sys
import wx

# Local python modules
import imas

from imasviz.plugins.VIZPlugins import VIZPlugins

# Figures options
nrow               = 2
ncol               = 2
nbr_levels         = 30  # For Psi (magnetic flux function)
fontsize_requested = 11  # Font size for axis labels and subfigure titles
fontsize_req_ticks = 10  # Font size for tick labels
fontsize_title     = 14  # Font size for title
grid_points_interp = 100 # Number of points in R and Z for cartesian grid interpolation
Z_for_B_NORM       = 49  # Position in Z for 1D plot in the cartesian grid

def DataGen(dictDataSource):

    # For test:
    #time_i = 10
    #time_e = 30
    #delta_t = 2
    #shot = 50355
    #run = 0
    #machine = 'west'
    #user = getpass.getuser()

    shot = dictDataSource['imasviz_view'].dataSource.shotNumber
    run = dictDataSource['imasviz_view'].dataSource.runNumber
    machine = dictDataSource['imasviz_view'].dataSource.imasDbName
    user = dictDataSource['imasviz_view'].dataSource.userName
    time_i  = dictDataSource['time_i']
    time_e  = dictDataSource['time_e']
    delta_t = dictDataSource['delta_t']
    # shot    = dictDataSource['shot']
    # run     = dictDataSource['run']
    # machine = dictDataSource['machine']
    # user    = dictDataSource['user']



    # Figures options
    nbr_levels         = 30  # For Psi (magnetic flux function)
    fontsize_requested = 11  # Font size for axis labels and subfigure titles
    fontsize_req_ticks = 10  # Font size for tick labels
    fontsize_title     = 14  # Font size for title
    grid_points_interp = 100 # Number of points in R and Z for cartesian grid interpolation
    Z_for_B_NORM       = 49  # Position in Z for 1D plot in the cartesian grid

    print('time initial =', time_i)
    print('time end     =', time_e)
    print('time step    =', delta_t)
    print('shot         =', shot)
    print('run          =', run)
    print('machine      =', machine)
    print('user         =', user)

    # Array with all times requested
    arrTimes = np.arange(time_i, time_e+delta_t, delta_t)
    print('arrTimes    =', arrTimes)

    time_requested = time_i

    # Open shot and run of machine
    imas_entry = imas.ids(shot, run, 0, 0)
    imas_entry.open_env(user, machine, '3')

    #imas_entry.equilibrium.get()
    
    lenArrTimes = len(arrTimes)
    timeEquiIDS = np.zeros(lenArrTimes) 

    for timeit in range(lenArrTimes):
        startTime = datetime.now()

        time_requested = arrTimes[timeit]

        # Function def getSlice(self, time_requested, interpolation_method, occurence=0)
        # -interpolation_method: 1 = closest time, 2 = previous time, 3 = linear
        #  interpolation
        imas_entry.equilibrium.getSlice(time_requested, 1)

        timeEquiIDS[timeit] = imas_entry.equilibrium.time
        print('-----')
        print('-----')
        print('-----')
        print('It:', timeit, ', time requested', time_requested, \
              ', time in equilibrium IDS =', timeEquiIDS[timeit])

        equi_prof = imas_entry.equilibrium.time_slice[0]

        # Some extra print
        print(' ')
        print('Profile of q at t =', imas_entry.equilibrium.time)
        print(equi_prof.profiles_1d.q)
        print('Profile of rho_tor at t =', imas_entry.equilibrium.time)
        print(equi_prof.profiles_1d.rho_tor)
        print('Profile of Psi at t =', imas_entry.equilibrium.time)
        print(equi_prof.profiles_1d.psi)

        equi_space = imas_entry.equilibrium.time_slice[0].ggd[0]

        if (timeit == 0):
            Nknots = len(equi_space.grid.space[0].objects_per_dimension[0].object)
            print('Nknots (number of grid points) =', Nknots)
            Rknots  = np.zeros(Nknots)
            Zknots  = np.zeros(Nknots)

            for i in range(Nknots):
                Rknots[i]  = equi_space.grid.space[0].objects_per_dimension[0]. \
                             object[i].geometry[0]
                Zknots[i]  = equi_space.grid.space[0].objects_per_dimension[0]. \
                             object[i].geometry[1]

            # Read triangle knots indices
            Ntri = len(equi_space.grid.space[0].objects_per_dimension[2].object)
            triKnots = np.zeros((Ntri, 3))
            print('Ntri (number of grid triangles) =', Ntri)
            for i in range(0,Ntri):
                triKnots[i,0] = equi_space.grid.space[0].objects_per_dimension[2]. \
                                object[i].nodes[0]
                triKnots[i,1] = equi_space.grid.space[0].objects_per_dimension[2]. \
                                object[i].nodes[1]
                triKnots[i,2] = equi_space.grid.space[0].objects_per_dimension[2]. \
                                object[i].nodes[2]

            min_Rknots  = np.min(Rknots)
            max_Rknots  = np.max(Rknots)
            min_Zknots  = np.min(Zknots)
            max_Zknots  = np.max(Zknots)

            # Create cartesian grid for interpolation of the data
            R_interp = np.linspace(min_Rknots, max_Rknots, grid_points_interp)
            Z_interp = np.linspace(min_Zknots, max_Zknots, grid_points_interp)

            Psi_val = np.zeros((lenArrTimes, Nknots))
            B_R     = np.zeros((lenArrTimes, Nknots))
            B_Z     = np.zeros((lenArrTimes, Nknots))
            B_tor   = np.zeros((lenArrTimes, Nknots))
            B_NORM  = np.zeros((lenArrTimes, Nknots))

            B_NORM_interp = np.zeros((lenArrTimes, len(R_interp), len(Z_interp)))

            min_Psi_val  = np.zeros(lenArrTimes)
            max_Psi_val  = np.zeros(lenArrTimes)
            min_B_NORM   = np.zeros(lenArrTimes)
            max_B_NORM   = np.zeros(lenArrTimes)

            levels1_requested = np.zeros((lenArrTimes, nbr_levels))
            levels2_requested = np.zeros((lenArrTimes, nbr_levels))

            print('length of rho_tor = ', len(equi_prof.profiles_1d.rho_tor))
            pressEqui    = np.zeros((lenArrTimes, len(equi_prof.profiles_1d.rho_tor)))
            PsiProf      = np.zeros((lenArrTimes, len(equi_prof.profiles_1d.rho_tor)))
            j_tor        = np.zeros((lenArrTimes, len(equi_prof.profiles_1d.rho_tor)))
            q_safe_fact  = np.zeros((lenArrTimes, len(equi_prof.profiles_1d.rho_tor)))
            rho_tor_norm = np.zeros((lenArrTimes, len(equi_prof.profiles_1d.rho_tor)))

        # Read [R,Z] coordinates of knots (dimension 0)
        for i in range(Nknots):
            Psi_val[timeit, i] = equi_space.psi[0].values[i]
            B_R[timeit, i]     = equi_space.b_field_r[0].values[i]
            B_Z[timeit, i]     = equi_space.b_field_z[0].values[i]
            B_tor[timeit, i]   = equi_space.b_field_tor[0].values[i]
        
        # Compute B_NORM
        B_NORM[timeit, :] = np.sqrt(np.square(B_R[timeit, :]) \
                                  + np.square(B_Z[timeit, :]) \
                                  + np.square(B_tor[timeit, :]))
        
        min_Psi_val[timeit] = np.min(Psi_val[timeit, :])
        max_Psi_val[timeit] = np.max(Psi_val[timeit, :])
        min_B_NORM[timeit]  = np.min(B_NORM[timeit, :])
        max_B_NORM[timeit]  = np.max(B_NORM[timeit, :])

        levels1_requested[timeit, :] = np.linspace(min_Psi_val[timeit], \
                                         max_Psi_val[timeit], nbr_levels)

        levels2_requested[timeit, :] = np.linspace(min_B_NORM[timeit], \
                                         max_B_NORM[timeit], nbr_levels)

        # Compute profiles pressure, Psi, j_tor, q and rho_tor_norm
        pressEqui[timeit, :]   = equi_prof.profiles_1d.pressure
        PsiProf[timeit, :]     = equi_prof.profiles_1d.psi
        j_tor[timeit, :]       = equi_prof.profiles_1d.j_tor
        q_safe_fact[timeit, :] = equi_prof.profiles_1d.q
        if (equi_prof.profiles_1d.rho_tor[-1] != 0.):
            rho_tor_norm[timeit, :] = equi_prof.profiles_1d.rho_tor \
                                    / equi_prof.profiles_1d.rho_tor[-1]
            rho_tor_label = 'rho_tor_norm'
        else:
            print('WARNING: final value of rho_tor (at separatrix) is:', \
                   equi_prof.profiles_1d.rho_tor[-1])
            print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            print('USING points instead of rho_tor_norm !!!')
            print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            rho_tor_norm[timeit, :] = np.linspace(0, 1,  \
                                      len(equi_prof.profiles_1d.rho_tor))
            rho_tor_label = 'Points equally spaced'

        # Interpolate B_NORM
        B_NORM_interp[timeit, :, :] = mlab.griddata(Rknots, Zknots, \
                                      B_NORM[timeit, :], R_interp, Z_interp, \
                                      interp='linear')
        
        # Print time of the loop
        print('Time loop', timeit, '=', datetime.now() - startTime)
        print('In DataDen id(Psi_val) =', id(Psi_val))

    return shot, run, machine, user, \
           timeEquiIDS, lenArrTimes, \
           Psi_val, Rknots, Zknots, triKnots, levels1_requested, \
           rho_tor_norm, rho_tor_label, q_safe_fact, j_tor, \
           PsiProf, pressEqui

class PlotFrame(wx.Frame):
    """ The main frame of the application
    """
    title = 'Equilibrium charts'

    def __init__(self, dictDataSource):
        wx.Frame.__init__(self, None, wx.ID_ANY, self.title)
        self.Bind(wx.EVT_CLOSE, self.on_exit)        

        self.shot,          self.run,               self.machine, \
        self.user,          self.timeEquiIDS,       self.lenArrTimes,\
        self.Psi_val,       self.Rknots,            self.Zknots, \
        self.triKnots,      self.levels1_requested, self.rho_tor_norm, \
        self.rho_tor_label, self.q_safe_fact,       self.j_tor, \
        self.PsiProf,       self.pressEqui = DataGen(dictDataSource)

        print('In init PlotFrame id(self.Psi_val) =',    id(self.Psi_val))
        print('In init PlotFrame type(self.Psi_val) =',  type(self.Psi_val))
        print('In init PlotFrame type(self.triKnots) =', type(self.triKnots))

        self.dataTimes = [self.timeEquiIDS[0], self.timeEquiIDS[-1]]
        self.boolOnTextEnter = False

        self.create_menu()
        self.create_status_bar()
        self.create_main_panel()
        
        self.redraw_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_redraw_timer, self.redraw_timer)        

        self.textbox.SetValue(' '.join(map(str, self.dataTimes)))
        self.draw_figure()

    def create_menu(self):
        self.menubar = wx.MenuBar()
        
        menu_file = wx.Menu()
        m_expt = menu_file.Append(wx.ID_SAVE, "Save plot\tCtrl-S", "Save plot to file")
        self.Bind(wx.EVT_MENU, self.on_save_plot, m_expt)
        menu_file.AppendSeparator()
        m_exit = menu_file.Append(wx.ID_EXIT, "Exit\tCtrl-X", "Exit")
        self.Bind(wx.EVT_MENU, self.on_exit, m_exit)
        
        menu_help = wx.Menu()
        m_about = menu_help.Append(wx.ID_ABOUT, "About\tF1", "About the demo")
        self.Bind(wx.EVT_MENU, self.on_about, m_about)
        
        self.menubar.Append(menu_file, "File")
        self.menubar.Append(menu_help, "Help")
        self.SetMenuBar(self.menubar)

    def create_main_panel(self):
        """ Creates the main panel with all the controls on it:
             * mpl canvas 
             * mpl navigation toolbar
             * Control panel for interaction
        """
        self.panel = wx.Panel(self)
        
        # Create the mpl Figure and FigCanvas objects. 
        # 100 dots-per-inch
        self.dpi = 110
        self.fig = Figure(dpi=self.dpi)
        self.canvas = FigCanvas(self.panel, wx.ID_ANY, self.fig)
        

        self.fig.subplots_adjust(left=0.1, right=0.9, bottom=0.1, top=0.9, \
                                 wspace=0.6, hspace=0.6)

        self.fig.suptitle('Equilibrium' \
                        + '       ' + 'Shot: ' + str(self.shot) + '    run: ' \
                        + str(self.run) + '    ' + 'machine: ' + self.machine \
                        + '    user: '  + self.user) #, fontsize=fontsize_title)

        # Since we have only one plot, we can use add_axes 
        # instead of add_subplot, but then the subplot
        # configuration tool in the navigation toolbar wouldn't
        # work.
        self.numAxes = (nrow*ncol + 1)
        self.axes    = [None]*self.numAxes
        #for nplt in range(nrow*ncol):
        #    print('nplt =', nplt)
        #    self.axes[nplt] = self.fig.add_subplot(nrow, ncol, nplt+1)
        
        self.axes[0] = self.fig.add_subplot(1, 3, 1)
        self.axes[1] = self.fig.add_subplot(2, 3, 2)
        self.axes[2] = self.fig.add_subplot(2, 3, 3)
        self.axes[3] = self.fig.add_subplot(2, 3, 5)
        self.axes[4] = self.fig.add_subplot(2, 3, 6)

        # Bind the 'pick' event for clicking on one of the bars
        self.canvas.mpl_connect('pick_event', self.on_pick)
        
        self.cb_grid = wx.CheckBox(self.panel, wx.ID_ANY, \
                                   'Grid', \
                                   style=wx.ALIGN_RIGHT)
        #self.Bind(wx.EVT_CHECKBOX, self.on_cb_grid, self.cb_grid)
        self.cb_grid.Bind(wx.EVT_CHECKBOX, self.on_cb_grid)

        self.textbox = wx.TextCtrl(
            self.panel, 
            size=(100,-1),
            style=wx.TE_PROCESS_ENTER)
        #self.Bind(wx.EVT_TEXT_ENTER, self.on_text_enter, self.textbox)
        self.textbox.Bind(wx.EVT_TEXT_ENTER, self.on_text_enter)
        
        self.drawbutton = wx.Button(self.panel, wx.ID_ANY, 'Run')
        #self.Bind(wx.EVT_BUTTON, self.on_draw_button, self.drawbutton)
        self.drawbutton.Bind(wx.EVT_BUTTON, self.on_draw_button)

        self.slider_time = wx.Slider(self.panel, wx.ID_ANY, \
                                      value=0, \
                                      minValue=0, \
                                      maxValue=(self.lenArrTimes-1), \
                                      size=wx.Size(500,-1))
        # For more Slider options:
        #size=wx.DefaultSize
        #style=wx.SL_AUTOTICKS | wx.SL_LABELS
        #self.slider_time.SetTickFreq(10) #(10, 1)
        #self.Bind(wx.EVT_COMMAND_SCROLL_CHANGED, \
        #          self.on_slider_time, self.slider_time)
        self.slider_time.Bind(wx.EVT_COMMAND_SCROLL_CHANGED, \
                               self.on_slider_time)

        self.textbox_label = wx.StaticText(self.panel, wx.ID_ANY, \
                                          'Time values list: ')

        # Create the navigation toolbar, tied to the canvas
        self.toolbar = NavigationToolbar(self.canvas)
        
        # Layout with box sizers
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.toolbar, 0, wx.EXPAND)
        self.vbox.Add(self.canvas, 1, wx.CENTER | wx.GROW)
        self.vbox.AddSpacer(20)
        
        self.hbox = wx.BoxSizer(wx.HORIZONTAL)
        flags  = wx.ALIGN_LEFT | wx.ALL | wx.ALIGN_CENTER_VERTICAL
        flags2 = wx.ALIGN_LEFT | wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.EXPAND
        self.hbox.AddSpacer(10)
        self.hbox.Add(self.cb_grid, 0, border=5, flag=flags)
        self.hbox.AddSpacer(10)
        self.hbox.Add(self.textbox_label, 0, border=5, flag=flags)
        self.hbox.Add(self.textbox, 0, border=5, flag=flags)
        self.hbox.AddSpacer(10)
        self.hbox.Add(self.drawbutton, 0, border=5, flag=flags)
        self.hbox.AddSpacer(10)
        self.hbox.Add(self.slider_time, 1, border=5, flag=flags2)
        self.hbox.AddSpacer(10)
        
        self.vbox.Add(self.hbox, 0, flag=wx.CENTER | wx.TOP)
        self.vbox.AddSpacer(20)
        
        self.panel.SetSizer(self.vbox)
        self.vbox.Fit(self)
    
    def create_status_bar(self):
        self.statusbar = self.CreateStatusBar()

    def draw_figure(self):
        """ Draws figure
        """
        sliderValue = int(round(self.slider_time.GetValue()))
        print('In draw_figure, self.slider_time.GetValue = ', sliderValue)

        if (not self.boolOnTextEnter):
            self.timeText = self.axes[0].text(0.5, 1.25, \
                                        'Time = ' \
                                        + str(self.timeEquiIDS[sliderValue]), \
                                        horizontalalignment='center', \
                                        verticalalignment='center', \
                                        transform=self.axes[0].transAxes, \
                                        fontsize=14)
        else:
            self.timeText.set_text('')

        self.axes[0].tricontour(self.Rknots, self.Zknots, self.triKnots, \
                                self.Psi_val[sliderValue], \
                                colors='blue', \
                                linestyles='solid', linewidths=0.5, \
                                levels=self.levels1_requested[sliderValue, :])
        self.axes[0].set(aspect=1)
        self.axes[0].set_title(   'Psi')
        self.axes[0].set_xlabel('R [m]')
        self.axes[0].set_ylabel('Z [m]')

        self.plt1, = self.axes[1].plot(self.rho_tor_norm[sliderValue], \
                                       self.q_safe_fact[sliderValue])   
        self.axes[1].set_xlabel(self.rho_tor_label)
        self.axes[1].set_ylabel('Safety factor q')
        if (self.boolOnTextEnter):
            print('In set_label')
            self.plt1.set_label('t = ' + str(self.timeEquiIDS[sliderValue]))
            self.axes[1].legend()

        self.plt2, = self.axes[2].plot(self.rho_tor_norm[sliderValue], \
                                       self.j_tor[sliderValue])   
        self.axes[2].set_xlabel(self.rho_tor_label)
        self.axes[2].set_ylabel('j tor [A/m^2]')

        self.plt3, = self.axes[3].plot(self.rho_tor_norm[sliderValue], \
                                       self.PsiProf[sliderValue])   
        self.axes[3].set_xlabel(self.rho_tor_label)
        self.axes[3].set_ylabel('Psi [Wb]')

        self.plt4, = self.axes[4].plot(self.rho_tor_norm[sliderValue], \
                                       self.pressEqui[sliderValue])   
        self.axes[4].set_xlabel(self.rho_tor_label)
        self.axes[4].set_ylabel('P [Pa]')

        self.canvas.draw()

    def update_figure(self):
        """ Updates the figure
        """
        sliderValue = int(round(self.slider_time.GetValue()))
        #print('self.slider_time.GetValue = ', sliderValue)

        #self.timeText.set_text('Time = ' + str(self.timeEquiIDS[sliderValue]))

        self.axes[0].cla()
        self.timeText = self.axes[0].text(0.5, 1.25, \
                                    'Time = ' \
                                    + str(self.timeEquiIDS[sliderValue]), \
                                    horizontalalignment='center', \
                                    verticalalignment='center', \
                                    transform=self.axes[0].transAxes, \
                                    fontsize=14)
        self.axes[0].tricontour(self.Rknots, self.Zknots, self.triKnots, \
                                self.Psi_val[sliderValue], \
                                colors='blue', \
                                linestyles='solid', linewidths=0.5, \
                                levels=self.levels1_requested[sliderValue, :])
        self.axes[0].set(aspect=1)
        self.axes[0].set_title(   'Psi')
        self.axes[0].set_xlabel('R [m]')
        self.axes[0].set_ylabel('Z [m]')
        if (self.cb_grid.IsChecked()):
            self.axes[0].minorticks_on()
            self.axes[0].grid(b=True, which='major', linestyle='-', \
                             linewidth=0.5)
            self.axes[0].grid(b=True, which='minor', linestyle=':', \
                                  linewidth=0.2)

        self.plt1.set_ydata(self.q_safe_fact[sliderValue])
        self.axes[1].relim()
        self.axes[1].autoscale_view(scalex=False)

        self.plt2.set_ydata(self.j_tor[sliderValue])   
        self.axes[2].relim()
        self.axes[2].autoscale_view(scalex=False)

        self.plt3.set_ydata(self.PsiProf[sliderValue])   
        self.axes[3].relim()
        self.axes[3].autoscale_view(scalex=False)

        self.plt4.set_ydata(self.pressEqui[sliderValue])   
        self.axes[4].relim()
        self.axes[4].autoscale_view(scalex=False)

        self.canvas.draw()
    
    def on_cb_grid(self, event):
        if (self.cb_grid.IsChecked()):
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
    
    def on_text_enter(self, event):
        if (self.redraw_timer.IsRunning()):
            self.redraw_timer.Stop()
            self.drawbutton.SetLabel('Run')
        for it_ax in range(self.numAxes):
            self.axes[it_ax].cla()
        if (self.cb_grid.IsChecked()):
            self.on_cb_grid(wx.EVT_CHECKBOX)
        str_in = self.textbox.GetValue()
        self.dataTimes = map(float, str_in.split())
        print('self.dataTimes =', self.dataTimes)
        if (self.dataTimes):
            self.boolOnTextEnter = True
            for varTime in self.dataTimes:
                idxTime = (np.abs(self.timeEquiIDS-varTime)).argmin()
                print('idxTime =', idxTime)
                self.slider_time.SetValue(idxTime)
                self.draw_figure()
        else:
            self.boolOnTextEnter = False
            self.slider_time.SetValue(0)
            self.draw_figure()

    def on_draw_button(self, event):
        if (self.redraw_timer.IsRunning()):
            self.redraw_timer.Stop()
            self.drawbutton.SetLabel('Run')
        else:
            if (self.boolOnTextEnter):
                self.boolOnTextEnter = False
                for it_ax in range(self.numAxes):
                    self.axes[it_ax].cla()
                if (self.cb_grid.IsChecked()):
                    self.on_cb_grid(wx.EVT_CHECKBOX)
                self.draw_figure()
            self.it_data = int(round(self.slider_time.GetValue()))
            self.redraw_timer.Start(1000)
            self.drawbutton.SetLabel('Stop')

    def on_redraw_timer(self, event):
        self.slider_time.SetValue(self.it_data)
        self.update_figure()
        if (self.it_data < (self.lenArrTimes - 1)):
            self.it_data += 1
        else:
            self.it_data = 0

    def on_slider_time(self, event):
        if (self.redraw_timer.IsRunning()):
            self.redraw_timer.Stop()
            self.drawbutton.SetLabel('Run')
        if (self.boolOnTextEnter):
            self.boolOnTextEnter = False
            for it_ax in range(self.numAxes):
                self.axes[it_ax].cla()
            if (self.cb_grid.IsChecked()):
                self.on_cb_grid(wx.EVT_CHECKBOX)
            self.draw_figure()
        else:
            self.update_figure()

    def on_pick(self, event):
        # The event received here is of the type
        # matplotlib.backend_bases.PickEvent
        #
        # It carries lots of information, of which we're using
        # only a small amount here.
        # 
        box_points = event.artist.get_bbox().get_points()
        msg = "You've clicked on a bar with coords:\n %s" % box_points
        
        dlg = wx.MessageDialog(self, \
                               msg, \
                               "Click!", \
                               wx.OK | wx.ICON_INFORMATION)

        dlg.ShowModal() 
        dlg.Destroy()        
    
    def on_save_plot(self, event):
        file_choices = "PNG (*.png)|*.png"
        
        dlg = wx.FileDialog(self, \
                            message="Save plot as...", \
                            defaultDir=os.getcwd(), \
                            defaultFile="plot.png", \
                            wildcard=file_choices, \
                            style=wx.FD_SAVE)
        
        if (dlg.ShowModal() == wx.ID_OK):
            path = dlg.GetPath()
            self.canvas.print_figure(path, dpi=self.dpi)
            self.flash_status_message("Saved to %s" % path)
        
    def on_exit(self, event):
        self.redraw_timer.Stop()
        self.Destroy()
        
    def on_about(self, event):
        msg = """ A demo using wxPython with matplotlib:
        
         * Use the matplotlib navigation bar
         * Add values to the text box and press Enter (or click "Draw!")
         * Show or hide the grid
         * Drag the slider to modify the width of the bars
         * Save the plot to a file using the File menu
         * Click on a bar to receive an informative message
        """
        dlg = wx.MessageDialog(self, msg, "About", wx.OK)
        dlg.ShowModal()
        dlg.Destroy()
    
    def flash_status_message(self, msg, flash_len_ms=1500):
        self.statusbar.SetStatusText(msg)
        self.timeroff = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, \
                  self.on_flash_status_off, \
                  self.timeroff)
        self.timeroff.Start(flash_len_ms, oneShot=True)
    
    def on_flash_status_off(self, event):
        self.statusbar.SetStatusText('')

class equilibriumcharts(VIZPlugins):
    def __init__(self):
        pass
    def execute(self, app, dictDataSource):
        self.frame = PlotFrame(dictDataSource)
        self.frame.Show()
        app.MainLoop()

    # def getSubjects(self):
    #     subjects = {'overview':'Equilibrium overview...'}
    #     return subjects

    def getEntriesPerSubject(self):
        return {'equilibrium_overview':[0], 'overview':[0]}

    def getAllEntries(self):
        return [(0, 'Equilibrium overview...')] #(config number, description)


if (__name__ == '__main__'):
    app = wx.App()
    dictDataSource = {'time_i': 10,
                      'time_e': 20,
                      'delta_t': 5,
                      'shot': 50355,
                      'run': 0,
                      'machine': 'west',
                      'user': getpass.getuser()}
    #importedClass = my_import('equilibriumcharts')
    #pluginEquiPlot = importedClass()
    #pluginEquiPlot.execute(dictDataSource)
    app.frame = PlotFrame(dictDataSource)
    app.frame.Show()
    app.MainLoop()
