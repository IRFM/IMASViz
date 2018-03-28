import wx
from imasviz.gui_commands.AbstractCommand import AbstractCommand
from imasviz.signals_data_access.SignalDataAccessFactory import SignalDataAccessFactory
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.plotframes.IMASVIZPlotFrame import IMASVIZ_PreviewPlotFrame
import matplotlib.pyplot as plt
import wxmplot
import traceback
import sys

class PreviewPlotSignal(AbstractCommand):

    def __init__(self, view, nodeData = None, signal = None, figureKey = None,
                 title = '', label = None, xlabel = None, update = 0,
                 signalHandling = None):

        """Check if a frame with the preview plot frame already exists. If it
           does, close it. Max one is to be open at a time.
        """
        if (wx.FindWindowByLabel('Preview Plot') != None):
            wx.FindWindowByLabel('Preview Plot').Close()

        AbstractCommand.__init__(self, view, nodeData)

        self.updateNodeData();

        self.signalHandling = signalHandling

        if signal == None:
            signalDataAccess = \
                SignalDataAccessFactory(self.view.dataSource).create()
            treeNode = self.view.getNodeAttributes(self.nodeData['dataName'])
            self.signal = \
                signalDataAccess.GetSignal(self.nodeData,
                                           self.view.dataSource.shotNumber,
                                           treeNode)
        else:
            self.signal = signal

        if figureKey == None:
            self.figureKey = self.view.imas_viz_api.GetNextKeyForFigurePlots()
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
                t = PreviewPlotSignal.getTime(self.signal)
                v = PreviewPlotSignal.get1DSignalValue(self.signal)
                self.plot1DSignal(self.view.shotNumber, t, v, self.figureKey,
                                  self.title, self.label, self.xlabel,
                                  self.update)
            else:
                raise ValueError("only 1D plots are currently supported.")
        except ValueError as e:
            self.view.log.error(str(e))

    def getFrame(self):
        self.plotFrame = \
            IMASVIZ_PreviewPlotFrame(None, size=(360, 300), title='Plot Preview',
                             signalHandling=self.signalHandling)
    @staticmethod
    def getTime(oneDimensionSignal):
        return oneDimensionSignal[0]

    @staticmethod
    def get1DSignalValue(oneDimensionSignal):
        """Returns the signal values of a 1D signal returned by
           get1DSignal(signalName, shotNumber)
        """
        return oneDimensionSignal[1]

    def plot1DSignal(self, shotNumber, t, v, figureKey=0, title='',
                     label=None, xlabel=None, update=0):
        """Plot a 1D signal as a function of time
        """

        try:
            self.updateNodeData()

            api = self.view.imas_viz_api
            self.getFrame()

            fig =  self.plotFrame.get_figure()

            key = self.view.dataSource.dataKey(self.nodeData)
            tup = (self.view.dataSource.shotNumber, self.nodeData)
            api.addNodeToFigure(figureKey, key, tup)

            # Shape of the signal
            nbRows = v.shape[0]

            frame = self.plotFrame

            label, xlabel, ylabel, title = \
                self.plotOptions(self.view, self.nodeData, shotNumber=shotNumber,
                                 label=label, xlabel=xlabel, title=title)

            if update == 1:
                for i in range(0, nbRows):
                    u = v[i]
                    # ti = t[i]
                    ti = t[0]
                    frame.oplot(ti, u, label=label, title=title)
            else:
                frame.panel.toggle_legend(None, True)
                for i in range(0, nbRows):
                    u = v[i]
                    ti = t[0]

                    if i == 0:
                        frame.plot(ti, u, title=title, xlabel=xlabel,
                                   ylabel=ylabel, label=label)
                    else:
                        frame.oplot(ti, u, label=label)
                frame.Center()

            """Set preview plot frame position"""
            # TODO: Get WxDataTreeview position and position preview panel on
            #       the right side of it
            frame.SetPosition((100,100))
            """Set preview plot frame label"""
            frame.SetLabel('Preview Plot')

            """Show preview plot frame"""
            frame.Show()

        except:
            traceback.print_exc(file=sys.stdout)
            raise

    @staticmethod
    def getSignal(view, selectedNodeData):
        try:
            signalDataAccess = SignalDataAccessFactory(view.dataSource).create()
            treeNode = view.getNodeAttributes(selectedNodeData['dataName'])
            s = signalDataAccess.GetSignal(selectedNodeData,
                                           view.dataSource.shotNumber,
                                           treeNode)
            return s
        except:
            #view.log.error(str(e))
            raise

    @staticmethod
    def plotOptions(view, signalNodeData, shotNumber=None, title='', label=None,
                   xlabel=None):

        t = view.getNodeAttributes(signalNodeData['dataName'])

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

        machineName = str(view.dataSource.imasDbName)
        shotNumber = str(view.dataSource.shotNumber)
        runNumber = str(view.dataSource.runNumber)

        label = view.dataSource.getShortLabel() + ':' + label
        #label = machineName + ":" + shotNumber + ":" + runNumber + ':' + label

        if xlabel == None:
            xlabel = "Time[s]"


        return (label, xlabel, ylabel, title)