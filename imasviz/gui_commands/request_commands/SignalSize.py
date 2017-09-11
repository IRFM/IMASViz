
from imasviz.gui_commands.AbstractCommand import AbstractCommand

class SelectSignal(AbstractCommand):
    def __init__(self, view, nodeData = None):
        AbstractCommand.__init__(self, view, nodeData)

    def execute(self):
        pass
        
        # def signalSizeRequest(self, event):
    #     try:
    #         if event.GetId() == wx.ID_MORE:
    #             self.updateNodeData();
    #             #selectedNodeData = self.view.GetItemData(self.view.selectedItem)
    #             if 'sizeRequestAlreadyPerformed' in self.nodeData and self.nodeData[
    #                 'sizeRequestAlreadyPerformed'] == 1:
    #                 return
    #             label = self.view.GetItemText(self.view.selectedItem)
    #
    #             signalDataAccess = SignalDataAccessFactory(self.view.dataSource).create()
    #             shape = signalDataAccess.GetShapeofSignal(self.nodeData,
    #                                                                  self.view.dataSource.shotNumber)
    #             self.nodeData['shape'] = shape
    #
    #             resV = ''
    #             vshape = shape[0]
    #             timeshape = shape[1]
    #             cross = ""
    #             for i in range(0, len(vshape)):
    #                 if i == len(vshape) - 1:
    #                     cross = ""
    #                 else:
    #                     cross = " x "
    #                 resV += str(vshape[i]) + cross
    #             resT = ''
    #             for i in range(0, len(timeshape)):
    #                 if i == len(timeshape) - 1:
    #                     cross = ""
    #                 else:
    #                     cross = " x "
    #                 resT += str(timeshape[i]) + cross
    #
    #             label += " Shape= " + resV + ', ' + " (Time shape= " + resT + " )"
    #
    #             self.view.SetItemText(self.view.selectedItem, label)
    #             self.nodeData['sizeRequestAlreadyPerformed'] = 1
    #     except ValueError as e:
    #         self.view.log.error(str(e))
        