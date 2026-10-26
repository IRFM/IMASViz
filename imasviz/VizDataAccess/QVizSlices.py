# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Which axes of a quantity the plot does not draw, and at which index.

A curve draws one axis and an image two. Every other axis of the quantity has
to be fixed somewhere to produce those numbers -- and a number fixed silently,
at whatever the tree happens to carry, is a plot of one unnamed slice. Each
fixed axis therefore becomes a slice the user can move: an index, a length, and
a name to put on the control.

This is a new module, written against the axes model rather than the slider the
legacy plot frames carried. That one was built when the figure was created --
before any quantity was known -- offered one slider, either time or coordinate1,
and drove the read by the caller reading `slider.value()` out of band. Neither
its count nor its wiring could describe a quantity with more than two axes, so
nothing here is derived from it. The slider itself is gone with the frames that
carried it; the controls this model produces are what the frames answer with.
"""


class QVizSlice:
    """One axis the plot does not draw inside a picture.

    key identifies the axis in the spec, so a control's value can be read back
    as the index of that axis; label names it the way the tree names it (an
    array of structures by its own name, a leaf axis by its coordinate);
    position is its place in the spec, which is what tells a figure which of its
    two axes is *not* this one.
    """

    def __init__(self, axis, length=None, index=0, position=None):
        self.axis = axis
        self.key = axis.key()
        self.label = sliceLabel(axis)
        self.length = length
        self.index = index
        self.position = position

    def __repr__(self):
        return '<QVizSlice %s length=%s index=%s>' % (self.key, self.length,
                                                      self.index)


def sliceLabel(axis):
    """What a user would call this axis.

    An array of structures is named by the array itself -- 'ion', not 'level 2'
    -- because that is the name the tree shows and the name the path is written
    with. A leaf axis is named by its coordinate when the dictionary gives one;
    when it does not (the 1..N spelling), by its rank position, which is the
    only thing the dictionary says about it.
    """
    if axis.origin == axis.AOS:
        return axis.name or axis.placeholder or ('level %d' % axis.level)
    if axis.coordinate:
        return axis.coordinate.rsplit('.', 1)[-1].rsplit('/', 1)[-1]
    return 'dimension %d' % axis.level


def elementLabel(node, axes=(), indices=None):
    """Which element of which array one drawn trace came from, spelled out.

    The parametrized path names the arrays with their loop letters
    ('flux_loop[i]'), which says a trace came from *some* element of flux_loop
    and not which. Two curves of one array in one figure therefore carry the same
    label -- and once the array stops being a control the user reads, nothing on
    the figure says where its numbers came from at all.

    `axes` are the axes the trace fixes, never the one it draws: substituting the
    array a curve runs along would label a whole time axis with one index.
    `indices` is where a tensor exploration's sliders stand; left out, the
    indices the tree carries are used, which is the element the node is.
    """
    path = node.getParametrizedDataPath()
    if not path:
        return node.getName()
    indices = indices or {}
    for axis in axes:
        if axis.origin != axis.AOS or not axis.placeholder:
            continue
        index = indices.get(axis.key(), axis.index)
        if index is None:
            continue
        path = path.replace('[' + axis.placeholder + ']', '[%d]' % int(index))
    return path


def slicesFor(axesSpec, plottedPositions=(), lengths=None, frames=None):
    """One slice per axis the plot leaves out, in the order the spec lists them.

    lengths comes from the values just read: the dictionary does not always know
    how long a leaf axis is (an unbounded 1..N coordinate), and the length the
    control needs is the length of what was actually read.

    frames is the axis the figure reads across its images rather than pinning. It
    is drawn -- three pictures are its three elements -- so it needs no control,
    and a slider for it would ask the user for something already on screen.
    """
    lengths = lengths or {}
    drawn = set(plottedPositions)
    if frames is not None:
        drawn.add(frames)
    slices = []
    for position, axis in enumerate(axesSpec.axes):
        if position in drawn:
            continue
        slices.append(QVizSlice(axis,
                                length=lengths.get(axis.key(), axis.length),
                                index=axis.index if axis.index is not None else 0,
                                position=position))
    return slices


def frameLabel(axis, index, values=None):
    """Which element of the axis one of the images stands for.

    The element number always, because that is what the read indexed. The value
    the axis carries at that element when it carries values, because a slice
    number is not a time: three pictures whose titles say when they were taken
    can be read in order, and three that say only 0, 1, 2 cannot.
    """
    label = '%s %d' % (sliceLabel(axis), index)
    if values is not None and 0 <= index < len(values):
        spelled = '%g' % float(values[index])
        if axis.units:
            spelled += ' ' + axis.units
        label += ' (%s)' % (('t = ' + spelled) if axis.is_time else spelled)
    return label
