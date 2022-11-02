#  Name   : tabSummary
#
#           Summary tab for plugin.
#
#  Author :
#         Ludovic Fleury

#  E-mail :
#         ludovic.fleury@cea.fr
#
# ****************************************************
#     Copyright(c) 2022- L. Fleury

from PyQt5.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QScrollArea
from PyQt5.QtCore import Qt, QRect, pyqtSlot
from imasviz.Viz_API import Viz_API
from imasviz.VizPlugins.viz_Profiles.viz_profiles.QVizTablePlotViewForPlugin import QVizTablePlotViewForPlugin

class QVizTab(QWidget):

    def __init__(self, parent=None, tab_page_name=None):
        super(QWidget, self).__init__(parent)

        self.parent = parent
        self.tab_page_name = tab_page_name
        self.data_entry = self.parent.data_entry
        self.dataTreeView = self.parent.dataTreeView

        # Get log parser
        self.log = self.parent.getLogger()
        self.signals = None

    def setTabUI(self, multiPlots, signals, plotWidget):
        """Set tab user interface.
        """

        scrollLayout = QGridLayout()
        self.setLayout(scrollLayout)
        self.parent.tabWidget.addTab(self, self.tab_page_name)
        multiPlots.plot1D(signals, plotWidget, self.parent.request)
        scrollLayout.addWidget(multiPlots)
        self.signals = signals

