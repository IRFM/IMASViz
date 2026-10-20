# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The plot command that goes through the tensor read.

The legacy command refuses any node the dictionary does not rank 0 or 1: a figure
holds one slider group and has no way to say which element of which array the
numbers on screen came from. This command takes a quantity of any rank because
the axes it does not draw come back from the read as named, bounded controls --
see QVizCurvePlot and QVizImagePlot for the loop that closes around them.

It also picks the frame, because a user selects signals and not figure types. What
a frame can show is how many axes the read would draw, which is not the dimension
the dictionary spells on the leaf: a two-dimension quantity inside a dynamic array
has a time axis and two axes to draw, so it is a picture with time pinned, while
the same quantity read along time is a curve. The read answers that, so the choice
of frame and the numbers on it cannot come apart.

The figure keys keep their own namespaces, declared with the other kinds in
FigureTypes. The legacy "Figure:" key is listed by the "add to an existing figure"
menu entries, which build their curves through the old path and would be handed
frames they do not know how to fill. The keys are still handed out by the api,
because the Show/Hide and Delete menus read the same bookkeeping and two ways of
numbering it is how a key gets reused under a live window.
"""

import logging

from imasviz.VizUtils import FigureTypes
from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand
from imasviz.VizDataAccess.QVizNodePlotting import QVizNodePlotting
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizImagePlot import QVizImagePlot


class QVizPlotAsSlices(QVizAbstractCommand):
    """Draw the selection: one curve figure, one figure per image.

    Not a QVizAbstractPlot: this command owns no single plot widget. How many
    frames it draws is whatever the selection needs.
    """

    CURVE_FIGURE_TYPE = FigureTypes.CURVEPLOTTYPE
    IMAGE_FIGURE_TYPE = FigureTypes.IMAGEPLOTTYPE

    def __init__(self, dataTreeView, all_DTV=True, intoFigureKey=None):
        """
        Arguments:
            all_DTV       (bool) : whether the selection of this view or of every
                                   opened view is drawn.
            intoFigureKey  (str) : an already open curve figure to add the
                                   selection to. A picture frame cannot be given
                                   one: it shows one quantity, with its colour
                                   scale and its controls.
        """
        self.api = dataTreeView.imas_viz_api
        self.all_DTV = all_DTV
        self.intoFigureKey = intoFigureKey
        self.figures = []
        self.curveFigure = None
        self.imageFigures = []
        # Tracked apart from self.figures because execute() returns the frames it
        # built and the caller embeds them in the MDI area: a frame the user
        # already has on screen must not be embedded a second time.
        self.targetFigure = None
        QVizAbstractCommand.__init__(self, dataTreeView, None)

    def execute(self):
        """Draw every selected node, then show the figures.

        Returns the frames this command built, in creation order, so the caller
        can embed them.
        """
        selected = [(dtv, node) for dtv in self.views()
                    for node in self.selectedNodes(dtv)]
        if not selected:
            raise ValueError("No signal selected.")
        if self.intoFigureKey is not None:
            self.targetFigure = self.figureToJoin(self.intoFigureKey)

        for dtv, node in selected:
            self.plotNode(dtv, node)

        if not self.isDrawing():
            raise ValueError("Nothing to plot: no selected node gave a value.")

        for frame in self.figures + ([self.targetFigure]
                                     if self.targetFigure else []):
            frame.show()
        return self.figures

    def isDrawing(self):
        """Whether anything was drawn, in a frame built here or in the joined one.

        Not `self.figures`: a command that added nothing to a figure the user
        already had drew nothing either, and the caller has to know that to say
        so.
        """
        frames = self.figures + ([self.targetFigure] if self.targetFigure else [])
        return any(frame.isDrawing() for frame in frames)

    def figureToJoin(self, figureKey):
        """The open figure the selection is asked for, or the reason it cannot take it."""
        frame = self.api.figureframes.get(figureKey)
        if frame is None:
            raise ValueError('There is no figure "%s" to plot the selection into.'
                             % figureKey)
        if isinstance(frame, QVizImagePlot):
            raise ValueError('"%s" shows a picture: one quantity, with its own '
                             'colour scale and slice controls. The selection '
                             'needs a figure of its own.' % figureKey)
        return frame

    def plotNode(self, dtv, treeNode):
        """Add one node to the figure that can show it. Returns what was drawn."""
        frame = None
        try:
            frame = self.figureFor(treeNode)
            drawn = frame.plot(treeNode)
        except Exception as e:
            # Reading a real case fails for reasons the node cannot know about (a
            # coordinate the dictionary names and the shot does not hold), and a
            # quantity can carry more axes than any frame draws. One unreadable
            # selection must not cost the user the rest of them.
            logging.getLogger(dtv.uri).error(str(e))
            self.discardIfEmpty(frame)
            return 0
        self.api.AddNodeToFigure(frame.figureKey, dtv.dataSource.dataKey(treeNode),
                                 (dtv.dataSource.uri, treeNode))
        return drawn

    def figureFor(self, treeNode):
        """The frame for this quantity, built the first time one needs it.

        Quantities with one axis to draw share the curve figure: they are
        comparable, which is what a curve figure is for. An image is never shared,
        because two pictures in one frame would need one colour scale for two
        quantities and one control answering two images.

        Asked to join a figure the user already has, the command cannot send a
        quantity to the frame it needs -- that window is by definition not the one
        the user opened -- so it says so, naming the quantity. The rest of the
        selection still lands.
        """
        plottedAxes = self.plottedAxes(treeNode)
        if self.targetFigure is not None:
            if plottedAxes == 2:
                raise ValueError('"%s" needs a picture: two axes to draw, and "%s" '
                                 'holds curves.'
                                 % (self.dataPathOf(treeNode),
                                    self.targetFigure.figureKey))
            return self.targetFigure
        if plottedAxes == 2:
            return self.newImageFigure()
        if self.curveFigure is None:
            self.curveFigure = self.newCurveFigure()
        return self.curveFigure

    def dataPathOf(self, treeNode):
        path = treeNode.getParametrizedDataPath()
        return path if path else treeNode.getName()

    def plottedAxes(self, treeNode):
        """How many axes of the quantity a picture would show.

        The read decides this, and the node model is where that decision lives:
        the menu needs the same answer to offer the right entry, and working it
        out twice is how the entry and the picture come apart.
        """
        return QVizNodePlotting(treeNode).plottedAxes()

    def newCurveFigure(self):
        return self.newFigure(self.CURVE_FIGURE_TYPE, QVizCurvePlot)

    def newImageFigure(self):
        figure = self.newFigure(self.IMAGE_FIGURE_TYPE, QVizImagePlot)
        self.imageFigures.append(figure)
        return figure

    def newFigure(self, figureType, frameClass):
        figureKey = self.api.GetNextKeyForFigure(figureType)
        frame = frameClass(title=figureKey)
        frame.figureKey = figureKey
        self.api.figureframes[figureKey] = frame
        self.figures.append(frame)
        return frame

    def discardIfEmpty(self, frame):
        """Drop a frame this command built and ended up showing nothing.

        A window holding neither a curve nor a picture says nothing, and the
        reason the node was refused is already in the log panel of its shot view.
        A figure the user already had is never dropped here: it was on screen
        before the click, and refusing one node of the selection is not a reason
        to take the user's window away.
        """
        if frame is None or frame.isDrawing() or frame not in self.figures:
            return
        self.api.DeleteFigure(figureKey=frame.figureKey)
        self.figures.remove(frame)
        if frame is self.curveFigure:
            self.curveFigure = None
        if frame in self.imageFigures:
            self.imageFigures.remove(frame)

    def views(self):
        return self.api.DTVlist if self.all_DTV else [self.dataTreeView]

    @staticmethod
    def selectedNodes(dtv):
        return [entry['QTreeWidgetItem'] for entry in dtv.selectedSignalsDict.values()]
