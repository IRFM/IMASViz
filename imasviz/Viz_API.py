# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

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


class QVizMdiSubWindow(QMdiSubWindow):
    """The MDI window a figure frame is embedded in.

    The window is what the user closes to get rid of a figure when no command is
    involved, so it is what tells the api the key is free again. PySide6 6.6 does
    not expose QMdiSubWindow.aboutToClose, hence the close event.
    """

    def __init__(self, imas_viz_api):
        super(QVizMdiSubWindow, self).__init__()
        self.imas_viz_api = imas_viz_api

    def closeEvent(self, event):
        super(QVizMdiSubWindow, self).closeEvent(event)
        self.imas_viz_api.ForgetFigureOf(self.widget())


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
        # The frame was the last one displaying this case: let go of the IDSs
        # that were loaded for it, as the per-source cache used to go away with
        # the source it owned.
        frame.dataTreeView.dataSource.forget_case()

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

    def GetFiguresCount(self, figureType=FigureTypes.FIGURETYPE):
        """How many figures of one kind are open.

        :param figureType: (str) a FigureTypes prefix
        :returns: (int)
        """
        return len(self.GetFiguresKeys(figureType))

    def GetFigurePlotsCount(self):
        """Returns the next figure number available for plotting.

        :returns: (int) The number of the next figure
        """
        return self.GetFiguresCount()

    def GetTablePlotViewsCount(self):
        """Returns the next table plot number available for plotting.

        :returns: (int) The number of the next table plot
        """
        return self.GetFiguresCount(FigureTypes.TABLEPLOTTYPE)

    def GetStackedPlotViewsCount(self):
        """Returns the next table plot number available for plotting.

        :returns: (int) The number of the next table plot
        """
        return self.GetFiguresCount(FigureTypes.STACKEDPLOTTYPE)

    def GetProfilesPlotViewsCount(self):
        """Returns the next plots table number available.

        :returns: (int) The number of the next plots table
        """
        return self.GetFiguresCount(FigureTypes.PROFILESPLOTTYPE)

    def GetNextKeyForFigure(self, figureType=FigureTypes.FIGURETYPE):
        """The key of the next figure of one kind: one past the highest number
        still in use.

        Counting the open figures instead -- what this did when every kind had
        its own accessor -- hands back a number that is already taken as soon as
        one of the lower figures was deleted. Two figures then share a key, and
        the key is how show/hide and delete address a figure: one of the two
        becomes unreachable.

        :param figureType: (str) a FigureTypes prefix
        :returns: (str) the key of the next figure of that kind
        """
        numbers = [self.getFigureKeyNum(key, figureType)
                   for key in self.GetFiguresKeys(figureType)]
        return figureType + str(max(numbers) + 1 if numbers else 1)

    def GetNextKeyForTablePlotView(self):
        """Returns the key of the next table plot (e.g. if 'TablePlot i' is the
        latest table plot on the list of existing table plots, value
        'TablePlot i+1' is returned).

        :returns: (str) The key of the next table plot
        """
        return self.GetNextKeyForFigure(FigureTypes.TABLEPLOTTYPE)

    def GetNextKeyForFigurePlots(self):
        """Returns the key of the next figure plot (e.g. if 'Figure i' is the
        latest figure on the list of existing figures, value 'Figure i+1' is
        returned).

        :returns: (str) The key of the next figure (plot)
        """
        return self.GetNextKeyForFigure(FigureTypes.FIGURETYPE)

    def GetNextKeyForStackedPlotView(self):
        """Returns the key of the next stacked plot (e.g. if 'StackedPlot i'
        is the latest stacked plot on the list of existing stacked plots,
        value 'StackedPlot i+1' is returned).

        :returns: (str) The key of the next stacked plot
        """
        return self.GetNextKeyForFigure(FigureTypes.STACKEDPLOTTYPE)

    def GetNextKeyForProfilesPlotView(self):
        """Returns the key of the next table of profiles plot
        :returns: (str) The key of the next plots table
        """
        return self.GetNextKeyForFigure(FigureTypes.PROFILESPLOTTYPE)

    def GetFiguresKeys(self, figureType=FigureTypes.FIGURETYPE):
        """Returns the list of all figure keys.

        :returns: (list) A list of figure keys
        """
        figureKeys = []
        for key in self.figureframes.keys():
            if key.startswith(figureType):
                figureKeys.append(key)
        return sorted(figureKeys)

    def ForgetFigure(self, figureKey):
        """Take a figure out of the bookkeeping, leaving its window alone.

        The window is already going away: this is what the user closing it does.
        A frame left registered stays in the show/hide and delete menus as a
        figure that is not there, and keeps a number the next figure of that kind
        is then not entitled to.

        :param figureKey: A figure key (e.g. 'Figure:1')
        """
        self.figureframes.pop(figureKey, None)
        self.figToNodes.pop(figureKey, None)

    def GetFigureKeyOf(self, frame):
        """The key a frame is registered under, or None if it is not registered.

        The kind of a figure is spelled in its key rather than carried on the
        frame, so a caller holding the widget and needing the key has to ask the
        registry.
        """
        for figureKey, registered in self.figureframes.items():
            if registered is frame:
                return figureKey
        return None

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
        self.ForgetFigure(figureKey)

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

        :param plotAxis: kept for call compatibility, and no longer selects
                         anything: the frame takes its abscissa from the axes the
                         read walks along each quantity, and carries a named
                         control for every axis it leaves out.
        :param dataTreeFrame: A QVizDataTreeViewFrame object
        :param figureKey: A figure key. If None, a new figure is created.
        :param update: kept for call compatibility: adding to the figure named by
                       figureKey is what the command does, and the figure to
                       create is what a None figureKey means.
        :param all_DTV: if True, all current selected set of signals on all
                        shot views are plotted
        """
        from imasviz.VizGUI.VizGUICommands.VizPlotting import QVizPlotAsSlices
        QVizPlotAsSlices(dataTreeView=dataTreeFrame.dataTreeView,
                         all_DTV=all_DTV,
                         intoFigureKey=figureKey).execute()

    def PlotSelectedSignalsInTablePlotViewFrame(self, dataTreeFrame,
                                                all_DTV=False,
                                                plotAxis='TIME'):
        """Plots the current selected set of signals of this shot view on a
           new table plot.

        :param plotAxis: 'TIME' reads every quantity along time; anything else
                         lets the read answer per quantity, which is what a
                         selection mixing coordinates needs -- each quantity then
                         gets a panel of its own with its own labels.
        :param dataTreeFrame: A QVizDataTreeViewFrame object
        :param all_DTV:       When True, all current selected set of signals
                              on all shot views are plotted
        """
        from imasviz.VizGUI.VizGUICommands.VizPlotting import QVizPlotAsTable
        frame = QVizPlotAsTable(dataTreeView=dataTreeFrame.dataTreeView,
                                all_DTV=all_DTV,
                                plotAxis=plotAxis).execute()
        if frame is not None:
            self.addPlotWidgetToMDI(frame)

    # Plot the set of signals selected by the user
    def ApplyTablePlotViewConfiguration(self, dataTreeFrame, configFilePath,
                                        all_DTV=False, plotAxis='TIME'):
        """Selects a set of signals using the selection file and plots of this
        shot view on a new table plot.

        The file names the quantities by IDS path and occurrence; what it holds
        besides the paths (pen, symbols, axis ranges) is not applied, and the log
        says so.

        :param plotAxis: see PlotSelectedSignalsInTablePlotViewFrame.
        :param dataTreeFrame:  A QVizDataTreeViewFrame object
        :param configFilePath: The path to a data selection file
        :param all_DTV: kept for call compatibility: a configuration file names
                        its quantities in this shot view, so there is no other
                        view to take a selection from.
        """
        from imasviz.VizGUI.VizGUICommands.VizPlotting import QVizPlotAsTable
        frame = QVizPlotAsTable(dataTreeView=dataTreeFrame.dataTreeView,
                                plotAxis=plotAxis,
                                configFile=configFilePath).execute()
        if frame is not None:
            self.addPlotWidgetToMDI(frame)

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

        One command per shot view in the list, each drawing that view's
        selection. With no figureKey each gets figures of its own, as before; with
        one, the selection is added to the curve figure it names.

        :param dataTreeFramesList:  A list of DTV frames
        :param figureKey: A figure key. If None, a new figure is created.
        :param all_DTV: When True, all current selected set of signals on all
                        shot views are plotted
        """
        from imasviz.VizGUI.VizGUICommands.VizPlotting import QVizPlotAsSlices
        for f in dataTreeFramesList:
            QVizPlotAsSlices(dataTreeView=f.dataTreeView,
                             all_DTV=all_DTV,
                             intoFigureKey=figureKey).execute()

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
        """Overwrite/Update the existing plot (the one currently shown in the
        plot window labeled as 'currentFigureKey') using the same
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

    def ForgetFigureOf(self, plotWidget):
        """Take a frame out of the bookkeeping under whichever key holds it.

        Closing the window is not going through DeleteFigure: no command sees it,
        so without this the frame stays in the registry, keeps a number the next
        figure of that kind is not entitled to, and stays in the menus as a
        figure that is not there any more.
        """
        figureKey = self.GetFigureKeyOf(plotWidget)
        if figureKey is not None:
            self.ForgetFigure(figureKey)

    def addPlotWidgetToMDI(self, plotWidget):
        """Embeds the plotWidget inside MDI subwindow.
        """
        subWindow = QVizMdiSubWindow(self)
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
