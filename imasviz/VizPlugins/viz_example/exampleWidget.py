#! /usr/bin/env python3

import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QVBoxLayout, QSizePolicy
from PyQt5.QtCore import pyqtSlot

import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

import random
import imas

class exampleWidget(QWidget):

    def __init__(self, parent=None, ids=None, *args, **kwargs):
        QWidget.__init__(self, parent)

        # Check if display is available (display is mandatory, as this is
        # PyQt5 widget)
        self.checkDisplay()

        self.ids = ids

        # Set IDS case parameters
        # - Empty dictionary
        self.idsParameters = {}
        # - shot
        self.idsParameters['shot'] = '52344'
        # - run r
        self.idsParameters['run'] = '0'
        # - user
        self.idsParameters['user'] = os.getenv('USER')
        # - device / machine / database name
        self.idsParameters['device'] = 'viztest'
        # - IMAS major version (3.x.y)
        self.idsParameters['IMAS major version'] = '3'
        # - label of the IDS to be used
        self.idsParameters['idsName'] = 'magnetics'

        # Set IDS object
        self.ids = ids
        # Set widget layout
        self.setLayout(QVBoxLayout())
        # Set empty matplotlib canvas
        self.canvas = PlotCanvas(self)
        # Set matplotlib toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        # Add widgets to layout
        self.layout().addWidget(self.canvas)
        self.layout().addWidget(self.toolbar)

    @pyqtSlot()
    def plotFluxAoS(self):
        """Plot Flux Loop arrays to canvas.
        """
        self.canvas.plotFluxAoS(self.ids)

    @pyqtSlot()
    def plotBPolAoS(self):
        """Plot poloidal field probe arrays to canvas.
        """
        self.canvas.plotBPolAoS(self.ids)

    @pyqtSlot()
    def openIDS(self):
        """Open magnetics IDS.
        """
        self.ids = imas.ids(int(self.idsParameters['shot']),
                            int(self.idsParameters['run']))
        # logging.info('Opening IDS')
        self.ids.open_env(self.idsParameters['user'],
                          self.idsParameters['device'],
                          self.idsParameters['IMAS major version'])
        # if self.ids.isConnected():
        #     # logging.info('IDS opened OK!')
        #     return True
        # else:
        #     # logging.error('IDS open failed!')
        #     return False

        self.ids.magnetics.get()

    def getIDS(self):
        return self.ids

    @pyqtSlot(str)
    def setShot(self, shot):
        self.idsParameters['shot'] = shot

    def getShot(self):
        return self.idsParameters['shot']

    @pyqtSlot(str)
    def setRun(self, run):
        self.idsParameters['run'] = run

    def getRun(self):
        return self.idsParameters['run']

    @pyqtSlot(str)
    def setUser(self, user):
        self.idsParameters['user'] = user

    def getUser(self):
        return self.idsParameters['user']

    @pyqtSlot(str)
    def setDevice(self, device):
        self.idsParameters['device'] = device

    def getDevice(self):
        return self.idsParameters['device']

    @pyqtSlot(str)
    def setIMASmVer(self, ver):
        self.idsParameters['IMAS major version'] = ver

    def getIMASmVer(self):
        return self.idsParameters['IMAS major version']

    @pyqtSlot(str)
    def setIDSname(self, idsName):
        self.idsParameters['idsName'] = idsName

    def getIDSname(self):
        return self.idsParameters['idsName']

    @pyqtSlot()
    def checkDisplay(self):
        try:
            os.environ['DISPLAY']
        except:
            logging.error('No display available!')

class PlotCanvas(FigureCanvas):

    def __init__(self, parent=None, width=5, height=4, dpi=100):


        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                                   QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def plotFluxAoS(self, ids=None):
        """Plot values found in flux loops AoS.
        """
        self.ids = ids
        ax = self.figure.add_subplot(111)
        num_flux_loop_AoS = len(self.ids.magnetics.flux_loop)
        for i in range(num_flux_loop_AoS):
            data = self.ids.magnetics.flux_loop[i].flux.data
            ax.plot(data, '-')
        ax.set_title('Flux loop plots')
        self.draw()

    def plotBPolAoS(self, ids=None):
        """Plot poloidal field probe values.
        """
        self.ids = ids
        ax = self.figure.add_subplot(111)
        num_bpol_probe_AoS = len(self.ids.magnetics.bpol_probe)
        for i in range(num_bpol_probe_AoS):
            data = self.ids.magnetics.bpol_probe[i].field.data
            ax.plot(data, '-')
        ax.set_title('Poloidal field probe plots')
        self.draw()

if __name__ == '__main__':
    # Set application object
    app = QApplication(sys.argv)
    # Set main PyQt5 window
    mainWindow = QMainWindow()
    # Set window title
    mainWindow.setWindowTitle('Example Widget')
    # Set example widget object
    ew = exampleWidget()
    # Open IDS (magnetics IDS)
    ew.openIDS()
    # Plot Flux Loop arrays
    ew.plotFluxAoS()
    # Plot poloidal field probe arrays (an option other than plotFluxAoS)
    # ew.plotBPolAoS()
    # Set example widget as a central widget of the main window
    mainWindow.setCentralWidget(ew)
    # Show the main window
    mainWindow.show()
    # Keep the application running (until the 'exit application' command is
    # executed
    sys.exit(app.exec_())
