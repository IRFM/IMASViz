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

"""The **Spectre** entry a figure of curves offers on its view box.

`test_155` pins the math, `test_156` pins the tool surface. This pins the GUI
face of the same, the sibling of the Événements entry (test_154): a real
`QVizCurvePlot` built off-screen carries the sub-menu on its own view box, runs
the spectrum on the curve that is already on screen (no re-read of the case),
and keeps the pure layer's refusal voice -- a flat series is refused, and a
figure with no live curve says so rather than acting.

The frame is kept alive for the duration of the module, and closed on the way
out, the way test_154 does -- a shown plot frame is the ownership hazard the
suite punishes (tests/support/ownership).
"""

import math

import pytest

from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import (QVizCurvePlot,
                                                                QVizTrace)

pytestmark = [pytest.mark.ui]


def _frame(qapp):
    frame = QVizCurvePlot()
    frame.show()
    qapp.processEvents()
    return frame


def _liveCurve(frame, x, y):
    """A live curve (not frozen) on `frame`, so `liveCurve` sees it as the one."""
    curve = frame.pgPlotWidget.plot(list(x), list(y))
    # `movable` non-empty is what makes it live; the rest is not read here.
    frame._curves.append(QVizTrace(None, 0, curve, True, {}, ('time',), {}, ''))
    return curve


def test_the_entry_is_on_the_view_box_menu(qapp):
    frame = _frame(qapp)
    try:
        names = [a.text() for a in frame.pgPlotWidget.getViewBox().menu.actions()]
        assert 'Spectre' in names
        sub = [a.menu() for a in
               frame.pgPlotWidget.getViewBox().menu.actions()
               if a.text() == 'Spectre'][0]
        assert {a.text() for a in sub.actions()} == {'Sommets du spectre (top 5)'}
    finally:
        frame.close()
        qapp.processEvents()


def test_the_entry_runs_on_the_curve_that_is_on_screen(qapp):
    frame = _frame(qapp)
    try:
        n = 256
        x = list(range(n))                       # an increasing clock, dt = 1
        y = [math.sin(2.0 * math.pi * 8.0 * i / n) for i in range(n)]
        _liveCurve(frame, x, y)

        answer = frame.spectrumMenu.spectrum()
        assert answer['samples'] == n
        assert 1 <= len(answer['peaks']) <= 5
        assert answer['total_power'] > 0
        # the single frequency on that grid, answered exactly by its bin
        assert answer['dominant']['frequency'] == pytest.approx(8.0 / n)
        # the window words are there for the handler, and name that peak
        text = frame.spectrumMenu._format(answer)
        assert 'Dominant' in text and 'Pics :' in text
    finally:
        frame.close()
        qapp.processEvents()


def test_a_figure_with_no_live_curve_is_refused_by_name(qapp):
    frame = _frame(qapp)
    try:
        with pytest.raises(ValueError, match='no curve'):
            frame.spectrumMenu.spectrum()
    finally:
        frame.close()
        qapp.processEvents()


def test_a_flat_series_is_refused(qapp):
    frame = _frame(qapp)
    try:
        _liveCurve(frame, range(64), [0.0] * 64)
        with pytest.raises(ValueError, match='flat'):
            frame.spectrumMenu.spectrum()
    finally:
        frame.close()
        qapp.processEvents()
