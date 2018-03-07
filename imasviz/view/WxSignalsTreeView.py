import wx

from imasviz.gui_commands.SignalHandling import SignalHandling


class WxSignalsTreeView(wx.TreeCtrl):

    def __init__(self, parent, idsTree, *args, **kwargs):
        super(WxSignalsTreeView, self).__init__(parent, style=wx.TR_DEFAULT_STYLE | wx.TR_LINES_AT_ROOT)
        self.signalsRoot = self.AddRoot('signals')
        self.idsTree = idsTree

    def addNewNode(self,path,treeData):
        signalNode = self.AppendItem( self.signalsRoot, path, -1, -1,
                                               treeData)
        return signalNode

    def selectNodeWithPath(self, searchedPath):
        # print 'searchedPath ', searchedPath
        child, cookie = self.GetFirstChild(self.signalsRoot)
        lastChild = self.GetLastChild(self.signalsRoot)
        if not child.IsOk():
            print ('No signals available')
            return

        signalHandling = SignalHandling(self.idsTree)
        while True:
            itemSignalsDataDict = self.GetItemData(child)
            idsNode = itemSignalsDataDict['idsNode']
            data = self.idsTree.GetItemData(idsNode)
            path = data['Path']
            #print ('existing path :' + path)
            if path == searchedPath:
                # print 'found path : ' + path
                # print idsNode
                self.idsTree.setSelectedItem(idsNode)
                signalHandling.selectSignal()
                return idsNode
            if child == lastChild:
                #print 'path not found --> ' + path
                return None
            child, cookie = self.GetNextChild(self.signalsRoot, cookie)


class IDSSignalTreeFrame(wx.Frame):
    def __init__(self, parent, idsTree, shot, IDSDefFile, *args, **kwargs):
        from imasviz.view.WxSignalTreeViewBuilder import WxSignalTreeViewBuilder
        super(IDSSignalTreeFrame, self).__init__(parent, *args, **kwargs)
        self.SetTitle("IMAS Signals tree for shot : " + shot)
        s = WxSignalTreeViewBuilder(self, idsTree)
        self.tree = s.signalTree
        self.Bind(wx.EVT_CLOSE, self.onClose)

    def onClose(self, event):
        event.Skip()
