# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import os, logging
import imas
import numpy as np
from functools import partial
from PySide6.QtCore import Qt, Slot, QMetaObject
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QDockWidget, QMenuBar, QMenu
from PySide6.QtWidgets import QMainWindow, QTreeWidget, QTreeWidgetItem, \
    QWidget, QGridLayout, QPlainTextEdit
from PySide6.QtWidgets import QApplication
from imasviz.VizUtils import QVizLogger, QVizGlobalValues, GlobalIDs,getWindowSize
from imasviz.VizDataSource.QVizCaseOccurrences import QVizCaseOccurrences
from imasviz.VizDataAccess.VizTimeSlices import FIRST_SLICE
from imasviz.VizGUI.VizConfigurations.QVizApplyConfigurations \
    import QVizApplyConfigurations
from imasviz.VizGUI.VizGUICommands.VizDataExport.QVizExportToIDS \
    import QVizExportToIDS
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSaveNodeSelection \
    import QVizSaveNodeSelection
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizDisplayCurrentSelection \
    import QVizDisplayCurrentSelection
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizHandleRightClick \
    import QVizHandleRightClick
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizGUI.VizGUICommands.VizMenusManagement\
    .QVizHandleShiftAndRightClick \
    import QVizHandleShiftAndRightClick
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPreviewPlot \
    import QVizPreviewPlot
from imasviz.VizGUI.VizTreeView.QVizDataTreeViewBuilder import QVizDataTreeViewBuilder
from imasviz.VizGUI.VizWidgets.VizNodeDocumentation.QVizNodeDocumentationPanel \
    import QVizNodeDocumentationPanel
from imasviz.VizGUI.VizTreeView.QVizTreeNode import QVizTreeNode
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
    import QVizLoadOccurrence


