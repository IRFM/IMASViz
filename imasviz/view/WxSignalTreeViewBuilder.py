import wx

from WxSignalsTreeView import WxSignalsTreeView


class WxSignalTreeViewBuilder:
    def __init__(self, parent, idsTree):
        self.signalTree = WxSignalsTreeView(parent, idsTree)
        self.buildSignalTree(idsTree)


    def buildSignalTree(self, idsTree):
        signalsList = idsTree.signalsList
        for s in signalsList:
            self.createNode(s, idsTree)


    def createNode(self, child, idsTree):
        childNodeData = idsTree.GetItemData(child)
        isSignal = childNodeData['isSignal']
        path = childNodeData['Path']

        if isSignal == 0:
            return

        itemDataDict = {}
        itemDataDict['idsNode'] = child
        self.signalTree.addNewNode(path, itemDataDict)
