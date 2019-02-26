
import importlib

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

            for i in range(0,len(pluginsNames)):
                pluginsName = pluginsNames[i]

                pluginsObject = pluginsObjects[i]
                subjects =  VizPlugins().getSubjects(pluginsName=pluginsName)
                subjects.sort()
                for subjectKey in subjects:
                    if subject == subjectKey:
                        entriesPerSubject = \
                            VizPlugins.getEntriesPerSubject(pluginsName)
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
            allEntries = VizPlugins.getAllEntries(pluginsName)
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
            allEntries = VizPlugins.getAllEntries(pluginsName)
            pluginsConfigurationsList = VizPlugins.getPluginsConfiguration(
                pluginsName)
            pluginsConfiguration =  pluginsConfigurationsList[allEntries[entry][0]]
            pluginsConfiguration['imasviz_view'] = self.dataTreeView
            # Set ArraySize Plugin 'node_attributes' option
            # (defined in the plugin definition .py file
            pluginsConfiguration['node_attributes'] = self.infoDict
            # Run the plugins
            if type(pluginsObject) == QMainWindow:
                # If pluginsObject is QMainWindow type (indicating that the
                # plugin was provided as an instance of the user interface
                # (.ui file)
                self.dataTreeView.log.info('Running plugin as instance of the '
                                           'user interface (.ui) file.')
                # Find the main Qt designer widget (by widget object name)
                qdw = pluginsObject.findChild(QWidget, 'SOLPSwidget')

                # Set DTV (mandatory if the IDS loaded in the DTV is to be
                # passed to the plugin
                qdw.dataTreeView = self.dataTreeView
                # Set flag that the plugin is being used within IMASViz
                qdw.usingIMASViz = True
                # Show the plugin user interface
                pluginsObject.show()
            elif 'execute' in dir(pluginsObject):
                self.dataTreeView.log.info('Running plugin with execute.')
                # pluginsObject.execute(wx.App(), pluginsConfiguration)
                pluginsObject.execute(pluginsConfiguration,
                                      dataTreeView=self.dataTreeView)
            else:
                print('No proper instance of user interface or execute routine '
                      'provided by the plugin!')


