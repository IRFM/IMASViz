from imasviz.VizPlugins.VizPlugins import VizPlugins
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal import QVizPlotSignal
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
import traceback, logging, os, sys
import numpy as np
from PyQt5.QtWidgets import QInputDialog, QLineEdit
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg

class viz_1D_overtime_plugin(VizPlugins):
    def __init__(self, *args, **kwargs):
        VizPlugins.__init__(self, *args, **kwargs)

    def execute(self, vizAPI):

        try:
            logging.info('viz_1D_overtime_plugin to be executed...')

            logging.info('Data :' + self.selectedTreeNode.getDataName())
            logging.info('Data param. :' + self.selectedTreeNode.getParametrizedDataPath())
            logging.info('coordinate1 :' + self.selectedTreeNode.getParametrizedCoordinate(1))

            ## Create window with ImageView widget
            # win = QtGui.QMainWindow()
            # win.resize(800, 800)
            # imv = pg.ImageView()
            # win.setCentralWidget(imv)
            # win.show()
            # win.setWindowTitle('pyqtgraph example: ImageView')

            # figureKey, plotWidget = vizAPI.CreatePlotWidget()
            # plwg = plotWidget.pgPlotWidget
            #
            # #cfset = ax.contourf(xx, yy, f, cmap=cmap)
            #
            # imv = pg.ImageView()
            # plwg.setCentralWidget(imv)
            #
            # ## Display the data and assign each frame a time value from 1.0 to 3.0
            # imv.setImage(data, xvals=np.linspace(1., 3., data.shape[0]))
            #
            # ## Set a custom color map
            # colors = [
            #     (0, 0, 0),
            #     (45, 5, 61),
            #     (84, 42, 55),
            #     (150, 87, 60),
            #     (208, 171, 141),
            #     (255, 255, 255)
            # ]
            # cmap = pg.ColorMap(pos=np.linspace(0.0, 1.0, 6), color=colors)
            # imv.setColorMap(cmap)

        except :
            traceback.print_exc()
            logging.error(traceback.format_exc())


    def getEntriesPerSubject(self):
        return {'FLT_1D':[0]}

    def getAllEntries(self):
        return [(0, '2D plot over time...')]

    def getPluginsConfiguration(self):
        return [{}]

    def isEnabled(self):
        return True
