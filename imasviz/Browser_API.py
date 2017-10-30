import os
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.view.WxDataTreeView import WxDataTreeViewFrame
from imasviz.gui_commands.plot_commands.PlotSelectedSignals import PlotSelectedSignals
from imasviz.gui_commands.plot_commands.PlotSelectedSignalsWithWxmplot import PlotSelectedSignalsWithWxmplot
from imasviz.gui_commands.select_commands.SelectSignals import SelectSignals
from imasviz.gui_commands.select_commands.UnselectAllSignals import UnselectAllSignals
from imasviz.gui_commands.select_commands.LoadSelectedData import LoadSelectedData

class Browser_API():

    def __init__(self):
        self.figures = {}
        self.figToNodes= {} #key = figure, values = list of selectedData
        self.figureframes={}
        self.subplots={}

        self.multiPlotsFrames=[] #key=0,1,2 value=list of frames

    def addNodeToFigure(self, fig, key, tup):
        if fig not in self.figToNodes:
            self.figToNodes[fig] = {}
        dic = self.figToNodes[fig]
        dic[key] = tup

    #Create a IDS data tree from a data source
    def CreateDataTree(self, dataSource):
        treeDict = {}
        frame = WxDataTreeViewFrame(None, treeDict, dataSource, GlobalOperations.getIDSDefFile(os.environ['IMAS_DATA_DICTIONARY_VERSION']), size=(450,550))
        frame.wxTreeView.imas_viz_api = self
        frame.wxTreeView.dataSource = dataSource  # update the dataSource attached to the view
        return frame

    # Show the IDS data tree frame
    def ShowDataTree(self, dataTreeFrame):
        dataTreeFrame.Show()

    # Returns the signals (nodes) selected by the user or from script commands
    def GetSelectedSignals(self, dataTreeFrame):
        return dataTreeFrame.wxTreeView.selectedSignals

    # Show/Hide a figure
    def HideShowFigure(self, numFig):
        frame = self.figureframes[numFig]
        if frame.IsShown():
            frame.Hide()
        else:
            frame.Show()

    # Show/Hide a subplots window
    def HideShowSubplots(self, key):
        subplot = self.subplots[key]
        if subplot.IsShown():
            subplot.Hide()
        else:
            subplot.ShowFrame()

    # Return the next figure number available for plotting
    def GetNextNumFigForNewPlot(self):
        return len(self.figures)

    # Return the next figure number available for plotting
    def GetNextNumFigForNewMultiplePlots(self):
        return len(self.multiPlotsFrames)

    # Plot the set of signals selected by the user
    def PlotSelectedSignals(self, dataTreeFrame, numfig=0, update=0):
        PlotSelectedSignals(dataTreeFrame.wxTreeView, numfig=0, update=0).execute()

    # Plot the set of signals selected by the user
    def PlotSelectedSignalsInMultiFrame(self, dataTreeFrame, configFileName = None, numfig=0, update=0):
        PlotSelectedSignalsWithWxmplot(dataTreeFrame.wxTreeView, numfig=0, update=0, configFileName=configFileName).execute()
    
    # Load IDSs data for the given data tree frame
    def LoadMultipleIDSData(self, dataTreeFrame, IDSNamesList, occurrence=0, threadingEvent=None):
        for IDSName in IDSNamesList:
            self.LoadIDSData(dataTreeFrame, IDSName, occurrence, threadingEvent)

    #Load IDS data for a given data tree frame and a given occurrence
    def LoadIDSData(self, dataTreeFrame, IDSName, occurrence=0, threadingEvent=None):
        dataTreeFrame.wxTreeView.setIDSNameSelected(IDSName)
        LoadSelectedData(dataTreeFrame.wxTreeView, occurrence, threadingEvent).execute()

    # Select signals from a list of IMAS paths for the given data tree frame
    def SelectSignals(self, dataTreeFrame, pathsList):
        SelectSignals(dataTreeFrame.wxTreeView, pathsList).execute()
    
    #Plot select signals from multiple data tree frames (different shots) on a single plot window
    def PlotSelectedSignalsFrom(self, dataTreeFramesList, numfig=0):
        i = 0
        update = 0
        for f in dataTreeFramesList:
            if i!=0:
                update = 1
            PlotSelectedSignals(f.wxTreeView, numfig=numfig, update=update).execute()
            i += 1

    # Unselect all previously selected signals for the given data tree frame
    def UnSelectAllSignals(self, dataTreeFrame):
        UnselectAllSignals(dataTreeFrame.wxTreeView).execute()
