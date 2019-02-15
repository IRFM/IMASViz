#! /usr/bin/env python3

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QAction, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpacerItem, QSizePolicy, QPushButton
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize

import logging
import matplotlib.pyplot as plt
import matplotlib.collections

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

import numpy as np

from getEPGGD import getEPGGD

import random

class plotEPGGD(QWidget):
    """Plot edge_profiles (EP) IDS GGD.
    """

    def __init__(self, ids, parent=None, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.ids = ids
        self.setLayout(QVBoxLayout())
        self.canvas = PlotCanvas(self, width=10, height=8)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.canvas)

class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=10, height=8, dpi=100):
        self.ids = parent.ids

        self.figure = Figure(figsize=(width, height), dpi=dpi)
        FigureCanvas.__init__(self, self.figure)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.plotData()

    def plotData(self):
        """Plots edge data to 2D VTK.
        """

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
    from getIDS import GetIDSWrapper

    app = QApplication(sys.argv)

    Vars = {0: 122264, 1: 1, 2: 'penkod', 3: 'iter', 4: '3'}
    ids = GetIDSWrapper(Vars).getIDS()
    plotWidget = plotEPGGD(ids)

    mainWindow = QMainWindow()
    title = 'Test: Plot edge_profiles GGD'

    mainWindow.setWindowTitle(title)

    widget =  QWidget(mainWindow)
    mainWindow.setCentralWidget(plotWidget)
    mainWindow.show()

    sys.exit(app.exec_())