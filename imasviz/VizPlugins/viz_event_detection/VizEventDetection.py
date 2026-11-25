# Copyright holders : Commissariat à l'Energie Atomique et aux Energies
# Alternatives (CEA), France; and Laboratory for Engineering Design - LECAD,
# University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C
# open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted
# upon downloading the software and/or exercising any of the rights granted
# under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The ELM / sawtooth / L-H events a hand wants marked on a figure of curves.

FIGURE scope: offered on the view-box menu of a curve frame, the same four
lines the frame used to build itself (pinned in `tests/test_154`). The run
methods delegate to `QVizEventMarks._on` / `_onClear`, which already handles
the dialog and the cap -- the plugin adds nothing to the work, only the
offering: disable it in the preferences and the sub-menu disappears from the
frame's menu box, the frame and its domain objects are unchanged.
"""

from imasviz.VizPlugins.VizPlugin import (
    FIGURE,
    QVizPluginAction,
    QVizPluginScope,
    VizPlugin,
)


def _detect_run(kind):
    """The run callable for one detection kind on the frame's live curve."""
    def run(context):
        frame = context.figure
        if frame is None:
            return
        # `_on` already handles ValueError (shown in a dialog) and the success
        # count -- the plugin needs to add nothing to it.
        frame.eventMarks._on(kind)
    return run


def _clear_run(context):
    frame = context.figure
    if frame is None:
        return
    frame.eventMarks._onClear()


class VizEventDetection(VizPlugin):
    """The ELM / sawtooth / L-H event-detection lines on a figure's menu box.

    SCOPE: FIGURE, so `figureMenuFor` finds it and builds its sub-menu on the
    frame's view box. LABEL is the sub-menu title the user reads; it used to be
    the first argument to `QMenu` in `QVizEventMarks.addMenuEntry`.
    """
    SCOPE = QVizPluginScope(FIGURE)
    LABEL = 'Events'
    ACTIONS = (
        QVizPluginAction(0, 'ELM', run=_detect_run('elm')),
        QVizPluginAction(1, 'sawtooth', run=_detect_run('sawtooth')),
        QVizPluginAction(2, 'transition L-H', run=_detect_run('lh')),
        QVizPluginAction(3, 'Remove the marks', run=_clear_run),
    )
