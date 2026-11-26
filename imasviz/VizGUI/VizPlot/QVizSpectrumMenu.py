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

"""The **Spectrum** entry a figure of curves offers on its view box.

The same spectral facts the tool surface runs (`imasviz/VizAnalysis/spectra`,
pinned in `tests/test_155`), applied to what the figure has already drawn: the
first live curve's arrays, read back off its pyqtgraph item. No re-read of the
case -- the data is on screen -- and the refusal voice of the pure layer is the
one a slot offers: a flat series is a flat series, a figure with no live curve
says so rather than acting.

It is the sibling of the **Events** entry (`QVizEventMarks`): the same
sub-menu on the same view box, the same `liveCurve` read, and the same rule --
hold the frame through a `weakref`, never a bound method of it, which is the
cycle that has this package segfaulting on this stack. The entry is a sub-menu,
so it is the object the slot answers, not a name it invents.
"""

import weakref

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QMessageBox

from imasviz.VizAnalysis.spectra import spectrum as ask

# How many of the leading peaks the readout shows. The figure is a quick
# readout, not a spectrum editor: more than this is a report-shaped answer,
# which the tool surface already gives.
TOP_PEAKS = 5


class QVizSpectrumMenu:
    """The spectral readout of this figure's live curve, and how it is offered."""

    def __init__(self, frame):
        self._frame = weakref.ref(frame)

    # ------------------------------------------------------------------------ entry

    def addMenuEntry(self, menu):
        """Hang the **Spectrum** sub-menu on that view box's menu, and answer it."""
        submenu = QMenu('Spectrum', menu)
        action = QAction('Spectral peaks (top %d)' % TOP_PEAKS, submenu)
        action.triggered.connect(lambda checked=False: self._on())
        submenu.addAction(action)
        menu.addMenu(submenu)
        return submenu

    def _on(self):
        """The slot: a refusal is said in a window, not dropped into the menu."""
        frame = self._frame()
        try:
            answer = self.spectrum()
        except ValueError as err:
            if frame is not None:
                QMessageBox.warning(None, 'Spectrum', str(err))
            return
        if frame is not None:
            QMessageBox.information(None, 'Spectrum', self._format(answer))

    # -------------------------------------------------------------------- the read

    def liveCurve(self):
        """The first curve following the sliders, or None for a figure that has none."""
        frame = self._frame()
        if frame is None:
            return None
        for trace in frame._curves:
            if not trace.isFrozen():
                return trace.curve
        return None

    def spectrum(self, n_peaks=TOP_PEAKS):
        """The spectral facts of the figure's live curve, raised as `ValueError` on refusal.

        The same `spectrum` as the tool surface; the same refusals (no live
        curve, a flat series, not on an increasing clock) so the slot can offer
        them a window without this object knowing one.
        """
        frame = self._frame()
        if frame is None:
            raise ValueError('the figure behind this entry is gone.')
        curve = self.liveCurve()
        if curve is None:
            raise ValueError('This figure holds no curve following the sliders, '
                             'so there is no series to run a spectrum on.')
        x, y = curve.getData()
        return ask(x, y, n_peaks)

    # -------------------------------------------------------------------- the words

    @staticmethod
    def _format(answer):
        """The top peaks as a window reads them: the dominant first, then the list."""
        dom = answer['dominant']
        lines = [
            'Dominant: f = %g  ·  period %g  ·  %g %% of the power'
            % (dom['frequency'], dom['period'], 100 * dom['fraction']),
            'Total power: %g' % answer['total_power'],
            '%d sample(s)' % answer['samples'],
            '',
            'Peaks:',
        ]
        for i, peak in enumerate(answer['peaks']):
            lines.append(
                '  %d.  f = %g  ·  period %g  ·  %g %%'
                % (i + 1, peak['frequency'], peak['period'],
                   100 * peak['fraction']))
        return '\n'.join(lines)
