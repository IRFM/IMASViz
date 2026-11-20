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

"""The **Événements** entry a figure of curves offers on its view box.

`test_152` pins the math, `test_153` pins the tool surface. This pins the GUI
face of the same: a real `QVizCurvePlot` built off-screen carries the sub-menu
on its own view box, detects on the curve that is already on screen (no re-read
of the case), puts one vertical per event on the frame, and keeps the tool
surface's refusal voice -- past the cap the *report* is named, a flat signal is
refused by name, and a figure with no live curve says so rather than acting.

The frame is kept alive for the duration of the module that builds it -- a shown
plot frame is the ownership hazard the suite punishes (tests/support/ownership) --
and closed on the way out, the way test_132 keeps the session clean.
"""

import pytest

from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import (QVizCurvePlot,
                                                                QVizTrace)

pytestmark = [pytest.mark.ui]


def _elmCurve(frame, spikes):
    """A live curve on `frame`: a flat baseline with `spikes` sharp peaks."""
    n = 1000 * spikes + 100
    y = [0.0] * n
    for i in range(spikes):
        y[100 + 1000 * i] = 1.0
    curve = frame.pgPlotWidget.plot(range(n), y)
    # A row that is not frozen, so `liveCount` and the entry see it as the curve
    # the figure is standing on. `movable` is what makes it live; `treeNode` is
    # not read for any of what this file asks (only `isFrozen` and `getData`).
    frame._curves.append(QVizTrace(None, 0, curve, True, {}, ('time',), {}, ''))
    return curve


def _frame(qapp):
    frame = QVizCurvePlot()
    frame.show()
    qapp.processEvents()
    return frame


def test_the_entry_is_on_the_view_box_menu(qapp):
    frame = _frame(qapp)
    try:
        names = [a.text() for a in frame.pgPlotWidget.getViewBox().menu.actions()]
        assert 'Événements' in names
        sub = [a.menu() for a in
               frame.pgPlotWidget.getViewBox().menu.actions()
               if a.text() == 'Événements'][0]
        words = {a.text() for a in sub.actions()}
        assert words == {'ELM', 'sawtooth', 'transition L-H', 'Retirer les marques'}
    finally:
        frame.close()
        qapp.processEvents()


def test_the_entry_detects_on_the_curve_that_is_on_screen(qapp):
    frame = _frame(qapp)
    try:
        _elmCurve(frame, 12)
        count = frame.eventMarks.detect('elm')
        assert count == 12
        assert len(frame._eventMarkers) == 12
    finally:
        frame.close()
        qapp.processEvents()


def test_a_figure_with_no_live_curve_is_refused_by_name(qapp):
    frame = _frame(qapp)
    try:
        with pytest.raises(ValueError, match='no curve'):
            frame.eventMarks.detect('elm')
    finally:
        frame.close()
        qapp.processEvents()


def test_a_flat_signal_is_refused(qapp):
    frame = _frame(qapp)
    try:
        frame.pgPlotWidget.plot(range(50), [0.0] * 50)
        frame._curves.append(QVizTrace(None, 0,
                                       frame.pgPlotWidget.plot(range(50), [0.0] * 50),
                                       True, {}, ('time',), {}, ''))
        with pytest.raises(ValueError, match='flat'):
            frame.eventMarks.detect('elm')
    finally:
        frame.close()
        qapp.processEvents()


def test_past_the_cap_the_entry_names_the_report(qapp):
    frame = _frame(qapp)
    try:
        _elmCurve(frame, 45)
        with pytest.raises(ValueError, match='report'):
            frame.eventMarks.detect('elm')
        # A refusal writes nothing: the figure holds no mark of that kind.
        assert not getattr(frame, '_eventMarkers', [])
    finally:
        frame.close()
        qapp.processEvents()


def test_clear_takes_the_marks_off_and_is_safe(qapp):
    frame = _frame(qapp)
    try:
        _elmCurve(frame, 6)
        frame.eventMarks.detect('elm')
        assert frame.eventMarks.clear() == 6
        assert frame._eventMarkers == []
        assert frame.eventMarks.clear() == 0
    finally:
        frame.close()
        qapp.processEvents()
