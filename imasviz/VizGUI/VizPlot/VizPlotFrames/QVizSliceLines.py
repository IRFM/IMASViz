# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Where the user points on a picture, and the slice that question asks for.

A picture draws two axes and pins the rest. The pinned axes have sliders, but
nothing on the figure answers the other question: what does the curve look like
*here*, at this place on the picture. The legacy image window answered it with a
movable line per drawn axis and a 1D plot of the slice under it, and that answer
is worth keeping. Three things about it were not.

The lines stood in element ranks, because the legacy picture never spanned the
coordinate extents: its rank space and its label space agreed. Here the picture
is laid over the extents its coordinates take, so a line in ranks sits somewhere
the user is not looking at. The lines therefore carry coordinate values, and the
element they stand on is the nearest one -- a slice is an element of the array,
and on an irregular grid the nearest one is not the one below.

The slice was drawn against range(len(slice)), so a curve two metres wide carried
element numbers under a label naming metres. It is drawn here against the other
drawn axis's values, which is the abscissa the picture already carries.

And the commands to keep a slice -- the point of the exercise, since comparing
slices is why anyone drags a line -- lived in a context menu built by the legacy
viewBox, which these frames do not use. They are buttons on the figure now.

One pair of lines, on the first picture. What the lines answer is that picture,
and with a window of pictures side by side a line on each would be several
answers to one question; the window control moves which picture that is.
"""

import numpy as np
import pyqtgraph as pg


class QVizDrawnAxis:
    """One axis a picture draws: its name, its units, its values.

    A line on one axis needs the other one -- its name for the label under the
    slice, its values for that slice's abscissa -- so the two carry each other
    rather than leaving the frame to pair them up again on every read.
    """

    def __init__(self, name, units, values):
        self.name = name
        self.units = units
        self.values = np.asarray(values, dtype=float)
        self.other = None

    def spelling(self):
        """How the axis is named on screen: rho_tor[m], units and all."""
        return self.name + ('[' + self.units + ']' if self.units else '')

    def labelFormat(self):
        """The pyqtgraph label format: it re-formats itself on every move."""
        return self.spelling() + '={value:g}'

    def __repr__(self):
        return '<QVizDrawnAxis %s %d values>' % (self.spelling(),
                                                 len(self.values))


class QVizSliceLines:
    """The lines on one picture, the slice each answers, and the kept ones."""

    BOTTOM = 'bottom'
    LEFT = 'left'
    SIDES = (BOTTOM, LEFT)

    def __init__(self, layout):
        """
        Arguments:
            layout (pg.GraphicsLayoutWidget) : the figure's layout; the slice
                plots are added to it, under the pictures.
        """
        self._layout = layout
        self._picture = None
        self._axes = {}
        self._lines = {}
        self._plots = {}
        self._curves = {}
        self._kept = {}
        self._markers = {}
        self._values = np.asarray([])
        self._columns = 1

    def forQuantity(self, picture, quantity, axes, columns):
        """Pose the lines and the slice plots for a newly drawn quantity.

        Arguments:
            picture   (pg.PlotItem) : the picture the lines are drawn on.
            quantity    (str)       : what the pictures show, for the slice plots'
                                      vertical label.
            axes       (dict)       : {side: QVizDrawnAxis} for the two axes drawn,
                                      each carrying the other as `other`.
            columns     (int)       : how many pictures sit side by side.
        """
        self.clear()
        self._picture = picture
        self._axes = dict(axes)
        self._axes[self.BOTTOM].other = self._axes[self.LEFT]
        self._axes[self.LEFT].other = self._axes[self.BOTTOM]
        self._columns = max(int(columns), 1)

        for side in self.SIDES:
            axis = self._axes[side]
            line = pg.InfiniteLine(pos=float(axis.values[len(axis.values) // 2]),
                                   angle=90 if side == self.BOTTOM else 0,
                                   movable=True,
                                   bounds=(float(axis.values[0]),
                                           float(axis.values[-1])),
                                   label=axis.labelFormat())
            line.label.setZValue(1000)
            # On the view box rather than the plot: the line has to stay above
            # the image and be grabbed where the image is.
            picture.getViewBox().addItem(line)
            line.sigPositionChanged.connect(self._onMoved)
            self._lines[side] = line

            plotItem = self._layout.addPlot(row=1 if side == self.BOTTOM else 2,
                                            col=0, colspan=self._columns)
            plotItem.setLabel('bottom', axis.other.name or '',
                              units=axis.other.units or '')
            plotItem.setLabel('left', quantity)
            self._plots[side] = plotItem
            self._markers[side] = [self._newMarker(side)]

    def addMarker(self, side):
        """Pose one more read-out cursor on the slice plot under one line.

        The legacy image window did this from its viewBox context menu, and the
        marker was the only way to read a position off a slice without moving the
        line that produced it. The cursor says which axis it stands on and its
        units, so a slice running along time reads seconds.
        """
        marker = self._newMarker(side)
        self._markers.setdefault(side, []).append(marker)
        return marker

    def markers(self, side):
        return list(self._markers.get(side, []))

    def markerText(self, side, index=0):
        return self._markers[side][index].label.toPlainText()

    def clearMarkers(self):
        for side, markers in self._markers.items():
            for marker in markers:
                self._plots[side].removeItem(marker)
        self._markers = {}

    def _newMarker(self, side):
        axis = self._axes[side].other
        marker = pg.InfiniteLine(pos=float(axis.values[len(axis.values) // 2]),
                                 angle=90, movable=True,
                                 bounds=(float(axis.values[0]),
                                         float(axis.values[-1])),
                                 label=axis.labelFormat())
        self._plots[side].addItem(marker)
        return marker

    def updateValues(self, values, quantity=''):
        """The picture under the lines changed: the lines stay, the slice moves.

        Moving the window of pictures, or a pinned axis, changes what is on
        screen. The line is where the user put it, so it keeps its place; the
        slice is an answer about the picture up now, so it follows. A kept slice
        does not follow: it is a record of the picture that was up when it was
        kept, which is what makes two of them comparable.
        """
        self._draw(values)

    def line(self, side):
        return self._lines[side]

    def curve(self, side):
        return self._curves[side]

    def numbers(self, side):
        return self._curves[side].getData()

    def labelText(self, side):
        return self._lines[side].label.toPlainText()

    def axisLabel(self, side):
        """(name, units) of the abscissa the slice under this line runs along."""
        other = self._axes[side].other
        return (other.name or '', other.units or '')

    def keep(self, side):
        """Record the slice under one line, and leave it on its plot."""
        x, y = self._curves[side].getData()
        label = self.labelText(side)
        curve = self._plots[side].plot(np.asarray(x), np.asarray(y), name=label)
        curve.setPen(pg.mkPen(width=1))
        self._kept.setdefault(side, []).append((label, curve))
        return label

    def kept(self, side):
        return [(label, np.asarray(curve.getData()[1]))
                for label, curve in self._kept.get(side, [])]

    def clearKept(self):
        for side, entries in self._kept.items():
            for _, curve in entries:
                self._plots[side].removeItem(curve)
        self._kept = {}

    def isPosed(self):
        return bool(self._lines)

    def clear(self):
        """Take the lines and the slice plots off the figure."""
        for side, line in self._lines.items():
            if self._picture is not None:
                self._picture.getViewBox().removeItem(line)
        for plot in self._plots.values():
            self._layout.removeItem(plot)
        self._lines = {}
        self._plots = {}
        self._curves = {}
        self._kept = {}
        self._markers = {}
        self._axes = {}

    def _onMoved(self, line):
        self._draw(self._values)

    def _draw(self, values):
        self._values = np.asarray(values)
        if not self._lines or self._values.size == 0:
            return
        for side in self.SIDES:
            x, y = self._slice(side)
            curve = self._curves.get(side)
            if curve is None:
                curve = self._plots[side].plot(x, y)
                curve.setPen(pg.mkPen(width=1, color='k'))
                self._curves[side] = curve
            else:
                curve.setData(x, y)

    def _slice(self, side):
        """The curve under one line: one element of one axis, run along the other.

        The values are screen-oriented, so their first index lies along the
        bottom axis and their second along the left one: the line standing on the
        bottom axis picks the nearest index of the first, and its slice runs
        along the second.
        """
        axis = self._axes[side]
        position = int(np.argmin(np.abs(axis.values - self._lines[side].value())))
        if side == self.BOTTOM:
            return axis.other.values, self._values[position, :]
        return axis.other.values, self._values[:, position]

    def __repr__(self):
        return '<QVizSliceLines %s>' % ({side: self._lines[side].value()
                                         for side in self._lines},)
