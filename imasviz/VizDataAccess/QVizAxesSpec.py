# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
import re

from imasviz.VizUtils import QVizGlobalValues

# The data dictionary spells an unbounded coordinate 1..N; the shadow tree
# rewrites every dot in a coordinate as a slash, so it reaches the view as
# 1///N. Neither one names a node in the dictionary: they describe an axis of
# ranks only.
UNBOUNDED_COORDINATE = re.compile(r'^1[./]+[NM]$')

PLACEHOLDER = re.compile(r'\[([a-z]+)\]')

# An array of structures in a parametrized path, with the name of the array in
# front of its loop placeholder: 'ion[j]', 'time_slice[itime]'. The name is what
# a control labels that axis with -- a user knows 'ion', not 'level 2'.
AOS_STEP = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)\[([a-z]+)\]')


def isTimeSpelling(coordinate):
    """Whether a coordinate spelling names a time base.

    The dictionary spells it three ways depending on where the coordinate sits:
    bare 'time' at IDS level, '<aos>.time' in dotted form and '<aos>/time' in
    the slashed form the view also builds. QVizTreeNode.applyCoordinate tests
    the same three endings.
    """
    if not coordinate:
        return False
    return coordinate == 'time' or coordinate.endswith('.time') \
        or coordinate.endswith('/time')


def leafRank(element):
    """Number of dimensions a leaf would have to be plotted along.

    Not the data dictionary rank: an array of structures contributes one
    dimension each, so a 0D value inside a dynamic AoS is a curve over time and
    must not be treated as a scalar. buildLeaf records the enclosing count, the
    leaf type records its own.

    Only a real data leaf carries that count: buildLeaf also appends a
    synthetic STR_0D 'name' child for the label, which would otherwise be
    counted as a rank 0 quantity -- on equilibrium alone that is 3 518 ghosts.
    """
    enclosing = element.get('aos_parents_count')
    if enclosing is None:
        return None
    ndim = leafDataDimension(element.get('data_type'))
    if ndim is None:
        return None
    return int(enclosing) + ndim


def leafDataDimension(dataType):
    """ndim out of the data dictionary spelling, None for a non leaf type."""
    if not dataType or dataType in ('structure', 'struct_array'):
        return None
    tail = dataType.split('_')[-1]
    if tail.endswith('D') and tail[:-1].isdigit():
        return int(tail[:-1])
    return None


class QVizAxis:
    """One dimension of a quantity.

    Either a dimension contributed by an enclosing array of structures (AOS),
    whose extent is the length of that array and whose coordinate is often
    nothing but a rank, or one of the leaf's own coordinates, named by the
    dictionary.
    """

    AOS = 'AOS'
    LEAF = 'LEAF'

    def __init__(self, origin, level, placeholder=None, coordinate=None,
                 units=None, length=None, is_time=False, index=None,
                 same_as=None, name=None, idsName=None):
        self.origin = origin
        # 1-based position among the enclosing arrays of structures for an AOS
        # axis, among the leaf coordinates for the other kind.
        self.level = level
        self.placeholder = placeholder
        # The array's own name for an AOS axis ('ion' in '...ion[j]...'), which
        # is how a control should name the axis it lets the user move.
        self.name = name
        self.idsName = idsName
        self.coordinate = coordinate
        self.units = units
        self.length = length
        self.is_time = is_time
        self.index = index
        self.same_as = same_as

    def key(self):
        """A stable handle on this axis, to carry a control's value back to it.

        Named by the IDS and by the array or coordinate, never by the nesting
        level alone: one figure holds curves from several quantities, and two of
        them can sit in different arrays at the same level. A control keyed by
        the level moves one and is then read back for the other, which shows up
        as a curve changing that the user never touched. The level stays what
        the read indexes by -- it is the identity of the axis that changes.

        The coordinate is spelled with a slash by the shadow tree and with a dot
        by the tree node, so it is normalised here: the same axis read either way
        has to be the same control.
        """
        if self.origin == QVizAxis.AOS:
            return (self.origin, self.idsName, self.name or self.placeholder
                    or self.level)
        if self.coordinate:
            return (self.origin, self.idsName, self.coordinate.replace('/', '.'))
        return (self.origin, self.idsName, 'dimension %d' % self.level)

    def isUnbounded(self):
        """True when the dictionary names no node for this axis."""
        return self.origin == QVizAxis.LEAF and self.coordinate is None

    def __repr__(self):
        return '<QVizAxis %s %d %s%s>' % (
            self.origin, self.level, self.coordinate or '-',
            ' time' if self.is_time else '')


