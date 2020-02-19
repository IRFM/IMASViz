#  Name   : tabMain0DParam
#
#           "Main 0-D parameters" tab for ETS plugin.
#
#  Author :
#         Dejan Penko
#  E-mail :
#         dejan.penko@lecad.fs.uni-lj.si
#
# ****************************************************
#     Copyright(c) 2019- D. Penko

import inspect
import matplotlib
from matplotlib.figure import Figure
from matplotlib import ticker
from matplotlib.backends.backend_qt5agg import \
    FigureCanvasQTAgg as FigCanvas
from matplotlib.backends.backend_qt5agg import \
    NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import QWidget, QGridLayout


class tabMain0DParam(QWidget):

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)

        self.parent = parent
        # Get/set IDS
        if self.parent.ids is None:
            self.parent.setIDS()
        self.ids = self.parent.ids

        # Get log parser
        self.log = self.parent.getLogger()

        self.parent.writeLogDebug(self, inspect.currentframe(), "START")

        # Set tab user interface
        self.setTabUI()

        # Set initial time slice
        self.it = 0

        self.parent.writeLogDebug(self, inspect.currentframe(), "END")

    def setTabUI(self):

        """Set tab user interface.
        """

        self.parent.writeLogDebug(self, inspect.currentframe(), "START")

        self.setLayout(QGridLayout())
        self.parent.tabWidget.addTab(self, "Main 0-D parameters")

        self.parent.writeLogDebug(self, inspect.currentframe(), "END")

    def plot(self):
        """Main plot function.
        """
        pass

    def plotUpdate(self, time_index):
        """Update data.
        """
        pass
