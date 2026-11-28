# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The selection of a shot view.

The one record of the tree -- ``selectedSignalsDict`` -- and the verbs
that fill it: a selection from hand, from a file, or a whole group of one
AOS.
"""

from imasviz.VizUtils import QVizGlobalOperations


class QVizSelectionMixin:
    def GetSelectedNodes(self, DTV):
        """Returns the list of nodes selected by GUI or script commands.

        :param DTV: A QVizDataTreeViewFrame or QVizDataTreeView object
        :returns: (list) A list of QVizTreeNode objects.
        """
        from imasviz.VizGUI.VizTreeView import QVizDataTreeViewFrame
        dataTreeView = DTV
        if isinstance(DTV, QVizDataTreeViewFrame):
            dataTreeView = DTV.dataTreeView
        selectedNodes = []
        for key in dataTreeView.selectedSignalsDict:
            v = dataTreeView.selectedSignalsDict[key]
            vizTreeNode = v['QTreeWidgetItem']
            selectedNodes.append(vizTreeNode)
        return selectedNodes

    def GetSelectedSignalsDict(self, DTV):
        """Returns the list of signals (nodes) dictionaries selected by GUI or
        script commands.

        :param DTV: A QVizDataTreeViewFrame or QVizDataTreeView object
        :returns: (list) A list of signals (nodes) dictionaries.
        """
        from imasviz.VizGUI.VizTreeView import QVizDataTreeViewFrame
        dataTreeView = DTV
        if isinstance(DTV, QVizDataTreeViewFrame):
            dataTreeView = DTV.dataTreeView
        return dataTreeView.selectedSignalsDict

    def GetSelectedSignalsDictFromAllDTVs(self):
        """Returns the list of signals (nodes) dictionaries selected by GUI or
        script commands from all opened shot views (DTVs).

        :returns: (list) A list of signals (nodes) dictionaries
        """
        allSelectedSignals = {}
        for i in range(len(self.DTVframeList)):
            allSelectedSignals.update(
                self.DTVframeList[i].dataTreeView.selectedSignalsDict)

        return allSelectedSignals

    def SelectSignals(self, DTV, paths):
        """Select the nodes these paths name in the given shot view.

        The manual spells the argument as a plain list of node paths; a script
        written against the older dictionary of two parallel lists is still
        taken. Either way the selection is left by the same command that applies
        a saved node-configuration, so a scripted selection is shaped exactly
        like one made by hand in the tree -- and, as before, an IDS whose data
        are not in the tree yet is fetched first.

        :param DTV: a QVizDataTreeViewFrame object
        :param paths: a list of node paths (e.g.
                      ['magnetics/flux_loop(0)/flux/data']), a single path, or
                      the older map with 'paths' and 'occurrences'. Occurrences
                      are optional; one occurrence applies to every path.
        :returns: how many of the named nodes were found and selected
        """
        from imasviz.VizGUI.VizConfigurations.QVizConfigurationFile import \
            QVizConfigurationFile, QVizQuantity, SELECTION
        from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectFromConfiguration import QVizSelectFromConfiguration

        pathsList = paths.get('paths') if isinstance(paths, dict) else paths
        occurrences = paths.get('occurrences') if isinstance(paths, dict) else None
        if isinstance(pathsList, str):
            pathsList = [pathsList]
        pathsList = list(pathsList or [])
        occurrences = list(occurrences or [])
        if occurrences and len(occurrences) not in (1, len(pathsList)):
            raise ValueError('The number of specified occurrences differs from '
                             'the number of specified paths.')
        if len(occurrences) == 1:
            occurrences = occurrences * len(pathsList)

        quantities = [QVizQuantity(path=path,
                                  occurrence=int(occurrences[index])
                                  if occurrences else 0,
                                  row=None, column=None, uri=None)
                      for index, path in enumerate(pathsList)]
        configuration = QVizConfigurationFile(kind=SELECTION,
                                              quantities=quantities,
                                              spellPathsAsDocumented=True)
        return QVizSelectFromConfiguration(DTV.dataTreeView,
                                          configuration).execute()

    def UnSelectAllSignals(self, dataTreeFrame, all_DTV=False):
        """Unselects all previously selected signals for the given shot view.

        :param dataTreeFrame: A QVizDataTreeViewFrame object
        :param all_DTV: When True, all selected signals from all shot views are
                        unselected
        """
        from imasviz.VizGUI.VizGUICommands import QVizSelectNodes
        QVizSelectNodes(dataTreeFrame.dataTreeView,
                        all_DTV=all_DTV).unselectAll()

    def SelectSignalsGroup(self, dataTreeFrame, occurrence, onePathInTheGroup):
        """Selects nodes for this shot view.

        :param dataTreeFrame: A QVizDataTreeViewFrame object
        :param occurrence: the occurrence of an IDS
        :param onePathInTheGroup: An IDS path to one of the node
                                      (signals), containing a data array
                                      (e.g. FLT_1D), of which all siblings
                                      in the AOS are to be selected.
                                      Example:
                                      'magnetics/flux_loop(0)/flux/data'
        """
        # The two arguments are honoured: the body used to ignore both and take
        # whatever node the tree happened to have as its current item, so the
        # group selected had nothing to do with the path and occurrence asked for.
        from imasviz.VizGUI.VizGUICommands import QVizSelectNodes
        view = dataTreeFrame.dataTreeView
        path = QVizGlobalOperations.makeIMASPath(onePathInTheGroup)
        node = next((node for node in view.signalsList
                     if node.getPath() == path and
                     node.getOccurrence() == int(occurrence)),
                    view.selectedItem)
        QVizSelectNodes(view, node).sameAos()

