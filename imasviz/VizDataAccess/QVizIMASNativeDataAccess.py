
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

    def GetSignal(self, treeNode):
        return self.GetSignalAt(treeNode, treeNode.timeValue())


    def GetSignalAt(self, treeNode, itimeValue):

        try:
            if treeNode.getNodeData() is None:
                return

            imas_entry = self.dataSource.ids[treeNode.getOccurrence()] #TODO replace ids by imas_entry (confusing!)
            t = None
            signalPath = 'imas_entry.' + treeNode.evaluateDataPath(itimeValue)
            rval = eval(signalPath)

            r = np.array([rval])

            coordinate1 = treeNode.evaluateCoordinate1At(itimeValue)

            if treeNode.isCoordinate1_time_dependent(): #coordinate1 is a function of time
                t = QVizGlobalOperations.getCoordinate1D_array(imas_entry, treeNode.getNodeData(), coordinate1)
                t = np.array([t])
            else:
                if "1..N" in treeNode.treeNodeExtraAttributes.coordinate1 or "1...N" in treeNode.treeNodeExtraAttributes.coordinate1:
                    N = len(r[0])
                    t = np.array([range(0, N)])
                else:
                    path = "imas_entry." + treeNode.getIDSName() + "." + coordinate1
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
    def GetSignalVsTime(self, treeNode, index):
        # Get list of paths of arrays through time slices
        data_path_list = treeNode.getDataVsTime()  # parametrizedPath[0], parametrizedPath[1], ... , parametrizedPath[itime], ...
        # - Add missing part to the end (the name of the array ('phi',
        #   'psi' etc.) is missing
        # TODO: fix 'getDataVsTime' to get full required path
        missing_path_part = '.' + treeNode.getPath().split('/')[-1]
        data_path_list = [x + missing_path_part for x in data_path_list]

        ids = self.dataSource.ids[treeNode.getOccurrence()]
        time_slices_count = len(data_path_list)
        #print "time_slices_count " + str(time_slices_count)
        v = []
        time = QVizGlobalOperations.getGlobalTimeForArraysInDynamicAOS(ids, treeNode.getInfoDict())

        for i in range(0, time_slices_count):
            # Get values of the array at index
            value_at_index = eval('ids.' + data_path_list[i] + '[' + str(index) + ']')
            v.append(value_at_index)

        rarray = np.array([np.array(v)])
        tarray = np.array([time])
        return tarray, rarray

    #this function is used for plotting dynamic arrays whose values are defined in time slices (dynamic AOSs)
    def Get0DSignalVsTime(self, treeNode):

        # Get list of paths of arrays through time slices
        data_path_list = treeNode.getDataVsTime()  # parametrizedPath[0], parametrizedPath[1], ... , parametrizedPath[itime], ...
        # - Add missing part to the end (the name of the array ('phi',
        #   'psi' etc.) is missing
        missing_path_part = '.' + treeNode.getPath().split('/')[-1]
        data_path_list = [x + missing_path_part for x in data_path_list]

        ids = self.dataSource.ids[treeNode.getOccurrence()]
        time_slices_count = len(data_path_list)
        #print "time_slices_count " + str(time_slices_count)
        v = []
        time = QVizGlobalOperations.getGlobalTimeForArraysInDynamicAOS(ids, treeNode.getInfoDict())

        for i in range(0, time_slices_count):# Get values of the 0D scalar at each time slice
            value_at_index = eval('ids.' + data_path_list[i])
            v.append(value_at_index)

        rarray = np.array([np.array(v)])
        tarray = np.array([time])
        return tarray, rarray

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