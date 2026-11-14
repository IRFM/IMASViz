# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The equilibrium, drawn in the application's own style, from its Plugins menu.

Where `equilibriumcharts` carries its own matplotlib window, this plugin draws
the same quantities through the application's figures — the black ground and
the one trace palette every curve frame wears — so the window it opens is one
`EquiSurfaces:` key in `figureframes`, addressed by the *Windows* menu and its
*Delete* sub-menu like any other figure, and replayed by a session.

Two lines, both offered on the `equilibrium` branch and refused by name on any
other:

* *Surfaces de flux (début, milieu, fin)* — the flux surfaces of three instants
  side by side, one frame a bound: first, middle and last slice of the case. The
  comparison the row exists for is what keeps the three frames comparable: the
  same levels, the same bounds, the same marks (boundary, axis, O-point,
  limiter) at each named instant.
* *Équilibre à un instant (surface + profils)* — one instant: its flux surface,
  the eight radial profiles of the Equilibrium overview stacked under it, and
  the slice's global quantities said in the window title. The instant is asked
  through a dialog bounded to the case's own range, and answered in the user's
  place when a session replays the entry.

The gesture is `McpGuiCore` — the *same* two methods an MCP tool and the in-app
agent drive (`equilibrium_surfaces`, `equilibrium_at_time`) — so what the menu
does is what the manual describes and the suite pins, and a refusal is the
named `ValueError` of the command rather than an empty window.
"""

from imasviz.VizPlugins.VizPlugin import VizPlugin, QVizPluginWindow


class equilibriumsurfaces(VizPlugin):
    """The flux surfaces and radial profiles of `equilibrium`, as application figures."""

    IDS = 'equilibrium'
    PLUGIN_NAME = 'equilibriumsurfaces'

    def isEnabled(self):
        return True

    def getEntries(self):
        return [0, 1] if self.selectedTreeNode is not None \
            and self.selectedTreeNode.getIDSName() == self.IDS else []

    def getAllEntries(self):
        return [(0, 'Surfaces de flux (début, milieu, fin)...'),
                (1, 'Équilibre à un instant (surface + profils)...')]

    def getDescription(self):
        return ("Draw the equilibrium the way the application draws its figures: "
                "the flux surfaces of several instants side by side, or one instant "
                "with its radial profiles stacked under it. The same quantities "
                "the Equilibrium overview plots, dressed on the same ground and "
                "palette as every other window, so a session can put them back.")

    # ---------------------------------------------------------------- entry 0

    def _threeInstants(self, times):
        """The first, middle and last slice of the case, as three instants.

        Chosen from the case's own clock rather than named by hand: a menu
        line that asks no question must still open the window, and the
        reference case's 49 slices keep the three apart (measured 32.1 to
        48.5 s). Distinct ones only, sorted — a short pulse in which the ends
        meet would rather open two frames than three that say the same.
        """
        lo = float(times[0])
        hi = float(times[-1])
        mid = float(times[len(times) // 2])
        return sorted({lo, mid, hi})

    # ---------------------------------------------------------------- entry 1

    def _askTime(self, times):
        """The instant one line asks for, bounded to the case's own clock.

        `QInputDialog` clamps the answer into [min, max], which is what
        "bounded to the case" says: an instant far outside the pulse would
        still open a window, but the core names the slice that answered. A
        cancelled question is a named refusal, not a default the user did not
        ask for — the entry must not draw on a guess.
        """
        from PySide6.QtWidgets import QInputDialog
        lo = float(times[0])
        hi = float(times[-1])
        value, accepted = QInputDialog.getDouble(
            None, 'Équilibre à un instant', 'Quelle heure (s) ?',
            value=(lo + hi) / 2, minValue=lo, maxValue=hi)
        if not accepted:
            raise ValueError(
                'equilibriumsurfaces: la question de l\'instant a été '
                'annulée, et aucune figure n\'est ouverte sur une heure '
                'qu\'on n\'a pas demandée.')
        return float(value)

    # --------------------------------------------------------------- execute

    def execute(self, vizAPI, pluginEntry, answers=None):
        """Draw one of the two windows, on the case the entry was offered on.

        `vizAPI` is the session's own api (the catalog hands it over), so the
        figure lands in the `figureframes` the *Windows* menu reads, under the
        key a session replay named — `FigureKeyFor` honours it and refuses a
        key a live window already holds. An entry a session is replaying is
        answered with the occurrence and the instant it held, not asked again:
        a restore must not open a modal dialog that has no one to answer it.
        """
        node = self.selectedTreeNode
        uri = self.dataTreeView.dataSource.uri

        # `equilibriumcharts` reads occurrence 0 of `equilibrium` and refuses a
        # file naming another one; the same boundary here keeps the stamp the
        # session writes and the occurrence the read uses telling one story.
        occurrence = 0
        if answers is not None and answers.occurrence != 0:
            raise ValueError(
                'the Equilibrium surfaces read occurrence 0 of the equilibrium '
                'IDS, so they cannot be opened on occurrence %d as "%s" asks.'
                % (answers.occurrence, answers.figureKey))

        from imasviz.VizDataAccess.QVizEquilibriumRead import QVizEquilibriumRead
        from imasviz.VizAgent.core import McpGuiCore
        reader = QVizEquilibriumRead(self.dataTreeView.dataSource, occurrence)
        times = reader.timeValues()
        core = McpGuiCore(api=vizAPI)
        figure_key = None if answers is None else answers.figureKey

        time_answer = None
        if pluginEntry == 0:
            instants = self._threeInstants(times)
            result = core.equilibrium_surfaces(
                uri, instants, occurrence=occurrence, figure_key=figure_key)
        elif pluginEntry == 1:
            if answers is not None and answers.time is not None:
                time_answer = float(answers.time)
            else:
                time_answer = self._askTime(times)
            result = core.equilibrium_at_time(
                uri, time_answer, occurrence=occurrence, figure_key=figure_key)
        else:
            raise ValueError('entry %r is not offered by this plugin' % (pluginEntry,))

        key = result['figure']
        frame = vizAPI.figureframes[key]

        # Register the window under its case, so the *Windows* menu and the
        # case gestures (*Close this case*, *Show only this case*) reach it
        # the way `equilibriumcharts` reaches its own — `casesServedBy` reads
        # this, and a figure registered without it serves no case.
        vizAPI.AddNodeToFigure(key,
                               self.dataTreeView.dataSource.dataKey2(key),
                               (uri, None))

        # What a session needs to put this window back: the entry, the case,
        # the occurrence the read used, and — for entry 1 — the instant it
        # answered, so the replay draws that one without opening the dialog.
        frame.pluginWindow = QVizPluginWindow(
            uri=uri, plugin=self.PLUGIN_NAME, entry=pluginEntry, ids=self.IDS,
            occurrence=occurrence, time=time_answer)
        return frame
