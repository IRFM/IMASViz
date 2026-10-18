# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
import re

import numpy as np

from imas.ids_struct_array import IDSStructArray

from imasviz.VizDataAccess.QVizAxesSpec import QVizAxis

# coordinateSegments comes from QVizIDSViewParser, whose module imports reach the
# whole VizGUI package -- and the GUI's plotting commands import the data access
# factory, which imports this module. Importing it here closes that cycle, so it
# is imported where it is used, as Viz_API does for the factory itself.

# One step of a parametrized path: a node name and, for an array of
# structures, the loop placeholder the view wrote in front of it.
SEGMENT = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)(?:\[([a-z]+)\])?$')


def pathSegments(path):
    """Splits a parametrized path into (name, placeholder) steps.

    'equilibrium.time_slice[itime].boundary.r_0' becomes five steps, the second
    carrying 'itime'. The view turns the same path into Python source and hands
    it to eval, which works while the rank is known in advance (patchIndices
    writes [i1] as [i], [i2] as [j], and so on) but needs one spelled expression
    per rank, and only reports a mistake once the string is executed. Walking
    the names instead keeps the rank a number.
    """
    segments = []
    for step in str(path).split('.'):
        match = SEGMENT.match(step)
        if match is None:
            raise ValueError('Cannot read the path step %r in %r' % (step, path))
        segments.append((match.group(1), match.group(2)))
    return segments


class QVizTensor:
    """A quantity read whole, with what each of its axes means.

    axesValues holds one entry per axis of the spec, in the same order: an
    array when the axis has values (a time base, a coordinate), None when the
    dictionary leaves it unbounded (1..N) or this case holds no values for it.
    """

    def __init__(self, values, axesValues, axesSpec, timeAxisPosition=None,
                 indexAxes=None):
        self.values = values
        self.axesValues = axesValues
        self.axesSpec = axesSpec
        self.timeAxisPosition = timeAxisPosition
        # Axis position -> how many elements the array of structures that names
        # that axis holds. The axis itself is left without values, because its
        # values are its own ranks; the count is what lets the caller notice a
        # dictionary whose array and whose values disagree.
        self.indexAxes = indexAxes or {}

    @property
    def rank(self):
        return self.values.ndim

    def timeAxisValues(self):
        if self.timeAxisPosition is None:
            return None
        return self.axesValues[self.timeAxisPosition]

    def alongTime(self):
        """The time axis and the values laid along it.

        For a scalar inside a dynamic array of structures that is the whole
        curve, which is what the view calls "0D and dynamic".
        """
        if self.timeAxisPosition is None:
            return None, None
        return (self.axesValues[self.timeAxisPosition],
                self.values[self.timeAxisPosition])

    def atTime(self, position):
        """The tensor with its time axis reduced to one index."""
        if self.timeAxisPosition is None:
            return self.values
        return np.take(self.values, position, axis=self.timeAxisPosition)