class QVizAxesSpec:
    """The axes of one leaf, read off the shadow tree.

    Everything needed is already there: aos_parents_count and the loop
    placeholders in parametrizedPath give the arrays of structures, coordinateN
    (with _units and _same_as) give the leaf's own, and itime_index says which
    array of structures carries the time index. So this is a read of the tree,
    not a second walk of the dictionary: no case has to be open to know that
    calorimetry.group[i].component[j].power.data is a rank 3 quantity.
    """

    def __init__(self, axes, idsName=None, dataPath=None, dataType=None,
                 units=None):
        self.axes = axes
        self.idsName = idsName
        self.dataPath = dataPath
        self.dataType = dataType
        self.units = units

    @staticmethod
    def fromShadowElement(element, idsName=None):
        timeLevel = int(element.get('itime_index', -1)) + 1
        parametrizedPath = element.get('parametrizedPath') or ''
        axes = []

        for position, (arrayName, variable) in enumerate(AOS_STEP.findall(parametrizedPath),
                                                         start=1):
            # The walk builds pathText outermost array first, so the order the
            # placeholders appear in is their nesting level. Reading the level
            # off the loop letter instead would tie this to
            # QVizGlobalValues.indices, which stops at seven levels and would
            # then mis-key the extent attributes.
            level = timeLevel if variable == 'itime' else position
            axes.append(QVizAxis(
                origin=QVizAxis.AOS,
                level=level,
                placeholder=variable,
                name=arrayName,
                # An array of structures carries no coordinate of its own; when
                # it is the dynamic one, the time base of the whole IDS is what
                # indexes it -- which is how QVizTreeNode already resolves it.
                coordinate=(idsName + '.time' if level == timeLevel else None),
                units='s' if level == timeLevel else None,
                length=_intOrNone(element.get(QVizGlobalValues.max_indices[str(level)])),
                is_time=(level == timeLevel),
                index=_intOrNone(element.get(QVizGlobalValues.indices[str(level)])),
                idsName=idsName))

        for dimension in range(leafDataDimension(element.get('data_type')) or 0):
            number = str(dimension + 1)
            coordinate = element.get('coordinate' + number)
            if coordinate is not None and UNBOUNDED_COORDINATE.match(coordinate):
                coordinate = None
            axes.append(QVizAxis(
                origin=QVizAxis.LEAF,
                level=dimension + 1,
                coordinate=coordinate,
                units=element.get('coordinate' + number + '_units'),
                same_as=element.get('coordinate' + number + '_same_as'),
                is_time=isTimeSpelling(coordinate),
                idsName=idsName))

        return QVizAxesSpec(axes, idsName=idsName,
                            dataPath=element.text,
                            dataType=element.get('data_type'),
                            units=element.get('units'))

    @staticmethod
    def fromTreeNode(node):
        """The same axes, read off the QVizTreeNode the widgets hold.

        A data access is handed a tree node, never a shadow tree element, and
        the builder copied onto the node exactly what the axes need: the
        parametrized path, the time index, the current index and the length of
        every enclosing array of structures, the coordinates and their units.

        Reading from the node is also the only reading that sees what the user
        did. An array index picked in the tree or a coordinate changed from the
        right-click menu lives on the node and nowhere else, so a plot built
        from the dictionary's spelling would ignore the choice the user just
        made.

        The coordinate spelling differs from the shadow tree by one separator:
        buildNamedDataElement rewrites every '/' as a '.'. The model accepts
        both (isTimeSpelling, UNBOUNDED_COORDINATE and coordinateSegments all
        do), so the two readings are compared after normalising the separator
        rather than by rewriting one of them here.
        """
        parametrizedPath = node.getParametrizedPath() or ''
        timeLevel = node.getItimeIndex() + 1
        axes = []

        for position, (arrayName, variable) in enumerate(AOS_STEP.findall(parametrizedPath),
                                                         start=1):
            level = timeLevel if variable == 'itime' else position
            # The node keys the index and the length of an array by its loop
            # letter, and the dynamic level carries a letter too -- it is the
            # parametrized path that renames that one to 'itime'.
            letter = QVizGlobalValues.indices.get(str(level))
            axes.append(QVizAxis(
                origin=QVizAxis.AOS,
                level=level,
                placeholder=variable,
                name=arrayName,
                coordinate=(node.getIDSName() + '.time' if level == timeLevel else None),
                units='s' if level == timeLevel else None,
                length=_intOrNone(node.parameters_max_values.get(letter)),
                is_time=(level == timeLevel),
                index=_intOrNone(node.parameters_values.get(letter)),
                idsName=node.getIDSName()))

        for dimension in range(leafDataDimension(node.getDataType()) or 0):
            coordinate = (node.coordinates[dimension]
                          if dimension < len(node.coordinates) else None)
            if coordinate is not None and UNBOUNDED_COORDINATE.match(coordinate):
                coordinate = None
            number = str(dimension + 1)
            axes.append(QVizAxis(
                origin=QVizAxis.LEAF,
                level=dimension + 1,
                coordinate=coordinate,
                units=node.getCoordinateUnits(dimension + 1),
                same_as=node.getInfoDict().get('coordinate' + number + '_same_as'),
                is_time=isTimeSpelling(coordinate),
                idsName=node.getIDSName()))

        return QVizAxesSpec(axes, idsName=node.getIDSName(),
                            dataPath=node.getParametrizedDataPath(),
                            dataType=node.getDataType(),
                            units=node.getUnits())

    @property
    def rank(self):
        return len(self.axes)

    def timeAxes(self):
        return [axis for axis in self.axes if axis.is_time]

    def aosAxes(self):
        return [axis for axis in self.axes if axis.origin == QVizAxis.AOS]

    def aosCount(self):
        """How many arrays of structures enclose the leaf."""
        return len(self.aosAxes())

    def leafAxes(self):
        return [axis for axis in self.axes if axis.origin == QVizAxis.LEAF]

    def isPlottable(self):
        """A rank 0 quantity has nothing to draw: it is a single value."""
        return self.rank > 0

    def __repr__(self):
        return '<QVizAxesSpec rank=%d %s>' % (self.rank, self.dataPath)


def _intOrNone(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
