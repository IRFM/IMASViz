#  Name   : VizProfiles_plugin
#
#           IMASViz plugin for visualizing profiles.
#
#  Author :
#         Ludovic Fleury
#  E-mail :
#         ludovic.fleury@cea.fr
#
# ****************************************************
#     Copyright(c) 2022- L. Fleury

import sys
import os

from imasviz.VizPlugins.VizPlugin import VizPlugin
from imasviz.VizPlugins.viz_Profiles.viz_profiles.VizProfiles import VizProfiles, Request
import logging
from PySide2.QtWidgets import QMdiSubWindow, QInputDialog
import traceback


class VizProfiles_plugin(VizPlugin):

    def __init__(self):
        self.edge_profiles_main_window = None
        self.data_entry = None
        self.IDS_parameters = {}
        self.supported_idss = ['edge_profiles', 'core_profiles', 'equilibrium', 'core_sources', 'core_transport']

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
                list_of_filters = ['profiles_1d(0)/grid', 'profiles_1d(0)/electrons', 'profiles_1d(0)/ion',
                                   'profiles_1d(0)/neutral', 'profiles_1d(0)/t_i_average',
                                   'profiles_1d(0)/n_i', 'profiles_1d(0)/momentum_tor', 'profiles_1d(0)/zeff',
                                   'profiles_1d(0)/pressure', 'profiles_1d(0)/j_',
                                   'profiles_1d(0)/conductivity_parallel', 'profiles_1d(0)/e_field',
                                   'profiles_1d(0)/rotation', 'profiles_1d(0)/q', 'profiles_1d(0)/magnetic_shear']
                tab_names = ['profiles_1d/grid', 'profiles_1d/electrons', 'profiles_1d/ion', 'profiles_1d/neutral',
                             'profiles_1d/t_i_average', 'profiles_1d/n_i', 'profiles_1d/momentum_tor',
                             'profiles_1d/zeff', 'profiles_1d/pressure', 'profiles_1d/j',
                             'profiles_1d/conductivity_parallel', 'profiles_1d/e_field',
                             'profiles_1d/rotation', 'profiles_1d/q', 'profiles_1d/magnetic_shear']

            elif selected_ids == 'edge_profiles':
                slices_aos_name = 'profiles_1d'
                list_of_filters = ['profiles_1d(0)/grid', 'profiles_1d(0)/electrons', 'profiles_1d(0)/ion',
                                   'profiles_1d(0)/neutral', 'profiles_1d(0)/t_i_average',
                                   'profiles_1d(0)/n_i', 'profiles_1d(0)/momentum_tor', 'profiles_1d(0)/zeff',
                                   'profiles_1d(0)/pressure', 'profiles_1d(0)/j_',
                                   'profiles_1d(0)/current_parallel_inside',
                                   'profiles_1d(0)/conductivity_parallel', 'profiles_1d(0)/e_field',
                                   'profiles_1d(0)/rotation', 'profiles_1d(0)/q', 'profiles_1d(0)/magnetic_shear',
                                   'profiles_1d(0)/phi_potential']
                tab_names = ['profiles_1d/grid', 'profiles_1d/electrons', 'profiles_1d/ion', 'profiles_1d/neutral',
                             'profiles_1d/t_i_average', 'profiles_1d/n_i', 'profiles_1d/momentum_tor',
                             'profiles_1d/zeff', 'profiles_1d/pressure', 'profiles_1d/j',
                             'profiles_1d/current_parallel_inside',
                             'profiles_1d/conductivity_parallel', 'profiles_1d/e_field', 'profiles_1d/rotation',
                             'profiles_1d/q', 'profiles_1d/magnetic_shear', 'profiles_1d/phi_potential']

            elif selected_ids == 'equilibrium':
                slices_aos_name = 'time_slice'
                list_of_filters = ['time_slice(0)/boundary', 'time_slice(0)/constraints', 'time_slice(0)/profiles_1d',
                                   'time_slice(0)/profiles_2d', 'time_slice(0)/global_quantities',
                                   'time_slice(0)/coordinate_system', 'time_slice(0)/convergence']
                tab_names = ['time_slice/boundary', 'time_slice/constraints', 'time_slice/profiles_1d',
                             'time_slice/profiles_2d', 'time_slice/global_quantities', 'time_slice/coordinate_system',
                             'time_slice/convergence']

            elif selected_ids == 'core_sources':
                user_input = QInputDialog()
                source_index_max = len(self.data_entry.core_sources.source) - 1
                source_index = 0
                if source_index_max > 0:
                    user_input.resize(400, 200)
                    source_index, ok = user_input.getInt(None, "Source index:", "Index:",
                                                         value=source_index_max, min=0, max=source_index_max)
                    if not ok:
                        logging.error("Cancelled or bad input from user.")
                        return

                if pluginEntry == 0 or pluginEntry == 1:
                    slices_aos_name = 'source[' + str(source_index) + '].global_quantities'
                    list_of_filters = ['source(' + str(source_index) + ')/global_quantities(0)']
                    tab_names = ['source(' + str(source_index) + ')/global_quantities']
                else:
                    slices_aos_name = 'source[' + str(source_index) + '].profiles_1d'
                    list_of_filters = ['source(' + str(source_index) + ')/profiles_1d(0)']
                    tab_names = ['source(' + str(source_index) + ')/profiles_1d']

            elif selected_ids == 'core_transport':
                user_input = QInputDialog()
                model_index_max = len(self.data_entry.core_transport.model) - 1
                model_index = 0
                if model_index_max > 0:
                    user_input.resize(400, 200)
                    model_index, ok = user_input.getInt(None, "Model index:", "Index:",
                                                        value=model_index_max, min=0, max=model_index_max)
                    if not ok:
                        logging.error("Cancelled by user or bad input.")
                        return

                if pluginEntry == 0 or pluginEntry == 1:
                    slices_aos_name = 'model[' + str(model_index) + '].profiles_1d'
                    model = 'model(' + str(model_index) + ')'
                    profile = model + '/profiles_1d(0)'
                    list_of_filters = [profile + '/grid', profile + '/conductivity', profile + '/electrons',
                                       profile + '/total_ion', profile + '/momentum', profile + '/e_field',
                                       profile + '/ion', profile + '/neutral']
                    tab_name = 'model(' + str(model_index) + ')/profiles_1d'
                    tab_names = [tab_name + '/grid', tab_name + '/conductivity', tab_name + '/electrons',
                                 tab_name + '/total_ion', tab_name + '/momentum', tab_name + '/e_field',
                                 tab_name + '/ion', tab_name + '/neutral']

            if pluginEntry == 0:  # user has selected the first entry, so we call the first feature provided by the
                # plugin
                strategy = 'COORDINATE1'
            elif pluginEntry == 1:
                strategy = 'TIME'
            elif pluginEntry == 2:
                strategy = 'COORDINATE1'
            elif pluginEntry == 3:
                strategy = 'TIME'

            request = Request(selected_ids, tab_names, list_of_filters, slices_aos_name, strategy)
            self.edge_profiles_main_window = VizProfiles(vizAPI, self.IDS_parameters, self.data_entry,
                                                         self.dataTreeView, request)
            # self.edge_profiles_main_window.show()

        except Exception as err:
            logging.error("ERROR! (%s)" % err, exc_info=True)
            traceback.print_exc()
            logging.error(traceback.format_exc())

    def getEntries(self):
        selected_ids = self.selectedTreeNode.getIDSName()
        if selected_ids in self.supported_idss:
            if selected_ids == 'core_sources':
                return [0, 1, 2, 3]
            else:
                return [0, 1]

    def getPluginsConfiguration(self):
        return None

    def getAllEntries(self):
        """ Set a text which will be displayed in the pop-up menu.
        """
        selected_ids = self.selectedTreeNode.getIDSName()
        if selected_ids in self.supported_idss:
            if selected_ids == 'core_sources':
                return [(0, 'Visualization of 1D nodes from source(i1)/global_quantities(itime) along coordinate1 '
                            'axis...'),
                        (1, 'Visualization of 0D/1D nodes from source(i1)/global_quantities(itime) along time axis...'),
                        (2, 'Visualization of 1D nodes from source(i1)/profiles_1d(itime) along coordinate1 axis...'),
                        (3, 'Visualization of 0D/1D nodes from  source(i1)/profiles_1d(itime) along time axis...')]
            elif selected_ids == 'core_transport':
                return [(0, 'Visualization of 1D nodes from model(i1)/profiles_1d(itime) along coordinate1 axis...'),
                        (1, 'Visualization of 0D/1D nodes from model(i1)/profiles_1d(itime) along time axis...')]
            elif selected_ids == 'core_profiles' or selected_ids == 'edge_profiles':
                return [(0, 'Visualization of 1D nodes from profiles_1d(itime) along coordinate1 axis...'),
                        (1, 'Visualization of 0D/1D nodes from profiles_1d(itime) along time axis...')]
            elif selected_ids == 'equilibrium':
                return [(0, 'Visualization of 1D nodes from time_slice(itime) along coordinate1 axis...'),
                        (1, 'Visualization of 0D/1D nodes from time_slice(itime) along time axis...')]
            else:
                pass
        else:
            return []

    def getDescription(self):
        """ Return plugin description.
        """

        return "Make 0D/1D plots from IDS data arrays embedded in dynamic array of structures. \n" \
               "Author: Ludovic Fleury (ludovic.fleury@cea.fr)"

    def isEnabled(self):
        return True
