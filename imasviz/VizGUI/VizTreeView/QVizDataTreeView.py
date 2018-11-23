#  Name   :IDSTree
#
#          Container to create IDS Tree View structure in PyQt5.
#          Note: The wxPython predecessor of this Python file is
#          WxDataTreeView.py
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#  TODO:
#
#    - Function definitions (from WxDataTreeView to QVizDataTreeView class)
#       def onMouseEvent(...):
#       def OnShowPopup(...):
#
#    - Function definitions (from WxDataTreeViewFrame to QVizDataTreeViewFrame
#      class)
#       def onClose(...):
#       def onUnselectSignals(...):
#       def onCloseAndReopenDatabase(...):
#       def updateView(...):
#
#    - class TextCtrlLogger definition
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic,L.xinyi, D. Penko
#****************************************************

import os
import xml.etree.ElementTree as ET
from functools import partial

from PyQt5.QtCore import Qt, QSize, pyqtSlot, QMetaObject
from PyQt5.QtWidgets import QDockWidget, QMenuBar, QAction
from PyQt5.QtWidgets import QMainWindow, QTreeWidget, QTreeWidgetItem, \
    QWidget, QGridLayout, QTextEdit

from imasviz.VizGUI.VizConfigurations.QVizConfigurationListsWindow \
    import QVizConfigurationListsWindow
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSaveSignalSelection \
    import QVizSaveSignalSelection
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizHandleRightClick \
    import QVizHandleRightClick
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPreviewPlotWidget \
    import QVizPreviewPlotWidget
from imasviz.VizGUI.VizTreeView.QVizDataTreeViewBuilder import QVizDataTreeViewBuilder
from imasviz.VizGUI.VizWidgets.QVizNodeDocumentationWidget \
    import QVizNodeDocumentationWidget
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues, GlobalIDs, GlobalColors
from imasviz.VizUtils.QVizWindowUtils import getWindowSize
from imasviz.VizGUI.VizTreeView.QVizTreeNode import QVizTreeNode
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizUnselectAllSignals \
    import QVizUnselectAllSignals


