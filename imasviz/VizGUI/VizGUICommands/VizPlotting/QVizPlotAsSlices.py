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

The figure keys are allocated here rather than through Viz_API. The legacy
'Figure:' and 'Image:' keys are listed by the "add to an existing figure" menu
entries, which build their curves through the old path and would be handed frames
they do not know how to fill, so the two paths keep separate key namespaces.
"""

import logging

from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand
from imasviz.VizDataAccess.QVizTensorDataAccess import QVizTensorDataAccess
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizImagePlot import QVizImagePlot


class QVizPlotAsSlices(QVizAbstractCommand):
    """Draw the selection: one curve figure, one figure per image.

    Not a QVizAbstractPlot: this command owns no single plot widget. How many
    frames it draws is whatever the selection needs.
    """

    CURVE_FIGURE_TYPE = 'SlicesPlot'
    IMAGE_FIGURE_TYPE = 'SlicesImage'

    def __init__(self, dataTreeView, all_DTV=True):
        self.api = dataTreeView.imas_viz_api
        self.all_DTV = all_DTV
        self.figures = []
        self.curveFigure = None
        self.imageFigures = []
        QVizAbstractCommand.__init__(self, dataTreeView, None)

    def execute(self):
        """Draw every selected node, then show the figures.

        Returns the frames drawn, in creation order, so the caller can embed them.
        """
        selected = [(dtv, node) for dtv in self.views()
                    for node in self.selectedNodes(dtv)]
        if not selected:
            raise ValueError("No signal selected.")

        for dtv, node in selected:
            self.plotNode(dtv, node)

        if not self.figures:
            raise ValueError("Nothing to plot: no selected node gave a value.")

        for frame in self.figures:
            frame.show()
        return self.figures

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
        """
        if self.plottedAxes(treeNode) == 2:
            return self.newImageFigure()
        if self.curveFigure is None:
            self.curveFigure = self.newCurveFigure()
        return self.curveFigure

    def plottedAxes(self, treeNode):
        """How many axes of the quantity a read would draw.

        Asked with the time axis pinned, which is the image's rule: if that read
        still has two axes to draw, the quantity is a picture and its time slice
        becomes one of its controls. Asked with time left open, every quantity in
        a dynamic array would answer one axis -- time -- and be called a curve.
        """
        plotted = QVizTensorDataAccess(treeNode.getDataSource()).plan(
            treeNode, plotWidget=None, as_function_of_time=False)[3]
        if len(plotted) > 2:
            raise ValueError('"' + self.dataPathOf(treeNode) + '" has ' +
                             str(len(plotted)) + ' axes to draw: no frame shows '
                             'more than two, and its controls cannot pin the rest.')
        return len(plotted)

    def newCurveFigure(self):
        return self.newFigure(self.CURVE_FIGURE_TYPE, QVizCurvePlot)

    def newImageFigure(self):
        figure = self.newFigure(self.IMAGE_FIGURE_TYPE, QVizImagePlot)
        self.imageFigures.append(figure)
        return figure

    def newFigure(self, figureType, frameClass):
        figureKey = self.nextFigureKey(figureType)
        frame = frameClass(title=figureKey)
        frame.figureKey = figureKey
        self.api.figureframes[figureKey] = frame
        self.figures.append(frame)
        return frame

    def discardIfEmpty(self, frame):
        """Drop a frame that ended up showing nothing.

        A window holding neither a curve nor a picture says nothing, and the
        reason the node was refused is already in the log panel of its shot view.
        """
        if frame is None or frame.isDrawing():
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

    def nextFigureKey(self, figureType):
        taken = [key for key in self.api.figureframes if key.startswith(figureType)]
        return figureType + str(len(taken) + 1)

    @staticmethod
    def dataPathOf(treeNode):
        path = treeNode.getParametrizedDataPath()
        return path if path else treeNode.getName()
