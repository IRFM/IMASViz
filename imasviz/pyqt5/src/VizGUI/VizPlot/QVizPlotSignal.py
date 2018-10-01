#  Name   : QVizPlotSignal
#
#          Container to handle plotting of signals/nodes.
#          Note: The wxPython predecessor of this Python file is
#          PlotSignal.py
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#  TODO:
#
#    - Function definitions (from PlotSignal class)
#    def onHide
#    def getSignal
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#****************************************************

from imasviz.gui_commands.AbstractCommand import AbstractCommand
from imasviz.signals_data_access.SignalDataAccessFactory import SignalDataAccessFactory
from imasviz.util.GlobalOperations import GlobalOperations
# from imasviz.plotframes.IMASVIZPlotFrame import IMASVIZPlotFrame
# import matplotlib.pyplot as plt
import traceback
import sys
from PyQt5 import QtGui, QtCore
from imasviz.pyqt5.src.VizGUI.VizPlot.VizPlotFrames.QVizPlotWidget import QVizPlotWidget
from imasviz.pyqt5.src.VizGUI.VizPlot.VizPlotFrames.QVizPlotServices import QVizPlotServices

class QVizPlotSignal(AbstractCommand):
    def __init__(self, dataTreeView, nodeData = None, signal = None,
                 figureKey = None, title = '', label = None, xlabel = None,
                 update = 0, signalHandling = None):
        AbstractCommand.__init__(self, dataTreeView, nodeData)

        self.updateNodeData();

        self.signalHandling = signalHandling

        if signal == None:
            signalDataAccess = \
                SignalDataAccessFactory(self.dataTreeView.dataSource).create()
            treeNode = \
                self.dataTreeView.getNodeAttributes(self.nodeData['dataName'])
            self.signal = signalDataAccess.GetSignal(self.nodeData,
                            self.dataTreeView.dataSource.shotNumber, treeNode)
        else:
            self.signal = signal

        # Set widget window title by getting the next figure number
        if figureKey == None:
            self.figureKey = \
                self.dataTreeView.imas_viz_api.GetNextKeyForFigurePlots()
        else:
            self.figureKey = figureKey

        self.title = title

        if label == None:
            self.label = self.nodeData['Path']
        else:
            self.label = label

        self.xlabel = xlabel
        self.update = update
        self.plotFrame = None

    def execute(self):
        try:
            if len(self.signal) == 2:
                t = QVizPlotSignal.getTime(self.signal)
                v = QVizPlotSignal.get1DSignalValue(self.signal)
                self.plot1DSignal(self.dataTreeView.shotNumber, t, v,
                                  self.figureKey, self.title, self.label,
                                  self.xlabel, self.update)
            else:
                raise ValueError("only 1D plots are currently supported.")
        except ValueError as e:
            self.dataTreeView.log.error(str(e))

    def getPlotWidget(self, figureKey=0):
        api = self.dataTreeView.imas_viz_api
        if figureKey in api.figureframes:
            self.plotWidget = api.figureframes[figureKey]
        else:
            figureKey = api.GetNextKeyForFigurePlots()
            self.plotWidget = QVizPlotWidget(size=(600,500), title=figureKey)
            # self.plotWidget = \
            #     IMASVIZPlotFrame(None, size=(600, 500), title=figureKey,
            #                      signalHandling=self.signalHandling)
            api.figureframes[figureKey] = self.plotWidget

    @staticmethod
    def getTime(oneDimensionSignal):
        return oneDimensionSignal[0]

    @staticmethod
    def get1DSignalValue(oneDimensionSignal):
        """Returns the signal values of a 1D signal returned by
           get1DSignal(signalName, shotNumber)
        """
        return oneDimensionSignal[1]

    def plot1DSignal(self, shotNumber, t, v, figureKey=0, title='', label=None,
                     xlabel=None, update=0):
        """Plot a 1D signal as a function of time.

        Arguments:
            shotnumber (int) : IDS database parameter - shot number of the case.
            t     (2D array) : 2D array of time values.
            v     (2D array) : 2D array of physical quantity values.
            figureKey  (str) : Label for the figure frame window.
            title      (str) : Plot title.
            label      (str) : Label describing IMAS database (device, shot) and
                               path to signal/node in IDS database structure.
            xlabel     (str) : Plot X-axis label.
            update     (int) : Plot update parameter (0 or 1). Set to 1 when
                               adding additional plot lines to an already
                               existing plot.
        """

        try:
            # Update node data
            self.updateNodeData()

            # Set IMASViz api
            api = self.dataTreeView.imas_viz_api
            self.getPlotWidget(self.figureKey)

            # fig =  self.plotFrame.get_figure()

            key = self.dataTreeView.dataSource.dataKey(self.nodeData)
            tup = (self.dataTreeView.dataSource.shotNumber, self.nodeData)
            api.addNodeToFigure(figureKey, key, tup)

            # Shape of the signal
            nbRows = v.shape[0]

            # Set plot options
            label, xlabel, ylabel, title = \
                self.plotOptions(self.dataTreeView, self.nodeData,
                                 shotNumber=shotNumber, label=label,
                                 xlabel=xlabel, title=self.figureKey)
            if update == 1:
                # Add plot to existing plot
                for i in range(0, nbRows):
                    u = v[i]
                    # ti = t[i]
                    ti = t[0]
                    # plotWidget_2 = QVizPlotServices().plot(x=ti, y=u, title=title, pen='b')
                    self.plotWidget.plot(x=ti, y=u, label=label)
            else:
                # Create new plot
                for i in range(0, nbRows):
                    u = v[i]
                    ti = t[0]

                    if i == 0:
                        # New plot
                        # plotWidget_2 = QVizPlotServices().plot(x=ti, y=u, title=title, pen='b')
                        # Automaticaly creates three different-colored pens (Not yet implemented)
                        # self.plotWidget.plot(x=ti, y=u, xlabel=xlabel, ylabel=ylabel, pen=(i, nbRows))
                        self.plotWidget.plot(x=ti, y=u, label=label, xlabel=xlabel,
                                        ylabel=ylabel)
                    else:
                        # Add plot
                        self.plotWidget.plot(x=ti, y=u, label=label, pen=(i, nbRows))

            # api.figureframes[figureKey] = plotWidget_2
            self.plotWidget.show()

        except:
            traceback.print_exc(file=sys.stdout)
            raise

    @staticmethod
    def plotOptions(dataTreeView, signalNodeData, shotNumber=None, title='',
                    label=None, xlabel=None):
        """Set plot options.

        Arguments:
            dataTreeView (QTreeWidget) : QVizDataTreeView object.
            signalNodeData   : Tree signal/item/node data.
            shotnumber (int) : IDS database parameter - shot number of the case.
            title      (str) : Plot title.
            label      (str) : Label describing IMAS database (device, shot) and
                               path to signal/node in IDS database structure.
            xlabel     (str) : Plot X-axis label.
        """

        t = dataTreeView.getNodeAttributes(signalNodeData['dataName'])

        if label == None:
            label = signalNodeData['Path']

        if xlabel == None:
            if 'coordinate1' in signalNodeData:
                xlabel = \
                    GlobalOperations.replaceBrackets(signalNodeData['coordinate1'])
            if xlabel != None and xlabel.endswith("time"):
                xlabel +=  "[s]"

        #ylabel = signalNodeData['dataName']

        ylabel = 'S(t)'
        if t != None and not (t.isCoordinateTimeDependent(t.coordinate1)):
           ylabel = 'S'

        if 'units' in signalNodeData:
            units = signalNodeData['units']
            ylabel += '[' + units + ']'

        #title = ""

        # Get IDS dataSource parameters
        machineName = str(dataTreeView.dataSource.imasDbName)
        shotNumber = str(dataTreeView.dataSource.shotNumber)
        runNumber = str(dataTreeView.dataSource.runNumber)

        label = dataTreeView.dataSource.getShortLabel() + ':' + label
        #label = machineName + ":" + shotNumber + ":" + runNumber + ':' + label

        if xlabel == None:
            xlabel = "Time[s]"

        return (label, xlabel, ylabel, title)