class QVizDataTreeView(QTreeWidget):
    """Set and populate QTreeWidget.
    """

    def __init__(self, parent, dataSource, mappingFilesDirectory,
                 IDSDefFile, *args, **kwargs):
        """
        Arguments:
            parent     (QWindow)            : QVizDataTreeView parent.
            dataSource (QVizIMASDataSource) : IDS data source from QVizDataSourceFactory
            mappingFilesDirectory (str)     : Path to IMASViz mapping files directory
                                          (example: viz/ts_mapping_files)
            IDSDefFile (str)                : Path to IDS dictionary definition .xml
                                          file (example:
                                          viz/imas_data_dictionaries/IDSDef_{IMAS_VERSION}.xml)
        """
        super(QVizDataTreeView, self).__init__(parent)

        # Set QTreeWidget name
        self.setObjectName('DTV')

        # Set custom popup menu. Will run the contextMenuEvent() function
        self.setContextMenuPolicy(Qt.DefaultContextMenu)
        # Hide header
        self.setHeaderHidden(True)

        # Connect 'itemClicked' with the 'onLeftClickItem' function.
        # On clicking on the QTreeWidgetItem (left click) the function will
        # be run
        self.itemClicked.connect(self.onLeftClickItem)

        self.dataSource = dataSource
        self.idsNamesList = []
        self.idsAlreadyFetched = {}
        self.selectedItem = None
        self.shotNumber = dataSource.shotNumber
        self.runNumber = dataSource.runNumber
        self.mappingFilesDirectory = mappingFilesDirectory

        # Create a IDS root node with each shotnumber
        self.DTVRoot = QVizTreeNode(self, ['IDSs' + '(' + str(dataSource.shotNumber) + ')'])

        # #Dictionary where each element is also a dictionary containing
        # self.dataTreeView.selectedSignalsDict[key] = \
        #     {'index': index,
        #      'QTreeWidgetItem': self.dataTreeView.selectedItem,
        #      'shotNumber': self.dataTreeView.dataSource.shotNumber,
        #      'runNumber': self.dataTreeView.dataSource.runNumber,
        #      'imasDbName': self.dataTreeView.dataSource.imasDbName,
        #      'userName': self.dataTreeView.dataSource.userName}
        self.selectedSignalsDict = {}

        # List of all nodes which contain a signal (all FLT_1D nodes etc.)
        self.signalsList = []

        # Parent of this tree, this is the wxDataTreeViewFrame
        self.parent = parent

        # Keep a reference to shared data (frames, figures, ...)
        # - This is a BrowserAPI instance
        self.viz_api = None

        # key = idsName, value = root node (of type QVizTreeNode) of the IDS tree
        self.IDSRoots = {}

        # Create the empty tree
        self.createEmptyIDSsTree(IDSDefFile)

        self.log = None

        # Set dummy for node documentation widget
        self.ndw = None

        # contains root nodes for each IDS occurrence
        self.ids_roots_occurrence = {}

        # key=occurrence, value=IDS name
        self.IDSNameSelected = {}

    def createEmptyIDSsTree(self, IDSDefFile):
        """The tree is created from CPODef.xml or IDSDef.xml file.
        Note: The original routine source (ues with wxPython) can be found in
        viz/imasviz/view/WxDataTreeView.py
        """
        idsNode = None
        tree = ET.parse(IDSDefFile)
        # Add the node information to each IDS node
        returnedDict = {}
        for child in tree.getroot():
            if (child.tag == 'IDS'):
                """Extract IDS properties from IDSDef.xml file"""
                """Get IDS name"""
                idsName = child.get('name')
                """Get IDS documentation"""
                idsDocumentation = child.get('documentation')
                self.idsNamesList.append(idsName)
                self.idsAlreadyFetched[idsName] = 0

                """Set array holding IDS properties"""
                itemDataDict = {}
                itemDataDict['IDSName'] = idsName
                itemDataDict['isIDSRoot'] = 1
                itemDataDict['dataName'] = idsName
                itemDataDict['isSignal'] = 0
                itemDataDict['isSelected'] = 0
                itemDataDict['Tag'] = idsName
                itemDataDict['Path'] = itemDataDict['Tag']
                itemDataDict['availableIDSData'] = 0
                itemDataDict['documentation'] = idsDocumentation
                # Add the IDS node as a tree item to the tree view
                self.IDSRoots[idsName] = QVizTreeNode(self.DTVRoot, [idsName], itemDataDict)
                if self.dataSource.exists(idsName) == 1:
                    # - If there is any data available from the IDS, change set
                    # its dictionary 'availableIDSData' value from 0 to 1 and
                    # color its item text (IDS name) to blue
                    itemDataDict['availableIDSData'] = 1
                    # Set tree item text color
                    self.IDSRoots[idsName].setForeground(0, GlobalColors.BLUE)

    def setSelectedItem(self, item, mouseButton=None):
        """Set selected item.
        Optional: Beside setting the base selected item, set selected item
        explicitly obtained by either left click (marked with blue fill in DTV)
        or right click (on showing the context menu).

        Arguments:
            item        (QTreeWidgetItem) : QTreeWidgetItem object.
            mouseButton (str)             : Define the mouse button clicked on
                                            the QTreeWidgetItem.
                                            Options:
                                            - 'LEFT' for left click
                                            - 'RIGHT' for right click
        """

        # Set base selected item variable
        self.selectedItem = item
        # Set selected item variable obtained by left/right click on the
        # QTreeWidgetItem
        if mouseButton != None:
            if mouseButton == "LEFT":
                self.selectedItem_leftClick = item
            elif mouseButton == "RIGHT":
                self.selectedItem_rightClick = item

    def isAlreadyFetched(self, IDSName, occurrence):
        # occurrence of IDS with name IDSName already loaded ?
        key = IDSName + "/" + str(occurrence)
        if self.ids_roots_occurrence.get(key) is not None:
            return True
        return False

    # Note: pyqtSlot needs QObject to work, in this case, self=QTreeWidget
    # (inherited)
    @pyqtSlot(QTreeWidgetItem, int)
    def onLeftClickItem(self, item, column):
        """ Action to execute upon left clicking on DTV item.

        Arguments:
            item   (QTreeWidgetItem) : QTreeWidgetItem object.
            column (int)             : Item column.
        """

        # Check if item has the 'itemVIZData' attribute. If not -> return
        if item.getDataName() is not None:
            pass
        else:
            return

        # Set selected QTreeWidgetItem on left click
        # (marked with blue fill color in DTV)
        self.setSelectedItem(item=item, mouseButton="LEFT")

        # UPDATE NODE DOCUMENTATION WIDGET
        # - Set node label
        node_label = "..."    # Assigning default label
        if (item.getDataName() is not None):
            node_label = str(item.getDataName())
        elif (item.getName() is not None):
            node_label = str(item.getName())
        # - Set node documentation#
        node_doc = str(item.getDocumentation())

        # - Set all node documentation related strings to single
        # string array for better handling
        node_doc_str_array = []
        node_doc_str_array.append("Node: ")
        node_doc_str_array.append(node_label)
        node_doc_str_array.append("Documentation: ")
        node_doc_str_array.append(node_doc)

        # Find and update DTVFrame-docked node documentation widget (NDW)
        ndw = self.parent.findChild(QWidget, "QVizNodeDocumentationWidget")
        if ndw != None:
            ndw.update(documentation=node_doc_str_array)
        else:
            error = 'Node Documentation Widget not found. Update not possible'
            raise ValueError(error)
            self.log.error(str(error))

        # UPDATE PLOT PREVIEW WIDGET
        if (item.isDynamicData() == 1 and
            item.getDataType() == 'FLT_1D' and
            (item.foreground(0).color().name() == GlobalColors.BLUE_HEX or
             item.foreground(0).color().name() == GlobalColors.RED_HEX)):
            # If the node holds an 1D array of values (1D_FLT) then its
            # isSignal attribute equals 1 (isSignale = 1)

            # Set and show preview panel
            QVizSignalHandlingObj = QVizSignalHandling(dataTreeView=self)
            QVizSignalHandlingObj.plotPreviewSignalCommand()

    def contextMenuEvent(self, event):
        """ Custom menu event on the right click on the tree item.
        """
        # print(event)
        if len(self.selectedItems()) == 1:
            # The selected item
            item = self.selectedItems()[0]  # QTreeWidgetItem object

            # Set selected QTreeWidgetItem on right click
            self.setSelectedItem(item=item, mouseButton="RIGHT")

            # Get position
            self.pos = event.pos()

            # TODO
            handleRightClick = QVizHandleRightClick(self)
            showPopUp = handleRightClick.execute(item)

    def update_view(self, idsName, occurrence, idsData):
        """ Update the tree view with the data.
        """
        self.idsAlreadyFetched[idsName] = 1
        #ids_root_node = self.IDSRoot[idsName]
        if idsData != None:
            self.buildTreeView(self.IDSRoots[idsName], occurrence, idsData)
            # Expand the tree item
            self.DTVRoot.setExpanded(True)

    def buildTreeView(self, ids_root_node, occurrence, idsData):
        """ Build the data tree view by adding a set of available IDS nodes as
            an items to it.

        Arguments:
            ids_root_node (QTreeWidgetItem) : IDS root tree widget item
                                              (Example: magnetics IDS root node)
            occurrence    (int)             : IDS occurrence number (0-9).
            idsData       (obj)             : Object (element) holding IDS data.
        """
        rootNodeData = ids_root_node.getDataDict()

        idsName = ids_root_node.getIDSName()
        key = idsName + "/" + str(occurrence)

        occNodeData = rootNodeData
        occNodeData['occurrence'] = occurrence
        nodeBuilder = QVizDataTreeViewBuilder()
        ids_root_occ = QVizTreeNode(ids_root_node, ['occurrence ' + str(int(occurrence))], occNodeData)
        self.ids_roots_occurrence[key] = ids_root_occ

        for child in idsData:
            self.addChildren(nodeBuilder, child, ids_root_occ, idsName, occurrence)

    def addChildren(self, nodeBuilder, element, parent, idsName, occurrence):
        """ To parent item, add all children IDS nodes as a tree view items.

        Arguments:
            nodeBuilder (QVizDataTreeViewBuilder) : Class QVizDataTreeViewBuilder
                                                    object.
            element     (obj)             : idsData child element.
            parent      (QTreeWidgetItem) : Parent tree view item to which the
                                            child is to be added.
            idsName     (str)             : Name of the IDS e.g. 'magnetics'.
        """
        element_node = nodeBuilder.addNewNode(idsName, element, parent,
                                              occurrence, self)
        if element_node != None:
            for child in element:
                self.addChildren(nodeBuilder, child, element_node, idsName,
                                 occurrence)

    def OnExpandItem(self, event):
        return

    def OnCollapseItem(self, event):
        return


