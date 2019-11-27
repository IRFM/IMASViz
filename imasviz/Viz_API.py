#  Name   : Viz_API
#
#          IMASViz Application Programming Interface.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
#****************************************************

import os

from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPlotWidget import QVizPlotWidget
from imasviz.VizGUI.VizTreeView.QVizDataTreeView import QVizDataTreeViewFrame, QVizDataTreeView
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSelectedSignals import QVizPlotSelectedSignals
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignals import QVizSelectSignals
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignalsGroup import QVizSelectSignalsGroup
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizUnselectAllSignals import QVizUnselectAllSignals
from imasviz.VizUtils.QVizGlobalValues import FigureTypes
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues, QVizPreferences
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadSelectedData import QVizLoadSelectedData
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizDataAccess.QVizDataAccessFactory import QVizDataAccessFactory
from PyQt5.QtWidgets import QMdiSubWindow

class Viz_API:

    def __init__(self, parent=None):

        self.parent = parent

        self.figToNodes= {} #key = figure, values = list of selectedData
        #figureframes contains all plotting frames
        self.figureframes = {} #key = FigureType + FigureKey, example: FigureType="Figure:", FigureKey="1"

        # PyQt5 DTV lists
        self.DTVframeList = []
        self.DTVlist = []

        QVizPreferences().build()

    def GetDTVFrames(self):
        return self.DTVframeList

    def GetDataSources(self):
        dataSourcesList = []
        for dtv in self.DTVlist:
            dataSourcesList.append(dtv.dataSource)
        return dataSourcesList

    def isDataSourceAlreadyOpened(self, dataSource):
        dataSourcesList = self.GetDataSources()
        for ds in dataSourcesList:
            if dataSource.getKey() == ds.getKey():
                return True
        return False

    def GetDTVFor(self, dataSourceKey):
        for dtv in self.DTVlist:
            if dataSourceKey == dtv.dataSource.getKey():
                return dtv
        return None

    def removeDTVFrame(self, frame):
        self.DTVframeList.remove(frame)
        self.DTVlist.remove(frame.dataTreeView)

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
            dataSource (QVizIMASDataSource) : IDS data source from
                                          QVizDataSourceFactory.
        """
        if QVizGlobalValues.TESTING:
            IMAS_VERSION = QVizGlobalValues.TESTING_IMAS_VERSION
        else:
            IMAS_VERSION = os.environ['IMAS_VERSION']

        frame = QVizDataTreeViewFrame(parent=None,
                                      views={},
                                      dataSource=dataSource,
                                      IDSDefFile=QVizGlobalOperations.getIDSDefFile(IMAS_VERSION),
                                      imas_viz_api=self)

        frame.dataTreeView.dataSource = dataSource # update the dataSource
                                                   # attached to the view

        # Add created data tree view (DTV) frame to a list of DTV frames
        self.DTVframeList.append(frame)

        # Add current data tree view (DTV) frame to a list of DTVs
        self.DTVlist.append(frame.dataTreeView)

        return frame


    # Show the IDS data tree frame
    def ShowDataTree(self, dataTreeView):
        if isinstance(dataTreeView, QVizDataTreeViewFrame):

            # If MDI is present, add the DTV to it as a subwindow
            if self.getMDI() != None:
                subWindow = QMdiSubWindow()
                subWindow.setWidget(dataTreeView)

                self.getMDI().addSubWindow(subWindow)
            dataTreeView.show()
        elif isinstance(dataTreeView, QVizDataTreeView):
            dataTreeView.parent.show()
        else:
            raise ValueError('Wrong argument type arg for ShowDataTree(arg).')

    def ShowNodesSelection(self, selectedSignalsDict):
        from imasviz.VizGUI.VizWidgets.QVizNodesSelectionWindow import QVizNodesSelectionWindow
        self.nsw = QVizNodesSelectionWindow(selectedSignalsDict)
        self.nsw.show()

    def getSelectedSignalsDict(self, dataTreeFrame):
        """Returns the list of signals (nodes) dictionaries
        selected by the user or from script commands (from a single opened
        data tree view (DTVs)).

        Arguments:
            dataTreeFrame (QMainWindow) : DTV frame/main window object.
        """
        return dataTreeFrame.dataTreeView.selectedSignalsDict

    def getSelectedSignalsDict_AllDTVs(self):
        """Returns the signals (nodes) selected by the user of from script
           commands (from all opened data tree views (DTVs))
        """
        allSelectedSignals = {}
        for i in range(len(self.DTVframeList)):
            allSelectedSignals.update(self.DTVframeList[i].dataTreeView.selectedSignalsDict)

        return allSelectedSignals

    def ShowHideFigure(self, figureKey):
        """Hide/show a figure.

        Arguments:
            figureKey (str) : Figure plotwidget window label (e.g. 'Figure:0).
        """
        frame = self.figureframes[figureKey]
        if frame.window().objectName() == "IMASViz root window":
            # Hide/Show MDI subwindow
            if frame.parent().isVisible():
                # frame.parent() is QMdiSubWindow
                frame.parent().hide()
            else:
                frame.parent().show()
        else:
            if frame.isVisible():
                frame.hide()
            else:
                frame.show()

    # Return the next figure number available for plotting
    def GetFigurePlotsCount(self):
        return len(self.GetFiguresKeys())

    # Return the next figure number available for plotting
    def GetTablePlotViewsCount(self):
        return len(self.GetFiguresKeys(FigureTypes.TABLEPLOTTYPE))

    def GetStackedPlotViewsCount(self):
        return len(self.GetFiguresKeys(FigureTypes.STACKEDPLOTTYPE))

    def getNextKeyForTablePlotView(self):
        return FigureTypes.TABLEPLOTTYPE + str(self.GetTablePlotViewsCount())

    def GetNextKeyForFigurePlots(self):
        """Returns string label for the next figure (e.c. if 'Figure i' is the
        last figure on the list of existing figures, value 'Figure i+1' is
        returned.)
        """
        return FigureTypes.FIGURETYPE + str(self.GetFigurePlotsCount())

    def getNextKeyForStackedPlotView(self):
        return FigureTypes.STACKEDPLOTTYPE + str(self.GetStackedPlotViewsCount())

    def GetFiguresKeys(self, figureType=FigureTypes.FIGURETYPE):
        figureKeys = []
        for key in self.figureframes.keys():
            if key.startswith(figureType):
                figureKeys.append(key)
        return sorted(figureKeys)

    def DeleteFigure(self, figureKey):
        if figureKey in self.figureframes:
            frame = self.figureframes[figureKey]
            if frame.window().objectName() == "IMASViz root window":
                frame.parent().hide()
                frame.parent().deleteLater()
            else:
                frame.close()
            del self.figureframes[figureKey]
        if figureKey in self.figToNodes:
            del self.figToNodes[figureKey]

    def GetFigureKey(self, userKey, figureType):
        return figureType + userKey

    def getFigureKeyNum(self, figureKey, figureType):
        """Extract figure number from figureKey (e.g. 'Figure:0' -> 0).

        Arguments (str) figureKey: Figure key (label) (e.g. 'Figure:0').
        """
        numFig = int(figureKey[len(figureType):])
        return numFig

    def getFigureFrame(self, figureKey):
        if figureKey in self.figureframes:
            return self.figureframes[figureKey]
        else:
            print("No frame found with key: " + str(figureKey))

    # Plot the set of signals selected by the user
    def PlotSelectedSignals(self, dataTreeFrame, plotWidget=None, figureKey=None, update=0, all_DTV=False):
        if figureKey is None:
            figureKey = self.GetNextKeyForFigurePlots()
        QVizPlotSelectedSignals(dataTreeFrame.dataTreeView, figureKey=figureKey,
                                update=update, all_DTV=all_DTV).execute(plotWidget)

    def PlotSelectedSignalsInTablePlotViewFrame(self, dataTreeFrame,
                                            configFileName = None,
                                            update=0,
                                            all_DTV=False):
        """ Plot the set of signal nodes selected by the user to a new Table
        Plot View.
        """
        QVizSignalHandling(dataTreeFrame.dataTreeView).onPlotToTablePlotView(all_DTV)

    # Plot the set of signals selected by the user
    def ApplyTablePlotViewConfiguration(self, dataTreeFrame, configFilePath,
                                    figureKey=None, update=0, all_DTV=False):
        """ Plot the set of signal nodes selected by the user to a new Table
        Plot View and apply configuration.
        """
        QVizSignalHandling(dataTreeFrame.dataTreeView).onPlotToTablePlotView(
            all_DTV=all_DTV,
            configFile=configFilePath)
        #if figureKey == None:
        #    figureKey = self.getNextKeyForTablePlotView()
        #PlotSelectedSignalsWithWxmplot(dataTreeFrame.wxTreeView,
        #                               figurekey=figureKey, update=update,
        #                               configFileName=configFileName).execute()

    # Load IDSs data for the given data tree frame
    def LoadMultipleIDSData(self, dataTreeFrame, IDSNamesList, occurrence=0,
                            threadingEvent=None):
        for IDSName in IDSNamesList:
            self.LoadIDSData(dataTreeFrame, IDSName, occurrence, threadingEvent)

    #Load IDS data for a given data tree frame and a given occurrence
    def LoadIDSData(self, dataTreeFrame, IDSName, occurrence=0,
                    threadingEvent=None):

        if isinstance(dataTreeFrame, QVizDataTreeViewFrame):
            QVizLoadSelectedData(dataTreeFrame.dataTreeView, IDSName, occurrence, threadingEvent).execute()
        else:
            QVizLoadSelectedData(dataTreeFrame, IDSName, occurrence, threadingEvent).execute()


    def SelectSignals(self, dataTreeWindow, pathsMap):
        """Select signals from a list of IMAS paths for the given tree view
        QMainWindow.

        Arguments:
            dataTreeWindow (QMainWindow) : DTV QMainWindow object (containing
                                           DTV - QTreeWidget).
            pathsMap       (dict)       : pathsMap['paths'] : a list if signal paths (e.g.
                                           ['magnetics/flux_loop(0)/flux/data'])
                                           pathsMap['occurrences'] : a list of occurrences
        """
        QVizSelectSignals(dataTreeWindow.dataTreeView, pathsMap).execute()

    def PlotSelectedSignalsFrom(self, dataTreeFramesList, figureKey=None, all_DTV=False):
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
            if i != 0:
                update = 1
            if figureKey is None:
                figureKey = self.GetNextKeyForFigurePlots()
            QVizPlotSelectedSignals(f.dataTreeView, figureKey=figureKey,
                                update=update, all_DTV=all_DTV).execute()
            i += 1

    # Unselect all previously selected signals for the given data tree frame
    def UnSelectAllSignals(self, dataTreeFrame):
        QVizUnselectAllSignals(dataTreeFrame.dataTreeView).execute()


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
        QVizSelectSignalsGroup(dataTreeFrame.dataTreeView,  dataTreeFrame.dataTreeView.selectedItem.infoDict).execute()

    def IDSDataAlreadyFetched(self, dataTreeView, IDSName, occurrence):
        key = IDSName + "/" + str(occurrence)
        if key in dataTreeView.ids_roots_occurrence:
            return True
        else:
            return False

    def GetDataSource(self, dataTreeFrame):
        if isinstance(dataTreeFrame, QVizDataTreeViewFrame):
            return dataTreeFrame.parent.dataSource
        else:
            return dataTreeFrame.dataSource

    def GetIMASDataEntry(self, dataTreeFrame, occurrence):
        if isinstance(dataTreeFrame, QVizDataTreeViewFrame):
            return self.GetDataSource(dataTreeFrame.parent).ids[occurrence]
        else:
            return self.GetDataSource(dataTreeFrame).ids[occurrence]

    def CreatePlotWidget(self):
        figureKey = self.GetNextKeyForFigurePlots()
        plotWidget = QVizPlotWidget(size=(600, 550), title=figureKey)
        self.figureframes[figureKey] = plotWidget
        return figureKey, plotWidget

    def GetPlotWidget(self, figureKey=0):
        if figureKey in self.figureframes:
            plotWidget = self.figureframes[figureKey]
        else:
            figureKey, plotWidget = self.CreatePlotWidget()
        return figureKey, plotWidget

    def GetSignal(dataTreeView, vizTreeNode, as_function_of_time=False, coordinate1Index=0, plotWidget=None):
        try:
            signalDataAccess = QVizDataAccessFactory(dataTreeView.dataSource).create()
            return  signalDataAccess.GetSignalAt(vizTreeNode, plotWidget, as_function_of_time, coordinate1Index)
        except:
            raise

    def getMDI(self):
        if self.parent != None:
            return self.parent
        return None
