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
#    def onHide
#    def getSignal
#
#****************************************************
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
#****************************************************

import sys, logging
import traceback

from PyQt5.QtWidgets import QWidget
from netaddr import strategy

from imasviz.VizDataAccess.QVizDataAccessFactory import QVizDataAccessFactory
from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal import QVizPlotSignal


class QVizPreviewPlotSignal(QVizAbstractCommand):

    def __init__(self, dataTreeView, treeNode = None, signal = None,
                 title = '', label = None, xlabel = None, signalHandling = None):

        self.exists = None

        QVizAbstractCommand.__init__(self, dataTreeView, treeNode)

        self.signalHandling = signalHandling

        if signal is None:
            signal = self.get1DArrayData()

        self.signal = signal

        # Set widget window title
        self.title = 'Preview Plot'

        if label is None:
            self.label = self.nodeData['Path']
        else:
            self.label = label

        self.xlabel = xlabel

    def get1DArrayData(self):
        return self.dataTreeView.imas_viz_api.GetSignal(self.dataTreeView, self.treeNode,
                                                        strategy="DEFAULT", plotWidget=self.getPlotWidget())

    def execute(self):
        try:
            if not (self.treeNode.is1D() or self.treeNode.is0D()):
                self.getPlotWidget().clear(noPreviewAvailable=True)
                return
            elif self.signal is None:
                return

            if len(self.signal) == 2:
                t = QVizPreviewPlotSignal.getTime(self.signal)
                v = QVizPreviewPlotSignal.get1DSignalValue(self.signal)
                if len(t[0]) != len(v[0]):
                    raise ValueError("Data can not be previewed, x and y shapes are different.")
                self.plot1DSignal(shotNumber=self.dataTreeView.shotNumber,
                                  t=t, v=v, title=self.title,
                                  label=self.label, xlabel=self.xlabel)
            else:
                raise ValueError("Warning! Only 1D plots are currently supported.")
        except ValueError as e:
            logging.error(str(e))

    # @staticmethod
    def getPlotWidget(self):
        """Find the child widget in DTV main window.
        """
        plotWidget = self.dataTreeView.parent.findChild(QWidget, 'QVizPreviewPlotWidget')
        if plotWidget is None:
            error = 'Preview Plot Widget not found. Update not possible'
            raise ValueError(error)
            logging.error(str(error))
        return plotWidget

    @staticmethod
    def getTime(oneDimensionSignal):
        return oneDimensionSignal[0]

    @staticmethod
    def get1DSignalValue(oneDimensionSignal):
        """Returns the signal values of a 1D signal returned by
           get1DSignal(signalName, shotNumber)
        """
        return oneDimensionSignal[1]

    def plot1DSignal(self, shotNumber, t, v, title='', label=None,
                     xlabel=None):
        """Plot a 1D signal as a function of time.

        Arguments:
            shotnumber (int) : IDS database parameter - shot number of the case.
            t     (2D array) : 2D array of time values.
            v     (2D array) : 2D array of physical quantity values.
            title      (str) : Plot title.
            label      (str) : Label describing IMAS database (device, shot) and
                               path to signal/node in IDS database structure.
            xlabel     (str) : Plot X-axis label.
        """

        try:
            # Get the preview plot widget
            self.plotWidget = self.getPlotWidget()
            # Clear the preview plot widget (should contain only one plot at
            # a time)
            self.plotWidget.clear()

            # Shape of the signal
            nbRows = v.shape[0]

            # Set plot options
            label, xlabel, ylabel, title = \
                self.dataTreeView.selectedItem.plotOptions(self.dataTreeView,label=label,
                                 xlabel=xlabel, title=title, plotWidget=self.plotWidget, strategy='DEFAULT')
            # Get plottable data
            u = v[0]    # first (should be the only) array of physical
                        # quantity values
            ti = t[0]   # first (should be the only) array of time values
            # Create plot
            self.plotWidget.plot(x=ti, y=u, label=label, xlabel=xlabel,
                            ylabel=ylabel)
            self.plotWidget.update()
        except:
            traceback.print_exc(file=sys.stdout)
            raise
