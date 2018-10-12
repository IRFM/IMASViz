#  Name   : SaveSignalSelection.py
#
#          Container to handle saving signal selection configuration.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic,L.xinyi, D. Penko
#****************************************************

import os
from imasviz.gui_commands.AbstractCommand import AbstractCommand
from imasviz.util.GlobalOperations import GlobalOperations
import xml.etree.ElementTree as ET

class SaveSignalSelection(AbstractCommand):
    """Save signal selection as a list of signal paths to '.lsp' file.
    """

    def __init__(self, DTV, nodeData=None):
        """Set self.nodeData = nodeData etc. with the use of the
           AbstractCommand
        """
        AbstractCommand.__init__(self, nodeData)

        self.DTV = DTV

    def execute(self):
        default_file_name = ""
        configName = None
        cancel = None
        loop = True
        configName = \
            GlobalOperations.askWithCancel(parent=self.DTV,
                                           title='Dialog',
                                           message='Type the name of the configuration',
                                           default_value=default_file_name)
        # while loop:
            # x = GlobalOperations.askWithCancel(message='Name of the configuration ?',
            #                                    default_value=default_file_name)
        #     cancel = x[0]
            # configName = x[1]
        #     if cancel != wx.CANCEL and (x == None or x == ""):
        #         x = GlobalOperations.showMessage(message='Please give a name to the configuration')
        #     else:
        #         loop = False

        # if (cancel == wx.CANCEL):
        #     return

        configName = GlobalOperations.replaceSpacesByUnderScores(configName)
        if configName.endswith(".lsp"):
            configName = configName[:-3]

        # Set file name
        fileName = GlobalOperations.getConfFilePath(configName=configName,
                                                    configType='lsp')

        # Set root element
        root = ET.Element('SignalSelection')
        root.set('comment', 'This file has been generated automatically by '
                 'the IMAS_VIZ application. It contains saved signal selection: '
                 'a list of signal paths - IDS database paths to arrays '
                 'containing data suitable for plotting.')

        # Set new subelement
        listElement = ET.SubElement(root, 'ListOfSignalPaths')

        # Get list of signals, selected in the WxDataTreeView
        # selectedsignalsList = \
        #     GlobalOperations.getSortedSelectedSignals(self.DTV.selectedSignals)
        selectedsignalsList = self.DTV.selectedSignalsDict

        # TODO
        # for n in range(0, len(selectedsignalsList)):

        #     key = n

        #     # Set new subelement
        #     pathElement = ET.SubElement(listElement, 'IDSPath')
        #     # Set subelement attribute 'key'
        #     pathElement.set('key', str(key))

        #     # Extract signal node data (it contains also 'path') from the
        #     # signal
        #     selectedArray = selectedsignalsList[n]
        #     nodeData = selectedArray[1]

        #     # Set subelement attribute 'path'
        #     self.saveAttribute(pathElement, 'path', nodeData['Path'])

        #     # self.saveAttribute(pathElement, 'shotnum', selectedArray[0])
        #     # self.saveAttribute(pathElement, 'runnum', selectedArray[3])
        #     # self.saveAttribute(pathElement, 'database', selectedArray[4])
        #     # self.saveAttribute(pathElement, 'username', selectedArray[5])

        # self.indent(root)
        # treeConfiguration = ET.ElementTree(root)
        # treeConfiguration.write(fileName, encoding="utf-8", xml_declaration=True)
        # #self.f.close()

        # if self.DTV.parent.configurationListsFrame != None:
        #     self.DTV.parent.configurationListsFrame.update_lsp()

    def saveAttribute(self, pathElement, attribute, value):
        if value != None:
            pathElement.set(attribute, str(value))

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
