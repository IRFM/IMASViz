
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
        return self.GetSignalAt(treeNode, treeNode.timeValue())

    def GetSignalAt(self, treeNode, itimeValue):

        try:
            if treeNode.getNodeData() is None:
                return

            ids = self.dataSource.ids[treeNode.getOccurrence()]
            t = None
            signalPath = 'ids.' + treeNode.getDataName()
            idsName = treeNode.getIDSName()
            signalPath = signalPath.replace(idsName + '.time_slice[0]', idsName + '.time_slice[' + str(itimeValue) + ']')
            signalPath = signalPath.replace(idsName + '.profiles_1d[0]', idsName + '.profiles_1d[' + str(itimeValue) + ']')
            rval = eval(signalPath)

            r = np.array([rval])

            # Note: patch added while experiencing issues in radiation.process[i].profiles_1d[j]
            if "profiles_1d[j]" in treeNode.infoDict['aos']:
                coordinate1 = treeNode.evaluateCoordinate1At(int(treeNode.infoDict['j']))
            else:
                coordinate1 = treeNode.evaluateCoordinate1At(itimeValue)
            print("*coordinate1: ", coordinate1)

            if  treeNode.isCoordinate1_time_dependent(): #coordinate1 is a function of time
                t = QVizGlobalOperations.getCoordinate1D_array(ids, treeNode.getNodeData(), coordinate1)
                t = np.array([t])
            else:
                if "1..N" in treeNode.treeNodeExtraAttributes.coordinate1 or "1...N" in treeNode.treeNodeExtraAttributes.coordinate1:
                    N = len(r[0])
                    t = np.array([range(0, N)])
                else:
                    path = "ids." + idsName + "." + coordinate1
                    e = eval(path)
                    if len(e) == 0:
                        raise ValueError("Coordinate1 has no values.")
                    if len(e) != len(rval):
                        raise ValueError("Coordinate1 array has not the same length than the signal you want to plot.")
                    t = np.array([e])

            return t, r
        except:
            print(sys.exc_info()[0])
            traceback.print_exc(file=sys.stdout)
            raise

    #this function is used for plotting dynamic arrays whose values are defined in time slices (dynamic AOSs)
    def GetSignalVsTime(self, data_path_list, selectedNodeData, treeNode, index):
        ids = self.dataSource.ids[selectedNodeData['occurrence']]
        time_slices_count = len(data_path_list)
        #print "time_slices_count " + str(time_slices_count)
        v = []
        time = QVizGlobalOperations.getGlobalTimeForArraysInDynamicAOS(ids, selectedNodeData)

        for i in range(0, time_slices_count):
            # Get values of the array at index
            value_at_index = eval('ids.' + data_path_list[i] + '[' + str(index) + ']')
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

            return r.shape, t.shape

        except:
            # return -1
            raise

    #def GetTime(self, selectedNodeData, treeNode):
    #    ids = self.dataSource.ids[selectedNodeData['occurrence']]
    #    time = QVizGlobalOperations.getCoordinate1D_array(ids, selectedNodeData, treeNode.evaluateCoordinate1())
    #    return time