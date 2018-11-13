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
        gWindowEl = ET.SubElement(root, 'GraphicsWindow')

        # Get dictionary of all plot items
        plotItemsDict = self.gWin.getPlotItemsDict()

        # Set shorter name for saveAttribute function
        sa = self.saveAttribute

        # k = 0
        # for n in range(0, len(self.gWin.getPlotItemsDict())):
        for plotItem in plotItemsDict:
            # Get row and column of the plot
            row = plotItemsDict[plotItem][0][0]
            column = plotItemsDict[plotItem][0][1]
            # Set key, specifying plot row and column in graphicsWindow
            key = (row, column)

            # Continue only if the plotItem is filled (contains signal info)
            if hasattr(plotItem, 'signalData') != True:
                break

            # Extract signal node data (it contains also 'path') from the
            # signal
            nodeData = plotItem.signalData['nodeData']

            # Set new subelement
            plotItemEl = ET.SubElement(gWindowEl, 'PlotItem')
            # Set subelement attribute 'key'
            sa(plotItemEl, 'key', key)
            # Set subelement attributes 'row' and 'column'
            sa(plotItemEl, 'row', row)
            sa(plotItemEl, 'column', column)
            # Set subelement attribute 'title'
            sa(plotItemEl, 'title',
                plotItem.titleLabel.item.document().toRawText())

            # Set new subelement for holding source information
            sourceInfoEl = ET.SubElement(plotItemEl, 'sourceInfo')

            # Save plot source information
            sa(sourceInfoEl, 'path',       nodeData['Path'])
            sa(sourceInfoEl, 'shotNumber', plotItem.signalData['shotNumber'])
            sa(sourceInfoEl, 'runNumber',  plotItem.signalData['runNumber'])
            sa(sourceInfoEl, 'imasDbName', plotItem.signalData['imasDbName'])
            sa(sourceInfoEl, 'userName',   plotItem.signalData['userName'])

            # Set new subelement for holding plot opts configuration
            opts = plotItem.dataItems[0].opts
            optsEl = ET.SubElement(plotItemEl, 'opts')
            sa(optsEl, 'connect',     opts['connect'])
            sa(optsEl, 'fftMode',     opts['fftMode'])
            sa(optsEl, 'logMode',     opts['logMode'])
            sa(optsEl, 'alphaHint',   opts['alphaHint'])
            sa(optsEl, 'alphaMode',   opts['alphaMode'])
            # sa(optsEl, 'pen',         opts['pen'])
            sa(optsEl, 'shadowPen',   opts['shadowPen'])
            sa(optsEl, 'fillLevel',   opts['fillLevel'])
            sa(optsEl, 'fillBrush',   opts['fillBrush'])
            sa(optsEl, 'stepMode',    opts['stepMode'])
            sa(optsEl, 'symbol',      opts['symbol'])
            sa(optsEl, 'symbolSize',  opts['symbolSize'])
            sa(optsEl, 'symbolPen',   opts['symbolPen'])
            sa(optsEl, 'symbolBrush', opts['symbolBrush'])
            sa(optsEl, 'pxMode',      opts['pxMode'])
            sa(optsEl, 'antialias',   opts['antialias'])
            sa(optsEl, 'pointMode',   opts['pointMode'])
            sa(optsEl, 'downsample',  opts['downsample'])
            sa(optsEl, 'autoDownsample',       opts['autoDownsample'])
            sa(optsEl, 'downsampleMethod',     opts['downsampleMethod'])
            sa(optsEl, 'autoDownsampleFactor', opts['autoDownsampleFactor'])
            sa(optsEl, 'clipToView',  opts['clipToView'])
            sa(optsEl, 'data',        opts['data'])
            sa(optsEl, 'name',        opts['name'])

            # Set new subelement for holding plot pen configuration
            pen = opts['pen'] # QPen
            penEl = ET.SubElement(optsEl, 'pen')
            # - Brush
            penBrushEl = ET.SubElement(penEl, 'QBrush')
            penBrushColorEl = ET.SubElement(penBrushEl, 'QColor')
            sa(penBrushColorEl, 'style', pen.brush().style())
            sa(penBrushColorEl, 'colorRGB', pen.brush().color().getRgb())
            sa(penBrushColorEl, 'alpha', pen.brush().color().alpha())
            # - Cap style
            sa(penEl, 'Qt.PenCapStyle',  pen.capStyle())
            # - Color
            penColorEl = ET.SubElement(penEl, 'QColor')
            sa(penColorEl, 'colorRGB', pen.color().getRgb())
            sa(penColorEl, 'alpha', pen.color().alpha())
            # - Join style
            sa(penEl, 'Qt.PenJoinStyle', pen.joinStyle())
            # - Pen style
            sa(penEl, 'Qt.PenStyle', pen.style())
            # - Pen width
            sa(penEl, 'width', opts['pen'].width()) # int
            sa(penEl, 'widthF', opts['pen'].widthF()) # float
            # - Other
            sa(penEl, 'dashOffset', opts['pen'].dashOffset())
            sa(penEl, 'isCosmetic', opts['pen'].isCosmetic())
            sa(penEl, 'isSolid', opts['pen'].isSolid())
            sa(penEl, 'miterLimit', opts['pen'].miterLimit())

            # TODO
            # plotItem.axes.top ...
            # plotItem.axes.bottom ...
            # plotItem.axes.left ...
            # plotItem.axes.right ...

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
