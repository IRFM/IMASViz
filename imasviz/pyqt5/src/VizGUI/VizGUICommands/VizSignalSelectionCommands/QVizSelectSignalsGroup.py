#  Name   : QVizSelectSignalsGroup
#
#          Container to handle the selection of a group of signals.
#          Note: The wxPython predecessor of this Python file is
#          SelectSignalsGroup.py
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2016- F. Ludovic, L. xinyi, D. Penko
#****************************************************

from imasviz.gui_commands.AbstractCommand import AbstractCommand
from imasviz.util.GlobalValues import GlobalValues
from imasviz.pyqt5.src.VizGUI.VizGUICommands.VizSignalSelectionCommands.QVizSelectSignal \
    import QVizSelectSignal
from imasviz.util.VizServices import VizServices
import re

class QVizSelectSignalsGroup(AbstractCommand):
    """Select a group of all signals - siblings of the node.
    """
    def __init__(self, dataTreeView, nodeData = None):
        """
        Arguments:
            dataTreeView (QTreeWidget) : QTreeWidget object (DTV tree widget).
            nodeData     (array)       : Array of node data.
        """
        AbstractCommand.__init__(self, dataTreeView, nodeData)

    def execute(self):
        #self.updateNodeData()
        key = self.dataTreeView.dataSource.dataKey(self.nodeData)
        aos = self.nodeData['aos']
        aos_parents_count = self.nodeData['aos_parents_count']

        startSigName = self.nodeData['name']

        for signal in self.dataTreeView.signalsList:
            sigName = signal.itemVIZData['name']
            if re.sub("[\(\[].*?[\)\]]", "", startSigName) == re.sub("[\(\[].*?[\)\]]", "", sigName):
                print("* sigName: ", sigName)
                QVizSelectSignal(self.dataTreeView, signal.itemVIZData, treeItem = signal).execute()

        """
        path = aos.replace('self.ids.','').replace('.', '/')
        for i in range(0, int(aos_parents_count) - 1):
            index_name = GlobalValues.indices[str(i+1)]
            index_value = self.nodeData[index_name]
            path = path.replace('[' + index_name + ']', '[' + str(index_value) + ']')

        aos_direct_parent_index_name = GlobalValues.indices[str(aos_parents_count)]
        aos_direct_parent_index_max_value_name = GlobalValues.max_indices[str(aos_parents_count)]
        aos_direct_parent_index_max_value = self.nodeData[aos_direct_parent_index_max_value_name]

        i = 0
        paths_list = []
        while i < int(aos_direct_parent_index_max_value):
            last_aos_index_name = GlobalValues.indices[str(aos_parents_count)]
            last_aos_index_value = self.nodeData[last_aos_index_name]
            list_item = path.replace('[' + last_aos_index_name + ']', '[' + str(i) + ']')
            paths_list.append(list_item.replace('[', '(').replace(']', ')'))
            i += 1

        vizServices = VizServices()
        for path in paths_list:
            rootNodeData = vizServices.getRootNodeData(self.dataTreeView, self.nodeData['IDSName'])
            #nodeData = vizServices.getNodeData(self.dataTreeView, rootNodeData['occurrence'], path)
            #QVizSelectSignal(self.dataTreeView, nodeData).execute()

        #print('paths_list={0}'.format(paths_list))
        #selection_command = SelectSignals(dataTreeView=self.dataTreeView, pathsList=paths_list)
        #selection_command.execute()

        """
