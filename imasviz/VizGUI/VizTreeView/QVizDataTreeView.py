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
#       def onCloseAndReopenDatabase(...):
#       def updateView(...):
#
#    - class TextCtrlLogger definition
#
#****************************************************
#     Copyright(c) 2016- L. Fleury,X. Li, D. Penko
#****************************************************

import os, logging
import xml.etree.ElementTree as ET
import numpy as np
import threading
from threading import Thread, Condition
from functools import partial
from PyQt5.QtCore import Qt, pyqtSlot, QMetaObject
from PyQt5.QtWidgets import QDockWidget, QMenuBar, QAction, QMenu
from PyQt5.QtWidgets import QMainWindow, QTreeWidget, QTreeWidgetItem, \
    QWidget, QGridLayout, QPlainTextEdit
from PyQt5.QtWidgets import QApplication, QDialog, QLineEdit, QLabel, QPushButton
from imasviz.VizUtils import (QVizLogger, QVizGlobalValues, GlobalIDs,
                              getWindowSize)
from imasviz.VizGUI.VizConfigurations.QVizConfigurationListsWindow \
    import QVizConfigurationListsWindow
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSaveSignalSelection \
    import QVizSaveSignalSelection
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizDisplayCurrentSelection \
    import QVizDisplayCurrentSelection
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizHandleRightClick \
    import QVizHandleRightClick
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizGUI.VizGUICommands.VizMenusManagement\
    .QVizHandleShiftAndRightClick \
    import QVizHandleShiftAndRightClick
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPreviewPlotWidget \
    import QVizPreviewPlotWidget
from imasviz.VizGUI.VizTreeView.QVizDataTreeViewBuilder import QVizDataTreeViewBuilder
from imasviz.VizGUI.VizWidgets.QVizNodeDocumentationWidget \
    import QVizNodeDocumentationWidget
from imasviz.VizGUI.VizTreeView.QVizTreeNode import QVizTreeNode
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizUnselectAllSignals \
    import QVizUnselectAllSignals
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadSelectedData import QVizLoadSelectedData


