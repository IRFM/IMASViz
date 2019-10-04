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
from PyQt5.QtGui import QAction, QMenu, QTreeWidgetItem, QMainWindow
from imasviz.VizGUI.VizPlot.QVizPlotConfigUI \
    import QVizPlotConfigUI

from pyqtgraph.exporters.Matplotlib import MatplotlibExporter, Exporter
from pyqtgraph.GraphicsScene.exportDialog import ExportDialog
from pyqtgraph.graphicsItems.PlotItem import PlotItem
from pyqtgraph import functions as fn


class QVizCustomPlotContextMenu(pg.ViewBox):
    """Subclass of ViewBox.
    """

    def __init__(self, qWidgetParent, parent=None):
        """Constructor of the QVizCustomPlotContextMenu

        Arguments:
            qWidgetParent (QWidget) : Parent of ViewBox which is PyQt5 QWidget
                                      object (setting QWidget (PyQt5) as a
                                      regular ViewBox (pyqtgraph) parent doesn't
                                      seem to be allowed).
            parent        (obj)     : Parent.
        """
        super(QVizCustomPlotContextMenu, self).__init__(parent)

        # Set rect mode as default
        # self.setRectMode() # Set mouse mode to rect for convenient zooming

        self.qWidgetParent = qWidgetParent

        # Set original plot context menu
        # Note: self.menu must not be None (this way works fine for plotWidgets,
        # but not for GraphicsWindow (TablePlotView))
        self.menu = pg.ViewBoxMenu.ViewBoxMenu(self)

        # Menu update property
        self.menuUpdate = True

        # Modify list of available exporters (in order to remove the problematic
        # Matplotlib exporter and replace it with ours)
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

class MatplotlibExporterPatched(MatplotlibExporter):
    """ The pyqtgraph 0.10.0 Matplotlib exporter has many issues, one of them are:
            1. When scientific notation is being used the labels any values
              do not match
            2. After closing the matplotlib window whole IMASViz closes (!).
    The issue 2 is already solved in the develop branch of the pyqtgraph
    library but it is unknown when there will be a new release.
    The issue 1 is being acknowledged but it is not yet present not even in the
    develop branch (3.10.2019: https://github.com/pyqtgraph/pyqtgraph/issues/1050#).

    To tackle those issues as general fix is needed now (modifying pyqtgraph
    source code on all HPC machines e.g. ITER HPC and GateWay is not good way
    of solving things), the patched Matplotlib Exporter was provided.

    When and if the required fixes will be released with next pyqtgraph release,
    delete all MatplotlibExporterPatched related code.
    """
    Name = "Matplotlib Window (v2)"

    def __init__(self, item):

        super(MatplotlibExporterPatched, self).__init__(item)

    def export(self, fileName=None):

        if isinstance(self.item, PlotItem):
            mpw = MatplotlibWindowPatched()
            MatplotlibExporter.windows.append(mpw)

            stdFont = 'Arial'

            fig = mpw.getFigure()

            # get labels from the graphic item
            xlabel = self.item.axes['bottom']['item'].label.toPlainText()
            ylabel = self.item.axes['left']['item'].label.toPlainText()
            title = self.item.titleLabel.text

            # pyqtgraph by default uses scientific notation for large
            # values. Matplotlib values and label should reflect that too.
            SIprefix_scale_default = 1.0 # default SI prefix scale value
            SIprefix_scale_bottom = SIprefix_scale_default
            if self.item.axes['bottom']['item'].autoSIPrefix == True:
                SIprefix_scale_bottom = self.item.axes['bottom']['item'].autoSIPrefixScale
            SIprefix_scale_left = SIprefix_scale_default
            if self.item.axes['left']['item'].autoSIPrefix == True:
                SIprefix_scale_left = self.item.axes['left']['item'].autoSIPrefixScale

            ax = fig.add_subplot(111, title=title)
            ax.clear()
            self.cleanAxes(ax)
            #ax.grid(True)
            for item in self.item.curves:
                x, y = item.getData()

                # pyqtgraph by default uses scientific notation for large
                # values. Matplotlib values and label should reflect that too.
                if SIprefix_scale_bottom != SIprefix_scale_default:
                    x = x * SIprefix_scale_bottom
                if SIprefix_scale_left != SIprefix_scale_default:
                    y = y * SIprefix_scale_left

                opts = item.opts
                pen = fn.mkPen(opts['pen'])
                if pen.style() == Qt.NoPen:
                    linestyle = ''
                else:
                    linestyle = '-'
                color = tuple([c/255. for c in fn.colorTuple(pen.color())])
                symbol = opts['symbol']
                if symbol == 't':
                    symbol = '^'
                symbolPen = fn.mkPen(opts['symbolPen'])
                symbolBrush = fn.mkBrush(opts['symbolBrush'])
                markeredgecolor = tuple([c/255. for c in fn.colorTuple(symbolPen.color())])
                markerfacecolor = tuple([c/255. for c in fn.colorTuple(symbolBrush.color())])
                markersize = opts['symbolSize']

                if opts['fillLevel'] is not None and opts['fillBrush'] is not None:
                    fillBrush = fn.mkBrush(opts['fillBrush'])
                    fillcolor = tuple([c/255. for c in fn.colorTuple(fillBrush.color())])
                    ax.fill_between(x=x, y1=y, y2=opts['fillLevel'], facecolor=fillcolor)

                pl = ax.plot(x, y, marker=symbol, color=color, linewidth=pen.width(),
                        linestyle=linestyle, markeredgecolor=markeredgecolor,
                        markerfacecolor=markerfacecolor,
                        markersize=markersize)
                xr, yr = self.item.viewRange()

                # pyqtgraph by default uses scientific notation for large
                # values. Matplotlib values and label should reflect that too.
                if SIprefix_scale_bottom != SIprefix_scale_default:
                    xr = [a*SIprefix_scale_bottom for a in xr]
                if SIprefix_scale_left != SIprefix_scale_default:
                    yr = [a*SIprefix_scale_left for a in yr]

                ax.set_xbound(*xr)
                ax.set_ybound(*yr)
            ax.set_xlabel(xlabel)  # place the labels.
            ax.set_ylabel(ylabel)
            mpw.draw()
        else:
            raise Exception("Matplotlib export currently only works with plot items")

MatplotlibExporterPatched.register()

class MatplotlibWindowPatched(QMainWindow):
    """Intended for MatplotlibExporterPatched.
    """
    def __init__(self):
        from pyqtgraph.widgets import MatplotlibWidget
        QMainWindow.__init__(self)
        self.mpl = MatplotlibWidget.MatplotlibWidget()
        self.setCentralWidget(self.mpl)
        self.show()

    def __getattr__(self, attr):
        return getattr(self.mpl, attr)

    def closeEvent(self, ev):
        MatplotlibExporter.windows.remove(self)
        self.deleteLater()