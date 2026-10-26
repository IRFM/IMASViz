# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""One slider per axis the plot fixes rather than draws.

Written against QVizSlices rather than on top of the slider the plot frames
carry today, on purpose. That one is built when the figure is created -- before
any quantity is known -- offers a single slider chosen by two flags set at that
moment (time or coordinate 1), and is read back out of band by the data access
and by the node's label code. Three consequences it cannot get round: a quantity
with more than two axes has axes no control can reach; the control can be for an
axis the plot already draws; and the labels a slider drives are recomputed by
code that has to know the slider exists.

Here the plot frame asks the data access which axes it is going to fix, hands
that list to this widget, and hands the widget's values back to the read. The
widget knows nothing about IDSs, paths or plots: it turns a list of slices into
controls and a mapping back.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QSizePolicy, QSlider,
                               QToolButton, QVBoxLayout, QWidget)


class QVizSliceRow(QWidget):
    """Label, slider, and where in the axis we are, for one fixed axis.

    The index is spelled out rather than left to the handle's position: a user
    comparing two plots needs to read which element of which array the numbers
    came from, which is the whole point of showing the control at all.
    """

    moved = Signal()

    def __init__(self, sl, parent=None):
        super().__init__(parent)
        self.key = sl.key
        self.label = sl.label
        self.length = sl.length

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.nameLabel = QLabel(sl.label + ':', self)
        self.nameLabel.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)

        self.slider = QSlider(Qt.Horizontal, self)
        index = 0 if sl.index is None else int(sl.index)
        if sl.length is None:
            # No length means no range to offer. The axis stays named and its
            # index shown: a fixed axis with no control is exactly the silent
            # assumption this widget exists to remove.
            self.slider.setEnabled(False)
            self.slider.setToolTip('Number of values in this axis is unknown')
        else:
            length = max(int(sl.length), 1)
            self.slider.setRange(0, length - 1)
            self.slider.setPageStep(1)
            if length < 2:
                self.slider.setEnabled(False)
                self.slider.setToolTip('This axis holds a single value')
        self.slider.setValue(index)
        # Read back what the slider kept rather than trusting the index: a
        # rebuild can hand over the index the user picked on an axis that has
        # since shrunk, and the label must show where the control actually is.
        index = int(self.slider.value())

        self.indexLabel = QLabel(self)
        self.indexLabel.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        self._showIndex(index)

        layout.addWidget(self.nameLabel)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.indexLabel)

        self.slider.valueChanged.connect(self._onValueChanged)

    def index(self):
        return int(self.slider.value())

    def setIndex(self, index):
        index = int(index)
        if self.length is not None:
            index = max(0, min(index, max(int(self.length), 1) - 1))
        else:
            index = max(0, index)
        self.slider.setValue(index)
        self._showIndex(index)

    def _onValueChanged(self, value):
        self._showIndex(value)
        self.moved.emit()

    def _showIndex(self, index):
        if self.length is None:
            self.indexLabel.setText(str(index))
        else:
            self.indexLabel.setText('%d / %d' % (index, max(int(self.length), 1) - 1))

    def indexText(self):
        """What this row says about where it stands, for whoever has no slider.

        The folded band spells one line out of these, so the numbers a row shows
        are the same numbers whether the band is open or shut.
        """
        return self.indexLabel.text()

    def __repr__(self):
        return '<QVizSliceRow %s index=%s length=%s>' % (self.key, self.index(),
                                                         self.length)