cv = Condition()


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

        # Set action on double click on item
        self.itemDoubleClicked.connect(self.loadDefaultOccurrence)

        self.dataSource = dataSource
        self.idsNamesList = []
        self.selectedItem = None
        self.shotNumber = dataSource.shotNumber
        self.runNumber = dataSource.runNumber
        self.mappingFilesDirectory = mappingFilesDirectory

        # Create a IDS root node with each shotnumber
        self.DTVRoot = QVizTreeNode(self, ['IDSs' + '(' + str(dataSource.shotNumber) + ')'])
        self.DTVRoot.dataTreeView = self
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

        # Parent of this tree, this is the QVizDataTreeViewFrame
        self.parent = parent

        # Keep a reference to shared data (frames, figures, ...)
        # - This is a BrowserAPI instance
        self.imas_viz_api = None

        # key = idsName, value = root node (of type QVizTreeNode) of the IDS tree
        self.IDSRoots = {}

        # Create the empty tree
        self.createEmptyIDSsTree(IDSDefFile)

        # Set dummy for node documentation widget
        self.ndw = None

        # contains root nodes for each IDS occurrence, key = IDSName + '/' + occurrence,value = ids_root_occurrence
        self.ids_roots_occurrence = {}

        # key=occurrence, value=IDS name
        self.IDSNameSelected = {}

        self.popupmenu = None

    def createEmptyIDSsTree(self, IDSDefFile):
        """The tree is created from CPODef.xml or IDSDef.xml file.
        """
        idsNode = None
        xmlTree = ET.parse(IDSDefFile)
        imas_entry = self.dataSource.createImasDataEntry()
        self.dataSource.open(imas_entry)

        for child in xmlTree.getroot():
            if (child.tag == 'IDS'):
                """Extract IDS properties from IDSDef.xml file"""
                """Get IDS name"""
                idsName = child.get('name')
                """Get IDS documentation"""
                idsDocumentation = child.get('documentation')
                self.idsNamesList.append(idsName)

                """Set array holding IDS properties"""
                IDSRootNode = self.createIDSRootNode(idsName=idsName,
                                                     idsDocumentation=idsDocumentation,
                                                     DTVRoot=self.DTVRoot)
                IDSContainsData = self.dataSource.containsData(IDSRootNode, imas_entry)
                IDSRootNode.updateIDSNode(IDSContainsData)

                # Add the IDS node as a tree item to the tree view
                self.IDSRoots[idsName] = IDSRootNode

        self.dataSource.close(imas_entry)

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

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return:
            self.loadDefaultOccurrence()

    # Note: pyqtSlot needs QObject to work, in this case, self=QTreeWidget
    # (inherited)
    @pyqtSlot(QTreeWidgetItem, int)
    def onLeftClickItem(self, item, column):
        """ Action to execute upon left clicking on DTV item.

        Arguments:
            item   (QTreeWidgetItem) : QTreeWidgetItem object.
            column (int)             : Item column.
        """

        # Set selected QTreeWidgetItem on left click
        # (marked with blue fill color in DTV)
        self.setSelectedItem(item=item, mouseButton="LEFT")

        # Find and update DTVFrame-docked node documentation widget (NDW)
        ndw = self.parent.findChild(QWidget, "QVizNodeDocumentationWidget")
        if ndw is not None:
            ndw.update(item, self)
        else:
            error = 'Node Documentation Widget not found. Update not possible'
            raise ValueError(error)
            logging.error(str(error))

        # UPDATE PLOT PREVIEW WIDGET
        if item.hasAvailableData() and (item.isDynamicData() or item.is1D()) and (not item.isIDSRoot()) and item.getName() is not None:
            # If the node holds an 1D array of values (1D_FLT) then its
            # isSignal attribute equals 1 (isSignal = 1)
            # Set and show preview panel
            QVizSignalHandlingObj = QVizSignalHandling(dataTreeView=self)
            QVizSignalHandlingObj.plotPreviewSignalCommand()

    def contextMenuEvent(self, event):
        """ Custom menu event on the (shift +) right click on the tree item.
        """
        # Get the current state of the modifier keys (SHIFT, CTRL etc.)
        modifiers = QApplication.keyboardModifiers()
        # If shift key is pressed while clicking the right mouse button,
        # proceed to build and show the 'shift + right click' custom menu
        # instead of the one provided with QVizHandleRightClick

        if modifiers == Qt.ShiftModifier:
            if len(self.selectedItems()) == 1:
                # The selected tree node item
                treeNode = self.selectedItems()[0]  # QTreeWidgetItem object

                # Set selected QTreeWidgetItem on right click
                self.setSelectedItem(item=treeNode, mouseButton="RIGHT")

                # Get position
                self.pos = event.pos()

                # Set and show the popup menu
                QVizHandleShiftAndRightClick(self).execute(treeNode)

            return

        # If shift key was not pressed while mouse right clicking, proceed
        # building and showing the 'regular' menu, handling signal nodes
        if len(self.selectedItems()) == 1:
            # The selected tree node item
            treeNode = self.selectedItems()[0]  # QTreeWidgetItem object

            # Set selected QTreeWidgetItem on right click
            self.setSelectedItem(item=treeNode, mouseButton="RIGHT")

            # Get position
            self.pos = event.pos()

            # Set and show the popup
            QVizHandleRightClick().execute(treeNode, self)


    def updateView(self, idsName, occurrence, idsData=None, viewLoadingStrategy=None):
        """ Update QVizDataTreeViewFrame.
        Arguments:
            idsName        (str) : Name of the IDS e.g. 'magnetics'.
            occurrence     (int) : IDS occurrence number (0-9).
            idsData        (obj) : Object (element) holding IDS data.
        """
        self.update_view(idsName, occurrence, idsData, viewLoadingStrategy)


    def update_view(self, idsName, occurrence, idsData, viewLoadingStrategy=None):
        """ Update the tree view with the data.
        """
        global cv
        if idsData is not None:
            self.IDSRoots[idsName].setOccurrence(occurrence)
            nodeBuilder = QVizDataTreeViewBuilder(ids=self.dataSource.data_entries)
            thread1 = threading.Thread(target=self.buildTreeView, args=(nodeBuilder, idsName, occurrence, idsData, viewLoadingStrategy))
            cv.acquire()
            thread1.start()
            cv.wait()
            cv.release()
            nodeBuilder.endBuildView(idsName, occurrence, self)


    def buildTreeView(self, nodeBuilder, idsName, occurrence, idsData, viewLoadingStrategy):
        """ Build the data tree view by adding a set of available IDS nodes as
            an items to it.

        Arguments:
            idsName                         : name of the IDS
            occurrence    (int)             : IDS occurrence number (0-9).
            idsData       (obj)             : Object (element) holding IDS data.
        """
        cv.acquire()
        import time
        t1 = time.time()
        logging.info("Occurrence "
                     + str(int(occurrence))
                     + " of " + idsName
                     + " IDS in memory, building "
                     + " view...")
        idsDocumentation = self.IDSRoots[idsName].getDocumentation()
        root_node_ori = self.IDSRoots[idsName]
        ids_root_node = self.createIDSRootNode(idsName, idsDocumentation, None, root_node_ori)
        ids_root_node.setOccurrence(occurrence)
        root_node_label = 'occurrence ' + str(int(occurrence))

        if viewLoadingStrategy is not None:
            label = viewLoadingStrategy.getLabel()
            if label is not None:
               root_node_label += " [" + label + "]"
        
        ids_root_occ = QVizTreeNode(ids_root_node, [root_node_label], ids_root_node.getData())
        ids_root_occ.setOccurrenceEntry(True)
        if viewLoadingStrategy is not None:
            ids_root_occ.setIDSIsDynamic(viewLoadingStrategy.isIDSDynamic())
        ids_root_occ.setStyleWhenContainingData()

        for child in idsData:
            self.addChildren(nodeBuilder, child, ids_root_occ, idsName, occurrence, ids_root_occ)

        t2 = time.time()
        logging.info("Building tree view took " + str(t2 - t1) + ' seconds.')
        nodeBuilder.setIDSRootNode(ids_root_node)
        logging.info("View update ended.")

        cv.notify()
        cv.release()

    def createIDSRootNode(self, idsName, idsDocumentation, DTVRoot, root_node_ori=None):
        if root_node_ori is not None:
            itemDataDict = root_node_ori.getData()
        else:
            itemDataDict = {}
        itemDataDict['IDSName'] = idsName
        itemDataDict['isIDSRoot'] = 1
        itemDataDict['dataName'] = idsName
        itemDataDict['isSignal'] = 0
        itemDataDict['isSelected'] = 0
        itemDataDict['Tag'] = idsName
        itemDataDict['Path'] = itemDataDict['Tag']
        itemDataDict['documentation'] = idsDocumentation
        return QVizTreeNode(DTVRoot, [idsName], itemDataDict)

    def addChildren(self, nodeBuilder, element, parent,
                    idsName, occurrence, ids_root_occ):
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
                                              occurrence, self, ids_root_occ)
        if element_node is not None:
            for child in element:
                self.addChildren(nodeBuilder, child, element_node, idsName,
                                 occurrence, ids_root_occ)

    def OnExpandItem(self, event):
        return

    def OnCollapseItem(self, event):
        return

    def loadDefaultOccurrence(self):
        """Loads the next available occurrence which contains data.
        """

        # Get currently selected QTreeWidgetItem
        item = self.selectedItems()[0]

        # Continue only if the QTreeWidgetItem is the IDS root
        if not item.isIDSRoot():
            return

        occ = self.imas_viz_api.GetNextOccurrenceUnloadedWithAvailableData(self, item)

        if occ is None:
            return

        # Set class object
        QVizLoadSelectedData(dataTreeView=self,
                             IDSName=item.getIDSName(),
                             occurrence=occ,
                             viewLoadingStrategy=None,
                             asynch=True).execute()

    def getMDI(self):
        """ Get MDI area through the root IMASViz main window.
        """
        if self.window().objectName() == "IMASViz root window":
            return self.window().getMDI()
        return None


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
            publicStr = "UDA "
            self.setWindowTitle("Database: " + dataSource.machineName + " "
                                + "(from UDA), shot: "
                                + str(dataSource.shotNumber) + ", run: "
                                + str(dataSource.runNumber))
        else:
            self.setWindowTitle("Database: " + dataSource.imasDbName + ", "
                                + "user: " + dataSource.userName + ", shot: "
                                + str(dataSource.shotNumber) + ", run: "
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
        arg = event.data[0]
        if arg == 1:
            message = event.data[1]
            logging.info(message)
        else:
            idsName = event.data[0]
            occurrence = event.data[1]
            idsData = event.data[2]
            progressBar = event.data[3]
            progressBar.setWindowTitle("Updating view...")
            viewLoadingStrategy = event.data[4]
            self.dataTreeView.updateView(idsName, occurrence, idsData, viewLoadingStrategy)
            progressBar.hide()


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

        #------
        # Add menu item to export the contents, opened in DTV, to a new local
        # IDS
        action_onExportToLocal = QAction('Export to IDS', self)
        action_onExportToLocal.triggered.connect(self.onExportToLocal)
        actions.addAction(action_onExportToLocal)

        #-----------------------------------------------------------------------

        # Set menu handling node selection features
        nodeSelection = menuBar.addMenu('Node Selection Actions')
        #-----------------------------------------------------------------------
        # Set new submenu for handling signal selection to be added to 'Actions'
        # menu
        # subMenu_select = nodeSelection.addMenu('Signal Selection Options')

        action_onSaveSignalSelection = QAction('Save Node Selection', self)
        action_onSaveSignalSelection.triggered.connect(self.onSaveSignalSelection)
        nodeSelection.addAction(action_onSaveSignalSelection)

        action_onDisplayNodesSelection = QAction('Display Node(s) selection', self)
        action_onDisplayNodesSelection.triggered.connect(self.onDisplayNodesSelection)
        nodeSelection.addAction(action_onDisplayNodesSelection)

        # -----
        # Add menu item to unselect all signals - This/Current DTV
        subMenu_unselect = nodeSelection.addMenu('Unselect All Nodes')
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
        # - Add menu for handling plotting a selection of signal nodes
        nodeSelection.addMenu(QVizSignalHandling(self.dataTreeView). \
            menuPlotSelectedSignalNodes(parentMenu=nodeSelection))

        # - Update menu on show
        nodeSelection.aboutToShow.connect(partial(self.updateMenuNodeSelection,
            menu=nodeSelection))

        vizFiguresManagement = menuBar.addMenu('Plot windows')
        vizFiguresManagement.aboutToShow.connect(partial(self.updateMenuNodePlotWindows,
                                                  vizFiguresManagement))

        # Set menu bar
        self.setMenuBar(menuBar)


    def updateMenuNodePlotWindows(self, vizFiguresManagement):
        QVizSignalHandlingObj = QVizSignalHandling(dataTreeView=self.dataTreeView)
        numFig = self.dataTreeView.imas_viz_api.GetFigurePlotsCount()
        numTPV = self.dataTreeView.imas_viz_api.GetTablePlotViewsCount()
        numSPV = self.dataTreeView.imas_viz_api.GetStackedPlotViewsCount()
        numImg = self.dataTreeView.imas_viz_api.GetImagePlotsCount()
        vizFiguresManagement.clear()
        QVizSignalHandlingObj.menusShowHideAndDelete(numFig, numTPV, numSPV, numImg, vizFiguresManagement)

    def updateMenuNodeSelection(self, menu):
        """Update menu handling node selection.

        Arguments:
            menu (QMenu) : Menu that handles node selection to update.

        """

        # TODO: Fix the plotting routines dependency on having signal node
        #       QTreeWidget selected in DTV in order for them to work
        # As most plotting routines assume that signal node is set as
        # active/selected, they fail if they're activated while
        # non-signal node is selected (due to them first being available
        # only from the right-click-on-signal-node popup menu)
        # To avoid that we manually set active QTreeWidget corresponding to the
        # first selected signal node.

        # Get a list of selected node signals (red colored)
        sigDict = self.dataTreeView.selectedSignalsDict

        # Update only if selection of node signals is available
        if len(sigDict) > 0:
            # Get first selected node signal
            firstKey = next(iter(sigDict))
            # Get QTreeWidgetItem of the first node signal
            firstItem = sigDict[firstKey]['QTreeWidgetItem']
            # To jump to tree item (not actually selecting it)
            # self.dataTreeView.setCurrentItem(firstItem)
            # Set tree item as selected tree item
            self.dataTreeView.selectedItem = firstItem

            # Find and delete menu 'Plot selected nodes to'
            childMenu = menu.findChildren(QMenu, 'Plot selected nodes to')[0]
            childMenu.menuAction().setVisible(False)
            childMenu.deleteLater()
            # Rebuild menu
            # - Add menu for handling plotting a selection of signal nodes
            # TODO: Create a set of actions that can be used by multiple
            #       menus, buttons etc. instead of 'borrowing' them from
            #       QVizSignalHandling
            menu.addMenu(QVizSignalHandling(self.dataTreeView).menuPlotSelectedSignalNodes(parentMenu=menu))
        else:
            pass

    def addDockWidgets(self):
        """Add dockable widgets to DTV frame main window.
        """

        # Get reference parameters
        # - DTV frame width and height
        # ref_width, ref_height = getWindowSize(self)

        # PREVIEW PLOT WIDGET (PPW)
        # - Set the widget
        self.previewPlotWidget = QVizPreviewPlotWidget(dataTreeView=self.dataTreeView, parent=self,
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
        self.addDockWidget(Qt.RightDockWidgetArea, self.dockWidget_ppw)

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
        self.addDockWidget(Qt.RightDockWidgetArea, self.dockWidget_ndw)

        # LOG WIDGET
        self.logWidget = QPlainTextEdit(parent=self)
        self.logWidget.setReadOnly(True)
        self.dockWidget_log = QDockWidget("Log", self)
        self.dockWidget_log.setFeatures(QDockWidget.DockWidgetFloatable)
        self.dockWidget_log.setObjectName("DockWidget_LOG")
        self.dockWidgetContents_log = QWidget()
        self.dockWidgetContents_log.setObjectName("DockWidgetContents_LOG")
        self.gridLayout_log = QGridLayout(self.dockWidgetContents_log)
        self.gridLayout_log.addWidget(self.logWidget, 0, 0, 1, 1)
        self.dockWidget_log.setWidget(self.dockWidgetContents_log)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dockWidget_log)
        handler = QVizLogger.getHandler()
        handler.new_record.connect(self.logWidget.appendHtml)

        # Set first docked widget minimum width
        self.dockWidget_ppw.setMinimumWidth(400)
        # Determine how much of vertical space the docked widgets should take
        # Note: Without using 'setMinimumWidth' on one of docked widgets
        #       the central widget takes ~90% of horizontal space (no 'resize'
        #       solves that ...)
        self.resizeDocks([self.dockWidget_ppw,
                          self.dockWidget_ndw,
                          self.dockWidget_log],
                         [50, 50, 25], Qt.Vertical)

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

    @pyqtSlot()
    def onDisplayNodesSelection(self):
        """Displays signal selection as a list of signal paths for single DTV
        (QVizDataTreeView)
        """
        # Displays signal selection as a list of signal paths
        QVizDisplayCurrentSelection(dataTreeView=self.dataTreeView).execute()

    @pyqtSlot()
    def onExportToLocal(self):
        """A feature that allows export of opened (!) IDSs to a new separate
        IDS using a popup dialog window.
        NOTE: the database (created using 'imasdb' command) must ALREADY
        EXIST!
        """

        dataSource = self.dataTreeView.dataSource

        dialog = QDialog(self)
        dialog.setWindowTitle('Export browsed tree view contents to local ID')
        dialog.resize(300,200)

        userLabel = QLabel('User: ', self)
        databaseLabel = QLabel('Database: ', self)
        shotLabel = QLabel('Shot: ', self)
        runLabel = QLabel('Run: ', self)

        noteLabel1 = QLabel('Note 1: Only IDSs, that are CURRENTLY OPENED in '
                           'the tree view, will be exported!',
                           self)
        noteLabel2 = QLabel('Note 2: Make sure the database/machine '
                            '(created using imasdb command) exists!',
                           self)

        userBox = QLineEdit(self)
        userBox.setText('/')
        databaseBox = QLineEdit(self)
        databaseBox.setText('/')
        shotBox = QLineEdit(self)
        shotBox.setText('1')
        runBox = QLineEdit(self)
        runBox.setText('1')

        def onOk():
            import imas
            # Execute the export to local IDS
            logging.info('Starting to export opened IDSs to ' +
                                       ' IDS with user: ' +
                                       userBox.text() + ', database: ' +
                                       databaseBox.text() + ', shot: ' +
                                       shotBox.text() +
                                       ', run: ' + runBox.text() + '.')
            exported_ids = imas.ids(int(shotBox.text()), int(runBox.text()))

            # Patch: In case IDS database or user do not exist
            try:
                exported_ids.create_env(userBox.text(), databaseBox.text(), '3')
            except:
                logging.info('The specified database ' +
                                           databaseBox.text() + ' for user ' +
                                           userBox.text() + ' not found.')
                return
            dataSource.exportToLocal(self.dataTreeView, exported_ids)

            logging.info('Export finished.')

        def onCancel():
            # Close the dialog
            dialog.destroy()

        okButton = QPushButton('OK', dialog)
        okButton.clicked.connect(onOk)

        cancelButton = QPushButton('Cancel', dialog)
        cancelButton.clicked.connect(onCancel)

        # Set layout
        layout = QGridLayout(dialog)
        layout.setObjectName('gridLayout')

        # Set layout marigin (left, top, right, bottom)
        # layout.setContentsMargins(10, 10, 10, 10)

        # Set starting row index
        r = 0

        layout.addWidget(noteLabel1,     r, 0, 1, 4)
        r += 1
        layout.addWidget(noteLabel2,     r, 0, 1, 4)
        r += 1
        layout.addWidget(userLabel,     r, 0, 1, 1)
        layout.addWidget(userBox,       r, 1, 1, 1)
        r += 1
        layout.addWidget(databaseLabel, r, 0, 1, 1)
        layout.addWidget(databaseBox,   r, 1, 1, 1)
        r += 1
        layout.addWidget(shotLabel,     r, 0, 1, 1)
        layout.addWidget(shotBox,       r, 1, 1, 1)
        r += 1
        layout.addWidget(runLabel,      r, 0, 1, 1)
        layout.addWidget(runBox,        r, 1, 1, 1)
        r += 1
        layout.addWidget(okButton,      r, 0, 1, 2)
        r += 1
        layout.addWidget(cancelButton,  r, 0, 1, 2)

        dialog.show()

    def getMDI(self):
        """ Get MDI area through the root IMASViz main window.
        """
        if self.window().objectName() == "IMASViz root window":
            return self.window().getMDI()
        return None

    # TODO:
    # def onCloseAndReopenDatabase()
