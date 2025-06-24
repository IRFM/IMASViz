# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import numpy as np
import logging
from imasviz.VizUtils import (QVizGlobalOperations, QVizGlobalValues,
                              QVizPreferences, GlobalColors)
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QTreeWidgetItem


class QVizTreeNode(QTreeWidgetItem):

    def __init__(self, *args, **kwargs):

        self.globalTime = None
        self.dataTreeView = None
        self.occurrenceEntry = False
        self.ids_is_dynamic = False
        self.idsRef = None
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

    def getDataTreeView(self):
        p = self
        while p.dataTreeView is None:
            p = p.parent()
        return p.dataTreeView

    def getDataSource(self):
        return self.getDataTreeView().dataSource

    def getOccurrenceRootNode(self):
        p = self
        if p.occurrenceEntry:
            return p
        if p.parent() is None:
            return None
        p = p.parent()
        while p is not None:
            if p.occurrenceEntry:
                return p
            p = p.parent()
        return None

    def createAttributes(self):
        self.parametrizedPath = None
        self.itime_index = None  # string
        self.aos_parents_count = None  # sring
        self.parameters_values = {}  # key = index name ('i', 'j', ...)
        self.parameters_max_values = {}
        self.coordinates = []
        self.coordinates_explicitly_time_dependent = {}  # key = coordinate number, value = 0 or 1
        self.default_coordinates = {} #index = coordinate number, value = value extracted from DD

    def initAttributes(self, vizTreeNode):
        self.createAttributes()
        self.parametrizedPath = vizTreeNode.parametrizedPath
        self.itime_index = vizTreeNode.itime_index  # string
        self.aos_parents_count = vizTreeNode.aos_parents_count  # sring
        self.parameters_values = vizTreeNode.parameters_values  # key = index name ('i', 'j', ...)
        self.parameters_max_values = vizTreeNode.parameters_max_values
        self.coordinates = vizTreeNode.coordinates
        self.default_coordinates = vizTreeNode.default_coordinates
        self.coordinates_explicitly_time_dependent = vizTreeNode.coordinates_explicitly_time_dependent

    def setOccurrenceEntry(self, value):
        self.occurrenceEntry = value

    def isOccurrenceEntry(self):
        return self.occurrenceEntry is True

    def setParameterValue(self, aos_indice_name, value):
        self.parameters_values[aos_indice_name] = value

    def setMaxParameterValue(self, aos_indice_name, value):
        self.parameters_max_values[aos_indice_name] = value

    def setCoordinate(self, coordinateNumber, value):
        self.coordinates[coordinateNumber - 1] = value
        if value.endswith('/time') or value.endswith('.time') or value == 'time':
            self.coordinates_explicitly_time_dependent[coordinateNumber] = 1
        else:        
            self.coordinates_explicitly_time_dependent[1] = 0
        for i in range(self.childCount()):
            child = self.child(i)
            if child.text(0).startswith('coordinate1'):
                child.setText(0, 'coordinate1=' + value)
                break

    def setDefaultCoordinate(self, coordinateNumber):
        coordinate = self.default_coordinates.get(coordinateNumber - 1)
        if coordinate is not None:
            self.coordinates[coordinateNumber - 1] = coordinate
            if coordinate.endswith('/time') or coordinate.endswith('.time') or coordinate == 'time':
                self.coordinates_explicitly_time_dependent[coordinateNumber] = 1
            else:
                self.coordinates_explicitly_time_dependent[1] = 0
            for i in range(self.childCount()):
                child = self.child(i)
                if child.text(0).startswith('coordinate1'):
                    child.setText(0, 'coordinate1=' + coordinate)
                    break

    def isCoordinateTimeDependent(self, coordinateNumber):
        return self.coordinates_explicitly_time_dependent.get(coordinateNumber) == 1

    def time_dependent(self, path):
        if 'itime' in path:
            return True
        return False

    def embedded_in_time_dependent_aos(self):
        return self.time_dependent(self.parametrizedPath)

    def hasTimeAxis(self):
        if self.is0DAndDynamic():
            return True
        elif self.is1DAndDynamic():
            if self.embedded_in_time_dependent_aos() or self.isCoordinateTimeDependent(coordinateNumber=1):
                return True
        elif self.is2DAndDynamic():
            if self.embedded_in_time_dependent_aos() or self.isCoordinateTimeDependent(coordinateNumber=2):
                return True
        return False

    def isPlotToPerformAlongTimeAxis(self, plotWidget):

        if plotWidget is None:
            return self.hasTimeAxis()
        #print('isPlotToPerformAlongTimeAxis::plotWidget.getPlotAxis()=', plotWidget.getPlotAxis())
        if plotWidget.getPlotAxis() == "TIME":
            return self.hasTimeAxis()
        elif plotWidget.getPlotAxis() == "DEFAULT" or plotWidget.getPlotAxis() == "COORDINATE1":
            if self.is0DAndDynamic():
                return True
            elif self.is1DAndDynamic():
                return False

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

    def coordinateLabels(self, coordinateNumber, dtv, index):  # index is the coordinate value given by the slider
        # Get time index
        itime_index = self.getItimeIndex()
        title = ''
        xlabel = ''
        if self.coordinates[coordinateNumber - 1] == "1..N" or \
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

    def setLabelForFigure(self, dataSource):
        if self.getOccurrence() == 0:
            return dataSource.getShortLabel() + ":" + self.evaluatePath(self.getParametrizedDataPath())
        else:
            return dataSource.getShortLabel() + ":" + self.evaluatePath(self.getParametrizedDataPath()) \
                   + '[occ=' + str(self.getOccurrence()) + ']'

    def evaluateCoordinateVsTime(self, coordinateNumber):  # the result can eventually depend on [itime]
        return self.evaluatePath(self.coordinates[coordinateNumber - 1])

    def coordinateLength(self, coordinateNumber, dataTreeView):
        # Set IDS source database
        if self.coordinates[coordinateNumber - 1] == "1..N" or \
                self.coordinates[coordinateNumber - 1] == "1...N":
            r = np.array([self.evalPath(self.getDataName())])
            return len(r[0])
        # Set python expression to get length of the array
        to_evaluate = self.getIDSName() + '.' + self.evaluateCoordinate(coordinateNumber)
        len_to_evaluate = self.evalPath('len(' + to_evaluate + ')')
        return len_to_evaluate

    def coordinateValues(self, coordinateNumber, dataTreeView):
        if len(self.coordinates) < coordinateNumber:
            return None
        # Set IDS data entry
        if self.coordinates[coordinateNumber - 1] == "1..N" or \
                self.coordinates[coordinateNumber - 1] == "1...N":
            return np.array(range(len(self.evalPath(self.getDataName()))))
        to_evaluate = self.getIDSName() + '.' + self.evaluateCoordinate(coordinateNumber)
        return self.evalPath(to_evaluate)

    def getGlobalTimeForArraysInDynamicAOS(self):
        t = None
        try:
            t = self.evalPath(self.getIDSName() + ".time")
            return t
        except ValueError:
            return None

    def timeMaxValue(self):
        if self.time_dependent(self.parametrizedPath):
            return self.parameters_max_values[self.index_name_of_itime()]

    def timeValue(self):
        time_index = 0
        if self.time_dependent(self.parametrizedPath):
            time_index = self.parameters_values[self.index_name_of_itime()]
        return time_index

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
        path = self.patchIndices(path)  # replace [i1] by [i], [i2] by [j] and so on
        for i in range(0, self.aos_parents_count):  # loop on all AOSs which contain this path
            index_name = QVizGlobalValues.indices[str(i + 1)]
            index_value = self.parameters_values[index_name]  # AOS index value for this node
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

    def getDataTimeSlices(self):  # return a list of full data path for all time slices
        data_list = []
        aos_vs_itime = self.evaluatePath(self.getParametrizedDataPath())
        # print "QVizTreeNode : time max value = " + self.timeMaxValue()
        for itime in range(0, int(self.timeMaxValue())):
            data_path = aos_vs_itime.replace("[itime]", "[" + str(itime) + "]")
            data_list.append(data_path)
        return data_list

    def getIDSRef(self):
        return self.idsRef

    def getData(self):
        return self.infoDict

    def getParametrizedPath(self):
        # e.g: 'magnetics.flux_loop[i].position[j]'
        return self.parametrizedPath

    def getParametrizedDataPath(self):
        # e.g: 'magnetics.flux_loop[i].position[j].r'
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
        return self.infoDict.get('isSignal') == 1 and not self.isStaticData()

    def isStaticData(self):
        return self.infoDict.get('isStatic')

    def hasAvailableData(self):
        import imas
        if self.isIDSRoot():
            if self.getDataTreeView() is None:
                return False
            maxOccurrences = eval("imas." + self.getIDSName() + "().getMaxOccurrences()")
            for occurrence in range(0, maxOccurrences):
                if self.hasIDSAvailableData(occurrence):
                    return True
            return False
        return self.infoDict.get('availableData')  # node is not a root IDS node

    def hasIDSAvailableData(self, occurrence):
        if not self.isIDSRoot():
            raise ValueError(
                'Implementation error: method hasIDSAvailableData(occurrence) should be called for IDS root nodes only.')
        return self.infoDict.get('availableIDSData/' + str(occurrence))

    def getDataType(self):
        return self.infoDict.get('data_type')

    def getUnits(self):
        return self.infoDict.get('units')

    def getPathDoc(self):
        return self.infoDict.get('path_doc')

    def getIDSName(self):
        return self.infoDict.get('IDSName')

    def getURI(self):
        return self.infoDict.get('URI')

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
            raise ValueError('Undefined ' + searchedCoordinate + ".")

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

    def setIDSIsDynamic(self, ids_is_dynamic):
        root_node_occ = self.getOccurrenceRootNode()
        if root_node_occ is None:
            raise ValueError("Node " + self.getName() + " has no occurrence root!")
        root_node_occ.ids_is_dynamic = ids_is_dynamic

    def isIDSDynamic(self):
        root_node_occ = self.getOccurrenceRootNode()
        if root_node_occ is None:
            raise ValueError("Node " + self.getName() + " has no occurrence root!")
        return root_node_occ.ids_is_dynamic

    def setDataName(self, dataName):
        self.infoDict['dataName'] = dataName

    def setOccurrence(self, occurrence):
        self.infoDict['occurrence'] = occurrence

    def setAvailableIDSData(self, occurrence, value):
        self.infoDict['availableIDSData/' + str(occurrence)] = value

    def setAvailableData(self, value):  # value is True of False
        self.infoDict['availableData'] = value

    def isStructure(self):
        return self.getDataType() == 'structure'

    def isArrayOfStructure(self):
        return self.getDataType() == 'struct_array'

    def is0D(self):
        return self.getDataType() == 'FLT_0D' or self.getDataType() == 'INT_0D' or self.getDataType() == 'STR_0D' or \
               self.getDataType() == 'flt_type' or self.getDataType() == 'int_type' or \
               self.getDataType() == 'CPX_0D' or self.getDataType() == 'cpx_type'

    def is1D(self):
        return self.getDataType() == 'FLT_1D' or self.getDataType() == 'INT_1D' or self.getDataType() == 'STR_1D' or \
               self.getDataType() == 'flt_1d_type' or self.getDataType() == 'int_1d_type' or \
               self.getDataType() == 'CPX_1D' or self.getDataType() == 'cplx_1d_type'

    def is2D(self):
        return self.getDataType() == 'FLT_2D' or self.getDataType() == 'INT_2D' or \
               self.getDataType() == 'flt_2d_type' or self.getDataType() == 'int_2d_type' or \
               self.getDataType() == 'CPX_2D' or self.getDataType() == 'cplx_2d_type'

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

    def is2DAndDynamic(self):
        return self.is2D() and self.isDynamicData()

    def is2DOrLarger(self):
        if not self.is0D() and not self.is1D() and self.isDynamicData():
            return True

    def hasClosedOutline(self, dtv):
        if not self.is1D():
            return False
        if self.coordinates[0] == "1..N" or \
                self.coordinates[0] == "1...N":
            return False
        tokens = str(self.getPath()).split("/")
        if not (len(tokens) > 1 and tokens[-2].startswith('outline')):
            return False
        closedOutlinePath = self.getPath().replace("/" + tokens[-1], "", 1);
        closedOutlinePath = closedOutlinePath.replace("/" + tokens[-2], "", 1) + "/closed";
        #expression = 'dtv.dataSource.data_entries[' + str(self.getOccurrence()) + '].' + closedOutlinePath
        expression = closedOutlinePath
        value = self.evalPath(QVizGlobalOperations.makePythonPath(expression))
        return value

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
        if self.isDynamicData():  # set dynamic data to bold (0D and 1D nodes)
            self.setFontBold()

    def setStyleForWhenNotContainingData(self):
        self.setForeground(0, GlobalColors.BLACK)

    def setStyleForAOSContainingData(self):
        self.setForeground(0, QVizPreferences.ColorOfNodesContainingData)

    def setStyleForElementAOS(self):
        self.setForeground(0, QVizPreferences.ColorOfNodesContainingData)

    def setStyleForAOSNotContainingData(self):
        self.setForeground(0, GlobalColors.BLACK)

    def setStyleWhenSelected(self):
        self.setForeground(0, QVizPreferences.SelectionColor)

    def setFontBold(self):
        font = QFont()
        font.setBold(True)
        self.setFont(0, font)

    # Define the color of a node which contains a signal
    def updateStyle(self):

        if self.getIDSRef() is not None and self.getIDSName() is not None:
            exec(self.getIDSName() + " = self.getIDSRef()")
        
        if self.is1D():

            # And error occurs for non-homogeneous cases (time array is
            # different or empty). This is 'solved' with the below fix using
            # 'e' variable
            e = self.evalPath(self.getDataName())
            #print(e)
            if self.getDataType() != 'STR_1D' and (e is None or e.all() is None):
                self.setAvailableData(0)
                self.setStyleForWhenNotContainingData()
            elif len(self.evalPath(self.getDataName())) == 0:  # empty (signals) arrays appear in black
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

            e = self.evalPath(self.getDataName())

            emptyField = False
            if self.getDataType() == 'FLT_0D' or self.getDataType() == 'flt_type':
                if e == -9.0E40:
                    emptyField = True

            elif self.getDataType() == 'INT_0D' or self.getDataType() == 'int_type':
                if e == -999999999:
                    emptyField = True

            elif self.getDataType() == 'STR_0D' or self.getDataType() == 'str_type':
                if e == '':
                    emptyField = True

            if emptyField:  # empty (signals) arrays appear in black
                self.setAvailableData(0)
                self.setStyleForWhenNotContainingData()
            else:
                self.setAvailableData(1)
                self.setStyleWhenContainingData()


        elif self.is2DOrLarger():
            e = self.evalPath(self.getDataName())
            if e.shape[0] == 0:
                self.setAvailableData(0)
                self.setStyleForWhenNotContainingData()
            else:
                self.setAvailableData(1)
                self.setStyleWhenContainingData()

        # elif self.isStructure():
        # pass

        elif self.isArrayOfStructure():
            self.setAvailableData(1)
            self.setStyleWhenContainingData()

        else:
            pass

        if self.hasAvailableData():  # update parents
            parent = self.parent()
            while parent is not None and not (parent.isIDSRoot()):
                parent.setAvailableData(True)
                parent.setStyleWhenContainingData()
                parent.updateStyle()
                parent = parent.parent()

    def plotOptions(self, dataTreeView, title='', label=None, xlabel=None,
                    plotWidget=None, time_index=None, coordinate_index=None):
        """Set plot options.

        Arguments:
            dataTreeView (QTreeWidget) : QVizDataTreeView object.
            title      (str) : Plot title.
            label      (str) : Label describing IMAS database (URI) and
                               path to signal/node in IDS database structure.
            xlabel     (str) : Plot X-axis label.
            ylabel     (str) : Plot Y-axis label.
        """

        ylabel = self.getName()

        if self.getUnits() is not None:
            if 'as_parent' in self.getUnits():
                ylabel += '[' + '' + ']'
            else:
                ylabel += '[' + self.getUnits() + ']'

        if time_index is None:
            time_index = self.timeValue()
            if plotWidget is not None and plotWidget.addTimeSlider:
                if plotWidget.sliderGroup is not None:
                    time_index = plotWidget.sliderGroup.slider.value()

        if coordinate_index is None:
            coordinate_index = 0
            if plotWidget is not None and plotWidget.addCoordinateSlider:
                coordinate_index = plotWidget.sliderGroup.slider.value()

        plotAxis = None
        if plotWidget is not None:
            plotAxis = plotWidget.getPlotAxis()

        if self.is0DAndDynamic() or (self.is1DAndDynamic() and (plotAxis is not None and plotAxis == 'TIME')):
            label = None
            xlabel = 'time'
            label = self.setLabelForFigure(dataTreeView.dataSource)
            if self.isPlotToPerformAlongTimeAxis(plotWidget):
                label = label.replace('itime', str(':'))
            else:
                label = label.replace('itime', str(time_index))
            label = QVizGlobalOperations.makeIMASPath(label)

        elif self.is1D():
            label = None
            xlabel2 = None
            coordinateNumber = 1
            label = self.setLabelForFigure(dataTreeView.dataSource)
            if "1.." in self.coordinates[coordinateNumber - 1]:
                xlabel2 = "1..N"
            else:
                if self.isPlotToPerformAlongTimeAxis(plotWidget):
                    if self.embedded_in_time_dependent_aos():
                        xlabel2 = 'time'
                        label = label.replace('itime', str(':')) + '[' + str(coordinate_index) + ']'
                    else:
                        if self.hasHomogeneousTime():
                            xlabel2 = 'time'
                        else:
                            xlabel2 = self.getIDSName() + "." + \
                                      self.evaluateCoordinateVsTime(coordinateNumber=coordinateNumber)
                        label = label.replace('itime', str(':'))
                else:
                    label = label.replace('itime', str(time_index))
                    if self.isCoordinateTimeDependent(coordinateNumber=1):

                        if self.hasHomogeneousTime():
                            xlabel2 = 'time'
                        else:
                            xlabel2 = self.getIDSName() + "." + \
                                      self.evaluateCoordinateVsTime(coordinateNumber=coordinateNumber)
                    else:
                        xlabel2 = self.getIDSName() + "." + \
                                  self.evaluateCoordinateVsTime(coordinateNumber=coordinateNumber)

            label = QVizGlobalOperations.makeIMASPath(label)

            if xlabel is None:
                xlabel = xlabel2

        if xlabel == 'time' or xlabel.endswith('.time'):
            xlabel = xlabel + '[s]'

        xlabel = xlabel.replace('itime', str(time_index))

        return label, xlabel, ylabel, title

    def labels(self, plotWidget, coordinateNumber, coordinate_index, time_index):

        xlabel = None
        label = self.setLabelForFigure(self.getDataTreeView().dataSource)

        if "1.." in self.coordinates[coordinateNumber - 1]:
            xlabel = "1..N"
        else:
            if self.isPlotToPerformAlongTimeAxis(plotWidget):
                if self.embedded_in_time_dependent_aos():
                    xlabel = 'time'
                    label = label.replace('itime', str(':')) + '[' + str(coordinate_index) + ']'
                else:
                    if self.hasHomogeneousTime():
                        xlabel = 'time'
                    else:
                        xlabel = self.getIDSName() + "." + \
                                 self.evaluateCoordinateVsTime(coordinateNumber=coordinateNumber)
                    label = label.replace('itime', str(':'))
            else:
                label = label.replace('itime', str(time_index))
                if self.isCoordinateTimeDependent(coordinateNumber=coordinateNumber):

                    if self.hasHomogeneousTime():
                        xlabel = 'time'
                    else:
                        xlabel = self.getIDSName() + "." + \
                                 self.evaluateCoordinateVsTime(coordinateNumber=coordinateNumber)
                else:
                    xlabel = self.getIDSName() + "." + \
                             self.evaluateCoordinateVsTime(coordinateNumber=coordinateNumber)

        label = QVizGlobalOperations.makeIMASPath(label)

        if xlabel == 'time' or xlabel.endswith('.time'):
            xlabel += '[s]'

        xlabel = xlabel.replace('itime', str(time_index))

        quantityName = self.getName()
        if self.getUnits() is not None:
            quantityName += '[' + self.getUnits() + ']'

        return quantityName, label, xlabel

    def getPlotAxisForDefaultPlotting(self):
        plotAxis = "DEFAULT"
        if self.embedded_in_time_dependent_aos() and \
                self.is0DAndDynamic():
            plotAxis = "TIME"
        elif self.is1DAndDynamic() and not \
                self.embedded_in_time_dependent_aos() and \
                self.isCoordinateTimeDependent(coordinateNumber=1):
            plotAxis = "TIME"
        else:
            plotAxis = "COORDINATE1"
        return plotAxis

    def get_data_error_lower(self, dataItem):
        data_error_lower = None
        dtv = self.getDataTreeView()
        try:
            tokens = str(self.getPath()).split("/")
            nodeName = tokens[-1]
            data_error_lower_path = self.getPath().replace("/" + tokens[-1], "", 1);
            data_error_lower_path = data_error_lower_path + "/" + nodeName + "_error_lower";
            #expression_error_lower_path = 'dtv.dataSource.data_entries[' + str(
            #    self.getOccurrence()) + '].' + data_error_lower_path
            data_error_lower = self.evalPath(QVizGlobalOperations.makePythonPath(data_error_lower_path))
            (x, y) = dataItem.getData()
            if np.shape(data_error_lower) != np.shape(y):
                return None
        except:
            return None
        return data_error_lower

    def get_data_error_upper(self, dataItem):
        data_error_upper = None
        dtv = self.getDataTreeView()
        try:
            tokens = str(self.getPath()).split("/")
            nodeName = tokens[-1]
            data_error_upper_path = self.getPath().replace("/" + tokens[-1], "", 1);
            data_error_upper_path = data_error_upper_path + "/" + nodeName + "_error_upper";
            #expression_error_upper_path = 'dtv.dataSource.data_entries[' + str(
            #    self.getOccurrence()) + '].' + data_error_upper_path
            data_error_upper = self.evalPath(QVizGlobalOperations.makePythonPath(data_error_upper_path))
            (x, y) = dataItem.getData()
            if np.shape(data_error_upper) != np.shape(y):
                return None
        except:
            return None
        return data_error_upper

    def evalPath(self, path):
        exec(self.getIDSName() + " = self.getIDSRef()")
        return eval(path)

    def nodeDataShareSameCoordinatesAs(self, selectedNodeList, figureKey=None):
        """Check if data already in figure and next to be added signal plot
        share the same coordinates and other conditions for a meaningful plot.
        """
        plotAxis=None
        api = self.dataTreeView.imas_viz_api
        if self.is1DAndDynamic():
            if figureKey is not None:
                figureKey, plotWidget = api.GetPlotWidget(dataTreeView=self.dataTreeView,
                                                              figureKey=figureKey, treeNode=self)
                
                plotAxis = plotWidget.getPlotAxis()

            for si in selectedNodeList:
                # Following check on coordinates is performed only if the current plot axis is not the time axis
                if figureKey is None or (plotAxis is not None and plotAxis != 'TIME'):
                    if self.getCoordinate(coordinateNumber=1) != si.getCoordinate(coordinateNumber=1):
                        return False
                if QVizPreferences.Allow_data_to_be_plotted_with_different_units == 0 and self.getUnits() != si.getUnits():
                    return False
        elif self.is0DAndDynamic():
            for si in selectedNodeList:
                if QVizPreferences.Allow_data_to_be_plotted_with_different_units == 0 and self.getUnits() != si.getUnits():
                    return False
        return True
