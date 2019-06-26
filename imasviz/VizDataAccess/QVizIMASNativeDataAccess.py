
import sys
import traceback
import numpy as np
import re
from PyQt5.QtWidgets import QApplication
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues
from imasviz.VizGUI.VizGUICommands.VizPlotting import QVizPlotSignal


class QVizIMASNativeDataAccess:
    def __init__(self, dataSource):
        self.dataSource = dataSource

    def GetSignal(self, selectedNodeData, shotNumber, treeNode):
        return self.GetSignalAt(selectedNodeData, shotNumber, treeNode, treeNode.timeValue())

    def GetSignalAt(self, selectedNodeData, shotNumber, treeNode, itimeValue):

        try:
            if selectedNodeData is None:
                return

            coordinate1 = treeNode.evaluateCoordinate1At(itimeValue)
            ids = self.dataSource.ids[selectedNodeData['occurrence']]
            t = None
            signalPath = 'ids.' + selectedNodeData['dataName']
            idsName = selectedNodeData['IDSName']
            signalPath = signalPath.replace(idsName + '.time_slice[0]', idsName + '.time_slice[' + str(itimeValue) + ']')
            signalPath = signalPath.replace(idsName + '.profiles_1d[0]', idsName + '.profiles_1d[' + str(itimeValue) + ']')
            rval = eval(signalPath)

            r = np.array([rval])

            if selectedNodeData["coordinate1_itime_dependent"] == 1:
                t = QVizGlobalOperations.getTime(ids, selectedNodeData, coordinate1)
                t = np.array([t])
            else:
                if "1..N" in treeNode.treeNodeExtraAttributes.coordinate1 or "1...N" in treeNode.treeNodeExtraAttributes.coordinate1:
                    N = len(r[0])
                    t = np.array([range(0, N)])
                else:
                    path = "ids." + selectedNodeData['IDSName'] + "." + coordinate1
                    e = eval(path)
                    if len(e) == 0:
                        raise ValueError("Coordinate1 has no values.")
                    if len(e) != len(rval):
                        raise ValueError("Coordinate1 array has not the same length than the signal you want to plot.")
                    t = np.array([e])

            return t, r
        except:
            print (sys.exc_info()[0])
            traceback.print_exc(file=sys.stdout)
            #raise ValueError("Error while getting signal " + selectedNodeData['dataName'] + " from native backend.")
            raise

    def GetSignalVsTime(self, data_path_list, selectedNodeData, treeNode, index):
        ids = self.dataSource.ids[selectedNodeData['occurrence']]
        time_slices_count = len(data_path_list)
        #print "IMASNative : time_slices_count " + str(time_slices_count)
        v = []
        time = QVizGlobalOperations.getTime(ids, selectedNodeData, treeNode.evaluateCoordinate1())
        for i in range(0, time_slices_count):
            # Get values of the array at index
            value_at_index = eval('ids.' + data_path_list[i] + '['
                                  + str(index) + ']')
            v.append(value_at_index)

        rarray = np.array([np.array(v)])
        tarray = np.array([time])
        return (tarray, rarray)

    def GetShapeofSignal(self, selectedNodeData, shotNumber):
        try:
            if selectedNodeData == None: return

            ids = self.dataSource.ids[selectedNodeData['occurrence']]

            # eval time
            t = np.array([eval(selectedNodeData['coordinate1'])])

            # eval values
            r = np.array([eval(selectedNodeData['dataName'])])

            return (r.shape, t.shape)

        except:
            # return -1
            raise