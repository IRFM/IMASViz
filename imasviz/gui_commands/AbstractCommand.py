
class AbstractCommand():

    def __init__(self, dataTreeView, nodeData = None):
        self.dataTreeView = dataTreeView
        self.nodeData = nodeData
        # Old wx variable label. Remove when obsolete
        self.view = dataTreeView

    def updateNodeData(self):
        self.nodeData = self.dataTreeView.selectedItem.itemVIZData
        self.treeNode = self.dataTreeView.getNodeAttributes(self.nodeData['dataName'])

        # # Old wx variable label. Remove when obsolete
        self.nodeData = self.view.selectedItem.itemVIZData
        self.treeNode = self.view.getNodeAttributes(self.nodeData['dataName'])


