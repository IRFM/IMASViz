import os
from imasviz.util.VizServices import VizServices
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalValues import FigureTypes
from imasviz.pyqt5.src.VizGUI.VizTreeView.QVizDataTreeView import QVizDataTreeViewFrame
from imasviz.pyqt5.src.VizGUI.VizPlot.QVizPlotSelectedSignals import QVizPlotSelectedSignals
from imasviz.pyqt5.src.VizGUI.VizGUICommands.VizSignalSelectionCommands.QVizUnselectAllSignals \
    import QVizUnselectAllSignals
from imasviz.pyqt5.src.VizGUI.VizGUICommands.VizSignalSelectionCommands.QVizSelectSignalsGroup \
    import QVizSelectSignalsGroup
from imasviz.pyqt5.src.VizGUI.VizGUICommands.VizSignalSelectionCommands.QVizSelectSignal \
    import QVizSelectSignal
from imasviz.pyqt5.src.VizGUI.VizGUICommands.VizSignalSelectionCommands.QVizSelectSignals \
    import QVizSelectSignals

from imasviz.gui_commands.select_commands.SelectSignals import SelectSignals
from imasviz.gui_commands.select_commands.SelectSignalsGroup import SelectSignalsGroup
from imasviz.gui_commands.select_commands.UnselectAllSignals import UnselectAllSignals
from imasviz.gui_commands.select_commands.LoadSelectedData import LoadSelectedData
from imasviz.view.WxDataTreeView import WxDataTreeViewFrame
from imasviz.gui_commands.plot_commands.PlotSelectedSignalsWithWxmplot import PlotSelectedSignalsWithWxmplot

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
        Arguments:
            dataSource (IMASDataSource) : IDS data source from
                                          DataSourceFactory.
        """
        treeDict = {}
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
        frame.dataTreeView.dataSource = dataSource # update the dataSource
                                                   # attached to the view

        # Add created data tree view (DTV) frame to a list of DTV frames
        self.DTVframeList.append(frame)

        # Add current data tree view (DTV) frame to a list of DTVs
        self.DTVlist.append(frame.dataTreeView)

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

    def ShowHideFigure(self, figureKey):
        """Hide/show a figure.

        Arguments:
            figureKey (str) : Figure plotwidget window label (e.g. 'Figure:0).
        """
        frame = self.figureframes[figureKey]
        if frame.isVisible():
            frame.hide()
        else:
            frame.show()

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
        """Returns string label for the next figure (e.c. if 'Figure i' is the
        last figure on the list of existing figures, value 'Figure i+1' is
        returned.)
        """

        if self.GetFigurePlotsCount() == 0:
            # Figure number when no figures exist/are present
            numFig_next = 0
        else:
            # Get the last figure on the list of figures and get its figure
            # number
            # Note: this is used to avoid problems when figures top on list
            # got deleted.
            numFig = self.getFigureKeyNum(self.GetFiguresKeys()[-1])
            numFig_next = numFig + 1

        return FigureTypes.FIGURETYPE + str(numFig_next)

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
            self.figureframes[figureKey].close()
            del self.figureframes[figureKey]

    def GetFigureKey(self, userKey, figureType):
        return figureType + userKey

    def getFigureKeyNum(self, figureKey):
        """Extract figure number from figureKey (e.g. 'Figure:0' -> 0).

        Arguments (str) figureKey: Figure key (label) (e.g. 'Figure:0').
        """

        numFig = int(figureKey.split(':')[1])
        return numFig

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

    def SelectSignals(self, dataTreeWindow, pathsList):
        """Select signals from a list of IMAS paths for the given tree view
        QMainWindow.

        Arguments:
            dataTreeWindow (QMainWindow) : DTV QMainWindow object (containing
                                           DTV - QTreeWidget).
            nodeData       (array)       : A list if signal paths (e.g.
                                           ['magnetics/flux_loop(0)/flux/data'])
        """
        QVizSelectSignals(dataTreeWindow.dataTreeView, pathsList).execute()

    def PlotSelectedSignalsFrom(self, dataTreeFramesList, figureKey=None):
        """Plot select signals from multiple data tree frames (different shots)
        on a single plot window.

        Arguments:
            dataTreeFramesList (Array) : A list of DTV frames (QMainWindow
                                         objects)
            figurekey          (string) : Figure key/label.
        """
        i = 0
        update = 0
        for f in dataTreeFramesList:
            if i!=0:
                update = 1
            if figureKey == None:
                figureKey = self.GetNextKeyForFigurePlots()
            QVizPlotSelectedSignals(f.dataTreeView, figureKey=figureKey,
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
