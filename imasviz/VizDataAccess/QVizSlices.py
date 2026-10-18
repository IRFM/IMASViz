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
plot frames carry today. That one (sliderGroup in QVizPlotWidget) is built when
the figure is created -- before any quantity is known -- offers one slider,
either time or coordinate1, and drives the read by the caller reading
slider.value() out of band. Neither the count nor the wiring can describe a
quantity with more than two axes, so nothing here is derived from it.
"""


class QVizSlice:
    """One axis the plot fixes, with what a control needs to show it.

    key identifies the axis in the spec, so a control's value can be read back
    as the index of that axis; label names it the way the tree names it (an
    array of structures by its own name, a leaf axis by its coordinate).
    """

    def __init__(self, axis, length=None, index=0):
        self.axis = axis
        self.key = axis.key()
        self.label = sliceLabel(axis)
        self.length = length
        self.index = index

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


def slicesFor(axesSpec, plottedPositions=(), lengths=None):
    """One slice per axis the plot leaves out, in the order the spec lists them.

    lengths comes from the values just read: the dictionary does not always know
    how long a leaf axis is (an unbounded 1..N coordinate), and the length the
    control needs is the length of what was actually read.
    """
    lengths = lengths or {}
    slices = []
    for position, axis in enumerate(axesSpec.axes):
        if position in plottedPositions:
            continue
        slices.append(QVizSlice(axis,
                                length=lengths.get(axis.key(), axis.length),
                                index=axis.index if axis.index is not None else 0))
    return slices
