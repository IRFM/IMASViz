# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The plot command that goes through the tensor read.

The legacy command refuses any node the dictionary does not rank 0 or 1: a
figure holds one slider group and has no way to say which element of which array
the numbers on screen came from. This command takes a quantity of any rank
because the axes it does not draw come back from the read as named, bounded
controls -- see QVizCurvePlot for the loop that closes around them.

The figure key is allocated here rather than through Viz_API. The legacy 'Figure:'
keys are listed by the "add to an existing figure" menu entries, which build
their curves through the old path and would be handed a frame they do not know
how to fill, so the two paths keep separate key namespaces.
"""

import logging

from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizAbstractPlot import QVizAbstractPlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot


class QVizPlotAsSlices(QVizAbstractCommand, QVizAbstractPlot):
    """One curve per selected node, one control per axis the read leaves out."""

    FIGURE_TYPE = 'SlicesPlot'

    def __init__(self, dataTreeView, figureKey=None, all_DTV=True):
        self.api = dataTreeView.imas_viz_api
        self.all_DTV = all_DTV
        self.figureKey = figureKey or self.nextFigureKey()
        self.plotWidget = QVizCurvePlot(title=self.figureKey)
        self.api.figureframes[self.figureKey] = self.plotWidget
        QVizAbstractCommand.__init__(self, dataTreeView, None)
        QVizAbstractPlot.__init__(self, self.plotWidget)

    def execute(self):
        """Draw every selected node, then show the figure.

        Returns the figure, so a caller can embed it or plot further nodes on it.
        """
        selected = [(dtv, node) for dtv in self.views()
                    for node in self.selectedNodes(dtv)]
        if not selected:
            self.api.DeleteFigure(figureKey=self.figureKey)
            raise ValueError("No signal selected.")

        for dtv, node in selected:
            self.plotNode(dtv, node)

        if self.plotWidget.curveCount() == 0:
            # A window holding no curve says nothing, and the reason each node
            # was refused is already in the log panel of its shot view.
            self.api.DeleteFigure(figureKey=self.figureKey)
            raise ValueError("Nothing to plot: no selected node gave a value.")

        self.plotWidget.show()
        return self.plotWidget

    def plotNode(self, dtv, treeNode):
        """Add one node to the figure. Returns the number of rows drawn."""
        try:
            rows = self.plotWidget.plot(treeNode)
        except Exception as e:
            # Reading a real case fails for reasons the node cannot know about
            # (a coordinate the dictionary names and the shot does not hold). One
            # unreadable selection must not cost the user the other curves.
            logging.getLogger(dtv.uri).error(str(e))
            return 0
        self.api.AddNodeToFigure(self.figureKey, dtv.dataSource.dataKey(treeNode),
                                 (dtv.dataSource.uri, treeNode))
        return rows

    def views(self):
        return self.api.DTVlist if self.all_DTV else [self.dataTreeView]

    @staticmethod
    def selectedNodes(dtv):
        return [entry['QTreeWidgetItem'] for entry in dtv.selectedSignalsDict.values()]

    def nextFigureKey(self):
        taken = [key for key in self.api.figureframes if key.startswith(self.FIGURE_TYPE)]
        return self.FIGURE_TYPE + str(len(taken) + 1)
