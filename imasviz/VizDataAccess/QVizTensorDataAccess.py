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
from imasviz.VizDataAccess.QVizCurveAbscissa import TIME
from imasviz.VizDataAccess.QVizSlices import (QVizSlice, frameLabel, sliceLabel,
                                              slicesFor)
from imasviz.VizDataAccess.QVizTensorExtractor import QVizTensorExtractor
from imasviz.VizEntities.QVizDataArrayHandle import QVizDataArrayHandle, ArrayCoordinates


# How many pictures one image figure holds. Three is what stays readable next to
# a colour bar on one screen; the axis they are taken from is often longer, which
# is why the window moves rather than the count growing.
FRAMES = 3


class QVizTensorDataAccess:
    """The widgets' data access, reading a quantity whole instead of slice by slice.

    GetSignal answers either a (t, r) pair -- one row each, the way the plot code
    indexes them -- or a QVizDataArrayHandle for a two-dimension leaf. The curve,
    table and stacked frames consume the pair, the image frames the handle; which
    of the two a node gets follows from its axes, and a frame handed a shape it
    cannot read is a wrong routing, not a question for this access.

    What changes against the reader this one replaces is the number of reads. The
    other built one Python expression per time slice and evaluated it
    (getDataTimeSlices, then evalPath in the loop), and it decided what to build
    from the leaf's nominal dimension -- is0DAndDynamic, is1DAndDynamic,
    is2DAndDynamic -- which is why a quantity in three arrays of structures had
    no branch at all. Here the quantity is read once along all of its axes, and
    the slice a plot needs is one index into it: the rank stops being a case
    distinction.
    """

    def __init__(self, dataSource):
        self.dataSource = dataSource

    def GetSignal(self, treeNode, plotWidget=None, as_function_of_time=None,
                  coordinate_index=0, time_index=None, slices=None,
                  abscissa=None):
        """The quantity, read whole and reduced to what this plot draws.

        slices is {axis key: index}: the index to read each axis the plot does
        not draw at. It overrides the index the tree carries for an array of
        structures and the coordinate_index for a leaf axis, which is what a
        slice control is for. Left alone, the answer is the one the tree's own
        indices give.
        """
        axesSpec, timeAxis, alongTime, _ = \
            self.plan(treeNode, plotWidget, as_function_of_time, abscissa)
        extractor = QVizTensorExtractor(treeNode.getIDSRef())
        if time_index is None:
            time_index = int(treeNode.timeValue())
        if slices is None:
            # A plot frame that carries slice controls decides them; the axes
            # those controls offer are the ones this read fixes, because both
            # come out of plan(). A curve frame passes an explicit mapping
            # instead, because on a figure holding two elements of one array the
            # controls answer for whichever moved them last -- see
            # QVizCurvePlot._readSlices.
            controls = getattr(plotWidget, 'sliceControls', None)
            if controls is not None:
                slices = controls.indices()

        if alongTime:
            return self._curveAlongTime(treeNode, axesSpec, extractor, timeAxis,
                                        coordinate_index, slices)
        return self._sliceAtTime(treeNode, axesSpec, extractor, plotWidget,
                                 coordinate_index, time_index, slices)

    def plan(self, treeNode, plotWidget=None, as_function_of_time=None,
             abscissa=None):
        """What this plot draws, and therefore which axes must be fixed.

        One place decides it, because the read, the slice controls and the axis
        labels all have to agree: a control for an axis the plot already draws,
        no control for an axis the read silently fixes, or a label naming a
        different axis than the one the numbers came off, all look right until
        the numbers move under the user.

        `abscissa` is the axis a **curve figure** has already settled on, as
        `QVizCurveAbscissa` spells its identity. When a figure has one, the read
        follows it: a curve added to a figure that runs along time is read along
        time, whatever the quantity's own default would have been. Measured
        before that: a figure opened on `equilibrium.time_slice[i].profiles_1d.f`
        drew 101 points against `psi`, and adding `.psi` to it drew 101 points
        against the index and rewrote the figure's one bottom label from `psi` to
        `dimension 1`.

        Left out, the question falls back on the node -- which is what the table
        and stacked windows still ask, through the `plotAxis` spelling their
        menus document (`New (default axis)` / `New ('TIME' axis)`).
        """
        axesSpec = QVizAxesSpec.fromTreeNode(treeNode)
        timeAxis = self._timeAxis(axesSpec)
        if abscissa is not None:
            # The clock, walked by walking the dynamic array. A quantity whose
            # own coordinate *is* a time base has no dynamic array to walk --
            # `magnetics.flux_loop[i].flux.data` on the reference case -- and it
            # is sliced at one element while still running along the clock.
            alongTime = abscissa == TIME and timeAxis is not None
        else:
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
                  coordinate_index=0, frames=None, abscissa=None):
        """The axes this plot does not draw, ready for a control.

        A leaf axis length comes from the values themselves: the dictionary
        often names no node for it (the 1..N spelling), so the only length that
        means anything is the length of what was read.

        frames is the position of the axis the figure reads across its images;
        it is on screen, so it gets no control. See framesFor.
        """
        axesSpec, timeAxis, alongTime, plotted = \
            self.plan(treeNode, plotWidget, as_function_of_time, abscissa)
        lengths = self._readLengths(treeNode, axesSpec, timeAxis)
        return slicesFor(axesSpec, plotted, lengths, frames=frames)

    def _readLengths(self, treeNode, axesSpec, timeAxis):
        """How long each axis of the quantity is, as far as anything knows.

        From the values when they were read, from the tree when the axis is an
        array of structures: the dictionary states those lengths and the shot
        need not be opened to ask.
        """
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
        return lengths

    def framesFor(self, treeNode, plotWidget=None, as_function_of_time=False):
        """The axis a figure reads across its images, or None when nothing to spread.

        An image draws two axes and pins the rest with a control each. One pinned
        axis is better read between the pictures than under a slider: three
        elements of the dynamic array side by side are the only way to compare
        time slices, and a leaf with more axes than a picture draws has to put
        one of them somewhere the user can see it.

        The dynamic array wins when the quantity has one -- a picture never runs
        along time, so that axis is already outside the picture. Otherwise it is
        an axis the figure would otherwise pin: one of the leaf's own when there
        are more than two to draw, else the outermost of the pinned ones.
        """
        axesSpec, timeAxis, _, plotted = \
            self.plan(treeNode, plotWidget, as_function_of_time)
        position = self._framesPosition(axesSpec, timeAxis, plotted)
        if position is None:
            return None
        axis = axesSpec.axes[position]
        # An array of structures carries its length on the tree, and that is the
        # length the read validates a slice index against -- so answering it needs
        # no shot open. Only an axis the dictionary leaves unbounded has to be
        # measured on the values, and measuring it means leaving it open: reading
        # a whole axis to answer a question the tree already answers would be paid
        # once per selected node, on the way to deciding where to draw it.
        length = axis.length
        if length is None:
            length = self._readLengths(treeNode, axesSpec,
                                       timeAxis).get(axis.key())
        return QVizSlice(axis, length=length,
                         index=axis.index if axis.index is not None else 0,
                         position=position)

    def GetFrames(self, treeNode, plotWidget=None, start=0, count=FRAMES,
                  as_function_of_time=False):
        """The pictures of one figure: the same quantity at successive elements.

        Answers [(handle, index, label), ...], one per image. Each element is
        read on its own, which is cheaper than it looks: the extractor indexes
        the array of structures before descending into it, so a window of three
        reads three elements and not the whole axis.

        The indices of the axes the figure pins come from its controls, so the
        pictures differ only by the axis they are spread over.
        """
        axesSpec, timeAxis, _, plotted = \
            self.plan(treeNode, plotWidget, as_function_of_time)
        position = self._framesPosition(axesSpec, timeAxis, plotted)
        if position is None:
            raise ValueError('Nothing to spread over images: nothing around "' +
                             self._pathOf(treeNode) + '" is pinned.')
        axis = axesSpec.axes[position]

        slices = {}
        controls = getattr(plotWidget, 'sliceControls', None)
        if controls is not None:
            slices.update(controls.indices())

        values = None
        if timeAxis is not None and axis is timeAxis:
            values = QVizTensorExtractor(treeNode.getIDSRef()).timeBase(axesSpec)

        frames = []
        for index in range(int(start), int(start) + int(count)):
            slices[axis.key()] = index
            frames.append((self.GetSignal(treeNode=treeNode, plotWidget=None,
                                          as_function_of_time=False, slices=slices),
                           index, frameLabel(axis, index, values)))
        return frames

    def _framesPosition(self, axesSpec, timeAxis, plotted):
        if timeAxis is not None:
            return axesSpec.axes.index(timeAxis)
        if len(plotted) > 2:
            return plotted[0]
        pinned = [position for position in range(len(axesSpec.axes))
                  if position not in plotted]
        return pinned[0] if pinned else None

    def _pathOf(self, treeNode):
        path = treeNode.getParametrizedDataPath()
        return path if path else treeNode.getName()

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
            return self._scalarVsPlottedAxis(treeNode, plotWidget,
                                             tensor.values)

        # A leaf axis can be the axis a figure reads across its images: the
        # pictures then differ by one element of that coordinate, which has to
        # come out of the values before anything is labelled.
        leafAxes, values = self._reducePinnedLeafAxes(axesSpec, leafAxes,
                                                      tensor.values, slices)

        if len(leafAxes) == 1:
            coordinate = tensor.axesValues[leafAxes[0]]
            if coordinate is None:
                coordinate = np.arange(values.shape[0])
            return np.array([coordinate]), np.array([values])

        return self._dataArrayHandle(treeNode, axesSpec, tensor, leafAxes, values,
                                     plotWidget, coordinate_index, time_index)

    def _reducePinnedLeafAxes(self, axesSpec, leafAxes, values, slices):
        """Take out the leaf axes the plot fixes, and the axes they leave.

        Highest position first, so the axes below it keep the place they had. The
        axes left over are the value axes of the answer in order, which is what
        the image labels walk -- keeping the removed one in that list would put
        the second coordinate's name under the first axis of the picture.
        """
        kept = list(leafAxes)
        for position in reversed(leafAxes):
            axis = axesSpec.axes[position]
            if slices is None or axis.key() not in slices:
                continue
            valueAxis = kept.index(position)
            if valueAxis >= values.ndim:
                continue
            values = np.take(values,
                             self._sliceIndex(axis, slices, axis.index),
                             axis=valueAxis)
            kept.remove(position)
        return kept, values

    def _scalarVsPlottedAxis(self, treeNode, plotWidget, values):
        """One scalar, drawn at every point of the axis another quantity opened.

        A scalar held by a static array has no axis of its own, so a figure that
        shows it borrows the abscissa of whatever is already drawn -- which is
        what the table and the stacked figure have always done, and what this read
        refused until now. A flat line reads as a quantity that does not vary, so
        the shot's log panel is told the line is one value.
        """
        axisValues = plottedXValues(plotWidget)
        if axisValues is None or len(axisValues) == 0:
            raise ValueError("Data node '" + treeNode.getName() +
                             "' has no explicit dependency on current X axis.")

        scalar = np.asarray(values).reshape(-1)
        if scalar.size != 1:
            raise ValueError('Nothing to plot for "' + treeNode.getName() +
                             '": the quantity holds ' + str(scalar.size) +
                             ' values where one was expected.')

        self._uriLogger().warning(
            "Data node '" + treeNode.getName() + "' has no explicit dependency "
            "on coordinate1 dimension: its value is repeated along the plotted "
            "axis")
        return np.array([np.asarray(axisValues, dtype=float)]), \
               np.full((1, len(axisValues)), float(scalar[0]))

    def _uriLogger(self):
        """The log panel of the shot view this read came from."""
        return logging.getLogger(getattr(self.dataSource, 'uri', None) or 'IMASViz')

    def _dataArrayHandle(self, treeNode, axesSpec, tensor, leafAxes, values,
                         plotWidget, coordinate_index, time_index):
        """A two-dimension leaf, shaped for the image widgets.

        Numbers come from the tensor, words from the node: paths and labels are
        the node's own, so a plot configured before the switch keeps the legend
        and the axis label it had.
        """
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
        self._uriLogger().warning(
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


def plottedXValues(plotWidget):
    """The abscissa a figure already holds, taken from the plot showing it.

    A single-plot frame keeps one plot item; a table or a stacked figure keeps
    several and says which one is current. Both are asked through their own
    accessor instead of by widget type, which is how the current path decided it:
    a frame gains the scalar without having to be named here, and a frame that
    carries no plot at all answers None instead of raising.
    """
    if plotWidget is None:
        return None

    current = getattr(plotWidget, 'getCurrentPlotItem', None)
    if current is not None:
        plotItem = current()
    else:
        plotItem = getattr(getattr(plotWidget, 'pgPlotWidget', None), 'plotItem',
                           None)
    if plotItem is None:
        return None

    dataItems = getattr(plotItem, 'dataItems', None)
    if not dataItems:
        return None
    return dataItems[0].xData
