#  Name   : QVizSignalHandling
#
#          Container to handle right-click events for signals - filled (blue)
#          tree items (PyQt5).
#          Note: The wxPython predecessor of this Python file is
#          SignalHandling.py
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#  TODO:
#
#    - Function definitions (from SignalHandling class)
#    def plotSelectedSignalsToMultiPlotsFrame
#    def plotSelectedSignalVsTime
#    def plotSelectedSignalVsTimeAtIndex
#    def plotSelectedSignalVsCoordAtTimeIndex
#    def deleteMultiplots
#    def addSignalSelectionToMultiPlotFrame
#    def deleteSubplots
#    def showSubPlotsManager
#    def # onClose
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#****************************************************

# from imasviz.VizDataAccess.QVizDataAccessFactory import QVizDataAccessFactory
from functools import partial

from PyQt5.QtCore import QObject, pyqtSlot
from PyQt5.QtWidgets import QAction, QMenu
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations

from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizMultiPlot import QVizMultiPlot
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSelectedSignals import QVizPlotSelectedSignals
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal import QVizPlotSignal
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPreviewPlotSignal import QVizPreviewPlotSignal
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectOrUnselectSignal import QVizSelectOrUnselectSignal
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignalsGroup import QVizSelectSignalsGroup
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizUnselectAllSignals import QVizUnselectAllSignals
from imasviz.VizUtils.QVizGlobalValues import FigureTypes


