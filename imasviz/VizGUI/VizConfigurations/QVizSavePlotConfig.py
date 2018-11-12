#  Name   : QVizSavePlotConfig
#
#          Container for handling of saving plot configuration to.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#****************************************************

import time
import xml.etree.ElementTree as ET
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations

class QVizSavePlotConfig():
    """Save signal selection and plot configuration to '.pcfg' file.

    Arguments:
        gWin (pyqtgraph.GraphicsWindow) : Window containing the plots
                                          (MultiPlot, SubPlot window).
    """
    def __init__(self, gWin, nodeData=None):
        self.gWin = gWin
        self.dataTreeView = gWin.parent.dataTreeView
        self.nodeData = nodeData

    def execute(self):
        # Set default name of the configuration file
        defaultName = 'plotConfig-' + time.strftime('%d-%m-%Y')
        configName = None
        # Set dialog message
        message = 'Type the name of the plot configuration. \nNote. If left ' \
            'empty the default name \n' + defaultName + '\nwill be used.'
        # Set configuration file name via dialog
        configName, ok = \
            QVizGlobalOperations.askWithCancel(parent=self.gWin,
                                               title='Dialog',
                                               message=message,
                                               default_value=defaultName)

        # Don't proceed with saving the signal selection if the dialog was
        # cancelled
        if ok == False:
            return

        # Format the configuration file name
        configName = QVizGlobalOperations.replaceSpacesByUnderScores(configName)
        if configName.endswith(".pcfg"):
            configName = configName[:-4]
            print("* configName: ", configName)

        # Set file name path
        filePath = QVizGlobalOperations.getConfFilePath(configName=configName,
                                                        configType='pcfg')

        # Print message
        print('Saving plot configuration to ' + filePath)

        # Set root element
        root = ET.Element('Plot Configuration')
        root.set('comment', 'This file has been generated automatically by '
                 'the IMASVIZ application. It contains saved plot '
                 'configuration: '
                 'a list of configurations for each plot and its corresponding '
                 'signal path - IDS database paths to arrays '
                 'containing data suitable for plotting.')

        # Set new subelement
        gWinElement = ET.SubElement(root, 'GraphicsWindow')

        # Get dictionary of all plot items
        plotItemsDict = self.gWin.getPlotItemsDict()

        # k = 0
        # for n in range(0, len(self.gWin.getPlotItemsDict())):
        for plotItem in plotItemsDict:
            # Get row and column of the plot
            row = plotItemsDict[plotItem][0][0]
            column = plotItemsDict[plotItem][0][1]
            # Set key, specifying plot row and column in graphicsWindow
            key = (row, column)

            # TODO use
            # List of child plotDataItems
            # a = plotItem.dataItems
            # a = plotItem.items

            # Continue only if the plotItem is filled (contains signal info)
            if hasattr(plotItem, 'signalData') != True:
                break

            # Extract signal node data (it contains also 'path') from the
            # signal
            nodeData = plotItem.signalData['nodeData']

            # Set new subelement
            plotItemElement = ET.SubElement(gWinElement, 'PlotItem')
            # Set subelement attribute 'key'
            plotItemElement.set('key', str(key))

            # Set new subelement
            sourceInfoElement = ET.SubElement(plotItemElement, 'sourceInfoElement')

            # Save plot source information
            self.saveAttribute(sourceInfoElement, 'path', nodeData['Path'])
            self.saveAttribute(sourceInfoElement, 'shotNum', plotItem.signalData['shotNumber'])
            self.saveAttribute(sourceInfoElement, 'runNum', plotItem.signalData['runNumber'])
            self.saveAttribute(sourceInfoElement, 'database', plotItem.signalData['imasDbName'])
            self.saveAttribute(sourceInfoElement, 'userName', plotItem.signalData['userName'])

            # Save plot configuration
            self.saveAttribute(plotItemElement,'title', plotItem.titleLabel.item.document().toRawText())

            # TODO
            # plotItem.axes.top ...
            # plotItem.axes.bottom ...
            # plotItem.axes.left ...
            # plotItem.axes.right ...

            # First plotDataItem
            # plotItem.dataItems[0].opts ...

            # plotItem.legend ...


        self.indent(root)
         # Set element tree
        treeConfiguration = ET.ElementTree(root)
        # Write configuration file
        treeConfiguration.write(filePath, encoding="utf-8", xml_declaration=True)
        #self.f.close()
        # Update the DTV configuration window (for the newly created
        # configuration to be displayed)
        if self.dataTreeView.parent.configurationListsWindow != None:
            self.dataTreeView.parent.configurationListsWindow.updateList('pcfg')

        """



            # Set new subelement
            panelElement = ET.SubElement(frameElement, 'panel')
            # Set subelement attribute 'key'
            panelElement.set('key', str(key))

            # Set new subelement
            selectedArrayElement = ET.SubElement(panelElement, 'selectedArray')

            # Extract signal node data (it contains also 'path') from the
            # signal
            selectedArray = panel.signal
            nodeData = selectedArray[1]

            self.saveAttribute(selectedArrayElement, 'path', nodeData['Path'])

            self.saveAttribute(selectedArrayElement, 'shotnum', selectedArray[0])
            self.saveAttribute(selectedArrayElement, 'runnum', selectedArray[3])
            self.saveAttribute(selectedArrayElement, 'database', selectedArray[4])
            self.saveAttribute(selectedArrayElement, 'username', selectedArray[5])

            self.saveAttribute(panelElement,'title', panel.conf.title)
            self.saveAttribute(panelElement,'xlabel', panel.conf.xlabel)
            self.saveAttribute(panelElement,'ylabel', panel.conf.ylabel)
            self.saveAttribute(panelElement,'y2label', panel.conf.y2label)
            self.saveAttribute(panelElement,'xscale', panel.conf.xscale)
            self.saveAttribute(panelElement,'yscale', panel.conf.yscale)
            self.saveAttribute(panelElement,'plot_type', panel.conf.plot_type)
            self.saveAttribute(panelElement,'scatter_size', panel.conf.scatter_size)
            self.saveAttribute(panelElement,'scatter_normalcolor', panel.conf.scatter_normalcolor)
            self.saveAttribute(panelElement,'scatter_normaledge', panel.conf.scatter_normaledge)
            self.saveAttribute(panelElement,'scatter_selectcolor', panel.conf.scatter_selectcolor)
            self.saveAttribute(panelElement,'scatter_selectedge', panel.conf.scatter_selectedge)
            self.saveAttribute(panelElement,'scatter_data', panel.conf.scatter_data)
            self.saveAttribute(panelElement,'scatter_coll', panel.conf.scatter_coll)
            self.saveAttribute(panelElement,'scatter_mask', panel.conf.scatter_mask)
            self.saveAttribute(panelElement, 'show_legend', panel.conf.show_legend)
            self.saveAttribute(panelElement, 'show_grid', panel.conf.show_grid)

            self.saveAttribute(panelElement, 'legend_loc', panel.conf.legend_loc)
            self.saveAttribute(panelElement, 'legend_onaxis', panel.conf.legend_onaxis)
            self.saveAttribute(panelElement, 'mpl_legend', panel.conf.mpl_legend)
            self.saveAttribute(panelElement, 'draggable_legend', panel.conf.draggable_legend)
            self.saveAttribute(panelElement, 'hidewith_legend', panel.conf.hidewith_legend)
            self.saveAttribute(panelElement, 'show_legend_frame', panel.conf.show_legend_frame)
            self.saveAttribute(panelElement, 'axes_style', panel.conf.axes_style)

            self.saveAttribute(panelElement, 'bgcolor', panel.conf.bgcolor)
            self.saveAttribute(panelElement, 'textcolor', panel.conf.textcolor)
            self.saveAttribute(panelElement, 'gridcolor', panel.conf.gridcolor)
            self.saveAttribute(panelElement, 'framecolor', panel.conf.framecolor)
            self.saveAttribute(panelElement, 'color_theme', panel.conf.color_theme)

            # self.margins = None
            # self.auto_margins = True

            j = 0
            for trace in panel.conf.traces:
                traceElement = ET.SubElement(panelElement, 'trace')
                self.saveAttribute(traceElement,'index', str(j))
                self.saveAttribute(traceElement, 'color', str(trace.color))
                self.saveAttribute(traceElement, 'style', str(trace.style))
                self.saveAttribute(traceElement, 'drawstyle', str(trace.drawstyle))
                self.saveAttribute(traceElement, 'linewidth', str(trace.linewidth))
                self.saveAttribute(traceElement, 'marker', str(trace.marker))
                self.saveAttribute(traceElement, 'markersize', str(trace.markersize))
                self.saveAttribute(traceElement, 'markercolor', str(trace.markercolor))
                self.saveAttribute(traceElement, 'label', str(trace.label))
                self.saveAttribute(traceElement, 'zorder', str(trace.zorder))

                dataRangeElement = ET.SubElement(traceElement, 'data_range')
                self.saveAttribute(dataRangeElement, 'dr1', str(trace.data_range[0]))
                self.saveAttribute(dataRangeElement, 'dr2', str(trace.data_range[1]))
                self.saveAttribute(dataRangeElement, 'dr3', str(trace.data_range[2]))
                self.saveAttribute(dataRangeElement, 'dr4', str(trace.data_range[3]))

                j = j + 1
            k += 1

        self.indent(root)
        treeConfiguration = ET.ElementTree(root)
        treeConfiguration.write(fileName, encoding="utf-8", xml_declaration=True)
        #self.f.close()
        if self.DTV.parent.configurationListsFrame != None:
            self.DTV.parent.configurationListsFrame.update_pconf()

    """
    def saveAttribute(self, panelElement, attribute, value):
        if value != None:
            panelElement.set(attribute, str(value))

    # def printCode(self, text, level):
    #     return GlobalOperations.printCode(self.f, text, level)

    def indent(self, elem, level=0):
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self.indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
