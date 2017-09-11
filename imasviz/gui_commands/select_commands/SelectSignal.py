import wx
from imasviz.gui_commands.AbstractCommand import AbstractCommand

class SelectSignal(AbstractCommand):
    def __init__(self, view, nodeData = None):
        AbstractCommand.__init__(self, view, nodeData)

    def execute(self):
        self.updateNodeData();
        key = self.view.dataSource.dataKey(self.nodeData)
        self.nodeData['isSelected'] = 1
        self.view.SetItemTextColour(self.view.selectedItem, wx.RED)
        index = len(self.view.selectedSignals) - 1 #give the order of user selection
        self.view.selectedSignals[key] = (self.view.dataSource.shotNumber, self.nodeData, index)  # tuple