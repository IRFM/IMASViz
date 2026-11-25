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

* *Flux surfaces (begin, middle, end)* — the flux surfaces of three instants
  side by side, one frame a bound: first, middle and last slice of the case. The
  comparison the row exists for is what keeps the three frames comparable: the
  same levels, the same bounds, the same marks (boundary, axis, O-point,
  limiter) at each named instant.
* *Equilibrium at an instant (surface + profiles)* — one instant: its flux surface,
  the eight radial profiles of the Equilibrium overview stacked under it, and
  the slice's global quantities said in the window title. The instant is asked
  through a dialog bounded to the case's own range, and answered in the user's
  place when a session replays the entry.

The gesture is `McpGuiCore` — the *same* two methods an MCP tool and the in-app
agent drive (`equilibrium_surfaces`, `equilibrium_at_time`) — so what the menu
does is what the manual describes and the suite pins, and a refusal is the
named `ValueError` of the command rather than an empty window.
"""

from imasviz.VizPlugins.VizPlugin import (IDS, QVizPluginAction,
                                          QVizPluginScope, QVizPluginWindow,
                                          VizPlugin)


class equilibriumsurfaces(VizPlugin):
    """The flux surfaces and radial profiles of `equilibrium`, as application figures."""

    IDS = 'equilibrium'
    PLUGIN_NAME = 'equilibriumsurfaces'

    def __init__(self):
        # Offered on the `equilibrium` IDS only; nowhere else earns either line.
        self.SCOPE = QVizPluginScope(IDS, ids=('equilibrium',))
        self.ACTIONS = (
            QVizPluginAction(
                0,
                'Flux surfaces (begin, middle, end)...',
                run=self._drawSurfaces,
                description=('Draw the equilibrium the way the application '
                             'draws its figures: the flow surfaces of the '
                             'first, middle and last instants of the case, '
                             'side by side, in one figure.')),
            QVizPluginAction(
                1,
                'Equilibrium at an instant (surface + profiles)...',
                run=self._drawAtTime,
                description=('Draw the equilibrium at one instant with its '
                             'radial profiles stacked under it. The same '
                             'quantities the Equilibrium overview plots, '
                             'dressed on the same ground and palette as every '
                             'other window, so a session can put them back.')),
        )

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
            None, 'Equilibrium at an instant', 'What time (s)?',
            value=(lo + hi) / 2, minValue=lo, maxValue=hi)
        if not accepted:
            raise ValueError(
                'equilibriumsurfaces: the question of the instant was '
                'cancelled, and no figure is opened on a time that was '
                'not asked for.')
        return float(value)

    # ------------------------------------------------------------ entry 0 / 1

    def _case(self, context):
        """The shared half of the two entries: case URI, occurrence, clock, key.

        `equilibriumcharts` reads occurrence 0 of `equilibrium` and refuses a
        file naming another one; the same boundary here keeps the stamp the
        session writes and the occurrence the read uses telling one story.

        The key and the `reuse` word come from the answers handed to the entry:
        a session names the key of the window it is putting back, and a tool
        call asked for a line whose window already stands names that window so
        its row is drawn again rather than a second window opened beside it.
        """
        view = context.view
        uri = view.dataSource.uri
        occurrence = 0
        answers = context.answers
        if answers is not None and answers.occurrence != 0:
            raise ValueError(
                'the Equilibrium surfaces read occurrence 0 of the equilibrium '
                'IDS, so they cannot be opened on occurrence %d as "%s" asks.'
                % (answers.occurrence, answers.figureKey))
        from imasviz.VizDataAccess.QVizEquilibriumRead import QVizEquilibriumRead
        reader = QVizEquilibriumRead(view.dataSource, occurrence)
        figureKey = None if answers is None else answers.figureKey
        reuse = bool(answers is not None and answers.reuse)
        return uri, occurrence, reader, figureKey, reuse

    def _register(self, context, key, uri, occurrence, time_answer, entry):
        """Register the drawn figure under its case and stamp it for a session.

        `casesServedBy` reads the registry: a figure registered without it
        serves no case, and the *Windows* menu and the case gestures cannot
        reach it. The stamp carries what a session needs to put it back — the
        entry, the occurrence, and for entry 1 the instant it answered, so a
        replay draws that one rather than opening a dialog nobody is there
        to answer.
        """
        api = context.api
        frame = api.figureframes[key]
        api.AddNodeToFigure(key, context.view.dataSource.dataKey2(key),
                            (uri, None))
        frame.pluginWindow = QVizPluginWindow(
            uri=uri, plugin=self.PLUGIN_NAME, entry=entry, ids=self.IDS,
            occurrence=occurrence, time=time_answer)
        return frame

    def _drawSurfaces(self, context):
        """Entry 0 — the flux surfaces of the first, middle and last instant."""
        uri, occurrence, reader, figureKey, reuse = self._case(context)
        from imasviz.VizAgent.core import McpGuiCore
        instants = self._threeInstants(reader.timeValues())
        result = McpGuiCore(api=context.api).equilibrium_surfaces(
            uri, instants, occurrence=occurrence, figure_key=figureKey,
            reuse=reuse)
        return self._register(context, result['figure'], uri, occurrence,
                              time_answer=None, entry=0)

    def _drawAtTime(self, context):
        """Entry 1 — one instant with its radial profiles under it.

        The instant a session replay is answering in the user's place
        (`answers.time`) must not be re-asked: a restore has no one to answer
        the dialog. The same holds for a tool call, which hands its answers the
        same way: an answer handed without an instant is refused by name rather
        than left to open a dialog nobody is there for. Only a click on the menu
        line (`answers` is None) earns the question, bounded to the case's clock.
        """
        uri, occurrence, reader, figureKey, reuse = self._case(context)
        from imasviz.VizAgent.core import McpGuiCore
        if context.answers is not None:
            if context.answers.time is None:
                raise ValueError(
                    'equilibriumsurfaces entry 1 draws one instant and none was '
                    'answered: hand it as the "time" of run_plugin, or ask '
                    'equilibrium_at_time directly. Nothing is drawn on an instant '
                    'nobody asked for, and no dialog is opened where nobody is '
                    'there to answer it.')
            time_answer = float(context.answers.time)
        else:
            time_answer = self._askTime(reader.timeValues())
        result = McpGuiCore(api=context.api).equilibrium_at_time(
            uri, time_answer, occurrence=occurrence, figure_key=figureKey,
            reuse=reuse)
        return self._register(context, result['figure'], uri, occurrence,
                              time_answer=time_answer, entry=1)
