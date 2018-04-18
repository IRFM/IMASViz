import wx
from imasviz.gui_commands.AbstractCommand import AbstractCommand

class SelectOrUnselectSignal(AbstractCommand):
    def __init__(self, view, nodeData = None):
        AbstractCommand.__init__(self, view, nodeData)

    def execute(self):
        self.updateNodeData()
        isSelected = self.nodeData['isSelected']
        key = self.view.dataSource.dataKey(self.nodeData)
        if isSelected == 1:  # If the node is unselected,the text colour is black
            self.view.SetItemTextColour(self.view.selectedItem, wx.BLUE)
            del self.view.selectedSignals[key]
            self.nodeData['isSelected'] = 0
        else:
            self.view.SetItemTextColour(self.view.selectedItem, wx.RED)
            index = len(self.view.selectedSignals) -1 #give the order of user selection
            """Add selected signal to 'selectedSignals list'. Order of parameters:
               shot number, node data, index, shot number, IDS database name,
               user name
            """
            self.view.selectedSignals[key] = (self.view.dataSource.shotNumber,
                                              self.nodeData,
                                              index,
                                              self.view.dataSource.runNumber,
                                              self.view.dataSource.imasDbName,
                                              self.view.dataSource.userName)  # tuple
            self.nodeData['isSelected'] = 1