# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import numpy as np

from imasviz.VizDataAccess.QVizAxesSpec import QVizAxesSpec, QVizAxis
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
                  coordinate_index=0, time_index=None):
        if as_function_of_time is None:
            as_function_of_time = \
                treeNode.isPlotToPerformAlongTimeAxis(plotWidget=plotWidget)
        if time_index is None:
            time_index = int(treeNode.timeValue())
        if plotWidget is not None and plotWidget.addTimeSlider:
            if plotWidget.sliderGroup is not None:
                time_index = plotWidget.sliderGroup.slider.value()
        if plotWidget is not None and plotWidget.addCoordinateSlider:
            if plotWidget.sliderGroup is not None:
                coordinate_index = plotWidget.sliderGroup.slider.value()

        axesSpec = QVizAxesSpec.fromTreeNode(treeNode)
        extractor = QVizTensorExtractor(treeNode.getIDSRef())
        timeAxis = self._timeAxis(axesSpec)

        if as_function_of_time and timeAxis is not None:
            return self._curveAlongTime(treeNode, axesSpec, extractor, timeAxis,
                                        coordinate_index)
        return self._sliceAtTime(treeNode, axesSpec, extractor, plotWidget,
                                 coordinate_index, time_index)

    def _timeAxis(self, axesSpec):
        """The array of structures carrying the time index, if there is one."""
        for axis in axesSpec.axes:
            if axis.is_time and axis.origin == QVizAxis.AOS:
                return axis
        return None

    def _fixedIndices(self, axesSpec, timeIndex=None, timeAxis=None):
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
                if timeIndex is not None:
                    indices[axis.level] = timeIndex
                continue
            indices[axis.level] = axis.index if axis.index is not None else 0
        return indices

    def _curveAlongTime(self, treeNode, axesSpec, extractor, timeAxis,
                        coordinate_index):
        """The quantity read along the dynamic array, one point per time slice.

        The leaf's own axes are read at coordinate_index, which is what the
        current path does by appending [coordinate_index] to each slice path.
        """
        aosIndices = self._fixedIndices(axesSpec, timeIndex=None, timeAxis=timeAxis)
        tensor = extractor.extract(axesSpec, aosIndices)
        values = self._fixLeafAxes(axesSpec, self._keptAxes(axesSpec, aosIndices),
                                   tensor.values, coordinate_index)
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
                     coordinate_index, time_index):
        """One slice of the quantity, taken at the index the plot is on.

        Every array of structures is read at the index the tree carries (the
        dynamic one at time_index), so what is left is the leaf's own dimension
        or dimensions -- which is also why the leaf axes below are the value
        axes in order.
        """
        timeAxis = self._timeAxis(axesSpec)
        tensor = extractor.extract(axesSpec,
                                   self._fixedIndices(axesSpec, timeIndex=time_index,
                                                      timeAxis=timeAxis))
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
                # the element rank, as the current path makes it.
                coordinateValues = np.arange(values.shape[dim - 1])
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

    def _fixLeafAxes(self, axesSpec, keptAxes, values, coordinate_index):
        """Take one element of the leaf's own axes, highest axis first.

        Taking from the last axis down keeps the earlier axes valid. The numpy
        axis is the position inside keptAxes, not the position inside the spec:
        an array of structures read at a fixed index occupies a slot in the
        spec and none in the values.
        """
        for valueAxis, position in reversed(list(enumerate(keptAxes))):
            if axesSpec.axes[position].origin != QVizAxis.LEAF:
                continue
            if valueAxis >= values.ndim:
                continue
            if values.shape[valueAxis] == 0:
                return np.asarray([])
            values = np.take(values, coordinate_index, axis=valueAxis)
        return values
