import wx
from imasviz.gui_commands.AbstractCommand import AbstractCommand
from imasviz.util.GlobalValues import GlobalValues
from imasviz.gui_commands.select_commands.SelectSignal import SelectSignal
from imasviz.util.VizServices import VizServices

class SelectSignalsGroup(AbstractCommand):
    """Select a group of all signals - siblings of the node.
    """
    def __init__(self, view, nodeData = None):
        """
        Arguments:
            view     (obj)   : wxTreeView object of the wxDataTreeViewFrame.
            nodeData (array) : Array of node data.
        """
        AbstractCommand.__init__(self, view, nodeData)

    def execute(self):
        #self.updateNodeData()
        key = self.view.dataSource.dataKey(self.nodeData)
        aos = self.nodeData['aos']
        aos_parents_count = self.nodeData['aos_parents_count']

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
            rootNodeData = vizServices.getRootNodeData(self.view, self.nodeData['IDSName'])
            nodeData = vizServices.getNodeData(self.view, rootNodeData['occurrence'], path)
            SelectSignal(self.view, nodeData).execute()

        #print('paths_list={0}'.format(paths_list))



        #selection_command = SelectSignals(view=self.view, pathsList=paths_list)
        #selection_command.execute()
