# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import numpy as np
import logging
import re
from imasviz.VizUtils import (QVizGlobalOperations, QVizGlobalValues,
                              QVizPreferences, GlobalColors)
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QTreeWidgetItem

# What a path segment looks like: a node name of the dictionary, then the
# position of one element of a structure array. Both spellings the shot view
# hands out -- `magnetics.flux_loop[9].field.data` and the bare `magnetics` of
# an IDS root -- are covered by walking one of these after the other.
NODE_NAME = re.compile(r'[A-Za-z_]\w*')
ELEMENT_INDEX = re.compile(r'-?\d+')


def resolveIDSPath(path, idsName, idsInstance):
    """The value an IDS path names, taken out of the IDS instance itself.

    The shot view builds these paths as text -- the parser spells them, the
    builder turns them into the tree, the documentation panel turns a tree path
    back into one -- and it always asked for their value with
    `exec(idsName + " = self.getIDSRef()")` followed by `eval(path)`. That pair
    never read the IDS: it bound a *local name* in the frame of the caller and
    asked `eval` to find it back in the frame's locals, which is a CPython
    implementation detail. Measured on Python 3.11.5 it answers; on the frame
    semantics of Python 3.13 the binding made by `exec` is not visible to the
    `eval` that follows, and every node of a real session died with
    `NameError: name 'magnetics' is not defined` inside `updateStyle`, from
    `QVizDataTreeView.py:574 in event` down -- the tree stops building at the
    node that asks. Nothing in the traceback names the IDS or the case.

    Walking the instance instead answers the same value, and answers it faster:
    measured on the reference case (WEST 54924 run 0, its own dictionary 3.35.0),
    building the view of `magnetics` occurrence 0 and then of `equilibrium`
    occurrence 0 asks **15 131** paths -- **11 428** and **3 703** -- over **802**
    distinct shapes, and the walk answers each of them identically in **0,053 s**
    where the pair took **0,189 s**. Asked of every signal node of those two views
    through the callers that are still reached (`coordinateValues`, the error
    bars), it is **22 658** paths, **0,076 s** against **0,630 s**.

    A path is refused by name, never by a bare `NameError` or `SyntaxError`: a
    path of another IDS, an index that was never given a value -- `[i]`, `[itime]`
    -- and a coordinate spelled as a range instead of a position. The last one is
    not hypothetical: **537** nodes of `magnetics` and **6** of `equilibrium` on
    this case carry a coordinate the dictionary spells `1...2` or `1...3`, which
    reaches here as `magnetics.1...2` and was refused with
    `SyntaxError: invalid syntax (<string>, line 1)`, swallowed by the caller.
    It is refused the same way now, with the offending text named.
    """
    if idsInstance is None:
        raise ValueError("Cannot read %s: the IDS %s is not loaded in this view."
                         % (path, idsName))
    if idsName is None or not path.startswith(idsName):
        raise ValueError("Cannot read %s: it is not a path of IDS %s."
                         % (path, idsName))

    value = idsInstance
    position = len(idsName)
    while position < len(path):
        character = path[position]
        if character == '.':
            name = NODE_NAME.match(path, position + 1)
            if name is None:
                raise ValueError(
                    "Cannot read %s: %s is not a node of the dictionary."
                    % (path, path[position + 1:].split('[')[0]))
            value = getattr(value, name.group())
            position = name.end()
        elif character == '[':
            end = path.find(']', position)
            if end < 0:
                raise ValueError("Cannot read %s: a bracket is left open." % path)
            index = path[position + 1:end]
            if not ELEMENT_INDEX.fullmatch(index):
                raise ValueError(
                    "Cannot read %s: the element [%s] was never given a position."
                    % (path, index))
            value = value[int(index)]
            position = end + 1
        else:
            raise ValueError("Cannot read %s: %s is not a node of the dictionary."
                             % (path, path[position:]))
    return value


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
        self.applyCoordinate(coordinateNumber, value)

    def setDefaultCoordinate(self, coordinateNumber):
        coordinate = self.default_coordinates.get(coordinateNumber - 1)
        if coordinate is not None:
            self.applyCoordinate(coordinateNumber, coordinate)

    def applyCoordinate(self, coordinateNumber, value):
        """Record the coordinate the user picked, with the time flag it carries.

        The flag and the renamed child belong to coordinateNumber: writing them
        under coordinate 1 leaves a stale flag on the coordinate being changed
        and relabels the wrong child.
        """
        self.coordinates[coordinateNumber - 1] = value
        if value.endswith('/time') or value.endswith('.time') or value == 'time':
            self.coordinates_explicitly_time_dependent[coordinateNumber] = 1
        else:
            self.coordinates_explicitly_time_dependent[coordinateNumber] = 0
        coordinateLabel = 'coordinate' + str(coordinateNumber)
        for i in range(self.childCount()):
            child = self.child(i)
            if child.text(0).startswith(coordinateLabel):
                child.setText(0, coordinateLabel + '=' + value)
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

    def coordinateValues(self, coordinateNumber, dataTreeView):
        """The values one coordinate of this node is sampled on.

        A coordinate the dictionary spells as a range -- `1..N` -- has no values
        in the case: the position of the element *is* the axis, so the positions
        are handed back. Any other coordinate is a path of the IDS, and it is
        read off the instance the view holds.
        """
        if len(self.coordinates) < coordinateNumber:
            return None
        if self.coordinates[coordinateNumber - 1] == "1..N" or \
                self.coordinates[coordinateNumber - 1] == "1...N":
            return np.array(range(len(self.resolvePath(self.getDataName()))))
        return self.resolvePath(self.getIDSName() + '.' +
                                self.evaluateCoordinate(coordinateNumber))

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

    def getIDSRef(self):
        return self.idsRef

    def getData(self):
        return self.infoDict

    def getParametrizedPath(self):
        # e.g: 'magnetics.flux_loop[i].position[j]'
        return self.parametrizedPath

    def getParametrizedDataPath(self):
        # e.g: 'magnetics.flux_loop[i].position[j].r'
        # Only a leaf is spelled this way: the walk writes the parametrized path
        # on a leaf and nowhere else, so a structure or an element of a dynamic
        # array has no data path to name. The callers answer the node's name when
        # they get nothing (QVizNodePlotting.path, QVizSlices.labelOf, the
        # dataPathOf of every plot frame), which is the right answer for such a
        # node. Appending the name to a path that is not there is not: it killed
        # every left click on a folder of the tree, inside the panel that refuses
        # a node by naming it.
        if not self.parametrizedPath:
            return None
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
        if self.isIDSRoot():
            view = self.getDataTreeView()
            if view is None:
                return False
            # Asked of the case, not of the data dictionary: measured, the loop
            # this replaced opened with eval("imas." + idsName + "()") and raised
            # AttributeError on every IDS of this IMAS stack, which took the
            # pop-up menu entry and the double click down with it.
            return bool(view.occurrencesOf(self.getIDSName()))
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

    def getCoordinateUnits(self, coordinateNumber):
        """Unit of the coordinateN named by the dictionary for this node."""
        return self.infoDict.get('coordinate' + str(coordinateNumber) + '_units')

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

        if self.is1D():

            # And error occurs for non-homogeneous cases (time array is
            # different or empty). This is 'solved' with the below fix using
            # 'e' variable
            e = self.resolvePath(self.getDataName())
            #print(e)
            if self.getDataType() != 'STR_1D' and (e is None or e.all() is None):
                self.setAvailableData(0)
                self.setStyleForWhenNotContainingData()
            elif len(self.resolvePath(self.getDataName())) == 0:  # empty (signals) arrays appear in black
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

            e = self.resolvePath(self.getDataName())

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
            e = self.resolvePath(self.getDataName())
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

        if coordinate_index is None:
            coordinate_index = 0

        plotAxis = None
        if plotWidget is not None:
            plotAxis = plotWidget.getPlotAxis()

        # The unit of whatever ends up on the abscissa, set where the label is
        # picked rather than where it is printed.
        xunits = None

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

            if xlabel2 != 'time' and xlabel2 != "1..N":
                xunits = self.getCoordinateUnits(coordinateNumber)

            if xlabel is None:
                xlabel = xlabel2
            else:
                # The caller picked the abscissa (a plot configuration, a
                # plugin): its unit is not ours to guess.
                xunits = None

        # A time axis is always in seconds. The coordinate an array is indexed
        # by can name something else entirely (the r of an outline paired with
        # the z being drawn), so its unit must not be used for that axis.
        if xlabel == 'time' or xlabel.endswith('.time'):
            xunits = 's'
        if xunits:
            xlabel += '[' + xunits + ']'

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

        xunits = None
        if xlabel == 'time' or xlabel.endswith('.time'):
            xunits = 's'
        elif xlabel != "1..N":
            xunits = self.getCoordinateUnits(coordinateNumber)
        if xunits:
            xlabel += '[' + xunits + ']'

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
        """The `_error_lower` sibling of this node, when the case holds one.

        Most leaves have no such sibling in the dictionary, so "there is none" is
        an answer, not a failure: it is handed back as None and the plot draws
        without the bar.
        """
        try:
            tokens = str(self.getPath()).split("/")
            nodeName = tokens[-1]
            data_error_lower_path = self.getPath().replace("/" + tokens[-1], "", 1);
            data_error_lower_path = data_error_lower_path + "/" + nodeName + "_error_lower";
            data_error_lower = self.resolvePath(
                QVizGlobalOperations.makePythonPath(data_error_lower_path))
            (x, y) = dataItem.getData()
            if np.shape(data_error_lower) != np.shape(y):
                return None
        except Exception:
            return None
        return data_error_lower

    def get_data_error_upper(self, dataItem):
        """The `_error_upper` sibling of this node, when the case holds one."""
        try:
            tokens = str(self.getPath()).split("/")
            nodeName = tokens[-1]
            data_error_upper_path = self.getPath().replace("/" + tokens[-1], "", 1);
            data_error_upper_path = data_error_upper_path + "/" + nodeName + "_error_upper";
            data_error_upper = self.resolvePath(
                QVizGlobalOperations.makePythonPath(data_error_upper_path))
            (x, y) = dataItem.getData()
            if np.shape(data_error_upper) != np.shape(y):
                return None
        except Exception:
            return None
        return data_error_upper

    def resolvePath(self, path):
        """The value this path names, read off the IDS instance of the view."""
        return resolveIDSPath(path, self.getIDSName(), self.getIDSRef())
