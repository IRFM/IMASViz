
class QVizAbstractCommand:

    def __init__(self, dataTreeView, nodeData = None):
        self.dataTreeView = dataTreeView
        self.nodeData = nodeData

    def updateNodeData(self):
        self.nodeData = self.dataTreeView.selectedItem.itemVIZData
        self.treeNode = self.dataTreeView.getNodeAttributes(self.nodeData['dataName'])


