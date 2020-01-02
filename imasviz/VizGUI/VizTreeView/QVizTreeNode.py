import numpy as np
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues, QVizPreferences, GlobalColors
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QTreeWidgetItem


class QVizTreeNode(QTreeWidgetItem):

    def __init__(self, *args, **kwargs):

        self.globalTime = None
        if len(args) == 0:
            self.createAttributes()
            self.infoDict = {}
            QTreeWidgetItem.__init__(self, None, None)
        elif len(args) == 2:
            self.createAttributes()
            parent = args[0]
            name = args[1]
            self.infoDict = {}
            QTreeWidgetItem.__init__(self, parent, name)
        elif len(args) == 3:
            self.createAttributes()
            parent = args[0]
            name = args[1]
            self.infoDict = args[2]
            QTreeWidgetItem.__init__(self, parent, name)
        elif len(args) == 4:
            parent = args[0]
            name = args[1]
            self.infoDict = args[2]
            self.initAttributes(args[3])
            QTreeWidgetItem.__init__(self, parent, name)

    def createAttributes(self):
        self.parametrizedPath = None
        self.itime_index = None  # string
        self.aos_parents_count = None  # sring
        self.parameters_values = {}  # key = index name ('i', 'j', ...)
        self.parameters_max_values = {}
        self.coordinates = []
        self.coordinates_explicitly_time_dependent = {} #key = coordinate number, value = 0 or 1

    def initAttributes(self, vizTreeNode):
        self.createAttributes()
        self.parametrizedPath = vizTreeNode.parametrizedPath
        self.itime_index = vizTreeNode.itime_index  # string
        self.aos_parents_count = vizTreeNode.aos_parents_count  # sring
        self.parameters_values = vizTreeNode.parameters_values  # key = index name ('i', 'j', ...)
        self.parameters_max_values = vizTreeNode.parameters_max_values
        self.coordinates = vizTreeNode.coordinates
        self.coordinates_explicitly_time_dependent = vizTreeNode.coordinates_explicitly_time_dependent

    def addParameterValue(self, aos_indice_name, value):
        self.parameters_values[aos_indice_name] = value

    def addMaxParameterValue(self, aos_indice_name, value):
        self.parameters_max_values[aos_indice_name] = value

    def isCoordinateTimeDependent(self, coordinateNumber):
        return self.coordinates_explicitly_time_dependent.get(coordinateNumber) == 1

    def time_dependent(self, path):
        if 'itime' in path:
            return True
        return False

    def embedded_in_time_dependent_aos(self):
        return self.time_dependent(self.parametrizedPath)

    def asFunctionOfTime(self, plotWidget, strategy=None):
        as_function_of_time = False
        if strategy is None:
            return self.hasTimeXaxis(plotWidget=plotWidget)
        if strategy == "DEFAULT":
            if self.is0DAndDynamic():
                as_function_of_time = True
            elif self.is1DAndDynamic():
                as_function_of_time = False
        elif strategy == "TIME":
            if self.is0DAndDynamic():
                as_function_of_time = True
            elif self.is1DAndDynamic():
                if self.embedded_in_time_dependent_aos():
                    as_function_of_time = True
                else:
                    as_function_of_time = False
        elif strategy == "COORDINATE1":
            if self.is0DAndDynamic():
                as_function_of_time = True
            elif self.is1DAndDynamic():
                as_function_of_time = False
        return as_function_of_time

    def hasTimeXaxis(self, plotWidget=None):
        if plotWidget is not None:
            if plotWidget.addTimeSlider:
                return False
            elif plotWidget.addCoordinateSlider:
                return True
            elif plotWidget is not None and len(plotWidget.vizTreeNodesList) == 0:
                if self.is1DAndDynamic():
                    return self.isCoordinateTimeDependent(coordinateNumber=1)
                elif self.is0DAndDynamic():
                    return True
            elif plotWidget is not None and len(plotWidget.vizTreeNodesList) > 0:
                firstNode = plotWidget.vizTreeNodesList[0]
                if firstNode.is0DAndDynamic():
                    return True
                elif firstNode.is1DAndDynamic():
                    return firstNode.isCoordinateTimeDependent(coordinateNumber=1)
                else:
                    raise ValueError('Unable to define a time axis')
        else:
            if self.is1DAndDynamic():
                if self.embedded_in_time_dependent_aos():  # 1D Node in dynamic AOS has a time axis
                    return True
                else:
                    return self.isCoordinateTimeDependent(coordinateNumber=1) # 1D node not embedded in dynamic AOS
                                          #has a time axis only if coordinate1 depends on time
            elif self.is0DAndDynamic():
                return True
            else:
                raise ValueError('Unable to define a time axis')


    def index_name_of_itime(self):
        i = 0
        for key in QVizGlobalValues.indices:
            if i == int(self.itime_index):
                return QVizGlobalValues.indices[key]
            i += 1

    def evaluateCoordinate(self, coordinateNumber):
        coordinate = self.evaluateCoordinateVsTime(coordinateNumber)
        if self.time_dependent(self.coordinates[coordinateNumber - 1]):
            coordinate = coordinate.replace("[itime]", "[" + self.timeValue() + "]")
        return coordinate

    def evaluateDataPath(self, itime_value=None):
        parametrizedPath = self.getParametrizedDataPath()
        if parametrizedPath is None:
            return self.getDataName()
        evaluatedPath = parametrizedPath
        if itime_value is not None:
            evaluatedPath = evaluatedPath.replace('[itime]', '[' + str(itime_value) + ']')
        for key in self.parameters_values:
            v = self.parameters_values[key]
            evaluatedPath = evaluatedPath.replace('[' + key + ']', '[' + v + ']')
        return evaluatedPath

    def evaluateCoordinateAt(self, coordinateNumber, itimeValue):
        coordinate = QVizGlobalOperations.makePythonPath(self.evaluateCoordinateVsTime(coordinateNumber))
        if coordinate is None:
            coordinate = self.coordinates[coordinateNumber - 1]
        elif self.time_dependent(self.coordinates[coordinateNumber - 1]):
            coordinate = coordinate.replace("[itime]", "[" + str(itimeValue) + "]")
        return coordinate


    def coordinateLabels(self, coordinateNumber, dtv, index): #index is the coordinate value given by the slider
        # Get time index
        itime_index = self.getItimeIndex()
        title = ''
        xlabel = ''
        if self.coordinates[coordinateNumber-1] == "1..N" or \
                        self.coordinates[coordinateNumber - 1] == "1...N":
            title = "coordinate" + str(coordinateNumber) + " = " + str(index)
        else:
            xlabel = str(self.getIDSName() + "." + self.evaluateCoordinate(1))
            tokens_list = xlabel.split(".")
            coord1 = tokens_list[-1]
            title = coord1 + "[" + str(itime_index) + "]=" + xlabel
        # Set and format label
        xlabel = xlabel + '(' + str(index) + ')'
        xlabel = QVizGlobalOperations.makeIMASPath(xlabel)

        label = self.setLabelForFigure(dtv.dataSource)
        label = label.replace('[itime]', '[:]')
        label = label + '(' + str(index) + ')'
        label = QVizGlobalOperations.makeIMASPath(label)

        return label, title, xlabel

    def itimeEvaluatedLabels(self, dtv, plotWidget, time_index=None, strategy=None):
        label = None
        xlabel = 'time[s]'
        label = self.setLabelForFigure(dtv.dataSource)
        if self.asFunctionOfTime(plotWidget, strategy=strategy):
            label = label.replace('itime', str(':'))
        else:
            label = label.replace('itime', str(time_index))
        label = QVizGlobalOperations.makeIMASPath(label)
        return label, xlabel

    def itimeAndCoordinateAxisEvaluatedLabels(self, coordinateNumber, dtv,
                                              plotWidget,
                                              time_index=None,
                                              coordinate_index=0,
                                              strategy=None):

        label = None
        xlabel = None
        label = self.setLabelForFigure(dtv.dataSource)
        if self.coordinates[coordinateNumber-1] == "1..N" or \
                        self.coordinates[coordinateNumber-1] == "1...N":
            xlabel = "1..N"
        else:
            xlabel = self.getIDSName() + "." + self.evaluateCoordinateVsTime(coordinateNumber=coordinateNumber)
            if self.asFunctionOfTime(plotWidget, strategy=strategy):
                if self.embedded_in_time_dependent_aos():
                    label = label.replace('itime', str(':')) + '[' + str(coordinate_index) + ']'
                else:
                    label = label.replace('itime', str(':'))
                xlabel = 'time[s]'
            else:
                label = label.replace('itime', str(time_index))
                xlabel = xlabel.replace('itime', str(time_index))
                xlabel = QVizGlobalOperations.makeIMASPath(xlabel)

        label = QVizGlobalOperations.makeIMASPath(label)
        return label, xlabel

    def setLabelForFigure(self, dataSource):
        if self.getOccurrence() == 0:
            return dataSource.getShortLabel() + ":" + self.evaluatePath(self.getParametrizedDataPath())
        else:
            return dataSource.getShortLabel() + ":" + self.evaluatePath(self.getParametrizedDataPath()) \
                   + '[occ=' + str(self.getOccurrence()) + ']'

    def evaluateCoordinateVsTime(self, coordinateNumber):#the result can eventually depend on [itime]
        return self.evaluatePath(self.coordinates[coordinateNumber - 1])

    def coordinateLength(self, coordinateNumber, dataTreeView):
        # Set IDS source database
        imas_data_entry = dataTreeView.dataSource.ids[self.getOccurrence()]
        if self.coordinates[coordinateNumber - 1] == "1..N" or\
                        self.coordinates[coordinateNumber - 1] == "1...N":
            r = np.array([eval('imas_data_entry.' + self.getDataName())])
            return len(r[0])
        # Set python expression to get length of the array
        to_evaluate = 'imas_data_entry.' + self.getIDSName() + '.' + \
                       self.evaluateCoordinate(coordinateNumber)
        len_to_evaluate = eval('len(' + to_evaluate + ')')
        return len_to_evaluate

    def coordinateValues(self, coordinateNumber, dataTreeView):
        if len(self.coordinates) < coordinateNumber:
            return None
        # Set IDS data entry
        imas_data_entry = dataTreeView.dataSource.ids[self.getOccurrence()]
        if self.coordinates[coordinateNumber - 1] == "1..N" or\
                        self.coordinates[coordinateNumber - 1] == "1...N":
            return np.array(range(len(eval('imas_data_entry.' + self.getDataName()))))
        to_evaluate = 'imas_data_entry.' + self.getIDSName() + '.' + \
                       self.evaluateCoordinate(coordinateNumber)
        return eval(to_evaluate)

    def getGlobalTimeForArraysInDynamicAOS(self, dataSource):
        imas_entry = dataSource.ids[self.getOccurrence()]
        t = None
        try:
            t = eval("imas_entry." + self.getIDSName() + ".time")
            return t
        except ValueError:
            return None

    def timeMaxValue(self):
        if self.time_dependent(self.parametrizedPath):
            return self.parameters_max_values[self.index_name_of_itime()]

    def timeValue(self):
        if self.time_dependent(self.parametrizedPath):
            return self.parameters_values[self.index_name_of_itime()]


    def getItimeIndex(self):
        i = self.itime_index
        if i is not None:
            return int(i)
        return -1

    def aosParentsCount(self):
        apc = self.aos_parents_count
        if apc is None:
            return 0
        else:
            return int(apc)

    def evaluatePath(self, path):
        aos_valued = path
        path = QVizGlobalOperations.makePythonPath(path)
        path = self.patchIndices(path) #replace [i1] by [i], [i2] by [j] and so on
        for i in range(0, self.aos_parents_count): #loop on all AOSs which contain this path
            index_name = QVizGlobalValues.indices[str(i + 1)]
            index_value = self.parameters_values[index_name] #AOS index value for this node
            s = "[" + index_name + "]"
            aos_valued = path.replace(s, "[" + index_value + "]")
            path = aos_valued
        return aos_valued

    def patchIndices(self, value):
        value = value.replace("[i1]", "[i]")
        value = value.replace("[i2]", "[j]")
        value = value.replace("[i3]", "[k]")
        value = value.replace("[i4]", "[l]")
        value = value.replace("[i5]", "[q]")
        value = value.replace("[i6]", "[r]")
        value = value.replace("[i7]", "[t]")
        return value

    def getDataTimeSlices(self): #return a list of full data path for all time slices
        data_list = []
        aos_vs_itime = self.evaluatePath(self.getParametrizedDataPath())
        #print "QVizTreeNode : time max value = " + self.timeMaxValue()
        for itime in range(0, int(self.timeMaxValue())):
            data_path = aos_vs_itime.replace("[itime]", "[" + str(itime) + "]")
            data_list.append(data_path)
        return data_list

    def getData(self):
        return self.infoDict

    def getParametrizedPath(self):
        # e.g: 'magnetics.flux_loop[i].position[j]'
        return self.parametrizedPath

    def getParametrizedDataPath(self):
        #e.g: 'magnetics.flux_loop[i].position[j].r'
        return self.parametrizedPath + "." + self.getName()

    def getOccurrence(self):
        return self.infoDict.get('occurrence')

    def isIDSRoot(self):
        if self.infoDict.get('isIDSRoot') is not None:
            return self.infoDict.get('isIDSRoot')
        return 0

    def getPath(self):
        return self.infoDict.get('Path')

    def getName(self):
        return self.infoDict.get('name')

    def getDataName(self):
        return self.infoDict.get('dataName')

    def getDocumentation(self):
        return self.infoDict.get('documentation')

    def getInfoDict(self):
        return self.infoDict

    def isDynamicData(self):
        return self.infoDict.get('isSignal')

    def hasAvailableData(self):
        if self.isIDSRoot():
            for occurrence in range(0, QVizGlobalValues.MAX_NUMBER_OF_IDS_OCCURRENCES):
                if self.hasIDSAvailableData(occurrence):
                    return True
            return False
        return self.infoDict.get('availableData') #node is not a root IDS node

    def hasIDSAvailableData(self, occurrence):
        if not self.isIDSRoot():
            raise ValueError('Implementation error: method hasIDSAvailableData(occurrence) should be called for IDS root nodes only.')
        return self.infoDict.get('availableIDSData/' + str(occurrence))

    def getDataType(self):
        return self.infoDict.get('data_type')

    def getUnits(self):
        return self.infoDict.get('units')

    def getPathDoc(self):
        return self.infoDict.get('path_doc')

    def getIDSName(self):
        return self.infoDict.get('IDSName')

    def getShotNumber(self):
        return self.infoDict.get('shotNumber')

    def getCoordinate(self, coordinateNumber):
        if len(self.coordinates) >= coordinateNumber:
            return self.coordinates[coordinateNumber - 1]
        return None

    def getParametrizedCoordinate(self, coordinateNumber):
        searchedCoordinate = 'coordinate' + str(coordinateNumber)
        c = self.coordinates[coordinateNumber - 1]
        if c is not None:
            return QVizGlobalOperations.makePythonPath(c)
        else:
            raise ValueError('Undefined ' +  searchedCoordinate + ".")

    def hasHomogeneousTime(self):
        return self.infoDict.get('homogeneous_time') == 1

    def getHomogeneousTime(self):
        return self.infoDict.get('homogeneous_time')

    def setHomogeneousTime(self, value):
        self.infoDict['homogeneous_time'] = value

    def setPath(self, path):
        self.infoDict['Path'] = path

    def setIDSName(self, idsName):
        self.infoDict['IDSName'] = idsName

    def setDataName(self, dataName):
        self.infoDict['dataName'] = dataName

    def setOccurrence(self, occurrence):
        self.infoDict['occurrence'] = occurrence

    def setAvailableIDSData(self, occurrence, value):
        self.infoDict['availableIDSData/' + str(occurrence)] = value

    def setAvailableData(self, value): #value is True of False
        self.infoDict['availableData'] = value

    def is0D(self):
        return self.getDataType() == 'FLT_0D' or self.getDataType() == 'INT_0D' or self.getDataType() == 'STR_0D' or \
               self.getDataType() == 'flt_0d_type' or self.getDataType() == 'int_0d_type'

    def is1D(self):
        return self.getDataType() == 'FLT_1D' or self.getDataType() == 'INT_1D' or self.getDataType() == 'STR_1D' or \
               self.getDataType() == 'flt_1d_type' or self.getDataType() == 'int_1d_type'

    def is0DString(self):
        return self.getDataType() == 'STR_0D'

    def is0DAndNumeric(self):
        return self.is0D() and self.getDataType() != 'STR_0D'

    def is1DAndNumeric(self):
        return self.is1D() and self.getDataType() != 'STR_1D'

    def is0DAndDynamic(self):
        return self.is0D() and self.isDynamicData()

    def is1DAndDynamic(self):
        return self.is1D() and self.isDynamicData()

    def is2DOrLarger(self):
        if not self.is0D() and not self.is1D() and self.isDynamicData():
            return True

    def updateIDSNode(self, containsData):
        if containsData:
            # Set tree item style when node contains data
            self.setStyleForIDS(True)
        else:
            # Set tree item text color
            self.setStyleForIDS(False)

    def setStyleForIDS(self, containsData):
        if containsData:
            self.setForeground(0, QVizPreferences.ColorOfNodesContainingData)
            self.setFontBold()
        else:
            self.setForeground(0, GlobalColors.BLACK)

    def setStyleWhenContainingData(self):
        self.setForeground(0, QVizPreferences.ColorOfNodesContainingData)
        self.parent().setForeground(0, self.foreground(0))  # set the parent colour to the same colour
        if self.isDynamicData(): #set dynamic data to bold (0D and 1D nodes)
            self.setFontBold()

    def setStyleForWhenNotContainingData(self):
        self.setForeground(0, GlobalColors.BLACK)

    def setStyleForAOSContainingData(self):
        self.setForeground(0, QVizPreferences.ColorOfNodesContainingData)

    def setStyleForElementAOS(self):
        self.setForeground(0, QVizPreferences.ColorOfNodesContainingData)
        self.parent().setForeground(0, self.foreground(0))  # set the parent colour to the same colour

    def setStyleForAOSNotContainingData(self):
        self.setForeground(0, GlobalColors.BLACK)

    def setStyleWhenSelected(self):
        self.setForeground(0, QVizPreferences.SelectionColor)

    def setFontBold(self):
        font = QFont()
        font.setBold(True)
        self.setFont(0, font)

    # Define the color of a node which contains a signal
    def updateStyle(self, imas_entry):

        if self.is1D():

            # And error occurs for non-homogeneous cases (time array is
            # different or empty). This is 'solved' with the below fix using
            # 'e' variable
            e = eval('imas_entry.' + self.getDataName())
            if e is None or e.all() is None:
                self.setAvailableData(0)
                self.setStyleForWhenNotContainingData()
            elif len(eval('imas_entry.' + self.getDataName())) == 0:  # empty (signals) arrays appear in black
                self.setAvailableData(0)
                self.setStyleForWhenNotContainingData()
            else:
                self.setAvailableData(1)
                self.setStyleWhenContainingData()

        elif self.is0D():
            # And error occurs for non-homogeneous cases (time array is
            # different or empty). This is 'solved' with the below fix using
            # 'e' variable
            if self.getDataName() is None:
                self.setStyleForWhenNotContainingData()
                return

            e = eval('imas_entry.' + self.getDataName())

            emptyField = False
            if self.getDataType() == 'FLT_0D' or self.getDataType() == 'flt_0d_type':
                if e == -9.0E40:
                    emptyField = True

            elif self.getDataType() == 'INT_0D' or self.getDataType() == 'int_0d_type':
                if e == -999999999:
                    emptyField = True

            elif self.getDataType() == 'STR_0D':
                if e == '':
                    emptyField = True

            if emptyField:  # empty (signals) arrays appear in black
                self.setAvailableData(0)
                self.setStyleForWhenNotContainingData()
            else:
                self.setAvailableData(1)
                self.setStyleWhenContainingData()


        elif self.is2DOrLarger():
            e = eval('imas_entry.' + self.getDataName())
            if e.shape[0] == 0:
                self.setAvailableData(0)
                self.setStyleForWhenNotContainingData()
            else:
                self.setAvailableData(1)
                self.setStyleWhenContainingData()

            self.parent().setForeground(0, self.foreground(0))  # set the parent colour to the same colour
        else:
            #self.setForeground(0, GlobalColors.BLACK)
            self.parent().setForeground(0, self.foreground(0))


    def plotOptions(self, dataTreeView, title='', label=None, xlabel=None,
                    time_index=0, coordinate_index=0, plotWidget=None, strategy=None):
        """Set plot options.

        Arguments:
            dataTreeView (QTreeWidget) : QVizDataTreeView object.
            title      (str) : Plot title.
            label      (str) : Label describing IMAS database (device, shot) and
                               path to signal/node in IDS database structure.
            xlabel     (str) : Plot X-axis label.
        """

        if self.is0DAndDynamic():
            label, xlabel = self.itimeEvaluatedLabels(dataTreeView, plotWidget, time_index, strategy=strategy)

        elif self.is1DAndDynamic():
            label, xlabel2 = self.itimeAndCoordinateAxisEvaluatedLabels(1, dataTreeView,
                                                                       plotWidget,
                                                                       time_index,
                                                                       coordinate_index,
                                                                       strategy=strategy)
            if xlabel is None:
                xlabel = xlabel2
            # Setting/Checking the X-axis label
            # if xlabel is None:
            #     # If xlabel is not yet set
            #     if self.getCoordinate(coordinateNumber=1) is not None:
            #         xlabel = QVizGlobalOperations.replaceBrackets(
            #             self.getCoordinate(coordinateNumber=1))
            #         if self.isCoordinateTimeDependent() and self.hasHomogeneousTime():
            #             xlabel = 'time'
            #
            #     if xlabel is not None and xlabel.endswith("time"):
            #         xlabel += "[s]"
            # elif 'time[s]' in xlabel:
            #     # If 'Time[s]' is present in xlabel, do not modify it
            #     pass
            # elif '1.' not in xlabel and '.N' not in xlabel:
            #     xlabel = QVizGlobalOperations.makeIMASPath(xlabel)
            #     # - If IDS name is not present (at the front) of the xlabel string,
            #     #   then add it
            #     if self.getIDSName() not in xlabel:
            #         xlabel = self.getIDSName() + "/" + xlabel

        ylabel = self.getName()

        if self.getUnits() is not None:
            ylabel += '[' + self.getUnits() + ']'

        return label, xlabel, ylabel, title