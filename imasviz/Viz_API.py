#  Name   : Viz_API
#
#          IMASViz Application Programming Interface.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
# *****************************************************************************
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
# *****************************************************************************

import os
import logging
import sys
import numpy as np

from imasviz.VizUtils import (QVizGlobalOperations, FigureTypes,
                              QVizGlobalValues, QVizPreferences)

from PySide6.QtWidgets import QMdiSubWindow


def getNodePath(node):
    # print("getNodePath=", node.getPath())
    return node.getParametrizedDataPath()


class Viz_API:

    def __init__(self, parent=None):

        self.parent = parent

        self.figToNodes = {}  # key = figure, values = list of selected nodes
        # figureframes contains all plotting frames
        self.figureframes = {}  # key = FigureType + FigureKey,
        # example: FigureType="Figure:", FigureKey="1"
        self.DTVframeList = []
        self.DTVlist = []

        QVizPreferences().build()

    def GetDTVFrames(self):
        """Returns the list of shot views frames currently opened.
        There is only one frame for a given shot.
        """
        return self.DTVframeList

    def GetDataSources(self):
        """Returns the list of data sources currently opened.
        The data source is associated to one shot.

        :returns: A list of data sources (QVizIMASDataSource objects)
        """
        dataSourcesList = []
        for dtv in self.DTVlist:
            dataSourcesList.append(dtv.dataSource)
        return dataSourcesList

    def isDataSourceAlreadyOpened(self, dataSource):
        """Returns True if this data source has been already created.

        :param dataSource: a QVizIMASDataSource object
        :returns: True or False
        """
        dataSourcesList = self.GetDataSources()
        for ds in dataSourcesList:
            if dataSource.getKey() == ds.getKey():
                return True
        return False

    def GetDTVFor(self, dataSourceKey):
        """Returns the shot view frame for the given data source key.

        :param dataSourceKey: (str) The key of a data source (returned by
                                    QVizIMASDataSource.dataKey())
        :returns: a QVizDataTreeViewFrame object
        """
        for dtv in self.DTVlist:
            if dataSourceKey == dtv.dataSource.getKey():
                return dtv
        return None

    def RemoveDTVFrame(self, frame):
        """Removes the shot view frame from the list of opened frames
        :param frame: a QVizDataTreeViewFrame object
        """
        self.DTVframeList.remove(frame)
        self.DTVlist.remove(frame.dataTreeView)

    def AddNodeToFigure(self, figureKey, key, tup):
        """Adds an entry to the figToNodes[figureKey] dictionary.

        :param figureKey: (str) figure key
        :param key: (str)    dtv.dataSource.dataKey(vizTreeNode)
        :param tup: (tuple) (dtv.dataSource.uri, vizTreeNode)
        """
        if figureKey not in self.figToNodes:
            self.figToNodes[figureKey] = {}
        dic = self.figToNodes[figureKey]
        dic[key] = tup

    def GetPlotConfigurationPath(self, configurationName):
        """Get the path to plot configuration file (.pcfg extension).
        """
        return os.environ['HOME'] + "/.imasviz/" + configurationName + ".pcfg"

    def CreateDataTree(self, dataSource):
        """Returns the shot view frame for the specified data source.

        :param dataSource: A QVizIMASDataSource object
        :returns:          A QVizDataTreeViewFrame object
        """
        from imasviz.VizGUI.VizTreeView import QVizDataTreeViewFrame
        if QVizGlobalValues.TESTING:
            IMAS_VERSION = QVizGlobalValues.TESTING_IMAS_VERSION
        else:
            IMAS_VERSION = os.environ['IMAS_VERSION']

        frame = QVizDataTreeViewFrame(parent=None,
                                      views={},
                                      dataSource=dataSource,
                                      IDSDefFile=QVizGlobalOperations.getIDSDefFile(IMAS_VERSION),
                                      imas_viz_api=self)

        #frame.dataTreeView.dataSource = dataSource  # update the dataSource
        # attached to the view

        # Add created data tree view (DTV) frame to a list of DTV frames
        self.DTVframeList.append(frame)

        # Add current data tree view (DTV) frame to a list of DTVs
        self.DTVlist.append(frame.dataTreeView)

        return frame

    def ShowDataTree(self, dataTreeView):
        """Displays the specified data tree frame.
        NOTE: a QVizDataTreeView accepts QVizDataTreeViewFrame as a parent
              object.

        :param dataTreeView: (obj) A QVizDataTreeView or a
                                   QVizDataTreeViewFrame object
        """
        from imasviz.VizGUI.VizTreeView import QVizDataTreeView, QVizDataTreeViewFrame
        if isinstance(dataTreeView, QVizDataTreeViewFrame):

            # If MDI is present, add the DTV to it as a subwindow
            if self.getMDI() is not None:
                subWindow = QMdiSubWindow()
                subWindow.setWidget(dataTreeView)

                self.getMDI().addSubWindow(subWindow)
            dataTreeView.show()
        elif isinstance(dataTreeView, QVizDataTreeView):
            dataTreeView.parent.show()
        else:
            raise ValueError('Wrong argument type arg for ShowDataTree(arg).')

    def ShowNodesSelection(self, DTV):
        """Displays a window showing a list of all selected nodes from the
        dataTreeView object.
        NOTE: a QVizDataTreeView accepts QVizDataTreeViewFrame as a parent
              object.

        :param DTV (obj): A QVizDataTreeView or a QVizDataTreeViewFrame object
        """
        from imasviz.VizGUI.VizTreeView import QVizDataTreeViewFrame
        from imasviz.VizGUI.VizWidgets import QVizNodesSelectionWindow
        dataTreeView = DTV
        if isinstance(DTV, QVizDataTreeViewFrame):
            dataTreeView = DTV.dataTreeView
        self.nsw = QVizNodesSelectionWindow(dataTreeView)
        self.nsw.show()

    def GetSelectedNodes(self, DTV):
        """Returns the list of nodes selected by GUI or script commands.

        :param DTV: A QVizDataTreeViewFrame or QVizDataTreeView object
        :returns: (list) A list of QVizTreeNode objects.
        """
        from imasviz.VizGUI.VizTreeView import QVizDataTreeViewFrame
        dataTreeView = DTV
        if isinstance(DTV, QVizDataTreeViewFrame):
            dataTreeView = DTV.dataTreeView
        selectedNodes = []
        for key in dataTreeView.selectedSignalsDict:
            v = dataTreeView.selectedSignalsDict[key]
            vizTreeNode = v['QTreeWidgetItem']
            selectedNodes.append(vizTreeNode)
        return selectedNodes

    def GetSelectedSignalsDict(self, DTV):
        """Returns the list of signals (nodes) dictionaries selected by GUI or
        script commands.

        :param DTV: A QVizDataTreeViewFrame or QVizDataTreeView object
        :returns: (list) A list of signals (nodes) dictionaries.
        """
        from imasviz.VizGUI.VizTreeView import QVizDataTreeViewFrame
        dataTreeView = DTV
        if isinstance(DTV, QVizDataTreeViewFrame):
            dataTreeView = DTV.dataTreeView
        return dataTreeView.selectedSignalsDict

    def GetSelectedSignalsDictFromAllDTVs(self):
        """Returns the list of signals (nodes) dictionaries selected by GUI or
        script commands from all opened shot views (DTVs).

        :returns: (list) A list of signals (nodes) dictionaries
        """
        allSelectedSignals = {}
        for i in range(len(self.DTVframeList)):
            allSelectedSignals.update(
                self.DTVframeList[i].dataTreeView.selectedSignalsDict)

        return allSelectedSignals

    def ShowHideFigure(self, figureKey):
        """Shows/Hides a figure.

        :param figureKey: (str) A figure key (e.g. 'Figure:0)
        """
        frame = self.figureframes[figureKey]
        if frame.window().objectName() == "IMASViz root window":
            # Hide/Show MDI subwindow
            if frame.parent().isVisible():
                frame.parent().hide()  # frame.parent() is QMdiSubWindow
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
        """Returns the next figure number available for plotting.

        :returns: (int) The number of the next figure
        """
        return len(self.GetFiguresKeys())

    def GetImagePlotsCount(self):
        """Returns the next number of image plots.

        :returns: (int) The next number of image plots
        """
        return len(self.GetFiguresKeys(FigureTypes.IMAGETYPE))

    def GetTablePlotViewsCount(self):
        """Returns the next table plot number available for plotting.

        :returns: (int) The number of the next table plot
        """
        return len(self.GetFiguresKeys(FigureTypes.TABLEPLOTTYPE))

    def GetStackedPlotViewsCount(self):
        """Returns the next table plot number available for plotting.

        :returns: (int) The number of the next table plot
        """
        return len(self.GetFiguresKeys(FigureTypes.STACKEDPLOTTYPE))

    def GetProfilesPlotViewsCount(self):
        """Returns the next plots table number available.

        :returns: (int) The number of the next plots table
        """
        return len(self.GetFiguresKeys(FigureTypes.PROFILESPLOTTYPE))

    def GetNextKeyForTablePlotView(self):
        """Returns the key of the next table plot (e.g. if 'TablePlot i' is the
        latest table plot on the list of existing table plots, value
        'TablePlot i+1' is returned).

        :returns: (str) The key of the next table plot
        """
        return FigureTypes.TABLEPLOTTYPE + str(self.GetTablePlotViewsCount())

    def GetNextKeyForFigurePlots(self):
        """Returns the key of the next figure plot (e.g. if 'Figure i' is the
        latest figure on the list of existing figures, value 'Figure i+1' is
        returned).

        :returns: (str) The key of the next figure (plot)
        """
        return FigureTypes.FIGURETYPE + str(self.GetFigurePlotsCount())

    def GetNextKeyForImagePlots(self):
        """Returns the key of the next 2D plot (e.g. if 'Image i' is the
        latest image on the list of existing 2D plots, value 'Image i+1' is
        returned).

        :returns: (str) The key of the next 2D plot
        """
        return FigureTypes.IMAGETYPE + str(self.GetImagePlotsCount())

    def GetNextKeyForStackedPlotView(self):
        """Returns the key of the next stacked plot (e.g. if 'StackedPlot i'
        is the latest stacked plot on the list of existing stacked plots,
        value 'StackedPlot i+1' is returned).

        :returns: (str) The key of the next stacked plot
        """
        return FigureTypes.STACKEDPLOTTYPE + str(self.GetStackedPlotViewsCount())

    def GetNextKeyForProfilesPlotView(self):
        """Returns the key of the next table of profiles plot
        :returns: (str) The key of the next plots table
        """
        return FigureTypes.PROFILESPLOTTYPE + str(self.GetProfilesPlotViewsCount())

    def GetFiguresKeys(self, figureType=FigureTypes.FIGURETYPE):
        """Returns the list of all figure keys.

        :returns: (list) A list of figure keys
        """
        figureKeys = []
        for key in self.figureframes.keys():
            if key.startswith(figureType):
                figureKeys.append(key)
        return sorted(figureKeys)

    def DeleteFigure(self, figureKey):
        """Deletes the specified figure.

        :param figureKey: A figure key (e.g. 'Figure:0)
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
        """Get the figure key.

        :param userKey: (str) figure number
        :param figureType: FigureTypes.FIGURETYPE
        :returns: (str) a figure key
        """
        return figureType + userKey

    def getFigureKeyNum(self, figureKey, figureType):
        """Extract figure number from a figure key (e.g. 'Figure:0' -> 0).

        :param figureKey: A figure key (e.g. 'Figure:0')
        :param figureType: FigureTypes.FIGURETYPE or
                           FigureTypes.STACKEDPLOTTYPE or
                           FigureTypes.TABLEPLOTTYPE
        :returns: (str) a figure key
        """
        numFig = int(figureKey[len(figureType):])
        return numFig

    # def getFigureFrame(self, figureKey):
    #     if figureKey in self.figureframes:
    #         return self.figureframes[figureKey]
    #     else:
    #         print("No frame found with key: " + str(figureKey))

    def PlotSelectedSignals(self, dataTreeFrame, figureKey=None, update=0,
                            all_DTV=False, plotAxis="TIME"):
        """Plots the current selected set of signals on a figure.

        :param plotAxis:
        :param dataTreeFrame: A QVizDataTreeViewFrame object
        :param plotWidget: A plot widget
        :param figureKey: A figure key. If None, a new figure is created.
        :param update: if 1, the current plot is updated otherwise a new plot
                       is created
        :param all_DTV: if True, all current selected set of signals on all
                        shot views are plotted
        """
        # if figureKey is None:
        #     figureKey = self.GetNextKeyForFigurePlots()
        from imasviz.VizGUI.VizGUICommands.VizPlotting import QVizPlotSelectedSignals
        QVizPlotSelectedSignals(dataTreeView=dataTreeFrame.dataTreeView,
                                figureKey=figureKey,
                                update=update,
                                all_DTV=all_DTV,
                                plotAxis=plotAxis).execute()

    def PlotSelectedSignalsInTablePlotViewFrame(self, dataTreeFrame,
                                                all_DTV=False,
                                                plotAxis='TIME'):
        """Plots the current selected set of signals of this shot view on a
           new table plot.

        :param plotAxis:
        :param dataTreeFrame: A QVizDataTreeViewFrame object
        :param all_DTV:       When True, all current selected set of signals
                              on all shot views are plotted
        """
        from imasviz.VizGUI.VizGUICommands.VizMenusManagement import QVizSignalHandling
        QVizSignalHandling(dataTreeFrame.dataTreeView). \
            onPlotToTablePlotView(all_DTV, plotAxis=plotAxis)

    # Plot the set of signals selected by the user
    def ApplyTablePlotViewConfiguration(self, dataTreeFrame, configFilePath,
                                        all_DTV=False, plotAxis='TIME'):
        """Selects a set of signals using the selection file and plots of this
        shot view on a new table plot.

        :param plotAxis:
        :param dataTreeFrame:  A QVizDataTreeViewFrame object
        :param configFilePath: The path to a data selection file
        :param all_DTV: When True, all current selected set of signals on all
                        shot views are plotted
        """
        from imasviz.VizGUI.VizGUICommands.VizMenusManagement import QVizSignalHandling
        QVizSignalHandling(dataTreeFrame.dataTreeView).onPlotToTablePlotView(
            all_DTV=all_DTV,
            configFile=configFilePath,
            plotAxis=plotAxis)

    def LoadMultipleIDSData(self, dataTreeFrame, IDSNamesList, occurrence=0,
                            threadingEvent=None):
        """Load multiple IDSs data for a given data tree frame and a given
        occurrence.

        :param dataTreeFrame: A QVizDataTreeViewFrame object
        :param IDSNamesList: List of the names of the IDSs
        :param occurrence: (int) Occurrence to be loaded (will be the same
                                 for all IDSs)
        :param threadingEvent: When True, data are loaded from a new Thread
        """
        for IDSName in IDSNamesList:
            self.LoadIDSData(dataTreeFrame, IDSName, occurrence,
                             threadingEvent)

    def LoadIDSData(self, dataTreeFrame, IDSName, occurrence=0,
                    threadingEvent=None):
        """Load IDS data for a given data tree frame and a given occurrence.

        :param dataTreeFrame: A QVizDataTreeViewFrame object
        :param IDSName: The name of the IDS
        :param occurrence: (int) Occurrence of the IDS
        :param threadingEvent: If True, data are loaded from a new Thread
        """
        from imasviz.VizGUI.VizTreeView import QVizDataTreeViewFrame
        from imasviz.VizGUI.VizGUICommands import QVizLoadSelectedData
        if isinstance(dataTreeFrame, QVizDataTreeViewFrame):
            QVizLoadSelectedData(dataTreeView=dataTreeFrame.dataTreeView, IDSName=IDSName,
                                 occurrence=occurrence, viewLoadingStrategy=None, asynch=threadingEvent).execute()
        else:
            QVizLoadSelectedData(dataTreeView=dataTreeFrame, IDSName=IDSName,
                                 occurrence=occurrence, viewLoadingStrategy=None, asynch=threadingEvent).execute()

    def SelectSignals(self, DTV, pathsMap):
        """Select signals nodes from a list of IMAS paths for the given shot
           view.

        :param DTV: a QVizDataTreeViewFrame object
        :param pathsMap: (dict) pathsMap['paths'] : a list of signal paths (e.g.
                                           ['magnetics/flux_loop(0)/flux/data'])
                                           pathsMap['occurrences'] : a list of occurrences
        """
        from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignals import QVizSelectSignals
        QVizSelectSignals(DTV.dataTreeView, pathsMap).execute()

    def PlotSelectedSignalsFrom(self, dataTreeFramesList, figureKey=None,
                                all_DTV=False):
        """Plots current selected signal.

        :param dataTreeFramesList:  A list of DTV frames
        :param figureKey: A figure key. If None, a new figure is created.
        :param all_DTV: When True, all current selected set of signals on all
                        shot views are plotted
        """
        from imasviz.VizGUI.VizGUICommands.VizPlotting import QVizPlotSelectedSignals
        i = 0
        update = 0
        for f in dataTreeFramesList:
            if i != 0:
                update = 1
            QVizPlotSelectedSignals(dataTreeView=f.dataTreeView,
                                    figureKey=figureKey,
                                    update=update,
                                    all_DTV=all_DTV).execute()
            i += 1

    def UnSelectAllSignals(self, dataTreeFrame, all_DTV=False):
        """Unselects all previously selected signals for the given shot view.

        :param dataTreeFrame: A QVizDataTreeViewFrame object
        :param all_DTV: When True, all selected signals from all shot views are
                        unselected
        """
        from imasviz.VizGUI.VizGUICommands import QVizUnselectAllSignals
        QVizUnselectAllSignals(dataTreeFrame.dataTreeView, all_DTV=all_DTV).execute()

    def SelectSignalsGroup(self, dataTreeFrame, occurrence, onePathInTheGroup):
        """Selects nodes for this shot view.

        :param dataTreeFrame: A QVizDataTreeViewFrame object
        :param occurrence: the occurrence of an IDS
        :param onePathInTheGroup: An IDS path to one of the node
                                      (signals), containing a data array
                                      (e.g. FLT_1D), of which all siblings
                                      in the AOS are to be selected.
                                      Example:
                                      'magnetics/flux_loop(0)/flux/data'
        """
        from imasviz.VizGUI.VizGUICommands import QVizSelectSignalsGroup
        QVizSelectSignalsGroup(dataTreeFrame.dataTreeView,
                               dataTreeFrame.dataTreeView.selectedItem).execute()

    def IDSDataAlreadyFetched(self, dataTreeView, IDSName, occurrence):
        key = IDSName + "/" + str(occurrence)
        if key in dataTreeView.ids_roots_occurrence:
            return True
        else:
            return False

    def GetNextOccurrenceUnloadedWithAvailableData(self, dataTreeView, node):
        import imas
        maxOccurrences = eval("imas." + node.getIDSName() + "().getMaxOccurrences()")
        for i in range(0, maxOccurrences):
            if not self.IDSDataAlreadyFetched(dataTreeView, node.getIDSName(), i):
                if node.hasIDSAvailableData(i):
                    return i
        return None

    def GetAllOccurrencesWithAvailableData(self, node):
        import imas
        maxOccurrences = eval("imas." + node.getIDSName() + "().getMaxOccurrences()")
        availableOccurrences = []
        for i in range(0, maxOccurrences):
            if node.hasIDSAvailableData(i):
                availableOccurrences.append(i)
        return availableOccurrences

    def GetAllOccurrencesUnloadedWithAvailableData(self, dataTreeView, node):
        import imas
        maxOccurrences = eval("imas." + node.getIDSName() + "().getMaxOccurrences()")
        availableOccurrences = []
        for i in range(0, maxOccurrences):
            if node.hasIDSAvailableData(i) and \
                    not self.IDSDataAlreadyFetched(dataTreeView,
                                                   node.getIDSName(), i):
                availableOccurrences.append(i)
        return availableOccurrences

    def GetDataSource(self, dataTreeFrame):
        from imasviz.VizGUI.VizTreeView import QVizDataTreeViewFrame
        if isinstance(dataTreeFrame, QVizDataTreeViewFrame):
            return dataTreeFrame.parent.dataSource
        else:
            return dataTreeFrame.dataSource

    def GetIDSInstance(self, dataTreeFrame, occurrence):
        from imasviz.VizGUI.VizTreeView import QVizDataTreeViewFrame
        if isinstance(dataTreeFrame, QVizDataTreeViewFrame):
            return self.GetDataSource(dataTreeFrame.parent).data_entries[occurrence]
        else:
            return self.GetDataSource(dataTreeFrame).data_entries[occurrence]

    def CreatePlotWidget(self, dataTreeView, plotAxis="DEFAULT", treeNode=None):

        from imasviz.VizGUI.VizPlot import QVizPlotWidget

        figureKey = self.GetNextKeyForFigurePlots()

        addTimeSlider = False
        addCoordinateSlider = False
        logging.debug('Creation of a plot widget')
        if plotAxis == "COORDINATE1":
            logging.debug('Creation of a plot widget with addTimeSlider = True')
            addTimeSlider = True
            addCoordinateSlider = False
            
        elif plotAxis == "TIME":
            logging.debug('Creation of a plot widget with addTimeSlider = False')
            addTimeSlider = False
            addCoordinateSlider = True

        plotWidget = QVizPlotWidget(size=(600, 550),
                                    title=figureKey,
                                    dataTreeView=dataTreeView,
                                    addTimeSlider=addTimeSlider,
                                    addCoordinateSlider=addCoordinateSlider)
        #if treeNode is not None and addTimeSlider:
        #    plotWidget.sliderGroup.slider.setValue(int(treeNode.timeValue()))
        
        plotWidget.setPlotAxis(plotAxis)
        self.figureframes[figureKey] = plotWidget
        return figureKey, plotWidget

    def GetPlotWidget(self, dataTreeView, figureKey=0, plotAxis="DEFAULT", treeNode=None):
        if figureKey in self.figureframes:
            plotWidget = self.figureframes[figureKey]
        else:
            figureKey, plotWidget = self.CreatePlotWidget(dataTreeView=dataTreeView,
                                                          plotAxis=plotAxis, treeNode=treeNode)
        return figureKey, plotWidget

    def GetSignal(self, dataTreeView, vizTreeNode, as_function_of_time=None,
                  coordinate1_index=0, time_index=None, plotWidget=None):
        from imasviz.VizDataAccess.QVizDataAccessFactory import QVizDataAccessFactory
        try:
            signalDataAccess = QVizDataAccessFactory(dataTreeView.dataSource).create()
            return signalDataAccess.GetSignal(treeNode=vizTreeNode,
                                              plotWidget=plotWidget,
                                              as_function_of_time=as_function_of_time,
                                              coordinate_index=coordinate1_index,
                                              time_index=time_index)
        except:
            raise

    def Plot2DArray(self, dataTreeView, vizTreeNode):
        from imasviz.VizGUI.VizPlot.VizPlotFrames.QvizPlotImageWidget import QvizPlotImageWidget
        imageKey = self.GetNextKeyForImagePlots()
        plotWidget = QvizPlotImageWidget(vizTreeNode=vizTreeNode,
                                         size=(600, 500), plotSliceFromROI=True, title=imageKey, showImageTitle=False)
        self.figureframes[imageKey] = plotWidget
        self.addPlotWidgetToMDI(plotWidget)
        dataArrayHandle = self.GetSignal(dataTreeView, vizTreeNode, plotWidget=None)
        plotWidget.plot(dataArrayHandle)
        plotWidget.show()

    def AddPlot1DToFig(self, numFig, vizTreeNode):
        """Add signal plot to existing figure.

        Arguments:
            numFig (int) : Number identification of the existing figure.
        """
        from imasviz.VizGUI.VizGUICommands.VizPlotting import QVizPlotSignal

        try:

            label = None
            title = None

            # Get figure key (e.g. 'Figure:0' string)
            figureKey = self.GetFigureKey(str(numFig), figureType=FigureTypes.FIGURETYPE)
            # Get widget linked to this figure
            figureKey, plotWidget = self.GetPlotWidget(dataTreeView=vizTreeNode.dataTreeView,
                                                       figureKey=figureKey)

            QVizPlotSignal(dataTreeView=vizTreeNode.dataTreeView,
                           label=label,
                           title=title,
                           vizTreeNode=vizTreeNode,
                           plotWidget=plotWidget).execute(figureKey=figureKey,
                                                          update=0)
        except ValueError as e:
            logging.getLogger(vizTreeNode.dataTreeView.uri).error(str(e))

    def nodeDataShareSameCoordinates(self, figureKey, vizTreeNode):
        figureDataList = self.figToNodes.get(figureKey)
        if figureDataList is None:
            return False
        figureNodesList = []
        for k in figureDataList:
            v = figureDataList[k]
            figureNodesList.append(v[1])  # v[0] = shot number, v[1] = vizNode
        return self.nodeDataShareSameCoordinatesAs(figureNodesList, vizTreeNode, figureKey)

    def nodeDataShareSameCoordinatesAs(self, selectedNodeList, vizTreeNode,
                                       figureKey=None):
        """Check if data already in figure and next to be added signal plot
        share the same coordinates and other conditions for a meaningful plot.
        """
        return vizTreeNode.nodeDataShareSameCoordinatesAs(selectedNodeList, figureKey)

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
        from imasviz.VizGUI.VizGUICommands.VizPlotting import QVizPlotSignal
        try:
            treeNode = dataTreeView.selectedItem
            # Get signal node index
            index = treeNode.infoDict['i']
            # Get label and title
            label, title, dummy = \
                treeNode.coordinateLabels(coordinateNumber=1, dtv=dataTreeView,
                                          index=index)
            figureKey, plotWidget = self.GetPlotWidget(dataTreeView=dataTreeView,
                                                       figureKey=None,
                                                       plotAxis='TIME')
            self.addPlotWidgetToMDI(plotWidget)
            p = QVizPlotSignal(dataTreeView=dataTreeView,
                               vizTreeNode=treeNode,
                               title=title,
                               label=label,
                               xlabel="time",
                               plotWidget=plotWidget)
            p.execute(figureKey=figureKey, update=0)
        except ValueError as e:
            logging.getLogger(dataTreeView.uri).error(str(e))

    def plot0D_DataVsTimeCommand(self, dataTreeView, treeNode=None):
        """Plotting of 0D data nodes, found within timed AOS
        """
        from imasviz.VizGUI.VizGUICommands.VizPlotting import QVizPlotSignal
        try:
            # Get currently selected QVizTreeNode (QTreeWidgetItem)
            if treeNode is None:
                treeNode = dataTreeView.selectedItem
            figureKey, plotWidget = self.GetPlotWidget(dataTreeView=dataTreeView,
                                                       figureKey=None,
                                                       plotAxis='TIME')  # None will force a new Figure
            self.addPlotWidgetToMDI(plotWidget)
            p = QVizPlotSignal(dataTreeView=dataTreeView,
                               vizTreeNode=treeNode,
                               xlabel="time",
                               plotWidget=plotWidget)
            p.execute(figureKey=figureKey, update=0)
        except ValueError as e:
            logging.getLogger(dataTreeView.uri).error(str(e))

    def plotVsTimeAtGivenCoordinate1(self, dataTreeView, coordinateIndex,
                                     currentFigureKey, treeNode, update,
                                     dataset_to_update=0):
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
                                      replace the current plot in figure
                                      window.
        """
        from imasviz.VizGUI.VizGUICommands.VizPlotting import QVizPlotSignal
        try:

            # Get label, title and xlabel
            if treeNode.is1DAndDynamic():
                label, title, xlabel = treeNode.coordinateLabels(
                    coordinateNumber=1, dtv=dataTreeView,
                    index=coordinateIndex)

            elif treeNode.is0DAndDynamic():
                # logging.warning(
                #     "Data node '" + treeNode.getName() +
                #     "' has no explicit dependency on coordinate1 dimension.")
                self.plot0D_DataVsTimeCommand(dataTreeView, treeNode=treeNode)
                return

            else:
                logging.getLogger(treeNode.dataTreeView.uri).error("plotVsTimeAtGivenCoordinate1() supports only nodes with dimension <= 1D.")
                return

            currentFigureKey, plotWidget = \
                self.GetPlotWidget(dataTreeView=dataTreeView,
                                   figureKey=currentFigureKey,
                                   plotAxis='TIME',
                                   treeNode=treeNode)

            # Add plot window to subwindow and to MDI only if the plotWidget
            # with the given figurekey does not exist yet
            if currentFigureKey not in self.figureframes:
                self.addPlotWidgetToMDI(plotWidget)

            # Update/Overwrite plot
            QVizPlotSignal(dataTreeView=dataTreeView,
                           title=title,
                           label=label,
                           xlabel="time",
                           vizTreeNode=treeNode,
                           plotWidget=plotWidget).execute(figureKey=currentFigureKey,
                                                          update=update,
                                                          dataset_to_update=dataset_to_update)
        except ValueError as e:
            logging.getLogger(treeNode.dataTreeView.uri).error(str(e))

    def plotVsCoordinate1AtGivenTime(self, dataTreeView, currentFigureKey,
                                     treeNode, update, dataset_to_update=0):
        """Overwrite/Update the existing plot (done with
        'plotSignalCommand' routine and currently still shown in
        the plot window labeled as 'currentFigureKey') but for different time
        slice. The node must be of the same structure (sibling to the node used
        for the previous plot and both are located within the 'time_slice[:]'
        structure').

        Arguments:
            currentFigureKey  (str) : Label of the current/relevant figure
                                      window.
            treeNode (QVizTreeNode) : QTreeWidgetItem holding node data to
                                      replace the current plot in figure window.
        """
        from imasviz.VizGUI.VizGUICommands.VizPlotting import QVizPlotSignal
        try:
            currentFigureKey, plotWidget = \
                self.GetPlotWidget(dataTreeView=dataTreeView,
                                   figureKey=currentFigureKey,
                                   plotAxis='COORDINATE1',
                                   treeNode=treeNode)
            # Add plot window to subwindow and to MDI only if the plotWidget
            # with the given figurekey does not exist yet
            if currentFigureKey not in self.figureframes:
                self.addPlotWidgetToMDI(plotWidget)
            # Update/Overwrite plot
            QVizPlotSignal(dataTreeView=dataTreeView,
                           vizTreeNode=treeNode,
                           plotWidget=plotWidget).execute(figureKey=currentFigureKey,
                                                          update=update,
                                                          dataset_to_update=dataset_to_update)
        except ValueError as e:
            logging.getLogger(dataTreeView.uri)(str(e))

    def getMDI(self):
        if self.parent is not None:
            return self.parent
        return None

    def addPlotWidgetToMDI(self, plotWidget):
        """Embeds the plotWidget inside MDI subwindow.
        """
        from PySide6.QtWidgets import QMdiSubWindow

        subWindow = QMdiSubWindow()
        subWindow.setWidget(plotWidget)
        subWindow.resize(plotWidget.width(), plotWidget.height())
        if self.getMDI() is not None:
            self.getMDI().addSubWindow(subWindow)
        else:
            self.subWindow = subWindow

    def LoadListOfIDSs(self, dataTreeView, namesOfIDSs, occurrence=0):
        """Load given IDSs for given occurrence.

        Arguments:
            dataTreeView (obj)   : Instance of DTV.
            namesOfIDSs  (list)  : List of IDS names (strings)
            occurrence   (int)   : IDS occurrence
        """

        for idsName in namesOfIDSs:
            if not self.IDSDataAlreadyFetched(dataTreeView=dataTreeView,
                                              IDSName=idsName,
                                              occurrence=occurrence):
                self.LoadIDSData(dataTreeView, idsName, occurrence)

    def getAll_0D_1D_Nodes(self, node, errorBars=False, str_filter=None, plotAxis=None):
        children_id, children = self.getChildren_(node, set(), [], str_filter, errorBars, plotAxis)
        children.sort(key=getNodePath)
        return children_id, children

    def getChildren_(self, item, children_id, children, str_filter, errorBars, plotAxis):
        criteria = plotAxis == 'TIME'
        for row in range(item.childCount()):
            child_item = item.child(row)
            # print("--------------> checking :", child_item.getPath(), " plotAxis=", plotAxis)
            if not child_item.isStructure() and not child_item.isArrayOfStructure() and \
                    child_item.isDynamicData() and (child_item.is1D() or criteria * child_item.is0D()) and \
                    child_item.hasAvailableData():

                if not errorBars and "_error_" not in child_item.getPath():
                    if str_filter is None or (str_filter is not None and str_filter
                                              in child_item.getPath()):
                        if not id(child_item) in children_id:
                            # print("--------------> adding :", item.getPath())
                            children_id.add(id(child_item))
                            children.append(child_item)
            elif child_item.isIDSRoot() or child_item.isStructure() or child_item.isArrayOfStructure():
                children_id, children = self.getChildren_(child_item, children_id,
                                                          children, str_filter, errorBars, plotAxis)
        return children_id, children

    def find_nearest(self, array, value):
        array = np.asarray(array)
        idx = (np.abs(array - value)).argmin()
        return array[idx], idx

    def getAllPlottable_0D_1D_Signals(self, dtv_nodes, dataTreeView, plotWidget=None,
                                      profile_center=True):
        s_list = []
        for node in dtv_nodes:
            try:
                coordinate1_index = 0
                closest_value = 0
                if node.is1D() and plotWidget.plotAxis == 'TIME' and profile_center:
                    coordinate1_values = node.coordinateValues(coordinateNumber=1, dataTreeView=node.dataTreeView)
                    # print(node.getParametrizedDataPath() + '=', len(coordinate1_values))
                    # closest_value, coordinate1_index = self.find_nearest(coordinate1_values,
                    #                                                      np.max(coordinate1_values) / 2)
                    coordinate1_index = int(coordinate1_values.size / 2)
                    # closest_value, coordinate1_index = coordinate1_values[int(coordinate1_values.size)]
                    closest_value = coordinate1_values[coordinate1_index]

                s = self.GetSignal(dataTreeView=dataTreeView,
                                   vizTreeNode=node,
                                   coordinate1_index=coordinate1_index,
                                   plotWidget=plotWidget)
                s_list.append((node, s, closest_value))
            except Exception as e:
                print(e)
                continue
        return s_list

    def updateAllPlottable_0D_1D_Signals(self, s_list, time_index, plotWidget=None, profile_center=True):
        s_new_list = []
        for s in s_list:
            try:
                node = s[0]
                coordinate1_index = 0
                #closest_value = 0
                if node.is1D() and plotWidget.plotAxis == 'TIME' and profile_center:
                    coordinate1_values = node.coordinateValues(coordinateNumber=1, dataTreeView=node.dataTreeView)
                    # print(node.getParametrizedDataPath() + '=', len(coordinate1_values))
                    coordinate1_index = int(coordinate1_values.size / 2)
                    # closest_value, coordinate1_index = coordinate1_values[int(coordinate1_values.size)]
                    closest_value = coordinate1_values[coordinate1_index]
                snew = self.GetSignal(dataTreeView=node.dataTreeView,
                                      vizTreeNode=node,
                                      time_index=time_index,
                                      coordinate1_index=coordinate1_index,
                                      plotWidget=plotWidget)
                s_new_list.append((node, snew, coordinate1_index))
            except Exception as e:
                print(e)
                continue
        return s_new_list

    def modifyTitle(self, title, ids_name, slices_aos_name):
        if ids_name is not None:
            index = title.find(ids_name)
            if index == -1:
                return title
            return title[index:]
        elif slices_aos_name is not None:
            if 'itime' in title:
                title = title.replace("itime", ":")
            slices_aos_name = QVizGlobalOperations.makeIMASPath(slices_aos_name)
            index = title.find(slices_aos_name)
            if index == -1:
                return title
            return title[index + len(slices_aos_name) + 4:]

    def plot1DInNewFigure(self, x_label, signals_labels, signals, treeNode):
        """Plot data in a new figure
        Arguments:
            figureKey  (str) : Label of the current/relevant figure window.
            treeNode (QVizTreeNode) : QTreeWidgetItem holding node data to
                                      replace the current plot in figure
                                      window.
                                      :param signals_labels:
                                      :param signals: List of tuple (x,y) where x and y are 1D numpy arrays
                                      :param x_label:
                                      :param treeNode:
        """
        from imasviz.VizGUI.VizGUICommands.VizPlotting import QVizPlotSignal
        try:
            figureKey, plotWidget = self.CreatePlotWidget(dataTreeView=treeNode.dataTreeView)
            i = 0
            for sig in signals:
                QVizPlotSignal(dataTreeView=treeNode.dataTreeView,
                               title='',
                               label=signals_labels[i],
                               xlabel=x_label,
                               vizTreeNode=treeNode,
                               plotWidget=plotWidget).execute(figureKey=figureKey, signal=sig)
                i += 1
        except ValueError as e:
            logging.getLogger(dataTreeView.uri).error(str(e))