class QVizDataTreeViewFrame(QMainWindow):
    """ Set QMainWindow to contain the QTreeWidget.
    """

    def __init__(self, parent, views, dataSource, IDSDefFile, imas_viz_api, *args, **kwargs):
        """
        Arguments:
            parent     (PyQT obj)           : QVizDataTreeView parent.
            views      (array)              :
            dataSource (QVizIMASDataSource) : IDS data source from
                                              QVizDataSourceFactory
            IDSDefFile (str)                : Path to IDS dictionary definition
                                              .xml file (example:
                                              viz/imas_data_dictionaries/IDSDef_{IMAS_VERSION}.xml)
        """
        super(QVizDataTreeViewFrame, self).__init__(parent, *args, **kwargs)

        # Set empty list of configuration windows
        self.configurationListsWindow = None

        # Basic settings (QMainWindow)
        self.resize(800, 800)

        # Set Data Tree View Window name
        self.setObjectName('DTV Window')

        # Set title (QMainWindow)
        publicStr = ''
        if dataSource.name == QVizGlobalValues.IMAS_UDA:
            publicStr = "public "
            self.setWindowTitle("'" + dataSource.machineName + "' " + publicStr
                                + "data source, shot="
                                + str(dataSource.shotNumber) + ", run="
                                + str(dataSource.runNumber))
        else:
            self.setWindowTitle("'" + dataSource.imasDbName + "' "
                                + "data source, shot="
                                + str(dataSource.shotNumber) + ", run="
                                + str(dataSource.runNumber))

        # Set Qt TreeView
        self.dataTreeView = \
            QVizDataTreeView(parent=self,
                             dataSource=dataSource,
                             mappingFilesDirectory=os.environ['TS_MAPPINGS_DIR'],
                             IDSDefFile=IDSDefFile)
        self.dataTreeView.imas_viz_api = imas_viz_api

        # Set custom event type (ID)
        self.eventResultId = GlobalIDs.RESULT_EVENT

        # TreeView settings
        self.dataTreeView.setColumnWidth(0, 150)
        self.dataTreeView.setAlternatingRowColors(True)
        self.dataTreeView.setUniformRowHeights(True)
        self.dataTreeView.expandsOnDoubleClick()
        # self.dataTreeView.resize(400,500)
        self.setCentralWidget(self.dataTreeView)

        # Set and add dock widgets to QMainWindow
        self.addDockWidgets()

        # Set and add menu bar
        self.addMenuBar()

        # Connect custom UI elements
        QMetaObject.connectSlotsByName(self)

        # Old wx variable label. Remove when obsolete
        self.view = self.dataTreeView

    def event(self, event):
        """ Listen to events.
        """
        # print(event)
        # print(event.type())
        if event.type() == GlobalIDs.RESULT_EVENT:
            self.onResult(event)
        return super(QVizDataTreeViewFrame, self).event(event)

    def onResult(self, event):
        """ Set data obtained on event (event.type() == GlobalIDs.RESULT_EVENT).
        """
        idsName = event.data[0]
        occurrence = event.data[1]
        idsData = event.data[2]
        pathsList = event.data[3]
        threadingEvent = event.data[4]
        self.updateView(idsName, occurrence, idsData, pathsList, threadingEvent)

    def updateView(self, idsName, occurrence, idsData=None, pathsList=None,
                   threadingEvent=None):
        """ Update QVizDataTreeViewFrame.

        Arguments:
            idsName        (str) : Name of the IDS e.g. 'magnetics'.
            occurrence     (int) : IDS occurrence number (0-9).
            idsData        (obj) : Object (element) holding IDS data.
            pathsList      () :
            threadingEvent () :
        """
        # t4 = time.time()
        if idsData != None:
            self.dataTreeView.log.info("Loading occurrence "
                                       + str(int(occurrence))
                                       + " of " + idsName
                                       + " IDS ended successfully, building "
                                       + " view...")
            self.dataTreeView.update_view(idsName, occurrence, idsData)
            self.dataTreeView.log.info("View update ended.")

            if (idsName == 'equilibrium'):
                self.dataTreeView.log.info("WARNING: GGD structure array from "
                                           + "parent "
                                           + "equilibrium.time_slice[itime] "
                                           + "has been ignored.")

    def addMenuBar(self):
        """Create and configure the menu bar.
        """
        # Main menu bar
        menuBar = QMenuBar(self)
        # Set Options menu
        actions = menuBar.addMenu('Actions')
        #-----------------------------------------------------------------------
        # Set new menu item for showing the Configuration window
        action_onShowConfigurations = QAction('Apply Configuration', self)
        action_onShowConfigurations.triggered.connect(
            partial(self.onShowConfigurations, self))
        actions.addAction(action_onShowConfigurations)
        #-----------------------------------------------------------------------

        # Set menu handling node selection features
        nodeSelection = menuBar.addMenu('Node Selection')
        #-----------------------------------------------------------------------
        # Set new submenu for handling signal selection to be added to 'Actions'
        # menu
        # subMenu_select = nodeSelection.addMenu('Signal Selection Options')

        action_onSaveSignalSelection = QAction('Save Node Selection', self)
        action_onSaveSignalSelection.triggered.connect(self.onSaveSignalSelection)
        nodeSelection.addAction(action_onSaveSignalSelection)

        # -----
        # Add menu item to unselect all signals - This/Current DTV
        subMenu_unselect = nodeSelection.addMenu('Unselect Nodes')
        action_onUnselectSignals = QAction('This IMAS Database',
                                           self)
        action_onUnselectSignals.triggered.connect(
            partial(QVizSignalHandling(self.dataTreeView).onUnselectSignals, False))
        # Add to submenu
        subMenu_unselect.addAction(action_onUnselectSignals)

        # -----
        # Add menu item to unselect all signals - All DTVs
        action_onUnselectSignals = QAction('All IMAS Databases',
                                           self)
        action_onUnselectSignals.triggered.connect(
            partial(QVizSignalHandling(self.dataTreeView).onUnselectSignals, True))
        # Add to submenu
        subMenu_unselect.addAction(action_onUnselectSignals)

        #-----------------------------------------------------------------------
        subMenu_multiPlot = nodeSelection.addMenu('Create MultiPlot')

        # Set new submenu for handling TablePlotViews
        subMenu_tablePlotView = subMenu_multiPlot.addMenu('TablePlotView')
        subMenu_tablePlotView_set = subMenu_tablePlotView.addMenu(
            'Plot all selected signals to a new TablePlotView')

        # -----
        # Add menu item to plot selected signals to single
        # plot - This DTV
        action_setTablePlotView = QAction('This IMAS Database',
                                          self)
        action_setTablePlotView.triggered.connect(
            partial(QVizSignalHandling(self.dataTreeView).onPlotToTablePlotView, False))
        # Add to submenu
        subMenu_tablePlotView_set.addAction(action_setTablePlotView)

        # -----
        # Add menu item to plot selected signals to single
        # plot - All DTVs
        action_setTablePlotViewAll = QAction('All IMAS Databases',
                                             self)
        action_setTablePlotViewAll.triggered.connect(
            partial(QVizSignalHandling(self.dataTreeView).onPlotToTablePlotView, True))
        # Add to submenu
        subMenu_tablePlotView_set.addAction(action_setTablePlotViewAll)

        #-----------------------------------------------------------------------
        # Set new submenu for handling StackedPlotViews
        subMenu_stackedPlotView = subMenu_multiPlot.addMenu('StackedPlotView')
        subMenu_stackedPlotView_set = subMenu_stackedPlotView.addMenu(
            'Plot all selected signals to a new StackedPlotView')

        # -----
        # Add menu item to plot selected signals to single
        # plot - This DTV
        action_stackedPlotView = QAction('This IMAS Database',
                                         self)
        action_stackedPlotView.triggered.connect(
            partial(QVizSignalHandling(self.dataTreeView).onPlotToStackedPlotView, False))
        # Add to submenu
        subMenu_stackedPlotView_set.addAction(action_stackedPlotView)

        # -----
        # Add menu item to plot selected signals to single
        # plot - All DTVs
        action_stackedPlotViewAll = QAction('All IMAS Databases',
                                            self)
        action_stackedPlotViewAll.triggered.connect(
            partial(QVizSignalHandling(self.dataTreeView).onPlotToStackedPlotView, True))
        # Add to submenu
        subMenu_stackedPlotView_set.addAction(action_stackedPlotViewAll)

        # Set menu bar
        self.setMenuBar(menuBar)

    def addDockWidgets(self):
        """Add dockable widgets to DTV frame main window.
        """

        # Get reference parameters
        # - DTV frame width and height
        ref_width, ref_height = getWindowSize(self)

        # PREVIEW PLOT WIDGET (PPW)
        # - Set the widget
        self.previewPlotWidget = QVizPreviewPlotWidget(parent=self,
                                                       title='Preview Plot')
        # - Plot empty
        self.previewPlotWidget.plot()
        # - Dock the widget
        self.dockWidget_ppw = QDockWidget("Preview Plot", self)
        self.dockWidget_ppw.setFeatures(QDockWidget.DockWidgetFloatable)
        self.dockWidget_ppw.setObjectName("DockWidget_PPW")
        self.dockWidgetContents_ppw = QWidget()
        self.dockWidgetContents_ppw.setObjectName("DockWidgetContents_PPW")
        self.gridLayout_ppw = QGridLayout(self.dockWidgetContents_ppw)
        self.gridLayout_ppw.setObjectName("GridLayout_PPW")
        self.gridLayout_ppw.addWidget(self.previewPlotWidget, 0, 0, 1, 1)
        self.dockWidget_ppw.setWidget(self.dockWidgetContents_ppw)
        # - Set dockwidget size
        self.dockWidget_ppw.setMinimumSize(QSize(ref_width / 2, ref_height / 2))
        self.addDockWidget(Qt.DockWidgetArea(2), self.dockWidget_ppw)

        # NODE DOCUMENTATION WIDGET (NDW)
        # - Set the widget with default text
        self.nodeDocumentationWidget = QVizNodeDocumentationWidget(parent=self)
        # - Add the widget to dockwidget
        self.dockWidget_ndw = QDockWidget("Node documentation", self)
        self.dockWidget_ndw.setFeatures(QDockWidget.DockWidgetFloatable)
        self.dockWidget_ndw.setObjectName("DockWidget_NDW")
        self.dockWidgetContents_ndw = QWidget()
        self.dockWidgetContents_ndw.setObjectName("DockWidgetContents_NDW")
        self.gridLayout_ndw = QGridLayout(self.dockWidgetContents_ndw)
        self.gridLayout_ndw.setObjectName("GridLayout_NDW")
        self.gridLayout_ndw.addWidget(self.nodeDocumentationWidget, 0, 0, 1, 1)
        self.dockWidget_ndw.setWidget(self.dockWidgetContents_ndw)
        # - Set dockwidget size
        self.dockWidget_ndw.setMinimumSize(QSize(ref_width / 2, ref_height / 4))
        self.addDockWidget(Qt.DockWidgetArea(2), self.dockWidget_ndw)

        # LOG WIDGET
        self.logWidget = QTextEdit(parent=self)
        self.logWidget.setReadOnly(True)
        self.dockWidget_log = QDockWidget("Log", self)
        self.dockWidget_log.setFeatures(QDockWidget.DockWidgetFloatable)
        self.dockWidget_log.setObjectName("DockWidget_LOG")
        self.dockWidgetContents_log = QWidget()
        self.dockWidgetContents_log.setObjectName("DockWidgetContents_LOG")
        self.gridLayout_log = QGridLayout(self.dockWidgetContents_log)
        self.gridLayout_log.setObjectName("GridLayout_LOG")
        self.gridLayout_log.addWidget(self.logWidget, 0, 0, 1, 1)
        self.dockWidget_log.setWidget(self.dockWidgetContents_log)
        # - Set dockwidget size
        self.dockWidget_ndw.setMinimumSize(QSize(ref_width / 2, ref_height / 4))
        self.addDockWidget(Qt.DockWidgetArea(2), self.dockWidget_log)
        self.dataTreeView.log = Logger(self.logWidget)

        a = QTextEdit

    @pyqtSlot(QMainWindow)
    def onShowConfigurations(self, parent):
        """Show configuration window.
        """
        self.configurationListsWindow = \
            QVizConfigurationListsWindow(parent=self)
        self.configurationListsWindow.show()

    @pyqtSlot()
    def onSaveSignalSelection(self):
        """Save signal selection as a list of signal paths for single DTV
        (QVizDataTreeView)
        """
        # Save signal selection as a list of signal paths to .lsp file
        QVizSaveSignalSelection(dataTreeView=self.dataTreeView).execute()

    # TODO:
    # def onCloseAndReopenDatabase()


class Logger:
    """ Logger for handling passing the information and error messages to
    logWidget.

    Arguments:
        logWidget (QTextEdit) : Docked text widget.
    """

    def __init__(self, logWidget):
        self.logWidget = logWidget

    def info(self, message):
        """Print message as information.

        Arguments:
            message (str) : Message to print.
        """
        print(message)
        # Pass as html
        self.logWidget.insertHtml("<font color='black'>" + message
                                  + "</font><br />")

    def error(self, message):
        """Print message as error.

        Arguments:
            message (str) : Message to print.
        """
        print('ERROR! ' + message)
        # Pass as html
        self.logWidget.insertHtml("<b><font color='red'>"
                                  + "ERROR! </font></b><font color='red'>"
                                  + message + "</font><br />")

    def warning(self, message):
        """Print message as warning.

        Arguments:
            message (str) : Message to print.
        """
        print(message)
        # Pass as html
        self.logWidget.insertHtml("<b><font color='orange'>"
                                  + "WARNING! </font></b><font color='red'>"
                                  + message + "</font><br />")
