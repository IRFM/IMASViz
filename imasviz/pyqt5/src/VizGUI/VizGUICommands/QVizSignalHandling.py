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
# from imasviz.gui_commands.select_commands.SelectOrUnselectSignal import SelectOrUnselectSignal
# from imasviz.gui_commands.select_commands.UnselectAllSignals import UnselectAllSignals
# from imasviz.gui_commands.select_commands.SelectSignalsGroup import SelectSignalsGroup
# from imasviz.gui_commands.plot_commands.PlotSignal import PlotSignal
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

        # Set second-level popup menu for selection/deselection of the node
        # TODO
        # Set bitmap to menu item
        # TODO

        item3 = None
        # The popup menu behaviour in relation to the presence of pre-existing
        # plots
        if len(self.view.imas_viz_api.GetFiguresKeys(
                figureType=FigureTypes.FIGURETYPE))==0:
            # If there is no pre-existing plot
            action_plot = QAction('Plot ' + signalName)
            action_plot.triggered.connect(self.plotSignalCommand)
            self.dataTreeView.popupmenu.addAction(action_plot)
        else:
            pass
            # TODO:
            """
            - signal selection/deselection (above)
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
            - 'Unselect all signals'
            - 'Open subplots manager'
            - 'Plot ' + signalName + ' as a function of time'
            - 'Plot selected signals to a multiplots frame (all opened IMAS databases)'
            - 'Plot selected signals to a multiplots frame (this opened IMAS database'
            - 'Select all signals from the same AOS'
            """

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
            # TODO
            # p = PlotSignal(self.dataTreeView, self.nodeData, signal=None,
            #     figureKey=self.currentFigureKey, label=label, xlabel=xlabel,
            #     signalHandling=self)
            # p.execute()

        except ValueError as e:
            self.dataTreeView.log.error(str(e))