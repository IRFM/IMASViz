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

* the occurrence question went through a read of the data dictionary that does not
  exist on this IMAS-Python, so the entry raised where the manual says it should
  answer;
* the panel the entry opened kept only data it called dynamic, so even an offered
  IDS had little to show for it.

Now the tree the case built answers what can be drawn, for every IDS the case holds
(`QVizProfileOffer`), and the window that shows it (`QVizProfilePanel`) draws
through the application's own plot commands. So one entry is offered for any IDS
root -- and for the quantities under it, because the question it answers is about
the IDS, not about the node it was clicked on.

The entry refuses with a `ValueError` naming the reason; the catalog puts it in
the log panel of the case under this plugin's name. There is no `except` here, and
that is deliberate: the one this file used to carry is what made an impossible
question look like a logging failure.

Written against the pass that made the plugin contract declarative: a `SCOPE`
(this one, an IDS) and the one `ACTION` it offers, whose `run` is the work and
whose `label` reads "any IDS" under one root and the next under another.
"""

import logging

from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence import \
    QVizLoadOccurrence
from imasviz.VizPlugins.VizPlugin import (IDS, QVizPluginAction,
                                          QVizPluginScope, QVizPluginWindow,
                                          VizPlugin)
from imasviz.VizPlugins.viz_Profiles.viz_profiles.QVizProfileOffer import \
    QVizProfileOffer
from imasviz.VizPlugins.viz_Profiles.viz_profiles.QVizProfilePanel import \
    QVizProfilePanel


class VizProfiles_plugin(VizPlugin):

    def __init__(self):
        self.profilesPanel = None
        # Offered on any IDS root: the question it answers is about the IDS, not
        # about the quantity under the cursor, so it is declared once and not
        # tested on every node the gesture reaches.
        self.SCOPE = QVizPluginScope(IDS)
        self.ACTIONS = (
            QVizPluginAction(
                0,
                lambda ctx: 'Plot what the %s IDS holds...' % ctx.idsName,
                run=self.draw,
                description=('Plot the quantities any IDS of this case holds, '
                             'grouped by the array of structures that carries '
                             'them.\n'
                             'Author: Ludovic Fleury (ludovic.fleury@cea.fr)')),
        )

    def draw(self, context):
        """Open the panel for the IDS this entry was offered on.

        `answers` is what a session replaying this entry already answered for the
        user: the occurrence and the key of the window, in `context.answers`.
        Without it the entry takes the first occurrence the case holds; with it,
        nothing is asked, because a restore has no one in front of a question --
        and this plugin's question used to be a modal `QInputDialog` that a probe
        left alone for 240 s.
        """
        vizAPI = context.api
        view = context.view
        idsName = context.node.getIDSName()
        # Which occurrences exist is the opened case's answer, never the data
        # dictionary's: `getMaxOccurrences` does not exist on this IMAS-Python,
        # and asking it was the sixth and last `eval` of that spelling here.
        occurrences = view.occurrences.occurrencesOf(idsName)
        if not occurrences:
            raise ValueError('the opened case holds no occurrence of the %s IDS, '
                             'so there is nothing to plot.' % idsName)
        occurrence = (occurrences[0] if context.answers is None
                      else context.answers.occurrence)
        if occurrence not in occurrences:
            raise ValueError('the opened case holds no occurrence %d of the %s '
                             'IDS: it answers %s.'
                             % (occurrence, idsName,
                                ' and '.join(str(one) for one in occurrences)))

        # One window per IDS. A click on the menu already opened a panel for
        # this IDS -- bring it to the front instead of opening a second one,
        # which would ask the same case its questions again and hold two
        # occurrence choices for one answer. A tool call asking for the panel
        # that already stands is answered the same way (`answers.reuse`: the
        # caller found the window by the stamp this entry left on it and handed
        # its key back), because a second panel of one IDS says the same thing
        # twice on the screen. A session restore is let through: it has named
        # the key its file gave the window, and the panel it finds or builds
        # must answer to that key.
        if context.answers is None or context.answers.reuse:
            existing = QVizProfilePanel.findOpen(vizAPI, view, idsName)
            if existing is not None:
                self.profilesPanel = existing
                existing.raise_()
                existing.activateWindow()
                logging.getLogger(view.uri).info(
                    'The %s IDS panel is already open: %s is brought to the '
                    'front instead of opening a second window for it.'
                    % (idsName, existing.figureKey))
                return

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
            figureKey=None if context.answers is None
            else context.answers.figureKey)
        # What a session needs to put this window back, and the only place it
        # exists: measured, the panel answers neither `figureKey` nor `key` for
        # whoever asks, and the entry number and the occurrence it settled on live
        # nowhere but here.
        self.profilesPanel.pluginWindow = QVizPluginWindow(
            uri=view.dataSource.uri, plugin='VizProfiles_plugin',
            entry=0, ids=idsName, occurrence=occurrence)
        self.profilesPanel.show()
        logging.getLogger(view.uri).info(
            'The %s IDS panel holds %d tabs and %d quantities.'
            % (idsName, len(offer.groups()), offer.quantityCount()))
