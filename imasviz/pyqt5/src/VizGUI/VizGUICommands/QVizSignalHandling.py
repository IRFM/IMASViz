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
#    def showPopUpMenu
#    def popUpMenuHandler
#    def selectSignal
#    def selectOrUnselectSignal
#    def unselectAllSignals
#    def plotSignalCommand
#    def plotPreviewSignalCommand
#    def plotSelectedSignals
#    def plotSelectedSignalsToFig
#    def plotSelectedSignalsToMultiPlotsFrame
#    def selectAllSignalsFromSameAOS
#    def plotSelectedSignalVsTime
#    def plotSelectedSignalVsTimeAtIndex
#    def plotSelectedSignalVsCoordAtTimeIndex
#    def addSignalPlotToFig
#    def shareSameCoordinates
#    def shareSameCoordinatesFrom
#    def hideShowfigure
#    def deleteAllFigures
#    def deleteFigure
#    def deleteMultiplots
#    def addSignalSelectionToMultiPlotFrame
#    def deleteSubplots
#    def showSubPlotsManager
#    def # onClose
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#****************************************************

# from imasviz.signals_data_access.SignalDataAccessFactory import SignalDataAccessFactory
from imasviz.pyqt5.src.VizGUI.VizGUICommands.VizSignalSelectionCommands.QVizSelectOrUnselectSignal \
    import QVizSelectOrUnselectSignal
from imasviz.pyqt5.src.VizGUI.VizGUICommands.VizSignalSelectionCommands.QVizUnselectAllSignals \
    import QVizUnselectAllSignals
from imasviz.pyqt5.src.VizGUI.VizGUICommands.VizSignalSelectionCommands.QVizSelectSignalsGroup \
    import QVizSelectSignalsGroup
from imasviz.pyqt5.src.VizGUI.VizPlot.QVizPlotSignal import QVizPlotSignal
from imasviz.pyqt5.src.VizGUI.VizPlot.QVizPreviewPlotSignal import QVizPreviewPlotSignal
# from imasviz.gui_commands.plot_commands.PreviewPlotSignal import PreviewPlotSignal
# from imasviz.gui_commands.plot_commands.PlotSelectedSignals import PlotSelectedSignals
# from imasviz.gui_commands.plot_commands.PlotSelectedSignalsWithWxmplot import (PlotSelectedSignalsWithWxmplot,
#                                                                               modifyMultiPlot)
from imasviz.util.GlobalValues import GlobalIDs
from imasviz.util.GlobalOperations import GlobalOperations
# from imasviz.view.Coord1Slider import Coord1Slider
from imasviz.util.GlobalValues import FigureTypes
from PyQt5.QtWidgets import QAction, QMenu
from PyQt5.QtCore import QObject, pyqtSlot

class QVizSignalHandling(QObject):
    def __init__(self, dataTreeView):
        """
        Arguments:
            dataTreeView (QTreeWidget) : DataTreeView object of the QTreeWidget.
        """
        super(QVizSignalHandling, self).__init__()
        self.dataTreeView = dataTreeView
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
                  AbstractCommand instead.
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
        if bool(self.dataTreeView.selectedSignals) == True:
            action_UnselectAllSignals = QAction('Unselect all signals')
            action_UnselectAllSignals.triggered.connect(self.unselectAllSignals)
            self.dataTreeView.popupmenu.addAction(action_UnselectAllSignals)
            # Set bitmap to menu item
            # TODO

        # ----------------------------------------------------------------------
        # Add menu item for selection of all signals from the same array of
        # signals
        action_selectAllSignalsFromSameAOS = \
            QAction('Select all signals from the same AOS', self)
        action_selectAllSignalsFromSameAOS.triggered.connect(self.selectAllSignalsFromSameAOS)
        self.dataTreeView.popupmenu.addAction(action_selectAllSignalsFromSameAOS)
        # Set bitmap to menu item
        # TODO

        # ----------------------------------------------------------------------
        # The popup menu behaviour in relation to the presence of pre-existing
        # plots
        if len(self.dataTreeView.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.FIGURETYPE))==0:
            # If there is no pre-existing plot
            action_plotSignalCommand = QAction('Plot ' + signalName, self)
            action_plotSignalCommand.triggered.connect(self.plotSignalCommand)
            self.dataTreeView.popupmenu.addAction(action_plotSignalCommand)
        else:
            # Add menu for creation of a new figure
            action_plotSignalCommand = \
                QAction('Plot ' + signalName + ' to new figure', self)
            action_plotSignalCommand.triggered.connect(self.plotSignalCommand)
            self.dataTreeView.popupmenu.addAction(action_plotSignalCommand)

            pass
            # TODO:
            """
            - 'Plot ' + signalName + ' to new figure'
            - 'Add plot to existing figure'
            - 'Show/Hide figure'
            - 'Show/Hide multiplots'
            - 'Show/Hide subplots'
            - 'Delete figure'
            - 'Delete multiplot'
            - 'Add selection to MultiPlot'
            - 'Delete subplot'
            - 'Plot all selected signals to'
            - 'Plot all selected signals to a new figure'
            - 'Open subplots manager'
            - 'Plot ' + signalName + ' as a function of time'
            - 'Plot selected signals to a multiplots frame (all opened IMAS databases)'
            - 'Plot selected signals to a multiplots frame (this opened IMAS database'
            - 'Select all signals from the same AOS'
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
        print("* self.dataTreeView.selectedSignals: ", self.dataTreeView.selectedSignals)

    @pyqtSlot()
    def plotSignalCommand(self):
        try:
            self.currentFigureKey = \
                self.dataTreeView.imas_viz_api.GetNextKeyForFigurePlots()
            treeNode = self.dataTreeView.getNodeAttributes(self.nodeData['dataName'])
            label = None
            xlabel = None
            if treeNode != None and treeNode.time_dependent_aos():
                aos_vs_itime = treeNode.getDataPathVsTime(treeNode.aos)
                label = treeNode.getDataPath(aos_vs_itime, 0)
                label = label.replace("ids.", "")
                label = GlobalOperations.replaceBrackets(label)
                label = GlobalOperations.replaceDotsBySlashes(label)
                xlabel = \
                    GlobalOperations.replaceBrackets(treeNode.evaluateCoordinate1At(0))
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