class QVizDataTreeView(QTreeWidget):
    """Set and populate QTreeWidget.
    """

    def __init__(self, parent, dataSource, mappingFilesDirectory,
                 *args, **kwargs):
        """
        Arguments:
            parent     (QWindow)            : QVizDataTreeView parent.
            dataSource (QVizIMASDataSource) : IDS data source from QVizDataSourceFactory
            mappingFilesDirectory (str)     : Path to IMASViz mapping files directory
                                          (example: viz/ts_mapping_files)
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
        self.selectedItem = None
        self.uri = dataSource.uri
        self.mappingFilesDirectory = mappingFilesDirectory

        # What the opened case holds, asked of the case itself: which
        # occurrences of an IDS exist is the first question of every load, and
        # it used to be asked of the data dictionary through an expression that
        # this IMAS stack cannot evaluate at all (see QVizCaseOccurrences).
        self.occurrences = QVizCaseOccurrences(dataSource)

        # Loads this view has started and not finished, keyed IDSName/occurrence.
        # The guard against loading the same occurrence twice in the same view
        # used to be a class attribute keyed by IDS name only, shared by every
        # view and reset by the next command object built.
        self.loadsInProgress = set()

        # What the registered plugins offer for a node of this view, resolved on
        # the first menu that asks -- importing them costs close to a second, and
        # a view nobody right-clicks should not pay it. Built once for the view:
        # the framework used to import and build every plugin again on every
        # right click.
        self.pluginCatalog = None

        # Create a IDS root node with each URI
        self.DTVRoot = QVizTreeNode(self, ['IDSs' + '(' + dataSource.uri + ')'])
        self.DTVRoot.dataTreeView = self
        # #Dictionary where each element is also a dictionary containing
        # self.dataTreeView.selectedSignalsDict[key] = \
        #     {'index': index,
        #      'QTreeWidgetItem': self.dataTreeView.selectedItem,
        #      'uri': self.dataTreeView.dataSource.uri}
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
        self.createEmptyIDSsTree()

        # The node documentation panel of the frame this view lives in. The
        # frame sets it when it docks one; a view without a frame of its own
        # (the tests, a view built by hand) leaves it None and a click then says
        # so in the log instead of raising out of the slot, which used to kill
        # the preview update sitting after it.
        self.ndw = None

        # contains root nodes for each IDS occurrence, key = IDSName + '/' + occurrence,value = ids_root_occurrence
        self.ids_roots_occurrence = {}

        # key=occurrence, value=IDS name
        self.IDSNameSelected = {}

        self.popupmenu = None

    def createEmptyIDSsTree(self):
        """One root per IDS the data dictionary of **this case** declares.

        The inventory used to be parsed out of an `IDSDef_<version>.xml` file.
        Once the walk of a loaded IDS came from IMAS-Python reflection, that file
        supplied exactly two things: the name of a root and its documentation.
        And the path of it was built from a number this stack does not use for a
        data dictionary at all: measured on IMAS-Python/2.3.0, the distribution
        bundles 35 dictionary versions (3.22.0 through 4.1.1) and `5.7.1` -- the
        number `IMAS_VERSION` took because QVizGlobalValues copied AL_VERSION, an
        Access Layer version, into it -- is not one of them. The path therefore
        named a file that has never existed, and opening a pulse died on a
        FileNotFoundError raised outside the gesture that asked for it.

        The entry this view reads through answers the same two questions at the
        version the case was actually written with: `DBEntry.dd_version` names it,
        and the `IDSFactory` carried by that entry enumerates the names and their
        documentation. Measured on the reference case: 69 names, 0.4 s to read all
        69 documentations through `IDSFactory.new(name).metadata` -- against the
        55 names the harness file held, 3.23.3 being two minor versions older.
        """
        self.dataSource.open()

        # Asked of the entry, not of the environment: an entry built at a version
        # the distribution does not bundle has already refused by name
        # (UnknownDDVersion, a ValueError naming the version and the closest one
        # it knows), and the gesture that opened this view puts that in the log.
        factory = imas.IDSFactory(self.dataSource.db_entry.dd_version)
        for idsName in factory.ids_names():
            IDSRootNode = self.createIDSRootNode(
                idsName=idsName,
                idsDocumentation=factory.new(idsName).metadata.documentation,
                DTVRoot=self.DTVRoot)

            # Which occurrences hold data is answered by the case: the whole
            # inventory of the 69 IDS names of this data dictionary costs
            # 0.10 s, against 336 s for reading every IDS to answer the same
            # question. An IDS the entry refuses stays in the tree holding
            # nothing, with the reason in the log -- measured, the old
            # question was asked as eval("imas.<ids>()"), raised out of this
            # loop on the first IDS of the reference case (amns_data), and
            # took the whole shot view down with it.
            occurrences = self.occurrencesOf(idsName)
            for occurrence in occurrences:
                IDSRootNode.setAvailableIDSData(occurrence, 1)
            IDSRootNode.updateIDSNode(bool(occurrences))

            # Add the IDS node as a tree item to the tree view
            self.IDSRoots[idsName] = IDSRootNode

        # The open() above is this view's own reference on the case, held for as
        # long as the view lives and given back by Viz_API.RemoveDTVFrame. As
        # long as it is held the parser can open and close once per IDS without
        # ever closing and rebuilding the entry, and the occurrence inventory
        # reads through an entry that is genuinely open.

    def occurrencesOf(self, idsName):
        """The occurrences of `idsName` this case holds, [] when it cannot say.

        The refusal is logged rather than raised: this answers for every IDS of
        the shot view, and one IDS the back end refuses must not decide what the
        other roots of the view look like.
        """
        try:
            return self.occurrences.occurrencesOf(idsName)
        except ValueError as error:
            logging.getLogger(self.uri).error(error)
            return []

    def loadedOccurrences(self, idsName):
        """The occurrences of `idsName` this view already displays."""
        prefix = idsName + '/'
        return [int(key[len(prefix):]) for key in self.ids_roots_occurrence
                if key.startswith(prefix)]

    def loadedIds(self, idsName):
        """The IDS instance of an occurrence of `idsName` held in memory.

        Asked by the menu that names a slice: the number of elements a dynamic
        array holds is free to read from an instance already loaded, and unknown
        for an occurrence nobody has loaded yet.
        """
        for occurrence in self.loadedOccurrences(idsName):
            entry = self.ids_roots_occurrence.get(idsName + '/' + str(occurrence))
            if entry is not None and getattr(entry, 'idsRef', None) is not None:
                return entry.idsRef
        return None

    def isLoadInFlight(self, idsName, occurrence):
        """Whether this view is already building this occurrence."""
        return (idsName, occurrence) in self.loadsInProgress

    def beginLoad(self, idsName, occurrence):
        self.loadsInProgress.add((idsName, occurrence))

    def endLoad(self, idsName, occurrence):
        self.loadsInProgress.discard((idsName, occurrence))

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

    # Note: Slot needs QObject to work, in this case, self=QTreeWidget
    # (inherited)
    @Slot(QTreeWidgetItem, int)
    def onLeftClickItem(self, item, column):
        """ Action to execute upon left clicking on DTV item.

        Arguments:
            item   (QTreeWidgetItem) : QTreeWidgetItem object.
            column (int)             : Item column.
        """

        # Set selected QTreeWidgetItem on left click
        # (marked with blue fill color in DTV)
        self.setSelectedItem(item=item, mouseButton="LEFT")

        # Show what this node is in the frame's node documentation panel.
        # A measured consequence of the way this used to work: the lookup by
        # object name missed, the slot raised ValueError, PySide6 printed the
        # traceback and carried on -- so the user saw nothing about the node and
        # the preview update below never ran.
        if self.ndw is None:
            logging.getLogger(self.uri).info(
                'No node documentation panel in this window: cannot describe '
                'the selected node.')
        else:
            self.ndw.showNode(item)

        # UPDATE PLOT PREVIEW WIDGET
        # Every node the click names is handed to the panel, which decides from
        # the axes the read would walk and says what it refused. The gate that
        # used to sit here asked the dictionary how big the leaf was
        # (isDynamicData() or is1D()) and stayed silent for anything it did not
        # recognise, which is how the panel kept showing the previous node's
        # curve under the previous node's name.
        if (not item.isIDSRoot()) and item.getName() is not None:
            logging.debug('QVizDataTreeView::onLeftClickItem::calling plotPreviewSignalCommand')
            QVizSignalHandlingObj = QVizSignalHandling(dataTreeView=self, treeNode=item)
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


    def updateView(self, idsName, idsInstance, occurrence, idsData=None,
                   sliceSelection=None):
        """ Update QVizDataTreeViewFrame.
        Arguments:
            idsName        (str) : Name of the IDS e.g. 'magnetics'.
            occurrence     (int) : IDS occurrence number (0-9).
            idsData        (obj) : Object (element) holding IDS data.
        """
        self.update_view(idsName, idsInstance, occurrence, idsData,
                         sliceSelection)


    def update_view(self, idsName, idsInstance, occurrence, idsData,
                    sliceSelection=None):
        """Build the tree this walk produced, in the thread that owns the widget.

        When the load is asynchronous the walk runs in the parser's own thread
        and hands the shadow tree over with a Qt event, which is delivered in
        the GUI thread. This method used to start a Python thread of its own and
        wait on a condition for it, so the items were built in a thread that does
        not own the widget -- measured: updateView ran in 'Dummy-1' while the
        main thread sat in cv.wait().
        """
        if idsData is None:
            return
        nodeBuilder = QVizDataTreeViewBuilder()
        self.buildTreeView(nodeBuilder, idsName, idsInstance, occurrence, idsData,
                           sliceSelection)
        nodeBuilder.endBuildView(idsName, occurrence, self)

    def buildTreeView(self, nodeBuilder, idsName, idsInstance, occurrence,
                      idsData, sliceSelection):
        """ Build the data tree view by adding a set of available IDS nodes as
            an items to it.

        Arguments:
            idsName                         : name of the IDS
            occurrence    (int)             : IDS occurrence number (0-9).
            idsData       (obj)             : Object (element) holding IDS data.
        """
        import time
        t1 = time.time()
        logging.getLogger(self.uri).info("Occurrence "
                     + str(int(occurrence))
                     + " of " + idsName
                     + " IDS in memory, building "
                     + " view...")

        idsDocumentation = self.IDSRoots[idsName].getDocumentation()
        root_node_ori = self.IDSRoots[idsName]
        ids_root_node = self.createIDSRootNode(idsName, idsDocumentation, None, root_node_ori)
        ids_root_node.setOccurrence(occurrence)
        ids_root_node.idsRef = idsInstance
        selection = FIRST_SLICE if sliceSelection is None else sliceSelection
        root_node_label = 'occurrence ' + str(int(occurrence)) \
                          + ' [' + selection.viewLabel() + ']'

        ids_root_occ = QVizTreeNode(ids_root_node, [root_node_label], ids_root_node.getData())
        ids_root_occ.idsRef = idsInstance
        ids_root_occ.dataTreeView = self
        ids_root_occ.setOccurrenceEntry(True)
        ids_root_occ.setOccurrence(occurrence)
        # Whether this occurrence can be looked at another way is what the walk
        # met, not what the slice choice was: the flag used to be raised only in
        # the branch of the fourth choice, which left the "Add a new view" entry
        # of the pop-up menu unreachable for the other three.
        ids_root_occ.setIDSIsDynamic(idsData.get('dynamic_arrays') == '1')
        homogeneousTime = getattr(getattr(idsInstance, 'ids_properties', None),
                                  'homogeneous_time', None)
        if homogeneousTime is not None:
            # Where the time base of this IDS lives, needed by every quantity
            # read out of this view. It used to be written while asking whether
            # the IDS holds data, which meant reading the IDS to answer a
            # question the loaded instance answers for free.
            ids_root_occ.setHomogeneousTime(int(homogeneousTime))
        ids_root_occ.setStyleWhenContainingData()

        for child in idsData:
            self.addChildren(nodeBuilder, child, ids_root_occ, idsName, occurrence, ids_root_occ)

        t2 = time.time()
        logging.getLogger(self.uri).info("Building tree view took " + str(t2 - t1) + ' seconds.')
        nodeBuilder.setIDSRootNode(ids_root_node)
        logging.getLogger(self.uri).info("View update ended.")

    def createIDSRootNode(self, idsName, idsDocumentation, DTVRoot, root_node_ori=None):
        if root_node_ori is not None:
            itemDataDict = root_node_ori.getData().copy()
        else:
            itemDataDict = {}
        itemDataDict['IDSName'] = idsName
        itemDataDict['isIDSRoot'] = 1
        itemDataDict['dataName'] = idsName
        itemDataDict['isSignal'] = 0
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

        The double click and the Return key both land here. Measured, a gesture
        with nothing selected raised IndexError: list index out of range, and
        the helper under it -- GetNextOccurrenceUnloadedWithAvailableData --
        raised AttributeError on the expression eval("imas.<ids>()"), so nothing
        could be loaded this way on this IMAS stack.
        """
        selected = self.selectedItems()
        if not selected:
            logging.getLogger(self.uri).info(
                'Nothing is selected in the shot view: no occurrence to load.')
            return
        item = selected[0]

        # Continue only if the QTreeWidgetItem is the IDS root
        if not item.isIDSRoot():
            return

        occurrence = self.occurrences.nextUnloaded(
            item.getIDSName(), self.loadedOccurrences(item.getIDSName()))
        if occurrence is None:
            logging.getLogger(self.uri).info(
                'Every occurrence of the %s IDS this case holds is already '
                'displayed in this view.' % item.getIDSName())
            return

        try:
            QVizLoadOccurrence(dataTreeView=self, idsName=item.getIDSName(),
                               occurrence=occurrence).execute()
        except ValueError as error:
            logging.getLogger(self.uri).error(error)


