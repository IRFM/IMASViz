import os
from imasviz.util.VizServices import VizServices
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalValues import FigureTypes
from imasviz.view.WxDataTreeView import WxDataTreeViewFrame
from imasviz.gui_commands.plot_commands.PlotSelectedSignals import PlotSelectedSignals
from imasviz.gui_commands.plot_commands.PlotSelectedSignalsWithWxmplot import PlotSelectedSignalsWithWxmplot
from imasviz.gui_commands.select_commands.SelectSignals import SelectSignals
from imasviz.gui_commands.select_commands.SelectSignalsGroup import SelectSignalsGroup
from imasviz.gui_commands.select_commands.UnselectAllSignals import UnselectAllSignals
from imasviz.gui_commands.select_commands.LoadSelectedData import LoadSelectedData

from imasviz.pyqt5.src.VizGUI.VizTreeView.QVizDataTreeView import QVizDataTreeViewFrame

class Browser_API():

    def __init__(self):
        self.figToNodes= {} #key = figure, values = list of selectedData
        #figureframes contains all plotting frames
        self.figureframes = {} #key = FigureType + FigureKey, example: FigureType="Figure:", FigureKey="1"

        # wxPython DTV lists
        self.wxDTVframeList = []
        self.wxDTVlist = []

        # PyQt5 DTV lists
        self.DTVframeList = []
        self.DTVlist = []

    def addNodeToFigure(self, figureKey, key, tup):
        if figureKey not in self.figToNodes:
            self.figToNodes[figureKey] = {}
        dic = self.figToNodes[figureKey]
        dic[key] = tup

    def GetPlotConfigurationPath(self, configurationName):
        """Get path to plot configuration file (.pcfg extension).
        """
        return os.environ['HOME'] + "/.imasviz/" + configurationName + ".pcfg"

    def CreateDataTree(self, dataSource):
        """Create a IDS data tree from a data source.
        """
        treeDict = {}
        if GlobalValues.TESTING:
            frame = \
                QVizDataTreeViewFrame(None, treeDict, dataSource,
                                    GlobalOperations.getIDSDefFile(GlobalValues.TESTING_IMAS_VERSION)
                                    )
        else:
            frame = \
                QVizDataTreeViewFrame(None, treeDict, dataSource,
                                    GlobalOperations.getIDSDefFile(os.environ['IMAS_VERSION'])
                                    )
        # Set WxTreeViewFrame BrowserAPI
        frame.view.imas_viz_api = self
        frame.view.dataSource = dataSource  # update the dataSource
                                                  # attached to the view

        # Add created WxDataTreeViewFrame (DTV frame) to a list of DTV frames
        self.wxDTVframeList.append(frame)

        # Add current WxDataTreeView (DTV) to a list of DTVs
        self.wxDTVlist.append(frame.view)

        return frame

    # Show the IDS data tree frame
    def ShowDataTree(self, dataTreeFrame):
        dataTreeFrame.show()

    def GetSelectedSignals(self, dataTreeFrame):
        """Returns the list of signals (nodes) dictionaries
        selected by the user or from script commands (from a single opened
        data tree view (DTVs)).

        Arguments:
            dataTreeFrame (QMainWindow) : DTV frame/main window object.
        """
        return dataTreeFrame.dataTreeView.selectedSignalsDict

    def GetSelectedSignals_AllDTVs(self):
        """Returns the signals (nodes) selected by the user of from script
           commands (from all opened data tree views (DTVs))
        """
        allSelectedSignals = {}
        for i in range(len(self.wxDTVframeList)):
            allSelectedSignals.update(self.wxDTVframeList[i].dataTreeView.selectedSignalsDict)

        return allSelectedSignals

    # Show/Hide a figure
    def HideShowFigure(self, figureKey):
        frame = self.figureframes[figureKey]
        if frame.IsShown():
            frame.Hide()
        else:
            frame.Show()

    # Return the next figure number available for plotting
    def GetFigurePlotsCount(self):
        return len(self.GetFiguresKeys())

    # Return the next figure number available for plotting
    def GetMultiPlotsCount(self):
        return len(self.GetFiguresKeys(FigureTypes.MULTIPLOTTYPE))

    def GetSubPlotsCount(self):
        return len(self.GetFiguresKeys(FigureTypes.SUBPLOTTYPE))

    def GetNextKeyForMultiplePlots(self):
        return FigureTypes.MULTIPLOTTYPE + str(self.GetMultiPlotsCount())

    def GetNextKeyForFigurePlots(self):
        """Returns label for the next figure (e.c. if 'Figure i' already exists,
           value 'Figure i+1' will be returned.
        """
        return FigureTypes.FIGURETYPE + str(self.GetFigurePlotsCount())

    def GetNextKeyForSubPlots(self):
        return FigureTypes.SUBPLOTTYPE + str(self.GetSubPlotsCount())

    def GetFiguresKeys(self, figureType=FigureTypes.FIGURETYPE):
        figureKeys = []
        for key in self.figureframes.keys():
            if key.startswith(figureType):
                figureKeys.append(key)
        return sorted(figureKeys)

    def DeleteFigure(self, figureKey):
        if figureKey in self.figureframes:
            self.figureframes[figureKey].Close()
            del self.figureframes[figureKey]

    def GetFigureKey(self, userKey, figureType):
        return figureType + userKey

    def getFigureFrame(self, figureKey):
        if figureKey in self.figureframes:
            return self.figureframes[figureKey]
        else:
            print ("No frame found with key: " + str(figureKey))

    # Plot the set of signals selected by the user
    def PlotSelectedSignals(self, dataTreeFrame, figureKey=None, update=0):
        if figureKey == None:
            figureKey = self.GetNextKeyForFigurePlots()
        PlotSelectedSignals(dataTreeFrame.wxTreeView, figureKey=figureKey,
                            update=update).execute()

    # Plot the set of signals selected by the user
    def PlotSelectedSignalsInMultiPlotFrame(self, dataTreeFrame,
                                            configFileName = None,
                                            figureKey=None, update=0):
        if figureKey == None:
            figureKey = self.GetNextKeyForMultiplePlots()
        PlotSelectedSignalsWithWxmplot(dataTreeFrame.wxTreeView,
                                       figurekey=figureKey, update=update,
                                       configFileName=configFileName).execute()

    # Plot the set of signals selected by the user
    def ApplyMultiPlotConfiguration(self, dataTreeFrame, configFileName=None,
                                    figureKey=None, update=0):
        if figureKey == None:
            figureKey = self.GetNextKeyForMultiplePlots()
        PlotSelectedSignalsWithWxmplot(dataTreeFrame.wxTreeView,
                                       figurekey=figureKey, update=update,
                                       configFileName=configFileName).execute()

    # Load IDSs data for the given data tree frame
    def LoadMultipleIDSData(self, dataTreeFrame, IDSNamesList, occurrence=0,
                            threadingEvent=None):
        for IDSName in IDSNamesList:
            self.LoadIDSData(dataTreeFrame, IDSName, occurrence, threadingEvent)

    #Load IDS data for a given data tree frame and a given occurrence
    def LoadIDSData(self, dataTreeFrame, IDSName, occurrence=0,
                    threadingEvent=None):
        dataTreeFrame.wxTreeView.setIDSNameSelected(IDSName)
        LoadSelectedData(dataTreeFrame.wxTreeView, occurrence, threadingEvent).execute()

    # Select signals from a list of IMAS paths for the given data tree frame
    def SelectSignals(self, dataTreeFrame, pathsList):
        SelectSignals(dataTreeFrame.dataTreeView, pathsList).execute()

    #Plot select signals from multiple data tree frames (different shots) on a single plot window
    def PlotSelectedSignalsFrom(self, dataTreeFramesList, figureKey=None):
        i = 0
        update = 0
        for f in dataTreeFramesList:
            if i!=0:
                update = 1
            if figureKey == None:
                figureKey = self.GetNextKeyForFigurePlots()
            PlotSelectedSignals(f.wxTreeView, figureKey=figureKey,
                                update=update).execute()
            i += 1

    # Unselect all previously selected signals for the given data tree frame
    def UnSelectAllSignals(self, dataTreeFrame):
        UnselectAllSignals(dataTreeFrame.wxTreeView).execute()

    def SelectSignalsGroup(self, dataTreeFrame, occurrence, onePathInTheGroup):
        """Select a group of all signals - siblings of the node containing the
        'onePathInTheGroup' path data.

        Arguments:
            dataTreeFrame     (obj) : wxDataTreeViewFrame object.
            occurrence        (int) : IDS occurrence number (0-9).
            onePathInTheGroup (str) : An IDS path to one of the node
                                      (signals), containing a data array
                                      (e.g. FLT_1D), of which all siblings
                                      are to be selected.
                                      Example:
                                      'magnetics/flux_loop(0)/flux/data'
        """
        # Get full data of the node (given 'path' is one of them)
        oneNodeInTheGroup = VizServices().getNodeData(dataTreeFrame.wxTreeView,
            occurrence, onePathInTheGroup)
        # Select all sibling signals of the node
        SelectSignalsGroup(dataTreeFrame.wxTreeView, oneNodeInTheGroup).execute()

    #---------------------------------------------------------------------------
    # PyQt5 routine variations

    def QCreateDataTree(self, dataSource):
        """Create a IDS data tree from a data source. PyQt variant of the
        'CreateDataTree' function (wxPython).

        Arguments:
            dataSource (IMASDataSource) : IDS data source from DataSourceFactory
        """
        treeDict = {}

        # Create data tree view (DTV) frame
        if GlobalValues.TESTING:
            frame = \
                QVizDataTreeViewFrame(parent=None,
                                      views=treeDict,
                                      dataSource=dataSource,
                                      IDSDefFile=GlobalOperations.getIDSDefFile(GlobalValues.TESTING_IMAS_VERSION))
        else:
            frame = \
                QVizDataTreeViewFrame(parent=None,
                                      views=treeDict,
                                      dataSource=dataSource,
                                      IDSDefFile=GlobalOperations.getIDSDefFile(os.environ['IMAS_VERSION']))

        # Set data tree view (DTV) frame BrowserAPI
        frame.dataTreeView.imas_viz_api = self
        frame.dataTreeView.dataSource = dataSource  # update the dataSource
                                                  # attached to the view

        # Add created data tree view (DTV) frame to a list of DTV frames
        self.DTVframeList.append(frame)

        # Add current data tree view (DTV) frame to a list of DTVs
        self.DTVlist.append(frame.dataTreeView)

        return frame
