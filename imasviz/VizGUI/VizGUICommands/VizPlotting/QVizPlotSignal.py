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

from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizAbstractPlot import QVizAbstractPlot
from imasviz.VizUtils import QVizGlobalOperations


class QVizPlotSignal(QVizAbstractCommand, QVizAbstractPlot):
    """Handling plot execution.
    """

    def __init__(self, dataTreeView, signal=None,
                 title='', label=None, xlabel=None,
                 vizTreeNode=None,
                 plotWidget=None):
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
        QVizAbstractPlot.__init__(self, plotWidget)

        self.signal = None
        self.treeNode = vizTreeNode
        self.title = title
        self.label = label
        self.xlabel = xlabel
        self.plotFrame = None

    def execute(self, figureKey=0, update=0, dataset_to_update=0, signal=None):
        try:

            api = self.dataTreeView.imas_viz_api

            if signal is None:
                logging.debug("calling api.GetSignal() for node:" + self.treeNode.getName())
                self.signal = api.GetSignal(self.dataTreeView, self.treeNode, plotWidget=self.plotWidget)
            else:
                self.signal = signal

            if len(self.signal) == 2:
                logging.debug("calling api.get1DSignalValue() for node:" + self.treeNode.getName())
                t = QVizPlotSignal.getXAxisValues(self.signal)
                v = QVizPlotSignal.get1DSignalValue(self.signal)

                if t is None or t[0] is None:
                    raise ValueError("Time values are not defined.")

                if v is None or v[0] is None:
                    raise ValueError("Array values are not defined.")

                if len(t[0]) != len(v[0]):
                    raise ValueError("1D data can not be plotted, x and y shapes are different.")

                self.__plot1DSignal(self.dataTreeView.uri, t, v,
                                    figureKey, self.title, self.label,
                                    self.xlabel, update, dataset_to_update)
            else:
                raise ValueError("only 1D plots are currently supported.")
        except ValueError as e:
            logging.error(str(e))

    @staticmethod
    def getXAxisValues(oneDimensionSignal):
        return oneDimensionSignal[0]

    @staticmethod
    def get1DSignalValue(oneDimensionSignal):
        """Returns the signal values of a 1D signal returned by
           get1DSignal(signalName, uri)
        """
        return oneDimensionSignal[1]

    def __plot1DSignal(self, uri, t, v, figureKey=0, title='', label=None,
                       xlabel=None, update=0, dataset_to_update=0):
        """Plot a 1D signal as a function of time.

        Arguments:
            uri              : URI of the shot
            t     (2D array) : 2D array of time values.
            v     (2D array) : 2D array of physical quantity values.
            figureKey  (str) : Label for the figure frame window.
            title      (str) : Plot title.
            label      (str) : Label describing IMAS database (URI) and
                               path to signal/node in IDS database structure.
            xlabel     (str) : Plot X-axis label.
            update     (int) : Plot update parameter (0 or 1). Set to 1 when
                               adding additional plot lines to an already
                               existing plot.
        """

        try:
            # Set IMASViz api
            api = self.dataTreeView.imas_viz_api

            # Get time
            self.treeNode.globalTime = self.treeNode.getGlobalTimeForArraysInDynamicAOS()

            key = self.dataTreeView.dataSource.dataKey(self.treeNode)
            tup = (self.dataTreeView.dataSource.uri, self.treeNode)
            api.AddNodeToFigure(figureKey, key, tup)

            # Shape of the signal
            # TODO/Note: as it seems the QVizPlotSignal is used for single
            #            signals only, hence nbRows == 1 (always)
            nbRows = v.shape[0]

            label, xlabel, ylabel, title = \
                self.treeNode.plotOptions(self.dataTreeView,
                                          label=label,
                                          xlabel=xlabel, title=figureKey,
                                          plotWidget=self.plotWidget)

            if update == 1:

                # Updating/Overwriting existing plot
                for i in range(0, nbRows):
                    # y-axis values
                    u = v[i]
                    # x-axis values
                    ti = t[0]

                    # Get plot display PlotItem and CentralWidget
                    # pgPlotItem = self.plotWidget.pgPlotWidget.plotItem
                    pgPlotItem = self.plotWidget.getPlotItem()
                    pgCentralWidget = self.plotWidget.pgPlotWidget.centralWidget
                    #print('dataset_to_update=', dataset_to_update)
                    #if dataset_to_update < 0 or dataset_to_update >= len(pgPlotItem.items):
                    #    return  
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

                    # Setting range manually (see IMAS-3658)
                    try:
                        self.plotWidget.getPlotItem().setRange(xRange=(min(ti), max(ti)), yRange=(min(u), max(u)))
                    except:
                        pass
                    pm = self.plotWidget.getPlotItem()
                    if i == 0:
                        # New plot
                        self.plotWidget.plot(vizTreeNode=self.treeNode,
                                             x=ti, y=u,
                                             label=label,
                                             xlabel=xlabel,
                                             ylabel=ylabel,
                                             update=update)
                    else:
                        # Add plot
                        self.plotWidget.plot(vizTreeNode=self.treeNode, x=ti, y=u, label=label, update=update)

            # Show the widget window
            self.plotWidget.show()

        except:
            traceback.print_exc(file=sys.stdout)
            #self.plotWidget.pgPlotWidget.getViewBox().addVizTreeNode(self.treeNode, preview=0)
            #self.plotWidget.updateSlider(self.treeNode)
            raise
        finally:
            pass
            #self.plotWidget.show()

    def onHide(self, api, figureKey):
        self.dataTreeView.imas_viz_api.figureframes[figureKey].hide()

    def getTreeNode(self):
        return self.treeNode
