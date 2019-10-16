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
# ****************************************************
#  TODO:
#
#    - Function definitions (from PlotSignal class)
#    def onHide
#    def getSignal
#
# ****************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
# ****************************************************

import sys, logging
import traceback

from imasviz.VizDataAccess.QVizDataAccessFactory import QVizDataAccessFactory

from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPlotWidget import QVizPlotWidget
from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations

class QVizPlotSignal(QVizAbstractCommand):
    """Handling plot execution.
    """
    def __init__(self, dataTreeView, nodeData=None, signal=None,
                 figureKey=None, title='', label=None, xlabel=None,
                 update=0, vizTreeNode=None, addTimeSlider=False, addCoordinateSlider=False):
        """
        Arguments:
            dataTreeView (QTreeWidget) : DataTreeView object of the QTreeWidget.
            nodeData      (dict) : QVizTreeNode data dictionary.
            signal       (tuple) : Tuple holding plotting values.
            figureKey      (str) : Plot window label that also indicates type
                                   of the requested plot view type.
            title          (str) : Plot title.
            label          (str) : Plot label.
            xlabel         (str) : Plot x-axis label.
            update            () :

        """
        QVizAbstractCommand.__init__(self, dataTreeView, nodeData)

        if nodeData is None or vizTreeNode is None:
            self.updateNodeData()
        else:
            self.nodeData = nodeData
            self.treeNode = vizTreeNode

        if signal is None:
            self.signal = self.getSignal(dataTreeView=self.dataTreeView, vizTreeNode=self.treeNode)
        else:
            self.signal = signal

        # Set widget window title by getting the next figure number
        if figureKey is None:
            self.figureKey = self.dataTreeView.imas_viz_api.GetNextKeyForFigurePlots()
        else:
            self.figureKey = figureKey

        self.title = title
        self.label = label
        self.xlabel = xlabel
        self.update = update
        self.plotFrame = None
        self.addTimeSlider = addTimeSlider
        self.addCoordinateSlider = addCoordinateSlider

    def execute(self, plotWidget):
        try:
            if len(self.signal) == 2:
                t = QVizPlotSignal.getTime(self.signal)
                v = QVizPlotSignal.get1DSignalValue(self.signal)
                if t is None or t[0] is None:
                    raise ValueError("Time values are not defined.")
                if v is None or v[0] is None:
                    raise ValueError("Array values are not defined.")
                if len(t[0]) != len(v[0]):
                    raise ValueError("1D data can not be plotted, x and y shapes are different.")

                self.plot1DSignal(self.dataTreeView.shotNumber, t, v, plotWidget,
                                  self.figureKey, self.title, self.label,
                                  self.xlabel, self.update)
            else:
                raise ValueError("only 1D plots are currently supported.")
        except ValueError as e:
            logging.error(str(e))

    @staticmethod
    def getTime(oneDimensionSignal):
        return oneDimensionSignal[0]

    @staticmethod
    def get1DSignalValue(oneDimensionSignal):
        """Returns the signal values of a 1D signal returned by
           get1DSignal(signalName, shotNumber)
        """
        return oneDimensionSignal[1]


    def plot1DSignal(self, shotNumber, t, v, plotWidget, figureKey=0, title='', label=None,
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

            ids = self.dataTreeView.dataSource.ids[self.treeNode.getOccurrence()]

            # Get signal time
            self.treeNode.globalTime = QVizGlobalOperations.getGlobalTimeForArraysInDynamicAOS(ids, self.treeNode.getInfoDict())

            key = self.dataTreeView.dataSource.dataKey(self.treeNode.getInfoDict())
            tup = (self.dataTreeView.dataSource.shotNumber, self.nodeData)
            api.addNodeToFigure(figureKey, key, tup)

            # Shape of the signal
            # TODO/Note: as it seems the QVizPlotSignal is used for single
            #            signals only, hence nbRows == 1 (always)
            nbRows = v.shape[0]

            # Set plot options
            label, xlabel, ylabel, title = \
                self.plotOptions(self.dataTreeView, self.dataTreeView.selectedItem,
                                 shotNumber=shotNumber, label=label,
                                 xlabel=xlabel, title=self.figureKey)

            # A new plot is added to the current plot(s)
            if update == 1:
                # logging.info('Updating/Overwriting existing plot.')

                # Update/Overwrite existing plot
                for i in range(0, nbRows):
                    # y-axis values
                    u = v[i]
                    # x-axis values
                    # ti = t[i]
                    ti = t[0]

                    # Get plot display PlotItem and CentralWidget
                    pgPlotItem = plotWidget.pgPlotWidget.plotItem
                    pgCentralWidget = plotWidget.pgPlotWidget.centralWidget
                    # Update x and y values
                    pgPlotItem.items[0].setData(x=ti, y=u)
                    # Update x-axis label
                    x_axis = pgPlotItem.getAxis('bottom')
                    x_axis.setLabel(xlabel, "")
                    # Update legend
                    pgCentralWidget.legend.items[0][1].setText(label)

            else:
                # Create new plot
                for i in range(0, nbRows):
                    # y-axis values
                    u = v[i]
                    # x-axis values
                    ti = t[0]

                    if i == 0:
                        # New plot
                        # plotWidget_2 = QVizPlotServices().plot(x=ti, y=u, title=title, pen='b')
                        plotWidget.plot(x=ti, y=u, label=label, xlabel=xlabel,
                                        ylabel=ylabel)
                    else:
                        # Add plot
                        plotWidget.plot(x=ti, y=u, label=label)

            # Show the widget window
            plotWidget.show()

        except:
            traceback.print_exc(file=sys.stdout)
            raise

    def onHide(self, api, figureKey):
        self.dataTreeView.imas_viz_api.figureframes[figureKey].hide()

    @staticmethod
    def getSignal(dataTreeView, vizTreeNode):
        try:
            signalDataAccess = QVizDataAccessFactory(dataTreeView.dataSource).create()
            if vizTreeNode.is1DAndDynamic():
                signal = signalDataAccess.GetSignal(vizTreeNode)
            elif vizTreeNode.is0DAndDynamic():
                signal = signalDataAccess.Get0DSignalVsTime(vizTreeNode)
            else:
                raise ValueError('Unexpected data type')
            return signal
        except:
            raise

    @staticmethod
    def plotOptions(dataTreeView, signalNode, shotNumber=None, title='',
                    label=None, xlabel=None):
        """Set plot options.

        Arguments:
            dataTreeView (QTreeWidget) : QVizDataTreeView object.
            signalNode       : QVizTreeNode object.
            shotnumber (int) : IDS database parameter - shot number of the case.
            title      (str) : Plot title.
            label      (str) : Label describing IMAS database (device, shot) and
                               path to signal/node in IDS database structure.
            xlabel     (str) : Plot X-axis label.
        """
        if label is None:
            label = dataTreeView.dataSource.getShortLabel() + ':' + signalNode.getPath()

        if signalNode.is0DAndDynamic():
            label, title = signalNode.correctLabelForTimeSlices(label, title)

        elif signalNode.is1DAndDynamic():
            # Setting/Checking the X-axis label
            if xlabel is None:
                # If xlabel is not yet set
                if 'coordinate1' in signalNode.getInfoDict():
                    xlabel = QVizGlobalOperations.replaceBrackets(
                        signalNode.getInfoDict()['coordinate1'])
                if xlabel != None and xlabel.endswith("time"):
                    xlabel +=  "[s]"
            elif 'time[s]' in xlabel:
                # If 'Time[s]' is present in xlabel, do not modify it
                pass
            elif '1.' not in xlabel and '.N' not in xlabel:
                # If '1...N' or '1..N' (or other similar variant)  is not present
                # in xlabel:
                # - Replace dots '.' by slashes '/'
                xlabel = QVizGlobalOperations.replaceDotsBySlashes(xlabel)
                # - If IDS name is not present (at the front) of the xlabel string,
                #   then add it
                if signalNode.getIDSName() not in xlabel:
                    xlabel = signalNode.getIDSName() + "/" + xlabel

        if xlabel is None:
            xlabel = "time[s]"

        ylabel = signalNode.getName()

        if 'units' in signalNode.getInfoDict():
            units = signalNode.getInfoDict()['units']
            ylabel += '[' + units + ']'

        return label, xlabel, ylabel, title
