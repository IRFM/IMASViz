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
        self.coordinate1 = None

    def initAttributes(self, vizTreeNode):
        self.createAttributes()
        self.parametrizedPath = vizTreeNode.parametrizedPath
        self.itime_index = vizTreeNode.itime_index  # string
        self.aos_parents_count = vizTreeNode.aos_parents_count  # sring
        self.parameters_values = vizTreeNode.parameters_values  # key = index name ('i', 'j', ...)
        self.parameters_max_values = vizTreeNode.parameters_max_values
        self.coordinate1 = vizTreeNode.coordinate1

    def addParameterValue(self, aos_indice_name, value):
        self.parameters_values[aos_indice_name] = value

    def addMaxParameterValue(self, aos_indice_name, value):
        self.parameters_max_values[aos_indice_name] = value

    def isCoordinateTimeDependent(self, coordinate):
         if coordinate is not None:
             if '/time' in coordinate or '.time' in coordinate or coordinate == 'time':
                return True
         return False

    def isCoordinate1_time_dependent(self):
        return self.infoDict["coordinate1_time_dependent"] == 1

    def time_dependent(self, path):
        if 'itime' in path:
            return True
        return False

    def embedded_in_time_dependent_aos(self):
        return self.time_dependent(self.parametrizedPath)


    def hasTimeXaxis(self, plotWidget):
        if plotWidget is not None:
            if plotWidget.addTimeSlider:
                return False
            elif plotWidget.addCoordinateSlider:
                return True
            elif plotWidget is not None and len(plotWidget.vizTreeNodesList) == 0:
                if self.is1DAndDynamic():
                    if self.isCoordinate1_time_dependent():
                        return True
                    else:
                        return False
                elif self.is0DAndDynamic():
                    return True
            elif plotWidget is not None and len(plotWidget.vizTreeNodesList) > 0:
                firstNode = plotWidget.vizTreeNodesList[0]
                if firstNode.is0DAndDynamic():
                    return True
                elif firstNode.is1DAndDynamic():
                    if firstNode.isCoordinate1_time_dependent():
                        return True
                    else:
                        return False
                else:
                    raise ValueError('Unable to define a time axis')
        else:
            if self.is1DAndDynamic():
                if self.isCoordinate1_time_dependent():
                    return True
                else:
                    return False
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

    def replaceBrackets(self, toReplace): #replace '[' by '(' and ']' by ')'
        c = toReplace.replace("[", "(")
        return c.replace("]", ")")

    def evaluateCoordinate1(self):
        coordinate1 = self.evaluateCoordinate1VsTime()
        if self.time_dependent(self.coordinate1):
            coordinate1 = coordinate1.replace("[itime]", "[" + self.timeValue() + "]")
        return coordinate1

    def evaluateDataPath(self, itime_value):
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

    def evaluateCoordinate1At(self, itimeValue):
        coordinate1 = QVizGlobalOperations.makePythonPath(self.evaluateCoordinate1VsTime())
        if self.time_dependent(self.coordinate1):
            coordinate1 = coordinate1.replace("[itime]", "[" + str(itimeValue) + "]")
        if coordinate1 is None:
            coordinate1 = self.coordinate1
        return coordinate1


    def coordinate1Labels1(self, dtv, index): #index is the coordinate value given by the slider
        # Get time index
        itime_index = self.getItimeIndex()
        title = ''
        xlabel = ''
        if self.coordinate1 == "1..N" or \
                        self.coordinate1 == "1...N":
            title = "coordinate1 = " + str(index)
        else:
            xlabel = str(self.getIDSName() + "." + self.evaluateCoordinate1())
            tokens_list = xlabel.split(".")
            coord1 = tokens_list[-1]
            title = coord1 + "[" + str(itime_index) + "]=" + xlabel
            # Set and format label
        xlabel = QVizGlobalOperations.makeIMASPath(xlabel)
        label = self.setLabelForFigure(dtv.dataSource)
        xlabel = xlabel + '(' + str(index) + ')'
        xlabel = QVizGlobalOperations.makeIMASPath(xlabel)
        label = label.replace('[itime]', '[:]')
        label = label + '(' + str(index) + ')'
        label = QVizGlobalOperations.makeIMASPath(label)
        return label, title, xlabel

    def labelsFor0DData(self, dtv, plotWidget, time_index=None):
        label = None
        xlabel = None
        label = self.setLabelForFigure(dtv.dataSource)
        if self.hasTimeXaxis(plotWidget):
            label = label.replace('itime', str(':'))
            xlabel = 'time[s]'
        else:
            label = label.replace('itime', str(time_index))
        label = QVizGlobalOperations.makeIMASPath(label)
        return label, xlabel

    def labelsFor1DData(self, dtv, plotWidget, time_index=None, coordinate_index=0):
        label = None
        xlabel = None

        label = self.setLabelForFigure(dtv.dataSource)

        if self.coordinate1 == "1..N" or \
                        self.coordinate1 == "1...N":
            xlabel = "1..N"
        else:
            xlabel = self.getIDSName() + "." + self.evaluateCoordinate1VsTime()
            if self.hasTimeXaxis(plotWidget):
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


    def coordinate1Label(self, idsName, index, ids):
        if self.coordinate1 == "1..N" \
                or self.coordinate1 == "1...N":
            return "[" + str(index) + "]"
        to_eval = "ids." + idsName + \
                  "." + self.evaluateCoordinate1() + "[" + str(index) + "]"
        coordinate1_value = eval(to_eval)
        tokens_list = to_eval.split(".")
        coord1 = tokens_list[-1]
        label = coord1 + "=" + str(coordinate1_value)
        return label

    def setLabelForFigure(self, dataSource):
        if self.getOccurrence() == 0:
            return dataSource.getShortLabel() + ":" + self.evaluatePath(self.getParametrizedDataPath())
        else:
            return dataSource.getShortLabel() + ":" + self.evaluatePath(self.getParametrizedDataPath()) \
                   + '[occ=' + str(self.getOccurrence()) + ']'

    def evaluateCoordinate1VsTime(self):#the result can eventually depend on [itime]
        return self.evaluatePath(self.coordinate1)

    def coordinate1Length(self, selectedNodeData, ids):

        if self.coordinate1 == "1..N" or\
                        self.coordinate1 == "1...N":
            r = np.array([eval('ids.' + selectedNodeData['dataName'])])
            return len(r[0])
        # Set python expression to get length of the array
        to_evaluate = 'ids.' + selectedNodeData['IDSName'] + '.' + \
                       self.evaluateCoordinate1()
        len_to_evaluate = eval('len(' + to_evaluate + ')')
        return len_to_evaluate

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

    def getNodeData(self):
        return self.infoDict

    def getParametrizedPath(self):
        # e.g of a parametrized path: 'magnetics.flux_loop[i].position[j]'
        return self.parametrizedPath

    def getParametrizedDataPath(self):
        #e.g of a parametrized path: 'magnetics.flux_loop[i].position[j].r'
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
            for occurrrence in range(0, QVizGlobalValues.MAX_NUMBER_OF_IDS_OCCURRENCES):
                if self.hasIDSAvailableData(occurrrence):
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

    def getCoordinate1(self):
        return self.infoDict.get('coordinate1')

    def getParametrizedCoordinate(self, index):
        searchedCoordinate = 'coordinate' + str(index)
        c = self.infoDict.get(searchedCoordinate)
        if c is not None:
            return QVizGlobalOperations.makePythonPath(c)
        else:
            raise ValueError('Undefined coordinate: ' +  searchedCoordinate)

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


    def plotOptions(self, dataTreeView, shotNumber=None, title='',
                    label=None, xlabel=None, time_index=0, coordinate_index=0, plotWidget=None):
        """Set plot options.

        Arguments:
            dataTreeView (QTreeWidget) : QVizDataTreeView object.
            shotnumber (int) : IDS database parameter - shot number of the case.
            title      (str) : Plot title.
            label      (str) : Label describing IMAS database (device, shot) and
                               path to signal/node in IDS database structure.
            xlabel     (str) : Plot X-axis label.
        """

        if self.is0DAndDynamic():
            label, xlabel = self.labelsFor0DData(dataTreeView, plotWidget, time_index)

        elif self.is1DAndDynamic():
            label, xlabel = self.labelsFor1DData(dataTreeView, plotWidget, time_index, coordinate_index)

        if self.is1DAndDynamic():
            # Setting/Checking the X-axis label
            if xlabel is None:
                # If xlabel is not yet set
                if self.getCoordinate1() is not None:
                    xlabel = QVizGlobalOperations.replaceBrackets(
                        self.getCoordinate1())
                    if self.isCoordinate1_time_dependent() and self.hasHomogeneousTime():
                        xlabel = 'time'

                if xlabel is not None and xlabel.endswith("time"):
                    xlabel += "[s]"
            elif 'time[s]' in xlabel:
                # If 'Time[s]' is present in xlabel, do not modify it
                pass
            elif '1.' not in xlabel and '.N' not in xlabel:
                xlabel = QVizGlobalOperations.makeIMASPath(xlabel)
                # - If IDS name is not present (at the front) of the xlabel string,
                #   then add it
                if self.getIDSName() not in xlabel:
                    xlabel = self.getIDSName() + "/" + xlabel

        ylabel = self.getName()

        if self.getUnits() is not None:
            ylabel += '[' + self.getUnits() + ']'

        return label, xlabel, ylabel, title
