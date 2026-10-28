# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The command that fills a Table Plot View.

Two inputs name the quantities: a selection, or a configuration file saved from
an earlier window. Both end up as one panel per quantity, read through the
tensor read -- the old command read the whole selection against one abscissa
through ``Viz_API.GetSignal`` and drew whatever came back, which is why a
quantity with two axes to draw either died on the read or came back as a curve
of one of its elements.

The abscissa stays a per-selection choice, because the menu offers it that way
("New (default axis)" and "New ('TIME' axis)"), but it is a *strategy*: the read
decides per quantity what that strategy means, so a selection mixing quantities
on different coordinates gets one panel each with its own labels rather than one
label for the whole window. That is also why the old gate on this entry -- do
these signals share coordinates? -- is gone: nothing here shares an abscissa, so
there is nothing to agree on.

A configuration file names the quantities by IDS path and occurrence, and they
are looked for in the tree as it stands: a path the tree does not hold is named
in the log rather than drawn from a guess. The file also says where each panel
sat in the table and along which abscissa the window was drawn, and both are put
back -- which the old reader never did, though the old writer recorded the place:
measured, a file naming (0, 0) and (1, 1) laid its panels at (0, 0) and (0, 1),
and a window drawn along time came back along two spatial coordinates. What an
older file carries besides that -- pen, symbols, axis ranges -- is not carried
over, and the command says so rather than letting the user find out by comparing
two windows.
"""

import logging

from imasviz.VizUtils import FigureTypes
from imasviz.VizGUI.VizConfigurations.QVizConfigurationFile import \
    QVizConfigurationFile
from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizTablePlot import QVizTablePlot


class QVizPlotAsTable(QVizAbstractCommand):
    """One panel per quantity, from a selection or from a configuration file."""

    FIGURE_TYPE = FigureTypes.TABLEPLOTTYPE

    def __init__(self, dataTreeView, all_DTV=False, plotAxis=None,
                 configFile=None, configuration=None, figureKey=None):
        """
        Arguments:
            all_DTV   (bool) : draw the selection of this view, or of every
                               opened view.
            plotAxis  (str)  : 'TIME' to read every quantity along time,
                               anything else for the default strategy -- which
                               the read answers per quantity, because only the
                               read knows whether this one has a time base.
                               Left out, a configuration file's own abscissa
                               decides; a saved window was drawn along one, and
                               applying it should give that window back.
            configFile (str) : a saved plot configuration: it names the
                               quantities by path and occurrence instead of
                               taking them from the selection.
            configuration    : a configuration already read, for whoever names
                               the same things in another file. A session file
                               holds the quantities of a Table Plot View and the
                               cell each panel sat in -- the same two answers a
                               plot configuration carries -- and the places only
                               survive if they reach this command as a
                               configuration, because laying them out again by
                               hand is how two panels ended up in one cell.
            figureKey  (str) : the key the new window is to carry, for a session
                               put back under the names its file gave them.
        """
        self.api = dataTreeView.imas_viz_api
        self.all_DTV = all_DTV
        self.plotAxis = plotAxis
        self.configFile = configFile
        self.configuration = configuration
        self.figureKey = figureKey
        self.figure = None
        QVizAbstractCommand.__init__(self, dataTreeView, None)

    def execute(self):
        """Fill one window with a panel per quantity, and show it.

        Returns the frame, or None when the quantities named turned out to be
        undrawable: the caller then has nothing to embed, and the reason is
        already in the log.
        """
        quantities = self.quantities()
        if not quantities:
            raise ValueError(
                'Nothing to plot: %s.' % (
                    '"%s" names no quantity this tree can provide'
                    % self.source() if self.namesQuantities() else
                    'no selected node to draw'))

        self.figure = self.newFigure()
        for dtv, node, entry, place in quantities:
            self.plotNode(dtv, node, entry, place)

        if not self.figure.isDrawing():
            self.api.DeleteFigure(figureKey=self.figure.figureKey)
            frame, self.figure = self.figure, None
            raise ValueError('Nothing to plot: none of the quantities named '
                             'gave a value along an axis a panel can draw.')
        self.figure.show()
        return self.figure

    def namesQuantities(self):
        return self.configFile is not None or self.configuration is not None

    def source(self):
        """The file to name when a quantity named by it is not in the tree."""
        if self.configFile is not None:
            return self.configFile
        return self.configuration.path

    def quantities(self):
        """[(view, node, selection entry, place)] for the quantities to draw.

        `place` is the (row, column) a configuration said the panel sat at, or
        None to lay it in the next free slot.
        """
        if self.namesQuantities():
            return self.quantitiesFromConfiguration()
        return [(dtv, node, self.selectionEntryOf(dtv, node), None)
                for dtv in self.views() for node in self.selectedNodes(dtv)]

    def views(self):
        return self.api.DTVlist if self.all_DTV else [self.dataTreeView]

    @staticmethod
    def selectedNodes(dtv):
        return [entry['QTreeWidgetItem'] for entry in dtv.selectedSignalsDict.values()]

    @staticmethod
    def selectionEntryOf(dtv, treeNode):
        return dtv.selectedSignalsDict.get(dtv.dataSource.dataKey(treeNode))

    def quantitiesFromConfiguration(self):
        """The quantities a configuration names, found in this tree.

        The file is read by the format, so the two shapes this application has
        written are read the same way and a file that is not a configuration is
        refused with its own reason. A path the tree does not hold is named and
        skipped: loading an IDS is another command's job, and drawing a quantity
        that is not in the tree would invent a node the user cannot select, name
        or click.
        """
        if self.configuration is None:
            self.configuration = QVizConfigurationFile.read(self.configFile)
        self.refuseConfigurationStyling()
        if self.plotAxis is None and self.configuration.abscissa:
            self.plotAxis = self.configuration.abscissa

        quantities = []
        for quantity, path in zip(self.configuration.quantities,
                                  self.configuration.treePaths()):
            node = self.findNode(path, quantity.occurrence)
            if node is None:
                logging.getLogger(self.dataTreeView.uri).error(
                    '"%s" is named by "%s" but is not in this tree: load the '
                    'IDS it belongs to before applying the configuration.'
                    % (path, self.source()))
                continue
            quantities.append((self.dataTreeView, node,
                               {'QTreeWidgetItem': node,
                                'uri': quantity.uri or
                                       self.dataTreeView.dataSource.uri},
                               self.placeOf(quantity)))
        return quantities

    @staticmethod
    def placeOf(quantity):
        """(row, column) the file said this panel sat at, or None."""
        if quantity.row is None or quantity.column is None:
            return None
        return quantity.row, quantity.column

    def findNode(self, path, occurrence):
        for node in self.dataTreeView.signalsList:
            if node.getPath() == path and node.getOccurrence() == occurrence:
                return node
        return None

    def refuseConfigurationStyling(self):
        """Say what an old configuration file carries that is not applied.

        Not a silent omission: the user saved a window that looked a certain way
        and is about to be shown one that looks different. What is carried over
        is which quantities, where they sit in the table, and the abscissa they
        were read along.
        """
        if not self.configuration.styledPanels:
            return
        logging.getLogger(self.dataTreeView.uri).warning(
            '"%s" holds styling for %d panel(s) (pen, symbols, axis '
            'ranges): it is not applied. The quantities, their place in '
            'the table and the abscissa are taken from the file; the panels '
            'are drawn from the data.'
            % (self.configFile, self.configuration.styledPanels))

    def plotNode(self, dtv, treeNode, entry, place=None):
        """Give one quantity its panel. Returns how many curves it holds."""
        try:
            drawn = self.figure.plot(treeNode,
                                     as_function_of_time=self.alongTime(),
                                     place=place)
        except Exception as e:
            # One unreadable quantity must not cost the user the rest of the
            # selection -- and a quantity with two axes to draw is refused by
            # name here rather than drawn wrong.
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
        figureKey = self.api.FigureKeyFor(self.FIGURE_TYPE, self.figureKey)
        frame = QVizTablePlot(title=figureKey)
        frame.figureKey = figureKey
        frame.dataTreeView = self.dataTreeView
        frame.setPlotAxis(self.plotAxis if self.plotAxis == 'TIME' else 'DEFAULT')
        self.api.figureframes[figureKey] = frame
        return frame
