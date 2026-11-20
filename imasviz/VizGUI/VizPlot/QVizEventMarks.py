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

The same detection the tool surface runs (`imasviz/VizAnalysis`, pinned in
`tests/test_152`), applied to what the figure has already drawn: the first live
curve's arrays, read back off its pyqtgraph item. No re-read of the case -- the
data is on screen -- and the cap and the refusal voice of the tool surface are
the ones here (past the cap the report is named, never a wall of verticals).

The entry is a sub-menu, one line per kind (ELM, sawtooth, transition L-H) and
one to take the marks back off. It holds the frame through a `weakref`, never a
bound method of it -- the cycle a bound method of a Qt widget makes is what has
this package segfaulting on this stack (`QVizCurveErrors`, the ownership guard
of tests/test_44). A `QMenu` made with the parent menu only gets a Qt parent:
nothing hangs it on the menu until `addMenu` is called, so the entry answers the
sub-menu it built.
"""

import weakref

import pyqtgraph as pg
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QMessageBox

from imasviz.VizAnalysis.detect import detect as ask

# The kinds the offer, in the order a physicist asks for them and in the words
# the manual and the tool surface use.
KINDS = (('elm', 'ELM'), ('sawtooth', 'sawtooth'),
         ('lh', 'transition L-H'))

# The same two answers the tool surface pins (`core.EVENT_MARKER_CAP` and the
# marker pen): past forty an event wall is not a marking, and the report is the
# shape it wants; and the line colour is the one the log uses, so a mark and
# the sentence that named it are the same colour.
MARKER_CAP = 40
MARKER_PEN_COLOUR = (255, 122, 40)


def _name(kind):
    for key, word in KINDS:
        if key == kind:
            return word
    return kind


class QVizEventMarks:
    """The marks a hand put on the events of this figure, and how they are done."""

    def __init__(self, frame):
        self._frame = weakref.ref(frame)

    # ------------------------------------------------------------------------ entry

    def addMenuEntry(self, menu):
        """Hang the **Événements** sub-menu on that view box's menu, and answer it."""
        submenu = QMenu('Événements', menu)
        for kind, word in KINDS:
            action = QAction(word, submenu)
            action.triggered.connect(lambda checked=False, k=kind: self._on(k))
            submenu.addAction(action)
        clear = QAction('Retirer les marques', submenu)
        clear.triggered.connect(self._onClear)
        submenu.addAction(clear)
        menu.addMenu(submenu)
        return submenu

    def _on(self, kind):
        """The slot: a refusal is said in the window, not dropped into the menu."""
        frame = self._frame()
        try:
            count = self.detect(kind)
        except ValueError as err:
            if frame is not None:
                QMessageBox.warning(None, 'Événements', str(err))
            return
        else:
            if frame is not None:
                QMessageBox.information(None, 'Événements',
                                        '%d marque(s) posée(s).' % count)

    def _onClear(self):
        frame = self._frame()
        try:
            self.clear()
        except ValueError:
            return
        if frame is not None:
            QMessageBox.information(None, 'Événements', 'Les marques sont retirées.')

    # -------------------------------------------------------------------- detection

    def liveCurve(self):
        """The first curve following the sliders, or None for a figure that has none."""
        frame = self._frame()
        if frame is None:
            return None
        for trace in frame._curves:
            if not trace.isFrozen():
                return trace.curve
        return None

    def detect(self, kind):
        """Detect the kind of event on the figure's live curve, and mark them.

        The same `detect` as the tool surface; the same cap, and the same refusals
        raised as `ValueError` (a flat signal, a wall of events, no live curve),
        so the slot can offer them a window without this object knowing one.
        """
        frame = self._frame()
        if frame is None:
            raise ValueError('the figure behind this entry is gone.')
        curve = self.liveCurve()
        if curve is None:
            raise ValueError('This figure holds no curve following the sliders, '
                             'so there is no series to detect '
                             + _name(kind) + ' on.')
        x, y = curve.getData()
        block = ask(kind, x, y)
        count = len(block['events'])
        if count > MARKER_CAP:
            raise ValueError('%d %s on this curve: more than %d verticals on one '
                             'figure is a wall, not a marking. The report is the '
                             'shape for that many.'
                             % (count, _name(kind), MARKER_CAP))
        self._addMarkers(frame, block['events'])
        return count

    def _addMarkers(self, frame, events):
        """Replace this figure's event marks with one vertical per event."""
        for line in list(getattr(frame, '_eventMarkers', []) or []):
            frame.pgPlotWidget.removeItem(line)
        frame._eventMarkers = []
        pen = pg.mkPen(MARKER_PEN_COLOUR, width=2)
        for event in events:
            line = pg.InfiniteLine(pos=float(event['t']), angle=90,
                                   pen=pen, movable=False)
            frame.pgPlotWidget.addItem(line)
            frame._eventMarkers.append(line)
        return len(events)

    def clear(self):
        """Take the marks back off; safe when the figure holds none."""
        frame = self._frame()
        if frame is None:
            raise ValueError('the figure behind this entry is gone.')
        items = list(getattr(frame, '_eventMarkers', []) or [])
        for line in items:
            frame.pgPlotWidget.removeItem(line)
        frame._eventMarkers = []
        return len(items)
