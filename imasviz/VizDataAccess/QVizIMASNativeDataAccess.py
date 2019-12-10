
import sys
import traceback
import logging
import numpy as np
import re

from PyQt5.QtWidgets import QApplication
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues
from imasviz.VizGUI.VizGUICommands.VizPlotting import QVizPlotSignal


class QVizIMASNativeDataAccess:
    def __init__(self, dataSource):
        self.dataSource = dataSource

    def GetSignal(self, treeNode, plotWidget=None, as_function_of_time=None,
                  coordinate_index=0, time_index=None, strategy=None):

        if as_function_of_time is None:
            as_function_of_time = treeNode.asFunctionOfTime(plotWidget=plotWidget,strategy=strategy)

        if time_index is None:
            time_index = treeNode.timeValue()

        if plotWidget is not None and plotWidget.addTimeSlider:
            time_index = plotWidget.sliderGroup.slider.value()

        if plotWidget is not None and plotWidget.addCoordinateSlider:
            coordinate_index = plotWidget.sliderGroup.slider.value()

        if as_function_of_time:
            if treeNode.is0DAndDynamic():
                return self.GetSignalVsTime(treeNode, coordinate_index)
            elif treeNode.is1DAndDynamic():
                if treeNode.isCoordinateTimeDependent(coordinateNumber=1):
                    return self.GetSignalAt(treeNode, time_index, plotWidget)
                elif treeNode.embedded_in_time_dependent_aos():
                    return self.GetSignalVsTime(treeNode, coordinate_index)
                else:
                    raise ValueError('Unable to get time dependent signal for node: ' + treeNode.getPath())
        else:
            if treeNode.is0DAndDynamic():
                return self.GetSignalAt(treeNode, time_index, plotWidget)
            elif treeNode.is1DAndDynamic():
                return self.GetSignalAt(treeNode, time_index, plotWidget)


    def GetSignalAt(self, treeNode, itimeValue, plotWidget=None):
        from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizStackedPlotView import QVizStackedPlotView, StackedPlotWindow
        from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizTablePlotView import QVizTablePlotView
        if treeNode.is1DAndDynamic():
            return self.GetSignal1DAt(treeNode, itimeValue)
        elif treeNode.is0DAndDynamic():
            xData = None
            if plotWidget is not None and isinstance(plotWidget, StackedPlotWindow) \
                    or isinstance(plotWidget, QVizTablePlotView) :
                pgPlotItem = plotWidget.getCurrentPlotItem()
                if pgPlotItem is not None and len(pgPlotItem.dataItems) > 0:
                    xData = pgPlotItem.dataItems[0].xData
                    return self.Get0DSignalVsOtherCoordinate(treeNode, itimeValue, xData)
            elif plotWidget is not None and not isinstance(plotWidget, StackedPlotWindow):
                pgPlotItem = plotWidget.pgPlotWidget.plotItem
                if pgPlotItem is not None and len(pgPlotItem.dataItems) > 0:
                    xData = pgPlotItem.dataItems[0].xData
                    return self.Get0DSignalVsOtherCoordinate(treeNode, itimeValue, xData)
            raise ValueError("Data node '" + treeNode.getName() + "' has no explicit dependency on current X axis.")


    def GetSignal1DAt(self, treeNode, itimeValue):

        try:
            if treeNode.getData() is None:
                return

            imas_entry = self.dataSource.ids[treeNode.getOccurrence()]
            t = None
            signalPath = 'imas_entry.' + treeNode.evaluateDataPath(itimeValue)
            rval = eval(signalPath)
            r = np.array([rval])
            coordinate1 = treeNode.evaluateCoordinateAt(coordinateNumber=1, itimeValue=itimeValue)

            if treeNode.isCoordinateTimeDependent(coordinateNumber=1): #coordinate1 is a function of time
                t = QVizGlobalOperations.getCoordinate1D_array(imas_entry, treeNode.getData(), coordinate1)
                t = np.array([t])
            else:
                if "1..N" in treeNode.getCoordinate(coordinateNumber=1) or \
                                "1...N" in treeNode.getCoordinate(coordinateNumber=1):
                    N = len(r[0])
                    t = np.array([range(0, N)])
                else:
                    path = "imas_entry." + treeNode.getIDSName() + "." + coordinate1
                    e = eval(path)
                    if len(e) == 0:
                        path1 = treeNode.getIDSName() + "." + coordinate1
                        raise ValueError("Coordinate1 has no values.")
                    if len(e) != len(rval):
                        path1 = treeNode.getIDSName() + "." + coordinate1
                        raise ValueError("Coordinate1 (" + path1 + ") array has not the same length than the signal you want to plot.")
                    t = np.array([e])

            return t, r
        except:
            print(sys.exc_info()[0])
            traceback.print_exc(file=sys.stdout)
            raise


    #this function is used for plotting 1D dynamic arrays whose values are defined in time slices (dynamic AOSs)
    def GetSignalVsTime(self, treeNode, index):
        # Set global time
        time = treeNode.getGlobalTimeForArraysInDynamicAOS(self.dataSource)
        treeNode.globalTime = time

        if treeNode.is0DAndDynamic():
            return self.Get0DSignalVsTime(treeNode)
        # Get list of paths of arrays through time slices
        data_path_list = treeNode.getDataTimeSlices()  # parametrizedPath[0], parametrizedPath[1], ... , parametrizedPath[itime], ...
        time_slices_count = len(data_path_list)
        #print "time_slices_count " + str(time_slices_count)
        v = []
        imas_entry = self.dataSource.ids[treeNode.getOccurrence()]
        for i in range(0, time_slices_count):
            # Get values of the array at index
            value_at_index = eval('imas_entry.' + data_path_list[i] + '[' + str(index) + ']')
            v.append(value_at_index)

        rarray = np.array([np.array(v)])
        tarray = np.array([time])
        return tarray, rarray

    # this function is used for plotting 0D dynamic arrays whose values are defined in time slices (dynamic AOSs)
    def Get0DSignalVsTime(self, treeNode):
        # Get list of paths of arrays through time slices
        data_path_list = treeNode.getDataTimeSlices()  # parametrizedPath[0], parametrizedPath[1], ... , parametrizedPath[itime], ...
        ids = self.dataSource.ids[treeNode.getOccurrence()]
        time_slices_count = len(data_path_list)
        # print "time_slices_count " + str(time_slices_count)
        v = []
        if treeNode.globalTime is None:
            treeNode.globalTime = \
                treeNode.getGlobalTimeForArraysInDynamicAOS(self.dataSource)
        time = treeNode.globalTime
        for i in range(0, time_slices_count):  # Get values of the 0D scalar at each time slice
            value_at_index = eval('ids.' + data_path_list[i])
            v.append(value_at_index)

        rarray = np.array([np.array(v)])
        tarray = np.array([time])
        return tarray, rarray

    def Get0DSignalVsOtherCoordinate(self, treeNode, itimeValue, xData):
        logging.warning("Data node '" + treeNode.getName() + "' has no explicit dependency on coordinate1 dimension.")
        data_path_list = []
        aos_vs_itime = treeNode.evaluatePath(treeNode.getParametrizedDataPath())
        imas_entry = self.dataSource.ids[treeNode.getOccurrence()]
        data_path = aos_vs_itime.replace("[itime]", "[" + str(itimeValue) + "]")
        value = eval('imas_entry.' + data_path)
        for i in range(0, len(xData)): #constant 1D array
            data_path_list.append(value)
        rarray = np.array([np.array(data_path_list)])
        tarray = np.array([np.array(xData)])
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