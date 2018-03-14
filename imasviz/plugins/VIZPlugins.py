import importlib

# RegisteredPlugins = {'equilibriumcharts':'viz_equi.equilibriumcharts',
#                      'ECEOverviewPlugin':'viz_tests.ECE_OverviewPlugin',
#                      'TFOverviewPlugin':'viz_tests.TF_OverviewPlugin' }

RegisteredPlugins = {'equilibriumcharts':'viz_equi.equilibriumcharts',
                     'ArraySizePlugin': 'viz_array_size.array_size_plugin',
                     'ToFuPlugin':'viz_tofu.viz_tofu_plugin'}

RegisteredPluginsConfiguration = {'equilibriumcharts':[{'time_i': 31.880, \
                          'time_e': 32.020, \
                          'delta_t': 0.02, \
                          'shot': 50642, \
                          'run': 0, \
                          'machine': 'west_equinox', \
                          'user': 'imas_private'}],
                          'ECEOverviewPlugin':[{'param1':1, 'param2':2}, {'param1':3, 'param2':4}],
                          'TFOverviewPlugin':[{}],
                          'ArraySizePlugin':[{}, {'size_request':1}],
                          'ToFuPlugin':[{'geom':True},{'data':True},
                                        {'geom':True},{'data':True},
                                        {'geom':True},{'data':True}]}

class VIZPlugins():
    def __init__(self):
        pass

    def getEntriesPerSubject(self):
        pass

    def getAllEntries(self):
        pass

    def getSubjects(self):
         subjects = []
         entriesPerSubject = self.getEntriesPerSubject()
         for subject in entriesPerSubject:
             subjects.append(subject)
         return subjects

    def execute(self):
        pass

    def getMenuItem(self, subject):
        return self.getSubjects()[subject]

    @staticmethod
    def getPluginsObjects():
        pluginsNames = []
        importedObjectsList = []
        for key in RegisteredPlugins:
            pluginsNames.append(key)
            mod = importlib.import_module('imasviz.plugins.' + RegisteredPlugins[key])
            importedClass = getattr(mod, key)
            importedObjectsList.append(importedClass())
        return (pluginsNames, importedObjectsList)

    @staticmethod
    def getPluginsNames():
        pluginsNames = []
        for key in RegisteredPlugins:
            pluginsNames.append(key)
        return pluginsNames

    @staticmethod
    def getPluginsConfiguration(pluginsName):
        return RegisteredPluginsConfiguration[pluginsName]
