import numpy as np
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues
from imasviz.VizGUI.VizTreeView.QVizTreeNodeExtraAttributes import QVizTreeNodeExtraAttributes

from PyQt5.QtWidgets import QTreeWidgetItem


class QVizTreeNode(QTreeWidgetItem):

    def __init__(self, *args, **kwargs):
        #from imasviz.VizGUI.VizTreeView.QVizDataTreeView import QVizDataTreeView

        self.globalTime = None
        if len(args) == 2:
            self.treeNodeExtraAttributes = QVizTreeNodeExtraAttributes()
            parent = args[0]
            name = args[1]
            self.infoDict = {}
            QTreeWidgetItem.__init__(self, parent, name)
        elif len(args) == 3:
            self.treeNodeExtraAttributes = QVizTreeNodeExtraAttributes()
            parent = args[0]
            name = args[1]
            self.infoDict = args[2]
            QTreeWidgetItem.__init__(self, parent, name)
        elif len(args) == 4:
            parent = args[0]
            name = args[1]
            self.infoDict = args[2]
            self.treeNodeExtraAttributes = args[3]
            QTreeWidgetItem.__init__(self, parent, name)


        # if len(args) == 1:
        #     QTreeWidgetItem.__init__(self, *args, **kwargs)
        #     self.infoDict = args[0]
        # elif len(args) == 2:
        #     if type(args[0]) is QVizDataTreeView or type(args[0]) is QVizTreeNode:
        #         self.infoDict = {}
        #         parent = args[0]
        #         name = args[1]
        #         QTreeWidgetItem.__init__(self, parent, name)
        # elif len(args) == 3:
        #     if type(args[0]) is QVizTreeNode:
        #         parent = args[0]
        #         name = args[1]
        #         self.infoDict = args[2]
        #         QTreeWidgetItem.__init__(self, parent, name)
        # elif len(args) == 4:
        #     if type(args[0]) is QVizTreeNode:
        #         parent = args[0]
        #         name = args[1]
        #         self.infoDict = args[2]
        #         self.treeNodeExtraAttributes = args[3]
        #         QTreeWidgetItem.__init__(self, parent, name)

    def isCoordinateTimeDependent(self, coordinate):
         if coordinate is not None:
             if '/time' in coordinate or '.time' in coordinate or coordinate == 'time':
                return True
         return False

    def isCoordinate1_time_dependent(self):
        return self.infoDict["coordinate1_time_dependent"] == 1

    def index_name_of_itime(self):
        i = 0
        for key in QVizGlobalValues.indices:
            if i == int(self.treeNodeExtraAttributes.itime_index):
                return QVizGlobalValues.indices[key]
            i = i + 1

    def replaceBrackets(self, toReplace): #replace '[' by '(' and ']' by ')'
        c = toReplace.replace("[", "(")
        return c.replace("]", ")")

    def evaluateCoordinate1(self):
        coordinate1 = self.evaluateCoordinate1VsTime()
        if self.treeNodeExtraAttributes.time_dependent(self.treeNodeExtraAttributes.coordinate1):
            coordinate1 = coordinate1.replace("[itime]", "[" + self.timeValue() + "]")
        return coordinate1

    def evaluateCoordinate1At(self, itimeValue):
        coordinate1 = self.evaluateCoordinate1VsTime()
        if self.treeNodeExtraAttributes.time_dependent(self.treeNodeExtraAttributes.coordinate1):
            coordinate1 = coordinate1.replace("[itime]", "[" + str(itimeValue) + "]")
        if coordinate1 == None:
            coordinate1 = self.treeNodeExtraAttributes.coordinate1
        return coordinate1

    def coordinate1LabelAndTitleForTimeSlices(self, dtv, node, index):
        # Get time index
        itime_index = node.getNodeData()['itime_index']
        # Get IDS name
        idsName = node.getIDSName()
        title = ''
        xlabel= ''
        if self.treeNodeExtraAttributes.coordinate1 == "1..N" or \
            self.treeNodeExtraAttributes.coordinate1 == "1...N":
            title = "coordinate1 = " + str(index)
        else:
            xlabel = str("ids." + idsName + "." + self.evaluateCoordinate1())
            tokens_list = xlabel.split(".")
            coord1 = tokens_list[-1]
            title = coord1 + "[" + itime_index + "]=" + xlabel
        # Set and format label

        label = dtv.dataSource.getShortLabel() + ":" + self.getPath()

        #label = nodeData['dataName']
        #label = label.replace('ids.','')
        #label = QVizGlobalOperations.replaceBrackets(label)
        #label = QVizGlobalOperations.replaceDotsBySlashes(label)
        # Set and format xlabel
        xlabel = xlabel.replace('ids.','')
        xlabel = QVizGlobalOperations.replaceBrackets(xlabel)
        xlabel = QVizGlobalOperations.replaceDotsBySlashes(xlabel)

        return label, title, xlabel

    def correctLabelForTimeSlices(self, label, title):
        if label is not None:
            label = label.replace('ids.', '')
            label = QVizGlobalOperations.replaceBrackets(label)
            label = QVizGlobalOperations.replaceDotsBySlashes(label)
        if label is not None:
            label = label.replace('time_slice(0)', 'time_slice(:)')
        if title is not None:
            title = title.replace('time_slice(0)', 'time_slice(:)')
        return label, title


    def coordinate1Label(self, idsName, index, ids):
        if self.treeNodeExtraAttributes.coordinate1 == "1..N" or \
            self.treeNodeExtraAttributes.coordinate1 == "1...N":
            return "[" + str(index) + "]"
            #return None
        to_eval = "ids." + idsName + \
                  "." + self.evaluateCoordinate1() + "[" + str(index) + "]"
        coordinate1_value = eval(to_eval)
        tokens_list = to_eval.split(".")
        coord1 = tokens_list[-1]
        label = coord1 + "=" + str(coordinate1_value)
        return label

    def evaluateCoordinate1VsTime(self):#the result can eventually depend on [itime]
        return self.evaluatePath(self.treeNodeExtraAttributes.coordinate1)

    def coordinate1Length(self, selectedNodeData, ids):

        if self.treeNodeExtraAttributes.coordinate1 == "1..N" or \
            self.treeNodeExtraAttributes.coordinate1 == "1...N":
            r = np.array([eval('ids.' + selectedNodeData['dataName'])])
            return len(r[0])
        # Set python expression to get lenght of the array
        to_evaluate = 'ids.' + selectedNodeData['IDSName'] + '.' + \
                       self.evaluateCoordinate1()
        len_to_evaluate = eval('len(' + to_evaluate + ')')
        return len_to_evaluate

    def timeMaxValue(self):
        if self.treeNodeExtraAttributes.time_dependent(self.treeNodeExtraAttributes.aos):
            return self.treeNodeExtraAttributes.aos_indices_max_values[self.index_name_of_itime()]

    def timeValue(self):
        if self.treeNodeExtraAttributes.time_dependent(self.treeNodeExtraAttributes.aos):
            return self.treeNodeExtraAttributes.aos_indices_values[self.index_name_of_itime()]

    def getDataPathVsTime(self, path):
        return self.evaluatePath(path)

    def evaluatePath(self, path):
        aos_valued = None
        path = self.patchIndices(path) #replace [i1] by [i], [i2] by [j] and so on
        for i in range(0, self.treeNodeExtraAttributes.aos_parents_count): #loop on all AOSs which contain this path
            index_name = QVizGlobalValues.indices[str(i + 1)]
            index_value = self.treeNodeExtraAttributes.aos_indices_values[index_name] #AOS index value for this node
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

    def getDataPath(self, data_path_vs_time, itime_value):
        s = "[itime]"
        replacement = "[" + str(itime_value) + "]"
        return data_path_vs_time.replace(s, replacement)

    def containedInDynamicAOS(self):
        if self.getPathDoc() is None:
            return -1
        try:
            self.getPathDoc().index("itime")
        except:
            return -1  # 'itime' not found
        return 1

    def getDataVsTime(self):
        data_list = []
        aos_vs_itime = self.getDataPathVsTime(self.treeNodeExtraAttributes.aos)
        #print "QVizTreeNode : time max value = " + self.timeMaxValue()
        for itime in range(0, int(self.timeMaxValue())):
            data_path = self.getDataPath(aos_vs_itime, itime)
            data_list.append(data_path)
        return data_list

    def getNodeData(self):
        return self.infoDict

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

    def isDataAvailable(self):
        return self.infoDict.get('availableData')

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

    def setPath(self, path):
        self.infoDict['Path'] = path

    def setIDSName(self, idsName):
        self.infoDict['IDSName'] = idsName

    def setDataName(self, dataName):
        self.infoDict['dataName'] = dataName

    def setOccurrence(self, occurrence):
        self.infoDict['occurrence'] = occurrence

    def is0D(self):
        return self.getDataType() == 'FLT_0D' or self.getDataType() == 'INT_0D' or self.getDataType() == 'STR_0D'

    def is1D(self):
        return self.getDataType() == 'FLT_1D' or self.getDataType() == 'INT_1D' or self.getDataType() == 'STR_1D'

    def is0DAndDynamic(self):
        return self.is0D() and self.isDynamicData()

    def is1DAndDynamic(self):
        return self.is1D() and self.isDynamicData()


