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

from imasviz.VizDataAccess.QVizDataAccessFactory import QVizDataAccessFactory
from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal import QVizPlotSignal


class QVizPreviewPlotSignal(QVizAbstractCommand):

    def __init__(self, dataTreeView, treeNode = None,
                 title = '', label = None, xlabel = None, signalHandling = None):

        self.exists = None

        QVizAbstractCommand.__init__(self, dataTreeView, treeNode)

        self.signalHandling = signalHandling

        # Set widget window title
        self.title = 'Preview Plot'

        if label is None:
            self.label = self.nodeData['Path']
        else:
            self.label = label

        self.xlabel = xlabel


    def getData(self):
        return self.dataTreeView.imas_viz_api.GetSignal(self.dataTreeView, self.treeNode,
                                                        plotWidget=self.getPlotWidget())

    def execute(self):
        try:
            data = self.getData()
            
            if self.treeNode.getDataType() == 'STR_1D':
                return
            elif not (self.treeNode.is1D() or self.treeNode.is0D() or self.treeNode.is2D()):
                self.getPlotWidget().clear(self.treeNode, noPreviewAvailable=True)
                return
            elif data is None:
                return

            if self.treeNode.is0D() or self.treeNode.is1D():
                t = data[0]
                v = data[1]
                if len(t[0]) !=len(v[0]):
                    raise ValueError("Data can not be previewed, x and y shapes are different.")

                self.getPlotWidget().setStrategy(self.treeNode.getStrategyForDefaultPlotting())
                self.plot1DSignal(shotNumber=self.dataTreeView.shotNumber,
                                  t=t, v=v, title=self.title,
                                  label=self.label, xlabel=self.xlabel)

            elif self.treeNode.is2D():
                self.plot2DImage(data) #coordinates, np.array([rval]), coordinate_of_time
            else:
                raise ValueError("Warning! Only 1D and 2D plots are currently supported.")
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
        return plotWidget

    def plot2DImage(self, data):
        try:
            # Get the preview plot widget
            plotWidget = self.getPlotWidget()
            # Clear the preview plot widget (should contain only one plot at
            # a time)
            plotWidget.clear(self.treeNode)
            plotWidget.plot2D(data)
            plotWidget.update()
        except:
            traceback.print_exc(file=sys.stdout)
            raise

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
            plotWidget = self.getPlotWidget()
            # Clear the preview plot widget (should contain only one plot at
            # a time)
            plotWidget.clear(self.treeNode)

            # Shape of the signal
            nbRows = v.shape[0]

            # Set plot options
            label, xlabel, ylabel, title = \
                self.dataTreeView.selectedItem.plotOptions(self.dataTreeView,label=label,
                                 xlabel=xlabel, title=title, plotWidget=plotWidget)
            # Get plottable data
            u = v[0]    # first (should be the only) array of physical
                        # quantity values
            ti = t[0]   # first (should be the only) array of time values
            # Create plot
            plotWidget.plot(vizTreeNode=self.treeNode, x=ti, y=u, label=label, xlabel=xlabel,
                            ylabel=ylabel)
            plotWidget.update()
        except:
            traceback.print_exc(file=sys.stdout)
            raise
