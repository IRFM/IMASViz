
class AbstractCommand():

    def __init__(self, view, nodeData = None):
        self.view = view
        self.nodeData = nodeData

    def updateNodeData(self):
        self.nodeData = self.view.GetItemData(self.view.selectedItem)
        self.treeNode = self.view.getNodeAttributes(self.nodeData['dataName'])

