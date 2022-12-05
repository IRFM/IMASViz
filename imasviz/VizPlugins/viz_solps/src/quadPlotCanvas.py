#! /usr/bin/env python3

#  Name   :quadPlotCanvas
#
#          Container to create canvas containing grid of quad elements with
#          corresponding quantity values.
#
#  Author :
#         Dejan Penko
#  E-mail :
#         dejan.penko@lecad.fs.uni-lj.si
#

import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
import matplotlib.collections

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

import numpy as np

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QSizePolicy

class QuadPlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=10, height=8, dpi=100):

        self.parent = parent

        self.figure = Figure(figsize=(width, height), dpi=dpi)
        FigureCanvas.__init__(self, self.figure)

        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    @Slot()
    def plotData(self, nodes, quad_conn_array, qValues, title='Plot'):
        """Plots edge data to 2D VTK.
        """

        self.title = title

        if len(nodes) < 1:
            logging.warning('Array of nodes coordinates is empty!')
            return

        if len(quad_conn_array) < 1:
            logging.warning('Quad connectivity array is empty!')
            return

        if len(qValues) < 1:
            logging.warning('Array of quantity values is empty!')
            return

        self.showMeshPlot(nodes, quad_conn_array, qValues)

    def showMeshPlot(self, nodes, elements, values):
        """Arrange the nodes, elements and values as needed and plot them to
        matplotlib canvas as PolyCollection.

        Arguments:
            nodes (2D array)    : Array of node/point coordinates
            elements (4D array) : Connectivity array for quad elements
            values (1D array)   : Quantities corresponding to the quad elements
        """

        y = nodes[:,0]
        z = nodes[:,1]

        def quadplot(y,z, quatrangles, values, ax=None, **kwargs):

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

        self.ax = self.figure.add_subplot(111)
        self.figure.subplots_adjust(right=0.85)
        self.ax.set_aspect('equal')

        pc = quadplot(y,z, np.asarray(elements), values, ax=self.ax,
                      cmap="plasma")
        self.figure.colorbar(pc, ax=self.ax)
        # self.ax.plot(y,z, marker="o", ls="", color="crimson")
        self.ax.plot(y,z, ls="", color="crimson")
        # Set background
        self.ax.set_facecolor((0.75, 0.75, 0.75))

        self.ax.set(title=self.title, xlabel='R[m] ', ylabel='Z[m]')

        self.draw()
