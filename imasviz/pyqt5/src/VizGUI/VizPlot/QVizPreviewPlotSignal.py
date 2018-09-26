#  Name   : QVizPreviewPlotSignal
#
#          Container to handle the preview plot of signals/nodes on left-click
#          on the appropriate FLT_1D node.
#          Note: The wxPython predecessor of this Python file is
#          PreviewPlotSignal.py
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
#    def getFrame
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

class QVizPreviewPlotSignal(AbstractCommand):
    def __init__(self, dataTreeView, nodeData = None, signal = None,
                 figureKey = None, title = '', label = None, xlabel = None,
                 signalHandling = None):
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

        # Set widget window title
        self.figureKey = 'Preview Plot'

        self.title = title

        if label == None:
            self.label = self.nodeData['Path']
        else:
            self.label = label

        self.xlabel = xlabel

    def execute(self):
        try:
            if len(self.signal) == 2:
                t = QVizPreviewPlotSignal.getTime(self.signal)
                v = QVizPreviewPlotSignal.get1DSignalValue(self.signal)
                self.plot1DSignal(self.dataTreeView.shotNumber, t, v,
                                  self.figureKey, self.title, self.label,
                                  self.xlabel)
            else:
                raise ValueError("only 1D plots are currently supported.")
        except ValueError as e:
            self.dataTreeView.log.error(str(e))

    def getPlotWidget(self, figureKey=0):
        self.plotWidget = QVizPlotWidget(size=(350,350), title='Preview Plot')
        # self.plotWidget = \
        #     IMASVIZPlotFrame(None, size=(600, 500), title=figureKey,
        #                      signalHandling=self.signalHandling)

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
                     xlabel=None):
        """Plot a 1D signal as a function of time.

        Arguments:
            shotnumber (int) : IDS database parameter - shot number of the case.
            t     (2D array) : 2D array of physical quantity values.
            v     (2D array) : 2D array of time values.
            figureKey  (str) : Label for the figure frame window.
            title      (str) : Plot title.
            label      (str) : Label describing IMAS database (device, shot) and
                               path to signal/node in IDS database structure.
            xlabel     (str) : Plot X-axis label.
        """

        try:
            self.getPlotWidget(self.figureKey)

            # Shape of the signal
            nbRows = v.shape[0]

            plotWidget = self.plotWidget

            # Set plot options
            label, xlabel, ylabel, title = \
                self.plotOptions(self.dataTreeView, self.nodeData,
                                 shotNumber=shotNumber, label=label,
                                 xlabel=xlabel, title=self.figureKey)
            u = v[0]
            ti = t[0]
            plotWidget.plot(x=ti, y=u, label=label, xlabel=xlabel,
                            ylabel=ylabel)

            plotWidget.show()

        except:
            traceback.print_exc(file=sys.stdout)
            raise

    @staticmethod
    def plotOptions(dataTreeView, signalNodeData, shotNumber=None, title='',
                    label=None, xlabel=None):
        """ Set plot options.

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

        ylabel = 'S(t)'
        if t != None and not (t.isCoordinateTimeDependent(t.coordinate1)):
           ylabel = 'S'

        if 'units' in signalNodeData:
            units = signalNodeData['units']
            ylabel += '[' + units + ']'

        label = dataTreeView.dataSource.getShortLabel() + ':' + label

        if xlabel == None:
            xlabel = "Time[s]"

        return (label, xlabel, ylabel, title)