class QVizTensorExtractor:
    """Reads a leaf out of the runtime IDS object as one tensor.

    The path is walked one attribute at a time, so the rank is a number rather
    than a shape the caller has to know: a leaf inside three arrays of
    structures and 1D of its own comes back rank 4 without any new branch.

    Where the time base lives is decided by ids_properties.homogeneous_time.
    When it is 1, IDS.time is the time base of every dynamic quantity of the
    IDS. When it is 0, each array of structures carries times of its own under
    <aos>[i].time: those of the dynamic array make up the same base as IDS.time,
    while a quantity under a static array is timed by that array's own times.
    An IDS with homogeneous_time 0 need not carry IDS.time at all (the reference
    case's pulse_schedule does not), which is why the array is read first.
    """

    def __init__(self, idsInstance):
        self.idsInstance = idsInstance

    def homogeneousTime(self):
        try:
            return int(self.idsInstance.ids_properties.homogeneous_time)
        except Exception:
            return 1

    def extract(self, axesSpec, aosIndices=None):
        """Reads one leaf into a tensor.

        aosIndices maps an array-of-structures level to the element to keep.
        A level left out stays a tensor axis -- leaving the dynamic (time) level
        out is what makes the time curve exist at all.
        """
        if aosIndices is None:
            aosIndices = {}
        segments = pathSegments(axesSpec.dataPath)[1:]  # the IDS name is the object
        timePosition = self._timeAxisPosition(axesSpec)

        keptLevels = [level for level in range(1, axesSpec.aosCount() + 1)
                      if level not in aosIndices]
        values = np.array(self._read(segments, self.idsInstance, 0, aosIndices),
                          dtype=float)
        if values.dtype == object:
            raise ValueError('%s does not hold the same shape in every slice of %s'
                             % (axesSpec.dataPath, ', '.join(
                                 'level %d' % level for level in keptLevels)))

        axesValues = []
        indexAxes = {}
        for position, axis in enumerate(axesSpec.axes):
            if axis.is_time and position == timePosition:
                axesValues.append(self._timeValues(axesSpec, timePosition))
            else:
                axesValues.append(self._axisValues(axesSpec, axis, aosIndices,
                                                  position, indexAxes))
        return QVizTensor(values, axesValues, axesSpec, timePosition, indexAxes)

    def _timeAxisPosition(self, axesSpec):
        for position, axis in enumerate(axesSpec.axes):
            if axis.is_time and axis.origin == QVizAxis.AOS:
                return position
        return None

    def _read(self, steps, holder, level, aosIndices):
        """Descends the path, keeping every unindexed array as a list axis.

        The name is read first, always: an array of structures is reached by its
        name and indexed only afterwards. Iterating a structure that was never
        reached by name walks its fields instead of its elements, which looks
        like a path step that worked on the wrong object.
        """
        for index, (name, placeholder) in enumerate(steps):
            holder = getattr(holder, name)
            if placeholder is None:
                continue
            level += 1
            rest = steps[index + 1:]
            if level in aosIndices:
                return self._read(rest, holder[aosIndices[level]], level, aosIndices)
            return [self._read(rest, element, level, aosIndices) for element in holder]
        return holder

    def _timeValues(self, axesSpec, timePosition):
        """The time base, placed by ids_properties.homogeneous_time."""
        if timePosition is None:
            return None
        if self.homogeneousTime() == 0:
            # Times are held by the array that carries the quantity: walk down
            # to it and collect one time per element.
            arrayTimes = self._arrayTimes(axesSpec, timePosition)
            if arrayTimes is not None:
                return arrayTimes
        try:
            return np.asarray(self.idsInstance.time, dtype=float)
        except Exception:
            return None

    def _arrayTimes(self, axesSpec, timePosition):
        """The per-element time of the dynamic array itself.

        The level names the array, not the spelling. buildLeaf rewrites the
        placeholder of the time level as [itime] in parametrizedPath while the
        data path keeps the loop letter ([i] for the first level), so comparing
        the two spellings never lands on the dynamic array and its own times go
        unread -- which only shows on an IDS whose homogeneous_time is 0, and
        not at all when the array's times happen to equal IDS.time.
        """
        axis = axesSpec.axes[timePosition]
        steps = pathSegments(axesSpec.dataPath)[1:]
        level = 0
        for index, (name, placeholder) in enumerate(steps):
            if placeholder is None:
                continue
            level += 1
            if level != axis.level:
                continue
            try:
                # Reading through the array name lands on the array itself,
                # so its elements are the holders of the time.
                holder = self._read(steps[:index + 1], self.idsInstance, 0, {})
                return np.asarray([element.time for element in holder], dtype=float)
            except Exception:
                return None
        return None

    def _axisValues(self, axesSpec, axis, aosIndices, position, indexAxes):
        """The values of one leaf coordinate, read under the same indices.

        A coordinate spelled as a time base is resolved by
        ids_properties.homogeneous_time and by nothing else. When it is 1 the
        base is IDS.time for every dynamic quantity of the IDS -- which is what
        the reference case needs, since tf.b_field_tor_vacuum_r.time holds no
        values there while IDS.time holds 17 344. When it is 0 the spelled
        coordinate is the base: it sits under the element carrying the quantity
        (b_field_tor_vacuum_r/time, ic/antenna(i1)/power/reference/time), and
        nothing stands in for it. An empty one leaves the axis without values
        rather than borrowing the IDS clock, which would plot the values
        against a time they were never taken on.

        A coordinate that is an array of structures itself names its axis
        without holding values for it: the rows of the quantity are the
        elements of that array, so the axis is their rank and its extent is the
        length of the array. Indexing it -- as a step of a longer path is --
        would descend one element and answer a whole axis with one number.
        """
        if axis.coordinate is None:
            return None
        if axis.is_time and self.homogeneousTime() == 1:
            return self._idsTime()
        from imasviz.VizDataAccess.QVizIDSViewParser import coordinateSegments
        holder = self.idsInstance
        level = 0
        segments = coordinateSegments(axis.coordinate)
        if segments and segments[0] == axesSpec.idsName:
            segments = segments[1:]  # the coordinate was spelled from the IDS
        named = [segment for segment in segments if not segment.isdigit()]
        for step, segment in enumerate(named):
            # A coordinate is spelled relative to the IDS, and a step of it may
            # be an array of structures the quantity sits in: descend it with
            # the index the leaf was read at, or the first element when the
            # caller kept that array as an axis. Iterating such an array without
            # indexing it first walks the fields of its elements instead.
            holder = getattr(holder, segment)
            if not isinstance(holder, IDSStructArray):
                continue
            if step + 1 == len(named):
                indexAxes[position] = len(holder)
                return None
            level += 1
            holder = holder[aosIndices.get(level, 0)]
        try:
            values = np.asarray(holder, dtype=float)
        except (TypeError, ValueError):
            return None
        return values if values.size else None

    def _idsTime(self):
        try:
            values = np.asarray(self.idsInstance.time, dtype=float)
        except Exception:
            return None
        return values if values.size else None
