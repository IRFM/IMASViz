# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The command that fills a Stacked Plot View.

One panel per selected quantity, stacked in a column and read against the same
abscissa -- which is the whole difference with a Table Plot View, and the reason
this command refuses quantities by name instead of drawing them. The old path
built the window first and read whatever came back through
``Viz_API.GetSignal``, so a quantity the window could not share came out as a
curve measured along another quantity's axis, and a quantity with two axes to
draw died on the read leaving a registered window with nothing in it.

The abscissa is a strategy the menu offers ('TIME', or the default the read
answers per quantity), but it is applied once: the first quantity that gives a
curve fixes the axis, and everything after it has to run along that one. The
refusal names both axes and points at TablePlotView, because a user who selected
two quantities on different coordinates is not doing anything wrong -- they are
in the wrong window.
"""

import logging

from imasviz.VizUtils import FigureTypes
from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizStackedPlot import QVizStackedPlot


class QVizPlotAsStacked(QVizAbstractCommand):
    """One panel per quantity, in a column that shares one abscissa."""

    FIGURE_TYPE = FigureTypes.STACKEDPLOTTYPE

    def __init__(self, dataTreeView, all_DTV=False, plotAxis='TIME',
                 figureKey=None):
        """
        Arguments:
            all_DTV   (bool) : draw the selection of this view, or of every
                               opened view.
            plotAxis  (str)  : 'TIME' to read every quantity along time --
                               which is what the scripting entry has always
                               asked for -- anything else for the default
                               strategy, answered per quantity by the read.
            figureKey (str)  : the key the window is to carry, for a session put
                               back under the names its file gave its windows.
        """
        self.api = dataTreeView.imas_viz_api
        self.all_DTV = all_DTV
        self.plotAxis = plotAxis
        self.figureKey = figureKey
        self.figure = None
        QVizAbstractCommand.__init__(self, dataTreeView, None)

    def execute(self):
        """Fill one window with a panel per quantity, and show it.

        Returns the frame, or None when none of the quantities could be drawn:
        the caller then has nothing to embed, and the reason is in the log.
        """
        quantities = self.quantities()
        if not quantities:
            raise ValueError('Nothing to plot: no selected node to draw.')

        self.figure = self.newFigure()
        for dtv, node, entry in quantities:
            self.plotNode(dtv, node, entry)

        if not self.figure.isDrawing():
            self.api.DeleteFigure(figureKey=self.figure.figureKey)
            frame, self.figure = self.figure, None
            raise ValueError('Nothing to plot: none of the quantities named '
                             'gave a value along an axis a panel can draw.')
        self.figure.show()
        return self.figure

    def quantities(self):
        """[(view, node, selection entry)] for the quantities to draw."""
        return [(dtv, node, self.selectionEntryOf(dtv, node))
                for dtv in self.views() for node in self.selectedNodes(dtv)]

    def views(self):
        return self.api.DTVlist if self.all_DTV else [self.dataTreeView]

    @staticmethod
    def selectedNodes(dtv):
        return [entry['QTreeWidgetItem'] for entry in dtv.selectedSignalsDict.values()]

    @staticmethod
    def selectionEntryOf(dtv, treeNode):
        return dtv.selectedSignalsDict.get(dtv.dataSource.dataKey(treeNode))

    def plotNode(self, dtv, treeNode, entry):
        """Add one quantity to the column. Returns how many curves it holds."""
        try:
            drawn = self.figure.plot(treeNode,
                                     as_function_of_time=self.alongTime())
        except Exception as e:
            # A quantity this window cannot share must not cost the user the
            # rest of the selection, and must not be drawn wrong either: the
            # frame says which axis it would have run along and why that is not
            # the abscissa of this window.
            logging.getLogger(dtv.uri).error(str(e))
            return 0
        self.api.AddNodeToFigure(self.figure.figureKey,
                                 dtv.dataSource.dataKey(treeNode),
                                 (dtv.dataSource.uri, treeNode))
        self.figure.setSignalData(treeNode, entry)
        return drawn

    def alongTime(self):
        """None leaves the choice to the read, which asks the quantity."""
        return True if self.plotAxis == 'TIME' else None

    def newFigure(self):
        # The key is the name the Show/Hide and Delete menus address this window
        # by, so a session that names one gets it: handing out the next key would
        # put the window of a restored session somewhere else than where its file
        # says it is.
        figureKey = self.api.FigureKeyFor(self.FIGURE_TYPE, self.figureKey)
        frame = QVizStackedPlot(title=figureKey)
        frame.figureKey = figureKey
        frame.dataTreeView = self.dataTreeView
        frame.setPlotAxis(self.plotAxis if self.plotAxis == 'TIME' else 'DEFAULT')
        self.api.figureframes[figureKey] = frame
        return frame
