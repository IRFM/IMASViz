
import importlib, logging

from functools import partial
from PyQt5.QtCore import QObject, pyqtSlot
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues, GlobalIcons
from imasviz.VizPlugins.VizPlugins import VizPlugins
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from PyQt5.QtWidgets import QAction, QMenu,  QApplication, QMainWindow, QWidget

class MenuIDS:
    def __init__(self):
        self.PLUGINS_MENU_IDS = [] #list of tuples (Id, menu desc., plugins object)

class QVizPluginsHandler:

    def __init__(self, dataTreeView, dataDict):
        self.dataTreeView = dataTreeView
        self.infoDict = dataDict    # Passed item/subject
        self.menuIDS = MenuIDS()
        self.pluginsObjects = VizPlugins.getPluginsObjects(
            dataTreeView=self.dataTreeView)

    def showPopUpMenu(self, subjectsList = None):
        self.dataTreeView.popupmenu = QMenu()

        addedPluginsEntries = {}

        pluginsNames = self.pluginsObjects[0]
        pluginsObjects = self.pluginsObjects[1]

        for p in pluginsNames:
            addedPluginsEntries[p] = []  # each plugins entry should appear only once in the popup menu

        for subject in subjectsList:

            for i in range(0, len(pluginsNames)):
                pluginsName = pluginsNames[i]
                pluginsObject = pluginsObjects[i]

                if isinstance(pluginsObject, VizPlugins):
                    if not pluginsObject.isEnabled():
                        continue

                if isinstance(pluginsObject, VizPlugins):
                    subjects = pluginsObject.getSubjects()
                else:
                    subjects = VizPlugins.getSubjectsFor(pluginsName)
                subjects.sort()
                for subjectKey in subjects:
                    if subject == subjectKey:
                        if isinstance(pluginsObject, VizPlugins):
                            entriesPerSubject = pluginsObject.getEntriesPerSubject()
                        else:
                            entriesPerSubject = VizPlugins.getEntriesPerSubjectFor(pluginsName)
                        entriesList = entriesPerSubject[subject] #list of entry index (ex: [0,1])
                        for entry in entriesList:
                            if entry not in addedPluginsEntries[pluginsName]:
                                # TODO: properly set ID
                                new_id = 9999
                                tuple = (pluginsName, new_id, entry,
                                         pluginsObject)
                                self.menuIDS.PLUGINS_MENU_IDS.append(tuple)
                                addedPluginsEntries[pluginsName].append(entry) #plugins entry should appear only once in the popup menu

        #print self.menuIDS.PLUGINS_MENU_IDS
        for i in range(0, len(self.menuIDS.PLUGINS_MENU_IDS)):
            m = self.menuIDS.PLUGINS_MENU_IDS[i]
            pluginsName = m[0]
            menuId = m[1]
            entry = m[2]
            pluginsObject = m[3]
            allEntries = []
            if isinstance(pluginsObject, VizPlugins):
                allEntries = pluginsObject.getAllEntries()
            else:
                allEntries = VizPlugins.getAllEntries(pluginsName)

            pluginsCommandDescription = allEntries[entry][1]

            # Add action ...
            icon_onPluginHandler = GlobalIcons.getCustomQIcon(QApplication,
                                                              'new')
            action_onPluginHandler = QAction(icon_onPluginHandler,
                                             pluginsCommandDescription , self.dataTreeView)
            action_onPluginHandler.triggered.connect(partial(self.popUpMenuHandler, i))
            # Add to submenu
            self.dataTreeView.popupmenu.addAction(action_onPluginHandler)

        # Map the menu (in order to show it)
        self.dataTreeView.popupmenu.exec_(
                self.dataTreeView.viewport().mapToGlobal(self.dataTreeView.pos))

        return 1

    @pyqtSlot(int)
    def popUpMenuHandler(self, itemId):
        m = self.menuIDS.PLUGINS_MENU_IDS[itemId]
        menuID = m[1]
        # if event.GetId() == menuID:
        pluginsName = m[0]
        entry = m[2]
        pluginsObject = m[3]

        allEntries = None
        pluginsConfigurationsList = None

        if isinstance(pluginsObject, VizPlugins):
            allEntries = pluginsObject.getAllEntries()
            pluginsConfigurationsList = pluginsObject.getPluginsConfiguration()

        else:
            allEntries = VizPlugins.getAllEntries(pluginsName)
            pluginsConfigurationsList = VizPlugins.getPluginsConfigurationFor(
                pluginsName)

        pluginsCommandDescription = allEntries[entry][1]

        pluginsConfiguration = pluginsConfigurationsList[allEntries[entry][0]]
        pluginsConfiguration['imasviz_view'] = self.dataTreeView
        # Set ArraySize Plugin 'node_attributes' option
        # (defined in the plugin definition .py file
        pluginsConfiguration['node_attributes'] = self.infoDict
        # Run the plugins
        if type(pluginsObject) == QMainWindow:
            # If pluginsObject is QMainWindow type (indicating that the
            # plugin was provided as an instance of the user interface
            # (.ui file)
            logging.info('Running plugin through instance of '
                                       'the user interface (.ui) file.')
            # Find the main Qt designer widget (by widget object name)
            qdw = pluginsObject.findChild(QWidget, 'mainPluginWidget')

            # Get IDS object from IMASViz DTV
            # - Get data source
            dataSource = self.dataTreeView.dataSource
            # - get IDS object
            try:
                ids = dataSource.ids[pluginsObject.targetOccurrence]
            except:
                ids = None
            if ids is None:
                # -Get IDS object for target IDS root and target occurrence
                # Note: This will also populate and update the IDS tree view
                #       structure
                dataSource.load(self.dataTreeView,
                                IDSName=pluginsObject.targetIDSroot,
                                occurrence=pluginsObject.targetOccurrence,
                                asynch=False)
                # Set IDS
                ids = dataSource.ids[pluginsObject.targetOccurrence]

            # Set IDS object for the main Qt designer widget
            qdw.setIDS(ids)


            # Show the plugin user interface
            pluginsObject.show()
        elif 'execute' in dir(pluginsObject):
            logging.info('Executing plugin...')
            pluginsObject.execute(pluginsConfiguration,
                                  dataTreeView=self.dataTreeView)
        else:
            print('No proper instance of user interface or execute routine '
                  'provided by the plugin!')
>>>>>>> develop


