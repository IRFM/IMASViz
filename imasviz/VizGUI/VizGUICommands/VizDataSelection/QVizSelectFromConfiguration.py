# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Selecting the quantities a configuration file names.

The manual promises that a selection saved from one database can be applied to
any other opened one. Applying it means three things, in order: the IDS a path
belongs to has to be in the tree, so it is loaded when it is not; the path has
to name a node this tree holds; and the node is selected by the one command that
selects, so the selection this leaves is shaped exactly like one the user made
by hand.

The path matching is done against the paths the tree spells, and the file's
paths are converted once, by the format -- the command that used to do this took
a dictionary of two parallel lists, rewrote the caller's list on the way in
(measured: a caller handing over ``['foo.time_slice[i].vector']`` got back
``['foo/time_slice(i)/vector']`` in its own dictionary), and answered a file
naming three paths and two occurrences with ``IndexError: list index out of
range`` instead of the reason its own code states two lines later.
"""

import logging

from imasviz.VizGUI.VizConfigurations.QVizConfigurationFile import \
    QVizConfigurationFile
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadSelectedData \
    import QVizLoadSelectedData
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectNodes \
    import QVizSelectNodes
from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand


class QVizSelectFromConfiguration(QVizAbstractCommand):
    """Select, in this view, the quantities a configuration names."""

    def __init__(self, dataTreeView, configFile):
        """
        Arguments:
            configFile (str | QVizConfigurationFile) : the file to read, or a
                configuration built in memory. The api selects a list of paths
                through this same command, so a scripted selection and a saved
                one leave exactly the same record behind.
        """
        QVizAbstractCommand.__init__(self, dataTreeView)
        self.configuration = \
            configFile if isinstance(configFile, QVizConfigurationFile) \
                else QVizConfigurationFile.read(configFile)
        self.configFile = self.configuration.path
        self.source = 'the configuration "%s"' % self.configFile \
            if self.configFile else 'the paths given to the api'

    def execute(self):
        """Select every quantity the file names that this tree can provide.

        Returns how many nodes were selected. A quantity this tree does not hold
        is named in the log and skipped: one missing quantity must not cost the
        user the rest of the configuration.
        """
        paths = self.configuration.treePaths()
        self.loadMissingIDS(paths)

        selected = 0
        for quantity, path in zip(self.configuration.quantities, paths):
            node = self.findNode(path, quantity.occurrence)
            if node is None:
                logging.getLogger(self.dataTreeView.uri).error(
                    '"%s" is named by %s but is not in this tree: load the '
                    'IDS it belongs to before applying the configuration.'
                    % (path, self.source))
                continue
            QVizSelectNodes(dataTreeView=self.dataTreeView,
                            treeNode=node).selectNode(node)
            selected += 1
        return selected

    def loadMissingIDS(self, paths):
        """Fetch the IDS roots the configuration refers to, as applying one always did."""
        api = self.dataTreeView.imas_viz_api
        for quantity, path in zip(self.configuration.quantities, paths):
            if not path:
                continue
            idsName = path.split('/')[0]
            if api.IDSDataAlreadyFetched(self.dataTreeView, idsName,
                                         quantity.occurrence):
                continue
            QVizLoadSelectedData(dataTreeView=self.dataTreeView,
                                 IDSName=idsName,
                                 occurrence=quantity.occurrence,
                                 viewLoadingStrategy=None,
                                 asynch=False).execute()

    def findNode(self, path, occurrence):
        for node in self.dataTreeView.signalsList:
            if node.getPath() == path and node.getOccurrence() == occurrence:
                return node
        return None
