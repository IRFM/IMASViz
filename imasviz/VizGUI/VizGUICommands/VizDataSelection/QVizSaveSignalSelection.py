#  Name   : SaveSignalSelection.py
#
#          Container to handle saving signal selection configuration.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
# ****************************************************
#     Copyright(c) 2016- L. Fleury,X. Li, D. Penko
# ****************************************************

import time
import xml.etree.ElementTree as ET
from imasviz.VizUtils import QVizGlobalOperations
from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand


class QVizSaveSignalSelection(QVizAbstractCommand):
    """Save signal selection as a list of signal paths to '.lsp' file.

    Arguments:
        dataTreeView (QTreeWidget) : Corresponding DataTreeView.
    """

    def __init__(self, dataTreeView, treeNode=None):
        """Set self.nodeData = nodeData etc. with the use of the
           QVizAbstractCommand
        """
        QVizAbstractCommand.__init__(self, dataTreeView, treeNode)

        self.dataTreeView = dataTreeView

    def execute(self):
        defaultName = 'signalSelection-' + time.strftime('%d-%m-%Y')
        configName = None
        message = 'Type the name of the configuration. \nNote. If left empty ' \
            'the default name \n' + defaultName + '\nwill be used.'
        configName, ok = \
            QVizGlobalOperations.askWithCancel(parent=self.dataTreeView,
                                               title='Dialog',
                                               message=message,
                                               default_value=defaultName)

        # Don't proceed with saving the signal selection if the dialog was
        # cancelled
        if ok == False:
            return

        # Format the configuration file name
        configName = QVizGlobalOperations.replaceSpacesByUnderScores(configName)
        if configName.endswith(".lsp"):
            configName = configName[:-3]

        # Set file name path
        filePath = QVizGlobalOperations.getConfFilePath(configName=configName,
                                                        configType='lsp')
        # Print message
        print('Saving signal selection to ' + filePath)

        # Set root element
        root = ET.Element('SignalSelection')
        root.set('comment', 'This file has been generated automatically by '
                 'the IMASVIZ application. It contains saved signal selection: '
                 'a list of signal paths - IDS database paths to arrays '
                 'containing data suitable for plotting.')

        # Set new subelement
        listElement = ET.SubElement(root, 'ListOfSignalPaths')

        # Get list of signals, selected in the DataTreeView (dataTreeView)
        selectedSignalsDict = self.dataTreeView.selectedSignalsDict

        n = 0
        for key in selectedSignalsDict:

            v = selectedSignalsDict[key]
            vizTreeNode = v['QTreeWidgetItem']

            # Set new subelement
            pathElement = ET.SubElement(listElement, 'IDSPath')
            # Set subelement attribute 'key'
            pathElement.set('key', str(n))

            # Set subelement attribute 'path'
            self.saveAttribute(pathElement, 'path', vizTreeNode.getPath())
            self.saveAttribute(pathElement, 'occurrence', vizTreeNode.getOccurrence())
            # self.saveAttribute(pathElement, 'shotNumber', nodeData['shotNumber'])
            # self.saveAttribute(pathElement, 'runNumber', nodeData['runNumber'])
            # self.saveAttribute(pathElement, 'imasDbName', nodeData['imasDbName'])
            # self.saveAttribute(pathElement, 'userName', nodeData['userName'])
            n += 1

        self.indent(root)
        treeConfiguration = ET.ElementTree(root)
        treeConfiguration.write(filePath, encoding="utf-8", xml_declaration=True)
        #self.f.close()

        if self.dataTreeView.parent.configurationListsWindow != None:
            self.dataTreeView.parent.configurationListsWindow.updateList('lsp')

    def saveAttribute(self, pathElement, attribute, value):
        if value != None:
            pathElement.set(attribute, str(value))

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
