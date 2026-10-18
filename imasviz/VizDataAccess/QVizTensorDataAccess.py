# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import logging

import numpy as np

from imasviz.VizDataAccess.QVizAxesSpec import QVizAxesSpec, QVizAxis
from imasviz.VizDataAccess.QVizSlices import sliceLabel, slicesFor
from imasviz.VizDataAccess.QVizTensorExtractor import QVizTensorExtractor
from imasviz.VizEntities.QVizDataArrayHandle import QVizDataArrayHandle, ArrayCoordinates


class QVizTensorDataAccess:
    """The widgets' data access, reading a quantity whole instead of slice by slice.

    The surface is QVizIMASNativeDataAccess's on purpose: GetSignal answers
    either a (t, r) pair -- one row each, the way the plot code indexes them --
    or a QVizDataArrayHandle for a two-dimension leaf. A widget therefore cannot
    tell which access it got, and switching the preference cannot change what it
    draws.

    What changes is the number of reads. The current access builds one Python
    expression per time slice and evaluates it (getDataTimeSlices, then evalPath
    in the loop), and it decides what to build from the leaf's nominal dimension
    -- is0DAndDynamic, is1DAndDynamic, is2DAndDynamic -- which is why a quantity
    in three arrays of structures has no branch at all. Here the quantity is
    read once along all of its axes, and the slice a plot needs is one index
    into it: the rank stops being a case distinction.
    """

    def __init__(self, dataSource):
        self.dataSource = dataSource

    def GetSignal(self, treeNode, plotWidget=None, as_function_of_time=None,
                  coordinate_index=0, time_index=None, slices=None):
        """The quantity, read whole and reduced to what this plot draws.

        slices is {axis key: index}: the index to read each axis the plot does
        not draw at. It overrides the index the tree carries for an array of
        structures and the coordinate_index for a leaf axis, which is what a
        slice control is for. Left alone, the answer is the one the tree's own
        indices give.
        """
        axesSpec, timeAxis, alongTime, _ = \
            self.plan(treeNode, plotWidget, as_function_of_time)
        extractor = QVizTensorExtractor(treeNode.getIDSRef())
        if time_index is None:
            time_index = int(treeNode.timeValue())
        if slices is None:
            # A plot frame that carries slice controls decides them; the axes
            # those controls offer are the ones this read fixes, because both
            # come out of plan().
            controls = getattr(plotWidget, 'sliceControls', None)
            if controls is not None:
                slices = controls.indices()
        if plotWidget is not None and plotWidget.addTimeSlider:
            if plotWidget.sliderGroup is not None:
                time_index = plotWidget.sliderGroup.slider.value()
        if plotWidget is not None and plotWidget.addCoordinateSlider:
            if plotWidget.sliderGroup is not None:
                coordinate_index = plotWidget.sliderGroup.slider.value()

        if alongTime:
            return self._curveAlongTime(treeNode, axesSpec, extractor, timeAxis,
                                        coordinate_index, slices)
        return self._sliceAtTime(treeNode, axesSpec, extractor, plotWidget,
                                 coordinate_index, time_index, slices)

    def plan(self, treeNode, plotWidget=None, as_function_of_time=None):
        """What this plot draws, and therefore which axes must be fixed.

        One place decides it, because the read, the slice controls and the axis
        labels all have to agree: a control for an axis the plot already draws,
        no control for an axis the read silently fixes, or a label naming a
        different axis than the one the numbers came off, all look right until
        the numbers move under the user.
        """
        axesSpec = QVizAxesSpec.fromTreeNode(treeNode)
        timeAxis = self._timeAxis(axesSpec)
        if as_function_of_time is None:
            as_function_of_time = \
                treeNode.isPlotToPerformAlongTimeAxis(plotWidget=plotWidget)
        alongTime = bool(as_function_of_time) and timeAxis is not None
        return axesSpec, timeAxis, alongTime, self._plottedPositions(axesSpec,
                                                                     timeAxis,
                                                                     alongTime)

    def _plottedPositions(self, axesSpec, timeAxis, alongTime):
        if alongTime:
            for position, axis in enumerate(axesSpec.axes):
                if axis is timeAxis:
                    return (position,)
        return tuple(position for position, axis in enumerate(axesSpec.axes)
                     if axis.origin == QVizAxis.LEAF)

    def slicesFor(self, treeNode, plotWidget=None, as_function_of_time=None,
                  coordinate_index=0):
        """The axes this plot does not draw, ready for a control.

        A leaf axis length comes from the values themselves: the dictionary
        often names no node for it (the 1..N spelling), so the only length that
        means anything is the length of what was read.
        """
        axesSpec, timeAxis, alongTime, plotted = \
            self.plan(treeNode, plotWidget, as_function_of_time)
        aosIndices = self._fixedIndices(axesSpec, timeAxis=timeAxis,
                                        timeIndex=None, slices=None)
        tensor = QVizTensorExtractor(treeNode.getIDSRef()).extract(axesSpec,
                                                                   aosIndices)
        lengths = {}
        for valueAxis, position in enumerate(self._keptAxes(axesSpec, aosIndices)):
            if valueAxis < tensor.values.ndim:
                lengths[axesSpec.axes[position].key()] = tensor.values.shape[valueAxis]
        for axis in axesSpec.axes:
            if axis.origin == QVizAxis.AOS and axis.length is not None:
                lengths.setdefault(axis.key(), axis.length)
        return slicesFor(axesSpec, plotted, lengths)

    def _timeAxis(self, axesSpec):
        """The array of structures carrying the time index, if there is one."""
        for axis in axesSpec.axes:
            if axis.is_time and axis.origin == QVizAxis.AOS:
                return axis
        return None

    def _fixedIndices(self, axesSpec, timeIndex=None, timeAxis=None, slices=None):
        """The index every array of structures is read at.

        An array of structures is not an axis of the plot: the tree already
        carries the index the user picked for it, and the current path
        substitutes the same values when it builds its time slices. Only the
        dynamic array can stay open, and only when the curve runs along time.
        """
        indices = {}
        for axis in axesSpec.axes:
            if axis.origin != QVizAxis.AOS:
                continue
            if timeAxis is not None and axis.level == timeAxis.level:
                index = self._effectiveTimeIndex(axesSpec, timeAxis, timeIndex,
                                                 slices)
                if index is not None:
                    indices[axis.level] = index
                continue
            indices[axis.level] = self._sliceIndex(axis, slices, axis.index)
        return indices

    def _effectiveTimeIndex(self, axesSpec, timeAxis, timeIndex, slices):
        """Which element of the dynamic array this read takes.

        A slice control wins over the index the caller passes. A curve along time
        draws that array, so it offers no control for it and the caller's index
        stands; an image does not draw it, so its control is where the user picks
        the time slice, and a read that ignored the control would leave the
        picture alone while its control moved.

        None means nothing decides it, which is the curve-along-time case: the
        array stays an axis of the tensor.
        """
        if timeAxis is None:
            return timeIndex
        # Read the control off the mapping rather than through _sliceIndex: that
        # one turns a missing index into 0, which would fix the dynamic array at
        # its first element on a curve that draws it -- collapsing the curve to a
        # point, silently.
        chosen = None if slices is None else slices.get(timeAxis.key())
        if chosen is None:
            return timeIndex
        return self._sliceIndex(timeAxis, slices, chosen)

    def _sliceIndex(self, axis, slices, default):
        """Where to read one axis: the slice control wins over the tree.

        Validated against the length the tree carries, because a slice index
        comes from a control the user moves: out of range it must say which
        axis is out, not raise an IndexError about a numpy axis.
        """
        index = default
        if slices is not None:
            chosen = slices.get(axis.key())
            if chosen is not None:
                index = chosen
        if index is None:
            index = 0
        index = int(index)
        if axis.length is not None and not 0 <= index < int(axis.length):
            raise ValueError("Slice index " + str(index) + " for '" +
                             sliceLabel(axis) + "' is out of the " +
                             str(axis.length) + " elements of that axis.")
        return index

    def _curveAlongTime(self, treeNode, axesSpec, extractor, timeAxis,
                        coordinate_index, slices=None):
        """The quantity read along the dynamic array, one point per time slice.

        The leaf's own axes are read at coordinate_index, which is what the
        current path does by appending [coordinate_index] to each slice path.
        """
        aosIndices = self._fixedIndices(axesSpec, timeIndex=None, timeAxis=timeAxis,
                                        slices=slices)
        tensor = extractor.extract(axesSpec, aosIndices)
        values = self._fixLeafAxes(axesSpec, self._keptAxes(axesSpec, aosIndices),
                                   tensor.values, coordinate_index, slices)
        if values.size == 0:
            # The leaf's own axis holds no value in this case, so there is no
            # point per time slice either. Dropping the time axis with it is
            # what the current path does by discarding every slice that failed
            # to evaluate, and it keeps the two rows the plot code zips equal.
            return np.array([np.asarray([])]), np.array([np.asarray([])])
        return np.array([tensor.timeAxisValues()]), np.array([values])

    def _keptAxes(self, axesSpec, aosIndices):
        """Which axes of the spec survive into the tensor values, in order.

        An array of structures read at a fixed index leaves no axis in values,
        while its coordinate still occupies a slot in axesValues. The two lists
        are therefore not indexed the same way: using a spec position as a numpy
        axis silently indexes the wrong dimension, which on a rank 3 quantity
        turns a curve into a third axis of its own.
        """
        return [position for position, axis in enumerate(axesSpec.axes)
                if axis.origin == QVizAxis.LEAF or axis.level not in aosIndices]

    def _sliceAtTime(self, treeNode, axesSpec, extractor, plotWidget,
                     coordinate_index, time_index, slices=None):
        """One slice of the quantity, taken at the index the plot is on.

        Every array of structures is read at the index the tree carries (the
        dynamic one at time_index), so what is left is the leaf's own dimension
        or dimensions -- which is also why the leaf axes below are the value
        axes in order.
        """
        timeAxis = self._timeAxis(axesSpec)
        # The labels are built below from the time index, so they have to be
        # told the index the read used: a picture taken at slice 1 and labelled
        # '[0]' is the drift this path exists to remove.
        time_index = self._effectiveTimeIndex(axesSpec, timeAxis, time_index,
                                              slices)
        tensor = extractor.extract(
            axesSpec,
            self._fixedIndices(axesSpec, timeIndex=time_index, timeAxis=timeAxis,
                               slices=slices))
        leafAxes = [position for position, axis in enumerate(axesSpec.axes)
                    if axis.origin == QVizAxis.LEAF]

        if not leafAxes:
            raise ValueError("Data node '" + treeNode.getName() +
                             "' has no explicit dependency on current X axis.")

        if len(leafAxes) == 1:
            values = tensor.values
            coordinate = tensor.axesValues[leafAxes[0]]
            if coordinate is None:
                coordinate = np.arange(values.shape[0])
            return np.array([coordinate]), np.array([values])

        return self._dataArrayHandle(treeNode, axesSpec, tensor, leafAxes,
                                     plotWidget, coordinate_index, time_index)

    def _dataArrayHandle(self, treeNode, axesSpec, tensor, leafAxes, plotWidget,
                         coordinate_index, time_index):
        """A two-dimension leaf, shaped for the image widgets.

        Numbers come from the tensor, words from the node: paths and labels are
        the node's own, so a plot configured before the switch keeps the legend
        and the axis label it had.
        """
        values = tensor.values
        coordinatesPaths = []
        coordinatesValues = []
        coordinatesLabels = []
        coordinateOfTime = None
        quantityName = ''
        label = ''

        for dim, position in enumerate(leafAxes, start=1):
            coordinatesPaths.append(treeNode.evaluateCoordinateAt(
                coordinateNumber=dim, itimeValue=time_index))
            coordinateValues = tensor.axesValues[position]
            axis = axesSpec.axes[position]
            if coordinateValues is None:
                # The dictionary names no node for this axis (1..N): the axis is
                # the element rank, as the current path makes it. A quantity that
                # holds nothing has no rank to take either, so the axis is empty
                # and the caller reports that on the path it asked for rather than
                # through an IndexError about a numpy shape.
                rank = values.shape[dim - 1] if dim - 1 < values.ndim else 0
                coordinateValues = np.arange(rank)
                self._sayIndexAxis(axesSpec, axis, rank,
                                   tensor.indexAxes.get(position))
            elif len(coordinateValues) == 0:
                raise ValueError("Coordinate array for dimension " + str(dim) +
                                 " has no values.")
            if axis.is_time:
                coordinateOfTime = dim
            coordinatesValues.append(coordinateValues)
            quantityName, label, coordinateLabel = treeNode.labels(
                plotWidget, dim, coordinate_index=coordinate_index,
                time_index=time_index)
            coordinatesLabels.append(coordinateLabel)

        arrayCoordinates = ArrayCoordinates(coordinatesPaths, coordinatesValues,
                                            coordinateOfTime, coordinatesLabels)
        return QVizDataArrayHandle(arrayCoordinates, np.asarray(values),
                                   label=label, name=quantityName,
                                   itimeValue=time_index)

    def _sayIndexAxis(self, axesSpec, axis, rank, elements):
        """Say out loud when the array a coordinate names is not the axis.

        An axis named by an array of structures is drawn as element ranks,
        because its values are those ranks. WEST 55799 declares one energy band
        and holds eight rows of radiance: the picture is right and the base it
        was written on is not, and a label cannot show both numbers -- so the
        shot's log panel is told the two counts to reconcile.
        """
        if elements is None or elements == rank:
            return
        logging.getLogger(getattr(self.dataSource, 'uri', None) or 'IMASViz').warning(
            "Coordinate '" + str(axis.coordinate) + "' names an array of "
            "structures of " + str(elements) + " element(s), where '" +
            axesSpec.dataPath + "' holds " + str(rank) + " along that axis: "
            "the axis is drawn as element ranks")

    def _fixLeafAxes(self, axesSpec, keptAxes, values, coordinate_index,
                     slices=None):
        """Take one element of the leaf's own axes, highest axis first.

        Taking from the last axis down keeps the earlier axes valid. The numpy
        axis is the position inside keptAxes, not the position inside the spec:
        an array of structures read at a fixed index occupies a slot in the
        spec and none in the values.
        """
        for valueAxis, position in reversed(list(enumerate(keptAxes))):
            axis = axesSpec.axes[position]
            if axis.origin != QVizAxis.LEAF:
                continue
            if valueAxis >= values.ndim:
                continue
            if values.shape[valueAxis] == 0:
                return np.asarray([])
            values = np.take(values, self._sliceIndex(axis, slices,
                                                      coordinate_index),
                             axis=valueAxis)
        return values
