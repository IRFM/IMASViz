# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The Profiles entry: one window listing what this IDS can be drawn as.

This plugin used to know five IDSs by name. Each one carried its own list of the
array of structures to slice, the paths to keep and the label of each tab -- about
a hundred and twenty literals here -- plus a `data_found` probe into the loaded IDS
to decide whether its array was empty, and an occurrence question asked through a
modal `QInputDialog`. Two of those are why the entry looked broken rather than
narrow:

* the occurrence question went through
  `eval("imas." + ids + "().getMaxOccurrences()")`, which on this IMAS-Python
  answers `AttributeError`; the `except` this method used to carry turned that into
  a logging line, so the entry looked like a logging bug;
* `data_found` asked the loaded IDS for `time_slice` / `profiles_1d` and counted
  its elements -- an IDS written at `homogeneous_time = 1` has neither, so
  `magnetics` and most of the dictionary answered "no profiles found" whatever it
  held. And the read the panel drew with (`Viz_API.getAll_0D_1D_Nodes`) keeps only
  nodes that `isDynamicData()`, so even an offered IDS had nothing to show.

Now the tree the case built answers what can be drawn, for every IDS the case holds
(`QVizProfileOffer`), and the window that shows it (`QVizProfilePanel`) draws
through the application's own plot commands. So one entry is offered for any IDS
root -- and for the quantities under it, because the question it answers is about
the IDS, not about the node it was clicked on.

The entry refuses with a `ValueError` naming the reason; the catalog puts it in the
log panel of the case under this plugin's name. There is no `except` here, and that
is deliberate: the one this file used to carry is what made an impossible question
look like a logging failure.
"""

import logging

from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence import \
    QVizLoadOccurrence
from imasviz.VizPlugins.VizPlugin import VizPlugin, QVizPluginWindow
from imasviz.VizPlugins.viz_Profiles.viz_profiles.QVizProfileOffer import \
    QVizProfileOffer
from imasviz.VizPlugins.viz_Profiles.viz_profiles.QVizProfilePanel import \
    QVizProfilePanel


class VizProfiles_plugin(VizPlugin):

    def __init__(self):
        self.profilesPanel = None

    def execute(self, vizAPI, pluginEntry, answers=None):
        """Open the panel for the IDS this entry was offered on.

        `answers` is what a session replaying this entry already answered for the
        user: the occurrence and the key of the window. Without it the entry takes
        the first occurrence the case holds; with it, nothing is asked, because a
        restore has no one in front of a question -- and this plugin's question
        used to be a modal `QInputDialog` that a probe left alone for 240 s.
        """
        view = self.dataTreeView
        idsName = self.selectedTreeNode.getIDSName()
        # Which occurrences exist is the opened case's answer, never the data
        # dictionary's: `getMaxOccurrences` does not exist on this IMAS-Python,
        # and asking it was the sixth and last `eval` of that spelling here.
        occurrences = view.occurrences.occurrencesOf(idsName)
        if not occurrences:
            raise ValueError('the opened case holds no occurrence of the %s IDS, '
                             'so there is nothing to plot.' % idsName)
        occurrence = occurrences[0] if answers is None else answers.occurrence
        if occurrence not in occurrences:
            raise ValueError('the opened case holds no occurrence %d of the %s '
                             'IDS: it answers %s.'
                             % (occurrence, idsName,
                                ' and '.join(str(one) for one in occurrences)))

        # Loading is the same command the tree's own *Load* gesture runs, asked
        # synchronously: the offer is a walk of the tree that load builds, so an
        # asynchronous one here answers "no tree" and refuses an IDS that has
        # everything. Measured cost on the reference case: 0,6 s for `equilibrium`.
        QVizLoadOccurrence(view, idsName, occurrence, asynch=False).execute()

        offer = QVizProfileOffer(view, idsName, occurrence)
        if not offer.isPlottable():
            raise ValueError(offer.refusal())

        self.profilesPanel = QVizProfilePanel(
            vizAPI, view, idsName, occurrence,
            figureKey=None if answers is None else answers.figureKey)
        # What a session needs to put this window back, and the only place it
        # exists: measured, the panel answers neither `figureKey` nor `key` for
        # whoever asks, and the entry number and the occurrence it settled on live
        # nowhere but here.
        self.profilesPanel.pluginWindow = QVizPluginWindow(
            uri=view.dataSource.uri, plugin='VizProfiles_plugin',
            entry=pluginEntry, ids=idsName, occurrence=occurrence)
        self.profilesPanel.show()
        logging.getLogger(view.uri).info(
            'The %s IDS panel holds %d tabs and %d quantities.'
            % (idsName, len(offer.groups()), offer.quantityCount()))

    def getEntries(self):
        """One entry, for any IDS. What is in it is the tree's answer.

        There used to be two entries per IDS and four for `core_sources`, each
        naming the abscissa and the array of structures in its text -- "1D nodes
        from source(i1)/global_quantities(itime) along coordinate1 axis". The
        window asks both questions with a control now, and an IDS with no list of
        its own used to get no entry at all.
        """
        return [0]

    def getAllEntries(self):
        """What the menu says about this entry, with the IDS it was offered on."""
        return [(0, 'Plot what the %s IDS holds...'
                 % self.selectedTreeNode.getIDSName())]

    def getPluginsConfiguration(self):
        return None

    def getDescription(self):
        return ("Plot the quantities any IDS of this case holds, grouped by the "
                "array of structures that carries them.\n"
                "Author: Ludovic Fleury (ludovic.fleury@cea.fr)")

    def isEnabled(self):
        return True
