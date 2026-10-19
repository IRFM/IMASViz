# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""What can be drawn of one quantity, and whether it is worth offering.

The menus used to ask the data dictionary how big a leaf is -- is0D, is1D, is2D,
is2DOrLarger -- and offered one command per answer. A quantity whose axes come
from the arrays that hold it (a two-dimension leaf inside three arrays of
structures, say) then answered "nothing to do here": no entry to select it, no
entry to draw it, even though the read walks those axes and draws it as a stack
of pictures. A leaf ranked 3 in the dictionary got nothing at all, and a static
one got an empty menu, because is2DOrLarger() only counts a quantity as large
when it is also dynamic -- and returns nothing at all when it is not.

The axes the read would walk answer the same questions, and they are known
without opening the shot: QVizAxesSpec.fromTreeNode. This is that read, turned
into the questions the interface asks. How many of those axes end up on screen is
a different question, because it depends on the axis a figure reads across its
pictures: plottedAxes() asks the read, and only the command that draws pays for
it -- a right click must not extract a tensor to decide what to offer.
"""

from imasviz.VizDataAccess.QVizAxesSpec import QVizAxesSpec, leafDataDimension
from imasviz.VizDataAccess.QVizTensorDataAccess import QVizTensorDataAccess


class QVizNodePlotting:
    """The questions the menus ask about one node, answered from its axes."""

    def __init__(self, treeNode):
        self.treeNode = treeNode
        self._axes = None

    @property
    def axes(self):
        if self._axes is None:
            self._axes = QVizAxesSpec.fromTreeNode(self.treeNode)
        return self._axes

    def rank(self):
        """How many axes the quantity has, enclosing arrays of structures included."""
        return self.axes.rank

    def isDataLeaf(self):
        """A node holding values, as opposed to a structure or an array of them."""
        dataType = self.treeNode.getDataType()
        return dataType is not None and dataType not in ('structure', 'struct_array')

    def isStringLeaf(self):
        """A leaf of text: nothing to draw, however many axes it has."""
        dataType = str(self.treeNode.getDataType() or '')
        return dataType.startswith('STR')

    def hasTimeAxis(self):
        """Whether one of the axes is a time base, spelled by an array or by a coordinate."""
        return bool(self.axes.timeAxes())

    def inArrayOfStructures(self):
        """Whether the quantity is held by an array of structures, at any depth.

        What "Select all the signals from the same array" is offered for. The
        dictionary counted the arrays on the leaf, so a scalar held by one was
        left out of the family it belongs to.
        """
        return self.isDataLeaf() and self.axes.aosCount() > 0

    def hasOwnCoordinate(self):
        """Whether the leaf has an axis of its own to set a coordinate on.

        Asked of the leaf's shape, not of the coordinate currently recorded: the
        user can put 1..N there, and a menu that answers "nothing to set" once
        they have is a menu that cannot be undone.
        """
        return bool(self.axes.leafAxes())

    def isPlottable(self):
        """Whether drawing this quantity means anything at all.

        A leaf of text does not plot. Neither does a scalar with nothing around
        it: it has no axis to draw along, which is why the read refuses it rather
        than drawing a line whose abscissa belongs to another quantity.
        """
        if not self.isDataLeaf() or self.isStringLeaf():
            return False
        return bool(self.axes.leafAxes()) or self.hasTimeAxis()

    def curveAxisKey(self):
        """Names the abscissa a curve of this quantity would run along.

        A curve figure has one bottom label, and what it says is the axis of the
        last curve read -- so a quantity read along another abscissa must not be
        added to a figure that already holds curves. Two leaf axes is a picture
        and not a curve: the curve frame draws one and would die unpacking a
        data-array handle. Nothing around the quantity but a time base is the
        history case, whose abscissa is time.

        Asked of the axes alone, because the menu that lists the open figures
        must not pay for a read: plottedAxes() below measures lengths on the
        values, this does not.
        """
        own = self.axes.leafAxes()
        if len(own) > 1:
            return None
        if own:
            return own[0].key()
        if self.hasTimeAxis():
            return 'time'
        return None

    def plottedAxes(self):
        """How many axes a picture of this quantity would show.

        Asked with the time axis pinned, which is the image's rule: asked with
        time left open, every quantity in a dynamic array would answer one axis
        -- time -- and be called a curve. One axis leaves the picture for the
        axis the figure reads across its images, which is displayed, not pinned,
        so it counts as drawn and gets no control.

        This reads, so the menus do not ask it: it is the command's decision,
        made once per quantity actually drawn.
        """
        access = QVizTensorDataAccess(self.treeNode.getDataSource())
        plotted = access.plan(self.treeNode, plotWidget=None,
                              as_function_of_time=False)[3]
        frames = access.framesFor(self.treeNode, plotWidget=None,
                                  as_function_of_time=False)
        drawn = [position for position in plotted
                 if frames is None or position != frames.position]
        if len(drawn) > 2:
            raise ValueError('"' + self.path() + '" has ' + str(len(drawn)) +
                             ' axes to draw: no frame shows more than two in '
                             'one picture, and the axis read between pictures '
                             'is taken.')
        return len(drawn)

    def path(self):
        path = self.treeNode.getParametrizedDataPath()
        return path if path else self.treeNode.getName()

    # What the legacy frames can still be asked to draw. Their limit is the shape
    # of the leaf, not the quantity: a curve figure holds one slider group for
    # everything else, so it only ever drew a one-dimension leaf, and the image
    # frame only a two-dimension one.

    def legacyCanDrawAsCurve(self):
        return (self.isPlottable() and
                leafDataDimension(self.treeNode.getDataType()) == 1)

    def legacyCanDrawAsImage(self):
        return (self.isPlottable() and
                leafDataDimension(self.treeNode.getDataType()) == 2)
