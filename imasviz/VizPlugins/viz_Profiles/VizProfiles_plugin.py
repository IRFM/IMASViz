#  Name   : ETSpluginIMASViz
#
#           IMASViz wrapper for ETS plugin.
#
#  Author :
#         Dejan Penko
#  E-mail :
#         dejan.penko@lecad.fs.uni-lj.si
#
# ****************************************************
#     Copyright(c) 2019- D. Penko

import sys
import os

from imasviz.VizPlugins.VizPlugin import VizPlugin
from imasviz.VizPlugins.viz_Profiles.viz_profiles.VizProfiles import VizProfiles, Request
import logging
from PyQt5.QtWidgets import QMdiSubWindow
import traceback


class VizProfiles_plugin(VizPlugin):

    def __init__(self):
        self.data_entry = None
        self.IDS_parameters = {}
        self.supported_idss = ['edge_profiles', 'core_profiles', 'equilibrium', 'edge_profiles']

    def execute(self, vizAPI, pluginEntry):
        """Main plugin function.
        """
        try:
            # Get dataSource from the VizAPI (Application Program Interface)
            # Note: instance of "self.datatreeView" is provided by the VizPlugins
            # through inheritance
            dataSource = vizAPI.GetDataSource(self.dataTreeView)
            shot = dataSource.shotNumber
            run = dataSource.runNumber
            device = dataSource.imasDbName
            user = dataSource.userName
            occurrence = 0

            # Check if the IDS data is already loaded in IMASviz. If it is not,
            # load it (LoadListOfIDSs contains this IDS check strategy)
            selected_ids = self.selectedTreeNode.getIDSName()
            ids_list = [selected_ids]
            vizAPI.LoadListOfIDSs(self.dataTreeView, ids_list, occurrence)
            self.data_entry = dataSource.getImasEntry(occurrence)

            self.IDS_parameters["shot"] = shot
            self.IDS_parameters["run"] = run
            self.IDS_parameters["user"] = user
            self.IDS_parameters["database"] = device
            self.IDS_parameters["occurrence"] = occurrence
            
            if selected_ids == 'core_profiles':
                slices_aos_name = 'profiles_1d'
                list_of_filters = ['profiles_1d(0)/grid', 'profiles_1d(0)/electrons', 'global_quantities']
                tab_names = ['profiles_1d/grid', 'profiles_1d/electrons', 'global_quantities']
                
            if pluginEntry == 0:  #user has selected the first entry, so we call the first feature provided by the plugin
                strategy = 'COORDINATE1'
            elif pluginEntry == 1:
                strategy = 'TIME'
                
            request = Request(selected_ids, tab_names, list_of_filters, slices_aos_name, strategy)
            self.edge_profiles_main_window = VizProfiles(vizAPI, self.IDS_parameters, self.data_entry, self.dataTreeView, request)
            self.edge_profiles_main_window.show()

        except Exception as err:
            logging.error("ERROR! (%s)" % err, exc_info=True)
            traceback.print_exc()
            logging.error(traceback.format_exc())

    def getEntries(self):
        selected_ids = self.selectedTreeNode.getIDSName()
        if selected_ids in self.supported_idss:
            return [0, 1]

    def getPluginsConfiguration(self):
        return None

    def getAllEntries(self):
        """ Set a text which will be displayed in the pop-up menu.
        """
        selected_ids = self.selectedTreeNode.getIDSName()
        if selected_ids in self.supported_idss:
           return [(0, '0D/1D visualization along coordinate1 axis...'), (1, '0D/1D visualization along time axis...')]
        else:
            return []

    def getDescription(self):
        """ Return plugin description.
        """

        return "Visualization tool for 0D/1D IDS data. \n"           \
               "Author: Ludovic Fleury (ludovic.fleury@cea.fr)"

    def isEnabled(self):
        return True
