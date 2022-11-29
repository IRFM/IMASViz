#  Name   : tabQt
#
#           Tab for plugin.
#
#  Author :
#         Ludovic Fleury

#  E-mail :
#         ludovic.fleury@cea.fr
#
# ****************************************************
#     Copyright(c) 2022- L. Fleury

from PyQt5.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QScrollArea, QLayout
from PyQt5.QtCore import Qt, QRect, pyqtSlot
from imasviz.Viz_API import Viz_API
from imasviz.VizPlugins.viz_Profiles.viz_profiles.QVizTablePlotView import QVizTablePlotView


class QVizTab(QWidget):

    def __init__(self, parent=None, tab_page_name=None, filter_index=None, slices_aos_name=None):
        super(QWidget, self).__init__(parent)

        self.layout = None
        self.scrollArea = None
        self.parent = parent
        self.tab_page_name = tab_page_name
        self.filter_index = filter_index
        self.data_entry = self.parent.data_entry
        self.dataTreeView = self.parent.dataTreeView
        self.tab_index = None
        self.signals = None
        self.slices_aos_name = slices_aos_name

    def setTabUI(self, index, tabWidget):
        """Set tab user interface.
        """
        container = QWidget(self)
        self.layout = QVBoxLayout(container)
        self.layout.setSizeConstraint(QLayout.SetFixedSize)
        container.setLayout(self.layout)
        scrollArea = QVizScrollArea(self)
        scrollArea.setWidget(container)
        self.tab_index = tabWidget.insertTab(index, scrollArea, self.tab_page_name)

    def buildPlots(self, multiPlots, signals, plotWidget, strategy):
        multiPlots.plot1D(signals, plotWidget, strategy)
        multiPlots.endOfPlotsProcessing()
        multiPlots.modifySize(len(signals))
        self.layout.addWidget(multiPlots)
        self.signals = signals


class QVizScrollArea(QScrollArea):
    def __init__(self, parent):
        super(QScrollArea, self).__init__(parent)
        self.parent = parent
