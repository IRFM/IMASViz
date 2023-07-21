import sys
import traceback
import logging
import numpy as np

from imasviz.VizUtils import QVizGlobalOperations, PlotTypes
from imasviz.VizEntities.QVizDataArrayHandle import QVizDataArrayHandle, ArrayCoordinates


class QVizIMASNativeDataAccess:
    def __init__(self, dataSource):
        self.dataSource = dataSource

    def GetSignal(self, treeNode, plotWidget=None, as_function_of_time=None,
                  coordinate_index=0, time_index=None):

        logging.debug("QVizIMASNativeDataAccess::treeNode=" + treeNode.getName())
        if as_function_of_time is None:
            as_function_of_time = \
                treeNode.isPlotToPerformAlongTimeAxis(plotWidget=plotWidget)

        if time_index is None:
            time_index = treeNode.timeValue()
            logging.debug("calling timeValue(), time_index:" + str(time_index))
            
        logging.debug("time_index=" + str(time_index))

        if plotWidget is not None and plotWidget.addTimeSlider:
            time_index = plotWidget.sliderGroup.slider.value()
            logging.debug("calling slider.value(), time_index:" + str(time_index))

        if plotWidget is not None and plotWidget.addCoordinateSlider:
            coordinate_index = plotWidget.sliderGroup.slider.value()

        if as_function_of_time:

            logging.debug("time dependent 1D data...")

            if treeNode.is0DAndDynamic():
                return self.GetSignalVsTime(treeNode, coordinate_index)

            elif treeNode.is1DAndDynamic():
                if treeNode.isCoordinateTimeDependent(coordinateNumber=1):
                    return self.GetSignalAt(treeNode, time_index, plotWidget)
                elif treeNode.embedded_in_time_dependent_aos():
                    return self.GetSignalVsTime(treeNode, coordinate_index)
                else:
                    raise ValueError("Unable to get time dependent signal " +
                                     "for node: " + treeNode.getPath())
            elif treeNode.is2DAndDynamic():
                if treeNode.isCoordinateTimeDependent(coordinateNumber=2):
                    return self.GetSignalAt(treeNode, time_index, plotWidget)
                elif treeNode.embedded_in_time_dependent_aos():
                    return self.GetSignalVsTime(treeNode, coordinate_index)
                else:
                    raise ValueError("Unable to get time dependent signal " +
                                     "for node: " + treeNode.getPath())
        else:
            logging.debug("time independent 1D data...")

            if treeNode.is0DAndDynamic():
                return self.GetSignalAt(treeNode, time_index, plotWidget)
            elif treeNode.is1D():
                logging.debug("calling GetSignalAt @ time_index= " + str(time_index))
                return self.GetSignalAt(treeNode, time_index, plotWidget)
            elif treeNode.is2DAndDynamic():
                return self.GetSignalAt(treeNode, time_index, plotWidget)

    def GetSignalAt(self, treeNode, itimeValue, plotWidget=None):
        if treeNode.is2DAndDynamic():
            return self.GetSignal2DAt(treeNode, itimeValue, plotWidget)
        if treeNode.is1D():
            logging.debug("calling GetSignalAt @ time_ivalue= " + str(itimeValue))
            return self.GetSignal1DAt(treeNode, itimeValue)
        elif treeNode.is0DAndDynamic():
            if plotWidget is not None:
                if plotWidget.getType() == PlotTypes.STACKED_PLOT or \
                        plotWidget.getType() == PlotTypes.TABLE_PLOT:
                    pgPlotItem = plotWidget.getCurrentPlotItem()
                    if pgPlotItem is not None and len(pgPlotItem.dataItems) > 0:
                        xData = pgPlotItem.dataItems[0].xData
                        return self.Get0DSignalVsOtherCoordinate(treeNode,
                                                                 itimeValue,
                                                                 xData)
                elif plotWidget.getType() == PlotTypes.SIMPLE_PLOT:
                    pgPlotItem = plotWidget.pgPlotWidget.plotItem
                    if pgPlotItem is not None and len(pgPlotItem.dataItems) > 0:
                        xData = pgPlotItem.dataItems[0].xData
                        return self.Get0DSignalVsOtherCoordinate(treeNode,
                                                                 itimeValue,
                                                                 xData)
            raise ValueError("Data node '" + treeNode.getName() +
                             "' has no explicit dependency on current X axis.")

    def GetSignal2DAt(self, treeNode, itimeValue, plotWidget=None):

        try:
            if treeNode.getData() is None:
                return

            coordinatesPaths = []
            coordinatesValues = []
            coordinate_of_time = None

            data_entry = self.dataSource.data_entries[treeNode.getOccurrence()]
            arrayPath = 'data_entry.' + treeNode.evaluateDataPath(itimeValue)
            r_val = eval(arrayPath)
            coordinates_labels = []
            label = ''
            quantityName = ''
            for dim in range(1, 3):
                coordinate = treeNode.evaluateCoordinateAt(coordinateNumber=dim,
                                                           itimeValue=itimeValue)

                coordinatesPaths.append(coordinate)

                if treeNode.isCoordinateTimeDependent(coordinateNumber=dim):
                    logging.debug("cooordinate of node '" + treeNode.getName() + "' is time dependent")
                    # coordinate for dimension dim is a function of time
                    coordinateValues = QVizGlobalOperations.getCoordinate_array(data_entry,
                                                                                treeNode.getData(),
                                                                                coordinate)
                    coordinate_of_time = dim
                else:
                    logging.debug("cooordinate of node '" + treeNode.getName() + "' is not time dependent")
                    if "1.." in treeNode.getCoordinate(coordinateNumber=dim):
                        logging.debug("cooordinate of node '" + treeNode.getName() + "' is 1..N")
                        N = len(r_val)
                        coordinateValues = np.asarray(range(0, N))
                    else:
                        logging.debug("cooordinate of node '" + treeNode.getName() + "' is not 1..N")
                        path = "data_entry." + treeNode.getIDSName() + "." + coordinate
                        coordinateValues = eval(path)
                        if len(coordinateValues) == 0:
                            raise ValueError("Coordinate array for dimension " + str(dim) + " has no values.")

                coordinatesValues.append(coordinateValues)
                quantityName, label, coordinate_label = treeNode.labels(plotWidget, dim, coordinate_index=0,
                                                                        time_index=itimeValue)
                coordinates_labels.append(coordinate_label)

            arrayCoordinates = ArrayCoordinates(coordinatesPaths, coordinatesValues, coordinate_of_time,
                                                coordinates_labels)
            return QVizDataArrayHandle(arrayCoordinates, np.asarray(r_val), label=label, name=quantityName,
                                       itimeValue=itimeValue)

        except:
            print(sys.exc_info()[0])
            traceback.print_exc(file=sys.stdout)
            raise

    def GetSignal1DAt(self, treeNode, itimeValue):

        try:
            if treeNode.getData() is None:
                return

            data_entry = self.dataSource.data_entries[treeNode.getOccurrence()]
            signalPath = 'data_entry.' + treeNode.evaluateDataPath(itimeValue)
            logging.debug("signalPath=" + signalPath)
            r_val = eval(signalPath)
            r = np.array([r_val])
            coordinate1 = treeNode.evaluateCoordinateAt(coordinateNumber=1,
                                                        itimeValue=itimeValue)

            if treeNode.isCoordinateTimeDependent(coordinateNumber=1):
                # coordinate1 is a function of time
                logging.debug("cooordinate1 of node '" + treeNode.getName() + "' is time dependent")
                t = QVizGlobalOperations.getCoordinate_array(data_entry,
                                                             treeNode.getData(),
                                                             coordinate1)
                t = np.array([t])
            else:
                logging.debug("cooordinate1 of node '" + treeNode.getName() + "' is not time dependent")
                if "1.." in treeNode.getCoordinate(coordinateNumber=1):
                    logging.debug("cooordinate1 of node '" + treeNode.getName() + "' is 1..N")
                    N = len(r[0])
                    t = np.array([range(0, N)])
                else:
                    logging.debug("cooordinate1 of node '" + treeNode.getName() + "' is not 1..N")
                    path = "data_entry." + treeNode.getIDSName() + "." + \
                           coordinate1
                    logging.debug("path=" + path)
                    e = eval(path)
                    if len(e) == 0:
                        logging.error("Coordinate1 has no values.")
                    if len(e) != 0 and len(e) != len(r_val):
                        path1 = treeNode.getIDSName() + "." + coordinate1
                        raise ValueError(
                            "Coordinate1 (" + path1 + ") array has not the same length than the signal you want to "
                                                      "plot.")
                    t = np.array([e])
                    # print(r)

            return t, r

        except:
            print(sys.exc_info()[0])
            traceback.print_exc(file=sys.stdout)
            raise

    def GetSignalVsTime(self, treeNode, coordinate_index):
        """Function for getting values of dynamic arrays whose values are
        defined in time slices (dynamic AOSs).
        """

        # Set global time
        time = treeNode.getGlobalTimeForArraysInDynamicAOS(self.dataSource)
        treeNode.globalTime = time

        if treeNode.is0DAndDynamic():
            return self.Get0DSignalVsTime(treeNode)
        elif treeNode.is1DAndDynamic():
            # Get list of paths of arrays through time slices
            data_path_list = treeNode.getDataTimeSlices()  # parametrizedPath[0], parametrizedPath[1], ... ,
            # parametrizedPath[itime], ...
            time_slices_count = len(data_path_list)
            v = []
            data_entry = self.dataSource.data_entries[treeNode.getOccurrence()]
            bad_time_values = []
            for i in range(time_slices_count):
                try:
                    # Get values of the array at index
                    value_at_index = eval('data_entry.' + data_path_list[i] + '[' +
                                        str(coordinate_index) + ']')
                    v.append(value_at_index)
                except:
                     bad_time_values.append(i)

            if len(bad_time_values) > 0:
                time = np.delete(time, bad_time_values)
            r_array = np.array([np.array(v)])
            t_array = np.array([time])
            return t_array, r_array
        elif treeNode.is2DAndDynamic:
            raise ValueError('Plotting 2D arrays located in a dynamic AOS is not currently supported')

    def Get0DSignalVsTime(self, treeNode):
        """Function intended for plotting 0D dynamic arrays whose values are
        defined in time slices (dynamic AOSs).
        """
        # Get list of paths of arrays through time slices
        data_path_list = treeNode.getDataTimeSlices()  # parametrizedPath[0], parametrizedPath[1], ... ,
        # parametrizedPath[itime], ...
        data_entry = self.dataSource.data_entries[treeNode.getOccurrence()]
        time_slices_count = len(data_path_list)
        # print "time_slices_count " + str(time_slices_count)
        v = []
        if treeNode.globalTime is None:
            treeNode.globalTime = \
                treeNode.getGlobalTimeForArraysInDynamicAOS(self.dataSource)
        time = treeNode.globalTime
        # Get values of the 0D scalar at each time slice
        bad_time_values = []
        for i in range(time_slices_count):
            try:
               value_at_index = eval('data_entry.' + data_path_list[i])
               v.append(value_at_index)
            except:
               bad_time_values.append(i)

        if len(bad_time_values) > 0:
            time = np.delete(time, bad_time_values)
        r_array = np.array([np.array(v)])
        t_array = np.array([time])
        return t_array, r_array

    def Get0DSignalVsOtherCoordinate(self, treeNode, itimeValue, xData):
        logging.warning("Data node '" + treeNode.getName() +
                        "' has no explicit dependency on coordinate1 dimension.")
        data_path_list = []
        aos_vs_itime = treeNode.evaluatePath(treeNode.getParametrizedDataPath())
        data_entry = self.dataSource.data_entries[treeNode.getOccurrence()]
        data_path = aos_vs_itime.replace("[itime]", "[" + str(itimeValue) + "]")
        value = eval('data_entry.' + data_path)
        for i in range(0, len(xData)):  # constant 1D array
            data_path_list.append(value)
        r_array = np.array([np.array(data_path_list)])
        t_array = np.array([np.array(xData)])
        return t_array, r_array
