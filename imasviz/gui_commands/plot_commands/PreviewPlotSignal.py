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

    def __init__(self, view, nodeData = None, signal = None,
                 title = '', label = None, xlabel = None, update = 0,
                 signalHandling = None):

        """Check if a frame with the preview plot frame already exists. If it
           does, close it. Max one is to be open at a time.
        """
        if (wx.FindWindowByLabel('Preview Plot') != None):
            wx.FindWindowByLabel('Preview Plot').Close()

        """view.parent holds the WxDatatreeView. The preview plot panel
           position is to be related to it
        """
        self.view = view

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
                self.plot1DSignal(self.view.shotNumber, t, v,
                                  self.title, self.label, self.xlabel,
                                  self.update)
            else:
                raise ValueError("only 1D plots are currently supported.")
        except ValueError as e:
            self.view.log.error(str(e))

    def getFrame(self):
        """Set preview plot frame size"""
        previewplot_size = (300,250)
        """Plot"""
        self.plotFrame = \
            IMASVIZ_PreviewPlotFrame(None, size=previewplot_size,
                                     title='Plot Preview',
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

    def plot1DSignal(self, shotNumber, t, v, title='',
                     label=None, xlabel=None, update=0):
        """Plot a 1D signal as a function of time
        """

        try:
            self.updateNodeData()
            self.getFrame()

            frame = self.plotFrame

            """Set label, xlabel, ylabel and title of the preview plot"""
            label, xlabel, ylabel, title = \
                self.plotOptions(self.view, self.nodeData, shotNumber=shotNumber,
                                 label=label, xlabel=xlabel, title=title)

            """Set preview plot legend"""
            frame.panel.toggle_legend(None, True)
            """Set preview plot values"""
            u = v[0]
            ti = t[0]
            """Plot the preview plot"""
            frame.plot(ti, u, title=title, xlabel=xlabel,
                       ylabel=ylabel, label=label)
            frame.Center()

            """Get size and position of WxTreeView display window to be used
               for positioning the preview plot panel
            """
            """ - Get position"""
            px, py = self.view.parent.GetPosition()
            """ - get size"""
            sx, sy = self.view.parent.GetSize()
            """Modify the position of the preview plot panel"""
            pos_ppp = (px+sx, py)

            """Set preview plot frame position"""
            # TODO: Get WxDataTreeview position and position preview panel on
            #       the right side of it
            frame.SetPosition(pos_ppp)
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
        """Return label, xlabel, ylabel and title for the plot"""
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