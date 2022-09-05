#  Name   : QVizMultiPlotWindow
#
#          Provides a main window for holding widgets/pg.GraphicsWindow that
#          provide display of
#          multiple plot panels in the same window such as Stacked Plot Widget
#          and Table Plot Widget.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
# *****************************************************************************
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
# *****************************************************************************
import logging
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMdiSubWindow
import xml.etree.ElementTree as ET
from imasviz.VizUtils import (FigureTypes, QVizGlobalOperations,
                              getScreenGeometry)
from imasviz.VizGUI.VizConfigurations.QVizSavePlotConfig \
    import QVizSavePlotConfig
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizTablePlotView import QVizTablePlotView
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizStackedPlotView import QVizStackedPlotView


class QVizMultiPlotWindow(QtWidgets.QMainWindow):
    """Main window for holding widgets intended for displaying multiple plots
    in the same window.
    """

    def __init__(self, dataTreeView, figureKey, update=0,
                 configFile=None, all_DTV=False, strategy="DEFAULT"):
        """
        Arguments:
            dataTreeView (QTreeWidget) : DataTreeView object of the QTreeWidget.
            figureKey (str)  : Plot window label that also indicates type of the
                               requested plot view type.
                               The argument can be given in next forms:
                               1.) Specifying full figureKey
                               - 'TablePlotView:0' (can be obtained using
                               VIZ_API.GetNextKeyForTablePlotView())
                               - 'StackedPlotView:0' (can be obtained using
                               VIZ_API.GetNextKeyForStackedPlotView())
                               2.) Specifying only view type and the full key
                               will be obtained by itself:
                               - 'TablePlotView'
                               - 'StackedPlotView'
            update (int)     :
            configFile (str) : System path to the configuration file.
            all_DTV (bool)   : Indicator to read selected signals from single
                               DTV (from the given one) or from all DTVs.
                               Note: This has no effect when reading list
                               of signals from the configuration file.
        """
        super(QVizMultiPlotWindow, self).__init__(parent=dataTreeView)

        self.dataTreeView = dataTreeView
        self.configFile = configFile  # Full path to configuration file + filename
        self.plotConfig = None
        if self.configFile is not None:
            # Set plot configuration dictionary
            self.plotConfig = ET.parse(self.configFile)  # dictionary
            # Set configuration before plotting
            self.applyPlotConfigurationBeforePlotting(plotConfig=self.plotConfig)
        self.imas_viz_api = self.dataTreeView.imas_viz_api

        if self.getNumSignals(all_DTV=all_DTV) < 1:
            logging.warning('QVizMultiPlotWindow: No nodes selected! Aborting '
                            'MultiPlotView creation.')
            return

        # Get screen resolution (width and height)
        self.screenWidth, self.screenHeight = getScreenGeometry()

        # Get the indicator from which DTVs should the signals be read
        # (single or all)
        self.all_DTV = all_DTV

        # Check figureKey argument
        self.figureKey = self.checkFigureKey(figureKey)
        self.imas_viz_api.figureframes[self.figureKey] = self

        # Extract multiPlot type
        multiPlot_type = self.figureKey.split(':')[0]

        # Get a list of required existing DTVs
        self.MultiPlotView_DTVList = self.getDTVList(self.all_DTV)

        # Set Qt object name
        self.setObjectName(self.figureKey)
        # Set main window title
        self.setWindowTitle(self.figureKey)

        # Set multiPlot view (pg.GraphicWindow)
        self.multiPlotView = self.setMultiPlotView(mpType=multiPlot_type,
                                                   strategy=strategy)

        # Embed GraphicsWindow inside scroll area
        scrollArea = self.setPlotViewAsScrollArea(self.multiPlotView)

        # Set GraphicsWindow as central widget
        self.setCentralWidget(scrollArea)

        # Adjust the window and its children size
        self.windowSizeAdjustement()

        # Add menu bar (don't show it for StackedPlotView)
        if 'TablePlotView' in figureKey:
            self.addMenuBar()

        # Connect custom UI elements
        QtCore.QMetaObject.connectSlotsByName(self)

        # If the root window exists, it is assumed that the mandatory MDI
        # exists too. Add the MultiplotWindow to to MDI.
        if self.dataTreeView.window().objectName() == "IMASViz root window":
            subWindow = QMdiSubWindow()
            subWindow.resize(self.width(), self.height())
            subWindow.setWidget(self)
            self.dataTreeView.getMDI().addSubWindow(subWindow)

        # Show the MultiPlot window (either on desktop or in MDI if it was
        # passed there as a subwindow)
        self.show()

    def checkFigureKey(self, figureKey):
        """Check if figure key was properly defined and if it is fully defined.
        """
        if figureKey == None:
            logging.warning('QVizMultiPlotWindow: FigureKey not provided!')
            return
        elif 'TablePlotView' not in figureKey != 'StackedPlotView' not in figureKey:
            # If neither required strings are not found
            logging.warning('QVizMultiPlotWindow: Proper figureKey not '
                            'provided! See class constructor figureKey '
                            'variable description for more information.')
            return

        # Check if figureKey already contains number identification at the end
        # of the name ( e.g. '0' in StackedPlotView:0)
        # If not, get the proper full figureKey
        if figureKey[-1].isdigit() is False:
            if 'TablePlotView' in figureKey:
                figureKey = self.imas_viz_api.GetNextKeyForTablePlotView()
            elif 'StackedPlotView' in figureKey:
                figureKey = self.imas_viz_api.GetNextKeyForStackedPlotView()

        return figureKey

    def setMultiPlotView(self, mpType, strategy='DEFAULT'):
        """Set multiPlotView (pg.GraphicsWindow).

        Arguments:
            multiPlot_type (str) : Type of the multi plot view.
        """

        # Set multi plot view of specified multi plot type
        if mpType == 'TablePlotView':
            mpView = QVizTablePlotView(parent=self, strategy=strategy)
        elif mpType == 'StackedPlotView':
            mpView = QVizStackedPlotView(parent=self, strategy=strategy)
        else:
            logging.error('QVizMultiPlotWindow: proper multiPlot type was not '
                          'provided!')

        # Get a list of viewBoxes each plot has its own associated viewbox)
        self.viewBoxes = mpView.viewBoxList

        # Set mpView title
        mpView.setWindowTitle(self.figureKey)
        # Add mpView to a list of IMASViz figure frames
        # self.imas_viz_api.figureframes[self.figureKey] = mpView
        self.imas_viz_api.figureframes[self.figureKey] = self
        return mpView  # pg.GraphicsWindow

    def getDTVList(self, all_DTV):
        """Get list of required DTVs ('This' or 'All' DTVs) """

        MultiPlotView_DTVList = []

        # If either configuration is provided or all_DTV is set to False,
        # use only single/current DTV.
        # Else if all_DTV is set to True (and not configuration is not
        # provided) use all existing DTVs
        if (self.plotConfig is not None) or (self.all_DTV is False):
            # Add a single (current) DTV to the list
            MultiPlotView_DTVList.append(self.dataTreeView)
        elif self.all_DTV is True:
            # Get the list of all currently opened DTVs
            MultiPlotView_DTVList = self.imas_viz_api.DTVlist

        return MultiPlotView_DTVList

        # if (self.plotConfig != None) != (self.all_DTV == False):

    def raiseErrorIfNoSelectedArrays(self):
        return False

    def getDimension(self):
        plotDimension = "1D"
        return plotDimension

    def setPlotViewAsScrollArea(self, graphicsWindow):
        """Set scrollable graphics window - scroll area contains the graphics
        window.

        Arguments:
            graphicsWindow (pg.GraphicsWindow) : GraphicsWindow containing the
                                              plots (PlotItems).
        """

        # Set scrollable area
        # scrollArea = QtGui.QScrollArea(self)
        scrollArea = QVizStackedPlotViewScrollArea(self)
        scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scrollArea.setWidgetResizable(True)
        scrollArea.setEnabled(True)
        scrollContent = QtGui.QWidget(scrollArea)

        # Set layout for scrollable area
        scrollLayout = QtGui.QVBoxLayout(scrollContent)
        scrollLayout.addWidget(graphicsWindow)
        scrollLayout.setContentsMargins(0, 0, 0, 0)
        scrollContent.setLayout(scrollLayout)
        scrollArea.setWidget(scrollContent)

        return scrollArea

    def windowSizeAdjustement(self):
        """Adjust the size of the main window and its children.
        """

        # Set size of the main window
        width = self.multiPlotView.okWidth + 100
        height = self.multiPlotView.okHeight + 20
        self.resize(width, height)

        # Set main window maximum size
        self.setMaximumSize(self.screenWidth, self.screenHeight)

    def addMenuBar(self):
        """Create and configure the menu bar.
        """
        # Main menu bar
        menuBar = QtWidgets.QMenuBar(self)
        options = menuBar.addMenu('Options')
        # ---------------------------------------------------------------------
        # Set new menu item for saving plot configuration
        action_onSavePlotConf = QtWidgets.QAction('Save Plot Configuration',
                                                  self)
        action_onSavePlotConf.triggered.connect(self.onSavePlotConf)
        options.addAction(action_onSavePlotConf)

        # Set menu bar
        self.setMenuBar(menuBar)

    def getNumSignals(self, all_DTV=True):
        """Get number of signals intended for the TablePlotView and
           StackedPlotView feature from either opened DTVs or from
           configuration file if it is loaded.
        """
        if self.plotConfig is not None:
            # Get number of signals through number of signal paths
            pathsList = QVizGlobalOperations.\
                getSignalsPathsFromConfigurationFile(self.configFile)
            nSignals = len(pathsList)
        else:
            # If plotConfig is not present (save configuration was
            # not used)
            if all_DTV is True:
                nSignals = \
                    len(self.imas_viz_api.GetSelectedSignalsDictFromAllDTVs())
            elif all_DTV is False:
                nSignals = \
                    len(self.imas_viz_api.GetSelectedSignalsDict(self.dataTreeView.parent))

        return nSignals

    # def setRowsColumns(self, num_signals):
    #     """Modify the TablePlotView rows and columns depending on total number
    #     of signals."""
    #         if num_signals > 6:
    #             if num_signals <= 8:
    #                 self.rows = 2
    #                 self.cols = 4
    #             elif num_signals > 8 and num_signals <= 12:
    #                 self.rows = 3
    #                 self.cols = 4
    #             elif num_signals > 12:
    #                 self.rows = 3
    #                 self.cols = 4
    #                 print('TablePlotView plot limit reached (12)!')

    def onHideFigure(self, api, figureKey):
        """

        Arguments:
            api       (obj)  : IMASViz Application Programming Interface.
            figurekey (str)  : Frame label.
        """
        if figureKey in api.GetFiguresKeys(figureType=FigureTypes.TABLEPLOTTYPE):
            api.figureframes[figureKey].hide()

    def getScreenGeometry(self):
        """Get screen geometry.
        Note: QApplication instance required / application must be running.
        """
        QtWidgets.QApplication.instance().desktop().screenGeometry()

    def getPlotItemsDict(self):
        """Return dictionary of GraphicWindow plot items."""
        return self.multiPlotView.centralWidget.items

    @QtCore.pyqtSlot()
    def onSavePlotConf(self):
        """Save configuration for single DTV.
        """
        QVizSavePlotConfig(gWin=self.multiPlotView).execute()

    def applyPlotConfigurationAfterPlotting(self, plotItem):
        """Apply configuration (from configuration file) to plot item after
        # it was created.

        Arguments:
            plotItem (pg.PlotItem) : Plot item to which the configuration is to
                                     be applied.
        """
        from ast import literal_eval

        logging.info('Applying plot configuration after plotting to plot '
                     'view column ' + str(plotItem.column) + ' row ' +
                     str(plotItem.row))

        # TODO: Browsing through plotConfig is done also in
        # selectSignalsFromConfig(). It would be good to create a common
        # function for that purposes

        # Get main 'GraphicsWindow' element
        graphicsWindowEl = self.plotConfig.find('GraphicsWindow')
        # Get a list of PlotItem elements
        plotItemElements = graphicsWindowEl.findall('PlotItem')
        # Get number of plot panels (pg.PlotItem-s)
        num_plotItems = len(plotItemElements)

        # Go through pg.PlotItems
        for pItemElement in plotItemElements:
            # Get key attribute (key=(column,row))
            key = pItemElement.get('key')

            # Set configuration for PlotItem that matches the key (columnt/row)
            if str(key) == str((plotItem.column, plotItem.row)):
                # Get a list of pg.PlotDataItems
                # Note: Only one per TablePlotView PlotItem
                plotItemDataElements = pItemElement.findall('PlotDataItem')
                # Get number of plots (pg.PlotDataItem-s)
                num_plots = len(plotItemDataElements)
                # Go through pg.PlotdataItems / plots / lines
                pdi = 0
                for pdItemElement in plotItemDataElements:

                    # Get pg.PlotDataItem
                    pdItem = plotItem.dataItems[pdi]
                    # get opts attribute of the pg.PlotDataItem
                    opts = pdItem.opts
                    # Find opts element in configuration
                    optsConfig = pdItemElement.find('opts')
                    # Set opts configuration
                    # TODO: resolve the configurations that are returning error
                    #       or the type is not know (as those configurations
                    #       were not yet actively used)
                    # TODO: create separate functions that converts the
                    #       element attribute value (always string) to correct
                    #       type

                    # opts['connect'] = optsConfig.get('connect') # error
                    # - Set fftMode by checking if string 'True' is present as
                    #   element attribute. If not 'True' then bool False is
                    #   returned
                    opts['fftMode'] = 'True' in optsConfig.get('fftMode')
                    # - Set logMode by converting attribute  (string) to list
                    opts['logMode'] = literal_eval(optsConfig.get('logMode'))
                    # - Set alphaHint by converting attribute  (string) to float
                    opts['alphaHint'] = float(optsConfig.get('alphaHint'))
                    # - Set alphaMode by checking if string 'True' is present as
                    #   element attribute. If not 'True' then bool False is
                    #   returned
                    opts['alphaMode'] = 'True' in optsConfig.get('alphaMode')
                    # opts['shadowPen'] = tuple(optsConfig.get('shadowPen')) # unknown type
                    # opts['fillLevel'] = literal_eval(optsConfig.get('fillLevel')) # unknown type
                    # opts['fillBrush'] = optsConfig.get('fillBrush') # unknown type
                    # opts['stepMode'] = optsConfig.get('stepMode') # unknown type
                    # - Set symbol. If attribute is 'None' then skip
                    if optsConfig.get('symbol') != 'None':
                        opts['symbol'] = optsConfig.get('symbol')

                    # - Set symbolSize by converting attribute  (string) to float
                    opts['symbolSize'] = float(optsConfig.get('symbolSize'))

                    # - Set symbolPen by converting attribute  (string) to list
                    opts['symbolPen'] = literal_eval(optsConfig.get('symbolPen'))
                    # - Set symbolBrush by converting attribute  (string) to list
                    opts['symbolBrush'] = literal_eval(optsConfig.get('symbolBrush'))
                    # - Set pxMode by checking if string 'True' is present as
                    #   element attribute. If not 'True' then bool False is
                    #   returned
                    opts['pxMode'] = 'True' in optsConfig.get('pxMode')
                    # # opts['antialias'] = bool(optsConfig.get('antialias')) # error
                    # opts['pointMode'] = optsConfig.get('pointMode') # unknown type
                    # - Set downsample by converting attribute  (string) to int
                    opts['downsample'] = int(optsConfig.get('downsample'))
                    # - Set autoDownsample by checking if string 'True' is present as
                    #   element attribute. If not 'True' then bool False is
                    #   returned
                    opts['autoDownsample'] = 'True' in optsConfig.get('autoDownsample')
                    # - Set downsampleMethod (string)
                    opts['downsampleMethod'] = optsConfig.get('downsampleMethod')
                    # - Set autoDownsampleFactor by converting attribute  (string) to float
                    opts['autoDownsampleFactor'] = float(optsConfig.get('autoDownsampleFactor'))
                    # - Set clipToView by checking if string 'True' is present as
                    #   element attribute. If not 'True' then bool False is
                    #   returned
                    opts['clipToView'] = 'True' in optsConfig.get('clipToView')
                    # opts['data'] = optsConfig.get('data') # unknown type
                    # - Set name (string)
                    opts['name'] = optsConfig.get('name')

                    # - Set pen configuration
                    optsPen = opts['pen']
                    #   - Find pen element from configuration
                    optsPenConfig = optsConfig.find('pen')
                    #   - Set pen color and alpha by converting attribute
                    #     (string) to int list (RBGA)
                    rgba = literal_eval(optsPenConfig.find('QColor').get('colorRGB'))
                    qcolor = QtGui.QColor(rgba[0], rgba[1], rgba[2], rgba[3])
                    optsPen.setColor(qcolor)
                    #   - Set pen style by converting attribute  (string) to int
                    #     Note: As for example, Qt.SolidLine == 1
                    optsPen.setStyle(int(optsPenConfig.get('Qt.PenStyle')))
                    #   - Set pen cap style by converting attribute  (string) to
                    #     int
                    optsPen.setCapStyle(int(optsPenConfig.get('Qt.PenCapStyle')))
                    #   - Set pen join by converting attribute  (string) to int
                    optsPen.setJoinStyle(int(optsPenConfig.get('Qt.PenJoinStyle')))
                    #   - Set pen width by converting attribute  (string) to
                    #     float
                    optsPen.setWidth(float(optsPenConfig.get('widthF')))

                    # TODO: Pen Brush (is it required?) dashOffset, isCosmetic,
                    #       isSolid and miterLimit

                    # TODO: Axis part

                    # Update items for the changes to be displayed
                    pdItem.updateItems()

    def applyPlotConfigurationBeforePlotting(self, plotConfig=None):
        pass

    def getDTV(self):
        return self.dataTreeView

    def getAllDTV(self):
        return self.all_DTV

    def getPlotConfig(self):
        return self.plotConfig

    def getIMASVizAPI(self):
        return self.imas_viz_api

    def getLog(self):
        return logging

    def getFigureKey(self):
        return self.figureKey

    def getMDI(self):
        """ Get MDI area through the root IMASViz main window.
        """
        if self.window().objectName() == "IMASViz root window":
            return self.window().getMDI()
        return None

    # TODO
    # def setPlotConfigAttribute


class QVizStackedPlotViewScrollArea(QtWidgets.QScrollArea):
    """Custom QtGui.QScrollArea.
    """

    def __init__(self, parent):
        QtGui.QScrollArea.__init__(self, parent=parent)

    def wheelEvent(self, ev):
        """Disable mouse scroll event.
        """
        if ev.type() == QtCore.QEvent.Wheel:
            ev.ignore()
