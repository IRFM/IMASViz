import wx
import importlib
from imasviz.util.GlobalValues import GlobalValues
from imasviz.plugins.VIZPlugins import VIZPlugins
from imasviz.util.GlobalOperations import GlobalOperations

class MenuIDS:
    def __init__(self):
        self.PLUGINS_MENU_IDS = [] #list of tuples (Id, menu desc., plugins object)

class PluginsHandler:

    def __init__(self, view):
        self.view = view
        self.menuIDS = MenuIDS()
        self.pluginsObjects = VIZPlugins.getPluginsObjects()

    def showPopUpMenu(self, subjectsList = None):
        self.view.popupmenu = wx.Menu()

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
                                tuple = (pluginsName, wx.NewId(), entry, pluginsObject)
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
            self.view.popupmenu.Append(menuId, pluginsCommandDescription)

        self.view.Bind(wx.EVT_MENU, self.popUpMenuHandler)
        return 1


    def popUpMenuHandler(self, event):
        for i in range(0, len(self.menuIDS.PLUGINS_MENU_IDS)):
            m = self.menuIDS.PLUGINS_MENU_IDS[i]
            menuID = m[1]
            if event.GetId() == menuID:
                pluginsName = m[0]
                entry = m[2]
                pluginsObject = m[3]
                allEntries = pluginsObject.getAllEntries()
                pluginsConfigurationsList = VIZPlugins.getPluginsConfiguration(pluginsName)
                pluginsConfiguration =  pluginsConfigurationsList[allEntries[entry][0]]
                pluginsObject.execute(wx.App(), pluginsConfiguration)


if __name__ == "__main__":
    app = wx.App(False)

    GlobalOperations.checkEnvSettings()
    from imasviz.data_source.DataSourceFactory import DataSourceFactory

    dataSourceFactory = DataSourceFactory()
    dataSource = dataSourceFactory.create(name=GlobalValues.IMAS_NATIVE, shotNumber=50355, runNumber=0, userName='imas_public', imasDbName='west_rawdata')
    from imasviz.Browser_API import Browser_API

    api = Browser_API()
    frame = api.CreateDataTree(dataSource)

    frame.Show()
    app.MainLoop()