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
are looked for in the tree as it stands: an IDS that has not been loaded is
named in the log rather than drawn from a guess. What the file holds besides the
paths -- pen, symbols, axis ranges -- is not carried over, and the command says
so rather than letting the user find out by comparing two windows.
"""

import logging
import xml.etree.ElementTree as ET

from imasviz.VizUtils import FigureTypes, QVizGlobalOperations
from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizTablePlot import QVizTablePlot


class QVizPlotAsTable(QVizAbstractCommand):
    """One panel per quantity, from a selection or from a configuration file."""

    FIGURE_TYPE = FigureTypes.TABLEPLOTTYPE

    def __init__(self, dataTreeView, all_DTV=False, plotAxis='DEFAULT',
                 configFile=None):
        """
        Arguments:
            all_DTV   (bool) : draw the selection of this view, or of every
                               opened view.
            plotAxis  (str)  : 'TIME' to read every quantity along time,
                               anything else for the default strategy -- which
                               the read answers per quantity, because only the
                               read knows whether this one has a time base.
            configFile (str) : a saved plot configuration: it names the
                               quantities by path and occurrence instead of
                               taking them from the selection.
        """
        self.api = dataTreeView.imas_viz_api
        self.all_DTV = all_DTV
        self.plotAxis = plotAxis
        self.configFile = configFile
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
        if self.configFile is not None:
            return self.quantitiesFromConfiguration()
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

    def quantitiesFromConfiguration(self):
        """The quantities a saved configuration names, found in this tree.

        The paths are read with the helper the signal-selection entries use, so
        a configuration written by either entry is read the same way. A path the
        tree does not hold is named and skipped: loading an IDS is another
        command's job, and drawing a quantity that is not in the tree would
        invent a node the user cannot select, name or click.
        """
        self.refuseConfigurationStyling()
        pathsMap = QVizGlobalOperations.getSignalsPathsFromConfigurationFile(
            self.configFile)
        paths = QVizGlobalOperations.makeIMASPaths(pathsMap.get('paths') or [])
        occurrences = pathsMap.get('occurrences') or []
        quantities = []
        for index, path in enumerate(paths):
            occurrence = self.occurrenceOf(occurrences, index)
            node = self.findNode(path, occurrence)
            if node is None:
                logging.getLogger(self.dataTreeView.uri).error(
                    '"%s" is named by "%s" but is not in this tree: load the '
                    'IDS it belongs to before applying the configuration.'
                    % (path, self.configFile))
                continue
            quantities.append((self.dataTreeView, node,
                               {'QTreeWidgetItem': node,
                                'uri': self.dataTreeView.dataSource.uri}))
        return quantities

    @staticmethod
    def occurrenceOf(occurrences, index):
        if not occurrences:
            return 0
        if len(occurrences) == 1:
            return int(occurrences[0])
        return int(occurrences[index])

    def findNode(self, path, occurrence):
        for node in self.dataTreeView.signalsList:
            if node.getPath() == path and node.getOccurrence() == occurrence:
                return node
        return None

    def refuseConfigurationStyling(self):
        """Say what a configuration file carries that is not applied.

        Not a silent omission: the user saved a window that looked a certain way
        and is about to be shown one that looks different. What is carried over
        is which quantities, and where they sit in the table.
        """
        try:
            styled = ET.parse(self.configFile).getroot().findall(
                './/PlotDataItem/opts')
        except (OSError, ET.ParseError) as e:
            raise ValueError('Cannot read "%s": %s' % (self.configFile, e))
        if styled:
            logging.getLogger(self.dataTreeView.uri).warning(
                '"%s" holds styling for %d panel(s) (pen, symbols, axis '
                'ranges): it is not applied. The quantities and their place in '
                'the table are taken from the file; the panels are drawn from '
                'the data.' % (self.configFile, len(styled)))

    def plotNode(self, dtv, treeNode, entry):
        """Give one quantity its panel. Returns how many curves it holds."""
        try:
            drawn = self.figure.plot(treeNode,
                                     as_function_of_time=self.alongTime())
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
        figureKey = self.api.GetNextKeyForFigure(self.FIGURE_TYPE)
        frame = QVizTablePlot(title=figureKey)
        frame.figureKey = figureKey
        frame.dataTreeView = self.dataTreeView
        frame.setPlotAxis(self.plotAxis if self.plotAxis == 'TIME' else 'DEFAULT')
        self.api.figureframes[figureKey] = frame
        return frame
