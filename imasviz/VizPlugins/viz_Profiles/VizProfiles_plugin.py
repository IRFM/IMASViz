# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import logging

from PySide6.QtWidgets import QInputDialog

from imasviz.VizPlugins.VizPlugin import VizPlugin, QVizPluginWindow
from imasviz.VizPlugins.viz_Profiles.viz_profiles.VizProfiles import VizProfiles, Request


class VizProfiles_plugin(VizPlugin):

    def __init__(self):
        self.edge_profiles_main_window = None
        #self.data_entry = None
        self.IDS_parameters = {}
        self.supported_idss = ['edge_profiles', 'core_profiles', 'equilibrium', 'core_sources', 'core_transport']

    def execute(self, vizAPI, pluginEntry, answers=None):
        """Main plugin function.

        `answers` is what a session replaying this entry already answered for the
        user: the occurrence and the key of the window. Without it the entry asks
        its question the way it always did; with it, nothing is asked, because a
        restore has no one in front of a modal `QInputDialog` (measured: a probe
        left to answer that one sat here for 240 s).
        """
        try:
            # Get dataSource from the VizAPI (Application Program Interface)
            # Note: instance of "self.datatreeView" is provided by the VizPlugins
            # through inheritance
            dataSource = vizAPI.GetDataSource(self.dataTreeView)
            selected_ids = self.selectedTreeNode.getIDSName()
            # Which occurrences this case holds is the opened case's answer, not
            # the data dictionary's. This was the sixth and last
            # `eval("imas." + ids + "().getMaxOccurrences()")` in the package, and
            # on this IMAS-Python it answered AttributeError -- which the except
            # below then hid behind a logging error of its own, so the entry looked
            # like a logging bug rather than an impossible question.
            occurrences = self.dataTreeView.occurrences.occurrencesOf(
                selected_ids)
            if not occurrences:
                raise ValueError('the opened case holds no occurrence of the %s '
                                 'IDS, so there are no profiles to plot.'
                                 % selected_ids)

            occurrence = occurrences[0]
            if answers is not None:
                occurrence = answers.occurrence
            elif len(occurrences) > 1:
                occurrence = self.askForOccurrence(selected_ids, occurrences)


            # Check if the IDS data is already loaded in IMASviz. If it is not,
            # load it (LoadListOfIDSs contains this IDS check strategy)
            
            ids_list = [selected_ids]
            vizAPI.LoadListOfIDSs(self.dataTreeView, ids_list, occurrence)

            #self.data_entry = imas.DBEntry(dataSource.uri, 'r')

            self.IDS_parameters["uri"] = dataSource.uri
            self.IDS_parameters["occurrence"] = occurrence

            if pluginEntry == 0:  # user has selected the first entry, so we call the first feature provided by the
                # plugin
                plotAxis = 'COORDINATE1'
            elif pluginEntry == 1:
                plotAxis = 'TIME'
            elif pluginEntry == 2:
                plotAxis = 'COORDINATE1'
            elif pluginEntry == 3:
                plotAxis = 'TIME'

            requests_list = []

            if selected_ids == 'core_profiles':
                slices_aos_name = 'profiles_1d'

                list_of_filters = ['profiles_1d(0)/grid', 'profiles_1d(0)/electrons', 'profiles_1d(0)/ion',
                                   'profiles_1d(0)/neutral', 'profiles_1d(0)/t_i_average',
                                   'profiles_1d(0)/n_i', 'profiles_1d(0)/momentum_tor', 'profiles_1d(0)/zeff',
                                   'profiles_1d(0)/pressure', 'profiles_1d(0)/j_',
                                   'profiles_1d(0)/conductivity_parallel', 'profiles_1d(0)/current_parallel_inside',
                                   'profiles_1d(0)/e_field', 'profiles_1d(0)/q',
                                   'profiles_1d(0)/rotation', 'profiles_1d(0)/phi_potential',
                                   'profiles_1d(0)/magnetic_shear']
                tab_names = ['profiles_1d/grid', 'profiles_1d/electrons', 'profiles_1d/ion', 'profiles_1d/neutral',
                             'profiles_1d/t_i_average', 'profiles_1d/n_i', 'profiles_1d/momentum_tor',
                             'profiles_1d/zeff', 'profiles_1d/pressure', 'profiles_1d/j',
                             'profiles_1d/conductivity_parallel', 'profiles_1d/current_parallel_inside',
                             'profiles_1d/e_field', 'profiles_1d/q',
                             'profiles_1d/rotation', 'profiles_1d/phi_potential', 'profiles_1d/magnetic_shear']

                if self.data_found(dataSource=dataSource, treeNode=self.selectedTreeNode, ids_name=selected_ids, dynamic_aos_name=slices_aos_name):
                    request = Request(selected_ids, tab_names, list_of_filters, slices_aos_name, plotAxis)
                    requests_list.append(request)

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

                if self.data_found(dataSource=dataSource, treeNode=self.selectedTreeNode, ids_name=selected_ids, dynamic_aos_name=slices_aos_name):
                    request = Request(selected_ids, tab_names, list_of_filters, slices_aos_name, plotAxis)
                    requests_list.append(request)

            elif selected_ids == 'equilibrium':
                slices_aos_name = 'time_slice'
                list_of_filters = ['time_slice(0)/boundary', 'time_slice(0)/constraints', 'time_slice(0)/profiles_1d',
                                   'time_slice(0)/profiles_2d', 'time_slice(0)/global_quantities',
                                   'time_slice(0)/coordinate_system', 'time_slice(0)/convergence']
                tab_names = ['time_slice/boundary', 'time_slice/constraints', 'time_slice/profiles_1d',
                             'time_slice/profiles_2d', 'time_slice/global_quantities', 'time_slice/coordinate_system',
                             'time_slice/convergence']

                
                if self.data_found(dataSource=dataSource, treeNode=self.selectedTreeNode, ids_name=selected_ids, dynamic_aos_name=slices_aos_name):
                    request = Request(selected_ids, tab_names, list_of_filters, slices_aos_name, plotAxis)
                    requests_list.append(request)

            elif selected_ids == 'core_sources':
                source_index_max = len(dataSource.data_entry.core_sources.source) - 1
                for source_index in range(source_index_max):
                    list_of_filters = []
                    tab_names = []
                    if pluginEntry == 0 or pluginEntry == 1:
                        slices_aos_name = 'source[' + str(source_index) + '].global_quantities'
                        list_of_filters.append('source(' + str(source_index) + ')/global_quantities(0)')
                        tab_names.append('source(' + str(source_index) + ')/global_quantities')
                    else:
                        slices_aos_name = 'source[' + str(source_index) + '].profiles_1d'
                        list_of_filters.append('source(' + str(source_index) + ')/profiles_1d(0)')
                        tab_names.append('source(' + str(source_index) + ')/profiles_1d')

                    if self.data_found(dataSource=dataSource, treeNode=self.selectedTreeNode, ids_name=selected_ids,
                                       dynamic_aos_name=slices_aos_name):
                        request = Request(selected_ids, tab_names, list_of_filters,
                                          slices_aos_name, plotAxis, source_index)
                        requests_list.append(request)

            elif selected_ids == 'core_transport':
                model_index_max = len(dataSource.data_entry.core_transport.model) - 1
                list_of_filters = []
                tab_names = []
                for model_index in range(model_index_max):
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

                    if self.data_found(dataSource=dataSource, treeNode=self.selectedTreeNode, ids_name=selected_ids,
                                       dynamic_aos_name=slices_aos_name):
                        request = Request(selected_ids, tab_names, list_of_filters, slices_aos_name,
                                          plotAxis, model_index)
                        requests_list.append(request)

            if len(requests_list) > 0:
                self.edge_profiles_main_window = VizProfiles(
                    vizAPI, self.IDS_parameters, self.selectedTreeNode,
                    self.dataTreeView, requests_list, selected_ids, plotAxis,
                    figureKey=None if answers is None else answers.figureKey)
                # What a session needs to put this window back, and the only
                # place it exists: measured, the panel answers neither `figureKey`
                # nor `key`, and the entry number and the occurrence it settled on
                # live nowhere but here.
                self.edge_profiles_main_window.pluginWindow = QVizPluginWindow(
                    uri=dataSource.uri, plugin='VizProfiles_plugin',
                    entry=pluginEntry, ids=selected_ids,
                    occurrence=occurrence)
            else:
                message = "No profiles found for " + selected_ids + " IDS."
                logging.getLogger(self.dataTreeView.uri).warning(message)
            # self.edge_profiles_main_window.show()

        except Exception as error:
            # Chaining a second getLogger onto the first answered `AttributeError:
            # 'Logger' object has no attribute 'getLogger'`, so the failure of the
            # entry never reached the log panel -- what the user read instead was a
            # logging error, and the traceback went to stdout. One line, on the log
            # of the case this view is reading, is what the panel shows.
            logging.getLogger(self.dataTreeView.uri).error(
                'The profiles panel could not be built: %s: %s'
                % (type(error).__name__, error))

    def askForOccurrence(self, idsName, occurrences):
        """Which occurrence to plot, asked of the view that owns the menu.

        Bounded by what the opened case holds and parented to that view: the spin
        box used to run from 0 to `maxOccurrences` -- one past the last valid
        occurrence -- and had no parent, so it appeared over whichever window Qt
        picked, and refusing it logged "Bad input from user" about a case nobody
        had named.
        """
        box = QInputDialog(self.dataTreeView)
        occ, ok = box.getInt(self.dataTreeView,
                             'Which occurrence of the %s IDS?' % idsName,
                             'Occurrence:', occurrences[0], occurrences[0],
                             occurrences[-1])
        if not ok:
            logging.getLogger(self.dataTreeView.uri).info(
                'No occurrence chosen: plotting occurrence %d.' % occurrences[0])
            return occurrences[0]
        return occ

    def data_found(self, dataSource, treeNode, ids_name, dynamic_aos_name):
        """Whether the loaded occurrence holds anything in the array to plot.

        Spelled as a call. It used to build a variable name with `exec` and read
        it back with `eval`, which is two ways for the same object to go missing
        with no name to blame -- and the value it produced lived in the local
        frame of the `exec`, not anywhere the reader could see it.
        """
        idsInstance = dataSource.get(ids_name, self.IDS_parameters['occurrence'])
        if idsInstance is None:
            return False
        return len(getattr(idsInstance, dynamic_aos_name)) != 0

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