class QVizSignalHandling(QObject):
    def __init__(self, dataTreeView):
        """
        Arguments:
            dataTreeView (QTreeWidget) : DataTreeView object of the QTreeWidget.
        """
        super(QVizSignalHandling, self).__init__()
        self.dataTreeView = dataTreeView
        self.api = self.dataTreeView.imas_viz_api
        # self.CHANGE_COORD1 = GlobalIDs.ID_CHANGE_COORD1
        # self.CHANGE_TIME1  = GlobalIDs.ID_CHANGE_TIME1
        self.plotFrame = None
        self.currentFigureKey = None
        # Get signal node (tree item) data
        self.nodeData = None
        if self.dataTreeView.selectedItem != None:
            self.nodeData = self.dataTreeView.selectedItem.itemVIZData
        # Get signal node dataName
        self.treeNode = None
        if self.nodeData != None:
            self.treeNode = \
                self.dataTreeView.getNodeAttributes(self.nodeData['dataName'])
        self.timeSlider = None

    def updateNodeData(self):
        """ Update tree node/item data.
            TODO: use the global routine 'updateNodeData' defined in
                  QVizAbstractCommand instead.
        """
        self.nodeData = self.dataTreeView.selectedItem.itemVIZData
        self.treeNode = \
            self.dataTreeView.getNodeAttributes(self.nodeData['dataName'])

    def showPopUpMenu(self, signalName):
        """Display the popup menu for plotting data.

        Arguments:
            signalName (str) : Name of the signal node (tree item).
                               (example: ids.magnetics.flux_loop[0].flux.data)
        """

        if (signalName == None): return 0

        # Set new popup menu
        self.dataTreeView.popupmenu = QMenu()
        s = ''

        # ----------------------------------------------------------------------
        # The popup menu behavior in relation on the selection/unselection
        # status of the node
        if self.nodeData['isSelected'] == 1:
            # If the node is selected, show unselect menu
            s = 'Unselect '
            # Bitmap icon
            # TODO
        else:
            # The node is unselected, show select menu
            s = 'Select '
            # Bitmap icon
            # TODO

        # Set second-level popup menu for selection/unselection of the node
        action_selectOrUnselectSignal = QAction(s + signalName + '...', self)
        action_selectOrUnselectSignal.triggered.connect(self.selectOrUnselectSignal)
        self.dataTreeView.popupmenu.addAction(action_selectOrUnselectSignal)
        # Set bitmap to menu item
        # TODO

        # ----------------------------------------------------------------------
        # Add menu item for unselection of all selected signals if there are
        # and selected signals present
        if bool(self.dataTreeView.selectedSignalsDict) == True:
            action_UnselectAllSignals = QAction('Unselect all signals', self)
            action_UnselectAllSignals.triggered.connect(self.unselectAllSignals)
            self.dataTreeView.popupmenu.addAction(action_UnselectAllSignals)
            # Set bitmap to menu item
            # TODO

        # ----------------------------------------------------------------------
        # Add menu item for selection of all signals from the same array of
        # structures
        action_selectAllSignalsFromSameAOS = \
            QAction('Select all signals from the same AOS', self)
        action_selectAllSignalsFromSameAOS.triggered.connect(
            self.selectAllSignalsFromSameAOS)
        self.dataTreeView.popupmenu.addAction(action_selectAllSignalsFromSameAOS)
        # Set bitmap to menu item
        # TODO

        # ----------------------------------------------------------------------
        # The popup menu behaviour in relation to the presence of pre-existing
        # plots
        if self.api.GetFigurePlotsCount() == 0:
            # ------------------------------------------------------------------
            # If there is no pre-existing figure:
            # Add menu item to plot the signal data to a new figure
            action_plotSignalCommand = QAction('Plot ' + signalName, self)
            action_plotSignalCommand.triggered.connect(self.plotSignalCommand)
            self.dataTreeView.popupmenu.addAction(action_plotSignalCommand)
        else:
            # ------------------------------------------------------------------
            # Else, if some plot already exists:
            # Add menu for creation of a new figure
            action_plotSignalCommand = \
                QAction('Plot ' + signalName + ' to new figure', self)
            action_plotSignalCommand.triggered.connect(self.plotSignalCommand)
            self.dataTreeView.popupmenu.addAction(action_plotSignalCommand)

            # ------------------------------------------------------------------
            ## Popup menu behaviour when figures are present
            # Create and add empty submenu to handle adding plots to existing
            # figure
            subMenu_addPlot = QMenu('Add plot to existing figure')
            self.dataTreeView.popupmenu.addMenu(subMenu_addPlot)
            # Create and add empty submenu to handle show/hide figures
            subMenu_showHideFigure = QMenu('Show/Hide figure')
            self.dataTreeView.popupmenu.addMenu(subMenu_showHideFigure)
            # Create and add empty submenu to handle figures deletion
            subMenu_deleteFigure = QMenu('Delete figure')
            self.dataTreeView.popupmenu.addMenu(subMenu_deleteFigure)

            for figureKey in self.api.GetFiguresKeys(
                figureType=FigureTypes.FIGURETYPE):
                # Get figure number out from the figureKey string
                # (e.g. 'Figure:0' -> 0)
                # numFig = int(figureKey.split(':')[1])
                numFig = self.api.getFigureKeyNum(figureKey)

                # --------------------------------------------------------------
                # Add menu item to add plot to specific existing figure
                # Check for figures that share the same coordinates
                if self.shareSameCoordinatesFrom(figureKey):
                    # Set action
                    action_addSignalPlotToFig = QAction(figureKey, self)
                    action_addSignalPlotToFig.triggered.connect(
                        partial(self.addSignalPlotToFig, numFig))
                    # Add to submenu
                    subMenu_addPlot.addAction(action_addSignalPlotToFig)

                # --------------------------------------------------------------
                # Add menu item to show/hide existing figure
                # Set action
                action_showHideFigure = QAction(figureKey, self)
                action_showHideFigure.triggered.connect(
                    partial(self.showHideFigure, numFig, FigureTypes.FIGURETYPE))
                # Add to submenu
                subMenu_showHideFigure.addAction(action_showHideFigure)

                # --------------------------------------------------------------
                # Add menu item to delete existing figure
                # Set action
                action_deleteFigure = QAction(figureKey, self)
                action_deleteFigure.triggered.connect(
                    partial(self.deleteFigure, numFig))
                # Add to submenu
                subMenu_deleteFigure.addAction(action_deleteFigure)

            # ------------------------------------------------------------------
            # Add menu item to delete all existing figures
            # Set action
            action_deleteAllFigures = QAction('All', self)
            action_deleteAllFigures.triggered.connect(self.deleteAllFigures)
            # Add to submenu
            subMenu_deleteFigure.addAction(action_deleteAllFigures)


            # Bitmap icon
            # TODO

            # ------------------------------------------------------------------
            # Add submenu to add plot selected signals to specific existing
            # figure, if selected signals are present
            if len(self.dataTreeView.selectedSignalsDict) > 0 \
                and self.shareSameCoordinates(self.dataTreeView.selectedSignalsDict):
                # Create and add empty submenu to main menu
                subMenu_2 = QMenu('Plot all selected signals to')
                self.dataTreeView.popupmenu.addMenu(subMenu_2)

                for figureKey in self.api.GetFiguresKeys(
                    figureType=FigureTypes.FIGURETYPE):
                    # Check for figures that share the same coordinates
                    if self.shareSameCoordinatesFrom(figureKey):
                        # Get figure number out from the figureKey string
                        # (e.g. 'Figure:0' -> 0)
                        # numFig = int(figureKey.split(':')[1])
                        numFig = self.api.getFigureKeyNum(figureKey)
                        # Add menu item to add plot to specific figure
                        action_addSelectedSignalsPlotToFig = \
                            QAction(figureKey, self)
                        action_addSelectedSignalsPlotToFig.triggered.connect(
                            partial(self.addSelectedSignalsPlotToFig, numFig))
                        # Add to submenu
                        subMenu_2.addAction(action_addSelectedSignalsPlotToFig)
        # Bitmap icon
        # TODO

        # ----------------------------------------------------------------------
        # Set submenu for handling features for plotting selected signals to new
        # plot widget
        if len(self.dataTreeView.selectedSignalsDict) > 0:
            if self.shareSameCoordinates(self.dataTreeView.selectedSignalsDict):
                subMenu_plot = QMenu('Plot all selected signals to a new figure')
                self.dataTreeView.popupmenu.addMenu(subMenu_plot)

                # --------------------------------------------------------------
                # Add menu item to plot selected signals to single
                # plot - This DTV
                action_plotSelectedSignals = QAction('This IMAS Database',
                                                     self)
                action_plotSelectedSignals.triggered.connect(
                    partial(self.plotSelectedSignals, False))
                # Add to submenu
                subMenu_plot.addAction(action_plotSelectedSignals)

                # --------------------------------------------------------------
                # Add menu item to plot selected signals to single
                # plot - All DTVs
                action_plotSelectedSignals = QAction('All IMAS Databases',
                                                     self)
                action_plotSelectedSignals.triggered.connect(
                    partial(self.plotSelectedSignals, True))
                # Add to submenu
                subMenu_plot.addAction(action_plotSelectedSignals)

        # ----------------------------------------------------------------------
        # Set submenu for handling features for plotting selected signals to new
        # MultiPlot
        if len(self.dataTreeView.selectedSignalsDict) > 0:
            subMenu_multiplot = \
                QMenu('Plot all selected signals to a new MultiPlot')
            self.dataTreeView.popupmenu.addMenu(subMenu_multiplot)

            # --------------------------------------------------------------
            # Add menu item to plot selected signals to single
            # plot - This DTV
            action_multiPlotSelectedSignals = QAction('This IMAS Database',
                                                 self)
            action_multiPlotSelectedSignals.triggered.connect(
                partial(self.plotSelectedSignalsToMultiPlotsFrame, False))
            # Add to submenu
            subMenu_multiplot.addAction(action_multiPlotSelectedSignals)

            # --------------------------------------------------------------
            # Add menu item to plot selected signals to single
            # plot - All DTVs
            action_multiPlotSelectedSignals = QAction('All IMAS Databases',
                                                 self)
            action_multiPlotSelectedSignals.triggered.connect(
                partial(self.plotSelectedSignalsToMultiPlotsFrame, True))
            # Add to submenu
            subMenu_multiplot.addAction(action_multiPlotSelectedSignals)

            # TODO:
            """
            - 'Show/Hide multiplots'
            - 'Show/Hide subplots'
            - 'Delete multiplot'
            - 'Add selection to MultiPlot'
            - 'Delete subplot'
            - 'Open subplots manager'
            - 'Plot ' + signalName + ' as a function of time'
            - 'Plot selected signals to a multiplots frame (all opened IMAS databases)'
            - 'Plot selected signals to a multiplots frame (this opened IMAS database'
            """

        # Map the menu (in order to show it)
        self.dataTreeView.popupmenu.exec_( \
            self.dataTreeView.viewport().mapToGlobal(self.dataTreeView.pos))
        return 1

    def selectSignal(self):
        QVizSelectOrUnselectSignal(self.dataTreeView, self.nodeData).execute()

    @pyqtSlot()
    def selectOrUnselectSignal(self):
        QVizSelectOrUnselectSignal(self.dataTreeView, self.nodeData).execute()

    @pyqtSlot()
    def unselectAllSignals(self):
        QVizUnselectAllSignals(self.dataTreeView).execute()

    @pyqtSlot()
    def selectAllSignalsFromSameAOS(self):
        QVizSelectSignalsGroup(self.dataTreeView, self.nodeData).execute()

    @pyqtSlot()
    def plotSignalCommand(self):
        try:
            self.currentFigureKey = self.api.GetNextKeyForFigurePlots()
            treeNode = self.dataTreeView.getNodeAttributes(self.nodeData['dataName'])
            label = None
            xlabel = None
            if treeNode != None and treeNode.time_dependent_aos():
                aos_vs_itime = treeNode.getDataPathVsTime(treeNode.aos)
                label = treeNode.getDataPath(aos_vs_itime, 0)
                label = label.replace("ids.", "")
                label = QVizGlobalOperations.replaceBrackets(label)
                label = QVizGlobalOperations.replaceDotsBySlashes(label)
                xlabel = \
                    QVizGlobalOperations.replaceBrackets(treeNode.evaluateCoordinate1At(0))
                self.timeSlider = True
            else:
                self.timeSlider = None
            # Get the signal data for plot widget
            p = QVizPlotSignal(self.dataTreeView, self.nodeData, signal=None,
                               figureKey=self.currentFigureKey, label=label,
                               xlabel=xlabel, signalHandling=self)
            # Plot signal data to plot widget
            p.execute()

        except ValueError as e:
            self.dataTreeView.log.error(str(e))

    def plotPreviewSignalCommand(self):
        """Show preview plot.
        """
        try:
            label = None
            xlabel = None

            # Get the signal data for preview plot update
            p = QVizPreviewPlotSignal(dataTreeView = self.dataTreeView,
                                      nodeData = self.nodeData,
                                      signal = None, label = label,
                                      xlabel = xlabel, signalHandling = self)
            # Plot signal data to preview plot widget
            p.execute()

        except ValueError as e:
            self.dataTreeView.log.error(str(e))

    # @pyqtSlot(bool)
    def plotSelectedSignals(self, all_DTV=True):
        """Plot selected signals from current or all DTV instances.

        Arguments:
            all_DTV (bool) : Boolean operator specifying if current or all DTVs
                             should be considered.
        """
        # Get label for the next figure (e.c. if 'Figure 2' already exists,
        # value 'Figure 3' will be returned)
        figureKey = self.api.GetNextKeyForFigurePlots()
        # Plot the selected signals
        if all_DTV == False:
            QVizPlotSelectedSignals(self.dataTreeView, figureKey,
                                    all_DTV=False).execute()
        else:
            QVizPlotSelectedSignals(self.dataTreeView, figureKey,
                                    all_DTV=True).execute()

    @pyqtSlot(bool)
    def plotSelectedSignalsToMultiPlotsFrame(self, all_DTV=False):
        """Create a MultiPlot using signals selected in single/all opened DTV
        windows.

        Arguments:
            all_DTV (bool) : Operator to read selected signals from the
                             current or all DTVs.
        """
        # Get next figure key/label
        figureKey = self.dataTreeView.imas_viz_api.GetNextKeyForMultiplePlots()
        if all_DTV != True:
            QVizMultiPlot(dataTreeView=self.dataTreeView, figureKey=figureKey,
                          update=1, all_DTV=False)
        else:
            QVizMultiPlot(dataTreeView=self.dataTreeView, figureKey=figureKey,
                          update=1, all_DTV=True)

    @pyqtSlot(int)
    def addSignalPlotToFig(self, numFig):
        """Add signal plot to existing figure.

        Arguments:
            numFig (int) : Number identification of the existing figure.
        """
        try:
            # Get figure key (e.g. 'Figure:0' string)
            figureKey = self.api. \
                GetFigureKey(str(numFig), figureType=FigureTypes.FIGURETYPE)
            QVizPlotSignal(dataTreeView=self.dataTreeView,
                           nodeData=self.nodeData,
                           figureKey=figureKey,
                           update=1).execute()
        except ValueError as e:
            self.dataTreeView.log.error(str(e))

    @pyqtSlot(int)
    def addSelectedSignalsPlotToFig(self, numFig):
        """Add/Plot selected signals to existing figure.

        Arguments:
            numFig (int) : Number identification of the existing figure.
        """
        # Get figure key (e.g. 'Figure:0' string)
        figureKey = self.api. \
            GetFigureKey(str(numFig), figureType=FigureTypes.FIGURETYPE)

        QVizPlotSelectedSignals(self.dataTreeView, figureKey, update=1,
                                all_DTV=False).execute()

    def shareSameCoordinates(self, selectedDataList):
        """Check if data in selectedDataList (dict) share the same coordinates
        """

        selectedSignalsList = []
        for key in selectedDataList:
            signalDict = selectedDataList[key]

            selectedSignalsList.append(signalDict['nodeData'])

        s = self.nodeData
        for si in selectedSignalsList:
            if s['coordinate1'] != si['coordinate1']:
                return False
            s = si
        return True

    def shareSameCoordinatesFrom(self, figureKey):
        """Check if data already in figure and next to be added signal plot
        share the same coordinates.
        """
        selectedDataList = self.api.figToNodes[figureKey]

        selectedSignalsList = []
        for k in selectedDataList:
            v = selectedDataList[k]
            selectedSignalsList.append(v[1]) # v[0] = shot number,
                                             # v[1] = node data
        s = self.nodeData
        for si in selectedSignalsList:
            if s['coordinate1'] != si['coordinate1']:
                return False
            s = si
        return True

    @pyqtSlot(int, str)
    def showHideFigure(self, numFig, figureType):
        """Show/Hide figure plot widget window or MultiPlot frame.

        Arguments:
            numFig     (int) : Figure number identificator.
            figureType (str) : Type of figure e.c. "Figure:", "Multiplot:",
                               "Subplot"... see QVizGlobalValues.py FigureTypes
                               class for a full list of figure types.
        """
        # Get figure key (e.g. 'Figure:0' string)
        figureKey = \
            self.api.GetFigureKey(str(numFig), figureType=FigureTypes.FIGURETYPE)
        self.api.ShowHideFigure(figureKey)

    @pyqtSlot()
    def deleteAllFigures(self):
        figureKeys = self.api.GetFiguresKeys(figureType=FigureTypes.FIGURETYPE)
        for figureKey in figureKeys:
            self.api.DeleteFigure(figureKey)

    @pyqtSlot(int)
    def deleteFigure(self, numFig):
        """Delete figure plot widget window.

        Arguments:
            numFig     (int) : Figure number identificator.
        """
        try:
            # Get figure key (e.g. 'Figure:0' string)
            figureKey = self.api. \
                GetFigureKey(str(numFig), figureType=FigureTypes.FIGURETYPE)
            self.api.DeleteFigure(figureKey)
        except ValueError as e:
            self.dataTreeView.log.error(str(e))
