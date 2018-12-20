
import importlib

from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues, GlobalIcons
from imasviz.VizPlugins.VizPlugins import VizPlugins
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from PyQt5.QtWidgets import QAction, QMenu,  QApplication

class MenuIDS:
    def __init__(self):
        self.PLUGINS_MENU_IDS = [] #list of tuples (Id, menu desc., plugins object)

class QVizPluginsHandler:

    def __init__(self, dataTreeView, dataDict):
        self.dataTreeView = dataTreeView
        self.dataDict = dataDict    # Passed item/subject
        self.menuIDS = MenuIDS()
        self.pluginsObjects = VizPlugins.getPluginsObjects()

    def showPopUpMenu(self, subjectsList = None):
        self.dataTreeView.popupmenu = QMenu()

        addedPluginsEntries = {}

        pluginsNames = self.pluginsObjects[0]
        pluginsObjects = self.pluginsObjects[1]

        for p in pluginsNames:
            addedPluginsEntries[p] = []  # each plugins entry should appear only once in the popup menu

        for subject in subjectsList:

            for i in range(0,len(pluginsNames)):
                pluginsName = pluginsNames[i]

                pluginsObject = pluginsObjects[i]
                subjects =  pluginsObject.getSubjects()
                subjects.sort()
                for subjectKey in subjects:
                    if subject == subjectKey:
                        entriesPerSubject = pluginsObject.getEntriesPerSubject()
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
            menuId = m[1]
            entry = m[2]
            pluginsObject = m[3]
            allEntries = pluginsObject.getAllEntries()
            pluginsCommandDescription = allEntries[entry][1]
            # print 'TESTING'
            # pluginsName = m[0]
            # print pluginsName
            # print menuId
            # print entry
            # print pluginsObject
            # print pluginsCommandDescription
            # self.dataTreeView.popupmenu.Append(menuId,
            #                                    pluginsCommandDescription)

            # Add action ...
            icon_onPluginHandler = GlobalIcons.getCustomQIcon(QApplication,
                                                              'new')
            action_onPluginHandler = QAction(icon_onPluginHandler,
                                             pluginsCommandDescription , self.dataTreeView)
            action_onPluginHandler.triggered.connect(self.popUpMenuHandler)
            # Add to submenu
            self.dataTreeView.popupmenu.addAction(action_onPluginHandler)

            # Map the menu (in order to show it)
            self.dataTreeView.popupmenu.exec_(
                self.dataTreeView.viewport().mapToGlobal(self.dataTreeView.pos))

        # self.dataTreeView.Bind(wx.EVT_MENU, self.popUpMenuHandler)
        return 1


    def popUpMenuHandler(self, event):
        for i in range(0, len(self.menuIDS.PLUGINS_MENU_IDS)):
            m = self.menuIDS.PLUGINS_MENU_IDS[i]
            menuID = m[1]
            # if event.GetId() == menuID:
            pluginsName = m[0]
            entry = m[2]
            pluginsObject = m[3]
            allEntries = pluginsObject.getAllEntries()
            pluginsConfigurationsList = VizPlugins.getPluginsConfiguration(pluginsName)
            pluginsConfiguration =  pluginsConfigurationsList[allEntries[entry][0]]
            pluginsConfiguration['imasviz_view'] = self.dataTreeView
            """Set ArraySize Plugin 'node_attributes' option
            (defined in the plugin definition .py file"""
            pluginsConfiguration['node_attributes'] = self.dataDict
            """Execute the plugins"""
            # pluginsObject.execute(wx.App(), pluginsConfiguration)
            pluginsObject.execute(pluginsConfiguration,
                                  dataTreeView=self.dataTreeView)
