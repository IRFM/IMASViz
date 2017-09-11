import wx
import os
from imasviz.gui_commands.AbstractCommand import AbstractCommand
from imasviz.util.GlobalOperations import GlobalOperations
import xml.etree.ElementTree as ET

class SavePlotsConfiguration(AbstractCommand):
    def __init__(self, view, nodeData=None):
        AbstractCommand.__init__(self, view, nodeData)

    def execute(self):
        default_file_name = ""
        configName = None
        cancel = None
        loop = True
        while loop:
            x = GlobalOperations.askWithCancel(message='Name of the configuration ?', default_value=default_file_name)
            cancel = x[0]
            configName = x[1]
            if cancel != wx.CANCEL and (x == None or x == ""):
                x = GlobalOperations.showMessage(message='Please give a name to the configuration')
            else:
                loop = False

        if (cancel == wx.CANCEL):
            return

        configName = GlobalOperations.replaceSpacesByUnderScores(configName)

        fileName = GlobalOperations.getPlotsConfigurationFileName(configName)

        #self.f = open(fileName, 'w')


        root = ET.Element('PlotConfiguration')
        root.set('comment', 'This file has been generated automatically by the IMAS_VIZ application')
        multiplotFrames = self.view.imas_viz_api.multiPlotsFrames


        #framesElement = ET.SubElement(root, 'frames')

        for frame in multiplotFrames:

            frameElement = ET.SubElement(root, 'frame')

            for key in frame.panels:

                panelElement = ET.SubElement(frameElement, 'panel')
                panelElement.set('key', str(key))

                panel = frame.panels[key]

                panelElement.set('title', panel.conf.title)
                panelElement.set('ylabel', panel.conf.ylabel)
                panelElement.set('y2label', panel.conf.y2label)

                #tracesElement = ET.SubElement(panelElement, 'traces')

                j = 0
                for trace in panel.conf.traces:
                    traceElement = ET.SubElement(panelElement, 'trace')
                    traceElement.set('index', str(j))
                    traceElement.set('color', str(trace.color))
                    j = j + 1

        self.indent(root)
        treeConfiguration = ET.ElementTree(root)
        treeConfiguration.write(fileName, encoding="utf-8", xml_declaration=True)
        #self.f.close()


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
