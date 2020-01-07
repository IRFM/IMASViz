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
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
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
    def __init__(self, dataTreeView, signal=None,
                 title='', label=None, xlabel=None,
                 vizTreeNode=None):
        """
        Arguments:
            dataTreeView (QTreeWidget) : DataTreeView object of the QTreeWidget.
            signal       (tuple) : Tuple holding plotting values.
            figureKey      (str) : Plot window label that also indicates type
                                   of the requested plot view type.
            title          (str) : Plot title.
            label          (str) : Plot label.
            xlabel         (str) : Plot x-axis label.
            update            () :

        """
        QVizAbstractCommand.__init__(self, dataTreeView, vizTreeNode)

        self.treeNode = vizTreeNode
        self.title = title
        self.label = label
        self.xlabel = xlabel
        self.plotFrame = None

    def execute(self, plotWidget, figureKey=0, update=0, dataset_to_update=0):
        try:
            api = self.dataTreeView.imas_viz_api
            self.signal = api.GetSignal(self.dataTreeView, self.treeNode, plotWidget=plotWidget)

            if len(self.signal) == 2:

                t = QVizPlotSignal.getTime(self.signal)
                v = QVizPlotSignal.get1DSignalValue(self.signal)

                if t is None or t[0] is None:
                    raise ValueError("Time values are not defined.")

                if v is None or v[0] is None:
                    raise ValueError("Array values are not defined.")

                if len(t[0]) != len(v[0]):
                    raise ValueError("1D data can not be plotted, x and y shapes are different.")

                self.__plot1DSignal(self.dataTreeView.shotNumber, t, v, plotWidget,
                                    figureKey, self.title, self.label,
                                    self.xlabel, update, dataset_to_update)
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


    def __plot1DSignal(self, shotNumber, t, v, plotWidget, figureKey=0, title='', label=None,
                       xlabel=None, update=0, dataset_to_update=0):
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
            # Set IMASViz api
            api = self.dataTreeView.imas_viz_api

            ids = self.dataTreeView.dataSource.ids[self.treeNode.getOccurrence()]

            # Get time
            self.treeNode.globalTime = self.treeNode.getGlobalTimeForArraysInDynamicAOS(self.dataTreeView.dataSource)

            key = self.dataTreeView.dataSource.dataKey(self.treeNode)
            tup = (self.dataTreeView.dataSource.shotNumber, self.treeNode)
            api.AddNodeToFigure(figureKey, key, tup)

            # Shape of the signal
            # TODO/Note: as it seems the QVizPlotSignal is used for single
            #            signals only, hence nbRows == 1 (always)
            nbRows = v.shape[0]

            # Set plot options
            time_index = 0
            if plotWidget.addTimeSlider:
                time_index = plotWidget.sliderGroup.slider.value()

            coordinate_index = 0
            if plotWidget.addCoordinateSlider:
                coordinate_index = plotWidget.sliderGroup.slider.value()

            label, xlabel, ylabel, title = \
                self.treeNode.plotOptions(self.dataTreeView,
                                 label=label,
                                 xlabel=xlabel, title=figureKey,
                                          time_index=time_index,
                                          coordinate_index=coordinate_index,
                                          plotWidget=plotWidget)

            if update == 1:

                # Updating/Overwriting existing plot
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
                    # if len(pgPlotItem.items) == 0:
                    #     item = PlotDataItem()
                    #     pgPlotItem.addItem(item)

                    pgPlotItem.items[dataset_to_update].setData(x=ti, y=u)
                    # Update x-axis label
                    x_axis = pgPlotItem.getAxis('bottom')
                    if xlabel is not None:
                        x_axis.setLabel(xlabel, "")
                    # Update legend
                    pgCentralWidget.legend.items[dataset_to_update][1].setText(label)

            else:
                # Creation of a new plot
                for i in range(0, nbRows):
                    # y-axis values
                    u = v[i]
                    # x-axis values
                    ti = t[0]

                    if i == 0:
                        # New plot
                        # plotWidget_2 = QVizPlotServices().plot(x=ti, y=u, title=title, pen='b')
                        plotWidget.plot(vizTreeNode=self.treeNode,x=ti, y=u, label=label, xlabel=xlabel,
                                        ylabel=ylabel, update=update)
                    else:
                        # Add plot
                        plotWidget.plot(vizTreeNode=self.treeNode,x=ti, y=u, label=label, update=update)

            # Show the widget window
            plotWidget.show()

        except:
            traceback.print_exc(file=sys.stdout)
            raise

    def onHide(self, api, figureKey):
        self.dataTreeView.imas_viz_api.figureframes[figureKey].hide()

    # This method gives a preferential way to plot data: as function
    # of time for 0D node and as function of coordinate1 for 1D nodes
    # @staticmethod
    # def getSignal(dataTreeView, vizTreeNode, plotWidget=None, as_function_of_time=False):
    #     try:
    #         signalDataAccess = QVizDataAccessFactory(dataTreeView.dataSource).create()
    #         if vizTreeNode.is1DAndDynamic():
    #             signal = signalDataAccess.GetSignal(vizTreeNode, plotWidget=plotWidget, as_function_of_time=as_function_of_time)
    #         elif vizTreeNode.is0DAndDynamic():
    #             signal = signalDataAccess.Get0DSignalVsTime(vizTreeNode)
    #         else:
    #             raise ValueError('Unexpected data type')
    #         return signal
    #     except:
    #         raise