class QVizDataTreeViewFrame(QMainWindow):
    """ Set QMainWindow to contain the QTreeWidget.
    """

    def __init__(self, parent, views, dataSource, imas_viz_api, *args, **kwargs):
        """
        Arguments:
            parent     (PyQT obj)           : QVizDataTreeView parent.
            views      (array)              :
            dataSource (QVizIMASDataSource) : IDS data source from
                                              QVizDataSourceFactory
        """
        super(QVizDataTreeViewFrame, self).__init__(parent, *args, **kwargs)

        # The one configurations window of this shot view, opened on demand
        self.configurationsWindow = None

        # Basic settings (QMainWindow)
        self.resize(800, 800)

        # Set Data Tree View Window name
        self.setObjectName('DTV Window')

        # Set title (QMainWindow)
        self.setWindowTitle("URI: " + dataSource.uri)

        # Set Qt TreeView
        self.dataTreeView = \
            QVizDataTreeView(parent=self,
                             dataSource=dataSource,
                             mappingFilesDirectory=os.environ['TS_MAPPINGS_DIR'])
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
        # print('event=', event)
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
            # The frame has no uri of its own; the view it holds does, and this
            # is the logger of the case, which is what the log panel shows.
            logging.getLogger(self.dataTreeView.uri).info(message)
        else:
            idsName = event.data[0]
            idsInstance =  event.data[1]
            occurrence = event.data[2]
            idsData = event.data[3]
            progressBar = event.data[4]
            progressBar.setWindowTitle("Updating view...")
            sliceSelection = event.data[5]
            self.dataTreeView.updateView(idsName, idsInstance, occurrence,
                                         idsData, sliceSelection)
            # The bar was built for this load: closing it takes it down, where
            # hide() left a live window stacked behind the next one.
            progressBar.close()
            self.dataTreeView.endLoad(idsName, occurrence)


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
        vizFiguresManagement.clear()
        QVizSignalHandlingObj.menusShowHideAndDelete(vizFiguresManagement)

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
        # - Set the widget. It says what it holds once a node is clicked, so
        #   there is nothing to draw before the first click -- the empty plot()
        #   call the legacy panel needed built axes for a quantity nobody had
        #   asked for.
        self.previewPlotWidget = QVizPreviewPlot(parent=self,
                                                 title='Preview Plot')
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

        # NODE DOCUMENTATION PANEL (NDW)
        # - Set the panel. It names the node it was handed, so it has something
        #   honest to say before the first click; the legacy widget prefilled
        #   every one of its twenty labels with '/' and showed all of them.
        self.nodeDocumentationWidget = QVizNodeDocumentationPanel(parent=self)
        # The view asks this panel rather than hunting it by object name: the
        # legacy click slot did a findChild on its parent and raised ValueError
        # when the name did not answer, out of a slot, which stopped the preview
        # update that followed it in the same slot.
        self.dataTreeView.ndw = self.nodeDocumentationWidget
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
        handler = QVizLogger()
        handler.new_signal_emiter.new_signal.connect(self.logWidget.appendHtml)
        logging.getLogger(self.dataTreeView.uri).addHandler(handler)
        logging.getLogger(self.dataTreeView.uri).setLevel(logging.INFO)

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

    @Slot(QMainWindow)
    def onShowConfigurations(self, parent):
        """Show configuration window.

        One window per shot view, shown again when the entry is used twice: the
        list it shows is read from the folder as it appears, so a configuration
        saved since it was last opened is in it.
        """
        if self.configurationsWindow is None:
            self.configurationsWindow = \
                QVizApplyConfigurations(self.dataTreeView)
        self.configurationsWindow.show()
        return self.configurationsWindow

    @Slot()
    def onSaveSignalSelection(self):
        """Save the node selection of this shot view as a list of paths.

        The name comes from the dialog the manual describes; a cancelled dialog
        writes nothing.
        """
        try:
            QVizSaveNodeSelection(dataTreeView=self.dataTreeView).execute()
        except ValueError as e:
            logging.getLogger(self.dataTreeView.uri).error(str(e))

    @Slot()
    def onDisplayNodesSelection(self):
        """Displays signal selection as a list of signal paths for single DTV
        (QVizDataTreeView)
        """
        # Displays signal selection as a list of signal paths
        QVizDisplayCurrentSelection(dataTreeView=self.dataTreeView).execute()

    @Slot()
    def onExportToLocal(self):
        """Write the IDSs this tree view has open into another case.

        The dialog names the case; the reason an export cannot happen -- nothing
        open, a field left empty, a case the Access Layer refuses -- is said in
        the log panel, where the manual tells the user to look. That reason used
        to be swallowed by a bare ``except:``, logged at info level as "Unable to
        create pulse file with URI: ..." with the Access Layer's own words thrown
        away and nothing on disk but a 1912-byte ``master.h5``.
        """
        try:
            QVizExportToIDS(self.dataTreeView).execute()
        except ValueError as e:
            logging.getLogger(self.dataTreeView.uri).error(str(e))

    # TODO:
    # def onCloseAndReopenDatabase()
