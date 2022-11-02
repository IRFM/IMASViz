#  Name   : QVizTablePlotViewForPlugin
#
#          Provides pg.GraphicWindow that contains multiple plot panels in a
#          table layout.
#
#  Author :
#         Ludovic Fleury
#  E-mail :
#         ludovic.fleury@cea.fr
#
# *****************************************************************************
#     Copyright(c) 2022- L. Fleury
# *****************************************************************************

import pyqtgraph as pg
import logging
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QWidget, QScrollArea
from PyQt5.QtCore import Qt
from imasviz.Viz_API import Viz_API
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal import QVizPlotSignal
from imasviz.VizUtils import getRGBColorList, PlotTypes, getScreenGeometry
from .CustomizedViewBox import CustomizedViewBox
from pyqtgraph.graphicsItems.ViewBox import ViewBox


class QVizTablePlotViewForPlugin(pg.GraphicsLayoutWidget):
    """TablePlotView pg.GraphicsWindow containing the plots in a table layout.
    """

    def __init__(self, viz_api, dataTreeView):
        super(QVizTablePlotViewForPlugin, self).__init__()

        self.dataTreeView = dataTreeView
        self.ncols = 3
        self.imas_viz_api = viz_api
        self.figureKey = 0; #TODO

        # # Get screen resolution (width and height)
        self.screenWidth, self.screenHeight = getScreenGeometry()
        # # Set base dimension parameter for setting plot size
        self.plotBaseDim = 50

        # # Set object name and title if not already set
        self.setObjectName("QVizPlugin")
        self.setWindowTitle(str(self.figureKey))

        # # Set number of rows and columns of panels in the TablePlotView frame
        #self.ncols = int(self.screenWidth * 0.7 / self.plotBaseDim)  # round down

        # # Add attribute describing the number of columns
        # # (same as self.centralWidget.rows is for number of rows. Initially
        # # the centralWidget does not contain the 'cols' attribute)
        self.centralWidget.cols = self.ncols

        self.setAntialiasing(True)
        self.setBackground((255, 255, 255))

        #self.modifySize()

        # Enable antialiasing for prettier plots
        pg.setConfigOptions(antialias=True)
        
        self.plotItems = []
        
        self.plotWidget = None
        
    def plot1D(self, plottable_signals, plotWidget, request):

        n = 0
        self.plotWidget = plotWidget
        dtv = self.dataTreeView
        
        for plottable_signal in plottable_signals:
            
            signalNode = plottable_signal[0]
            signal = plottable_signal[1]
            
            print("-->plotting node:" + signalNode.getPath())

            t = QVizPlotSignal.getXAxisValues(signal)
    
            # Get array of y-axis values
            v = QVizPlotSignal.get1DSignalValue(signal)

    
            # Set plot options
            label, xlabel, ylabel, title = \
                signalNode.plotOptions(dataTreeView=dtv,
                                       title=self.figureKey,
                                       plotWidget=self.plotWidget)
        
            # Add plot
            # y-axis values
            u = v[0]
            # x-axis values
            ti = t[0]
            if len(u) != len(ti):
                mess = 'x,y shapes are different, ignoring plot with label:' + label
                print(mess)
                logging.error(mess)
                continue

            currentPlotItem = self.plot(n=n, x=ti, y=u, label=label, xlabel=xlabel,
                     ylabel=ylabel, node=signalNode, request=request)

            #Setting range manually (see IMAS-3658)
            currentPlotItem.setRange(xRange=(min(ti), max(ti)), yRange=(min(u), max(u)))

            # Next plot number
            n+=1
            

    def plot(self, n, x, y, label, xlabel, ylabel, node=None, request=None):
        """Add new plot to TablePlotView pg.GraphicsWindow.

        Arguments:
            n      (int)      : Plot number.
            x      (1D array) : 1D array of X-axis values.
            y      (1D array) : 1D array of Y-axis values.
            label  (str)      : Plot label.
            xlabel (str)      : Plot X-axis label.
            ylabel (str)      : Plot Y-axis label.
        """

        # Set pen
        pen = self.setPen()
        viewBox = CustomizedViewBox(qWidgetParent=self, imas_viz_api=self.imas_viz_api)
        viewBox.id = n
        viewBox.addVizTreeNode(node)
        viewBox.strategy = request.strategy
        title=label.replace("\n", "")
        title = self.imas_viz_api.modifyTitle(title, None, request.slices_aos_name)
        plotItem = self.addPlot(x=x,
                                y=y,
                                pen=pen,
                                title=title,
                                viewBox=viewBox)                                              
        viewBox.addVizTreeNodeDataItems(node, plotItem.listDataItems())
        
        # Get titleLabel
        tLabel = plotItem.titleLabel
        
        # Set title label size
        # Note: empty text provided as requires text argument
        tLabel.setText(text=title, size='6pt')
        
        # Set title width
        # Note: required for alignment to take effect
        tLabel.item.setPlainText(title)
        
        #tLabel.item.setTextWidth(self.plotBaseDim)
        #tLabel.item.setTextWidth(300)
        # Set alignment as text option
        #option = QtGui.QTextOption()
        #option.setAlignment(QtCore.Qt.AlignCenter)
        #tLabel.item.document().setDefaultTextOption(option)
            
        # Set axis labels
        plotItem.setLabel('left', ylabel, units='')
        plotItem.setLabel('bottom', xlabel, units='')

        # Enable grid
        plotItem.showGrid(x=True, y=True)
        # Add a name attribute directly to pg.PlotDataItem - a child of
        # pg.PlotData
        #plotItem.dataItems[0].opts['name'] = label.replace("\n", "")
        plotItem.dataItems[0].opts['name'] = title.replace("\n", "")
        # plotItem.column = int(n / self.centralWidget.cols)
        # plotItem.row = int(n % self.centralWidget.cols)

        viewBox.plotItem = plotItem

        if (n + 1) % self.ncols == 0:
            self.nextRow()
            
        self.plotItems.append(plotItem)
        return plotItem
        
   

    def updatePlot(self, signals):

        #print("len(signals)=", len(signals))
        #print("len(self.plotItems)=", len(self.plotItems))
        
        for i in range(len(self.plotItems)):
            
            plottable_signal = signals[i]
           
            signalNode = plottable_signal[0]
            signal = plottable_signal[1]
            
            #print("-->updating node plot:" + signalNode.getPath())

            t = QVizPlotSignal.getXAxisValues(signal)
            ti = t[0]
    
            # Get array of y-axis values
            v = QVizPlotSignal.get1DSignalValue(signal)
            u = v[0]
            
            
            #dataItem = self.dataItems[i]
            plotItem = self.plotItems[i]
            dataItem = plotItem.listDataItems()[0]
            #print("u=", u)
            dataItem.setData(x=ti, y=u)
            
            #Setting range manually (see IMAS-3658)
            plotItem.setRange(xRange=(min(ti), max(ti)), yRange=(min(u), max(u)))
            
            i+=1
            

    @staticmethod
    def setPen():
        """Set pen (line design) for plot.
        """
        # Set line color
        # - Get list of available global colors (RGB)
        RGBlist = getRGBColorList()
        # - Note: self.RGBlist[0] -> blue color
        color = RGBlist[0]
        # Set style
        style = QtCore.Qt.SolidLine
        # Set pen
        pen = pg.mkPen(color=color, width=3, style=style)

        return pen

    def getCurrentPlotItem(self):
        """Get the current (last) plot item, created by gw.plot().
        """
        if len(self.centralWidget.items.keys()) > 0:
            return list(self.centralWidget.items.keys())[-1]
        return None

    def getPlotItemsDict(self):
        """Return dictionary of GraphicWindow plot items
        (list of pg.DataItem-s).
        """
        return self.centralWidget.items

    def modifySize(self):
        """Modify TablePlotView size.
        (depending on the number of plots and number of columns)
        """

        # Set suitable width and height
        self.okWidth = self.centralWidget.cols * (self.plotBaseDim + 50)
        self.okHeight = len(self.centralWidget.rows) * self.plotBaseDim
        self.setMinimumSize(self.okWidth, self.okHeight)

