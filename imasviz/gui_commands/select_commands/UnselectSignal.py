import wx
from imasviz.gui_commands.AbstractCommand import AbstractCommand

class UnselectSignal(AbstractCommand):
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