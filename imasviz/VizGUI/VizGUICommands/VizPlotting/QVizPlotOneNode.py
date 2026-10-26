# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Draw one node from the tree, into the frame its axes call for.

The three entries that do this -- "Plot X to -> Figure -> New", the same with an
open figure picked from the submenu, and "Plot as function of time" -- all ended
in one command that asked a legacy plot widget for a window, read through it, and
drew two rows. Measured on this checkout with a quantity of two axes: the window
was created and registered first, then the read handed back a data-array handle
and `len()` on it raised TypeError, so the user got an empty figure named
Figure:1, no entry in the figure bookkeeping saying what was in it, and no word
in the log panel. A quantity of three axes was refused the same way. The time
entry read `dataTreeView.selectedItem` instead of the node the menu was built on,
and took the index to pin from `infoDict['i']` -- the loop letter of the first
enclosing array of structures -- so a quantity held by two of them was read at
the outer element, and a node the dictionary does not tag died on KeyError.

Here the read is asked how many axes it would draw, and the frame is opened only
once that answer exists: a refusal costs no window and says why in the log panel
of the shot view it came from. Two axes go to an image, one to a curve, and a
number with nothing around it but a time base is read along time -- which is what
the separate 0D entry used to mean. The node drawn is the node the menu was built
on, and the index pinned is the one the tree carries, because both come from the
node itself rather than from whatever happened to be selected.

The figure keys live in the namespaces the selection command uses (FigureTypes):
one bookkeeping for the frames the new path knows how to fill, so the Show/Hide
and Delete menus, the submenu here and the frames themselves cannot disagree.
"""

import logging

from imasviz.VizUtils import FigureTypes
from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand
from imasviz.VizDataAccess.QVizNodePlotting import QVizNodePlotting
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizImagePlot import QVizImagePlot


class QVizPlotOneNode(QVizAbstractCommand):
    """One quantity, drawn in a curve figure or an image figure.

    This command owns no plot widget and reads through no plot widget: it asks
    the read what it drew, and the frame it builds carries the axes the read
    leaves out.
    """

    CURVE_FIGURE_TYPE = FigureTypes.CURVEPLOTTYPE
    IMAGE_FIGURE_TYPE = FigureTypes.IMAGEPLOTTYPE

    def __init__(self, dataTreeView, treeNode, intoFigureKey=None,
                 alongTime=False, tensor=False):
        """
        Arguments:
            treeNode       (QVizTreeNode) : the node to draw, never the selection.
            intoFigureKey      (str)      : an open figure to add to, or None for
                                            a figure of this quantity's own.
            alongTime        (bool)       : read it as a history, along time.
            tensor           (bool)       : draw the tensor that holds it, under a
                                            slider per pinned axis, instead of the
                                            one element the tree is standing on.
        """
        self.api = dataTreeView.imas_viz_api
        self.intoFigureKey = intoFigureKey
        self.alongTime = alongTime
        self.tensor = tensor
        # Set when this command opened the figure itself: a frame that is already
        # on screen must not be embedded in a second subwindow.
        self.builtFigure = False
        QVizAbstractCommand.__init__(self, dataTreeView, treeNode)

    def execute(self):
        """Read the node and draw it. Returns the frame, or None when refused.

        The frame is returned and not shown, so the caller embeds it in the MDI
        area once it holds something: a node that cannot be read costs no window.
        """
        frame = None
        try:
            frame = self.frameFor()
            self.draw(frame)
        except Exception as e:
            # A quantity can carry more axes than any frame draws, a coordinate
            # the dictionary names can be missing from the shot, and neither is
            # a reason to leave an empty window on the screen.
            logging.getLogger(self.dataTreeView.uri).error(str(e))
            self.discardIfEmpty(frame)
            return None

        self.api.AddNodeToFigure(frame.figureKey,
                                 self.dataTreeView.dataSource.dataKey(self.treeNode),
                                 (self.dataTreeView.dataSource.uri, self.treeNode))
        return frame

    def frameFor(self):
        """The frame this quantity needs -- opened only once the read can answer."""
        if self.intoFigureKey is not None:
            frame = self.api.figureframes.get(self.intoFigureKey)
            if frame is None:
                raise ValueError('No open figure "' + self.intoFigureKey +
                                 '" to add "' + self.path() + '" to.')
            return frame

        plotting = QVizNodePlotting(self.treeNode)
        plotted = plotting.plottedAxes()
        if plotted == 0 and plotting.hasTimeAxis():
            # Nothing left to show in a picture: the only axis worth running
            # along is the time base, which is what the separate 0D entry did.
            plotted = 1
            self.alongTime = True
        if plotted == 0:
            raise ValueError('"' + self.path() + '" has no axis to draw along.')
        if plotted == 2:
            return self.newFigure(self.IMAGE_FIGURE_TYPE, QVizImagePlot)
        return self.newFigure(self.CURVE_FIGURE_TYPE, QVizCurvePlot)

    def draw(self, frame):
        if isinstance(frame, QVizImagePlot):
            # An image reads across its pictures along one axis of the quantity;
            # asking it for a history would be asking for a curve. And asking it
            # to explore a tensor would be asking the pictures to move under a
            # slider they are already spread over.
            if self.tensor:
                raise ValueError('"' + self.path() + '" is drawn as pictures: '
                                 'exploring its tensor belongs on a figure of '
                                 'curves, where a pinned axis can move.')
            frame.plot(self.treeNode)
            return
        frame.plot(self.treeNode,
                   as_function_of_time=True if self.alongTime else None,
                   tensor=self.tensor)

    def newFigure(self, figureType, frameClass):
        figureKey = self.api.GetNextKeyForFigure(figureType)
        frame = frameClass(title=figureKey)
        frame.figureKey = figureKey
        self.api.figureframes[figureKey] = frame
        self.builtFigure = True
        return frame

    def discardIfEmpty(self, frame):
        """Drop a frame that ended up showing nothing.

        A window holding neither a curve nor a picture says nothing, and the
        reason the node was refused is already in the log panel.
        """
        if frame is None or frame.isDrawing():
            return
        self.api.DeleteFigure(figureKey=frame.figureKey)
        self.builtFigure = False

    def path(self):
        return QVizNodePlotting(self.treeNode).path()
