#  Name   : Viz_API
#
#          IMASViz Application Programming Interface.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
# ****************************************************
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
# ****************************************************

import os
import logging

from imasviz.VizUtils import (QVizGlobalOperations, FigureTypes,
                              QVizGlobalValues, QVizPreferences)
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

    def GetDTVFrames(self):
        """
        Returns the list of shot views frames currently opened.
        There is only one frame for a given shot.
        """
        return self.DTVframeList

    def GetDataSources(self):
        """
        Returns the list of data sources currently opened
        A data source is associated to one shot.
        :return: a list of data sources (QVizIMASDataSource objects)
        """
        dataSourcesList = []
        for dtv in self.DTVlist:
            dataSourcesList.append(dtv.dataSource)
        return dataSourcesList

    def isDataSourceAlreadyOpened(self, dataSource):
        """
        Returns True if this data source has been already created
        :param dataSource: a QVizIMASDataSource object
        :return: True or False
        """
        dataSourcesList = self.GetDataSources()
        for ds in dataSourcesList:
            if dataSource.getKey() == ds.getKey():
                return True
        return False

    def GetDTVFor(self, dataSourceKey):
        """
        Returns the shot view frame for the given data source key
        :param dataSourceKey: (str) the key of a data source (returned by QVizIMASDataSource.dataKey())
        :return: a QVizDataTreeViewFrame object
        """
        for dtv in self.DTVlist:
            if dataSourceKey == dtv.dataSource.getKey():
                return dtv
        return None

    def RemoveDTVFrame(self, frame):
        """
        Removes the shot view frame from the list of opened frames
        :param frame: a QVizDataTreeViewFrame object
        """
        self.DTVframeList.remove(frame)
        self.DTVlist.remove(frame.dataTreeView)

    def AddNodeToFigure(self, figureKey, key, tup):
        """
        Adds an entry to the figToNodes[figureKey] dictionary
        :param figureKey: (str) figure key
        :param key: (str) dtv.dataSource.dataKey(vizTreeNode)
        :param tup: (tuple) (dtv.dataSource.shotNumber, vizTreeNode)
        """
        if figureKey not in self.figToNodes:
            self.figToNodes[figureKey] = {}
        dic = self.figToNodes[figureKey]
        dic[key] = tup

    def GetPlotConfigurationPath(self, configurationName):
        """
        Get the path to plot configuration file (.pcfg extension).
        """
        return os.environ['HOME'] + "/.imasviz/" + configurationName + ".pcfg"

    def CreateDataTree(self, dataSource):
        """
        Returns the shot view frame for the specified data source
        :param dataSource: a QVizIMASDataSource object
        :return: a QVizDataTreeViewFrame object
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

    def ShowDataTree(self, dataTreeView):
        """
        Displays the specified data tree frame
        NOTE: a QVizDataTreeView accepts QVizDataTreeViewFrame as a parent object
        :param dataTreeView: a QVizDataTreeView or a QVizDataTreeViewFrame object
        """
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

    def ShowNodesSelection(self, DTV):
        """
        Displays a window showing a list of all selected nodes from the dataTreeView object
        NOTE: a QVizDataTreeView accepts QVizDataTreeViewFrame as a parent object
        :param DTV: a QVizDataTreeView or a QVizDataTreeViewFrame object
        """
        from imasviz.VizGUI.VizWidgets.QVizNodesSelectionWindow import QVizNodesSelectionWindow
        dataTreeView = DTV
        if isinstance(DTV, QVizDataTreeViewFrame):
            dataTreeView = DTV.dataTreeView
        self.nsw = QVizNodesSelectionWindow(dataTreeView)
        self.nsw.show()

    def GetSelectedNodes(self, DTV):
        """
        Returns the list of nodes selected by GUI or script commands.
        :param DTV: a QVizDataTreeViewFrame or QVizDataTreeView object
        :return: a list of QVizTreeNode objects
        """
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
        """
        Returns the list of signals (nodes) dictionaries selected by GUI or script commands.
        :param DTV: a QVizDataTreeViewFrame or QVizDataTreeView object
        :return: a list of signals (nodes) dictionaries
        """
        dataTreeView = DTV
        if isinstance(DTV, QVizDataTreeViewFrame):
            dataTreeView = DTV.dataTreeView
        return dataTreeView.selectedSignalsDict

    def GetSelectedSignalsDictFromAllDTVs(self):
        """
        Returns the list of signals (nodes) dictionaries selected by GUI or script commands
        from all opened shot views (DTVs)
        :return: a list of signals (nodes) dictionaries
        """
        allSelectedSignals = {}
        for i in range(len(self.DTVframeList)):
            allSelectedSignals.update(self.DTVframeList[i].dataTreeView.selectedSignalsDict)

        return allSelectedSignals

    def ShowHideFigure(self, figureKey):
        """
        SHows/Hides a figure
        :param figureKey: (str) a figure key (e.g. 'Figure:0).
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
        """
        Returns the next figure number available for plotting.
        :return: (int) the number of the next figure
        """
        return len(self.GetFiguresKeys())

    def GetTablePlotViewsCount(self):
        """
        Returns the next table plot number available for plotting.
        :return: (int) the number of the next table plot
        """
        return len(self.GetFiguresKeys(FigureTypes.TABLEPLOTTYPE))

    def GetStackedPlotViewsCount(self):
        """
        Returns the next table plot number available for plotting.
        :return: (int) the number of the next table plot
        """
        return len(self.GetFiguresKeys(FigureTypes.STACKEDPLOTTYPE))

    def GetNextKeyForTablePlotView(self):
        """
        Returns the key of the next table plot (e.g. if 'TablePlot i' is the
        latest table plot on the list of existing table plots, value 'TablePlot i+1' is
        returned.)
        :return: (str) the key of the next table plot
        """
        return FigureTypes.TABLEPLOTTYPE + str(self.GetTablePlotViewsCount())

    def GetNextKeyForFigurePlots(self):
        """
        Returns the key of the next figure plot (e.g. if 'Figure i' is the
        latest figure on the list of existing figures, value 'Figure i+1' is
        returned.)
        :return: (str) the key of the next figure (plot)
                """
        return FigureTypes.FIGURETYPE + str(self.GetFigurePlotsCount())

    def GetNextKeyForStackedPlotView(self):
        """
        Returns the key of the next stacked plot (e.g. if 'StackedPlot i' is the
        latest stacked plot on the list of existing stacked plots, value 'StackedPlot i+1' is
        returned.)
        :return: (str) the key of the next stacked plot
        """
        return FigureTypes.STACKEDPLOTTYPE + str(self.GetStackedPlotViewsCount())

    def GetFiguresKeys(self, figureType=FigureTypes.FIGURETYPE):
        """
        Returns the list of all figure keys
        :return: (list) a list of figure keys
        """
        figureKeys = []
        for key in self.figureframes.keys():
            if key.startswith(figureType):
                figureKeys.append(key)
        return sorted(figureKeys)

    def DeleteFigure(self, figureKey):
        """
        Deletes the specified figure
        :param figureKey: a figure key (e.g. 'Figure:0)
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
        """
        Get the figure key
        :param userKey: (str) figure number
        :param figureType: FigureTypes.FIGURETYPE
        :return: (str) a figure key
        """
        return figureType + userKey

    def getFigureKeyNum(self, figureKey, figureType):
        """
        Extract figure number from a figure key (e.g. 'Figure:0' -> 0).
        :param figureKey: a figure key (e.g. 'Figure:0')
        :param figureType: FigureTypes.FIGURETYPE or FigureTypes.STACKEDPLOTTYPE or FigureTypes.TABLEPLOTTYPE
        :return: (str) a figure key
        """
        numFig = int(figureKey[len(figureType):])
        return numFig

    # def getFigureFrame(self, figureKey):
    #     if figureKey in self.figureframes:
    #         return self.figureframes[figureKey]
    #     else:
    #         print("No frame found with key: " + str(figureKey))

    def PlotSelectedSignals(self, dataTreeFrame, figureKey=None, update=0, all_DTV=False, strategy="TIME"):
        """
        Plots the current selected set of signals on a figure
        :param dataTreeFrame: a QVizDataTreeViewFrame object
        :param plotWidget: a plot widget
        :param figureKey: a figure key. If None, a new figure is created.
        :param update: if 1, the current plot is updated otherwise a new plot is created
        :param all_DTV: if True, all current selected set of signals on all shot views are plotted
        """
        # if figureKey is None:
        #     figureKey = self.GetNextKeyForFigurePlots()
        QVizPlotSelectedSignals(dataTreeView=dataTreeFrame.dataTreeView,
                                figureKey=figureKey,
                                update=update,
                                all_DTV=all_DTV,
                                strategy=strategy).execute()

    def PlotSelectedSignalsInTablePlotViewFrame(self, dataTreeFrame, all_DTV=False, strategy='DEFAULT'):
        """
        Plots the current selected set of signals of this shot view on a new table plot
        :param dataTreeFrame: a QVizDataTreeViewFrame object
        :param all_DTV: if True, all current selected set of signals on all shot views are plotted
        """
        QVizSignalHandling(dataTreeFrame.dataTreeView).onPlotToTablePlotView(all_DTV, strategy=strategy)

    # Plot the set of signals selected by the user
    def ApplyTablePlotViewConfiguration(self, dataTreeFrame, configFilePath, all_DTV=False, strategy='DEFAULT'):
        """
        Selects a set of signals using the selection file and plots of this shot view on a new table plot
        :param dataTreeFrame: a QVizDataTreeViewFrame object
        :param configFilePath: the path to a data selection file
        :param all_DTV: if True, all current selected set of signals on all shot views are plotted
        """
        QVizSignalHandling(dataTreeFrame.dataTreeView).onPlotToTablePlotView(
            all_DTV=all_DTV,
            configFile=configFilePath,
            strategy=strategy)

    def LoadMultipleIDSData(self, dataTreeFrame, IDSNamesList, occurrence=0,
                            threadingEvent=None):
        """
        Load multiple IDSs data for a given data tree frame and a given occurrence
        :param dataTreeFrame: a QVizDataTreeViewFrame object
        :param IDSNamesList: list of the names of the IDSs
        :param occurrence: (int) occurrence to be loaded (will be the same for all IDSs)
        :param threadingEvent: if True, data are loaded from a new Thread
        """
        for IDSName in IDSNamesList:
            self.LoadIDSData(dataTreeFrame, IDSName, occurrence, threadingEvent)


    def LoadIDSData(self, dataTreeFrame, IDSName, occurrence=0,
                    threadingEvent=None):
        """
        Load IDS data for a given data tree frame and a given occurrence
        :param dataTreeFrame: a QVizDataTreeViewFrame object
        :param IDSName: the name of the IDS
        :param occurrence: (int) occurrence of the IDS
        :param threadingEvent: if True, data are loaded from a new Thread
        """
        if isinstance(dataTreeFrame, QVizDataTreeViewFrame):
            QVizLoadSelectedData(dataTreeFrame.dataTreeView, IDSName, occurrence, threadingEvent).execute()
        else:
            QVizLoadSelectedData(dataTreeFrame, IDSName, occurrence, threadingEvent).execute()


    def SelectSignals(self, DTV, pathsMap):
        """
        Select signals nodes from a list of IMAS paths for the given shot view.
        :param DTV: a QVizDataTreeViewFrame object
        :param pathsMap: (dict) pathsMap['paths'] : a list of signal paths (e.g.
                                           ['magnetics/flux_loop(0)/flux/data'])
                                           pathsMap['occurrences'] : a list of occurrences
        """
        QVizSelectSignals(DTV.dataTreeView, pathsMap).execute()

    def PlotSelectedSignalsFrom(self, dataTreeFramesList, figureKey=None, all_DTV=False):
        """
        Plots current selected signal
        :param dataTreeFramesList:  A list of DTV frames
        :param figureKey: a figure key. If None, a new figure is created.
        :param all_DTV: if True, all current selected set of signals on all shot views are plotted
        """
        # figureKey, plotWidget = self.GetPlotWidget(dataTreeView=self.dataTreeView,
        #                                            figureKey=figureKey)
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
        """
        Unselects all previously selected signals for the given shot view
        :param dataTreeFrame: a QVizDataTreeViewFrame object
        :param all_DTV: if True, all selected signals from all shot views are unselected
        """
        QVizUnselectAllSignals(dataTreeFrame.dataTreeView, all_DTV=all_DTV).execute()

    def SelectSignalsGroup(self, dataTreeFrame, occurrence, onePathInTheGroup):
        """
        Selects nodes for this shot view
        :param dataTreeFrame: a QVizDataTreeViewFrame object
        :param occurrence: the occurrence of an IDS
        :param onePathInTheGroup: An IDS path to one of the node
                                      (signals), containing a data array
                                      (e.g. FLT_1D), of which all siblings
                                      in the AOS are to be selected.
                                      Example:
                                      'magnetics/flux_loop(0)/flux/data'
        """
        QVizSelectSignalsGroup(dataTreeFrame.dataTreeView,  dataTreeFrame.dataTreeView.selectedItem).execute()

    def IDSDataAlreadyFetched(self, dataTreeView, IDSName, occurrence):
        key = IDSName + "/" + str(occurrence)
        if key in dataTreeView.ids_roots_occurrence:
            return True
        else:
            return False

    def GetNextOccurrenceUnloadedWithAvailableData(self, dataTreeView, node):
        for i in range(0, QVizGlobalValues.MAX_NUMBER_OF_IDS_OCCURRENCES):
            if not self.IDSDataAlreadyFetched(dataTreeView, node.getIDSName(), i):
                if node.hasIDSAvailableData(i):
                    return i
        return None

    def GetAllOccurrencesWithAvailableData(self, node):
        availableOccurrences = []
        for i in range(0, QVizGlobalValues.MAX_NUMBER_OF_IDS_OCCURRENCES):
            if node.hasIDSAvailableData(i):
                availableOccurrences.append(i)
        return availableOccurrences

    def GetAllOccurrencesUnloadedWithAvailableData(self, dataTreeView, node):
        availableOccurrences = []
        for i in range(0, QVizGlobalValues.MAX_NUMBER_OF_IDS_OCCURRENCES):
            if node.hasIDSAvailableData(i) and \
                    not self.IDSDataAlreadyFetched(dataTreeView, node.getIDSName(), i):
                availableOccurrences.append(i)
        return availableOccurrences


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

    def CreatePlotWidget(self, dataTreeView, strategy="DEFAULT"):
        figureKey = self.GetNextKeyForFigurePlots()

        addTimeSlider = False
        addCoordinateSlider = False

        if strategy=="COORDINATE1":
             addTimeSlider = True
             addCoordinateSlider = False
        elif strategy=="TIME":
             addTimeSlider = False
             addCoordinateSlider = True

        plotWidget = QVizPlotWidget(size=(600, 550),
                                    title=figureKey,
                                    dataTreeView=dataTreeView,
                                    addTimeSlider=addTimeSlider,
                                    addCoordinateSlider=addCoordinateSlider)
        plotWidget.setStrategy(strategy)
        self.figureframes[figureKey] = plotWidget
        return figureKey, plotWidget

    def GetPlotWidget(self, dataTreeView, figureKey=0, strategy="DEFAULT"):
        if figureKey in self.figureframes:
            plotWidget = self.figureframes[figureKey]
        else:
            figureKey, plotWidget = self.CreatePlotWidget(dataTreeView=dataTreeView,
                                                          strategy=strategy)
        return figureKey, plotWidget


    def GetSignal(self, dataTreeView, vizTreeNode, as_function_of_time=None,
                  coordinate1_index=0, time_index=None, plotWidget=None):
        try:
            signalDataAccess = QVizDataAccessFactory(dataTreeView.dataSource).create()
            return signalDataAccess.GetSignal(treeNode=vizTreeNode, plotWidget=plotWidget,
                                              as_function_of_time=as_function_of_time,
                                              coordinate_index=coordinate1_index,
                                              time_index=time_index)
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
            figureKey, plotWidget = self.GetPlotWidget(dataTreeView=dataTreeView, figureKey=None, strategy='TIME')
            self.addPlotWidgetToMDI(plotWidget)
            p = QVizPlotSignal(dataTreeView=dataTreeView,
                           vizTreeNode=treeNode,
                           title=title,
                           label=label,
                           xlabel="time",
                           plotWidget=plotWidget)
            p.execute(figureKey=figureKey, update=0)
        except ValueError as e:
            logging.error(str(e))

    def plot0D_DataVsTimeCommand(self, dataTreeView):

        """Plotting of 0D data nodes, found within timed AOS
        """
        try:
            # Get currently selected QVizTreeNode (QTreeWidgetItem)
            treeNode = dataTreeView.selectedItem
            figureKey, plotWidget = self.GetPlotWidget(dataTreeView=dataTreeView, figureKey=None, strategy='TIME') #None will force a new Figure
            self.addPlotWidgetToMDI(plotWidget)
            p = QVizPlotSignal(dataTreeView=dataTreeView,
                               vizTreeNode=treeNode,
                               xlabel="time",
                               plotWidget=plotWidget)
            p.execute(figureKey=figureKey, update=0)
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
                                                              strategy='TIME')

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
            logging.error(str(e))

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
        try:
            currentFigureKey, plotWidget = self.GetPlotWidget(dataTreeView=dataTreeView,
                                                              figureKey=currentFigureKey,
                                                              strategy='COORDINATE1')
            api = dataTreeView.imas_viz_api
            # Add plot window to subwindow and to MDI only if the plotWidget
            # with the given figurekey does not exist yet
            if currentFigureKey not in self.figureframes:
                self.addPlotWidgetToMDI(plotWidget)
            # Update/Overwrite plot
            QVizPlotSignal(dataTreeView=dataTreeView,
                           vizTreeNode=treeNode,
                           plotWidget=plotWidget,).execute(figureKey=currentFigureKey,
                                                         update=update,
                                                         dataset_to_update=dataset_to_update)
        except ValueError as e:
            logging.error(str(e))

    def getMDI(self):
        if self.parent is not None:
            return self.parent
        return None

    def addPlotWidgetToMDI(self, plotWidget):
        """Embeds the plotWidget inside MDI subwindow.
        """
        from PyQt5.QtWidgets import QMdiSubWindow

        subWindow = QMdiSubWindow()
        subWindow.setWidget(plotWidget)
        subWindow.resize(plotWidget.width(), plotWidget.height())
        self.getMDI().addSubWindow(subWindow)

    def LoadListOfIDSs(self, dataTreeView, namesOfIDSs, occurrence=0):
        """Load given IDSs for given occurrence.

        Arguments:
            dataTreeView (obj)   : Instance of DTV.
            namesOfIDSs  (list)  : List of IDS names (strings)
            occurrence   (int)   : IDS occurrence
        """
        idssByNames = {}

        for idsName in namesOfIDSs:
            if not self.IDSDataAlreadyFetched(dataTreeView=dataTreeView,
                                              IDSName=idsName,
                                              occurrence=occurrence):
                self.LoadIDSData(dataTreeView, idsName, occurrence)

            idd = dataTreeView.dataSource.getImasEntry(occurrence)
            idssByNames[idsName] = eval("idd." + idsName)

        return idssByNames
