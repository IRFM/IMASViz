#  Name   : QVizMultiPlot
#
#          Provides multiplot template.
#          Note: The wxPython predecessor for MultiPlots is
#          'PlotSelectedSignalsWithWxmplot' class.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#****************************************************

# from imasviz.gui_commands.plot_commands.PlotSignal import PlotSignal
# from imasviz.gui_commands.plot_commands.PlotSelectedSignals import PlotSelectedSignals
# from imasviz.plotframes.IMASVIZMultiPlotFrame import IMASVIZMultiPlotFrame
# from imasviz.gui_commands.select_commands.SelectSignals import SelectSignals
# from imasviz.gui_commands.select_commands.UnselectAllSignals import UnselectAllSignals
# from imasviz.util.GlobalOperations import GlobalOperations
# from imasviz.util.GlobalValues import FigureTypes
# from wxmplot.utils import Closure
# from wxmplot.plotpanel import PlotPanel
# import matplotlib.pyplot as plt
from pyqtgraph import GraphicsWindow
from PyQt5.QtWidgets import QMainWindow
import traceback
import sys


class QVizMultiPlot(QMainWindow):
    """Plotting the selected signals with wxmplot to MultiPlot frame.
    """
    def __init__(self, dataTreeView, figureKey=0, update=0,
                 configFile = None, all_DTV = True):
        """
        Arguments:
            dataTreeView (QTreeWidget) : DataTreeView object of the QTreeWidget.
            figurekey (str)  : Frame label.
            update (int)     :
            configFile (str) : System path to the configuration file.
            all_DTV (bool)   : Indicator to read selected signals from single
                               DTV (from the given one) or from all DTVs.
                               Note: This has no effect when reading list
                               of signals from the configuration file.
        """
        super(QVizMultiPlot, self).__init__(parent=dataTreeView)

        self.dataTreeView = dataTreeView

        # Set MultiPlot object name and title if not already set
        if figureKey == None:
            figureKey = self.dataTreeView.imas_viz_api.GetNextKeyForMultiplePlots()
        self.setObjectName(figureKey)
        self.setWindowTitle(figureKey)
        self.dataTreeView.imas_viz_api.figureframes[figureKey] = self

        # Set number of rows and columns of panels in the MultiPlot frame
        self.rows = 2
        self.cols = 3

        # Get the indicator from which DTVs should the signals be read
        # (single or all)
        self.all_DTV = all_DTV

    def raiseErrorIfNoSelectedArrays(self):
        return False

    def getDimension(self):
        plotDimension = "1D"
        return plotDimension

    # TODO
