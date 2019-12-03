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
import logging

from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizUtils.QVizGlobalValues import FigureTypes, QVizGlobalValues, QVizPreferences
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPlotWidget import QVizPlotWidget
from imasviz.VizGUI.VizTreeView.QVizDataTreeView import QVizDataTreeViewFrame, QVizDataTreeView
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSelectedSignals import QVizPlotSelectedSignals
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignals import QVizSelectSignals
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignalsGroup import QVizSelectSignalsGroup
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizUnselectAllSignals import QVizUnselectAllSignals
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadSelectedData import QVizLoadSelectedData
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling import QVizSignalHandling
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal import QVizPlotSignal
from imasviz.VizDataAccess.QVizDataAccessFactory import QVizDataAccessFactory
from PyQt5.QtWidgets import QMdiSubWindow

class Viz_API:

    def __init__(self, parent=None):

        self.parent = parent

        self.figToNodes= {} #key = figure, values = list of selected nodes
        #figureframes contains all plotting frames
        self.figureframes = {} #key = FigureType + FigureKey, example: FigureType="Figure:", FigureKey="1"
        self.DTVframeList = []
        self.DTVlist = []

        QVizPreferences().build()

    # Return the list of frames currently opened (QVizDataTreeViewFrame type object)
    # There is one frame for one shot
    def GetDTVFrames(self):
        return self.DTVframeList

    # Return the list of datasource currently opened (QVizIMASDataSource type)
    # A data source is associated to one shot
    def GetDataSources(self):
        dataSourcesList = []
        for dtv in self.DTVlist:
            dataSourcesList.append(dtv.dataSource)
        return dataSourcesList

    # Indicates if this data source object 'datasource' has been already created
    def isDataSourceAlreadyOpened(self, dataSource):
        dataSourcesList = self.GetDataSources()
        for ds in dataSourcesList:
            if dataSource.getKey() == ds.getKey():
                return True
        return False

    # Return the frame (of type QVizDataTreeViewFrame) for the given data source key
    def GetDTVFor(self, dataSourceKey):
        for dtv in self.DTVlist:
            if dataSourceKey == dtv.dataSource.getKey():
                return dtv
        return None

    # Return the shot view frame (QVizDataTreeViewFrame) from the list of opened frames
    def RemoveDTVFrame(self, frame):
        self.DTVframeList.remove(frame)
        self.DTVlist.remove(frame.dataTreeView)

    # Add an entry to the figToNodes[figureKey] dictionary where:
    # key   = dtv.dataSource.dataKey(vizTreeNode)      --> String
    # value = (dtv.dataSource.shotNumber, vizTreeNode) --> Tuple
    def AddNodeToFigure(self, figureKey, key, tup):
        if figureKey not in self.figToNodes:
            self.figToNodes[figureKey] = {}
        dic = self.figToNodes[figureKey]
        dic[key] = tup


    # Return the path to the configuration file with name 'configurationName'
    def GetPlotConfigurationPath(self, configurationName):
        """Get path to plot configuration file (.pcfg extension).
        """
        return os.environ['HOME'] + "/.imasviz/" + configurationName + ".pcfg"

    # Creates the (QVizDataTreeViewFrame) frame for the specified data source
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


    # Displays the specified data tree frame
    # dataTreeView can be a QVizDataTreeView object or a QVizDataTreeViewFrame object
    # NOTE: a QVizDataTreeView accepts QVizDataTreeViewFrame as a parent object
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

    # Displays a frame showing a list of all selected nodes from the dataTreeView object
    # DTV can be a QVizDataTreeView object or a QVizDataTreeViewFrame object
    # NOTE: a QVizDataTreeView accepts QVizDataTreeViewFrame as a parent object
    def ShowNodesSelection(self, DTV):
        from imasviz.VizGUI.VizWidgets.QVizNodesSelectionWindow import QVizNodesSelectionWindow
        if isinstance(DTV, QVizDataTreeViewFrame):
            dataTreeView = DTV.dataTreeView
        self.nsw = QVizNodesSelectionWindow(dataTreeView)
        self.nsw.show()

    def GetSelectedSignalsDict(self, DTV):
        """Returns the list of signals (nodes) dictionaries
        selected by the user or from script commands (from a single opened
        data tree view (DTVs)).

        Arguments:
            DTV: QVizDataTreeViewFrame or QVizDataTreeView object
        """
        if isinstance(DTV, QVizDataTreeViewFrame):
            dataTreeView = DTV.dataTreeView
        else:
            dataTreeView = DTV
        return dataTreeView.selectedSignalsDict

    def GetSelectedSignalsDictFromAllDTVs(self):
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
                frame.parent().hide() # frame.parent() is QMdiSubWindow
            else:
                # To show the figure, closed with X button, then both MDI
                # subwindow AND the embedded plot frame must be shown
                frame.parent().show()
                frame.show()
        else:
            if frame.isVisible():
                frame.hide()
            else:
                frame.show()

    def GetFigurePlotsCount(self):
        """Return the next figure number available for plotting.
        """
        return len(self.GetFiguresKeys())

    def GetTablePlotViewsCount(self):
        """Return the next table plot number available for plotting.
        """
        return len(self.GetFiguresKeys(FigureTypes.TABLEPLOTTYPE))

    def GetStackedPlotViewsCount(self):
        """Return the next stacked plot number available for plotting.
        """
        return len(self.GetFiguresKeys(FigureTypes.STACKEDPLOTTYPE))

    def GetNextKeyForTablePlotView(self):
        """Returns string label for the next table plot (e.c. if 'TablePlot i' is the
                last table plot on the list of existing table plots, value 'TablePlot i+1' is
                returned.)
                """
        return FigureTypes.TABLEPLOTTYPE + str(self.GetTablePlotViewsCount())

    def GetNextKeyForFigurePlots(self):
        """Returns string label for the next figure (e.c. if 'Figure i' is the
        last figure on the list of existing figures, value 'Figure i+1' is
        returned.)
        """
        return FigureTypes.FIGURETYPE + str(self.GetFigurePlotsCount())

    def GetNextKeyForStackedPlotView(self):
        """Returns string label for the next stacked plot (e.c. if 'StackedPlot i' is the
                        last table plot on the list of existing stacked plots, value 'StackedPlot i+1' is
                        returned.)
                        """
        return FigureTypes.STACKEDPLOTTYPE + str(self.GetStackedPlotViewsCount())

    def GetFiguresKeys(self, figureType=FigureTypes.FIGURETYPE):
        figureKeys = []
        for key in self.figureframes.keys():
            if key.startswith(figureType):
                figureKeys.append(key)
        return sorted(figureKeys)

    def DeleteFigure(self, figureKey):
        """Delete the figure
        Arguments:
            figureKey (str) : Figure plotwidget window label (e.g. 'Figure:0).
                """
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

    def GetFigureKey(self, userKey, figureType=FigureTypes.FIGURETYPE):
        """Get the figure key
                Arguments:
                    userKey (str) : figure number
                    figureType : FigureTypes.FIGURETYPE
                        """
        return figureType + userKey

    def getFigureKeyNum(self, figureKey, figureType):
        """Extract figure number from figureKey (e.g. 'Figure:0' -> 0).
        Arguments :
        figureKey (str) : Figure key (label) (e.g. 'Figure:0').
        figureType (str) : FigureTypes.FIGURETYPE or FigureTypes.TABLEPLOTTYPE or FigureTypes.STACKEDPLOTTYPE
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
        QVizSelectSignalsGroup(dataTreeFrame.dataTreeView,  dataTreeFrame.dataTreeView.selectedItem).execute()

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

    def CreatePlotWidget(self, dataTreeView, addTimeSlider=False, addCoordinateSlider=False):
        figureKey = self.GetNextKeyForFigurePlots()
        plotWidget = QVizPlotWidget(size=(600, 550),
                                    title=figureKey,
                                    dataTreeView=dataTreeView,
                                    addTimeSlider=addTimeSlider,
                                    addCoordinateSlider=addCoordinateSlider)
        self.figureframes[figureKey] = plotWidget
        return figureKey, plotWidget

    def GetPlotWidget(self, dataTreeView, figureKey=0, addTimeSlider=False, addCoordinateSlider=False):
        if figureKey in self.figureframes:
            plotWidget = self.figureframes[figureKey]
        else:
            figureKey, plotWidget = self.CreatePlotWidget(dataTreeView=dataTreeView,
                                                          addTimeSlider=addTimeSlider,
                                                          addCoordinateSlider=addCoordinateSlider)
        return figureKey, plotWidget

    def GetSignal(dataTreeView, vizTreeNode, as_function_of_time=False, coordinate1Index=0, plotWidget=None):
        try:
            signalDataAccess = QVizDataAccessFactory(dataTreeView.dataSource).create()
            return signalDataAccess.GetSignalAt(vizTreeNode, plotWidget, as_function_of_time, coordinate1Index)
        except:
            raise

    def plotSignalVsTimeCommand(self, dataTreeView):
        """Plotting of signal node, found within the 'time_slice[:]' array of
        structures in IDS. For certain physical quantities (e.g.
        equilibrium.time_slice[:].profiles_1d.phi) it plots how it changes
        through time.

        Example:
        (e=equilibrium)
        Index i -> x = array time values (e.time). n = len(e.time)
                   y = array of values ([e.time_slice[0].profiles_1d.phi[i],
                                         e.time_slice[1].profiles_1d.phi[i],
                                         ...
                                         e.time_slice[n].profiles_1d.phi[i])
        """
        # Get currently selected QVizTreeNode (QTreeWidgetItem)
        try:
            treeNode = dataTreeView.selectedItem
            # Get signal node index
            index = treeNode.infoDict['i']
            # Get label and title
            label, title, dummy = \
                treeNode.coordinateLabels(coordinateNumber=1, dtv=dataTreeView, index=index)
            figureKey, plotWidget = self.getPlotWidget(figureKey=None, addCoordinateSlider=True)
            self.addPlotWidgetToMDI(plotWidget)
            p = QVizPlotSignal(dataTreeView=dataTreeView,
                           vizTreeNode=treeNode,
                           title=title,
                           label=label,
                           xlabel="time[s]")
            p.execute(plotWidget, figureKey=figureKey, update=0)
        except ValueError as e:
            logging.error(str(e))

    def plot0D_DataVsTimeCommand(self, dataTreeView):

        """Plotting of 0D data nodes, found within timed AOS
        """
        try:
            # Get currently selected QVizTreeNode (QTreeWidgetItem)
            treeNode = dataTreeView.selectedItem
            figureKey, plotWidget = self.GetPlotWidget(dataTreeView=dataTreeView, figureKey=None) #None will force a new Figure
            self.addPlotWidgetToMDI(plotWidget)
            p = QVizPlotSignal(dataTreeView=dataTreeView,
                               vizTreeNode=treeNode,
                               xlabel="time[s]")
            p.execute(plotWidget, figureKey=figureKey, update=0)
        except ValueError as e:
            logging.error(str(e))

    def plotVsTimeAtGivenCoordinate1(self, dataTreeView, coordinateIndex, currentFigureKey,
                                     treeNode, update, dataset_to_update=0):
        """Overwrite/Update the existing plot (done with
        'plotSignalVsTimeCommand' routine and currently still shown in
        the plot window labeled as 'currentFigureKey') using the same
        physical quantity (found in sibling node of the same structure (AOS))
        but with different array positional index.

        Arguments:
            coordinateIndex             (int) : Array positional index.
            currentFigureKey  (str) : Label of the current/relevant figure
                                      window.
            treeNode (QVizTreeNode) : QTreeWidgetItem holding node data to
                                      replace the current plot in figure window.
        """
        try:

            # Get label, title and xlabel
            if treeNode.is1DAndDynamic():
                label, title, xlabel = treeNode.coordinateLabels(
                    coordinateNumber=1, dtv=dataTreeView, index=coordinateIndex)

            elif treeNode.is0DAndDynamic():
                logging.warning(
                    "Data node '" + treeNode.getName() + "' has no explicit dependency on coordinate1 dimension.")
                return

            else:
                logging.error("plotVsTimeAtGivenCoordinate1() supports only nodes with dimension <= 1D.")
                return


            currentFigureKey, plotWidget = self.GetPlotWidget(dataTreeView=dataTreeView,
                                                              figureKey=currentFigureKey,
                                                              addCoordinateSlider=True)
            self.addPlotWidgetToMDI(plotWidget)
            # Update/Overwrite plot
            QVizPlotSignal(dataTreeView=dataTreeView,
                           title=title,
                           label=label,
                           xlabel="time[s]",
                           vizTreeNode=treeNode).execute(plotWidget=plotWidget,
                                                         figureKey=currentFigureKey,
                                                         update=update,
                                                         dataset_to_update=dataset_to_update)
        except ValueError as e:
            logging.error(str(e))

    def plotVsCoordinate1AtGivenTime(self, dataTreeView, time_index, currentFigureKey,
                                     treeNode, update, dataset_to_update=0):
        """Overwrite/Update the existing plot (done with
        'plotSignalCommand' routine and currently still shown in
        the plot window labeled as 'currentFigureKey') but for different time
        slice. The node must be of the same structure (sibling to the node used
        for the previous plot and both are located within the 'time_slice[:]'
        structure').

        Arguments:
            time_index        (int) : Time slice index.
            currentFigureKey  (str) : Label of the current/relevant figure
                                      window.
            treeNode (QVizTreeNode) : QTreeWidgetItem holding node data to
                                      replace the current plot in figure window.
        """
        try:
            currentFigureKey, plotWidget = self.GetPlotWidget(dataTreeView=dataTreeView,
                                                              figureKey=currentFigureKey,
                                                              addTimeSlider=True)
            self.addPlotWidgetToMDI(plotWidget)
            # Update/Overwrite plot
            QVizPlotSignal(dataTreeView=dataTreeView,
                           vizTreeNode=treeNode).execute(plotWidget=plotWidget,
                                                         figureKey=currentFigureKey,
                                                         update=update,
                                                         dataset_to_update=dataset_to_update)
        except ValueError as e:
            logging.error(str(e))

    def getMDI(self):
        if self.parent != None:
            return self.parent
        return None
