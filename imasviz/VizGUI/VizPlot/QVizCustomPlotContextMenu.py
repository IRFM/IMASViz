#  Name   : QVizCustomPlotContextMenu
#
#          Modified plot context menu.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#****************************************************

import pyqtgraph as pg
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QAction, QMenu
from imasviz.VizGUI.VizPlot.QVizConfigurePlotWidget \
    import QVizConfigurePlotWidget

class QVizCustomPlotContextMenu(pg.ViewBox):
    """Subclass of ViewBox.
    """
    # signalShowT0 = pyqtSignal()
    # signalShowS0 = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor of the QVizCustomPlotContextMenu
        """
        super(QVizCustomPlotContextMenu, self).__init__(parent)

        # Set rect mode as default
        # self.setRectMode() # Set mouse mode to rect for convenient zooming

        # Set original plot context menu
        # Note: self.menu must not be None (this way works fine for plotWidgets,
        # but not for GraphicsWindow (MultiPlot))
        self.menu = pg.ViewBoxMenu.ViewBoxMenu(self)

        # Menu update property
        self.menuUpdate = True

    def getMenu(self, event=None):
        """Modify the menu. Called by the pyqtgraph.ViewBox raiseContextMenu()
        routine.
        Note: Overwriting the ViewBox.py getMenu() function.
        """

        if self.menuUpdate is True:
            # Modify contents of the original ViewBoxMenu
            for action in self.menu.actions():
                # Modify the original Mouse Mode
                if "Mouse Mode" in action.text():
                    # Change action labels
                    for mouseAction in self.menu.leftMenu.actions():
                        if "3 button" in mouseAction.text():
                            mouseAction.setText("Pan Mode")
                        elif "1 button" in mouseAction.text():
                            mouseAction.setText("Area Zoom Mode")

            # Add custom contents to menu
            self.addCustomToMenu()

            # self.showT0 = QAction('ActionTemplate1', self.menu)
            # self.showT0.triggered.connect(self.emitShowT0)
            # self.showT0.setCheckable(True)
            # self.showT0.setEnabled(True)
            # self.menu.addAction(self.showT0)
            # self.showS0 = QAction('ActionTemplate2', self.menu)
            # self.showS0.setCheckable(True)
            # self.showS0.triggered.connect(self.emitShowS0)
            # self.showS0.setEnabled(True)
            # self.menu.addAction(self.showS0)

            # Set menu update to false
            self.menuUpdate = False

        return self.menu

    def addCustomToMenu(self):
        """Add custom actions to the menu.
        """
        self.menu.addSeparator()
        # Autorange feature
        self.actionAutoRange = QAction("Auto Range", self.menu)
        self.actionAutoRange.triggered.connect(self.autoRange)
        # - Add to main menu
        self.menu.addAction(self.actionAutoRange)

        # Configure plot
        self.actionConfigurePlot = QAction("Configure Plot", self.menu)
        self.actionConfigurePlot.triggered.connect(self.showConfigurePlot)
        # - Add to main menu
        self.menu.addAction(self.actionConfigurePlot)

    # def emitShowT0(self):
    #     """Emit signalShowT0
    #     """
    #     self.signalShowT0.emit()

    # def emitShowS0(self):
    #     """Emit signalShowS0
    #     """
    #     self.signalShowS0.emit()

    def setRectMode(self):
        """Set mouse mode to rect mode for convenient zooming.
        """
        self.setMouseMode(self.RectMode)

    def setPanMode(self):
        """Set mouse mode to pan.
        """
        self.setMouseMode(self.PanMode)

    def showConfigurePlot(self):
        """Show custom plot configuration GUI.
        """
        a = QVizConfigurePlotWidget(viewBox=self)
        a.show()