class QVizSliceControls(QWidget):
    """The controls for the axes a plot fixes, and the mapping they answer.

    setSlices is called whenever the plotted quantity changes -- a new leaf, a
    new curve, a time slice redraw -- so the values the user picked are kept for
    an axis that survives the rebuild, and dropped for one that no longer exists
    rather than carried over onto an unrelated axis.

    A curve figure asks for `foldable`: exploring a tensor puts one slider on
    every axis the curve leaves out, and a quantity held by three arrays of
    structures then takes three lines of a window whose plot is what the user
    came to look at. Folded, the band answers with one line naming every axis
    and where it stands, and the sliders come back on a click. An image window
    and a table panel do not fold: there the rows are the only place saying which
    slice the colours and the panel numbers stand for.
    """

    changed = Signal()

    def __init__(self, parent=None, foldable=False):
        super().__init__(parent)
        self._foldable = bool(foldable)
        self._folded = False
        self._rows = []
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(2, 2, 2, 2)
        self._layout.setSpacing(2)

        # Added before the rows so folding leaves it where it is: the rows come
        # and go underneath it.
        self.summaryRow = QWidget(self)
        summary = QHBoxLayout(self.summaryRow)
        summary.setContentsMargins(0, 0, 0, 0)
        self.summaryLabel = QLabel(self.summaryRow)
        self.summaryLabel.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        self.foldButton = QToolButton(self.summaryRow)
        self.foldButton.setText('More')
        self.foldButton.clicked.connect(self.toggleFold)
        summary.addWidget(self.summaryLabel)
        summary.addWidget(self.foldButton)
        summary.addStretch(1)
        self.summaryRow.setVisible(False)
        self._layout.addWidget(self.summaryRow)

        self.setVisible(False)

    def setSlices(self, slices):
        """Rebuild the controls, keeping what the user already picked.

        The stored index is clamped to the new length instead of dropped, because
        the usual reason a length shrinks is a different quantity in the same
        array -- and losing the user's choice on every redraw makes a plot that
        was being compared move under them.
        """
        previous = {row.key: row.index() for row in self._rows}
        for row in self._rows:
            self._layout.removeWidget(row)
            row.deleteLater()
        self._rows = []

        for sl in slices:
            index = sl.index
            if sl.key in previous:
                index = previous[sl.key]
            row = QVizSliceRow(sl if index is None else self._withIndex(sl, index),
                               parent=self)
            row.moved.connect(self.changed)
            row.moved.connect(self._showSummary)
            self._layout.addWidget(row)
            self._rows.append(row)

        self._folded = self._foldable and len(self._rows) > 1
        self._showSummary()
        self._applyFold()
        self.setVisible(bool(self._rows))

    def indices(self):
        """{axis key: index} -- what a read takes to fix those axes."""
        return {row.key: row.index() for row in self._rows}

    def setIndex(self, key, index):
        for row in self._rows:
            if row.key == key:
                row.setIndex(index)
                return True
        return False

    def sliceCount(self):
        return len(self._rows)

    def rows(self):
        """The rows themselves, for whoever draws or inspects them."""
        return list(self._rows)

    def keys(self):
        return [row.key for row in self._rows]

    def isFoldable(self):
        return self._foldable

    def isFolded(self):
        return self._folded

    def toggleFold(self):
        """Put the sliders back on screen, or take them away.

        Visibility, never a rebuild: the rows stay built, so `indices` keeps
        answering the read with the indices the user picked whether the band is
        open or shut. Rebuilding them to fold would drop those indices and move
        the curves the figure is showing.
        """
        if not self._foldable:
            return False
        self._folded = not self._folded
        self._applyFold()
        return True

    def summaryText(self):
        return '   '.join('%s %s' % (row.label, row.indexText())
                          for row in self._rows)

    def _showSummary(self):
        self.summaryLabel.setText(self.summaryText())

    def _applyFold(self):
        for row in self._rows:
            row.setVisible(not self._folded)
        self.summaryRow.setVisible(self._folded)
        self.foldButton.setText('More' if self._folded else 'Fewer')

    @staticmethod
    def _withIndex(sl, index):
        # The caller owns the QVizSlice it built, and a rebuild must not rewrite
        # the index it carries: the axes model is the plot's, this widget's copy
        # of a starting point is not.
        from imasviz.VizDataAccess.QVizSlices import QVizSlice
        return QVizSlice(sl.axis, length=sl.length, index=index)

    def __repr__(self):
        return '<QVizSliceControls %s>' % ([row.key for row in self._rows],)


class QVizFramesWindow(QWidget):
    """Where a figure's window of pictures sits along the axis it reads across.

    That axis needs no slider: its elements are the pictures on screen. What it
    needs is a way to move on when the axis is longer than the figure holds, and
    a saying of which elements are up -- the same reason the slice rows spell
    their index out instead of leaving it to a handle's position.

    setWindow keeps the start the user moved to when the same axis comes back
    (a pinned control moved, a re-plot of the same quantity), because the whole
    point of the window is to keep two sets of pictures comparable.
    """

    moved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._key = None
        self._label = ''
        self._start = 0
        self._count = 0
        self._length = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.nameLabel = QLabel(self)
        self.nameLabel.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)

        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setPageStep(1)
        self.slider.setEnabled(False)

        layout.addWidget(self.nameLabel)
        layout.addWidget(self.slider, 1)

        self.slider.valueChanged.connect(self._onValueChanged)
        self.setVisible(False)

    def setWindow(self, sl, count):
        """The axis read across the images, and how many images it feeds."""
        if sl is None:
            self._key = None
            self._count = 0
            self._length = None
            self.slider.blockSignals(True)
            self.slider.setEnabled(False)
            self.slider.blockSignals(False)
            self.setVisible(False)
            return

        count = int(count)
        length = sl.length
        start = self._start if self._key == sl.key else sl.index
        self._key = sl.key
        self._label = sl.label
        self._count = count
        self._length = length

        self.slider.blockSignals(True)
        if length is None:
            self.slider.setEnabled(False)
            self.slider.setToolTip('Number of values in this axis is unknown')
        else:
            last = max(int(length) - count, 0)
            self.slider.setRange(0, last)
            self.slider.setEnabled(last > 0)
            if last == 0:
                self.slider.setToolTip('This axis holds fewer elements than the '
                                       'figure has images')
        self._start = self._clamp(start)
        self.slider.setValue(self._start)
        self.slider.blockSignals(False)

        self._showLabel()
        self.setVisible(True)

    def start(self):
        return self._start if self._key is not None else 0

    def setStart(self, index):
        if self._key is None:
            return False
        self._start = self._clamp(index)
        self.slider.setValue(self._start)
        self._showLabel()
        return True

    def count(self):
        return self._count

    def labelText(self):
        if self._key is None:
            return ''
        return '%s: %d-%d / %d' % (self._label, self.start(),
                                   self.start() + self._count - 1,
                                   max(int(self._length), 1) - 1)

    def _clamp(self, index):
        index = int(index if index is not None else 0)
        if self._length is None:
            return max(0, index)
        return max(0, min(index, max(int(self._length) - self._count, 0)))

    def _showLabel(self):
        self.nameLabel.setText(self.labelText())

    def _onValueChanged(self, value):
        self._start = int(value)
        self._showLabel()
        self.moved.emit()

    def __repr__(self):
        return '<QVizFramesWindow %s start=%s count=%s length=%s>' % (
            self._key, self.start(), self._count, self._length)
