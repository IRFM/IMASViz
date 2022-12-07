#  Name   : QVizSavePlotConfig
#
#          Container for handling of saving plot configuration to.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
# *****************************************************************************
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
# *******************************************************************************

import time
import logging
import xml.etree.ElementTree as ET
from imasviz.VizUtils import QVizGlobalOperations


class QVizSavePlotConfig():
    """Save signal selection and plot configuration to '.pcfg' file.

    Arguments:
        gWin (pyqtgraph.GraphicsWindow) : Window containing the plots
                                          (TablePlotView, StackedPlotView window).
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
        root = ET.Element('PlotConfiguration')
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
            if hasattr(plotItem, 'signalData') is not True:
                break

            # Extract signal node data (it contains also 'path') from the
            # signal

            nodeData = plotItem.signalData['QTreeWidgetItem'].infoDict

            # ------------------------------------------------------------------
            # Set new subelement for holding pg.PlotItem data
            plotItemEl = ET.SubElement(gWindowEl, 'PlotItem')
            # Set subelement attribute 'key'
            sa(plotItemEl, 'key', key)
            # Set subelement attributes 'row' and 'column'
            sa(plotItemEl, 'row', row)
            sa(plotItemEl, 'column', column)
            # Set subelement attribute 'title'
            sa(plotItemEl, 'title',
               plotItem.titleLabel.item.document().toPlainText())

            # ------------------------------------------------------------------
            # Set new subelement for holding pg.PlotDataItem data (child of
            # pg.PlotItem)
            plotDataItemEl = ET.SubElement(plotItemEl, 'PlotDataItem')

            # ------------------------------------------------------------------
            # Set new subelement for holding source information
            sourceInfoEl = ET.SubElement(plotDataItemEl, 'sourceInfo')

            # Save plot source information
            sa(sourceInfoEl, 'path', nodeData['Path'])
            sa(sourceInfoEl, 'occurrence', nodeData['occurrence'])
            sa(sourceInfoEl, 'shotNumber', plotItem.signalData['shotNumber'])
            sa(sourceInfoEl, 'runNumber', plotItem.signalData['runNumber'])
            sa(sourceInfoEl, 'imasDbName', plotItem.signalData['imasDbName'])
            sa(sourceInfoEl, 'userName', plotItem.signalData['userName'])

            # ------------------------------------------------------------------
            # Set new subelement for holding plot opts configuration
            opts = plotItem.dataItems[0].opts
            optsEl = ET.SubElement(plotDataItemEl, 'opts')
            sa(optsEl, 'connect', opts['connect'])
            sa(optsEl, 'fftMode', opts['fftMode'])
            sa(optsEl, 'logMode', opts['logMode'])
            sa(optsEl, 'alphaHint', opts['alphaHint'])
            sa(optsEl, 'alphaMode', opts['alphaMode'])
            # sa(optsEl, 'pen',         opts['pen'])
            sa(optsEl, 'shadowPen', opts['shadowPen'])
            sa(optsEl, 'fillLevel', opts['fillLevel'])
            sa(optsEl, 'fillBrush', opts['fillBrush'])
            sa(optsEl, 'stepMode', opts['stepMode'])
            # If symbol (shape) is not defined, save attribute as 'None'
            if opts['symbol'] is not None:
                sa(optsEl, 'symbol', opts['symbol'])
            else:
                sa(optsEl, 'symbol', 'None')
            sa(optsEl, 'symbolSize', opts['symbolSize'])
            sa(optsEl, 'symbolPen', opts['symbolPen'])
            sa(optsEl, 'symbolBrush', opts['symbolBrush'])
            sa(optsEl, 'pxMode', opts['pxMode'])
            sa(optsEl, 'antialias', opts['antialias'])
            sa(optsEl, 'pointMode', opts['pointMode'])
            sa(optsEl, 'downsample', opts['downsample'])
            sa(optsEl, 'autoDownsample', opts['autoDownsample'])
            sa(optsEl, 'downsampleMethod', opts['downsampleMethod'])
            sa(optsEl, 'autoDownsampleFactor', opts['autoDownsampleFactor'])
            sa(optsEl, 'clipToView', opts['clipToView'])
            sa(optsEl, 'data', opts['data'])
            sa(optsEl, 'name', opts['name'])

            # ------------------------------------------------------------------
            # Set new subelement for holding plot pen configuration
            pen = opts['pen']  # QPen
            self.savePenAttributes(panelElement=optsEl,
                                   pen=pen)
            # penEl = ET.SubElement(optsEl, 'pen')

            # ------------------------------------------------------------------
            # Set new subelement for holding plot axis configuration
            axisEl = ET.SubElement(plotDataItemEl, 'axisItem')
            # - Left axis
            self.saveAxisAttributes(panelElement=axisEl, axisType='left',
                                    plotItem=plotItem)
            # - Top axis
            self.saveAxisAttributes(panelElement=axisEl, axisType='top',
                                    plotItem=plotItem)
            # - Right axis
            self.saveAxisAttributes(panelElement=axisEl, axisType='right',
                                    plotItem=plotItem)
            # - Bottom axis
            self.saveAxisAttributes(panelElement=axisEl, axisType='bottom',
                                    plotItem=plotItem)

            # TODO
            # plotItem.legend ...

        self.indent(root)
        # Set element tree
        treeConfiguration = ET.ElementTree(root)
        # Write configuration file
        treeConfiguration.write(filePath, encoding="utf-8",
                                xml_declaration=True)
        # self.f.close()
        # Update the DTV configuration window (for the newly created
        # configuration to be displayed)
        if self.dataTreeView.parent.configurationListsWindow is not None:
            self.dataTreeView.parent.configurationListsWindow.updateList('pcfg')

    def saveAttribute(self, panelElement, attribute, value):
        """Save attribute as string to panelElement.

        Arguments:
            panelElement (ET.SubElement) : (Sub)Element to which the attribute
                                           is to be stored.
            attribute    (str)           : Attribute name/label.
            value        (any)           : Attribute value.
        """
        if value is not None:
            panelElement.set(attribute, str(value))

    def savePenAttributes(self, panelElement, pen):
        """Save pen attributes as string to panelElement.

        Arguments:
            panelElement (ET.SubElement) : (Sub)Element to which the attribute
                                           is to be stored.
            pen          (QPen)          : Pen from which pen attributes
                                           (color, width etc.) are extracted
                                           and saved under a new subelement
                                           tree for panelElement.
        """

        # Set shorter name for saveAttribute function
        sa = self.saveAttribute

        if pen is not None:
            # Set new subelement of the panelElement, holding all pen
            # attributes (in a form of a tree of subelements)
            penEl = ET.SubElement(panelElement, 'pen')
            # - Brush
            penBrushEl = ET.SubElement(penEl, 'QBrush')
            penBrushColorEl = ET.SubElement(penBrushEl, 'QColor')
            sa(penBrushColorEl, 'style', pen.brush().style())
            sa(penBrushColorEl, 'colorRGB', pen.brush().color().getRgb())
            sa(penBrushColorEl, 'alpha', pen.brush().color().alpha())
            # - Cap style
            sa(penEl, 'Qt.PenCapStyle', pen.capStyle())
            # - Color
            penColorEl = ET.SubElement(penEl, 'QColor')
            sa(penColorEl, 'colorRGB', pen.color().getRgb())
            sa(penColorEl, 'alpha', pen.color().alpha())
            # - Join style
            sa(penEl, 'Qt.PenJoinStyle', pen.joinStyle())
            # - Pen style
            sa(penEl, 'Qt.PenStyle', pen.style())
            # - Pen width
            sa(penEl, 'width', pen.width())  # int
            sa(penEl, 'widthF', pen.widthF())  # float
            # - Other
            sa(penEl, 'dashOffset', pen.dashOffset())
            sa(penEl, 'isCosmetic', pen.isCosmetic())
            sa(penEl, 'isSolid', pen.isSolid())
            sa(penEl, 'miterLimit', pen.miterLimit())
        else:
            # Print warning to DTV log
            logging.warning('savePenAttributes: Pen variable is not properly '
                            'defined.')

    def saveAxisAttributes(self, panelElement, axisType, plotItem):
        """Save pen attributes as string to panelElement.

        Arguments:
            panelElement (ET.SubElement) : (Sub)Element to which the attribute
                                           is to be stored.
            axisType    (str)           : Axis item from which the axis
                                           attributes (label, range etc.) are
                                           extracted and saved under a new
                                           subelement tree for panelElement.
                                           Note: accepts 'bottom', 'top',
                                           'right', 'left'.
            plotItem     (pg.PlotItem)   : PlotItem holding the AxisItems.
        """

        # Set shorter name for saveAttribute function
        sa = self.saveAttribute

        axisLabelList = ['left', 'top', 'right', 'bottom']

        # if axisType is not None and is 'bottom' or 'top' or 'left' or 'right':
        if axisType is not None and axisType in axisLabelList:
            # Set new subelement of the panelElement, holding all axis
            # attributes (in a form of a tree of subelements)
            axisItemEl = ET.SubElement(panelElement, axisType)
            AxisItem = plotItem.getAxis(axisType)  # pg.AxisItem
            # Set new subelement for holding plot pen configuration
            pen = AxisItem._pen  # QPen
            self.savePenAttributes(axisItemEl, pen)
            # Set new subelement for holding axis label configuration
            axisItemLabelEl = ET.SubElement(axisItemEl, 'label')
            axisItemLabel = AxisItem.label  # QGraphicsTextItem
            sa(axisItemLabelEl, 'text', axisItemLabel.toPlainText())
            sa(axisItemLabelEl, 'textWidth', axisItemLabel.textWidth())
            # sa(axisItemLabelEl, 'document', axisItemLabel.document()) # QTextDocument
            # Set new subelement for holding axis label font configuration
            axisItemLabelFontEl = ET.SubElement(axisItemEl, 'font')
            axisItemLabelFont = AxisItem.label.font()  # QGraphicsTextItem
            sa(axisItemLabelFontEl, 'bold', axisItemLabelFont.bold())
            sa(axisItemLabelFontEl, 'capitalization',
               axisItemLabelFont.capitalization())
            sa(axisItemLabelFontEl, 'family', axisItemLabelFont.family())
            sa(axisItemLabelFontEl, 'italic', axisItemLabelFont.italic())
            sa(axisItemLabelFontEl, 'overline', axisItemLabelFont.overline())
            sa(axisItemLabelFontEl, 'style', axisItemLabelFont.style())
            sa(axisItemLabelFontEl, 'underline', axisItemLabelFont.underline())
            sa(axisItemLabelFontEl, 'weight', axisItemLabelFont.weight())
            # Set new subelement for holding axis style configuration
            axisItemStyleEl = ET.SubElement(axisItemEl, 'style')
            axisItemStyle = AxisItem.labelStyle  # dict
            sa(axisItemStyleEl, 'color', axisItemStyle['color'])
            # Save other axis attributes
            sa(axisItemEl, 'labelText', AxisItem.labelText)
            sa(axisItemEl, 'labelUnitPrefix', AxisItem.labelUnitPrefix)
            sa(axisItemEl, 'labelUnits', AxisItem.labelUnits)
            sa(axisItemEl, 'range', AxisItem.range)
            sa(axisItemEl, 'scale', AxisItem.scale)
            # sa(axisItemEl, 'style', AxisItem.style)
            sa(axisItemEl, 'textHeight', AxisItem.textHeight)
            sa(axisItemEl, 'textWidth', AxisItem.textWidth)

        else:
            # Print warning to DTV log
            logging.warning('saveAxisAttributes: AxisItem variable is not '
                            'properly defined.')

    def printCode(self, text, level):
        return QVizGlobalOperations.printCode(self.f, text, level)

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
