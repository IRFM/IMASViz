import wx
import os
from imasviz.gui_commands.AbstractCommand import AbstractCommand
from imasviz.util.GlobalOperations import GlobalOperations
import xml.etree.ElementTree as ET

class SavePlotsConfiguration(AbstractCommand):
    """Save signal selection and plot configuration to '.pcfg' file.
    """
    def __init__(self, DTV, frame, nodeData=None, cols=None):
        # AbstractCommand.__init__(self, view, nodeData)
        """Set self.nodeData = nodeData etc. with the use of the
           AbstractCommand
        """
        AbstractCommand.__init__(self, nodeData)

        self.DTV = DTV
        self.frame = frame
        self.cols = cols

    def execute(self):
        default_file_name = ""
        configName = None
        cancel = None
        loop = True
        while loop:
            x = GlobalOperations.askWithCancel(message='Name of the configuration ?',
                                               default_value=default_file_name)
            cancel = x[0]
            configName = x[1]
            if cancel != wx.CANCEL and (x == None or x == ""):
                x = GlobalOperations.showMessage(message='Please give a name to the configuration')
            else:
                loop = False

        if (cancel == wx.CANCEL):
            return

        configName = GlobalOperations.replaceSpacesByUnderScores(configName)
        if configName.endswith(".pcfg"):
            configName = configName[:-4]

        # Set file name
        fileName = GlobalOperations.getConfFilePath(configName=configName,
                                                    configType='pcfg')

        # Set root element
        root = ET.Element('PlotConfiguration')
        root.set('comment', 'This file has been generated automatically by the IMAS_VIZ application')
        frameElement = ET.SubElement(root, 'frame')

        k = 0

        # Get list of signals, selected in the WxDataTreeView
        selectedsignalsList = \
            GlobalOperations.getSortedSelectedSignals(self.DTV.selectedSignals)

        for n in range(0, len(self.frame.panels)):

            if (n+1) > len(selectedsignalsList):
                break

            key = GlobalOperations.getNextPanelKey(k, cols=self.cols)

            # Set new subelement
            panelElement = ET.SubElement(frameElement, 'panel')
            # Set subelement attribute 'key'
            panelElement.set('key', str(key))

            panel = self.frame.panels[key]

            # Set new subelement
            selectedArrayElement = ET.SubElement(panelElement, 'selectedArray')

            # Extract signal node data (it contains also 'path') from the
            # signal
            selectedArray = selectedsignalsList[n]
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


    def saveAttribute(self, panelElement, attribute, value):
        if value != None:
            panelElement.set(attribute, str(value))

    def printCode(self, text, level):
        return GlobalOperations.printCode(self.f, text, level)

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
