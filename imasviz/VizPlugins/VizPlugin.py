import importlib
import os, sys

from PyQt5.QtWidgets import QMainWindow

RegisteredPlugins = {'equilibriumcharts': 'viz_equi.equilibriumcharts',
                     # 'ToFuPlugin':'viz_tofu.viz_tofu_plugin',
                     # 'SOLPS_UiPlugin': '',
                     # 'CompareFLT1DPlugin':'viz_tests.CompareFLT1DPlugin',
                     # 'viz_example_plugin':'viz_example_plugin.viz_example_plugin',
                     # 'viz_spectrometer_plugin':'viz_spectrometer.viz_spectrometer_plugin',
                     'VizProfiles_plugin': 'viz_Profiles.VizProfiles_plugin',
                     # 'example_UiPlugin': '',
                     # 'simplePlotPluginExample' : 'viz_simple_plot_example.simplePlotPluginExample',
                     # 'ETSpluginIMASViz' : 'viz_ETS.ETSpluginIMASViz'
                     }


def getRegisteredPlugins():
    return RegisteredPlugins


class VizPlugin:
    def __init__(self, *args, **kwargs):
        if len(args) == 2:
            self.selectedTreeNode = args[0]
            self.dataTreeView = args[1]
        else:
            self.selectedTreeNode = None
            self.dataTreeView = None

    def setSelectedTreeNode(self, selectedTreeNode):
        self.selectedTreeNode = selectedTreeNode

    def setDataTreeView(self, dataTreeView):
        self.dataTreeView = dataTreeView

    def isEnabled(self):
        return False

    def getEntries(self):
        raise ValueError('plugin getEntries() method should be implemented!')

    def getAllEntries(self):
        raise ValueError('plugin getAllEntries() method should be implemented!')

    def execute(self, vizAPI, pluginEntry=None):
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
                pluginConfiguration = VizPlugin.getPluginsConfigurationFor(key)[0]
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
        RegisteredPluginsConfiguration = { \
            'SOLPS_UiPlugin': [{
                'UiFile': 'SOLPSplugin.ui',
                'dir': os.environ['VIZ_HOME'] + '/imasviz/VizPlugins/viz_solps/',
                'targetIDSroot': 'edge_profiles',
                'targetOccurrence': 0}],
            'example_UiPlugin': [{
                'UiFile': 'examplePlugin.ui',
                'dir': os.environ['VIZ_HOME'] + '/imasviz/VizPlugins/viz_example/',
                'targetIDSroot': 'magnetics',
                'targetOccurrence': 0}]}
        return RegisteredPluginsConfiguration[pluginsName]

    @staticmethod
    def getEntriesFor(pluginsName, vizTreeNode):
        if pluginsName == "SOLPS_UiPlugin" and vizTreeNode.getIDSName() == "edge_profiles":
            return [0]
        elif pluginsName == "example_UiPlugin" and vizTreeNode.getIDSName() == "magnetics":
            return [0]
        else:
            return []

    @staticmethod
    def getAllEntries(pluginsName):
        AllEntries = {'SOLPS_UiPlugin': [(0, 'SOLPS overview...')],  # (config number, description)
                      'example_UiPlugin': [(0, 'Magnetics overview...')]
                      }
        return AllEntries[pluginsName]
