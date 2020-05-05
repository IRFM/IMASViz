#  Name   : QVizCustomPlotContextMenu
#
#          Modified plot context menu.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
# *****************************************************************************
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
# *****************************************************************************

import pyqtgraph as pg
from PyQt5.QtGui import QAction
from imasviz.VizGUI.VizPlot.QVizPlotConfigUI \
    import QVizPlotConfigUI

from pyqtgraph.exporters.Matplotlib import Exporter


class QVizCustomPlotContextMenu(pg.ViewBox):
    """Subclass of ViewBox.
    """

    def __init__(self, qWidgetParent, parent=None):
        """Constructor of the QVizCustomPlotContextMenu

        Arguments:
            qWidgetParent (QWidget) : Parent of ViewBox which is PyQt5 QWidget
                                      object (setting QWidget (PyQt5) as a
                                      regular ViewBox (pyqtgraph) parent
                                      doesn't seem to be allowed).
            parent        (obj)     : Parent.
        """
        super(QVizCustomPlotContextMenu, self).__init__(parent)

        # Set rect mode as default
        # self.setRectMode() # Set mouse mode to rect for convenient zooming

        self.qWidgetParent = qWidgetParent

        # Set original plot context menu
        # Note: self.menu must not be None (this way works fine for
        #       plotWidgets, but not for GraphicsWindow (TablePlotView))
        self.menu = pg.ViewBoxMenu.ViewBoxMenu(self)

        # Menu update property
        self.menuUpdate = True

        # Modify list of available exporters (in order to remove the
        # problematic Matplotlib exporter and replace it with ours)
        self.updateExportersList()

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

    def setRectMode(self):
        """Set mouse mode to rect mode for convenient zooming.
        """
        self.setMouseMode(self.RectMode)

    def setPanMode(self):
        """Set mouse mode to pan.
        """
        self.setMouseMode(self.PanMode)

    def showConfigurePlot(self):
        """Set and show custom plot configuration GUI.
        """
        self.plotConfDialog = QVizPlotConfigUI(viewBox=self)
        self.plotConfDialog.show()

    def updateExportersList(self):
        """Update/Modify list of available exporters (in order to remove the
        problematic Matplotlib exporter and replace it with ours).
        """
        # Remove the pyqtgrapth Matplotlib Window and add our Matplotlib Window
        # v2 to the same place on the list (initially it is on the end of the
        # list)
        for exporter in Exporter.Exporters:
            if exporter.Name == 'Matplotlib Window':
                i = Exporter.Exporters.index(exporter)
                del Exporter.Exporters[i]
            if exporter.Name == 'Matplotlib Window (v2)':
                i = Exporter.Exporters.index(exporter)
                Exporter.Exporters.insert(2, Exporter.Exporters.pop(i))
