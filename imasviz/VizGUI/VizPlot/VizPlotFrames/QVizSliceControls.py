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
                               QVBoxLayout, QWidget)


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

    def __repr__(self):
        return '<QVizSliceRow %s index=%s length=%s>' % (self.key, self.index(),
                                                         self.length)


class QVizSliceControls(QWidget):
    """The controls for the axes a plot fixes, and the mapping they answer.

    setSlices is called whenever the plotted quantity changes -- a new leaf, a
    new curve, a time slice redraw -- so the values the user picked are kept for
    an axis that survives the rebuild, and dropped for one that no longer exists
    rather than carried over onto an unrelated axis.
    """

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(2, 2, 2, 2)
        self._layout.setSpacing(2)
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
            self._layout.addWidget(row)
            self._rows.append(row)

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

    @staticmethod
    def _withIndex(sl, index):
        # The caller owns the QVizSlice it built, and a rebuild must not rewrite
        # the index it carries: the axes model is the plot's, this widget's copy
        # of a starting point is not.
        from imasviz.VizDataAccess.QVizSlices import QVizSlice
        return QVizSlice(sl.axis, length=sl.length, index=index)

    def __repr__(self):
        return '<QVizSliceControls %s>' % ([row.key for row in self._rows],)
