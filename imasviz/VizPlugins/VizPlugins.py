import importlib
import os

# RegisteredPlugins = {'equilibriumcharts':'viz_equi.equilibriumcharts',
#                      'ECEOverviewPlugin':'viz_tests.ECE_OverviewPlugin',
#                      'TFOverviewPlugin':'viz_tests.TF_OverviewPlugin' }

RegisteredPlugins = {'equilibriumcharts':'viz_equi.equilibriumcharts',
                     'Ui_MainWindow': 'viz_solps.SOLPSPlugin'}

RegisteredPluginsConfiguration = {'equilibriumcharts':[{'time_i': 31.880, \
                          'time_e': 32.020, \
                          'delta_t': 0.02, \
                          'shot': 50642, \
                          'run': 0, \
                          'machine': 'west_equinox', \
                          'user': 'imas_private'}],
                          'Ui_MainWindow':[{}] }

WestRegisteredPlugins = {'equilibriumcharts':'viz_equi.equilibriumcharts',
                         'ToFuPlugin':'viz_tofu.viz_tofu_plugin'}

WestRegisteredPluginsConfiguration = {'equilibriumcharts':[{'time_i': 31.880, \
                          'time_e': 32.020, \
                          'delta_t': 0.02, \
                          'shot': 50642, \
                          'run': 0, \
                          'machine': 'west_equinox', \
                          'user': 'imas_private'}],
                          'ToFuPlugin':[{'geom':True},{'data':True},
                                         {'geom':True},{'data':True},
                                         {'geom':True},{'data':True}]}

EntriesPerSubject = {'equilibriumcharts': {'equilibrium_overview': [0], 'overview': [0]},
                     'ToFuPlugin': {'interferometer_overview': [0, 1],
                     'bolometer_overview': [2, 3],
                     'soft_x_rays_overview': [4, 5]},
                     'Ui_MainWindow': {'edge_profiles_overview':[0], 'overview':[0]}}

AllEntries = {'equilibriumcharts': [(0, 'Equilibrium overview...')],
              'ToFuPlugin': [(0, 'tofu - geom...'), (1, 'tofu - data'),
                             (2, 'tofu - geom...'), (3, 'tofu - data'),
                             (4, 'tofu - geom...'), (5, 'tofu - data')],
              'Ui_MainWindow': [(0, 'SOLPS overview...')]}
              #(config number, description)

def getRegisteredPlugins():
    if 'WEST' in os.environ and os.environ['WEST'] == 1:
        return WestRegisteredPlugins
    else:
        return RegisteredPlugins

def getRegisteredPluginsConfiguration():
    if 'WEST' in os.environ and os.environ['WEST'] == 1:
        return WestRegisteredPluginsConfiguration
    else:
        return RegisteredPluginsConfiguration


class VizPlugins():
    def __init__(self):
        pass

    def getEntriesPerSubject(self):
        pass

    def getAllEntries(self):
        pass

    def getSubjects(self, pluginsName):
        subjects = []
        entriesPerSubject = self.getEntriesPerSubject(pluginsName)
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
        for key in getRegisteredPlugins():
            pluginsNames.append(key)
            mod = importlib.import_module('imasviz.VizPlugins.' +
                                          getRegisteredPlugins()[key])
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
        return getRegisteredPluginsConfiguration()[pluginsName]

    @staticmethod
    def getEntriesPerSubject(pluginsName):
        return EntriesPerSubject[pluginsName]

    @staticmethod
    def getAllEntries(pluginsName):
        return AllEntries[pluginsName]


