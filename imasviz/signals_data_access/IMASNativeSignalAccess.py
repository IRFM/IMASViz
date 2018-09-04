import wx
import imas
import numpy as np
import sys, traceback
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.util.GlobalValues import GlobalValues

class IMASNativeSignalAccess:
    def __init__(self, dataSource):
        self.dataSource = dataSource

    def GetSignal(self,selectedNodeData,shotNumber, treeNode):
        return self.GetSignalAt(selectedNodeData, shotNumber, treeNode, treeNode.timeValue())

    def GetSignalAt(self,selectedNodeData,shotNumber, treeNode, itimeValue):

        try:
            if selectedNodeData == None: return

            coordinate1 = treeNode.evaluateCoordinate1At(itimeValue)

            ids = self.dataSource.ids

            t = None

            rval = eval(selectedNodeData['dataName'])
            r = np.array([rval])

            if selectedNodeData["coordinate1_itime_dependent"] == 1:
                t = GlobalOperations.getTime(ids, selectedNodeData, coordinate1)
                t = np.array([t])
            else:
                if "1..N" in treeNode.coordinate1 or "1...N" in treeNode.coordinate1:
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

            return (t,r)
        except:
            print (sys.exc_info()[0])
            traceback.print_exc(file=sys.stdout)
            #raise ValueError("Error while getting signal " + selectedNodeData['dataName'] + " from native backend.")
            raise


    def GetSignalVsTime(self, data_path_list, selectedNodeData, treeNode, index):
        ids = self.dataSource.ids
        time_slices_count = len(data_path_list)
        #print "IMASNative : time_slices_count " + str(time_slices_count)
        v = []
        time = GlobalOperations.getTime(ids, selectedNodeData, treeNode.evaluateCoordinate1())
        for i in range(0, time_slices_count):
            value_at_index = eval(data_path_list[i] + "[" + str(index) + "]") #evaluate the array at index value
            v.append(value_at_index)

        rarray = np.array([np.array(v)])
        tarray = np.array([time])
        return (tarray, rarray)


    def GetShapeofSignal(self, selectedNodeData, shotNumber):
        try:
            if selectedNodeData == None: return

            ids = self.dataSource.ids

            # eval time
            t = np.array([eval(selectedNodeData['coordinate1'])])

            # eval values
            r = np.array([eval(selectedNodeData['dataName'])])

            return (r.shape, t.shape)

        except:
            # return -1
            raise


if __name__ == "__main__":
    from imasviz.data_source.DataSourceFactory import DataSourceFactory
    dataSource = DataSourceFactory().create(dataSourceName=GlobalValues.IMAS_NATIVE, shotNumber=52702, runNumber=0,
                                          userName='imas_public', imasDbName='west')
    mdsp = IMASNativeSignalAccess(dataSource)
    selectedNodeData = {}
    selectedNodeData['dataName'] = 'dataSource.ids.magnetics.flux_loop[1].flux.data'
    selectedNodeData['time'] = 'dataSource.ids.magnetics.flux_loop[1].flux.time'
    #print (mdsp.GetShapeofSignal(selectedNodeData, 12))
    #treeNode = self.view.getNodeAttributes(self.nodeData['dataName'])
    signal = mdsp.GetSignal(selectedNodeData, dataSource.shotNumber)
    # from imasviz.Browser_API import Browser_API
    app = wx.App()
    # api = Browser_API()
    # api.plotSignal(signal)


