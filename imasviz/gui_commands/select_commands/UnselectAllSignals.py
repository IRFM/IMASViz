import wx
from imasviz.gui_commands.AbstractCommand import AbstractCommand

class UnselectAllSignals(AbstractCommand):
    def __init__(self, view, nodeData = None):
        AbstractCommand.__init__(self, view, nodeData)

    def execute(self):
        keysToRemove = []
        for value in self.view.selectedSignals.values():
            selectedNodeData = value[1]
            for s in self.view.signalsList:
                if selectedNodeData == self.view.GetItemData(s):
                    selectedNodeData['isSelected'] = 0
                    self.view.SetItemTextColour(s, wx.BLUE)
                    key = self.view.dataSource.dataKey(selectedNodeData)
                    keysToRemove.append(key)
                    break
        for i in range(0, len(self.view.selectedSignals)):
            key = keysToRemove[i]
            del self.view.selectedSignals[key]