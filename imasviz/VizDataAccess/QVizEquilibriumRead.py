# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The read of one occurrence of the `equilibrium` IDS at one time slice.

The quantities the Equilibrium plugin draws (viz_equi/equilibriumcharts.py),
split out of its matplotlib window so a draw can be asked of them by the
application's own figures and by the agent. It reads the IDS object — the lazy
handle the registry hands out — and not the tree, because the tree does not
hold what this read needs: the GGD branch is skipped by the parser when
`Ignore_GGD=1` (the default), and `QVizTensorDataAccess` is not asked for a
grid at all.

The unit conversions are the plugin's unchanged: Ip [kA], W_mhd [kJ],
j_tor [MA/m2], pressure [kPa]; the profiles abscissa is `rho_tor` normalized
by its value at the last point — the separator it spells when it is non-zero,
and the ranks of the array when the case keeps it at zero (the same fallback
the plugin prints as a warning, said here as a named label).

An instant is answered by the case's own slice, the nearest one: a GGD grid
is a discrete structure that can differ slice to slice, and an interpolated
flux surface between two of them is a drawing no one owns. The slice the case
answered with is named back, and a value asked outside the case's range says
it was clamped.
"""

import numpy as np

# The levels a flux surface is drawn at, and the size of the raster the
# contours are cut on. The first is the plugin's `nbr_levels`; the second is a
# draw matter — the grid the case holds (7 229 points on the reference case,
# measured) is not a regular grid, so the levels are cut on a raster laid over
# its extents, and a raster twice as fine answers no different surface.
LEVELS = 30
RASTER = 256

# The radial profiles the window holds, in the order the plugin draws them.
# (quantity, the factor the plugin multiplies by, the units that factor
# spells). `rho_tor` is the abscissa, not a curve; `q` carries the plugin's
# `axhline(1)` reference, said here as a curve like the others.
PROFILES = (
    ('q',                 1.0,   ''),
    ('elongation',        1.0,   ''),
    ('triangularity_upper', 1.0, ''),
    ('triangularity_lower', 1.0, ''),
    ('j_tor',             1e-6,  'MA/m^2'),
    ('pressure',          1e-3,  'kPa'),
    ('f_df_dpsi',         1.0,   ''),
    ('dpressure_dpsi',    1.0,   ''),
)

# The global quantities of the slice, with the factor and units the plugin
# spells. The two axis positions are drawn on the surface; they are in the
# answer so a reader can name them without the window.
GLOBALS = (
    ('ip',        1e-3,  'kA'),
    ('q_95',      1.0,   ''),
    ('q_axis',    1.0,   ''),
    ('li_3',      1.0,   ''),
    ('w_mhd',     1e-3,  'kJ'),
    ('axis_r',    1.0,   'm'),
    ('axis_z',    1.0,   'm'),
)


def _refuse(what, message):
    """A named refusal, as the surfaces of `core.py` raise them."""
    raise ValueError('equilibrium: %s: %s' % (what, message))


def _isPosition(r, z):
    """Whether (r, z) is a position the chart can draw.

    IMAS spells an absent point with its `empty` value — the `-9e40` class,
    measured on the reference case for an O-point that the last slice does
    not hold — and a position a chart can place is one whose coordinates
    are finite and in the metres, not in that century.
    """
    return all(np.isfinite(v) and abs(v) < 1e4 for v in (r, z))


def _value(array, what, message):
    """The one value a 0D node holds, refused by name when it holds none."""
    try:
        values = np.asarray(array, dtype=float)
    except Exception:
        _refuse(what, message)
    values = values.ravel()
    if values.size == 0:
        _refuse(what, message)
    return float(values[0])


class QVizEquilibriumRead:
    """The per-slice read of one occurrence of the `equilibrium` IDS.

    `dataSource` is the case's data source (it holds the registry and the
    URI); the occurrence is the one asked. Everything read here is what a
    slice of that occurrence answers, and everything refused says which
    slice and which node.
    """

    IDS = 'equilibrium'

    def __init__(self, dataSource, occurrence=0):
        self.dataSource = dataSource
        self.occurrence = occurrence
        self._grid = None

    # ------------------------------------------------------------------ ids

    def ids(self):
        try:
            ids = self.dataSource.get(self.IDS, self.occurrence)
        except Exception as e:
            _refuse(self.IDS, 'occurrence %d could not be read: %s'
                    % (self.occurrence, str(e).split('\n', 1)[0][:200]))
        if ids is None:
            _refuse(self.IDS, 'occurrence %d is not in the case or could not '
                    'be read: the log of the case holds the reason the Access '
                    'Layer said.' % self.occurrence)
        if len(getattr(ids, 'time_slice', [])) == 0:
            _refuse(self.IDS, 'occurrence %d holds no time slice, so there is '
                    'no instant to draw.' % self.occurrence)
        return ids

    # --------------------------------------------------------------- times

    def timeValues(self):
        values = np.asarray(self.ids().time, dtype=float).ravel()
        if values.size == 0:
            _refuse(self.IDS + '.time', 'holds no time value in the case.')
        return values

    def resolve(self, time):
        """The slice the case answers for an instant.

        (index, the slice's own time, whether the ask was clamped into the
        case's range). `plot_slice` clamps the same way, which is what lets
        an instant far outside the pulse still name the slice that answered.
        """
        values = self.timeValues()
        asked = float(time)
        clamped = bool(asked < float(values[0]) or asked > float(values[-1]))
        clampedValue = min(max(asked, float(values[0])), float(values[-1]))
        index = int(np.argmin(np.abs(values - clampedValue)))
        return index, float(values[index]), clamped

    # ---------------------------------------------------------------- grid

    def grid(self):
        """The (R, Z, triangles) of the flux surface, one grid for the case.

        The first slice that carries a point grid names it, the way the
        plugin looks; `grid.space` empty (the reference case keeps the 7 229
        point grid in `grids_ggd[0].grid[0]`, measured) falls back there.
        A case that holds neither names it: a surface of flux without a
        triangulation is not a drawing this window does.
        """
        if self._grid is not None:
            return self._grid
        ids = self.ids()
        grid = None
        where = None
        for index in range(len(ids.time_slice)):
            ggd = getattr(ids.time_slice[index], 'ggd', None)
            if ggd is None or len(ggd) == 0:
                continue
            candidate = getattr(ggd[0], 'grid', None)
            if candidate is not None and len(getattr(candidate, 'space', [])) != 0:
                grid, where = candidate, 'time_slice[%d].ggd[0].grid' % index
                break
        if grid is None:
            grids = getattr(ids, 'grids_ggd', None)
            if grids is not None and len(grids) != 0:
                gridStruct = grids[0].grid
                if len(gridStruct) != 0 and len(getattr(gridStruct[0], 'space', [])) != 0:
                    grid, where = gridStruct[0], 'grids_ggd[0].grid[0]'
        if grid is None:
            _refuse('grid', 'occurrence %d carries no 2D grid: neither '
                    'time_slice[i].ggd[0].grid.space nor grids_ggd. The '
                    'flux-surface chart needs a triangulation to cut levels on.'
                    % self.occurrence)

        space = grid.space[0]
        points = space.objects_per_dimension[0].object
        count = len(points)
        if count == 0:
            _refuse(where + '.space[0]', 'holds no point, so the surface has '
                    'no grid to stand on.')
        try:
            R = np.array([point.geometry[0] for point in points], dtype=float)
            Z = np.array([point.geometry[1] for point in points], dtype=float)
        except Exception as e:
            _refuse(where + '.space[0].objects_per_dimension[0]',
                    'does not answer a (R, Z) per point: %s'
                    % str(e).split('\n', 1)[0][:160])
        triangles = np.array(
            [[point.nodes[0], point.nodes[1], point.nodes[2]]
             for point in space.objects_per_dimension[2].object], dtype=int)
        if R.size != count or Z.size != count:
            _refuse(where + '.space[0]', 'answers %d R and %d Z values for %d '
                    'points: the grid is not matched pairs.' % (R.size, Z.size, count))
        if triangles.size == 0:
            _refuse(where + '.space[0].objects_per_dimension[2]',
                    'holds no triangle: the flux surfaces are cut by levels '
                    'on a triangulation, and there is none here.')
        self._grid = (R, Z, triangles)
        return self._grid

    # -------------------------------------------------------------- surface

    def surfaceAt(self, index, levels=LEVELS):
        """One slice of the flux surface: the grid, the psi of it, and the
        marks the plugin draws over the levels.

        Everything read from one slice, and an absent piece is named for that
        slice rather than defaulted: a boundary none, an axis none, an O-point
        none.
        """
        ids = self.ids()
        R, Z, triangles = self.grid()
        slice_ = ids.time_slice[index]
        ggd = getattr(slice_, 'ggd', None)
        if ggd is None or len(ggd) == 0:
            _refuse('time_slice[%d].ggd' % index, 'is empty: this slice holds '
                    'no flux function to contour, and the nearest slice is '
                    'not substituted for it.')
        where = 'time_slice[%d].ggd[0].psi' % index
        psi_element = ggd[0].psi[0]
        # The element of the `psi` array is a structure in the current HLI,
        # and its value sits in the `psi` child of that structure; the older
        # HLI answered the array itself, which `.values` reads the same way
        # around.
        values = getattr(psi_element, 'psi', None)
        if values is None:
            values = getattr(psi_element, 'values', psi_element)
        try:
            psi = np.asarray(values, dtype=float).ravel()
        except Exception as e:
            _refuse(where, 'could not be read: %s'
                    % str(e).split('\n', 1)[0][:160])
        if psi.size == 0:
            _refuse('time_slice[%d].ggd[0].psi' % index,
                    'holds no value: nothing to cut levels of.' % index)
        if psi.size != R.size:
            _refuse('time_slice[%d].ggd[0].psi' % index,
                    'reads %d values on a grid of %d points: the case does '
                    'not match them, and no surface is drawn from such a '
                    'pair.' % (psi.size, R.size))
        low, high = float(psi.min()), float(psi.max())
        if low == high:
            # A flat surface has no level to cut: the linspace the chart uses
            # would be a straight line, and contourpy would answer none.
            _refuse('time_slice[%d].ggd[0].psi' % index,
                    'is flat (%g everywhere): a surface of flux needs levels '
                    'to separate.' % low)

        boundary = None
        outline = getattr(getattr(slice_, 'boundary', None), 'outline', None)
        if outline is not None:
            r = np.asarray(getattr(outline, 'r', []), dtype=float).ravel()
            z = np.asarray(getattr(outline, 'z', []), dtype=float).ravel()
            if r.size != 0 and r.size == z.size:
                boundary = (r, z)

        axis = None
        point = None
        source = getattr(slice_, 'global_quantities', None)
        axis_ = getattr(source, 'magnetic_axis', None) if source is not None else None
        if axis_ is not None:
            try:
                axis = (float(np.asarray(axis_.r, dtype=float).ravel()[0]),
                        float(np.asarray(axis_.z, dtype=float).ravel()[0]))
            except Exception:
                axis = None
            if axis is not None and not _isPosition(axis[0], axis[1]):
                axis = None
        xPoint = getattr(getattr(slice_, 'boundary', None), 'x_point', None)
        if xPoint is not None and len(xPoint) != 0:
            first = xPoint[0]
            try:
                r = float(np.asarray(first.r, dtype=float).ravel()[0])
                z = float(np.asarray(first.z, dtype=float).ravel()[0])
            except Exception:
                r = None
            # The plugin's rule: an O-point the case spells at R = 0 is not
            # an O-point; and IMAS spells an absent O-point with its empty
            # value (the -9e40 class), which is not a drawing either.
            point = None if (r in (0, None) or not _isPosition(r, z)) else (r, z)

        b0 = r0 = None
        field = getattr(slice_, 'vacuum_toroidal_field', None)
        if field is None:
            field = getattr(ids, 'vacuum_toroidal_field', None)
        if field is not None:
            try:
                b0 = float(np.asarray(field.b0, dtype=float).ravel()[0])
            except Exception:
                b0 = None
            try:
                r0 = float(np.asarray(field.r0, dtype=float).ravel()[0])
            except Exception:
                r0 = None

        return {
            'index': index,
            'R': R, 'Z': Z, 'triangles': triangles,
            'psi': psi,
            'levels': np.linspace(low, high, max(int(levels), 2)),
            'boundary': boundary,
            'axis': axis,
            'x_point': point,
            'b0': b0, 'r0': r0,
        }

    def wall(self):
        """The limiter outline of the `wall` IDS, or None.

        Read once — it is static for the case — and matched pairs: the plugin
        refuses an outline whose r and z do not agree in length.
        """
        try:
            ids = self.dataSource.get('wall', self.occurrence)
        except Exception:
            return None
        if ids is None:
            return None
        description = getattr(ids, 'description_2d', None)
        if description is None or len(description) == 0:
            return None
        outline = getattr(description[0].limiter.unit[0], 'outline', None)
        if outline is None:
            return None
        r = np.asarray(getattr(outline, 'r', []), dtype=float).ravel()
        z = np.asarray(getattr(outline, 'z', []), dtype=float).ravel()
        if r.size == 0 or r.size != z.size:
            return None
        return (r, z)

    # -------------------------------------------------------------- profiles

    def profilesAt(self, index):
        """The radial profiles of one slice, in the plugin's order.

        `x` is the abscissa (rho_tor_norm, or the ranks if the case keeps
        the separator at zero — said in `x_label`), `profiles` the drawn
        curves `(name, values, units)`, `empty` the quantities the slice
        holds no value for, and `gls` the global quantities of the slice
        with the factors and units the plugin spells.
        """
        slice_ = self.ids().time_slice[index]
        profiles = getattr(slice_, 'profiles_1d', None)
        if profiles is None:
            _refuse('time_slice[%d].profiles_1d' % index, 'is not in the case.')
        x = np.asarray(getattr(profiles, 'rho_tor', []), dtype=float).ravel()
        if x.size == 0:
            _refuse('time_slice[%d].profiles_1d.rho_tor' % index,
                    'is empty: the profiles have no abscissa to run along, '
                    'and the eight radial curves are drawn against it.')
        separator = float(x[-1])
        if separator != 0:
            abscissa, x_label = x / separator, 'rho_tor_norm'
        else:
            abscissa, x_label = np.linspace(0, 1, x.size), 'Eq_space_pts'

        curves = []
        missing = []
        for name, factor, units in PROFILES:
            value = np.asarray(getattr(profiles, name, []), dtype=float).ravel()
            where = 'time_slice[%d].profiles_1d.%s' % (index, name)
            if value.size == 0:
                missing.append(where)
                continue
            if value.size != abscissa.size:
                _refuse(where, 'reads %d values against an abscissa of %d: '
                        'the case does not match them.' % (value.size, abscissa.size))
            curves.append((name, value * factor, units))

        global_ = {}
        source = getattr(slice_, 'global_quantities', None)
        for name, factor, units in GLOBALS:
            if name == 'axis_r':
                value = getattr(getattr(source, 'magnetic_axis', None), 'r', None)
            elif name == 'axis_z':
                value = getattr(getattr(source, 'magnetic_axis', None), 'z', None)
            else:
                value = getattr(source, name, None)
            try:
                scalar = float(np.asarray(value, dtype=float).ravel()[0])
            except Exception:
                continue
            global_[name] = {'value': scalar * factor, 'units': units}

        return {
            'index': index,
            'x': abscissa,
            'x_label': x_label,
            'profiles': curves,
            'empty': missing,
            'global': global_,
        }
