
import logging
import traceback
from functools import partial
from PySide6.QtCore import Slot
from imasviz.VizUtils import GlobalIcons
from imasviz.VizPlugins.VizPlugin import VizPlugin
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget
from PySide6.QtGui import QAction


class MenuIDS:
    def __init__(self):
        self.PLUGINS_MENU_IDS = []  # list of tuples (Id, menu desc., plugins object)


class QVizPluginsHandler:

    def __init__(self, dataTreeView, selectedTreeNode):
        self.menuIDS = MenuIDS()
        self.pluginsObjects = VizPlugin.getPluginsObjects(
            dataTreeView=dataTreeView, selectedTreeNode=selectedTreeNode)

    def updateMenu(self, menu, dataTreeView, selectedTreeNode):

        addedPluginsEntries = {}

        pluginsNames = self.pluginsObjects[0]
        pluginsObjects = self.pluginsObjects[1]  # tuple: Plugins names, VizPlugin instances

        for p in pluginsNames:
            addedPluginsEntries[p] = []  # each plugins entry should appear only once in the popup menu

        for i in range(0, len(pluginsNames)):
            pluginsName = pluginsNames[i]
            pluginsObject = pluginsObjects[i]

            if isinstance(pluginsObject, VizPlugin):
                if not pluginsObject.isEnabled():
                    continue
            entriesList = []  # list of entry index (ex: [0,1])
            if isinstance(pluginsObject, VizPlugin):
                entriesList = pluginsObject.getEntries()
            else:
                entriesList = VizPlugin.getEntriesFor(pluginsName,
                                                      selectedTreeNode)

            if entriesList is None or len(entriesList) == 0:
                continue

            for entry in entriesList:
                if entry not in addedPluginsEntries[pluginsName]:
                    # TODO: properly set ID
                    new_id = 9999
                    tuple = (pluginsName, new_id, entry,
                             pluginsObject)
                    self.menuIDS.PLUGINS_MENU_IDS.append(tuple)
                    addedPluginsEntries[pluginsName].append(entry)  # plugins entry should appear only once in the popup menu

        for i in range(0, len(self.menuIDS.PLUGINS_MENU_IDS)):
            m = self.menuIDS.PLUGINS_MENU_IDS[i]
            pluginsName = m[0]
            menuId = m[1]
            entry = m[2]
            pluginsObject = m[3]
            allEntries = []
            if isinstance(pluginsObject, VizPlugin):
                allEntries = pluginsObject.getAllEntries()
            else:
                allEntries = VizPlugin.getAllEntries(pluginsName)

            pluginsCommandDescription = allEntries[entry][1]

            # Add action ...
            icon_onPluginHandler = GlobalIcons.getCustomQIcon(QApplication,
                                                              'new')
            action_onPluginHandler = QAction(icon_onPluginHandler,
                                             pluginsCommandDescription,
                                             dataTreeView)
            action_onPluginHandler.triggered.connect(
                partial(self.popUpMenuHandler, i, dataTreeView))
            # Check if pluginsObject contains the 'getDescription' routine
            if callable(getattr(pluginsObject, "getDescription", None)):
                # Set message to be displayed in status bar when hovering over
                # the # action in the pop up menu. Set it only
                action_onPluginHandler.setStatusTip(
                    pluginsObject.getDescription())
                action_onPluginHandler.setToolTip(pluginsObject.getDescription())
            else:
                action_onPluginHandler.setStatusTip(pluginsName)
                action_onPluginHandler.setToolTip(pluginsName)
            menu.setToolTipsVisible(True)
            menu.addAction(action_onPluginHandler)

    @Slot(int)
    def popUpMenuHandler(self, itemId, dataTreeView):
        m = self.menuIDS.PLUGINS_MENU_IDS[itemId]
        menuID = m[1]
        # if event.GetId() == menuID:
        pluginsName = m[0]
        entry = m[2]
        pluginsObject = m[3]

        # Run the plugins
        if type(pluginsObject) == QMainWindow:
            # If pluginsObject is QMainWindow type (indicating that the
            # plugin was provided as an instance of the user interface
            # (.ui file)
            logging.getLogger(dataTreeView.uri).info('Running plugin through instance of the use interface'
                         '(.ui) file.')
            # Find the main Qt designer widget (by widget object name)
            qdw = pluginsObject.findChild(QWidget, 'mainPluginWidget')

            # Get IDS object from IMASViz DTV
            dataTreeView.dataSource.load(dataTreeView,
                            IDSName=pluginsObject.targetIDSroot,
                            occurrence=pluginsObject.targetOccurrence,
                            asynch=False)
            
            # Show the plugin user interface
            pluginsObject.show()
        elif 'execute' in dir(pluginsObject):
            try:
                logging.getLogger(dataTreeView.uri).info('Executing plugin: ' + pluginsName)
                pluginsObject.execute(dataTreeView.imas_viz_api, entry)
            except:
                traceback.print_exc()
                logging.getLogger(dataTreeView.uri).error(traceback.format_exc())
        else:
            print("Unable to execute plugin: " + pluginsName +
                  ". Bad implementation provided by the plugin!")
