from imasviz.VizPlugins.VizPlugins import VizPlugins
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal import QVizPlotSignal
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizGUI.VizPlot.QVizCustomPlotContextMenu \
    import QVizCustomPlotContextMenu
from imasviz.VizDataAccess.QVizDataAccessFactory import QVizDataAccessFactory
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

            logging.info('Data:' + self.selectedTreeNode.getDataName())
            logging.info('Data param.:' + self.selectedTreeNode.getParametrizedDataPath())
            logging.info('coordinate1:' + self.selectedTreeNode.getParametrizedCoordinate(coordinateNumber=1))

            figureKey, plotWidget = vizAPI.CreatePlotWidget()
            dataAccess = QVizDataAccessFactory(self.dataTreeView.dataSource).create()
            signal = dataAccess.GetSignal(self.selectedTreeNode, plotWidget=plotWidget)

            t = QVizPlotSignal.getTime(signal)
            # v = QVizPlotSignal.get1DSignalValue(signal)
            # logging.info('Plotting signal')
            #plotWidget.plot(vizTreeNode=self.selectedTreeNode, x=t[0], y=v[0])
            #data = np.random.normal(size=(100, 200))
            # img = pg.gaussianFilter(np.random.normal(size=(200, 200)), (5, 5)) * 20 + 100
            # img = img[np.newaxis, :, :]
            # decay = np.exp(-np.linspace(0, 0.3, 100))[:, np.newaxis, np.newaxis]
            # data = np.random.normal(size=(100, 200, 200))
            # data += img * decay
            # data += 2
            #
            # ## Add time-varying signal
            # sig = np.zeros(data.shape[0])
            # sig[30:] += np.exp(-np.linspace(1, 10, 70))
            # sig[40:] += np.exp(-np.linspace(1, 10, 60))
            # sig[70:] += np.exp(-np.linspace(1, 10, 30))
            #
            # sig = sig[:, np.newaxis, np.newaxis] * 3
            # data[:, 50:60, 30:40] += sig
            pg.image(data)
            #imv.setImage(data, xvals=np.linspace(1., 3., data.shape[0]))

            # plwg = plotWidget.pgPlotWidget
            #
            # #cfset = ax.contourf(xx, yy, f, cmap=cmap)
            ## Set a custom color map
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
            # Show the widget window
            #plotWidget.show()

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
