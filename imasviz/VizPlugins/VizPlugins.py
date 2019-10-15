import importlib
import os, sys

from PyQt5.QtWidgets import QMainWindow

RegisteredPlugins = {'equilibriumcharts':'viz_equi.equilibriumcharts',
                     #'ToFuPlugin':'viz_tofu.viz_tofu_plugin',
                     'SOLPS_UiPlugin': '',
                     'CompareFLT1DPlugin':'viz_tests.CompareFLT1DPlugin',
                     'example_UiPlugin': ''
                     }

RegisteredPluginsConfiguration = {'SOLPS_UiPlugin':[{'UiFile': 'SOLPSplugin.ui',
                                'dir': os.environ['VIZ_HOME'] + '/imasviz/VizPlugins/viz_solps/',
                                'targetIDSroot': 'edge_profiles',
                                'targetOccurrence': 0}],
                                'example_UiPlugin': [{
                                'UiFile': 'examplePlugin.ui',
                                'dir': os.environ['VIZ_HOME'] + '/imasviz/VizPlugins/viz_example/',
                                'targetIDSroot': 'magnetics',
                                'targetOccurrence': 0}]}

# The 'overview' key should match the IDS name
# (for example: for edge_profiles IDS -> 'edge_profiles_overview')
EntriesPerSubject = {'SOLPS_UiPlugin':    {'edge_profiles_overview': [0],
                                           'overview': [0]},
                     'example_UiPlugin':  {'magnetics_overview': [0],
                                           'overview': [0]}
                     }

AllEntries = {'SOLPS_UiPlugin':    [(0, 'SOLPS overview...')], #(config number, description)
              'example_UiPlugin':  [(0, 'Magnetics overview...')]
              }


def getRegisteredPlugins():
    return RegisteredPlugins


class VizPlugins:
    def __init__(self):
        self.selectedTreeNode = None
        self.dataTreeView = None
        pass

    def setSelectedTreeNode(self, selectedTreeNode):
        self.selectedTreeNode = selectedTreeNode

    def setDataTreeView(self, dataTreeView):
        self.dataTreeView = dataTreeView

    def isEnabled(self):
        return False

    def getEntriesPerSubject(self):
        raise ValueError('plugin getEntriesPerSubject() method should be implemented!')

    def getAllEntries(self):
        entries = []
        entriesPerSubject = self.getEntriesPerSubject()
        for subject in entriesPerSubject:
            entries.append(entriesPerSubject[subject])

    def getSubjects(self):
        subjects = []
        entriesPerSubject = self.getEntriesPerSubject()
        if entriesPerSubject is None:
            return subjects
        for subject in entriesPerSubject:
            subjects.append(subject)
        return subjects

    def getPluginsConfiguration(self):
        raise ValueError('no plugin configuration defined. The method getPluginsConfiguration() should be implemented!')

    def execute(self, vizAPI):
        raise ValueError('plugin execute() method should be implemented!')

    def getMenuItem(self, subject):
        return self.getSubjects()[subject]

    @staticmethod
    def getPluginsObjects(dataTreeView=None, selectedTreeNode=None):
        pluginsNames = []
        importedObjectsList = []
        for key in getRegisteredPlugins():
            pluginsNames.append(key)

            # Check for plugins created by Qt designer (.ui files)
            if 'UiPlugin' in key:
                from PyQt5 import uic
                # Get directory where the plugin .ui file is located
                pluginConfiguration = VizPlugins.getPluginsConfigurationFor(key)[0]
                dir = pluginConfiguration['dir']
                # Get ui. file name
                UiFile = pluginConfiguration['UiFile']
                # Append to Python path
                sys.path.append(dir)
                # Set MainWindow
                w = QMainWindow(parent=dataTreeView)
                # Get IDS case object
                ids = None
                w.targetOccurrence = pluginConfiguration['targetOccurrence']
                w.targetIDSroot = pluginConfiguration['targetIDSroot']

                # Set an instance of the user interface
                uiObj = uic.loadUi(dir + UiFile, w)
                # Add the MainWindow (containing the user interface) to
                # list of imported objects
                importedObjectsList.append(w)
            else:
                mod = importlib.import_module('imasviz.VizPlugins.' +
                                              getRegisteredPlugins()[key])
                importedClass = getattr(mod, key)
                vizPluginObject = importedClass()
                vizPluginObject.setSelectedTreeNode(selectedTreeNode=selectedTreeNode)
                vizPluginObject.setDataTreeView(dataTreeView=dataTreeView)
                importedObjectsList.append(vizPluginObject)
        return pluginsNames, importedObjectsList

    @staticmethod
    def getPluginsNames():
        pluginsNames = []
        for key in RegisteredPlugins:
            pluginsNames.append(key)
        return pluginsNames

    @staticmethod
    def getPluginsConfigurationFor(pluginsName):
        return RegisteredPluginsConfiguration[pluginsName]

    @staticmethod
    def getEntriesPerSubjectFor(pluginsName):
        return EntriesPerSubject[pluginsName]

    @staticmethod
    def getSubjectsFor(pluginsName):
        subjects = []
        entriesPerSubject = VizPlugins.getEntriesPerSubjectFor(pluginsName)
        if entriesPerSubject is None:
            return subjects
        for subject in entriesPerSubject:
            subjects.append(subject)
        return subjects

    @staticmethod
    def getAllEntries(pluginsName):
        return AllEntries[pluginsName]
