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

import sys
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
                 update=0, signalHandling=None, vizTreeNode=None):
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
            signalHandling (obj) : Object to QVizSignalHandling.

        """
        QVizAbstractCommand.__init__(self, dataTreeView, nodeData)

        if nodeData == None or vizTreeNode == None:
            self.updateNodeData()
        else:
            self.nodeData = nodeData
            self.treeNode = vizTreeNode

        self.signalHandling = signalHandling

        self.log = self.dataTreeView.log

        if signal == None:
            # signalDataAccess = \
            #     QVizDataAccessFactory(self.dataTreeView.dataSource).create()
            # self.signal = signalDataAccess.GetSignal(self.nodeData,
            #                 self.dataTreeView.dataSource.shotNumber, self.treeNode)

            self.signal = self.getSignal(dataTreeView=self.dataTreeView,
                                         selectedNodeData=self.nodeData,
                                         vizTreeNode=self.treeNode)

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
            # Set label containing node path
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
                if (len(t[0]) != len(v[0])):
                    raise ValueError("1D data can not be plotted, x and y shapes are different.")
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
            plotWidget = api.figureframes[figureKey]
        else:
            figureKey = api.GetNextKeyForFigurePlots()
            plotWidget = QVizPlotWidget(size=(600,550), title=figureKey,
                                        signalHandling=self.signalHandling)
            api.figureframes[figureKey] = plotWidget
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
            plotWidget = self.getPlotWidget(self.figureKey)

            # fig =  self.plotFrame.get_figure()

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

            # Add username to legend label (in front)
            if self.dataTreeView.dataSource.userName != None:
                label = self.dataTreeView.dataSource.userName + ":" + label
            # In case of UDA loaded case
            elif self.dataTreeView.dataSource.name != None:
                label = self.dataTreeView.dataSource.name + ":" + label

            if update == 1:
                # self.log.info('Updating/Overwriting existing plot.')

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
    def getSignal(dataTreeView, selectedNodeData, vizTreeNode):
        try:
            signalDataAccess = QVizDataAccessFactory(dataTreeView.dataSource).create()
            # treeNode = dataTreeView.selectedItem
            s = signalDataAccess.GetSignal(selectedNodeData,
                                           dataTreeView.dataSource.shotNumber,
                                           vizTreeNode)
            return s
        except:
            #dataTreeView.log.error(str(e))
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

        #t = dataTreeView.getNodeAttributes(signalNodeData['dataName'])

        if label == None:
            label = signalNode.getPath()

        # Setting/Checking the X-axis label
        if xlabel == None:
            # If xlabel is not yet set
            if 'coordinate1' in signalNode.getInfoDict():
                xlabel = QVizGlobalOperations.replaceBrackets(
                    signalNode.getInfoDict()['coordinate1'])
            if xlabel != None and xlabel.endswith("time"):
                xlabel +=  "[s]"
        elif 'Time[s]' in xlabel:
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

        #ylabel = signalNodeData['dataName']

        ylabel = 'S(t)'
        if signalNode is not None and not (signalNode.isCoordinateTimeDependent(
                signalNode.treeNodeExtraAttributes.coordinate1)):
           ylabel = 'S'

        if 'units' in signalNode.getInfoDict():
            units = signalNode.getInfoDict()['units']
            ylabel += '[' + units + ']'

        # Get IDS dataSource parameters
        machineName = str(dataTreeView.dataSource.imasDbName)
        shotNumber = str(dataTreeView.dataSource.shotNumber)
        runNumber = str(dataTreeView.dataSource.runNumber)

        label = dataTreeView.dataSource.getShortLabel() + ':' + label
        # label = machineName + ":" + shotNumber + ":" + runNumber + ':' + label

        if xlabel == None:
            xlabel = "Time[s]"

        return label, xlabel, ylabel, title
