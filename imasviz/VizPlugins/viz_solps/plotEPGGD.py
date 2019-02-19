#! /usr/bin/env python3

import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QAction, \
                            QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, \
                            QSpacerItem, QSizePolicy, QPushButton
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize, pyqtSlot


import logging
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
import matplotlib.collections

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

import numpy as np

from getEPGGD import getEPGGD

class GetVars:
    names = ['SHOT', 'RUN', 'USER', 'DEVICE', 'VERSION']
    numOfParams = len(names)
    shot, run, user, device, version = range(numOfParams)

    defaultValues = {}
    defaultValues[shot] = '122264'
    defaultValues[run] = '1'
    defaultValues[user] = os.getenv('USER')
    defaultValues[device] = 'iter'
    defaultValues[version] = '3'

class plotEPGGD(QWidget):
    """Plot edge_profiles (EP) IDS GGD.
    """

    def __init__(self, parent=None, ids=None, *args, **kwargs):
        QWidget.__init__(self, parent)

        self.checkDisplay()

        self.ids = ids
        self.setLayout(QVBoxLayout())
        self.canvas = PlotCanvas(self, width=5, height=4)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout().addWidget(self.canvas)
        self.layout().addWidget(self.toolbar)
        self.resize(200,200)

    @pyqtSlot()
    def checkIDS(self):
        self.vars = {}
        # If IDS object is not provided, display dialog window where the IDS
        # parameters can be specified. Then open the specified IDS
        if self.ids != None:
            return
        else:
            from getIDS import GetIDSWrapper, GetDialog
            for i in range(GetVars.numOfParams):
                # At the begining clear all parameters
                self.vars[i] = ''

            dialog = GetDialog(self)
            dialog.prepareWidgets(self.vars)
            if dialog.exec_():
                self.vars = dialog.on_close()

            self.ids = GetIDSWrapper(self.vars).getIDS()

    @pyqtSlot()
    def plotData(self):
        """Populate (plot) the canvas.
        """
        self.canvas.plotData()

    @pyqtSlot( )
    def checkDisplay(self):
        try:
            os.environ['DISPLAY']
        except:
            logging.error('No display available!')

class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=10, height=8, dpi=100):

        self.parent = parent
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        FigureCanvas.__init__(self, self.figure)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    @pyqtSlot()
    def plotData(self):
        """Plots edge data to 2D VTK.
        """
        self.ids = self.parent.ids

        logging.info('Getting IDS')
        self.ids.edge_profiles.get()
        self.ep = self.ids.edge_profiles

        getGGD = getEPGGD(self.ep)

        self.num_obj_0D, self.num_obj_1D, self.num_obj_2D = getGGD.ggdCheck()

        # Reading IDS grid geometry and physics quantities array
        nodes = np.zeros(shape=(self.num_obj_0D, 2))
        quad_conn_array = np.zeros(shape=(self.num_obj_2D, 4), dtype=np.int)
        # quad_values_array = np.zeros(self.num_obj_2D)

        # List of nodes and corresponding coordinates (2D spade - x and y)
        for i in range(self.num_obj_0D):
            # X coordinate
            nodes[i][0] = self.ep.grid_ggd[0].space[0].objects_per_dimension[0].object[i].geometry[0]
            # Y coordinate
            nodes[i][1] = self.ep.grid_ggd[0].space[0].objects_per_dimension[0].object[i].geometry[1]

        # Connectivity array. Each quad is formed using 4 nodes/points
        for i in range(self.num_obj_2D):
            for j in range(0,4):
                quad_conn_array[i][j] = self.ep.grid_ggd[0].space[0].objects_per_dimension[2].object[i].nodes[j] - 1

        # print("quad_conn_array: ", quad_conn_array)

        # Values corresponding to quads


        # for i in range(self.num_obj_2D):
        #     quad_values_array[i] = i

        # TODO: check ... electrons.density[0].grid_subset_index etc.

        quad_values_array = self.ep.ggd[0].electrons.temperature[0].values

        self.showMeshPlot(nodes, quad_conn_array, quad_values_array)

    def showMeshPlot(self, nodes, elements, values):

        y = nodes[:,0]
        z = nodes[:,1]

        def quatplot(y,z, quatrangles, values, ax=None, **kwargs):

            if not ax: ax=plt.gca()
            yz = np.c_[y,z]
            verts= yz[quatrangles]
            white = (1,1,1,1)
            pc = matplotlib.collections.PolyCollection(verts,
                                                       edgecolor=white,
                                                       linewidths=(0.1,),
                                                       **kwargs)
            pc.set_array(values)
            ax.add_collection(pc)
            ax.autoscale()
            return pc

        ax = self.figure.add_subplot(111)
        ax.set_aspect('equal')

        pc = quatplot(y,z, np.asarray(elements), values, ax=ax,
                      cmap="plasma")
        self.figure.colorbar(pc, ax=ax)
        # ax.plot(y,z, marker="o", ls="", color="crimson")
        ax.plot(y,z, ls="", color="crimson")
        # Set background
        ax.set_facecolor((0.75, 0.75, 0.75))

        ax.set(title='This is the plot for: quad', xlabel='Y Axis', ylabel='Z Axis')

        self.draw()

