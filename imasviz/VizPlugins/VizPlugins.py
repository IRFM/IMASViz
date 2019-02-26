import importlib
import os, sys

from PyQt5.QtWidgets import QMainWindow

# RegisteredPlugins = {'equilibriumcharts':'viz_equi.equilibriumcharts',
#                      'ECEOverviewPlugin':'viz_tests.ECE_OverviewPlugin',
#                      'TFOverviewPlugin':'viz_tests.TF_OverviewPlugin' }

RegisteredPlugins = {'equilibriumcharts':'viz_equi.equilibriumcharts',
                     'SOLPS_UiPlugin': {
                         'UiFile': 'designer_SOLPSPlugin.ui',
                         'dir': os.environ['VIZ_HOME'] +
                                '/imasviz/VizPlugins/viz_solps/'}}

RegisteredPluginsConfiguration = {'equilibriumcharts':[{'time_i': 31.880, \
                          'time_e': 32.020, \
                          'delta_t': 0.02, \
                          'shot': 50642, \
                          'run': 0, \
                          'machine': 'west_equinox', \
                          'user': 'imas_private'}],
                          'SOLPS_UiPlugin':[{}] }

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
                     'SOLPS_UiPlugin': {'edge_profiles_overview':[0],
                                       'overview':[
                         0]}}

AllEntries = {'equilibriumcharts': [(0, 'Equilibrium overview...')],
              'ToFuPlugin': [(0, 'tofu - geom...'), (1, 'tofu - data'),
                             (2, 'tofu - geom...'), (3, 'tofu - data'),
                             (4, 'tofu - geom...'), (5, 'tofu - data')],
              'SOLPS_UiPlugin': [(0, 'SOLPS overview...')]}
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
    def getPluginsObjects(dataTreeView=None):
        pluginsNames = []
        importedObjectsList = []
        for key in getRegisteredPlugins():
            pluginsNames.append(key)

            # Check for plugins created by Qt designer (.ui files)
            if 'UiPlugin' in key:
                from PyQt5 import uic
                # Get directory where the plugin .ui file is located
                dir = getRegisteredPlugins()[key]['dir']
                # Get ui. file name
                UiFile = getRegisteredPlugins()[key]['UiFile']
                # Append to Python path
                sys.path.append(dir)
                # Set MainWindow
                w = QMainWindow(parent=dataTreeView)
                # Set an instance of the user interface
                uiObj = uic.loadUi(dir + UiFile, w)
                # Add the MainWindow (containing the user interface) to
                # list of imported objects
                importedObjectsList.append(w)
            else:
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
