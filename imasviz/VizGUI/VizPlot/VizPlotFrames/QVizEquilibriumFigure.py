# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The equilibrium window: flux-surface frames in a row, and under them a stack of profiles.

One of the two shapes of the equilibrium read (`QVizEquilibriumRead`): the
row shows several instants at once, each in the application's own drawing
style — the ground is black, the one this application paints
(`pyqtgraph`'s own default); the palette is `QVizCurveColors`, legible on
that ground; and a frame that holds nothing is a named refusal, not a blank.
That is the window the row exists for, the comparison a single frame
cannot: the same levels, the same bounds, the same marks, at the instants
the caller named.

The window is not drawn through the axes model: `ggd` is a discrete
structure the tree does not hold (`Ignore_GGD=1` skips it), and the read is
the `QVizEquilibriumRead` of the IDS object, not the tensor read of a node.
It keeps its own figure namespace (`FigureTypes.EQUISURFACES`), registered
in `figureframes` like a figure, so that the *Windows* menu, its *Delete*
sub-menu, the sessions and the screenshots reach it in the same way they
reach the others.
"""

import numpy as np
import pyqtgraph as pg

from PySide6.QtWidgets import QVBoxLayout, QWidget

from imasviz.VizDataAccess.QVizEquilibriumRead import RASTER
from imasviz.VizGUI.VizPlot.QVizCurveColors import colourFor, nameFor


# The 12 non-saddle cases of marching squares over a cell of four corners:
# the pair of edges the level crosses. The code's bits name the corners
# above the level -- bottom-left corner 1, top-left 2, top-right 4,
# bottom-right 8 -- and the edges are numbered 0 bottom, 1 top, 2 left,
# 3 right. A contour crosses an edge exactly when that edge's two corners
# answer on opposite sides of the level, which is what each row of this
# table spells out.
_CASES = {
    1: ((2, 0),), 2: ((2, 1),), 3: ((0, 1),), 4: ((1, 3),),
    6: ((2, 3),), 7: ((0, 3),), 8: ((0, 3),), 9: ((2, 3),),
    11: ((1, 3),), 12: ((0, 1),), 13: ((2, 1),), 14: ((0, 2),),
}

# The two saddle codes, where both diagonals are above and both off-diagonals
# below (or vice versa) and the level crosses all four edges: the centre of
# the cell decides which pairs of edges belong to the same contour. The first
# pair set is the one the cell answers when its centre is above the level.
_SADDLES = {
    5:  ([(2, 1), (0, 3)], [(2, 0), (1, 3)]),
    10: ([(2, 0), (1, 3)], [(2, 1), (0, 3)]),
}


class _RasterField:
    """The flux function rasterized over the grid's extents.

    The case holds a triangulation, not a raster: the levels are cut on a
    raster laid over its extents, and the `LinearTriInterpolator` measures
    the value at every corner -- `nan` outside the convex hull, which is how
    a hole in the surface says so (the plugin's `tricontour` cuts the same
    levels directly on the triangles, and the answer is the same surface
    through a raster the levels are read across). The raster is a place,
    not the surface: twice finer answers a level no one can tell apart, so
    it is a constant of the read (`RASTER`), not an argument here.

    The corner values, the finiteness of the cells and the positions of
    their corners are settled once, because one raster is cut at many
    levels. A cell whose corners are not all finite is never cut: a hole is
    an absence, not a line laid across it.
    """

    def __init__(self, R, Z, triangles, psi):
        from matplotlib.tri import LinearTriInterpolator, Triangulation
        self.xr = np.linspace(float(R.min()), float(R.max()), RASTER)
        self.yr = np.linspace(float(Z.min()), float(Z.max()), RASTER)
        rGrid, zGrid = np.meshgrid(self.xr, self.yr, indexing='ij')
        values = np.asarray(
            LinearTriInterpolator(Triangulation(R, Z, triangles), psi)
            (rGrid, zGrid), dtype=float)
        if not np.isfinite(values).any():
            raise ValueError('no value of the triangulation answered inside '
                             'its own extents: the surface has no raster to '
                             'cut levels on.')
        self.nx = self.xr.size - 1
        self.ny = self.yr.size - 1
        # a = bottom-left, b = top-left, c = top-right, d = bottom-right.
        self.a_ = values[:-1, :-1]
        self.b_ = values[:-1, 1:]
        self.c_ = values[1:, 1:]
        self.d_ = values[1:, :-1]
        self.finite = (np.isfinite(self.a_) & np.isfinite(self.b_)
                       & np.isfinite(self.c_) & np.isfinite(self.d_))
        self.centre = (self.a_ + self.b_ + self.c_ + self.d_) / 4
        # Corner coordinates, at every cell: the crossing formulas only
        # differ in which corner of the edge they start from.
        self.A_r = np.tile(self.xr[:-1][:, None], (1, self.ny))
        self.D_r = np.tile(self.xr[1:][:, None], (1, self.ny))
        self.A_z = np.tile(self.yr[:-1][None, :], (self.nx, 1))
        self.B_z = np.tile(self.yr[1:][None, :], (self.nx, 1))

    def segments(self, level):
        """The (p, q) crossing pairs of one level, each point an (r, z) float."""
        from collections import defaultdict

        def point(r0, r1, z0, z1, v0, v1):
            t = (level - v0) / (v1 - v0)
            return (r0 + t * (r1 - r0), z0 + t * (z1 - z0))
        with np.errstate(invalid='ignore', divide='ignore'):
            edges = {
                # bottom (a-d), top (b-c), left (a-b), right (d-c).
                0: point(self.A_r, self.D_r, self.A_z, self.A_z, self.a_, self.d_),
                1: point(self.A_r, self.D_r, self.B_z, self.B_z, self.b_, self.c_),
                2: point(self.A_r, self.A_r, self.A_z, self.B_z, self.a_, self.b_),
                3: point(self.D_r, self.D_r, self.A_z, self.B_z, self.d_, self.c_),
            }
        code = ((self.a_ > level).astype(np.int8)
                + 2 * (self.b_ > level).astype(np.int8)
                + 4 * (self.c_ > level).astype(np.int8)
                + 8 * (self.d_ > level).astype(np.int8))

        def collect(mask, pairs):
            """The crossing points of the cells holding `mask`, as pairs."""
            if not mask.any():
                return
            rows = np.argwhere(mask)
            i = rows[:, 0]
            j = rows[:, 1]
            for edgeOne, edgeTwo in pairs:
                p1r = edges[edgeOne][0][i, j]
                p1z = edges[edgeOne][1][i, j]
                p2r = edges[edgeTwo][0][i, j]
                p2z = edges[edgeTwo][1][i, j]
                for k in range(i.shape[0]):
                    segments.append(((float(p1r[k]), float(p1z[k])),
                                     (float(p2r[k]), float(p2z[k]))))

        segments = []
        centreAbove = self.centre > level
        for eachCode, pairs in _CASES.items():
            collect(self.finite & (code == eachCode), pairs)
        for eachCode, (above, below) in _SADDLES.items():
            collect(self.finite & (code == eachCode) & centreAbove, above)
            collect(self.finite & (code == eachCode) & (~centreAbove), below)
        adjacency = defaultdict(list)
        for index, (q, r) in enumerate(segments):
            adjacency[q].append((index, r))
            adjacency[r].append((index, q))
        used = set()
        polylines = []
        for index in range(len(segments)):
            if index in used:
                continue
            used.add(index)
            first, last = segments[index]
            path = [first, last]
            for end in (0, 1):
                cursor = path[end]
                while True:
                    nxt = None
                    for index2, other in adjacency[cursor]:
                        if index2 not in used:
                            used.add(index2)
                            nxt = other
                            break
                    if nxt is None:
                        break
                    if end == 0:
                        path.insert(0, nxt)
                    else:
                        path.append(nxt)
                    cursor = nxt
            polylines.append(np.asarray(path, dtype=float))
        return polylines


def isolineSegments(R, Z, triangles, psi, levels):
    """The (x, y) of every level: the polylines of one level in a row, a NaN
    gap between two polylines.

    The levels are cut by marching squares on the raster of `psi` over the
    grid's extents (a cell whose corners are not all finite is never cut).
    The joints of neighbouring cells are answered bit-for-bit identical,
    which is what the chain at the end of `segments` relies on to join the
    crossing pairs into one polyline per contour.
    """
    field = _RasterField(R, Z, triangles, psi)
    x, y = [], []
    for level in levels:
        for polyline in field.segments(float(level)):
            x.append(polyline[:, 0])
            y.append(polyline[:, 1])
            x.append([np.nan])
            y.append([np.nan])
    if not x:
        raise ValueError('no level of the %d levels asked could be cut: the '
                         'case may keep its psi flat, or the triangulation '
                         'may not span the raster.' % len(levels))
    return np.concatenate(x), np.concatenate(y)


class QVizEquilibriumFigure(QWidget):
    """The frames of one equilibrium read.

    1..N flux-surface frames in a row (one per named instant), and under
    them a stack of the radial profiles of one instant. A window that
    holds neither answers no curve at all, and
    `QVizPlotOneNode.discardIfEmpty` takes it back for that.
    """

    def __init__(self, parent=None, title=''):
        super().__init__(parent)
        self.figureKey = None
        self._row = []
        self._profilesStack = None

        self.pgPlotWidget = pg.GraphicsLayoutWidget(self)
        self.pgPlotWidget.setObjectName('equilibriumSurfaces')

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.pgPlotWidget)
        layout.addStretch(1)

        if title:
            self.setWindowTitle(title)

    # --------------------------------------------------------------- row

    def drawRow(self, surfaces, wall=None):
        """Lays the row of frames down, one per read. Returns how many sit on it.

        The bounds of the row are settled across every frame at once, which
        is the comparison the row is present for: a frame whose own psi
        spans one tenth of the case's would otherwise dress to the same
        colour as one that spans the case, and a boundary drawn against a
        frame of its own would not be comparable to one of its neighbour's.
        """
        if self._row:
            raise ValueError('This figure already holds %d flux-surface frame(s): '
                             'a second read needs a window of its own.' % len(self._row))
        if not surfaces:
            raise ValueError('no frame to draw: the row of an equilibrium figure '
                             'needs at least one read.')
        plotItems = []
        for position, surface in enumerate(surfaces):
            plotItem = self.pgPlotWidget.addPlot(row=0, col=position)
            plotItem.setAspectLocked(True)
            self._frame(plotItem, surface, wall)
            plotItem.setTitle(self._titleOf(surface))
            plotItems.append(plotItem)
        self._setCommonBounds(plotItems, surfaces, wall)
        self._row = [(plot, surface) for plot, surface in zip(plotItems, surfaces)]
        return len(self._row)

    def _frame(self, plotItem, surface, wall):
        """One frame: the levels of the psi, and the marks the plugin drew over them."""
        x, y = isolineSegments(surface['R'], surface['Z'], surface['triangles'],
                               surface['psi'], surface['levels'])
        plotItem.plot(x, y, pen=pg.mkPen(colourFor(0), width=1),
                      name='psi levels (' + nameFor(0) + ')')
        if surface['boundary'] is not None:
            r, z = surface['boundary']
            plotItem.plot(np.asarray(r, dtype=float), np.asarray(z, dtype=float),
                          pen=pg.mkPen(colourFor(1), width=2),
                          name='plasma boundary (' + nameFor(1) + ')')
        if surface['axis'] is not None:
            r, z = surface['axis']
            plotItem.plot([r], [z], pen=pg.mkPen(width=0, color=colourFor(2)),
                          symbol='+', symbolBrush=colourFor(2), symbolSize=12,
                          name='magnetic axis (' + nameFor(2) + ')')
        if surface['x_point'] is not None:
            r, z = surface['x_point']
            plotItem.plot([r], [z], pen=pg.mkPen(width=0, color=colourFor(3)),
                          symbol='x', symbolBrush=colourFor(3), symbolSize=12,
                          name='x-point (' + nameFor(3) + ')')
        if wall is not None:
            r, z = wall
            plotItem.plot(np.asarray(r, dtype=float), np.asarray(z, dtype=float),
                          pen=pg.mkPen(colourFor(4), width=2),
                          name='limiter (' + nameFor(4) + ')')
        plotItem.setLabel('bottom', 'R', units='m')
        plotItem.setLabel('left', 'Z', units='m')

    def _titleOf(self, surface):
        """What the frame stands for, in the words the plugin's title said."""
        time = surface['time_slice_time'] if 'time_slice_time' in surface else None
        words = []
        if time is not None:
            words.append('t = %g s' % time)
        words.append('slice %d' % surface['index'])
        if surface['b0'] is not None:
            words.append('B0 = %g T' % surface['b0'])
        if surface['r0'] is not None:
            words.append('R0 = %g m' % surface['r0'])
        return '   '.join(words)

    def _setCommonBounds(self, plotItems, surfaces, wall):
        """One pair of bounds across the whole row.

        Measured the other way, every plot re-scaled to its own data: a
        frame that holds a tenth of the case's psi span, or whose boundary
        dips lower, would dress to a different colour than its neighbour's,
        which is the comparison the row exists to remove.
        """
        xs = [surface['R'] for surface in surfaces]
        ys = [surface['Z'] for surface in surfaces]
        for surface in surfaces:
            if surface['boundary'] is not None:
                r, z = surface['boundary']
                xs.append(r)
                ys.append(z)
        if wall is not None:
            r, z = wall
            xs.append(r)
            ys.append(z)
        lowX = float(min(np.min(np.asarray(v, dtype=float)) for v in xs))
        lowY = float(min(np.min(np.asarray(v, dtype=float)) for v in ys))
        highX = float(max(np.max(np.asarray(v, dtype=float)) for v in xs))
        highY = float(max(np.max(np.asarray(v, dtype=float)) for v in ys))
        marginX = 0.05 * (highX - lowX) if highX > lowX else 0.01
        marginY = 0.05 * (highY - lowY) if highY > lowY else 0.01
        for plotItem in plotItems:
            plotItem.setRange(xRange=(lowX - marginX, highX + marginX),
                              yRange=(lowY - marginY, highY + marginY))

    # ------------------------------------------------------------- stack

    def drawProfiles(self, x, xLabel, xUnits, profiles):
        """Lays down the radial profiles. Returns how many panels the stack holds.

        One panel per quantity in the order given, on the abscissa the read
        settled: they all run on the same one, which is what the stack
        (`QVizStackedPlot`) is, and what keeps a profile read against the
        clock from masquerading as a radial one.
        """
        if self._profilesStack is not None:
            raise ValueError('This figure already holds a stack of %d profile panels.'
                             % self._profilesStack.panelCount())
        from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizStackedPlot import QVizStackedPlot
        stack = QVizStackedPlot(self)
        for name, values, units in profiles:
            stack.plotRaw(x, values, name, name_units=units,
                          x_label=xLabel, x_units=xUnits)
        self._profilesStack = stack
        stack.applyLinkPolicy()
        stack.applyXLabelsPolicy()
        return stack.panelCount()

    # ---------------------------------------------------------- accessors

    def surfaceFrames(self):
        return len(self._row)

    def profilePanels(self):
        return 0 if self._profilesStack is None else self._profilesStack.panelCount()

    def profilesStack(self):
        return self._profilesStack

    def curveCount(self):
        count = sum(len(plotItem.listDataItems()) for plotItem, _ in self._row)
        if self._profilesStack is not None:
            count += self._profilesStack.curveCount()
        return count

    def isDrawing(self):
        return self.curveCount() > 0

    def plotItem(self):
        """The first frame's plot, for whoever asks one plot item of the window."""
        if not self._row:
            return None
        return self._row[0][0]

    def windowsForStyle(self):
        """The plots this window's *Configure Plot* entries dress."""
        items = [plot for plot, _ in self._row]
        if self._profilesStack is not None:
            items += [panel.plotItem() for panel in self._profilesStack.panels()]
        return items
