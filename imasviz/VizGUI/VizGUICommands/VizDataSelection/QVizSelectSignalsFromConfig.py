# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import xml.etree.ElementTree as ET
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizUnselectAllSignals \
    import QVizUnselectAllSignals
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignals \
    import QVizSelectSignals


class QVizSelectSignalsFromConfig():
    """Select a group of all signals by given list of signal paths.
    """
    # TODO: it could be better to set it as a part of one of already
    #       existing signal selection classes

    def __init__(self):
        pass

    def execute(self, dataTreeView, config):
        """Select signals, listed in the configuration file.

        Arguments:
            dataTreeView (QTreeWidget) : DataTreeView object of the QTreeWidget.
            config   (str/dict) : System path to the configuration file or
                                  configuration dictionary.
        """
        plotItem_plotDataItemCountMap = {}  # key = panel key, value = selected arrays count
        pathsMap = []
        pathsList = []
        occurrencesList = []

        # If path to configuration file was given, get the dictionary. If
        # configuration dictionary is was given, used it
        if isinstance(config, str):
            plotConfig = ET.parse(config)  # dictionary
        else:
            plotConfig = config

            # Set plot configuration dictionary

        # Unselect all signals
        QVizUnselectAllSignals(dataTreeView).execute()

        # Get main 'GraphicsWindow' element
        graphicsWindowEl = plotConfig.find('GraphicsWindow')
        # Get a list of PlotItem elements
        plotItemElements = graphicsWindowEl.findall('PlotItem')
        # Get number of plot panels (pg.PlotItem-s)
        num_plotItems = len(plotItemElements)

        # Go through pg.PlotItems
        for pItemElement in plotItemElements:
            # Get key attribute (key=(column,row))
            key = pItemElement.get('key')
            # Get a list of pg.PlotDataItems
            # Note: Only one per StackedPlotView PlotItem
            plotItemDataElements = pItemElement.findall('PlotDataItem')
            # Get number of plots (pg.PlotDataItem-s)
            num_plots = len(plotItemDataElements)
            # Go through pg.PlotdataItems / plots / lines
            for pdItemElement in plotItemDataElements:
                # Find sourceInfo element
                sourceInfoEl = pdItemElement.find('sourceInfo')
                # Append node path from the sourceInfo element
                pathsList.append(sourceInfoEl.get("path"))
                occurrencesList.append(sourceInfoEl.get("occurrence"))
            # Add plot panel plot/line count/pg.PlotDataItems count to dict
            # for plot panel (pg.Item) key
            plotItem_plotDataItemCountMap[key] = num_plots

        pathsMap['paths'] = pathsList
        pathsMap['occurrences'] = occurrencesList
        # Select the signals using list of paths
        QVizSelectSignals(dataTreeView, pathsMap).execute()

        # Get a dictionary of selected signals
        dtv_selectedSignals = dataTreeView.selectedSignalsDict

        return dtv_selectedSignals, plotItem_plotDataItemCountMap