if __name__ == '__main__':
    from getIDS import GetIDSWrapper, GetDialog, GetVars
    import getopt

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    root.addHandler(ch)

    app = QApplication(sys.argv)

    mainWindow = QMainWindow()

    # If any IDS parameters are given as an argument (via terminal), open the
    # specified IDS. Otherwise, open dialog where the parameters can be set
    if len(sys.argv) > 1:
        # Set IDS object, open it and provide it as an argument to plotEPGGD
        # Vars = {0: 122264, 1: 1, 2: 'penkod', 3: 'iter', 4: '3'}

        # For launching python script directly from terminal with python command
        Vars = {}
        Help = """
                This is used for testing the plotting data from an edge_profilesIDS.

                In order to run this plugin, shot, run, user, device and version must
                be defined. Example (terminal):

                python3 solpswidget.py --shot=122264 --run=1 --user=penkod \
                --device=iter --version=3

                """
        try:
            opts, args = getopt.getopt(sys.argv[1:], "srudvh", ["shot=",
                                                                "run=",
                                                                "user=",
                                                                "device=",
                                                                "version=",
                                                                "help"])

            for opt, arg in opts:
                # print opt, arg
                if opt in ("-s", "--shot"):
                    Vars[GetVars.shot] = int(arg)
                elif opt in ("-r", "--run"):
                    Vars[GetVars.run] = int(arg)
                elif opt in ("-u", "--user"):
                    Vars[GetVars.user] = arg
                elif opt in ("-t", "--device"):
                    Vars[GetVars.device] = arg
                elif opt in ("-v", "--version"):
                    Vars[GetVars.version] = arg
                if opt in ("-h", "--help"):
                    print(Help % (os.environ['USER'], os.path.expanduser('~')))
                    sys.exit()

            ids = GetIDSWrapper(Vars).getIDS()
            plotWidget = plotEPGGD(ids)

        except Exception:
            print('Supplied option not recognized!')
            print('For help: -h / --help')
            # sys.exit(2)
            print('Switching to dialog window')
            plotWidget = plotEPGGD()


        if len(Vars) < GetVars.numOfParams:
            print('Not enough variables defined!')
            print('For help: -h / --help')
            # sys.exit(2)
            print('Switching to dialog window')
            plotWidget = plotEPGGD()
        elif len(Vars) > GetVars.numOfParams:
            print('Too many variables defined!')
            print('For help: -h / --help')
            # sys.exit(2)
            print('Switching to dialog window')
            plotWidget = plotEPGGD()

    else:
        # Open IDS (specify parameters using dialog)
        plotWidget = plotEPGGD()

    plotWidget.checkIDS()

    plotWidget.plotData()

    title = 'Test: Plot edge_profiles GGD'

    mainWindow.setWindowTitle(title)

    widget =  QWidget(mainWindow)
    mainWindow.setCentralWidget(plotWidget)
    mainWindow.show()

    sys.exit(app.exec_())