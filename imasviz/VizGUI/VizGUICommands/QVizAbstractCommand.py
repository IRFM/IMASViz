
class QVizAbstractCommand:

    def __init__(self, dataTreeView, nodeData = None):
        self.dataTreeView = dataTreeView
        self.nodeData = nodeData

    def updateNodeData(self):
        self.treeNode = self.dataTreeView.selectedItem
        self.nodeData = self.dataTreeView.selectedItem.dataDict


