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

"""The spectral readout of the live curve on a figure of curves.

FIGURE scope: the one action runs the same `spectrum` the tool surface runs
(`imasviz/VizAnalysis/spectra`, pinned in `tests/test_155`), applied to the
arrays already on screen -- no re-read of the case. The run method delegates
to `QVizSpectrumMenu._on`, which already handles the refusal dialog and the
formatting of the result.

The label "Sommets du spectre (top 5)" is what the line reads; the plugin
itself says "Spectre" for the sub-menu, the same title `QVizSpectrumMenu.
addMenuEntry` used to give the `QMenu`.
"""

from imasviz.VizPlugins.VizPlugin import (
    FIGURE,
    QVizPluginAction,
    QVizPluginScope,
    VizPlugin,
)

# How many of the leading peaks the readout shows: same constant the frame's
# spectrum menu used to read (QVizSpectrumMenu.TOP_PEAKS).
TOP_PEAKS = 5


def _spectrum_run(context):
    """Run the spectral readout on the frame's live curve."""
    frame = context.figure
    if frame is None:
        return
    # `_on` already handles ValueError (shown in a dialog) and the success
    # formatting -- the plugin adds nothing to the work.
    frame.spectrumMenu._on()


class VizSpectral(VizPlugin):
    """The spectral readout line on a figure's menu box.

    SCOPE: FIGURE, so `figureMenuFor` finds it and builds its sub-menu on the
    frame's view box. LABEL is the sub-menu title the user reads; it used to be
    the first argument to `QMenu` in `QVizSpectrumMenu.addMenuEntry`.
    """
    SCOPE = QVizPluginScope(FIGURE)
    LABEL = 'Spectre'
    ACTIONS = (
        QVizPluginAction(0, 'Sommets du spectre (top %d)' % TOP_PEAKS,
                         run=_spectrum_run),
    )
