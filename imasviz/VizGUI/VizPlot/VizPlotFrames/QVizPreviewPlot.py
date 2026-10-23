# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The thumbnail the shot view shows for the node under the click.

The panel used to subclass the legacy curve window, so it carried the slider
machinery a figure needs and none of the reasons a thumbnail gives: the gesture
asked the data dictionary how big the leaf was (isDynamicData() or is1D()) and
only called the panel when the answer was one it recognised, the command
answered a text node by returning without clearing what was already drawn, and
a quantity whose leaf ranked 3 in the dictionary was told 'No preview available'
although the read walks its axes. A click on anything the branch did not
recognise therefore left the previous node's curve on screen, labelled with the
previous node's name: a panel that answers a question nobody asked.

This panel answers for every node it is handed. The axes the read would walk say
what can be shown -- one axis becomes a curve, two become a picture, a number
with only a time base around it becomes its history -- and when nothing can be
shown the panel says which of those is the case instead of keeping what was
there. It reads one slice, through the same access the figures use, and hands
that read no plot widget of its own: it has no control to be read through.
"""

import numpy as np
import pyqtgraph as pg

from PySide6.QtWidgets import QLabel, QStackedWidget, QVBoxLayout, QWidget

from imasviz.VizDataAccess.QVizNodePlotting import QVizNodePlotting
from imasviz.VizDataAccess.QVizSlices import sliceLabel
from imasviz.VizDataAccess.QVizTensorDataAccess import QVizTensorDataAccess
from imasviz.VizEntities.QVizDataArrayHandle import QVizDataArrayHandle

CURVE, PICTURE, NOTHING = 'curve', 'picture', 'nothing'


class QVizPreviewPlot(QWidget):
    """One quantity, drawn small, saying what it stands for."""

    def __init__(self, parent=None, title=''):
        super(QVizPreviewPlot, self).__init__(parent)
        # The gesture finds the panel by this name, as the shot view docks it.
        self.setObjectName(type(self).__name__)
        if title:
            self.setWindowTitle(title)

        self._kind = NOTHING
        self._reason = 'Nothing has been clicked yet.'
        self._sliceText = ''

        self.curvePlot = pg.PlotWidget(self)
        self.curvePlot.setObjectName('previewCurve')
        self.curvePlot.showGrid(x=True, y=True)

        self.imagePlot = pg.GraphicsLayoutWidget(self)
        self.imagePlot.setObjectName('previewImage')
        self.imagePanel = self.imagePlot.addPlot(row=0, col=0)
        self.imageItem = pg.ImageItem()
        self.imagePanel.addItem(self.imageItem)

        self.notice = QLabel(self)
        self.notice.setObjectName('previewNotice')
        self.notice.setWordWrap(True)
        self.notice.setText(self._reason)

        self.slice = QLabel(self)
        self.slice.setObjectName('previewSlice')
        self.slice.setWordWrap(True)

        stack = QStackedWidget(self)
        stack.addWidget(self.curvePlot)
        stack.addWidget(self.imagePlot)
        stack.addWidget(self.notice)
        self.stack = stack

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(stack)
        layout.addWidget(self.slice)

    @staticmethod
    def forView(dataTreeView):
        """The panel docked in the shot view this gesture came from."""
        panel = dataTreeView.parent.findChild(QVizPreviewPlot)
        if panel is None:
            raise ValueError('Preview Plot Widget not found. Update not possible')
        return panel

    def showNode(self, treeNode):
        """Draw what this quantity allows, or say why nothing is drawn.

        Returns 'curve', 'picture' or 'nothing'. Whatever was on the panel is
        gone either way: a thumbnail of another quantity, still labelled with
        that quantity's name, is not an answer about the node under the click.
        """
        self.clear()
        plotting = QVizNodePlotting(treeNode)

        if not plotting.isDataLeaf():
            return self._refuse('"%s" is a structure, not a quantity.'
                                % plotting.path())
        if plotting.isStringLeaf():
            return self._refuse('"%s" holds text: nothing to draw.'
                                % plotting.path())

        ownAxes = plotting.axes.leafAxes()
        if len(ownAxes) > 2:
            return self._refuse('"%s" has %d axes of its own: a thumbnail shows '
                                'two. Plot it to a figure, which reads the rest.'
                                % (plotting.path(), len(ownAxes)))

        # A quantity with no axis of its own can only be shown as it moves: the
        # read along time is what turns a number held by the dynamic array into
        # a history. Without a time base there is no abscissa to borrow -- that
        # belongs to another quantity already on a figure.
        alongTime = not ownAxes
        if alongTime and not plotting.hasTimeAxis():
            return self._refuse('"%s" is one number with no axis around it: '
                                'nothing to draw it against.' % plotting.path())

        access = QVizTensorDataAccess(treeNode.getDataSource())
        try:
            answer = access.GetSignal(treeNode=treeNode, plotWidget=None,
                                      as_function_of_time=alongTime)
        except ValueError as error:
            # The read says what it refused and why; for a preview that is the
            # reason, and the panel is where the user is looking for it.
            return self._refuse(str(error))

        self._sayWhatWasPinned(plotting.axes, drawn=ownAxes, alongTime=alongTime)

        if isinstance(answer, QVizDataArrayHandle):
            return self._drawPicture(answer, treeNode, plotting)
        return self._drawCurve(answer, treeNode, ownAxes, alongTime)

    def kind(self):
        return self._kind

    def reason(self):
        return self._reason

    def sliceText(self):
        return self._sliceText

    def curve(self):
        """The curve on screen: (x, y) as pyqtgraph holds them."""
        if self._kind != CURVE or not self.curvePlot.getPlotItem().curves:
            return None, None
        return self.curvePlot.getPlotItem().curves[0].getData()

    def picture(self):
        """The picture on screen, and the box it was laid over."""
        if self._kind != PICTURE or self.imageItem.image is None:
            return None, None
        rect = self.imageItem.mapRectToParent(self.imageItem.boundingRect())
        return np.asarray(self.imageItem.image), rect

    def clear(self):
        self._kind = NOTHING
        self._sliceText = ''
        self.curvePlot.clear()
        self.imageItem.clear()
        self.imagePanel.setTitle('')
        self._show(self.notice)

    # ------------------------------------------------------------------
    # The two things it can draw.

    def _drawCurve(self, answer, treeNode, ownAxes, alongTime):
        x, y = answer[0], answer[1]
        if x.size == 0 or y.size == 0 or y.shape[0] == 0 or y.shape[-1] == 0:
            return self._refuse('"%s" holds no values along that axis.'
                                % (treeNode.getName() or ''))
        self.curvePlot.plot(np.asarray(x[0]), np.asarray(y[0]))
        if alongTime:
            self.curvePlot.setLabel('bottom', 'time', units='s')
        else:
            axis = ownAxes[0]
            self.curvePlot.setLabel('bottom', sliceLabel(axis),
                                    units=axis.units or '')
        self.curvePlot.setLabel('left', self.quantityLabel(treeNode))
        self._kind = CURVE
        self._reason = ''
        self._show(self.curvePlot)
        return CURVE

    def _drawPicture(self, handle, treeNode, plotting):
        values = np.asarray(handle.arrayValues)
        if values.size == 0 or 0 in values.shape:
            return self._refuse('"%s" holds no values to picture.'
                                % plotting.path())
        self.imageItem.setImage(values)
        self._layOver(handle, values)
        self.imagePanel.setTitle(self.quantityLabel(treeNode))
        for side, dim in zip(('bottom', 'left'), (1, 2)):
            self.imagePanel.setLabel(side, handle.getCoordinateLabel(dim))
        self._kind = PICTURE
        self._reason = ''
        self._show(self.imagePlot)
        return PICTURE

    def _layOver(self, handle, values):
        """Span the picture over the coordinates it was taken on.

        Without this an axis labelled in metres carries element ranks under it.
        A coordinate the dictionary names but this case leaves empty leaves the
        picture on its ranks, which is what the numbers are then.
        """
        extents = []
        for dim in (1, 2):
            try:
                coordinates = np.asarray(handle.getCoordinateValues(dim),
                                         dtype=float)
            except (TypeError, ValueError):
                coordinates = np.asarray([])
            if coordinates.size == 0:
                return
            low, high = float(np.min(coordinates)), float(np.max(coordinates))
            if high == low:
                return
            extents.append((low, high))
        (x0, x1), (y0, y1) = extents
        self.imageItem.setRect(x0, y0, x1 - x0, y1 - y0)

    # ------------------------------------------------------------------
    # What the panel says about itself.

    def _sayWhatWasPinned(self, axes, drawn, alongTime):
        """Which element of every axis the thumbnail leaves out.

        The indices come from the tree, so naming them costs no read: this is
        the same answer a figure's slice controls would carry, spelled out in
        one line under a picture that cannot carry them.
        """
        pinned = []
        for axis in axes.axes:
            if axis in drawn:
                continue
            if alongTime and axis.is_time:
                continue
            index = axis.index
            pinned.append('%s %s' % (sliceLabel(axis),
                                     '?' if index is None else index))
        self._sliceText = ', '.join(pinned)
        self.slice.setText(self._sliceText)

    def quantityLabel(self, treeNode):
        quantity = treeNode.getName() or ''
        units = treeNode.getUnits()
        return quantity + '[' + units + ']' if units else quantity

    def _refuse(self, reason):
        self._kind = NOTHING
        self._reason = reason
        self.notice.setText(reason)
        self.slice.setText('')
        self._show(self.notice)
        return NOTHING

    def _show(self, page):
        self.stack.setCurrentWidget(page)
