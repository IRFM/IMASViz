
class QVizAbstractCommand:

    def __init__(self, dataTreeView, treeNode=None):
        self.dataTreeView = dataTreeView
        if treeNode is not None:
            self.treeNode = treeNode
        else:
            self.treeNode = self.dataTreeView.selectedItem
        self.nodeData = self.treeNode.getData()



