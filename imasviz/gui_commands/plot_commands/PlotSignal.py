import wx
from imasviz.gui_commands.AbstractCommand import AbstractCommand
from imasviz.signals_data_access.SignalDataAccessFactory import SignalDataAccessFactory
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.plotframes.IMASVIZPlotFrame import IMASVIZPlotFrame
import matplotlib.pyplot as plt
import wxmplot
import traceback
import sys

class PlotSignal(AbstractCommand):
    
    def __init__(self, view, nodeData = None, signal = None, figureKey = None, title = '', label = None, xlabel = None, update = 0, signalHandling = None):
        AbstractCommand.__init__(self, view, nodeData)
        
        self.updateNodeData();

        self.signalHandling = signalHandling
         
        if signal == None:
            signalDataAccess = SignalDataAccessFactory(self.view.dataSource).create()
            treeNode = self.view.getNodeAttributes(self.nodeData['dataName'])
            self.signal = signalDataAccess.GetSignal(self.nodeData, self.view.dataSource.shotNumber, treeNode)
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
                t = PlotSignal.getTime(self.signal)
                v = PlotSignal.get1DSignalValue(self.signal)
                self.plot1DSignal(self.view.shotNumber, t, v, self.figureKey, self.title, self.label, self.xlabel, self.update)
            else:
                raise ValueError("only 1D plots are currently supported.")
        except ValueError as e:
            self.view.log.error(str(e))

    def getFrame(self, figureKey=0):
        api = self.view.imas_viz_api
        if figureKey in api.figureframes:
            self.plotFrame = api.figureframes[figureKey]
        else:
            figureKey = api.GetNextKeyForFigurePlots()
            self.plotFrame = IMASVIZPlotFrame(None, size=(600, 500), title=figureKey, signalHandling=self.signalHandling)
            api.figureframes[figureKey] = self.plotFrame

    @staticmethod
    def getTime(oneDimensionSignal):
        return oneDimensionSignal[0]

    # Returns the signal values of a 1D signal returned by get1DSignal(signalName, shotNumber)
    @staticmethod
    def get1DSignalValue(oneDimensionSignal):
        return oneDimensionSignal[1]

    # Plot a 1D signal as a function of time
    def plot1DSignal(self, shotNumber, t, v, figureKey=0, title='', label=None, xlabel=None, update=0):
        
        try:
            self.updateNodeData()

            api = self.view.imas_viz_api
            self.getFrame(self.figureKey)

            fig =  self.plotFrame.get_figure()

            key = self.view.dataSource.dataKey(self.nodeData)
            tup = (self.view.dataSource.shotNumber, self.nodeData)
            api.addNodeToFigure(figureKey, key, tup)

            # Shape of the signal
            nbRows = v.shape[0]

            def lambda_f(evt, i=figureKey, imas=self):
                self.onHide(api, i)


            frame = self.plotFrame
            frame.Bind(wx.EVT_CLOSE, lambda_f)

            label, xlabel, ylabel, title = self.plotOptions(self.view, self.nodeData, shotNumber=shotNumber,
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
                        frame.plot(ti, u, title=title, xlabel=xlabel, ylabel=ylabel, label=label)
                    else:
                        frame.oplot(ti, u, label=label)
                frame.Center()

            frame.Show()

        except:
            traceback.print_exc(file=sys.stdout)
            raise


    def onHide(self, api, figureKey):
        self.view.imas_viz_api.figureframes[figureKey].Hide()
            
    @staticmethod
    def getSignal(view, selectedNodeData):
        try:
            signalDataAccess = SignalDataAccessFactory(view.dataSource).create()
            treeNode = view.getNodeAttributes(selectedNodeData['dataName'])
            s = signalDataAccess.GetSignal(selectedNodeData, view.dataSource.shotNumber, treeNode)
            return s
        except:
            #view.log.error(str(e))
            raise

    @staticmethod
    def plotOptions(view, signalNodeData, shotNumber=None, title='', label=None, xlabel=None):

        t = view.getNodeAttributes(signalNodeData['dataName'])

        if label == None:
            label = signalNodeData['Path']

        if xlabel == None:
            if 'coordinate1' in signalNodeData:
                xlabel = GlobalOperations.replaceBrackets(signalNodeData['coordinate1'])
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